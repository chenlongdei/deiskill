#!/usr/bin/env python3
"""音效：scenes.py 用到、工程里还没有的音效，按 templates/sfx_prompts.json 用 ElevenLabs 生成，存成 work/sfx/<名>.wav（48 kHz 立体声）。
有本地可商用音效库的，同名 wav 放进 work/sfx/ 就不再生成。

用法：
  python3 scripts/sfx.py <工程>                                   补齐缺的
  python3 scripts/sfx.py <工程> --name typing --prompt "..." --dur 2.8   单独生成 / 替换一个
"""
import argparse, json, subprocess, urllib.error, urllib.request
from common import SKILL, eleven_key, project, die


def gen(path, prompt, dur):
    body = json.dumps({"text": prompt, "duration_seconds": max(.5, dur), "prompt_influence": .6}).encode("utf-8")
    req = urllib.request.Request("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_128", data=body,
                                 headers={"xi-api-key": eleven_key(), "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        die(f"音效生成失败 {e.code}：{e.read().decode('utf-8', 'replace')[:200]}")
    tmp = path.with_suffix(".mp3")
    tmp.write_bytes(raw)
    fade = max(.05, dur - .3)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-ar", "48000", "-ac", "2",
                    "-af", f"afade=t=in:d=0.01,afade=t=out:st={fade}:d=0.3", str(path)], check=True)
    tmp.unlink()


ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--name"); ap.add_argument("--prompt"); ap.add_argument("--dur", type=float, default=1.0)
a = ap.parse_args()
d, plan = project(a.project)
folder = d / "work/sfx"
folder.mkdir(parents=True, exist_ok=True)
lib = json.loads((SKILL / "templates/sfx_prompts.json").read_text(encoding="utf-8"))
if a.name:
    if not a.prompt and a.name not in lib:
        die("新音效要给 --prompt（英文描述，结尾加 no music）")
    gen(folder / f"{a.name}.wav", a.prompt or lib[a.name]["prompt"], a.dur if a.prompt else lib[a.name]["dur"])
    print("已生成", a.name)
else:
    evp = d / "work/sfx_events.json"
    if not evp.is_file():
        die("先运行 build.py（它会列出用到哪些音效）")
    need = sorted({e["kind"] for e in json.loads(evp.read_text(encoding="utf-8"))["ev"]})
    for n in need:
        f = folder / f"{n}.wav"
        if f.exists():
            print("已有", n)
        elif n in lib:
            gen(f, lib[n]["prompt"], lib[n]["dur"])
            print("已生成", n, "—", lib[n]["用在"])
        else:
            print(f"⚠ {n} 不在 sfx_prompts.json：用 --name {n} --prompt \"...\" 生成，或放一个同名 wav 进 work/sfx/")
