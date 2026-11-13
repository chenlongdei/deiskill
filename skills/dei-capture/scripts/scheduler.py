"""把一个 Python 脚本登记成每天定时运行的系统任务，不依赖任何 Agent。

- macOS：launchd（~/Library/LaunchAgents/com.deiskill.<name>.plist）
- Windows：任务计划程序（任务名 deiskill-<name>，通过 ~/.deiskill/tasks/<name>.cmd 包一层以便写日志）
- Linux：crontab（行尾带 # deiskill:<name> 标记）

macOS 上已验证的坑（2026-11-12）：
1. 「完全磁盘访问权限」按真正的 Python 程序判断。/usr/bin/python3 只是转接程序，授权给 Python.app 后
   plist 里也必须直接写 Python.app/Contents/MacOS/Python，否则写外接盘、桌面、文稿仍报 Operation not permitted。
2. plist 的日志路径如果在受保护位置（如外接盘），launchd 连任务都起不来（EX_CONFIG），日志统一放 ~/Library/Logs/deiskill/。
"""
from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()


def log_dir() -> Path:
    if sys.platform == "darwin":
        d = HOME / "Library" / "Logs" / "deiskill"
    else:
        d = HOME / ".deiskill" / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def scheduler_python() -> str:
    """定时任务要用的 Python 程序路径。macOS 上优先用框架里的 Python.app（权限按它判断）。"""
    if sys.platform == "darwin":
        app = Path(sys.base_prefix) / "Resources" / "Python.app" / "Contents" / "MacOS" / "Python"
        if app.exists():
            return str(app)
    return str(Path(sys.executable).resolve())


def disk_access_app() -> str:
    """macOS 上要加进「完全磁盘访问权限」的程序（Python.app 整个包）。"""
    p = Path(scheduler_python())
    for parent in p.parents:
        if parent.suffix == ".app":
            return str(parent)
    return str(p)


def protected(path: Path) -> bool:
    """macOS 上后台任务默认不能写的位置：外接盘、桌面、文稿、下载、iCloud。"""
    if sys.platform != "darwin":
        return False
    p = str(Path(path).expanduser().resolve())
    roots = [os.path.join("/Volumes", "")] + [str(HOME / x) for x in ("Desktop", "Documents", "Downloads", "Library/Mobile Documents")]
    return any(p.startswith(r) for r in roots)


def _parse_at(at: str) -> tuple[int, int]:
    h, m = at.split(":")
    h, m = int(h), int(m)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(f"时间格式应为 HH:MM：{at}")
    return h, m


# ---------- macOS ----------

def _label(name: str) -> str:
    return f"com.deiskill.{name}"


def _plist_path(name: str) -> Path:
    return HOME / "Library" / "LaunchAgents" / f"{_label(name)}.plist"


def _launchctl(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def _mac_load(label: str, plist: Path):
    uid = os.getuid()
    _launchctl("bootout", f"gui/{uid}/{label}")
    r = _launchctl("bootstrap", f"gui/{uid}", str(plist))
    if r.returncode != 0:
        raise RuntimeError(f"launchctl bootstrap 失败：{r.stderr.strip()}")


def mac_write_test(target_dir: Path, timeout: int = 15) -> tuple[bool, str]:
    """用一个临时 launchd 任务，测试后台 Python 能不能写 target_dir。"""
    name = "writetest"
    label, plist = _label(name), _plist_path(name)
    probe = Path(target_dir) / ".deiskill_write_test"
    out = log_dir() / "writetest.log"
    out.write_text("")
    code = f"import pathlib;pathlib.Path({str(probe)!r}).write_text('ok');print('ok')"
    plist.parent.mkdir(parents=True, exist_ok=True)
    with open(plist, "wb") as f:
        plistlib.dump({"Label": label, "ProgramArguments": [scheduler_python(), "-c", code],
                       "StandardOutPath": str(out), "StandardErrorPath": str(out)}, f)
    try:
        _mac_load(label, plist)
        _launchctl("kickstart", f"gui/{os.getuid()}/{label}")
        for _ in range(timeout * 2):
            time.sleep(0.5)
            if probe.exists():
                return True, "后台任务可以写入保存位置"
            if "Error" in out.read_text(errors="replace"):
                break
        msg = out.read_text(errors="replace").strip().splitlines()
        return False, (msg[-1] if msg else "后台任务没有写入（超时）")
    finally:
        _launchctl("bootout", f"gui/{os.getuid()}/{label}")
        plist.unlink(missing_ok=True)
        probe.unlink(missing_ok=True)


def _mac_install(name, argv, at, workdir, log):
    h, m = _parse_at(at)
    plist = _plist_path(name)
    plist.parent.mkdir(parents=True, exist_ok=True)
    with open(plist, "wb") as f:
        plistlib.dump({
            "Label": _label(name),
            "ProgramArguments": [scheduler_python(), *argv],
            "WorkingDirectory": str(workdir),
            "EnvironmentVariables": {"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin", "PYTHONUTF8": "1"},
            "StartCalendarInterval": {"Hour": h, "Minute": m},
            "StandardOutPath": str(log), "StandardErrorPath": str(log),
        }, f)
    _mac_load(_label(name), plist)
    return str(plist)


def _mac_status(name):
    r = _launchctl("print", f"gui/{os.getuid()}/{_label(name)}")
    if r.returncode != 0:
        return None
    running = "pid =" in r.stdout
    return {"任务": _label(name), "文件": str(_plist_path(name)), "正在运行": running}


def _mac_remove(name):
    _launchctl("bootout", f"gui/{os.getuid()}/{_label(name)}")
    _plist_path(name).unlink(missing_ok=True)


def run_now(name) -> bool:
    """立刻触发一次已登记的任务（和定时触发走同一条路）。"""
    if sys.platform == "darwin":
        return _launchctl("kickstart", f"gui/{os.getuid()}/{_label(name)}").returncode == 0
    if sys.platform.startswith("win"):
        return subprocess.run(["schtasks", "/Run", "/TN", f"deiskill-{name}"], capture_output=True).returncode == 0
    return False


# ---------- Windows ----------

def _win_install(name, argv, at, workdir, log):
    h, m = _parse_at(at)
    tasks = HOME / ".deiskill" / "tasks"
    tasks.mkdir(parents=True, exist_ok=True)
    cmd = tasks / f"{name}.cmd"
    args = " ".join(f'"{a}"' for a in [scheduler_python(), *argv])
    cmd.write_text(f'@echo off\r\nchcp 65001 >nul\r\nset PYTHONUTF8=1\r\ncd /d "{workdir}"\r\n{args} >> "{log}" 2>&1\r\n',
                   encoding="utf-8")
    r = subprocess.run(["schtasks", "/Create", "/F", "/SC", "DAILY", "/ST", f"{h:02d}:{m:02d}",
                        "/TN", f"deiskill-{name}", "/TR", f'"{cmd}"'], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"schtasks 失败：{r.stderr.strip() or r.stdout.strip()}")
    return str(cmd)


def _win_status(name):
    r = subprocess.run(["schtasks", "/Query", "/TN", f"deiskill-{name}"], capture_output=True, text=True)
    return {"任务": f"deiskill-{name}"} if r.returncode == 0 else None


def _win_remove(name):
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", f"deiskill-{name}"], capture_output=True)


# ---------- Linux ----------

def _cron_lines():
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return r.stdout.splitlines() if r.returncode == 0 else []


def _cron_write(lines):
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)


def _linux_install(name, argv, at, workdir, log):
    if not shutil.which("crontab"):
        raise RuntimeError("没有 crontab：请先安装 cron")
    h, m = _parse_at(at)
    tag = f"# deiskill:{name}"
    args = " ".join(f"'{a}'" for a in [scheduler_python(), *argv])
    line = f"{m} {h} * * * cd '{workdir}' && PYTHONUTF8=1 {args} >> '{log}' 2>&1 {tag}"
    _cron_write([x for x in _cron_lines() if not x.endswith(tag)] + [line])
    return "crontab"


def _linux_status(name):
    return {"任务": "crontab"} if any(x.endswith(f"# deiskill:{name}") for x in _cron_lines()) else None


def _linux_remove(name):
    _cron_write([x for x in _cron_lines() if not x.endswith(f"# deiskill:{name}")])


# ---------- 统一入口 ----------

def install(name: str, argv: list[str], at: str, workdir: Path) -> dict:
    """登记每天 at（本机时间）运行一次 argv（第一个是脚本路径）。返回说明。"""
    log = log_dir() / f"{name}.log"
    if sys.platform == "darwin":
        where = _mac_install(name, argv, at, workdir, log)
    elif sys.platform.startswith("win"):
        where = _win_install(name, argv, at, workdir, log)
    else:
        where = _linux_install(name, argv, at, workdir, log)
    return {"已登记": where, "每天": at, "日志": str(log), "Python": scheduler_python()}


def status(name: str):
    if sys.platform == "darwin":
        return _mac_status(name)
    if sys.platform.startswith("win"):
        return _win_status(name)
    return _linux_status(name)


def remove(name: str):
    if sys.platform == "darwin":
        _mac_remove(name)
    elif sys.platform.startswith("win"):
        _win_remove(name)
    else:
        _linux_remove(name)
