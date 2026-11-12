#!/usr/bin/env python3
"""dei-notebook：在 NotebookLM 上建知识库、批量导入资料、提问并存档。

只做 notebooklm-py CLI 做不顺的部分：展开文件夹、去重导入、等待就绪、失败重试一次、
问答和生成物存档到用户确认的保存位置。其余操作直接用 CLI（见 references/notebooklm-cli.md）。

    python3 nb.py doctor
    python3 nb.py import --new "主题 2026-11" 文件或文件夹... YouTube链接... [--from-list urls.txt]
    python3 nb.py import --notebook <ID或名称> ...
    python3 nb.py ask --notebook <ID> "问题" [--prompt-file q.md] [--follow-up]
    python3 nb.py make --notebook <ID> audio|mind-map|report|... [-- 透传给 generate 的参数]
    python3 nb.py status --notebook <ID>

所有命令最后在 stdout 打印一行 JSON 摘要。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG = SKILL_ROOT / "config.json"

# notebooklm-py 0.8.x 认可的本地上传扩展名（_types/sources.py::_UPLOAD_FILE_EXTENSIONS）
FILE_EXTS = {".csv", ".doc", ".docx", ".epub", ".md", ".markdown", ".odt", ".pdf", ".pptx", ".rtf", ".tsv", ".txt"}
YOUTUBE_RE = re.compile(r"^https?://(www\.|m\.)?(youtube\.com/(watch\?|shorts/|live/)|youtu\.be/)")
AUTH_HINTS = ("not authenticated", "CSRF token not found", "storage_state", "Authentication", "login", "401")


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.is_file() else {}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def emit(summary: dict) -> None:
    print(json.dumps(summary, ensure_ascii=False))


def data_root() -> Path:
    override = os.environ.get("DEI_NOTEBOOK_DATA_DIR")
    if override:
        return Path(override).expanduser()
    root = load_config().get("output_root", "")
    if not root:
        sys.exit(f"未配置知识库存档位置：请先按 SKILL.md「首次配置」询问用户，把 output_root 写入 {CONFIG}")
    path = Path(root).expanduser()
    if not path.is_dir():
        sys.exit(f"存档位置不存在：{path}。请用户确认是新建、改路径，还是本次跳过（不静默新建）。")
    return path


def slug(text: str, limit: int = 40) -> str:
    text = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", text).strip()
    return re.sub(r"\s+", "-", text)[:limit].rstrip("-.") or "untitled"


# ---------------------------------------------------------------- CLI


class NbError(RuntimeError):
    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code
        self.auth = any(h.lower() in message.lower() for h in AUTH_HINTS)


def nb_cmd() -> list[str]:
    c = load_config()
    cmd = shlex.split(c.get("notebooklm_cmd") or "notebooklm")
    if c.get("profile"):
        cmd += ["--profile", c["profile"]]
    return cmd


def nb(args: list[str], timeout: int = 300, want_json: bool = True, cwd: Path | None = None):
    cmd = nb_cmd() + args + (["--json"] if want_json else [])
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd)
    except FileNotFoundError:
        raise NbError("找不到 notebooklm 命令：先安装 notebooklm-py，或在 config.notebooklm_cmd 指定")
    except subprocess.TimeoutExpired:
        raise NbError(f"notebooklm {' '.join(args[:2])} 超时（{timeout}s）")
    out = proc.stdout.strip()
    if proc.returncode != 0:
        detail = out or proc.stderr.strip()
        try:
            err = json.loads(detail)
            detail = err.get("message") or err.get("error") or detail
        except (json.JSONDecodeError, AttributeError):
            pass
        raise NbError(str(detail)[-600:] or f"退出码 {proc.returncode}", proc.returncode)
    if not want_json:
        return out
    try:
        return json.loads(out) if out else {}
    except json.JSONDecodeError:
        # 个别版本在 JSON 前打印提示行，取最后一个 JSON 对象
        start = out.find("{")
        return json.loads(out[start:]) if start >= 0 else {"text": out}


def auth_stop(exc: NbError) -> int:
    emit({"status": "auth_required", "error": str(exc),
          "fix": "请用户在终端运行 `notebooklm login`（浏览器登录 Google，等终端提示保存成功再关窗口），"
                 "或 `notebooklm auth refresh --verify`；详见 references/notebooklm-cli.md「登录」"})
    return 3


# ---------------------------------------------------------------- 本地记录


def record_path(nb_id: str, title: str) -> Path:
    root = data_root()
    for p in root.glob("*/notebook.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("id") == nb_id:
                return p
        except (json.JSONDecodeError, OSError):
            continue
    d = root / slug(title)
    if d.exists():
        d = root / f"{slug(title)}-{nb_id[:6]}"
    d.mkdir(parents=True, exist_ok=True)
    return d / "notebook.json"


def load_record(path: Path, nb_id: str, title: str) -> dict:
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"id": nb_id, "title": title, "created_at": now(), "sources": {}, "asks": 0}


def save_record(path: Path, rec: dict) -> None:
    rec["updated_at"] = now()
    path.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_notebook(ref: str) -> tuple[str, str]:
    data = nb(["list"], timeout=120)
    books = data.get("notebooks") or []
    exact = [b for b in books if b.get("id") == ref or b.get("title") == ref]
    partial = [b for b in books if str(b.get("id", "")).startswith(ref)]
    hits = exact or partial
    if len(hits) != 1:
        names = ", ".join(f"{b.get('title')}({str(b.get('id'))[:8]})" for b in hits[:5])
        raise SystemExit(f"找不到唯一的笔记本「{ref}」" + (f"：匹配到 {names}" if hits else ""))
    return hits[0]["id"], hits[0].get("title") or ref


# ---------------------------------------------------------------- 资料展开


def frontmatter_title(path: Path) -> str | None:
    if path.suffix.lower() not in {".md", ".markdown"}:
        return None
    head = path.read_text(encoding="utf-8", errors="ignore")[:3000]
    m = re.match(r"\A---\n(.*?)\n---\n", head, re.DOTALL)
    if not m:
        return None
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip().strip("\"'")
    if not fields.get("title"):
        return None
    return f"{fields['title']}-{fields['channel']}" if fields.get("channel") else fields["title"]


def expand(items: list[str]) -> tuple[list[dict], list[dict]]:
    sources, skipped = [], []
    for item in items:
        item = item.strip()
        if not item or item.startswith("#"):
            continue
        if YOUTUBE_RE.match(item):
            sources.append({"kind": "youtube", "content": item, "key": item, "title": None})
            continue
        if re.match(r"^https?://", item):
            skipped.append({"input": item, "reason": "网页链接暂不支持（当前只导入本地文件和 YouTube）"})
            continue
        path = Path(item).expanduser()
        if not path.exists():
            skipped.append({"input": item, "reason": "文件不存在"})
            continue
        files = sorted(p for p in path.rglob("*") if p.is_file()) if path.is_dir() else [path]
        for f in files:
            if f.name.startswith(("." , "_")):
                continue
            if f.suffix.lower() not in FILE_EXTS:
                if not path.is_dir():
                    skipped.append({"input": str(f), "reason": f"NotebookLM 不接受 {f.suffix or '无扩展名'} 文件；"
                                    "音视频请先转成逐字稿，其他格式先转成 PDF 或 txt"})
                continue
            if f.is_symlink():
                skipped.append({"input": str(f), "reason": "符号链接不上传（防止误传链接指向的文件）"})
                continue
            sources.append({"kind": "file", "content": str(f.resolve()), "key": str(f.resolve()),
                            "title": frontmatter_title(f) or f.stem})
    return sources, skipped


# ---------------------------------------------------------------- 命令


def cmd_doctor(a) -> int:
    checks = []
    try:
        ver = subprocess.run(nb_cmd() + ["--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30).stdout.strip()
        checks.append({"name": "notebooklm-py", "ok": bool(ver), "detail": ver or "无输出"})
    except FileNotFoundError:
        checks.append({"name": "notebooklm-py", "ok": False, "detail": "未安装"})
    try:
        books = nb(["list"], timeout=120).get("notebooks") or []
        checks.append({"name": "登录", "ok": True, "detail": f"正常，共 {len(books)} 个笔记本"})
    except NbError as exc:
        checks.append({"name": "登录", "ok": False, "detail": str(exc)[:300], "auth": exc.auth})
    try:
        checks.append({"name": "output_root", "ok": True, "detail": str(data_root())})
    except SystemExit as exc:
        checks.append({"name": "output_root", "ok": False, "detail": str(exc)})
    for c in checks:
        print(f"{'✅' if c['ok'] else '⚠️ '} {c['name']}: {c['detail']}", file=sys.stderr)
    emit({"command": "doctor", "checks": checks})
    return 0 if all(c["ok"] for c in checks) else 1


def existing_sources(nb_id: str) -> list[dict]:
    return nb(["source", "list", "-n", nb_id], timeout=120).get("sources") or []


def add_one(nb_id: str, src: dict) -> dict:
    args = ["source", "add", src["content"], "-n", nb_id, "--type", src["kind"], "--timeout", "180"]
    if src["kind"] == "file" and src.get("title"):
        args += ["--title", src["title"][:100]]
    data = nb(args, timeout=300)
    return data.get("source") or data


def wait_one(nb_id: str, source_id: str, timeout: int) -> str:
    try:
        data = nb(["source", "wait", source_id, "-n", nb_id, "--timeout", str(timeout)], timeout=timeout + 60)
        return (data.get("status") or "ready").lower()
    except NbError as exc:
        if exc.auth:
            raise
        return "timeout" if exc.code == 2 else "error"


def cmd_import(a) -> int:
    items = list(a.items)
    if a.from_list:
        items += Path(a.from_list).expanduser().read_text(encoding="utf-8").splitlines()
    sources, skipped = expand(items)
    if not sources:
        emit({"command": "import", "status": "nothing", "skipped": skipped})
        return 2
    try:
        if a.new:
            data = nb(["create", a.new], timeout=120)
            book = data.get("notebook") or data
            nb_id, title = book["id"], book.get("title") or a.new
            created_here = True
        else:
            nb_id, title = resolve_notebook(a.notebook)
            created_here = False
        current = existing_sources(nb_id)
    except NbError as exc:
        return auth_stop(exc) if exc.auth else (emit({"command": "import", "status": "failed", "error": str(exc)}) or 1)

    rpath = record_path(nb_id, title)
    rec = load_record(rpath, nb_id, title)
    if created_here:
        rec["owned"] = True  # 本 Skill 新建的笔记本：主问题默认开新对话（服务器端对话历史可删，本地有存档）
    known_titles = {s.get("title") for s in current}
    known_urls = {s.get("url") for s in current if s.get("url")}
    limit = int(load_config().get("source_limit") or 50)
    room = limit - len(current)
    results = []
    for src in sources:
        prev = rec["sources"].get(src["key"])
        already = (prev and prev.get("status") == "ready") or src["content"] in known_urls or (
            src["kind"] == "file" and src["title"] in known_titles)
        if already:
            results.append({"input": src["key"], "status": "exists"})
            continue
        if room <= 0:
            results.append({"input": src["key"], "status": "skipped", "error": f"已到来源上限 {limit}（可在 config.source_limit 按账号档位调整）"})
            continue
        status, err, sid = "error", "", None
        for attempt in (1, 2):
            try:
                added = add_one(nb_id, src)
                sid = added.get("id")
                status = wait_one(nb_id, sid, a.wait) if sid else "unknown"
            except NbError as exc:
                if exc.auth:
                    save_record(rpath, rec)
                    return auth_stop(exc)
                status, err = "error", str(exc)[:300]
            if status == "ready":
                break
            if sid and status == "error":
                try:
                    nb(["source", "delete", sid, "-n", nb_id, "-y"], timeout=120, want_json=False)
                except NbError:
                    pass
                sid = None
            if status == "timeout":
                break  # 处理中的来源不重复添加，下次 status 再查
        room -= 1 if sid else 0
        rec["sources"][src["key"]] = {"kind": src["kind"], "title": src.get("title"), "source_id": sid,
                                      "status": status, "error": err, "at": now()}
        results.append({"input": src["key"], "status": status, "source_id": sid, "error": err})
        print(f"[{status}] {src.get('title') or src['key']}", file=sys.stderr)
    save_record(rpath, rec)
    ok = [r for r in results if r["status"] in ("ready", "exists")]
    emit({"command": "import", "notebook_id": nb_id, "title": title, "record": str(rpath),
          "ok": len(ok), "pending": sum(r["status"] == "timeout" for r in results),
          "failed": [r for r in results if r["status"] not in ("ready", "exists", "timeout")], "skipped": skipped})
    return 0 if ok else 2


def split_batch(text: str) -> list[str]:
    """问题清单：用单独一行 --- 分隔；# 开头的首行当作说明，不发送。"""
    blocks = re.split(r"(?m)^\s*---\s*$", text)
    out = []
    for b in blocks:
        lines = [ln for ln in b.strip().splitlines() if not ln.startswith("<!--")]
        body = "\n".join(lines).strip()
        if body and not (len(lines) == 1 and lines[0].startswith("# ")):
            out.append(body)
    return out


CITE_RE = re.compile(r"[ \t]?\[\d+(?:\s*[-–,，]\s*\d+)*\]")


def strip_citations(text: str) -> str:
    """去掉回答里的 [1]、[2, 3]、[18-20] 这类引用编号（不动 Markdown 链接和代码块）。"""
    out, in_code = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code = not in_code
        out.append(line if in_code else CITE_RE.sub("", line))
    return "\n".join(out)


def ask_one(nb_id: str, title: str, rpath: Path, rec: dict, question: str,
            follow_up: bool, subdir: str, timeout: int, fresh: bool = False) -> dict:
    # notebooklm ask 默认接着服务器上的上一个对话问；接续时常不带引用。fresh 用 --new 开新对话
    args = ["ask", question, "-n", nb_id, "--timeout", str(timeout)]
    if follow_up and rec.get("conversation_id"):
        args += ["-c", rec["conversation_id"]]
    elif fresh:
        args += ["--new", "-y"]
    data = nb(args, timeout=timeout + 60)
    answer = data.get("answer") or ""
    refs = data.get("references") or []
    rec["asks"] = int(rec.get("asks", 0)) + 1
    rec["conversation_id"] = data.get("conversation_id") or rec.get("conversation_id")
    qdir = rpath.parent / (subdir or "问答")
    qdir.mkdir(parents=True, exist_ok=True)
    first_line = re.sub(r"^#+\s*", "", question.strip().splitlines()[0])
    path = qdir / f"{rec['asks']:03d}_{slug(first_line, 30)}.md"
    # 存档只给人看：问题 + 回答。[n] 编号和引用列表对读者没用，不写；出处靠提问时要求写明视频或文档名
    lines = [f"# {first_line}", "", f"> {title} · {now()[:16].replace('T', ' ')}", ""]
    if len(question.strip().splitlines()) > 1:
        lines += ["## 问题", "", question.strip(), ""]
    lines += ["## 回答", "", strip_citations(answer).strip() or "（NotebookLM 没有返回内容）", ""]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    save_record(rpath, rec)
    # 接续追问时 NotebookLM 常只凭对话上下文作答、不带引用；标出来由 Agent 决定是否单独重问
    return {"file": str(path), "references": len(refs), "answer_chars": len(answer), "empty": not answer.strip(), "follow_up": bool(follow_up),
            "uncited": bool(answer.strip()) and not refs}


def cmd_ask(a) -> int:
    if a.batch:
        questions = split_batch(Path(a.batch).expanduser().read_text(encoding="utf-8"))
    else:
        q = Path(a.prompt_file).expanduser().read_text(encoding="utf-8") if a.prompt_file else (a.question or "")
        questions = [q] if q.strip() else []
    if not questions:
        sys.exit("没有问题内容")
    results = []
    try:
        nb_id, title = resolve_notebook(a.notebook)
        rpath = record_path(nb_id, title)
        rec = load_record(rpath, nb_id, title)
        fresh_default = a.fresh or (bool(rec.get("owned")) and not a.keep_history)
        for i, q in enumerate(questions):
            follow = a.follow_up or (a.chain and i > 0)
            fresh = fresh_default and not follow
            print(f"[{i + 1}/{len(questions)}] {q.strip().splitlines()[0][:60]}", file=sys.stderr)
            try:
                results.append(ask_one(nb_id, title, rpath, rec, q, follow, a.dir, a.timeout, fresh))
            except NbError as exc:
                if exc.auth:
                    raise
                err = {"question": q.strip().splitlines()[0][:80], "error": str(exc)[:300]}
                if "exceeded" in str(exc) and "bytes" in str(exc):
                    err["hint"] = ("回答流超过 notebooklm-py 的缓冲上限（来源多且要求长回答时出现）："
                                   "把问题拆成更小的几问，或用 -s 只问相关来源")
                results.append(err)
                if sum("error" in r for r in results) >= 3:
                    break  # 连续出错就停，不硬撑
    except NbError as exc:
        return auth_stop(exc) if exc.auth else (emit({"command": "ask", "status": "failed", "error": str(exc)}) or 1)
    ok = [r for r in results if "file" in r and not r["empty"]]
    uncited = [r["file"] for r in results if r.get("uncited")]
    summary = {"command": "ask", "notebook_id": nb_id, "asked": len(results), "ok": len(ok),
               "dir": str(rpath.parent / (a.dir or "问答")), "results": results}
    if uncited:
        summary["uncited"] = uncited
        summary["hint"] = ("这些回答没有引用（多见于接续对话）。需要出处时用 --fresh 开新对话重问"
                           "（会删除该笔记本服务器端的对话历史；不是本 Skill 新建的笔记本要先问用户）；列来源清单这类问题可以接受无引用")
    emit(summary)
    return 0 if ok else 2


def cmd_make(a) -> int:
    """提交生成 → 等待完成 → 按 ID 下载。--artifact 时跳过提交，接着等待/下载已有的生成任务。"""
    try:
        nb_id, title = resolve_notebook(a.notebook)
        rpath = record_path(nb_id, title)
        outdir = rpath.parent / "产物"
        art_id = a.artifact
        if not art_id:
            submitted = nb(["generate", a.kind, "-n", nb_id] + a.extra, timeout=300)
            art_id = submitted.get("task_id") or submitted.get("artifact_id") or (submitted.get("artifact") or {}).get("id")
            print(f"已提交 {a.kind}：{art_id or submitted}", file=sys.stderr)
        if art_id and a.kind != "mind-map":
            print(f"等待生成完成（最多 {a.timeout}s）……", file=sys.stderr)
            try:
                waited = nb(["artifact", "wait", art_id, "-n", nb_id, "--timeout", str(a.timeout), "--interval", "10"],
                            timeout=a.timeout + 120)
            except NbError as exc:
                if exc.auth:
                    raise
                emit({"command": "make", "status": "timeout" if exc.code == 2 else "failed", "artifact_id": art_id,
                      "error": str(exc)[:300],
                      "resume": f"python3 nb.py make -n {nb_id} {a.kind} --artifact {art_id}"})
                return 2
            status = str((waited.get("artifact") or waited).get("status") or "").lower()
            if status and status not in ("completed", "ready"):
                emit({"command": "make", "status": status, "artifact_id": art_id, "detail": waited})
                return 2
        outdir.mkdir(exist_ok=True)
        args = ["download", a.kind, "-n", nb_id, "--no-clobber"] + (["-a", art_id] if art_id and a.kind != "mind-map" else ["--latest"])
        data = nb(args, timeout=900, cwd=outdir)
    except NbError as exc:
        return auth_stop(exc) if exc.auth else (emit({"command": "make", "status": "failed", "error": str(exc)}) or 1)
    outline = None
    saved = Path(str((data or {}).get("output_path") or ""))
    if a.kind == "mind-map" and saved.suffix == ".json" and saved.is_file():
        outline = saved.with_suffix(".md")
        outline.write_text(mindmap_markdown(json.loads(saved.read_text(encoding="utf-8"))), encoding="utf-8")
    emit({"command": "make", "status": "completed", "notebook_id": nb_id, "kind": a.kind, "artifact_id": art_id,
          "file": str(saved) if str(saved) not in ("", ".") else None, "outline": str(outline) if outline else None})
    return 0


def mindmap_markdown(node: dict) -> str:
    """把 NotebookLM 导图 JSON（name/children 树）转成 Markdown 大纲，便于阅读和导入其他工具。"""
    lines = [f"# {node.get('name', '思维导图')}", ""]

    def walk(n: dict, depth: int) -> None:
        for child in n.get("children") or []:
            lines.append(f"{'  ' * depth}- {child.get('name', '')}")
            walk(child, depth + 1)

    walk(node, 0)
    return "\n".join(lines) + "\n"


def cmd_status(a) -> int:
    try:
        nb_id, title = resolve_notebook(a.notebook)
        current = existing_sources(nb_id)
    except NbError as exc:
        return auth_stop(exc) if exc.auth else (emit({"command": "status", "status": "failed", "error": str(exc)}) or 1)
    rpath = record_path(nb_id, title)
    rec = load_record(rpath, nb_id, title)
    by_id = {s.get("id"): s for s in current}
    for v in rec["sources"].values():
        if v.get("source_id") in by_id:
            v["status"] = (by_id[v["source_id"]].get("status") or v.get("status") or "").lower()
    save_record(rpath, rec)
    counts = {}
    for s in current:
        st = (s.get("status") or "unknown").lower()
        counts[st] = counts.get(st, 0) + 1
    emit({"command": "status", "notebook_id": nb_id, "title": title, "record": str(rpath),
          "sources": len(current), "by_status": counts,
          "errors": [s.get("title") for s in current if (s.get("status") or "").lower() == "error"]})
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="dei-notebook：NotebookLM 知识库")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor")
    i = sub.add_parser("import")
    g = i.add_mutually_exclusive_group(required=True)
    g.add_argument("--new", metavar="标题", help="新建笔记本")
    g.add_argument("--notebook", "-n", help="已有笔记本的 ID（可前缀）或完整名称")
    i.add_argument("items", nargs="*", help="文件、文件夹或 YouTube 链接")
    i.add_argument("--from-list", help="每行一个文件路径或 YouTube 链接")
    i.add_argument("--wait", type=int, default=600, help="每个来源最多等待就绪的秒数")
    q = sub.add_parser("ask")
    q.add_argument("--notebook", "-n", required=True)
    q.add_argument("question", nargs="?")
    q.add_argument("--prompt-file")
    q.add_argument("--batch", help="问题清单文件：每个问题之间用单独一行 --- 分隔，按顺序提问")
    q.add_argument("--chain", action="store_true", help="批量时第 2 个问题起接着前一个追问；接续追问常不带引用，只用于澄清")
    q.add_argument("--dir", default="", help="存到笔记本文件夹下的哪个子目录，如 学习路线/单元1；默认 问答")
    q.add_argument("--follow-up", action="store_true", help="接着上一轮对话问")
    q.add_argument("--fresh", action="store_true",
                   help="每个问题开新对话（notebooklm ask --new，会删除服务器端对话历史；本 Skill 新建的笔记本默认如此）")
    q.add_argument("--keep-history", action="store_true", help="本 Skill 新建的笔记本也不开新对话")
    q.add_argument("--timeout", type=int, default=600)
    m = sub.add_parser("make")
    m.add_argument("--notebook", "-n", required=True)
    m.add_argument("kind", choices=["audio", "video", "mind-map", "report", "flashcards", "quiz",
                                    "infographic", "slide-deck", "data-table"])
    m.add_argument("--timeout", type=int, default=1800, help="最多等待生成完成的秒数")
    m.add_argument("--artifact", help="接着等待/下载已提交的生成任务 ID，不重新生成")
    s = sub.add_parser("status")
    s.add_argument("--notebook", "-n", required=True)
    argv = sys.argv[1:]
    extra = []
    if "--" in argv:  # -- 之后原样透传给 notebooklm generate
        cut = argv.index("--")
        argv, extra = argv[:cut], argv[cut + 1:]
    a = p.parse_args(argv)
    a.extra = extra
    return {"doctor": cmd_doctor, "import": cmd_import, "ask": cmd_ask, "make": cmd_make, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
