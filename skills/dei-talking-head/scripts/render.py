#!/usr/bin/env python3
"""出片：HyperFrames 本地渲染 → 两遍 loudnorm 到目标响度（默认 -14 LUFS）→ 成片/<名字>.mp4。旧版不覆盖。

用法：python3 scripts/render.py <工程> --name 口播_v1 [--open]
"""
import argparse, json, re, subprocess
from common import project, hf, die, run, ffdur, fmt, open_file

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--name", required=True)
ap.add_argument("--open", action="store_true")
a = ap.parse_args()
d, plan = project(a.project)
out = d / "成片" / f"{a.name}.mp4"
if out.exists():
    die(f"{out} 已存在：换个版本号（旧版不覆盖）")
raw = d / "work" / f"{a.name}_未标准化.mp4"
if hf(["render", "--quality", "delivery", "--output", str(raw)], d / "hf").returncode or not raw.exists():
    die("渲染失败：先跑 build.py 看检查结果")

target = plan.get("loudness", -14)
err = subprocess.run(["ffmpeg", "-v", "info", "-i", str(raw), "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                     capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
m = json.loads(err[err.rfind("{"):err.rfind("}") + 1])
af = (f"loudnorm=I={target}:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
      f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
out.parent.mkdir(exist_ok=True)
run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-c:v", "copy", "-af", af, "-ar", "48000", "-c:a", "aac", "-b:a", "256k", out])
e2 = subprocess.run(["ffmpeg", "-i", str(out), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", e2)
print(f"成片：{out}  {fmt(ffdur(out))}  {lufs[-1] if lufs else '?'} LUFS")
print("下一步：python3 scripts/review.py", d, "--video", out, "（Gemini 听审）")
if a.open:
    open_file(out)
