#!/usr/bin/env python3
"""把旧版（各 Skill 各自一个 output_root）的数据迁进统一的 dei 工作区。

    python3 scripts/migrate_workspace.py --skills-dir <Agent 的 skills 目录> --to <新工作区路径>          预览
    python3 scripts/migrate_workspace.py --skills-dir <Agent 的 skills 目录> --to <新工作区路径> --apply  执行
    python3 scripts/migrate_workspace.py --undo <新工作区>/99_系统/迁移记录/<时间>.json                   撤回

旧位置从 <skills-dir>/dei-capture|dei-daily-report|dei-notebook/config.json 的 output_root 读取，
也可以用 --capture / --daily / --notebook 直接指定。

做的事：
1. 逐个文件按新结构计算目标位置（见各 map_* 函数），预览时按目录汇总打印，并写出完整计划。
2. --apply 时移动文件（同一个盘是瞬间改名），改掉文件里引用的旧绝对路径，修正相对路径字段
   （抖音状态库、关键词总表、对外日报的 article），然后初始化工作区（标记文件、使用说明、共享配置），
   清空三个 Skill config.json 里的 output_root，补记运行总账。
3. 每一步都写进 99_系统/迁移记录/<时间>.json；被改写内容的文件先备份到 99_系统/备份/迁移前/<时间>/，
   --undo 按记录全部还原。
目标位置已有同名文件时不覆盖，该文件留在原处并在报告里列出。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "dei-capture" / "scripts"))
import dei_workspace as W  # noqa: E402

LISTS, CAP, DAILY, NB, SYS = (W.STAGES[k] for k in ("lists", "capture", "daily", "notebook", "system"))
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HMS = re.compile(r"^\d{6}$")
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".txt", ".log"}
JUNK = {".DS_Store"}


# ---------------------------------------------------------------- 映射规则（旧相对路径 → 新相对路径）


def hhmm_from_record(path: Path) -> str:
    """关键词巡检旧批次没有时间：从运行记录的「开始」取 HHMM。"""
    try:
        start = json.loads(path.read_text(encoding="utf-8")).get("开始", "")
        return datetime.fromisoformat(start).astimezone(W.BJ).strftime("%H%M")
    except (OSError, ValueError, json.JSONDecodeError):
        return "0000"


def blogger_name(dirname: str) -> str:
    """Get笔记导出目录 <博主名>_<订阅ID> → 博主名。"""
    return re.sub(r"_\d+$", "", dirname)


def map_capture(parts: tuple, old_root: Path):
    p = list(parts)
    if p[0] == "YouTube":
        if len(p) >= 3 and p[1] == "搜索":
            m = re.match(r"^(\d{4}-\d{2}-\d{2})_(\d{4})\d{2}_(.+)$", p[2])
            batch = f"{m.group(1)}_{m.group(2)}_{m.group(3)}" if m else p[2]
            rest = p[3:]
            if rest == ["results.json"]:
                rest = ["_原始数据", "results.json"]
            return [CAP, "YouTube", "搜索", batch, *rest]
        if len(p) == 4 and p[1] == "频道" and p[3] == "videos.json":
            return [CAP, "YouTube", "频道", p[2], "_原始数据", "videos.json"]
        if p[1:] == ["逐字稿", "_log.jsonl"]:
            return [SYS, "日志", "YouTube逐字稿.jsonl"]
        return [CAP, *p]
    if p[0] == "抖音" and len(p) >= 3:
        sub, rest = p[1], p[2:]
        if sub == "Get笔记导出":
            if rest[0] == "merged" and len(rest) >= 3:
                return [CAP, "抖音", "博主", blogger_name(rest[1]), "文案与数据", *rest[2:]]
            if len(rest) >= 2:
                return [CAP, "抖音", "博主", blogger_name(rest[0]), "逐字稿", *rest[1:]]
        if sub == "社媒数据" and len(rest) == 1 and "_作品数据" in rest[0]:
            return [CAP, "抖音", "博主", rest[0].split("_作品数据")[0], "作品数据", rest[0]]
        if sub == "监控":
            head = rest[0]
            if head == "videos.json" or head.startswith("."):
                return [CAP, "抖音", "_原始数据", *rest]
            if head == "transcripts":
                return [CAP, "抖音", "_原始数据", "逐字稿", *rest[1:]]
            if head == "INDEX.md":
                return [CAP, "抖音", "博主", "监控索引.md"]
            if len(rest) >= 2:  # <博主>/<日期>-<标题>.md
                return [CAP, "抖音", "博主", head, "监控更新", *rest[1:]]
        if sub == "监控工作簿":
            head = rest[0]
            if len(rest) == 1 and head.endswith(".xlsx"):
                return [LISTS, head]
            if head == "account_overrides.json":
                return [LISTS, "抖音账号覆盖表.json"]
            if head == "asr_tasks.json":
                return [SYS, "状态", "抖音监控工作簿", head]
            if head == "备份":
                return [SYS, "备份", "抖音监控工作簿", *rest[1:]]
            if head == "运行记录":
                return [SYS, "日志", "抖音监控工作簿", *rest[1:]]
        if sub == "关键词" and len(rest) >= 2:
            head = rest[0]
            if head == "_测试记录" or head.endswith("_试跑"):
                return [SYS, "测试", "抖音关键词巡检", head, *rest[1:]]
            if DATE.match(head):
                record = old_root / "抖音" / "关键词" / head / "运行记录.json"
                batch = f"{head}_{hhmm_from_record(record)}"
                tail = ["_原始数据", "运行记录.json"] if rest[1:] == ["运行记录.json"] else rest[1:]
                return [CAP, "抖音", "关键词", batch, *tail]
    return [CAP, *p]


def map_daily_module(module: str, newname: str, p: list, src_names: dict):
    sub, rest = p[0], p[1:]
    if sub == "topics.json" and not rest:
        return [DAILY, newname, "主题状态.json"]
    if sub == "logs":
        return [SYS, "日志", newname, *rest]
    if sub == "reports" and rest:
        m = re.match(r"^(\d{4})-\d{2}-\d{2}_", rest[0])
        return [DAILY, newname, "报告", *([m.group(1)] if m else []), *rest]
    if sub == "sources" and rest:
        year = [rest[0][:4]] if DATE.match(rest[0]) else []
        return [DAILY, newname, src_names[module], *year, *rest]
    rename = {"transcripts": "逐字稿", "revisions": "修订", "feeds": "线索"}
    return [DAILY, newname, rename.get(sub, sub), *rest]


def map_daily(parts: tuple, old_root: Path):
    p = list(parts)
    if len(p) >= 3 and DATE.match(p[0]) and HMS.match(p[1]):
        rest = p[2:]
        if len(rest) == 1 and rest[0] in ("运行记录.json", "对外日报.json", "头条原文.json"):
            rest = ["_原始数据", rest[0]]
        return [DAILY, "综合", p[0][:4], f"{p[0]}_{p[1][:4]}", *rest]
    if p[0] == "政策与商机" and len(p) >= 2:
        return map_daily_module("policy", "政策与商机", p[1:], {"policy": "原件"})
    if p[0] == "AI情报" and len(p) >= 2:
        return map_daily_module("ai", "AI情报", p[1:], {"ai": "原始采集"})
    if p[0] == "知乎热榜表达空间":
        if len(p) >= 4 and DATE.match(p[1]) and HMS.match(p[2]):
            rest = p[3:]
            if rest[0] == "raw":
                rest = ["_原始数据", *rest[1:]]
            return [DAILY, "知乎热榜", p[1][:4], f"{p[1]}_{p[2][:4]}", *rest]
        return [DAILY, "知乎热榜", *p[1:]]
    if p[0] == "抖音监控":
        return [SYS, "备份", "旧版日报抖音监控", *p[1:]]
    if p[0].startswith("_") and len(p) >= 2:
        return [SYS, "测试", "日报", p[0].lstrip("_"), *p[1:]]
    if p == ["CLAUDE.md"]:
        return ["CLAUDE.md"]
    return [DAILY, *p]


def map_notebook(parts: tuple, old_root: Path):
    p = list(parts)
    if len(p) >= 2:
        base = [SYS, "测试", "知识库", p[0]] if "测试" in p[0] else [NB, p[0]]
        rest = p[1:]
        if rest == ["notebook.json"]:
            rest = ["_原始数据", "notebook.json"]
        return [*base, *rest]
    return [NB, *p]


MAPPERS = {"dei-capture": map_capture, "dei-daily-report": map_daily, "dei-notebook": map_notebook}


# ---------------------------------------------------------------- 计划


def legacy_roots(args) -> dict:
    roots = {}
    for skill, flag in (("dei-capture", args.capture), ("dei-daily-report", args.daily), ("dei-notebook", args.notebook)):
        value = flag
        if not value and args.skills_dir:
            cfg = Path(args.skills_dir).expanduser() / skill / "config.json"
            if cfg.is_file():
                value = json.loads(cfg.read_text(encoding="utf-8")).get("output_root", "")
        if value and Path(value).expanduser().is_dir():
            roots[skill] = Path(value).expanduser().resolve()
    return roots


def build_plan(roots: dict, target: Path) -> list:
    moves = []
    for skill, old_root in roots.items():
        mapper = MAPPERS[skill]
        for f in sorted(old_root.rglob("*")):
            if not f.is_file() or f.name in JUNK:
                continue
            rel = f.relative_to(old_root).parts
            dst = target.joinpath(*mapper(rel, old_root))
            moves.append({"skill": skill, "src": str(f), "dst": str(dst)})
    return moves


def summarize(moves: list, roots: dict, target: Path) -> list:
    """按目录汇总：旧目录 → 新目录（文件数）。"""
    counter = Counter()
    for m in moves:
        src, dst = Path(m["src"]), Path(m["dst"])
        old_root = roots[m["skill"]]
        s = src.parent.relative_to(old_root)
        d = dst.parent.relative_to(target)
        counter[(m["skill"], str(Path(old_root.name) / s), str(d))] += 1
    return [{"skill": k[0], "from": k[1], "to": k[2], "files": n} for k, n in sorted(counter.items())]


# ---------------------------------------------------------------- 执行


def path_map(moves: list, roots: dict) -> list:
    """旧绝对路径 → 新绝对路径：每个文件，加上能唯一确定的目录（目录下所有文件都落到同一个新目录、
    相对位置不变时才映射，否则不映射，避免把路径改错）。按长度倒序，先替换最长的。"""
    pairs = {m["src"]: m["dst"] for m in moves if m.get("done")}
    tops = {str(r) for r in roots.values()}
    dirs: dict = {}
    for src, dst in list(pairs.items()):
        s = Path(src)
        while str(s) not in tops and len(s.parts) > 1:
            s = s.parent
            suffix = str(Path(src).relative_to(s))
            cand = dst[: -len(suffix) - 1] if dst.endswith(os.sep + suffix) else None
            if dirs.get(str(s), cand) != cand:
                dirs[str(s)] = None
            else:
                dirs.setdefault(str(s), cand)
    for k, v in dirs.items():
        if v and k not in pairs:
            pairs[k] = v
    return sorted(pairs.items(), key=lambda kv: -len(kv[0]))


def rewrite_text(files: list, mapping: list, roots: dict, backup: Path, record: dict) -> None:
    needles = [str(r) for r in roots.values()]
    needles += [n.replace(" ", "%20") for n in needles]
    # Markdown 里的 file:// 链接会把空格写成 %20，同样要改
    mapping = mapping + [(o.replace(" ", "%20"), n.replace(" ", "%20")) for o, n in mapping if " " in o]
    mapping.sort(key=lambda kv: -len(kv[0]))
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not any(n in text for n in needles):
            continue
        new = text
        for old, nw in mapping:
            if old in new:
                new = new.replace(old, nw)
        if new != text:
            save_backup(f, backup, record)
            f.write_text(new, encoding="utf-8")
            record["rewritten"].append(str(f))


def save_backup(f: Path, backup: Path, record: dict) -> None:
    dst = backup / f"{len(record['backups']):04d}_{f.name}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(f, dst)
    record["backups"].append({"file": str(f), "backup": str(dst)})


def fix_douyin_store(target: Path, backup: Path, record: dict) -> None:
    store = target / CAP / "抖音" / "_原始数据" / "videos.json"
    if not store.is_file():
        return
    data = json.loads(store.read_text(encoding="utf-8"))
    changed = False
    for v in (data.get("videos") or {}).values():
        tf = v.get("transcript_file") or ""
        if tf.startswith("transcripts/"):
            v["transcript_file"] = "逐字稿/" + tf[len("transcripts/"):]
            changed = True
        mf = v.get("merged_file") or ""
        if mf and "/监控更新/" not in mf and "/" in mf:
            author, name = mf.split("/", 1)
            v["merged_file"] = f"{author}/监控更新/{name}"
            changed = True
    if changed:
        save_backup(store, backup, record)
        store.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        record["rewritten"].append(str(store))


def fix_keyword_links(target: Path, renamed: dict, backup: Path, record: dict) -> None:
    """关键词总表里的逐字稿相对路径：<日期>/逐字稿/… → <日期_HHMM>/逐字稿/…"""
    if not renamed:
        return
    base = target / CAP / "抖音" / "关键词"
    master = base / ".master.json"
    if master.is_file():
        text = master.read_text(encoding="utf-8")
        new = text
        for old, nw in renamed.items():
            new = new.replace(f'"{old}/逐字稿/', f'"{nw}/逐字稿/')
        if new != text:
            save_backup(master, backup, record)
            master.write_text(new, encoding="utf-8")
            record["rewritten"].append(str(master))
    book = base / "关键词总表.xlsx"
    if book.is_file():
        try:
            import openpyxl
        except ImportError:
            record["warnings"].append("没有 openpyxl，关键词总表.xlsx 里的逐字稿链接没改（下次巡检会重建）")
            return
        wb = openpyxl.load_workbook(book)
        hits = 0
        for ws in wb.worksheets:
            for row in ws.iter_rows():
                for c in row:
                    for old, nw in renamed.items():
                        if isinstance(c.value, str) and c.value.startswith(f"{old}/逐字稿/"):
                            c.value = nw + c.value[len(old):]
                            hits += 1
                        if c.hyperlink is not None and (c.hyperlink.target or "").startswith(f"{old}/逐字稿/"):
                            c.hyperlink = nw + c.hyperlink.target[len(old):]
        if hits:
            save_backup(book, backup, record)
            wb.save(book)
            record["rewritten"].append(str(book))


def fix_publish_json(target: Path, backup: Path, record: dict) -> None:
    """对外日报.json 挪进 _原始数据/ 后，article 改成 ../对外日报.md。"""
    for f in (target / DAILY / "综合").glob("*/*/_原始数据/对外日报.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        art = data.get("article") or ""
        if art and not art.startswith("../") and not Path(art).is_absolute():
            save_backup(f, backup, record)
            data["article"] = "../" + art
            f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            record["rewritten"].append(str(f))


def update_configs(skills_dir: Path | None, target: Path, roots: dict, mapping: list, backup: Path, record: dict):
    if not skills_dir:
        return
    for skill in MAPPERS:
        cfg = skills_dir / skill / "config.json"
        if not cfg.is_file():
            continue
        data = json.loads(cfg.read_text(encoding="utf-8"))
        before = json.dumps(data, ensure_ascii=False)
        old_root = str(roots.get(skill, ""))
        data["output_root"] = ""
        if skill == "dei-daily-report":
            if data.get("zhihu_output_dir", "").startswith(old_root or "\0"):
                data["zhihu_output_dir"] = ""
            inp = data.get("douyin_default_input", "")
            for old, nw in mapping:
                if inp == old:
                    data["douyin_default_input"] = nw
                    break
        if skill == "dei-capture":
            dy = data.get("douyin") or {}
            for key in ("workspace", "biji_export_base", "transcript_library"):
                if dy.get(key) and old_root and dy[key].startswith(old_root):
                    dy[key] = ""
        if json.dumps(data, ensure_ascii=False) != before:
            save_backup(cfg, backup, record)
            cfg.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            record["configs"].append(str(cfg))


def backfill_ledger(target: Path) -> int:
    """把已有的批次补进运行总账，dei 才能找到它们。"""
    rows = []
    pat = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})")
    groups = [
        ("dei-daily-report", "综合日报", target / DAILY / "综合", 2),
        ("dei-daily-report", "zhihu", target / DAILY / "知乎热榜", 2),
        ("dei-capture", "youtube-search", target / CAP / "YouTube" / "搜索", 1),
        ("dei-capture", "douyin-keyword-watch", target / CAP / "抖音" / "关键词", 1),
    ]
    for skill, task, base, depth in groups:
        for d in sorted(base.glob("*/" * (depth - 1) + "*")):
            m = pat.match(d.name)
            if d.is_dir() and m:
                t = f"{m.group(1)}T{m.group(2)}:{m.group(3)}:00+08:00"
                rows.append({"time": t, "skill": skill, "task": task, "status": "migrated", "outputs": [str(d)]})
    for d in sorted((target / NB).iterdir()) if (target / NB).is_dir() else []:
        if d.is_dir():
            rows.append({"time": W.now().isoformat(timespec="seconds"), "skill": "dei-notebook", "task": "notebook",
                         "status": "migrated", "outputs": [str(d)]})
    rows.sort(key=lambda r: r["time"])
    ledger = target / SYS / W.LEDGER
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    return len(rows)


def remove_empty(root: Path) -> list:
    left = []
    for d in sorted([p for p in root.rglob("*") if p.is_dir()] + [root], key=lambda p: -len(p.parts)):
        for junk in JUNK:
            j = d / junk
            if j.is_file():
                j.unlink()
        try:
            d.rmdir()
        except OSError:
            if d == root:
                left = [str(p) for p in root.rglob("*") if p.is_file()]
    return left


def apply(moves: list, roots: dict, target: Path, skills_dir: Path | None) -> dict:
    stamp = W.now().strftime("%Y%m%d_%H%M%S")
    backup = target / SYS / "备份" / "迁移前" / stamp
    record = {"time": W.now().isoformat(timespec="seconds"), "target": str(target),
              "roots": {k: str(v) for k, v in roots.items()}, "moves": moves, "skipped": [], "rewritten": [],
              "backups": [], "configs": [], "warnings": [], "created_workspace": not (target / W.MARKER).exists()}
    renamed_kw = {}
    for m in moves:
        src, dst = Path(m["src"]), Path(m["dst"])
        if dst.exists():
            record["skipped"].append(m)
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        m["done"] = True
        parts = dst.relative_to(target).parts
        if parts[:3] == (CAP, "抖音", "关键词") and len(parts) > 4:
            old_day = Path(m["src"]).relative_to(roots["dei-capture"]).parts[2]
            if old_day != parts[3]:
                renamed_kw[old_day] = parts[3]
    mapping = path_map(moves, roots)
    text_files = [Path(m["dst"]) for m in moves if m.get("done") and Path(m["dst"]).suffix in TEXT_SUFFIXES]
    rewrite_text(text_files, mapping, roots, backup, record)
    fix_douyin_store(target, backup, record)
    fix_keyword_links(target, renamed_kw, backup, record)
    fix_publish_json(target, backup, record)
    os.environ.pop("DEI_WORKSPACE", None)
    record["init"] = W.init(str(target))
    update_configs(skills_dir, target, roots, mapping, backup, record)
    record["ledger_rows"] = backfill_ledger(target)
    record["left_behind"] = {k: remove_empty(v) for k, v in roots.items()}
    log = target / SYS / "迁移记录" / f"{stamp}.json"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    record["record_file"] = str(log)
    return record


def undo(record_file: Path) -> dict:
    rec = json.loads(record_file.read_text(encoding="utf-8"))
    restored = 0
    for b in reversed(rec["backups"]):
        if Path(b["backup"]).is_file():
            shutil.copy2(b["backup"], b["file"])
    for m in reversed(rec["moves"]):
        if m.get("done") and Path(m["dst"]).exists():
            Path(m["src"]).parent.mkdir(parents=True, exist_ok=True)
            shutil.move(m["dst"], m["src"])
            restored += 1
    return {"command": "undo", "restored_files": restored,
            "note": "工作区的空文件夹、使用说明、运行总账和 ~/.deiskill/config.json 没删，确认后可手动删除"}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skills-dir", help="Agent 的 skills 目录，用来读取旧 output_root 并清空")
    ap.add_argument("--capture"), ap.add_argument("--daily"), ap.add_argument("--notebook")
    ap.add_argument("--to", help="新工作区路径")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--plan-out", help="完整计划写到这个 JSON 文件")
    ap.add_argument("--undo")
    a = ap.parse_args()
    if a.undo:
        print(json.dumps(undo(Path(a.undo).expanduser()), ensure_ascii=False, indent=2))
        return 0
    if not a.to:
        ap.error("需要 --to <新工作区路径>")
    target = Path(a.to).expanduser().resolve()
    roots = legacy_roots(a)
    if not roots:
        ap.error("没找到旧数据位置：用 --skills-dir 指向 Agent 的 skills 目录，或用 --capture/--daily/--notebook 指定")
    for r in roots.values():
        if target == r or r in target.parents:
            ap.error(f"新工作区不能放在旧目录里面：{r}")
    moves = build_plan(roots, target)
    conflicts = [m for m in moves if Path(m["dst"]).exists()]
    dup = [d for d, n in Counter(m["dst"] for m in moves).items() if n > 1]
    if a.plan_out:
        Path(a.plan_out).write_text(json.dumps(moves, ensure_ascii=False, indent=2), encoding="utf-8")
    if not a.apply:
        print(json.dumps({"command": "preview", "target": str(target), "roots": {k: str(v) for k, v in roots.items()},
                          "files": len(moves), "conflicts": len(conflicts), "duplicate_targets": dup,
                          "summary": summarize(moves, roots, target)}, ensure_ascii=False, indent=2))
        return 0
    if dup:
        print(json.dumps({"error": "有多个文件映射到同一个目标，先修映射", "duplicate_targets": dup}, ensure_ascii=False))
        return 1
    rec = apply(moves, roots, target, Path(a.skills_dir).expanduser() if a.skills_dir else None)
    print(json.dumps({"command": "apply", "record": rec["record_file"], "moved": sum(1 for m in moves if m.get("done")),
                      "skipped": len(rec["skipped"]), "rewritten": len(rec["rewritten"]), "configs": rec["configs"],
                      "ledger_rows": rec["ledger_rows"], "warnings": rec["warnings"],
                      "left_behind": {k: len(v) for k, v in rec["left_behind"].items()}}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
