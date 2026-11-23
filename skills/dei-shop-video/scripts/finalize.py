#!/usr/bin/env python3
"""出片：build → check → 截帧 → 渲染 → 响度标准化 →（可选）整片语音核对。

用法：
  python3 scripts/finalize.py <工程> --out <成片.mp4> [--lufs -11] [--snap-only] [--verify]

  --snap-only  只生成并检查、截关键帧（看画面用），不渲染
  --verify     成片出来后用语音识别把整条口播再核对一遍（要 ElevenLabs key）
"""
import argparse, json, pathlib, re, subprocess, sys
from common import project, hf, die, config, open_file

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--out")
ap.add_argument("--lufs", type=float)
ap.add_argument("--snap-only", action="store_true")
ap.add_argument("--verify", action="store_true")
a = ap.parse_args()
d, P = project(a.project)
here = pathlib.Path(__file__).parent

r = subprocess.run([sys.executable, str(here / "build.py"), str(d)])
if r.returncode:
    sys.exit(r.returncode)
r = hf(["check"], d, capture=True)
tail = r.stdout + r.stderr
errs = [l for l in tail.splitlines() if "✗" in l]
if errs:
    print("\n".join(errs[:20]))
    die("HyperFrames 检查有错误，先改 project.json 再出片")
print("检查通过")

# 关键帧：每句开头 + 片尾
html = (d / "index.html").read_text(encoding="utf-8")
starts = [float(x) for x in re.findall(r'<audio id="vo\d+" class="clip" src="[^"]+" data-start="([\d.]+)"', html)]
total = float(re.search(r'data-composition-id="main" data-start="0" data-duration="([\d.]+)"', html).group(1))
pts = sorted({0.0, 0.5, 1.5, 3.0, 4.5} | {round(s + 0.6, 2) for s in starts} | {round(total - 0.3, 2)})
r = hf(["snapshot", "--at", ",".join(str(p) for p in pts)], d, capture=True)
m = re.findall(r"(\S*contact-sheet[^\s]*\.jpg)", r.stdout)
print("关键帧拼图：", "\n  ".join(m) if m else "(没生成，看 .hyperframes/artifacts/snapshots/)")
if a.snap_only:
    sys.exit(0)

if not a.out:
    die("给 --out 成片路径")
out = pathlib.Path(a.out).expanduser().resolve()
out.parent.mkdir(parents=True, exist_ok=True)
raw = out.with_name(out.stem + "_raw.mp4")
r = hf(["render", "-o", str(raw)], d)
if r.returncode or not raw.is_file():
    die("渲染失败，看上面的输出")
lufs = a.lufs if a.lufs is not None else config().get("loudness_lufs", -11)
subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-c:v", "copy", "-af",
                f"acompressor=threshold=-20dB:ratio=3:attack=5:release=100:makeup=3dB,loudnorm=I={lufs}:TP=-1.0:LRA=7",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)], check=True)
raw.unlink()
s = subprocess.run(["ffmpeg", "-i", str(out), "-af", "loudnorm=print_format=summary", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
m = re.search(r"Input Integrated:\s+(-?[\d.]+)", s)
print(f"成片：{out}  响度 {m.group(1) if m else '?'} LUFS")

if a.verify:
    wav = out.with_suffix(".verify.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(out), "-vn", "-ac", "1", "-ar", "16000", str(wav)], check=True)
    subprocess.run([sys.executable, str(here / "tts.py"), "check", str(wav), "".join(P["lines"])])
    wav.unlink()
open_file(out)
