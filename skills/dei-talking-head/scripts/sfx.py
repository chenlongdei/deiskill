#!/usr/bin/env python3
"""音效：scenes.py 用到、工程里还没有的音效，补齐成 work/sfx/<名>.wav（48 kHz 立体声）。两个来源：
  - mixkit（免费，不用账号）：templates/sfx_prompts.json 里每种音效配好了一条 Mixkit 免费可商用音效，运行时下载、裁到需要的长度
  - elevenlabs（要 key，按提示词现生成，更贴合）
默认 auto：配了 ElevenLabs key 用它，没配就走 Mixkit。分享给别人时对方不需要任何付费账号。
有本地可商用音效库的，同名 wav 放进 work/sfx/ 就不再生成。

用法：
  python3 scripts/sfx.py <工程> [--source auto|mixkit|elevenlabs]   补齐缺的
  python3 scripts/sfx.py <工程> --name typing --prompt "..." --dur 2.8   单独生成 / 替换一个
"""
import argparse, json, subprocess, urllib.error, urllib.request
from common import SKILL, eleven_key, project, die


def from_mixkit(path, mid, dur):
    """Mixkit 免费音效（Mixkit Sound Effects Free License，可商用、不需署名；不能原样再分发，所以不放进仓库，用时下载）"""
    url = f"https://assets.mixkit.co/active_storage/sfx/{mid}/{mid}-preview.mp3"
    tmp = path.with_suffix(".mp3")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            tmp.write_bytes(r.read())
    except Exception as e:
        die(f"Mixkit 音效 {mid} 下载失败：{e}；可以自己下一个同名 wav 放进 work/sfx/")
    fade = max(.05, dur - .25)
    # 去掉开头的静音再裁长度
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-ar", "48000", "-ac", "2", "-af",
                    f"silenceremove=start_periods=1:start_threshold=-45dB,atrim=0:{dur},afade=t=in:d=0.005,afade=t=out:st={fade}:d=0.25",
                    str(path)], check=True)
    tmp.unlink()


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
ap.add_argument("--source", choices=["auto", "mixkit", "elevenlabs"], default="auto")
ap.add_argument("--mixkit", type=int, help="和 --name 一起用：换成这个 Mixkit 音效编号（mixkit.co/free-sound-effects/ 页面上的数字）")
a = ap.parse_args()
SRC = a.source if a.source != "auto" else ("elevenlabs" if eleven_key(required=False) else "mixkit")
print("音效来源：", "ElevenLabs 生成" if SRC == "elevenlabs" else "Mixkit 免费音效")


def make(f, n, prompt=None, dur=None):
    item = lib.get(n, {})
    dur = dur or item.get("dur", 1.0)
    if SRC == "elevenlabs" and (prompt or item.get("prompt")):
        gen(f, prompt or item["prompt"], dur)
    elif item.get("mixkit"):
        from_mixkit(f, item["mixkit"]["id"], dur)
    else:
        die(f"{n} 没有配 Mixkit 音效：用 --name {n} --mixkit <编号>，或放一个同名 wav 进 work/sfx/")

d, plan = project(a.project)
folder = d / "work/sfx"
folder.mkdir(parents=True, exist_ok=True)
lib = json.loads((SKILL / "templates/sfx_prompts.json").read_text(encoding="utf-8"))
if a.name:
    if a.mixkit:
        from_mixkit(folder / f"{a.name}.wav", a.mixkit, a.dur)
    elif not a.prompt and a.name not in lib:
        die("新音效要给 --prompt（英文描述，结尾加 no music，走 ElevenLabs）或 --mixkit <编号>")
    else:
        make(folder / f"{a.name}.wav", a.name, a.prompt, a.dur if a.prompt else None)
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
            make(f, n)
            print("已生成", n, "—", lib[n]["用在"])
        else:
            print(f"⚠ {n} 不在 sfx_prompts.json：用 --name {n} --prompt \"...\" 生成，或放一个同名 wav 进 work/sfx/")
