#!/usr/bin/env python3
"""自检：Python、ffmpeg、Node/npx、HyperFrames CLI、Chrome、ElevenLabs key 和权限。
用法：python3 scripts/doctor.py"""
import json, shutil, subprocess, sys, urllib.request
from common import config, eleven_key, hf, SKILL

ok = True


def line(name, good, hint=""):
    global ok
    ok = ok and good
    print(("✅ " if good else "❌ ") + name + ("" if good else f"\n   → {hint}"))


def install_hint(pkg):
    if sys.platform == "darwin":
        return f"brew install {pkg}"
    if sys.platform.startswith("win"):
        return {"ffmpeg": "winget install Gyan.FFmpeg", "node": "winget install OpenJS.NodeJS.LTS"}.get(pkg, f"winget install {pkg}")
    return f"sudo apt install {pkg}"


line(f"Python {sys.version.split()[0]}", sys.version_info >= (3, 9), "需要 Python 3.9+")
line("ffmpeg / ffprobe", bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), install_hint("ffmpeg"))
line("Node.js / npx", bool(shutil.which("npx") or shutil.which("npx.cmd")), install_hint("node"))
if shutil.which("npx") or shutil.which("npx.cmd"):
    r = hf(["--version"], SKILL, capture=True)
    line("HyperFrames CLI " + (r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else ""), r.returncode == 0,
         "npx 第一次会自动下载 hyperframes；失败时检查网络，或运行 npx --yes hyperframes doctor")
key = eleven_key(required=False)
line("ElevenLabs key", bool(key), "config.json 填 elevenlabs_api_key 或设 ELEVENLABS_API_KEY；没有 key 只能用你自己录的配音")
if key:
    def get(url):
        req = urllib.request.Request(url, headers={"xi-api-key": key})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status
        except Exception as e:
            return getattr(e, "code", str(e))
    s = get("https://api.elevenlabs.io/v1/models")
    line("ElevenLabs 可用（模型列表）", s == 200, f"返回 {s}：key 无效或网络不通")
    s = get("https://api.elevenlabs.io/v1/shared-voices?page_size=1&language=zh")
    line("ElevenLabs 能搜音色（voices_read）", s == 200, "去 ElevenLabs → API Keys 给这个 key 勾上 Voices 读取；不勾也能配音，只是不能自动搜音色")
c = config()
print("\n当前配置：音色", c.get("voice_id"), "| 模型", c.get("tts_model"), "| HyperFrames", c.get("hyperframes_version"))
print("\n全部通过" if ok else "\n有未通过的项，按 → 后面的提示处理；用户同意后再执行安装命令")
sys.exit(0 if ok else 1)
