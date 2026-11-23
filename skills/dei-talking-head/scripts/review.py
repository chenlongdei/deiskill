#!/usr/bin/env python3
"""听审：把成片切成 30 秒一段（前后各多 1 秒重叠），交给能直接看视频、听音频的模型（默认 Gemini，经 Antigravity CLI `agy`），
专查卡顿、吞字、残留尾音、音效太冲、音画不同步、字幕和图解看不清。结果汇总到 审片意见.md。
它的每一条都要回原片核实（probe.py）再改，不照单全收：片段边界的「截断」「残音」是切片造成的，不算问题。

用法：
  python3 scripts/review.py <工程> --video 成片/口播_v1.mp4               全片
  python3 scripts/review.py <工程> --video ... --range 75,95              只审一段（成片秒数）
上传前提：视频会发给 Google（用户自己的账号）。第一次用要先问用户，出镜内容敏感的不审。
"""
import argparse, shutil, subprocess
from common import project, config, ffdur, fmt, die

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--video", required=True)
ap.add_argument("--range", default="")
ap.add_argument("--chunk", type=float, default=30)
a = ap.parse_args()
d, plan = project(a.project)
c = config()
agy = c.get("reviewer_cli") or shutil.which("agy")
if not agy:
    die("没有审片工具：装 Antigravity CLI（agy）并登录，或在 config.json 的 reviewer_cli 填路径（见 references/review.md）")
video = (d / a.video) if not a.video.startswith("/") else a.video
total = ffdur(video)
lo, hi = (map(float, a.range.split(","))) if a.range else (0, total)
folder = d / "work/review"
folder.mkdir(parents=True, exist_ok=True)

PROMPT = """你是短视频剪辑师。这个文件是一条中文真人口播成片的片段，对应成片的 {a:.1f}–{b:.1f} 秒。
请真正观看并收听（包括音频），逐条指出：
1. 剪辑点：卡顿、声音一顿一顿、吞字、被删的词留了半个音、气口太急或太长、画面跳动不自然；
2. 声音：音效太响、刺耳、和别的声音打架；配乐盖过人声；
3. 画面：字幕或图解看不清、挡脸、出画、和口播对不上。
每条写：成片时间（片段内秒数 + {a:.1f}）、问题、建议怎么改。没有问题就说没有。
片段开头和结尾的截断是我切片造成的，不要报。最后一行说明你是直接理解了视频音频，还是用工具间接分析的。用中文，简短。"""

notes = [f"# 审片意见（{video}）", "", "每条都要回原片核实再改（`probe.py`）；片段边界的截断不算。", ""]
t = lo
while t < hi - 1:
    s, e = max(0, t - 1), min(hi, t + a.chunk + 1)
    clip = folder / f"片段_{int(s)}-{int(e)}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(s), "-to", str(e), "-i", str(video), "-c:v", "libx264", "-crf", "23",
                    "-c:a", "aac", str(clip)], check=True)
    print(f"审 {fmt(s)}–{fmt(e)} …", flush=True)
    r = subprocess.run([agy, "-p", f"请看 {clip.name}。" + PROMPT.format(a=s, b=e), "--print-timeout", c.get("reviewer_timeout", "900s")],
                       cwd=str(folder), capture_output=True, text=True, encoding="utf-8", errors="replace")
    notes += [f"## {fmt(s)}–{fmt(e)}", "", (r.stdout or r.stderr).strip(), ""]
    t += a.chunk
(d / "审片意见.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
print("写好了：", d / "审片意见.md")
