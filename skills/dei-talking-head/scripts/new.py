#!/usr/bin/env python3
"""建工程：复制（或链接）原片 → 转写原片 → 找说话段 → 写逐字稿.md 和 plan.json 草稿 → 搭好 HyperFrames 骨架。

用法：python3 scripts/new.py <工程目录> --source <原片> [--title "标题"] [--names "Codex,Obsidian"] [--link]
  --names  专有名词，喂给 whisper 提高准确率，也写进 plan.json 的 names
  --link   原片太大时不复制，建符号链接（外接盘要一直插着）
"""
import argparse, json, pathlib, shutil
from common import SKILL, die, run, ffdur, silences, to16k, transcribe, save_plan, fmt, config, silence_db

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--source", required=True)
ap.add_argument("--title", default="")
ap.add_argument("--names", default="")
ap.add_argument("--link", action="store_true")
a = ap.parse_args()

d = pathlib.Path(a.project).resolve()
src = pathlib.Path(a.source).resolve()
if not src.is_file():
    die(f"找不到原片 {src}")
if (d / "plan.json").exists():
    die(f"{d} 已经是工程了（有 plan.json）。要重来就换个目录")
for sub in ["source", "work", "成片", "hf/compositions", "hf/assets/icons", "hf/assets/logos", "hf/assets/fonts", "hf/assets/music", "hf/assets/broll"]:
    (d / sub).mkdir(parents=True, exist_ok=True)

dst = d / "source" / ("原片" + src.suffix.lower())
if a.link:
    dst.symlink_to(src)
else:
    shutil.copy2(src, dst)
print("原片 →", dst)

# 转写原片：短语级时间（-ml 1 -sow），专有名词做提示
names = [n.strip() for n in a.names.replace("，", ",").split(",") if n.strip()]
prompt = "、".join(names) + "。" if names else ""
to16k(dst, d / "work/src16k.wav")
segs = transcribe(d / "work/src16k.wav", d / "work/src_tr", prompt)
# 说话段 = 去掉 ≥0.3 秒的静音（门限按这条录音的响度自适应，见 common.silence_db）
dur = ffdur(dst)
SIL_DB = silence_db(d / "work/src16k.wav")
sil = silences(d / "work/src16k.wav", SIL_DB, 0.3)
print(f"静音门限 {SIL_DB} dB（按原片响度定）")
speech, t = [], 0.0
for s, e in sil:
    if s - t > 0.05:
        speech.append([round(t, 3), round(s, 3)])
    t = e
if dur - t > 0.05:
    speech.append([round(t, 3), round(dur, 3)])
(d / "work/speech.json").write_text(json.dumps(speech), encoding="utf-8")

# 逐字稿：带原片时间码，标出 ≥0.8 秒的长停顿，给 Agent 和用户读
lines = [f"# 逐字稿（原片 {fmt(dur)}）", "", "时间是原片秒数。写 plan.json 的 keep / cut 用这里的时间；「⏸」是 0.8 秒以上的停顿。", ""]
prev_end = 0.0
for sg in segs:
    a0, a1 = sg["offsets"]["from"] / 1000, sg["offsets"]["to"] / 1000
    gap = [x for x in sil if x[0] >= prev_end - .05 and x[1] <= a0 + .3 and x[1] - x[0] >= .8]
    for s, e in gap:
        lines.append(f"- ⏸ {s:.2f}–{e:.2f}（{e - s:.1f} 秒）")
    lines.append(f"- `{a0:7.2f}–{a1:7.2f}` {sg['text'].strip()}")
    prev_end = a1
(d / "逐字稿.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

c = config()
plan = {
    "title": a.title or "（常驻标题，HTML，可用 <b> 标亮数字）",
    "names": names,
    "keep": [[0.0, round(dur, 2), "（待定：Agent 读逐字稿后改成真正的保留段）"]],
    "cut": [],
    "no_split": [],
    "split_gap": c.get("split_gap", 0.45),
    "pad": 0.07,
    "speed": c.get("speed", 1.1),
    "caption_fixes": [],
    "keywords": names,
    "bgm": "",
    "loudness": c.get("loudness_lufs", -14),
}
save_plan(d, plan)

# HyperFrames 骨架 + 图标 + 字体
(d / "hf/hyperframes.json").write_text(json.dumps({
    "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
    "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"},
    "media": {"autoProxy": True}}, indent=2), encoding="utf-8")
(d / "hf/meta.json").write_text(json.dumps({"id": "talking-head", "name": d.name}, ensure_ascii=False), encoding="utf-8")
(d / "hf/package.json").write_text(json.dumps({"name": "talking-head", "private": True, "type": "module"}, indent=2), encoding="utf-8")
for f in (SKILL / "templates/icons").iterdir():
    shutil.copy2(f, d / "hf/assets/icons" / f.name)
for key, name in [("font_bold", "Bold"), ("font_black", "Black"), ("font_number", "Number")]:
    p = pathlib.Path(c.get(key) or "").expanduser()
    if c.get(key) and p.is_file():
        shutil.copy2(p, d / f"hf/assets/fonts/{name}{p.suffix}")
    else:
        print(f"⚠ 没配置字体 {key}（config.json），字幕会退回系统字体，见 references/setup.md")
shutil.copy2(SKILL / "templates/scenes_example.py", d / "scenes_example.py")

print(f"转写 {len(segs)} 句，说话段 {len(speech)} 段，原片 {fmt(dur)}")
print("下一步：读", d / "逐字稿.md", "→ 改 plan.json 的 keep / cut（每段写理由）→ 给用户看删改清单")
