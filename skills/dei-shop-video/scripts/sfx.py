#!/usr/bin/env python3
"""音效包：按 templates/sfx_prompts.json 用 ElevenLabs 音效生成，存到 <工程>/<sfx_dir>/，统一峰值到 -3 dB。
已有的文件跳过；也可以把本地音效库里的文件直接放进去（同名即可）。

用法：
  python3 scripts/sfx.py <工程>                      生成 project.json 里 sfx 用到、但还没有的音效
  python3 scripts/sfx.py <工程> --name kaching --prompt "..." --dur 1.2   单独生成/替换一个
"""
import argparse, json, re, subprocess, urllib.request
from common import SKILL, eleven_key, project, die


def gen(path, prompt, dur):
    body = json.dumps({"text": prompt, "duration_seconds": max(0.5, dur), "prompt_influence": 0.6}).encode("utf-8")
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128", data=body,
                                 headers={"xi-api-key": eleven_key(), "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        die(f"音效生成失败 {e.code}：{e.read().decode('utf-8','replace')[:200]}")
    tmp = path.with_suffix(".raw.mp3")
    tmp.write_bytes(raw)
    out = subprocess.run(["ffmpeg", "-i", str(tmp), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.search(r"max_volume: (-?[\d.]+) dB", out)
    gain = -3 - float(m.group(1)) if m else 0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", f"volume={gain}dB", "-ar", "44100", str(path)], check=True)
    tmp.unlink()


ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--name"); ap.add_argument("--prompt"); ap.add_argument("--dur", type=float, default=1.0)
a = ap.parse_args()
d, P = project(a.project)
folder = d / P.get("sfx_dir", "assets/audio/sfx")
folder.mkdir(parents=True, exist_ok=True)
lib = json.loads((SKILL / "templates/sfx_prompts.json").read_text(encoding="utf-8"))
if a.name:
    if not a.prompt and a.name not in lib:
        die("新音效要给 --prompt（英文描述效果更稳，结尾加 no music）")
    gen(folder / f"{a.name}.mp3", a.prompt or lib[a.name]["prompt"], a.dur if a.prompt else lib[a.name]["dur"])
    print("已生成", a.name)
else:
    need = sorted({s["name"] for s in P.get("sfx", [])})
    for n in need:
        f = folder / f"{n}.mp3"
        if f.exists():
            print("已有", n)
            continue
        if n not in lib:
            print(f"⚠ {n} 不在 sfx_prompts.json 里：用 --name {n} --prompt \"...\" 单独生成，或放本地音效进来")
            continue
        gen(f, lib[n]["prompt"], lib[n]["dur"])
        print("已生成", n, "—", lib[n]["用在"])
