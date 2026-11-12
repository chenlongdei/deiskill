#!/usr/bin/env python3
"""dei-capture · YouTube 模块：关键词搜索、频道视频清单、单视频逐字稿。

数据来源：yt-dlp 优先（免费）；TikHub YouTube MCP 作补充（搜索按时间筛选、yt-dlp 被风控时）。
用法见 references/youtube.md。所有命令最后在 stdout 打印一行 JSON 摘要，供 Agent 读取。

    python3 youtube.py doctor
    python3 youtube.py search "关键词1" "关键词2" [--within this_month] [--limit 20]
    python3 youtube.py channel "@handle 或频道链接" [--limit 50] [--tabs videos,shorts]
    python3 youtube.py transcript <链接或ID> [...] [--from-list urls.txt] [--force]
    python3 youtube.py tikhub-tools [关键词]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_paths import data_dir, load_config, section, slug  # noqa: E402

DEFAULT_LANGS = ["zh-Hans", "zh-CN", "zh", "zh-Hant", "zh-TW", "en", "en-US", "en-GB"]
TIKHUB_URL = "https://mcp.tikhub.io/youtube/mcp"
BOT_HINT = "Sign in to confirm"


def cfg() -> dict:
    return section("youtube")


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def emit(summary: dict) -> None:
    print(json.dumps(summary, ensure_ascii=False))


# ---------------------------------------------------------------- yt-dlp


class YtdlpError(RuntimeError):
    def __init__(self, message: str):
        super().__init__(message)
        self.bot_check = BOT_HINT in message


COOKIE_ERRORS = ("cookies database", "could not copy", "Operation not permitted", "decrypt", "keyring")
COOKIE_NOTES: list[str] = []


def ytdlp_base(cookies: bool) -> list[str]:
    cmd = [cfg().get("yt_dlp_cmd") or "yt-dlp", "--no-warnings", "--no-update"]
    browser = cfg().get("cookies_from_browser")
    if cookies and browser:
        cmd += ["--cookies-from-browser", browser]
    return cmd


def ytdlp(args: list[str], timeout: int = 300, cookies: bool = False) -> str:
    """cookies 只用于单视频请求（搜索和频道列表不需要）；读不到浏览器 cookies 时退回不带 cookies。"""
    try:
        return _ytdlp(ytdlp_base(cookies) + args, timeout)
    except YtdlpError as exc:
        if cookies and cfg().get("cookies_from_browser") and any(k in str(exc) for k in COOKIE_ERRORS):
            note = f"读不到浏览器 cookies（{cfg().get('cookies_from_browser')}）：{exc}"
            if note not in COOKIE_NOTES:
                COOKIE_NOTES.append(note)
            return _ytdlp(ytdlp_base(False) + args, timeout)
        raise


def _ytdlp(cmd: list[str], timeout: int) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except FileNotFoundError:
        raise YtdlpError("找不到 yt-dlp，请先安装（pip/uv/brew 均可）或在 config.youtube.yt_dlp_cmd 指定命令")
    except subprocess.TimeoutExpired:
        raise YtdlpError(f"yt-dlp 超时（{timeout}s）")
    if proc.returncode != 0:
        lines = [ln for ln in proc.stderr.strip().splitlines() if ln.startswith("ERROR")] or proc.stderr.strip().splitlines()
        raise YtdlpError((lines[-1] if lines else f"yt-dlp 退出码 {proc.returncode}")[:500])
    return proc.stdout


def ytdlp_json(args: list[str], timeout: int = 300, cookies: bool = False) -> dict:
    return json.loads(ytdlp(["-J"] + args, timeout=timeout, cookies=cookies))


# ---------------------------------------------------------------- TikHub


def tikhub_token() -> str:
    tok = os.environ.get("TIKHUB_TOKEN") or (load_config().get("tikhub") or {}).get("token") or cfg().get("tikhub_token") or ""
    tok = tok.strip()
    return tok[len("Bearer "):].strip() if tok.startswith("Bearer ") else tok


class TikHub:
    """TikHub YouTube MCP（HTTP 流式 JSON-RPC）。坑：必须带 Bearer、自定义 UA、先 initialize 拿 session。"""

    def __init__(self) -> None:
        self.token = tikhub_token()
        if not self.token:
            raise RuntimeError("未配置 TikHub Token（config 顶层 tikhub.token 或环境变量 TIKHUB_TOKEN）")
        self.url = cfg().get("tikhub_mcp_url") or TIKHUB_URL
        self.sid = None
        self.rid = 0
        self._tools = None
        _, self.sid = self._post("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "dei-capture", "version": "1.0"},
        })
        self._post("notifications/initialized", {})

    def _post(self, method: str, params: dict | None = None):
        self.rid += 1
        payload = {"jsonrpc": "2.0", "id": self.rid, "method": method}
        if params is not None:
            payload["params"] = params
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "Mozilla/5.0 dei-capture/1.0",
        }
        if self.sid:
            headers["Mcp-Session-Id"] = self.sid
        req = urllib.request.Request(self.url, data=json.dumps(payload).encode(), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                sid = resp.headers.get("Mcp-Session-Id")
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            hint = {401: "Token 无效或缺 Bearer 前缀", 402: "余额不足", 403: "被拒绝（UA 或权限）", 429: "限流"}.get(exc.code, "")
            raise RuntimeError(f"TikHub HTTP {exc.code} {hint}".strip())
        for line in raw.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:]), sid
        return (json.loads(raw) if raw.strip() else {}), sid

    def tools(self) -> list[dict]:
        if self._tools is None:
            resp, _ = self._post("tools/list", {})
            self._tools = (resp.get("result") or {}).get("tools") or []
        return self._tools

    def call(self, name: str, arguments: dict) -> dict:
        resp, _ = self._post("tools/call", {"name": name, "arguments": arguments})
        if "error" in resp:
            raise RuntimeError(f"TikHub {name}: {resp['error']}")
        content = (resp.get("result") or {}).get("content") or []
        if not content:
            return {}
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}

    def call_auto(self, name: str, candidates: dict) -> dict:
        """按工具 inputSchema 自动填参数名（不同工具用 video_id / id / url / channel_id 等）。"""
        schema = next((t.get("inputSchema") or {} for t in self.tools() if t.get("name") == name), None)
        if schema is None:
            raise RuntimeError(f"TikHub 没有工具 {name}（用 tikhub-tools 查看可用工具）")
        props = schema.get("properties") or {}
        args = {k: v for k, v in candidates.items() if k in props and v not in (None, "")}
        missing = [k for k in schema.get("required") or [] if k not in args]
        if missing:
            raise RuntimeError(f"TikHub {name} 需要参数 {missing}，当前只有 {sorted(candidates)}")
        return self.call(name, args)


def find_dicts(obj, key: str) -> list[dict]:
    """在任意嵌套结构里找出含 key 的字典列表（TikHub 各接口返回结构不统一）。"""
    if isinstance(obj, list):
        if obj and all(isinstance(x, dict) for x in obj) and any(key in x for x in obj):
            return obj
        for x in obj:
            found = find_dicts(x, key)
            if found:
                return found
    elif isinstance(obj, dict):
        for v in obj.values():
            found = find_dicts(v, key)
            if found:
                return found
    return []


def walk_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_strings(v)


# ---------------------------------------------------------------- 通用


def to_int(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).replace(",", "").strip().lower()
    m = re.match(r"([\d.]+)\s*([kmb万亿]?)", text)
    if not m:
        return None
    mult = {"k": 1e3, "m": 1e6, "b": 1e9, "万": 1e4, "亿": 1e8}.get(m.group(2), 1)
    return int(float(m.group(1)) * mult)


def to_seconds(value) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    parts = str(value).strip().split(":")
    if all(p.isdigit() for p in parts):
        sec = 0
        for p in parts:
            sec = sec * 60 + int(p)
        return sec
    return None


def fmt_views(n) -> str:
    if n is None:
        return "—"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


def fmt_duration(sec) -> str:
    if sec is None:
        return "—"
    h, rest = divmod(int(sec), 3600)
    m, s = divmod(rest, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_date(value) -> str:
    if not value:
        return ""
    text = str(value)
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}" if re.fullmatch(r"\d{8}", text) else text


def video_id(text: str) -> str | None:
    text = text.strip()
    if re.fullmatch(r"[\w-]{11}", text):
        return text
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/|/embed/)([\w-]{11})", text)
    return m.group(1) if m else None


def run_dir(base: Path, name: str) -> Path:
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    path = base / f"{stamp}_{slug(name)}"
    n = 1
    while path.exists():
        n += 1
        path = base / f"{stamp}_{slug(name)}-{n}"
    path.mkdir(parents=True)
    return path


def write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------- search


def search_ytdlp(query: str, limit: int, newest: bool) -> list[dict]:
    prefix = "ytsearchdate" if newest else "ytsearch"
    data = ytdlp_json(["--flat-playlist", f"{prefix}{limit}:{query}"])
    out = []
    for e in data.get("entries") or []:
        vid = e.get("id")
        if not vid:
            continue
        out.append({
            "id": vid,
            "title": e.get("title") or "",
            "channel": e.get("channel") or e.get("uploader") or "",
            "channel_url": e.get("channel_url") or e.get("uploader_url") or "",
            "views": to_int(e.get("view_count")),
            "duration": to_seconds(e.get("duration")),
            "published": fmt_date(e.get("upload_date")),
            "url": f"https://www.youtube.com/watch?v={vid}",
            "desc": (e.get("description") or "")[:200],
        })
    return out


def search_tikhub(client: TikHub, query: str, within: str) -> list[dict]:
    args = {"search_query": query}
    if within != "any":
        args["order_by"] = within
    payload = client.call("youtube_web_search_video", args)
    videos = (payload.get("data") or {}).get("videos") or find_dicts(payload, "video_id")
    out = []
    for it in videos:
        vid = it.get("video_id")
        if not vid:
            continue
        out.append({
            "id": vid,
            "title": it.get("title") or "",
            "channel": it.get("author") or "",
            "channel_url": "",
            "views": to_int(it.get("number_of_views")),
            "duration": to_seconds(it.get("video_length")),
            "published": it.get("published_time") or "",
            "url": f"https://www.youtube.com/watch?v={vid}",
            "desc": (it.get("description") or "")[:200],
        })
    return out


def recommend(videos: list[dict], min_views: int, per_channel: int) -> list[dict]:
    picked, count = [], {}
    for v in videos:
        if (v.get("views") or 0) < min_views:
            continue
        key = v.get("channel") or v["id"]
        if count.get(key, 0) >= per_channel:
            continue
        count[key] = count.get(key, 0) + 1
        picked.append(v)
    return picked


def video_lines(i: int, v: dict) -> list[str]:
    lines = [f"### {i}. {v['title']}", "",
             f"- 频道：{v['channel'] or '—'}",
             f"- 播放：{fmt_views(v.get('views'))} · 时长：{fmt_duration(v.get('duration'))}"
             + (f" · 发布：{v['published']}" if v.get("published") else ""),
             f"- 链接：{v['url']}",
             f"- 命中关键词：{' / '.join(v.get('queries', []))}"]
    if v.get("desc"):
        lines.append(f"- 简介：{v['desc']}")
    return lines + [""]


def cmd_search(a) -> int:
    c = cfg()
    min_views = a.min_views if a.min_views is not None else int(c.get("min_views", 10000))
    per_channel = a.per_channel if a.per_channel is not None else int(c.get("per_channel", 2))
    engine = a.engine
    notes = []
    if engine == "auto" and a.within != "any":
        if tikhub_token():
            engine = "tikhub"
        else:
            notes.append(f"yt-dlp 不支持按「{a.within}」筛选，改为按最新排序；需要精确时间筛选请配置 TikHub Token")
    client = None
    merged: dict[str, dict] = {}
    per_query = {}
    for q in a.queries:
        results, used = [], engine
        if engine in ("auto", "ytdlp"):
            try:
                results, used = search_ytdlp(q, a.limit, newest=a.within != "any"), "ytdlp"
            except YtdlpError as exc:
                notes.append(f"[{q}] yt-dlp 失败：{exc}")
                if engine == "ytdlp" or not tikhub_token():
                    per_query[q] = {"engine": "ytdlp", "count": 0, "error": str(exc)}
                    continue
                used = "tikhub"
        if used == "tikhub":
            try:
                client = client or TikHub()
                results = search_tikhub(client, q, a.within)
            except RuntimeError as exc:
                notes.append(f"[{q}] TikHub 失败：{exc}")
                per_query[q] = {"engine": "tikhub", "count": 0, "error": str(exc)}
                continue
        per_query[q] = {"engine": used, "count": len(results)}
        for v in results:
            rec = merged.setdefault(v["id"], dict(v, queries=[]))
            rec["queries"].append(q)
            for k, val in v.items():
                if not rec.get(k) and val:
                    rec[k] = val
        print(f"[{q}] {used} {len(results)} 条", file=sys.stderr)

    ranked = sorted(merged.values(), key=lambda v: -(v.get("views") or 0))
    if not ranked:
        emit({"command": "search", "total": 0, "per_query": per_query, "notes": notes})
        return 2
    picked = recommend(ranked, min_views, per_channel)
    out = run_dir(data_dir("youtube") / "搜索", a.queries[0])
    result = {
        "captured_at": now(), "queries": a.queries, "within": a.within, "per_query": per_query,
        "filters": {"min_views": min_views, "per_channel": per_channel},
        "notes": notes, "recommended": [v["id"] for v in picked], "videos": ranked,
    }
    write_json(out / "results.json", result)
    (out / "urls.txt").write_text("".join(v["url"] + "\n" for v in picked), encoding="utf-8")
    md = [f"# YouTube 搜索：{' / '.join(a.queries)}", "",
          f"> 采集时间：{result['captured_at']} · 时间范围：{a.within} · 去重后 {len(ranked)} 条，按播放量排序",
          f"> 推荐规则：播放 ≥ {fmt_views(min_views)}，同一频道最多 {per_channel} 条 → {len(picked)} 条（链接在 urls.txt）", ""]
    for n in notes:
        md.append(f"> ⚠️ {n}")
    md += ["", f"## 推荐（{len(picked)}）", ""]
    for i, v in enumerate(picked, 1):
        md += video_lines(i, v)
    rest = [v for v in ranked if v["id"] not in set(result["recommended"])]
    if rest:
        md += [f"## 其余结果（{len(rest)}）", "", "| # | 标题 | 频道 | 播放 | 时长 | 链接 |", "|---|---|---|---|---|---|"]
        for i, v in enumerate(rest, 1):
            title = v["title"].replace("|", "｜")
            md.append(f"| {i} | {title} | {v['channel']} | {fmt_views(v.get('views'))} | {fmt_duration(v.get('duration'))} | {v['url']} |")
    (out / "清单.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    emit({"command": "search", "dir": str(out), "total": len(ranked), "recommended": len(picked), "notes": notes})
    return 0 if ranked else 2


# ---------------------------------------------------------------- channel


def channel_url(text: str) -> str:
    text = text.strip()
    if text.startswith("@"):
        return f"https://www.youtube.com/{text}"
    if re.fullmatch(r"UC[\w-]{22}", text):
        return f"https://www.youtube.com/channel/{text}"
    text = re.sub(r"/(videos|shorts|streams|featured|playlists)/?$", "", text.rstrip("/"))
    return text


def cmd_channel(a) -> int:
    base = channel_url(a.channel)
    tabs = [t.strip() for t in a.tabs.split(",") if t.strip()]
    videos: dict[str, dict] = {}
    meta, errors = {}, []
    for tab in tabs:
        args = ["--flat-playlist"]
        if a.limit:
            args += ["--playlist-end", str(a.limit)]
        try:
            data = ytdlp_json(args + [f"{base}/{tab}"], timeout=600)
        except YtdlpError as exc:
            errors.append(f"{tab}: {exc}")
            continue
        meta = meta or {
            "channel": data.get("channel") or data.get("uploader") or data.get("title"),
            "channel_id": data.get("channel_id"),
            "followers": data.get("channel_follower_count"),
            "url": base,
        }
        for e in data.get("entries") or []:
            vid = e.get("id")
            if vid and vid not in videos:
                videos[vid] = {
                    "id": vid, "tab": tab, "title": e.get("title") or "",
                    "views": to_int(e.get("view_count")), "duration": to_seconds(e.get("duration")),
                    "published": fmt_date(e.get("upload_date")),
                    "url": f"https://www.youtube.com/{'shorts/' + vid if tab == 'shorts' else 'watch?v=' + vid}",
                }
    if not videos and tikhub_token():
        try:
            client = TikHub()
            payload = client.call_auto("youtube_web_get_channel_videos_v2", {
                "channel_id": meta.get("channel_id") or (base.rsplit("/", 1)[-1] if "/channel/" in base else ""),
                "channel_url": base, "url": base,
            })
            for it in find_dicts(payload, "video_id"):
                vid = it["video_id"]
                videos[vid] = {"id": vid, "tab": "tikhub", "title": it.get("title") or "",
                               "views": to_int(it.get("number_of_views") or it.get("view_count")),
                               "duration": to_seconds(it.get("video_length") or it.get("length")),
                               "published": it.get("published_time") or "",
                               "url": f"https://www.youtube.com/watch?v={vid}"}
        except RuntimeError as exc:
            errors.append(f"TikHub: {exc}")
    if not videos:
        emit({"command": "channel", "url": base, "total": 0, "errors": errors})
        return 2

    name = meta.get("channel") or base.rsplit("/", 1)[-1]
    out = data_dir("youtube") / "频道" / slug(name)
    out.mkdir(parents=True, exist_ok=True)
    store = out / "videos.json"
    old = json.loads(store.read_text(encoding="utf-8")) if store.is_file() else {"videos": {}}
    stamp = now()
    new_ids = []
    had_history = bool(old["videos"])
    for vid, v in videos.items():
        prev = old["videos"].get(vid)
        if prev:
            v["first_seen"] = prev.get("first_seen", stamp)
        else:
            v["first_seen"] = stamp
            if had_history:
                new_ids.append(vid)
        old["videos"][vid] = dict(prev or {}, **{k: val for k, val in v.items() if val not in (None, "")})
    old.update(meta, last_fetch=stamp, history=(old.get("history") or []) + [{"at": stamp, "fetched": len(videos), "new": len(new_ids), "limit": a.limit}])
    write_json(store, old)

    allv = sorted(old["videos"].values(), key=lambda v: -(v.get("views") or 0))
    md = [f"# 频道：{name}", "",
          f"> 链接：{base} · 订阅：{fmt_views(meta.get('followers'))} · 已收录 {len(allv)} 条 · 最近抓取 {stamp}"
          + (f"（每个分区只取最新 {a.limit} 条）" if a.limit else ""), ""]
    for e in errors:
        md.append(f"> ⚠️ {e}")
    if new_ids:
        md += ["", f"## 本次新增（{len(new_ids)}）", ""]
        for vid in new_ids:
            v = old["videos"][vid]
            md.append(f"- {v['title']} · {fmt_views(v.get('views'))} · {v['url']}")
    md += ["", "## 全部视频（按播放量）", "", "| # | 标题 | 分区 | 播放 | 时长 | 链接 |", "|---|---|---|---|---|---|"]
    for i, v in enumerate(allv, 1):
        md.append(f"| {i} | {v['title'].replace('|', '｜')} | {v.get('tab', '')} | {fmt_views(v.get('views'))} | {fmt_duration(v.get('duration'))} | {v['url']} |")
    (out / "清单.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (out / "urls.txt").write_text("".join(v["url"] + "\n" for v in allv), encoding="utf-8")
    emit({"command": "channel", "dir": str(out), "channel": name, "fetched": len(videos), "total": len(allv),
          "new": len(new_ids), "errors": errors})
    return 0


# ---------------------------------------------------------------- transcript

TIME_RE = re.compile(r"(\d+):(\d{2}):(\d{2})[.,](\d{3})\s*-->|(\d{2}):(\d{2})[.,](\d{3})\s*-->")


def parse_subtitles(text: str) -> list[tuple[float, str]]:
    """解析 VTT/SRT，去掉 YouTube 自动字幕的滚动重复行，返回 [(开始秒, 文本)]。"""
    cues, start, last = [], None, None
    for raw in text.splitlines():
        line = raw.strip()
        m = TIME_RE.match(line)
        if m:
            if m.group(1) is not None:
                start = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            else:
                start = int(m.group(5)) * 60 + int(m.group(6))
            continue
        if not line or start is None or line.isdigit() or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        clean = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        if not clean or clean == last:
            continue
        cues.append((start, clean))
        last = clean
    return cues


def paragraphs(cues: list[tuple[float, str]], span: int = 60) -> list[str]:
    out, buf, head = [], [], None
    for start, text in cues:
        if head is None:
            head = start
        if start - head >= span and buf:
            out.append(f"[{fmt_duration(head)}] " + join_text(buf))
            buf, head = [], start
        buf.append(text)
    if buf:
        out.append(f"[{fmt_duration(head)}] " + join_text(buf))
    return out


def join_text(parts: list[str]) -> str:
    result = ""
    for p in parts:
        if result and re.search(r"[A-Za-z0-9,.!?;:]$", result) and re.match(r"[A-Za-z0-9]", p):
            result += " "
        result += p
    return result


def pick_subtitle(info: dict, prefs: list[str]) -> tuple[str, str] | None:
    """返回 (语言代码, 'manual'|'auto')。人工字幕优先；自动字幕取视频原语言，不取机器翻译。"""
    manual = info.get("subtitles") or {}
    auto = info.get("automatic_captions") or {}
    for lang in prefs:
        if lang in manual:
            return lang, "manual"
    manual_real = [k for k in manual if k != "live_chat"]
    if manual_real:
        return manual_real[0], "manual"
    orig = info.get("language")
    candidates = ([f"{orig}-orig", orig] if orig else []) + [k for k in auto if k.endswith("-orig")] + prefs
    for lang in candidates:
        if lang and lang in auto:
            return lang, "auto"
    return None


def fetch_ytdlp_subs(url: str, lang: str, kind: str, workdir: Path) -> list[tuple[float, str]]:
    flag = "--write-subs" if kind == "manual" else "--write-auto-subs"
    ytdlp(["--skip-download", "--ignore-no-formats-error", flag, "--sub-langs", lang, "--sub-format", "vtt/srt/best",
           "-o", str(workdir / "sub.%(ext)s"), url], cookies=True)
    files = sorted(workdir.glob("sub*.vtt")) + sorted(workdir.glob("sub*.srt"))
    if not files:
        raise YtdlpError("字幕文件没有下载下来")
    return parse_subtitles(files[0].read_text(encoding="utf-8", errors="replace"))


def fetch_tikhub_subs(vid: str) -> list[tuple[float, str]]:
    client = TikHub()
    payload = client.call_auto("youtube_web_get_video_subtitles", {"video_id": vid, "id": vid,
                                                                  "url": f"https://www.youtube.com/watch?v={vid}"})
    rows = find_dicts(payload, "text")
    if rows:
        cues = []
        for r in rows:
            start = r.get("start") or r.get("offset") or r.get("start_time") or 0
            start = to_int(start) or 0
            if "startMs" in r or "start_ms" in r:
                start = int(to_int(r.get("startMs") or r.get("start_ms")) or 0) // 1000
            if str(r.get("text", "")).strip():
                cues.append((start, html.unescape(str(r["text"]).strip())))
        return cues
    for text in walk_strings(payload):
        if "-->" in text:
            return parse_subtitles(text)
    raise RuntimeError("TikHub 返回里没有字幕文本（该视频可能没有字幕）")


def whisper_transcribe(url: str, workdir: Path) -> list[tuple[float, str]]:
    import asr
    ok, why = asr.whisper_ready()
    if not ok:
        raise RuntimeError("没有字幕，且" + why)
    js = [] if shutil.which("deno") else (["--js-runtimes", "node"] if shutil.which("node") else [])
    ytdlp(js + ["-f", "bestaudio/best", "-o", str(workdir / "audio.%(ext)s"), url], timeout=1800, cookies=True)
    audio = next(iter(sorted(workdir.glob("audio.*"))), None)
    if not audio:
        raise RuntimeError("音频下载失败")
    return asr.whisper_file(audio, workdir)


def yaml_str(value) -> str:
    return json.dumps("" if value is None else value, ensure_ascii=False)


def transcript_one(url_or_id: str, outdir: Path, prefs: list[str], force: bool) -> dict:
    vid = video_id(url_or_id)
    if not vid:
        return {"input": url_or_id, "status": "failed", "error": "不是 YouTube 视频链接或 ID"}
    existing = sorted(outdir.glob(f"{vid}_*.md"))
    if existing and not force:
        return {"id": vid, "status": "reused", "file": str(existing[0])}
    url = f"https://www.youtube.com/watch?v={vid}"
    info, attempts = {}, []
    cues, source, lang = [], "", ""
    with tempfile.TemporaryDirectory(prefix="dei-yt-") as tmp:
        work = Path(tmp)
        try:
            info = ytdlp_json(["--skip-download", "--ignore-no-formats-error", url], cookies=True)
            choice = pick_subtitle(info, prefs)
            if choice:
                lang, kind = choice
                cues = fetch_ytdlp_subs(url, lang, kind, work)
                source = f"yt-dlp {'人工字幕' if kind == 'manual' else '自动字幕'}"
            else:
                attempts.append("yt-dlp：视频没有字幕")
        except YtdlpError as exc:
            attempts.append("yt-dlp：被 YouTube 风控（需要在 config.youtube.cookies_from_browser 配置已登录 YouTube 的浏览器）"
                            if exc.bot_check else f"yt-dlp：{exc}")
        if not cues and tikhub_token():
            try:
                cues, source = fetch_tikhub_subs(vid), "TikHub 字幕"
            except RuntimeError as exc:
                attempts.append(f"TikHub：{exc}")
        if not cues:
            try:
                cues, source = whisper_transcribe(url, work), "本地转写（whisper）"
            except (RuntimeError, YtdlpError, subprocess.CalledProcessError) as exc:
                attempts.append(f"本地转写：{exc}")
    if not cues:
        return {"id": vid, "status": "failed", "error": "；".join(attempts)}

    title = info.get("title") or vid
    body = paragraphs(cues)
    front = {
        "title": title, "video_id": vid, "url": url,
        "channel": info.get("channel") or info.get("uploader") or "",
        "channel_url": info.get("channel_url") or "",
        "upload_date": fmt_date(info.get("upload_date")),
        "duration": fmt_duration(info.get("duration")) if info.get("duration") else "",
        "views": info.get("view_count"),
        "language": re.sub(r"-orig$", "", lang or info.get("language") or ""),
        "transcript_source": source,
        "captured_at": now(),
    }
    lines = ["---"] + [f"{k}: {yaml_str(v) if not isinstance(v, int) else v}" for k, v in front.items()] + ["---", "",
             f"# {title}", "",
             f"> {front['channel'] or '—'} · {front['upload_date'] or '日期未知'} · {front['duration'] or '时长未知'} · 来源：{source}",
             f"> {url}", ""]
    if info.get("description"):
        lines += ["## 视频简介", "", info["description"].strip()[:1500], ""]
    lines += ["## 逐字稿", ""] + [p + "\n" for p in body]
    path = outdir / f"{vid}_{slug(title, 50)}.md"
    for old in existing:
        old.unlink()
    path.write_text("\n".join(lines), encoding="utf-8")
    result = {"id": vid, "status": "completed", "file": str(path), "source": source, "chars": sum(len(t) for _, t in cues)}
    if attempts:
        result["fallbacks"] = attempts
    return result


def cmd_transcript(a) -> int:
    items = list(a.videos)
    if a.from_list:
        items += [ln.strip() for ln in Path(a.from_list).expanduser().read_text(encoding="utf-8").splitlines()
                  if ln.strip() and not ln.startswith("#")]
    if not items:
        sys.exit("没有要转写的视频")
    prefs = [s.strip() for s in a.langs.split(",")] if a.langs else (cfg().get("subtitle_langs") or DEFAULT_LANGS)
    outdir = data_dir("youtube") / "逐字稿"
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    for item in items:
        r = transcript_one(item, outdir, prefs, a.force)
        print(f"[{r.get('id', item)}] {r['status']} {r.get('file') or r.get('error', '')}", file=sys.stderr)
        results.append(r)
    log = outdir / "_log.jsonl"
    with log.open("a", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(dict(r, at=now()), ensure_ascii=False) + "\n")
    ok = [r for r in results if r["status"] in ("completed", "reused")]
    emit({"command": "transcript", "dir": str(outdir), "ok": len(ok), "failed": len(results) - len(ok),
          "notes": COOKIE_NOTES, "results": results})
    return 0 if ok else 2


# ---------------------------------------------------------------- doctor / tools


def cmd_doctor(a) -> int:
    c = cfg()
    checks = []
    try:
        ver = ytdlp(["--version"], timeout=30).strip()
        checks.append(("yt-dlp", True, ver))
    except YtdlpError as exc:
        checks.append(("yt-dlp", False, str(exc)))
    checks.append(("ffmpeg", bool(shutil.which("ffmpeg")), shutil.which("ffmpeg") or "未安装（仅本地转写需要）"))
    checks.append(("cookies_from_browser", bool(c.get("cookies_from_browser")), c.get("cookies_from_browser") or "未配置（遇到风控时需要）"))
    checks.append(("TikHub Token", bool(tikhub_token()), "已配置" if tikhub_token() else "未配置（可选补充）"))
    import asr
    w_ok, w_why = asr.whisper_ready()
    checks.append(("whisper", w_ok, w_why if w_ok else w_why + "（无字幕视频需要）"))
    try:
        checks.append(("output_root", True, str(data_dir("youtube"))))
    except SystemExit as exc:
        checks.append(("output_root", False, str(exc)))
    if a.probe:
        try:
            ytdlp_json(["--skip-download", "--ignore-no-formats-error", "https://www.youtube.com/watch?v=" + a.probe], cookies=True)
            checks.append(("单视频访问", True, "正常"))
            for note in COOKIE_NOTES:
                checks.append(("浏览器 cookies", False, note + "（已退回不带 cookies）"))
        except YtdlpError as exc:
            checks.append(("单视频访问", False, str(exc)))
    for name, ok, detail in checks:
        print(f"{'✅' if ok else '⚠️ '} {name}: {detail}", file=sys.stderr)
    emit({"command": "doctor", "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in checks]})
    return 0


def cmd_tools(a) -> int:
    client = TikHub()
    tools = client.tools()
    for t in tools:
        if a.keyword and a.keyword.lower() not in t.get("name", "").lower():
            continue
        props = (t.get("inputSchema") or {}).get("properties") or {}
        print(f"{t.get('name')}  参数：{', '.join(props)}  — {(t.get('description') or '')[:80]}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="dei-capture YouTube 模块")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("doctor")
    d.add_argument("--probe", metavar="VIDEO_ID", help="实际访问一个视频，检查是否被风控")
    s = sub.add_parser("search")
    s.add_argument("queries", nargs="+")
    s.add_argument("--limit", type=int, default=20, help="每个关键词取多少条（yt-dlp）")
    s.add_argument("--within", default="any", choices=["any", "today", "this_week", "this_month", "this_year"])
    s.add_argument("--engine", default="auto", choices=["auto", "ytdlp", "tikhub"])
    s.add_argument("--min-views", type=int)
    s.add_argument("--per-channel", type=int)
    c = sub.add_parser("channel")
    c.add_argument("channel", help="@handle、UC 开头的频道 ID 或频道链接")
    c.add_argument("--limit", type=int, default=0, help="每个分区只取最新 N 条；0 为全部")
    c.add_argument("--tabs", default="videos", help="逗号分隔：videos,shorts,streams")
    t = sub.add_parser("transcript")
    t.add_argument("videos", nargs="*")
    t.add_argument("--from-list", help="每行一个链接的文件（如搜索结果的 urls.txt）")
    t.add_argument("--langs", help="字幕语言优先级，逗号分隔")
    t.add_argument("--force", action="store_true", help="已有逐字稿也重做")
    tl = sub.add_parser("tikhub-tools")
    tl.add_argument("keyword", nargs="?")
    a = p.parse_args()
    return {"doctor": cmd_doctor, "search": cmd_search, "channel": cmd_channel,
            "transcript": cmd_transcript, "tikhub-tools": cmd_tools}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
