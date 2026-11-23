#!/usr/bin/env python3
"""换背景音乐：复制进工程、测节拍，把起点对到一个强拍，写回 project.json。

用法：
  python3 scripts/bgm.py <工程> <音乐文件> [--source "曲名 / 作者 / 平台 / 许可"] [--skip 4]
  python3 scripts/bgm.py <工程> --latest [--source ...]     取「下载」文件夹里最新的 mp3/wav（用户刚在浏览器里点了下载时用）

--skip：跳过开头几秒的前奏（默认 4 秒），从之后第一个节拍开始用。
"""
import argparse, json, pathlib, shutil
from common import project, save_project, hf, die

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("file", nargs="?")
ap.add_argument("--latest", action="store_true")
ap.add_argument("--source", default="")
ap.add_argument("--skip", type=float, default=4.0)
a = ap.parse_args()
d, P = project(a.project)

if a.latest:
    dl = pathlib.Path.home() / "Downloads"
    files = sorted([p for p in dl.glob("*") if p.suffix.lower() in (".mp3", ".wav", ".m4a")], key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        die(f"{dl} 里没有音乐文件")
    src = files[0]
else:
    if not a.file:
        die("给音乐文件路径，或用 --latest")
    src = pathlib.Path(a.file).expanduser()
if not src.is_file():
    die(f"找不到 {src}")

cands = d / "BGM候选"
cands.mkdir(exist_ok=True)
keep = cands / src.name
if not keep.exists():
    shutil.copy2(src, keep)
dst = d / "assets/audio" / ("bgm" + src.suffix.lower())
shutil.copy2(src, dst)

r = hf(["beats", str(dst), "--json"], d, capture=True)
try:
    info = json.loads(r.stdout[r.stdout.index("{"):])
except Exception:
    die("测节拍失败：" + (r.stderr or r.stdout)[-300:])
beats, bpm = info.get("beatTimes", []), info.get("bpm")
start = next((b for b in beats if b >= a.skip), beats[0] if beats else 0.0)
P.setdefault("bgm", {})
P["bgm"].update({"file": f"assets/audio/{dst.name}", "offset": round(start, 3), "bpm": bpm})
if a.source:
    P["bgm"]["source"] = a.source
save_project(d, P)
print(f"BGM：{src.name}  {bpm} BPM，从 {start:.3f}s 开始用；镜头里 snap:true 的切点会对到节拍")
print("原文件留在 BGM候选/。记得在交付说明里写曲名、作者和许可。")
