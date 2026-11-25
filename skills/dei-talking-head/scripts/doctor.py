#!/usr/bin/env python3
"""自检：Python 包、ffmpeg、whisper.cpp 和模型、Node/npx（HyperFrames）、字体、ElevenLabs key、审片工具 agy。
用法：python3 scripts/doctor.py"""
import shutil, sys
from common import config, eleven_key, hf, SKILL, expand

ok = True
def line(name, good, hint="", need=True):
    global ok
    if need:
        ok = ok and good
    print(("✅ " if good else ("❌ " if need else "⚪ ")) + name + ("" if good else f"\n   → {hint}"))

mac, win = sys.platform == "darwin", sys.platform.startswith("win")
c = config()
line(f"Python {sys.version.split()[0]}", sys.version_info >= (3, 9), "需要 Python 3.9+")
for mod in ("jieba", "numpy", "soundfile"):
    try:
        __import__(mod); line(mod, True)
    except ImportError:
        line(mod, False, f"{sys.executable} -m pip install jieba numpy soundfile")
line("ffmpeg / ffprobe", bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
     "brew install ffmpeg" if mac else ("winget install Gyan.FFmpeg" if win else "sudo apt install ffmpeg"))
wc = c.get("whisper_cli") or shutil.which("whisper-cli") or shutil.which("whisper-cli.exe")
line("whisper.cpp（whisper-cli）", bool(wc), "brew install whisper-cpp；Windows 从 github.com/ggml-org/whisper.cpp 的 Releases 下载")
m = expand(c.get("whisper_model") or "~/.cache/whisper-models/ggml-large-v3-turbo.bin")
line(f"whisper 模型 {m.name}", m.is_file(), "下载 ggml-large-v3-turbo.bin（约 1.6 GB）放到 config.json 的 whisper_model，见 references/setup.md")
npx = shutil.which("npx") or shutil.which("npx.cmd")
line("Node.js / npx", bool(npx), "brew install node" if mac else ("winget install OpenJS.NodeJS.LTS" if win else "sudo apt install nodejs npm"))
if npx:
    r = hf(["--version"], SKILL, capture=True)
    line("HyperFrames CLI", r.returncode == 0, "npx 第一次会自动下载；失败时检查网络")
for k in ("font_bold", "font_black", "font_number"):
    p = expand(c.get(k) or "")
    line(f"字体 {k}", bool(c.get(k)) and p.is_file(), "config.json 填字体文件路径（推荐阿里巴巴普惠体 Bold / Black、抖音美好体）", need=False)
line("ElevenLabs key（生成音效）", bool(eleven_key(required=False)), "没有也能剪：sfx.py 自动用 Mixkit 免费可商用音效，或放你自己的音效进工程 work/sfx/", need=False)
line("审片工具 agy（Gemini 听审）", bool(c.get("reviewer_cli") or shutil.which("agy")), "装 Antigravity CLI 并登录 Google；没有就跳过听审，由你自己逐刀听", need=False)
print("\n" + ("全部就绪" if ok else "有必需项没装好，按上面的提示补齐（安装前先问用户）"))
