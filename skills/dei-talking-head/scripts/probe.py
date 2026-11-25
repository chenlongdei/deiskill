#!/usr/bin/env python3
"""试刀口：把原片里两段接起来转写一遍，看接缝处有没有吞字、多出半个字。下刀前、改刀口时都用它。

用法：
  python3 scripts/probe.py <工程> 17.7 21.85 47.3 49      # 原片 17.7–21.85 接 47.3–49，转写一遍
  python3 scripts/probe.py <工程> --near 128.0            # 列出 128 秒前后 1.5 秒的细静音（-38 dB / 0.06 秒），找能下刀的空隙
  python3 scripts/probe.py <工程> --say 128.9 129.6       # 单独听写一小段，看里面到底说了什么
规矩：刀口要落在静音里；被删的词不能留尾音，留下的词不能被削掉尾巴。
"""
import argparse, pathlib, subprocess
from common import project, transcribe, silences, whisper_bin, whisper_model

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("times", nargs="*", type=float)
ap.add_argument("--near", type=float)
ap.add_argument("--say", nargs=2, type=float)
a = ap.parse_args()
d, plan = project(a.project)
src = next((d / "source").glob("原片.*"))
tmp = d / "work/probe.wav"

if a.near is not None:
    for s, e in silences(src, None, 0.06, ss=max(0, a.near - 1.5), to=a.near + 1.5):
        print(f"静音 {s:.2f}–{e:.2f}（{e - s:.2f} 秒）")
elif a.say:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.say[0]), "-to", str(a.say[1]), "-i", str(src), "-ar", "16000", "-ac", "1", str(tmp)], check=True)
    print(transcribe(tmp, None, "、".join(plan.get("names", [])), segments=False))
else:
    if len(a.times) < 4 or len(a.times) % 2:
        raise SystemExit("给偶数个时间：a1 b1 a2 b2 [a3 b3 ...]")
    pairs = list(zip(a.times[::2], a.times[1::2]))
    fc = "".join(f"[0:a]atrim={x}:{y},asetpts=PTS-STARTPTS[a{i}];" for i, (x, y) in enumerate(pairs))
    fc += "".join(f"[a{i}]" for i in range(len(pairs))) + f"concat=n={len(pairs)}:v=0:a=1,aresample=16000[o]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", fc, "-map", "[o]", "-ac", "1", str(tmp)], check=True)
    print(transcribe(tmp, None, "、".join(plan.get("names", [])), segments=False))
