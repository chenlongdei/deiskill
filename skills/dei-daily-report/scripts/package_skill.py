#!/usr/bin/env python3
"""Build a shareable package without local credentials or collected data."""
import argparse
from pathlib import Path
import zipfile
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"data", "node_modules", "__pycache__", ".git"}
PRIVATE = {"config.json", ".aihot-actor-id", "agent.conf", ".DS_Store", "feed-x.json", "feed-podcasts.json", "feed-blogs.json", "state-feed.json"}
def files():
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not str(relative).startswith(("skills/policy/references/examples/", "skills/ai/sources/follow-builders", "skills/zhihu/tools/zhihu")) and path.is_file() and not path.is_symlink() and not EXCLUDED.intersection(relative.parts) and path.name not in PRIVATE and path.suffix not in {".log", ".xlsx", ".zip", ".pyc"}:
            yield path
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files():
            archive.write(path, Path(ROOT.name) / path.relative_to(ROOT))
    print(output)
