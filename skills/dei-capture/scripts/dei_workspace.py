#!/usr/bin/env python3
"""dei 工作区：所有 dei Skill 共用的一个数据根目录。

这份文件在每个 dei Skill 的 scripts/ 里各有一份，内容完全相同（validate_repo.py 会检查），
因为 Skill 是分别安装的，彼此看不到对方的目录。改它时同时改所有副本。

结构（一级按「输入 → 处理 → 输出」排序，99 永远放最后）：

    <工作区>/
    ├── .dei-workspace        标记文件：找不到它就说明外接盘没挂载或路径错了，直接报错
    ├── 使用说明.md
    ├── 01_我的清单/          用户手动维护、Skill 只读的表（监控工作簿、账号覆盖表、选题表）
    ├── 02_采集/              输入：YouTube、抖音、转写
    ├── 03_日报/              处理：综合、政策与商机、AI情报、知乎热榜
    ├── 04_知识库/            处理：一个主题一个文件夹
    ├── 05_成品/              输出
    └── 99_系统/              运行总账.jsonl、日志/、状态/、备份/、测试/、缓存/

命名规则：
- 长期跟踪的对象按名字命名、不带日期，内容往里累加（博主、频道、知识库）。
- 一次性的批次命名为 YYYY-MM-DD_HHMM_主题（北京时间）；一天可能有一次以上的高频批次先按年分一层。
- 批次文件夹第一层只放人看的文件，机器数据放进 _原始数据/。
- 试跑、测试一律写到 99_系统/测试/（设环境变量 DEI_TRIAL=1）。

工作区位置记在 ~/.deiskill/config.json 的 workspace_root（与 Agent 无关）。
环境变量 DEI_WORKSPACE 可临时指定（测试用）。

命令行：
    python3 scripts/dei_workspace.py where                 打印工作区和各阶段目录（JSON）
    python3 scripts/dei_workspace.py init <路径>           新建或接管工作区，写入共享配置
    python3 scripts/dei_workspace.py log <skill> <任务> <状态> [产出路径 ...]   记一行运行总账
    python3 scripts/dei_workspace.py latest [skill] [任务]   查最近一次运行
    python3 scripts/dei_workspace.py clean                 清理 99_系统/缓存 里 30 天前的文件
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

VERSION = 1
BJ = timezone(timedelta(hours=8))  # 北京时间用固定偏移，不依赖时区数据库
MARKER = ".dei-workspace"
SHARED_CONFIG = Path(os.environ.get("DEI_SHARED_CONFIG") or Path.home() / ".deiskill" / "config.json")

STAGES = {
    "lists": "01_我的清单",
    "capture": "02_采集",
    "daily": "03_日报",
    "notebook": "04_知识库",
    "output": "05_成品",
    "system": "99_系统",
}
SYSTEM_DIRS = ("日志", "状态", "备份", "测试", "缓存")
LEDGER = "运行总账.jsonl"
CACHE_DAYS = 30


class WorkspaceError(SystemExit):
    pass


# ---------------------------------------------------------------- 定位


# 单个 Skill 的旧式数据目录覆盖（测试用）。设了它们而没设 DEI_WORKSPACE 时，不碰真实工作区。
ISOLATION_VARS = ("DEI_CAPTURE_DATA_DIR", "DEI_CAPTURE_CONFIG", "DEI_DAILY_DATA_DIR", "DEI_NOTEBOOK_DATA_DIR")


def configured_root() -> str:
    env = os.environ.get("DEI_WORKSPACE")
    if env:
        return env
    if any(os.environ.get(v) for v in ISOLATION_VARS):
        return ""
    if SHARED_CONFIG.is_file():
        try:
            return json.loads(SHARED_CONFIG.read_text(encoding="utf-8")).get("workspace_root", "") or ""
        except (json.JSONDecodeError, OSError):
            return ""
    return ""


def root() -> Path:
    """工作区根目录。没配置、目录不在、缺标记文件都直接报错，不静默新建。"""
    value = configured_root()
    if not value:
        raise WorkspaceError(
            "还没有 dei 工作区：按 SKILL.md「首次配置」问用户放在哪里（给 2—3 个建议），"
            f"确认后运行 python3 scripts/dei_workspace.py init <路径>（会写入 {SHARED_CONFIG}）"
        )
    path = Path(value).expanduser()
    if not (path / MARKER).is_file():
        hint = "" if path.parent.exists() else "连上一级目录都不在，多半是外接盘或云盘没有挂载/同步。"
        raise WorkspaceError(
            f"找不到 dei 工作区：{path} 下没有 {MARKER}。{hint}请用户确认路径；"
            "不要在这里新建，否则数据会写到错误的位置。"
        )
    return path


def trial() -> bool:
    return os.environ.get("DEI_TRIAL", "").strip() not in ("", "0", "false", "no")


def stage(key: str, create: bool = True) -> Path:
    """某个阶段的目录。DEI_TRIAL=1 时改写到 99_系统/测试/<阶段>/。"""
    base = root()
    name = STAGES[key]
    path = base / STAGES["system"] / "测试" / name if trial() and key not in ("system", "lists") else base / name
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def system(sub: str = "", create: bool = True) -> Path:
    """99_系统/ 下的子目录：日志、状态、备份、测试、缓存。"""
    path = root() / STAGES["system"]
    if sub:
        path = path / sub
    if create:
        path.mkdir(parents=True, exist_ok=True)
    return path


def lists_file(name: str) -> Path:
    return stage("lists") / name


# ---------------------------------------------------------------- 命名


def now() -> datetime:
    return datetime.now(BJ)


def slug(text: str, limit: int = 40) -> str:
    text = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", str(text)).strip()
    text = re.sub(r"\s+", "-", text)
    return text[:limit].rstrip("-.") or "untitled"


def batch_name(topic: str = "", when: datetime | None = None) -> str:
    when = (when or now()).astimezone(BJ)
    name = when.strftime("%Y-%m-%d_%H%M")
    return f"{name}_{slug(topic)}" if topic else name


def batch_dir(parent: Path, topic: str = "", yearly: bool = False, when: datetime | None = None) -> Path:
    """新建批次文件夹 YYYY-MM-DD_HHMM[_主题]；yearly=True 时先按年分一层。重名加 -2、-3。"""
    when = (when or now()).astimezone(BJ)
    base = parent / f"{when:%Y}" if yearly else parent
    name = batch_name(topic, when)
    path, n = base / name, 1
    while path.exists():
        n += 1
        path = base / f"{name}-{n}"
    path.mkdir(parents=True)
    return path


def raw_dir(batch: Path) -> Path:
    path = batch / "_原始数据"
    path.mkdir(parents=True, exist_ok=True)
    return path


# ---------------------------------------------------------------- 运行总账


def log_run(skill: str, task: str, status: str, outputs=(), **extra) -> None:
    """在 99_系统/运行总账.jsonl 记一行。工作区不可用时安静跳过，不影响主任务。"""
    try:
        ledger = system() / LEDGER
    except SystemExit:
        return
    row = {"time": now().isoformat(timespec="seconds"), "skill": skill, "task": task, "status": status,
           "outputs": [str(p) for p in outputs if p], **({"trial": True} if trial() else {}), **extra}
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    _maybe_clean()


def latest(skill: str = "", task: str = "", n: int = 1) -> list[dict]:
    ledger = system(create=False) / LEDGER
    if not ledger.is_file():
        return []
    rows = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if (not skill or r.get("skill") == skill) and (not task or r.get("task") == task) and not r.get("trial"):
            rows.append(r)
    return rows[-n:][::-1]


# ---------------------------------------------------------------- 清理


def clean(days: int = CACHE_DAYS) -> int:
    cache = system("缓存")
    cutoff = time.time() - days * 86400
    removed = 0
    for p in sorted(cache.rglob("*"), reverse=True):
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
            elif p.is_dir() and not any(p.iterdir()):
                p.rmdir()
        except OSError:
            continue
    return removed


def _maybe_clean() -> None:
    stamp = system("状态") / ".last_clean"
    try:
        if stamp.is_file() and time.time() - stamp.stat().st_mtime < 86400:
            return
        clean()
        stamp.write_text(now().isoformat(timespec="seconds"), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------- 初始化

GUIDE = """# dei 工作区使用说明

这个文件夹由 deiskill 自动维护，所有 dei Skill 的产出都在这里。路径记在 `~/.deiskill/config.json`。

| 文件夹 | 放什么 | 谁写入 |
| --- | --- | --- |
| `01_我的清单/` | 你手动维护的表：抖音监控工作簿、账号覆盖表、选题表。Skill 只读或只追加分页，不删你的内容 | 你 |
| `02_采集/` | YouTube 搜索清单、频道、逐字稿；抖音博主、关键词巡检；音视频转写 | dei-capture |
| `03_日报/` | 综合日报（按年分）、政策与商机、AI情报、知乎热榜 | dei-daily-report |
| `04_知识库/` | 一个主题一个文件夹：问答、学习路线、产物 | dei-notebook |
| `05_成品/` | 准备对外发布的文章、图卡、脚本 | 输出层 |
| `99_系统/` | 运行总账、日志、状态、备份、测试、缓存。平时不用看 | 所有 Skill |

## 命名规则

- **长期跟踪的对象**按名字命名，不带日期，内容往里累加：`博主/<博主名>/`、`频道/Claude/`。
- **一次性批次**命名为 `YYYY-MM-DD_HHMM_主题`（北京时间）：`搜索/2026-11-11_2326_Claude-Code入门/`。日报这种天天跑的，先按年分一层：`综合/2026/2026-11-13_1058/`。
- 批次文件夹第一层只放人看的文件，机器数据在 `_原始数据/`。
- 试跑和测试都在 `99_系统/测试/`，不和正式内容混在一起。
- 不要在这里放代码。

## 找最近的产出

`99_系统/运行总账.jsonl` 每次运行记一行：时间、Skill、任务、状态、产出路径。直接问 Agent「最近一次日报在哪」即可。

## 不要做的事

- 不要删除 `.dei-workspace`：Skill 靠它确认工作区在线（外接盘没插时会报错，而不是写到别处）。
- 不要把凭证放进这里，凭证在各 Skill 自己的 config.json。
"""


def init(path: str) -> dict:
    target = Path(path).expanduser().resolve()
    created = not target.exists()
    target.mkdir(parents=True, exist_ok=True)
    marker = target / MARKER
    if not marker.exists():
        marker.write_text(json.dumps({"version": VERSION, "created_at": now().isoformat(timespec="seconds")},
                                     ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for name in STAGES.values():
        (target / name).mkdir(exist_ok=True)
    for sub in SYSTEM_DIRS:
        (target / STAGES["system"] / sub).mkdir(exist_ok=True)
    guide = target / "使用说明.md"
    if not guide.exists():
        guide.write_text(GUIDE, encoding="utf-8")
    copied = _copy_list_templates(target / STAGES["lists"])
    SHARED_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if SHARED_CONFIG.is_file():
        try:
            cfg = json.loads(SHARED_CONFIG.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cfg = {}
    cfg["workspace_root"] = str(target)
    SHARED_CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"command": "init", "workspace": str(target), "created": created, "templates": copied,
            "config": str(SHARED_CONFIG)}


def _copy_list_templates(lists: Path) -> list[str]:
    """把本 Skill templates/ 里的「…模板.xlsx」复制到 01_我的清单（去掉「模板」二字），已有的不覆盖。"""
    tpl = Path(__file__).resolve().parents[1] / "templates"
    copied = []
    for f in sorted(tpl.glob("*模板.xlsx")) if tpl.is_dir() else []:
        dst = lists / f.name.replace("模板", "")
        if not dst.exists():
            shutil.copyfile(f, dst)
            copied.append(str(dst))
    return copied


def where() -> dict:
    base = root()
    return {"workspace": str(base), "trial": trial(),
            **{k: str(stage(k, create=False)) for k in STAGES}, "ledger": str(base / STAGES["system"] / LEDGER)}


def main(argv: list[str]) -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    cmd = argv[0] if argv else "where"
    if cmd == "where":
        out = where()
    elif cmd == "init" and len(argv) >= 2:
        out = init(argv[1])
    elif cmd == "log" and len(argv) >= 4:
        log_run(argv[1], argv[2], argv[3], argv[4:])
        out = {"command": "log", "ok": True}
    elif cmd == "latest":
        out = {"command": "latest", "runs": latest(*(argv[1:3]), n=5)}
    elif cmd == "clean":
        out = {"command": "clean", "removed": clean()}
    else:
        print(__doc__)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
