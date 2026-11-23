#!/usr/bin/env python3
"""交接件：把工程拆成能在剪映里手改的几样东西，放进 交接/：
  字幕.srt          对好成片时间的字幕
  图层.mov          透明背景的图解、贴纸、标题、进度条（ProRes 4444，带 alpha）
  人物.mp4 / 人声.wav / 配乐.wav / 音效/   分开的素材
  剪映草稿/<名字>/   多轨草稿：人物（按跳切换景别分段）/ 空镜 / 图层 / 字幕（可改字）/ 人声 / 配乐 / 音效 1–3（每个音效单独一段）
草稿用 pyJianYingDraft（Apache-2.0）生成；没装它就只出前几样，在剪映里手动拼：人物 → 图层 → 导入 SRT → 声音。

用法：python3 scripts/export.py <工程> [--name 口播_v1] [--no-mov]
先跑 build.py 和 mix.py。剪映打开草稿：把 交接/剪映草稿/<名字> 整个文件夹复制到剪映的草稿目录（剪映 → 全局设置 → 草稿位置），重启剪映。
"""
import argparse, json, re, shutil, subprocess
from common import project, hf, die, run, ffdur

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--name", default="口播")
ap.add_argument("--no-mov", action="store_true")
a = ap.parse_args()
d, plan = project(a.project)
L = json.loads((d / "work/layout.json").read_text(encoding="utf-8"))
AROLL, TOTAL, FACE_Y = L["aroll"], L["total"], L["face_y"]
OUT = d / "交接"
MAT = OUT / "素材"
(MAT / "音效").mkdir(parents=True, exist_ok=True)

# 1. 字幕.srt
def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
(OUT / "字幕.srt").write_text("".join(f"{i}\n{ts(g['start'])} --> {ts(g['end'])}\n{g['text']}\n\n" for i, g in enumerate(L["caps"], 1)), encoding="utf-8")
print("字幕.srt", len(L["caps"]), "条")

# 2. 图层.mov（透明）
mov = OUT / "图层.mov"
if not a.no_mov:
    r = subprocess.run([__import__("sys").executable, str(__import__("pathlib").Path(__file__).parent / "build.py"), str(d), "--overlay"], capture_output=True, text=True)
    if r.returncode:
        die("build.py --overlay 失败：" + r.stderr[-500:])
    if hf(["render", "--format", "mov", "--output", str(mov)], d / "hf_overlay").returncode or not mov.exists():
        die("透明图层渲染失败")
    print("图层.mov", round(ffdur(mov), 1), "秒")

# 3. 分开的素材（人声统一到 -16 LUFS，配乐和音效跟着同样加减，保持成片里的相对音量）
err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(d / "hf/assets/voice.wav"), "-af", "ebur128", "-f", "null", "-"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
gain = -16 - float(re.findall(r"I:\s+(-?[\d.]+) LUFS", err)[-1])
shutil.copy2(d / "hf/assets/aroll.mp4", MAT / "人物.mp4")
run(["ffmpeg", "-v", "error", "-y", "-i", d / "hf/assets/voice.wav", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.89", "-c:a", "pcm_s16le", MAT / "人声.wav"])
if (d / "work/bgm_track.wav").exists():
    run(["ffmpeg", "-v", "error", "-y", "-i", d / "work/bgm_track.wav", "-af", f"volume={gain:.2f}dB", "-c:a", "pcm_s16le", MAT / "配乐.wav"])
NAMES = dict(whoosh="图解进场", pop="弹出", tap="点击_逐条", ding="叮_完成", strike="划掉", sparkle="高亮", text_slam="砸字",
             riser="蓄力", impact="警示", typing="键盘打字")
for f in sorted((d / "work/sfx_scaled").glob("*.wav")):
    run(["ffmpeg", "-v", "error", "-y", "-i", f, "-af", f"volume={gain:.2f}dB", "-c:a", "pcm_s16le", MAT / "音效" / f"{NAMES.get(f.stem, f.stem)}.wav"])
for a0, b0, f, ms in L["broll"]:
    (MAT / "空镜").mkdir(exist_ok=True)
    shutil.copy2(d / "hf/assets/broll" / f, MAT / "空镜" / f)

# 4. 剪映草稿
try:
    import pyJianYingDraft as draft
    from pyJianYingDraft import trange_seconds, ClipSettings, TextStyle, TextBorder
except ImportError:
    print("没装 pyJianYingDraft（pip install pyJianYingDraft），跳过剪映草稿。手动拼：人物.mp4 → 图层.mov → 导入字幕.srt → 人声 / 配乐 / 音效")
    raise SystemExit(0)
(OUT / "剪映草稿").mkdir(exist_ok=True)
folder = draft.DraftFolder(str(OUT / "剪映草稿"))
sc = folder.create_draft(a.name, 1080, 1920, fps=30, allow_replace=True)
sc.append_tracks([draft.TrackSpec(draft.TrackType.video, "人物"), draft.TrackSpec(draft.TrackType.video, "空镜"),
                  draft.TrackSpec(draft.TrackType.video, "图层"), draft.TrackSpec(draft.TrackType.text, "字幕"),
                  draft.TrackSpec(draft.TrackType.audio, "人声"), draft.TrackSpec(draft.TrackType.audio, "配乐")] +
                 [draft.TrackSpec(draft.TrackType.audio, f"音效{i}") for i in (1, 2, 3)])
# 人物：按换景别的时间切段；绕画面中心放大会把脸推上去，用 transform_y 补回（剪映 y 向上为正，单位半个画布高）
pts = [(0.0, 1.0)] + [(t, s) for t, s in L["punch"] if 0 < t < AROLL]
for k, (t, s) in enumerate(pts):
    end = pts[k + 1][0] if k + 1 < len(pts) else AROLL
    if end - t < .05:
        continue
    ty = (s - 1) * (FACE_Y - 960) / 960
    sc.add_segment(draft.VideoSegment(str(MAT / "人物.mp4"), trange_seconds(t, duration=end - t), source_timerange=trange_seconds(t, duration=end - t),
                                      volume=0, clip_settings=ClipSettings(scale_x=s, scale_y=s, transform_y=ty)), "人物")
for a0, b0, f, ms in L["broll"]:
    sc.add_segment(draft.VideoSegment(str(MAT / "空镜" / f), trange_seconds(a0, duration=b0 - a0), source_timerange=trange_seconds(ms, duration=b0 - a0),
                                      volume=0), "空镜")
if mov.exists():
    sc.add_segment(draft.VideoSegment(str(mov), trange_seconds(0, duration=min(TOTAL, ffdur(mov) - .01))), "图层")
cy = -((L["caption_top"] + 45) - 960) / 960
for g in L["caps"]:
    if g["end"] - g["start"] < .05:
        continue
    sc.add_segment(draft.TextSegment(g["text"], trange_seconds(g["start"], end=g["end"]), style=TextStyle(size=11.0, bold=True, color=(1, 1, 1), align=1),
                                     border=TextBorder(color=(0, 0, 0), width=60), clip_settings=ClipSettings(transform_y=cy)), "字幕")
sc.add_segment(draft.AudioSegment(str(MAT / "人声.wav"), trange_seconds(0, duration=min(ffdur(MAT / "人声.wav") - .005, AROLL))), "人声")
if (MAT / "配乐.wav").exists():
    sc.add_segment(draft.AudioSegment(str(MAT / "配乐.wav"), trange_seconds(0, duration=min(ffdur(MAT / "配乐.wav") - .005, TOTAL))), "配乐")
ev = json.loads((d / "work/sfx_events.json").read_text(encoding="utf-8"))["ev"]
free, n = [0.0, 0.0, 0.0], 0
for e in ev:
    f = MAT / "音效" / f"{NAMES.get(e['kind'], e['kind'])}.wav"
    if not f.exists():
        continue
    dur = min(ffdur(f) - .005, TOTAL - e["t"])
    i = next((j for j in range(3) if free[j] <= e["t"]), None)
    if i is None or dur <= .02:
        continue
    sc.add_segment(draft.AudioSegment(str(f), trange_seconds(e["t"], duration=dur), volume=e.get("v", 1.0)), f"音效{i + 1}")
    free[i] = e["t"] + dur + .01; n += 1
sc.save()
print(f"剪映草稿：{OUT / '剪映草稿' / a.name}（人物 {len(pts)} 段、字幕 {len(L['caps'])} 条、音效 {n} 段）")
print("开头 4 秒的慢推没进草稿（剪映里要的话加两个缩放关键帧）；素材用的是绝对路径，工程文件夹不要挪")
