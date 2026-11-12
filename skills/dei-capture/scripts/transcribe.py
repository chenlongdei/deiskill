#!/usr/bin/env python3
"""统一转写入口：本地音视频文件或公网直链 → Markdown 逐字稿。

用法（在 dei-capture 目录下）：
  python3 scripts/transcribe.py <文件或直链> [<文件或直链> ...] [--engine auto|whisper|paraformer] [--force]
  python3 scripts/transcribe.py doctor

引擎选择（auto）：本地文件 → whisper（本地免费）；直链 → paraformer（阿里云，按时长计费）。
平台页面链接（YouTube、抖音分享链接等）不在这里处理，用对应平台的命令，它们会先拿到字幕或直链。
产出：<output_root>/转写/<文件名>.md；最后一行 stdout 是 JSON 摘要。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import asr  # noqa: E402
from capture_paths import data_dir, slug  # noqa: E402

PAGE_HOSTS = ("youtube.com", "youtu.be", "douyin.com", "iesdouyin.com", "bilibili.com", "b23.tv",
              "xiaohongshu.com", "xhslink.com")


def is_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def pick_engine(src: str, want: str) -> str:
    if want != "auto":
        return want
    return "paraformer" if is_url(src) else "whisper"


def one(src: str, engine: str, outdir: Path, force: bool) -> dict:
    if is_url(src):
        host = urlparse(src).hostname or ""
        if any(host == h or host.endswith("." + h) for h in PAGE_HOSTS):
            return {"source": src, "ok": False,
                    "error": "这是平台页面链接，不是音视频直链：YouTube 用 youtube.py transcript，抖音用 douyin/run.py monitor --links"}
        name = slug(Path(urlparse(src).path).stem or "audio", 30) + "_" + hashlib.md5(src.encode()).hexdigest()[:6]
    else:
        path = Path(src).expanduser()
        if not path.is_file():
            return {"source": src, "ok": False, "error": "文件不存在"}
        src, name = str(path.resolve()), slug(path.stem, 40)
    target = outdir / f"{name}.md"
    if target.exists() and not force:
        return {"source": src, "ok": True, "file": str(target), "skipped": "已存在（--force 重做）"}
    if engine == "whisper" and is_url(src):
        return {"source": src, "ok": False, "error": "whisper 只处理本地文件；直链用 paraformer，或先下载到本地"}
    if engine == "paraformer" and not is_url(src):
        return {"source": src, "ok": False,
                "error": "paraformer 只收公网直链；本地文件请配置 whisper（config 的 whisper.model）"}
    duration = None
    try:
        if engine == "whisper":
            with tempfile.TemporaryDirectory() as tmp:
                cues = asr.whisper_file(Path(src), Path(tmp))
        else:
            cues, duration = asr.paraformer_url(src)
    except Exception as e:  # noqa: BLE001
        return {"source": src, "ok": False, "engine": engine, "error": str(e)[:300]}
    if not cues:
        return {"source": src, "ok": False, "engine": engine, "error": "没有识别到语音（可能是纯音乐）"}
    body = asr.paragraphs(cues)
    meta = {"source": src, "engine": engine, "transcribed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "duration_seconds": duration, "chars": sum(len(t) for _, t in cues)}
    front = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items())
    outdir.mkdir(parents=True, exist_ok=True)
    target.write_text(f"---\n{front}\n---\n\n# {name}\n\n" + "\n\n".join(body) + "\n", encoding="utf-8")
    return {"source": src, "ok": True, "engine": engine, "file": str(target), "chars": meta["chars"]}


def doctor() -> int:
    ok_w, why_w = asr.whisper_ready()
    key = (asr.dashscope_config().get("api_key") or "").strip()
    print(f"{'✅' if ok_w else '⬜'} whisper（本地文件，免费）— {why_w}")
    print(f"{'✅' if key else '⬜'} paraformer（直链，阿里云计费）— {'已配置 Key' if key else '未配置 dashscope.api_key'}")
    print(json.dumps({"command": "doctor", "whisper": ok_w, "paraformer": bool(key)}, ensure_ascii=False))
    return 0


def main() -> int:
    if sys.argv[1:2] == ["doctor"]:
        return doctor()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+")
    ap.add_argument("--engine", choices=["auto", "whisper", "paraformer"], default="auto")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    outdir = data_dir("transcribe")
    results = [one(s, pick_engine(s, a.engine), outdir, a.force) for s in a.sources]
    for r in results:
        print(("✓ " if r["ok"] else "✗ ") + r["source"] + ("  → " + r["file"] if r.get("file") else "  " + r.get("error", "")))
    ok = sum(r["ok"] for r in results)
    print(json.dumps({"command": "transcribe", "ok": ok, "failed": len(results) - ok, "dir": str(outdir),
                      "results": results}, ensure_ascii=False))
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
