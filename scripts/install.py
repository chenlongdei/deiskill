#!/usr/bin/env python3
"""安装 deiskill：自有 Skill 从本仓库复制，上游 Skill 安装时从上游拉取。

覆盖安装时：
- 旧目录整体备份到 ~/.deiskill/backups/<时间>/，不留在 skills 目录里（否则会被识别成重名 Skill）；
- 运行数据与本机配置（data/、config.json 等）从旧目录恢复到新目录；
- kind=manual 的上游依赖无法自动获取，从旧目录保留本机已有副本。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CACHE = Path.home() / ".deiskill" / "cache"
BACKUPS = Path.home() / ".deiskill" / "backups"
# 常见 Agent 的用户级 skills 目录。只用于检测本机已有哪些，不默认任何一个。
KNOWN_AGENT_DIRS = {
    "Claude Code": Path.home() / ".claude" / "skills",
    "Codex": Path.home() / ".codex" / "skills",
    "WorkBuddy": Path.home() / ".workbuddy" / "skills",
    "通用 Agents": Path.home() / ".agents" / "skills",
}


def resolve_targets(explicit: list[Path] | None) -> list[Path]:
    """用户指定的目录优先；否则检测本机已有的 Agent skills 目录，多个时询问。"""
    if explicit:
        return explicit
    found = [(name, path) for name, path in KNOWN_AGENT_DIRS.items() if path.parent.is_dir()]
    if len(found) == 1:
        say(f"检测到 {found[0][0]}，安装到 {found[0][1]}")
        return [found[0][1]]
    if not found:
        sys.exit("没有检测到常见 Agent 的目录。请用 --target 指定你的 Agent 的 skills 目录。")
    say("检测到多个 Agent：")
    for i, (name, path) in enumerate(found, 1):
        say(f"  {i}. {name}  {path}")
    if not sys.stdin.isatty():
        sys.exit("请用 --target 指定要安装到哪个（可重复指定多个）。")
    answer = input("装到哪些？输入编号，多个用空格分隔，回车 = 全部：").split()
    if not answer:
        return [path for _, path in found]
    try:
        return [found[int(n) - 1][1] for n in answer]
    except (ValueError, IndexError):
        sys.exit("编号无效。")

# 在任意层级出现都视为本机运行状态，覆盖安装时从旧目录恢复。
PRESERVE_DIRS = {"data", "node_modules"}
PRESERVE_FILES = {"config.json", "agent.conf", ".aihot-actor-id", "account_overrides.json"}
COPY_IGNORE = shutil.ignore_patterns(".git", ".DS_Store", "__pycache__", "*.pyc")


def load(name: str) -> dict:
    return json.loads((REPO / name).read_text(encoding="utf-8"))


def say(message: str) -> None:
    print(message, flush=True)


def fetch_repo(url: str) -> Path:
    """浅克隆或更新上游仓库到缓存目录，返回本地路径。"""
    slug = url.rstrip("/").removesuffix(".git").split("github.com/")[-1].replace("/", "__")
    local = CACHE / slug
    if (local / ".git").is_dir():
        result = subprocess.run(["git", "-C", str(local), "pull", "--ff-only", "-q"], capture_output=True, text=True)
        if result.returncode != 0:
            say(f"  ! 更新 {url} 失败，使用缓存版本：{result.stderr.strip()}")
    else:
        local.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", "-q", url, str(local)], check=True)
    return local


def fetch_archive(url: str) -> Path:
    """下载并解压上游 zip 到缓存目录，返回解压根目录。每次安装都重新下载，保证是最新发布。"""
    slug = url.split("://", 1)[-1].replace("/", "__")
    root = CACHE / "archives" / slug
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    archive = root / "download.zip"
    with urllib.request.urlopen(url, timeout=60) as response, archive.open("wb") as out:
        shutil.copyfileobj(response, out)
    extracted = root / "extracted"
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.namelist():
            target = (extracted / member).resolve()
            if not str(target).startswith(str(extracted.resolve())):
                raise ValueError(f"压缩包含不安全路径：{member}")
        bundle.extractall(extracted)
    return extracted


def restore_state(backup: Path, destination: Path, extra: list[str]) -> list[str]:
    """把旧目录里的运行数据、本机配置和 manual 依赖恢复到新目录，不覆盖新文件。"""
    restored: list[str] = []
    for path in sorted(backup.rglob("*")):
        relative = path.relative_to(backup)
        if any(part in PRESERVE_DIRS for part in relative.parts[:-1]):
            continue  # 已随上层目录整体恢复
        keep = (path.is_dir() and path.name in PRESERVE_DIRS) or (path.is_file() and path.name in PRESERVE_FILES)
        if not keep:
            continue
        target = destination / relative
        if path.is_dir():
            if target.exists():
                continue
            shutil.copytree(path, target, symlinks=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)  # 本机配置优先于仓库里的示例默认值
        restored.append(str(relative))
    for relative in extra:
        source, target = backup / relative, destination / relative
        if source.is_dir() and not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source, target, symlinks=True)
            restored.append(relative)
    return restored


def install_vendor(item: dict, destination: Path) -> None:
    origin = fetch_archive(item["archive"]) if "archive" in item else fetch_repo(item["repo"])
    source = origin / item.get("path", ".")
    target = destination / item["install_into"]
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target, ignore=COPY_IGNORE)
    for old, new in item.get("rename", {}).items():
        if (target / old).exists():
            (target / old).rename(target / new)
    command = item.get("post_install")
    if command:
        if shutil.which(command[0]) is None:
            say(f"  ! 未找到 {command[0]}，跳过 {item['name']} 的依赖安装：{' '.join(command)}")
        else:
            result = subprocess.run(command, cwd=target, capture_output=True, text=True)
            if result.returncode != 0:
                say(f"  ! {item['name']} 依赖安装失败：{result.stderr.strip()[-300:]}")
    say(f"  + 上游依赖 {item['name']} → {item['install_into']}")


def place(name: str, source: Path, target_dir: Path, stamp: str, vendors: list[dict], manuals: list[dict],
          local_only: list[dict] | None = None) -> None:
    destination = target_dir / name
    backup = None
    if destination.exists() or destination.is_symlink():
        backup = BACKUPS / stamp / target_dir.name / name
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(destination), str(backup))
    shutil.copytree(source, destination, ignore=COPY_IGNORE)
    for item in vendors:
        try:
            install_vendor(item, destination)
        except (subprocess.CalledProcessError, OSError, ValueError, zipfile.BadZipFile) as exc:
            say(f"  ! 拉取 {item['name']} 失败（{exc}），该模块暂不可用")
    if backup:
        keep = [m["install_into"] for m in manuals + (local_only or [])]
        restored = restore_state(backup, destination, keep)
        say(f"已安装 {name}（旧版本备份在 {backup}）")
        if restored:
            say("  保留本机状态：" + "、".join(restored))
    else:
        say(f"已安装 {name}")
    for item in manuals:
        if not (destination / item["install_into"]).exists():
            say(f"  ! 缺少 {item['name']}：{item['instructions']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="安装 deiskill")
    parser.add_argument("names", nargs="*", help="只安装这些 Skill（自有或上游）")
    parser.add_argument("--list", action="store_true", help="列出全部 Skill")
    parser.add_argument("--all", action="store_true", help="安装 default 与 optional 级别")
    parser.add_argument("--target", action="append", type=Path, help="安装到这个 skills 目录，可重复；不指定时检测本机已有的 Agent")
    parser.add_argument("--no-external", action="store_true", help="不安装上游 Skill")
    args = parser.parse_args()

    catalog, external = load("catalog.json"), load("external.json")["externals"]
    local = {item["name"]: item for item in catalog["skills"]}
    upstream = {item["name"]: item for item in external if item["kind"] == "skill"}

    if args.list:
        say(f"{'SKILL':28} {'LAYER':8} {'LEVEL':9} 用途")
        for item in catalog["skills"]:
            say(f"{item['name']:28} {item['layer']:8} {item['install']:9} {item['summary']}")
        for item in upstream.values():
            say(f"{item['name']:28} {item['layer']:8} {'upstream':9} {item['summary']}")
        return 0

    if args.names:
        unknown = [n for n in args.names if n not in local and n not in upstream]
        if unknown:
            say("未知 Skill：" + "、".join(unknown))
            return 2
        selected = args.names
    else:
        levels = {"default", "optional"} if args.all else {"default"}
        selected = [n for n, item in local.items() if item["install"] in levels]
        if not args.no_external:
            selected += list(upstream)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for target_dir in resolve_targets(args.target):
        target_dir = target_dir.expanduser().resolve()
        target_dir.mkdir(parents=True, exist_ok=True)
        say(f"== 安装到 {target_dir}")
        for name in selected:
            if name in local:
                vendors = [e for e in external if e["kind"] == "vendor" and e["owner"] == name]
                manuals = [e for e in external if e["kind"] == "manual" and e["owner"] == name]
                local_only = [{"install_into": path, "name": path, "instructions": ""} for path in local[name].get("local_only", [])]
                place(name, REPO / "skills" / name, target_dir, stamp, vendors, manuals, local_only)
            else:
                item = upstream[name]
                try:
                    source = fetch_repo(item["repo"]) / item["path"]
                except subprocess.CalledProcessError as exc:
                    say(f"! 拉取上游 {name} 失败：{exc}")
                    continue
                place(name, source, target_dir, stamp, [], [])
    say("完成。重启或刷新 Agent，让它重新发现 Skills。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
