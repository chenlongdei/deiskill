#!/usr/bin/env python3
"""建剪辑工程：把素材复制进来、生成 HyperFrames 工程骨架和 project.json 草稿，并给每段素材出一张缩略图拼板。

用法：
  python3 scripts/new.py <工程文件夹> --footage <素材文件夹> [--card <团购卡截图>] [--title 名字]

工程文件夹不存在时会新建（Agent 先把完整路径告诉用户、确认后再运行）。原素材只复制、不改动。
"""
import argparse, json, pathlib, shutil, subprocess, sys
from datetime import datetime, timezone, timedelta
from common import SKILL, config, die, ffdur

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--footage", required=True, help="客户原始素材文件夹")
ap.add_argument("--card", help="团购卡截图（不给就在素材文件夹里找图片）")
ap.add_argument("--title", default="")
a = ap.parse_args()

src = pathlib.Path(a.footage).expanduser().resolve()
if not src.is_dir():
    die(f"素材文件夹不存在：{src}")
d = pathlib.Path(a.project).expanduser().resolve()
for sub in ["assets/video", "assets/img", "assets/audio", "assets/fonts", "素材缩略图"]:
    (d / sub).mkdir(parents=True, exist_ok=True)

# 素材：复制并统一命名 clip01.mp4…，记下原名
clips, mapping = [], {}
for i, f in enumerate(sorted(p for p in src.iterdir() if p.suffix.lower() in VIDEO_EXT), 1):
    name = f"clip{i:02d}{f.suffix.lower()}"
    dst = d / "assets/video" / name
    if not dst.exists():
        shutil.copy2(f, dst)
        dst.chmod(0o644)
    dur = ffdur(dst)
    mapping[name] = {"原文件": f.name, "时长": round(dur, 2)}
    clips.append((name, dur))
    # 每秒一帧的拼板（从左到右、从上到下，第 N 格 = 第 N-1 秒），给 Agent 看画面内容、挑镜头
    cols = 9
    rows = max(1, min(4, int(dur) // cols + 1))
    thumb = str(d / "素材缩略图" / f"{dst.stem}.jpg")
    stamp = "drawtext=text='%{pts\\:hms}':x=4:y=4:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.5,"
    for vf in (f"fps=1,scale=180:-1,{stamp}tile={cols}x{rows}", f"fps=1,scale=180:-1,tile={cols}x{rows}"):  # 有的 ffmpeg 没编 drawtext
        if subprocess.run(["ffmpeg", "-v", "quiet", "-y", "-i", str(dst), "-vf", vf, "-frames:v", "1", thumb]).returncode == 0:
            break
if not clips:
    die(f"{src} 里没有视频文件")

card = None
cands = [pathlib.Path(a.card).expanduser()] if a.card else sorted(p for p in src.iterdir() if p.suffix.lower() in IMG_EXT)
if cands:
    card = "assets/img/" + "groupbuy" + cands[0].suffix.lower()
    shutil.copy2(cands[0], d / card)

# 字体：config.json 里配置的两个字体文件
c = config()
fonts = {}
for key in ("caption", "display", "number"):
    p = c.get(f"font_{key}")
    if p and pathlib.Path(p).expanduser().is_file():
        fp = pathlib.Path(p).expanduser()
        shutil.copy2(fp, d / "assets/fonts" / fp.name)
        fonts[key] = fp.name
    else:
        print(f"提示：config.json 的 font_{key} 没配或文件不存在，见 references/setup.md「字体」")

# HyperFrames 工程骨架
(d / "hyperframes.json").write_text(json.dumps({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
    "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}, "media": {"autoProxy": True}},
    ensure_ascii=False, indent=2), encoding="utf-8")
now = datetime.now(timezone(timedelta(hours=8)))
(d / "meta.json").write_text(json.dumps({"id": d.name, "name": a.title or d.name, "createdAt": now.isoformat()}, ensure_ascii=False, indent=2), encoding="utf-8")
(d / "素材对照.json").write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")

pj = d / "project.json"
if not pj.exists():
    tpl = json.loads((SKILL / "templates/project.example.json").read_text(encoding="utf-8"))
    tpl["title"] = a.title or d.name
    tpl["voice"]["voice_id"] = c.get("voice_id", tpl["voice"]["voice_id"])
    tpl["voice"]["model"] = c.get("tts_model", tpl["voice"]["model"])
    tpl["fonts"] = fonts
    if card:
        for o in tpl["overlays"]:
            if o["type"] == "card":
                o["img"] = card
    tpl["_素材"] = {n: f"{dur:.1f}秒" for n, dur in clips}
    pj.write_text(json.dumps(tpl, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"已写 project.json 草稿（来自模板，口播、镜头、图层都要按这次的文案和素材改）")
print(f"工程：{d}")
for n, dur in clips:
    print(f"  {n}  {dur:.1f}s  ← {mapping[n]['原文件']}   缩略图：素材缩略图/{pathlib.Path(n).stem}.jpg")
print(f"团购卡：{card or '没有（CTA 段会缺团购卡，问用户要截图）'}")
