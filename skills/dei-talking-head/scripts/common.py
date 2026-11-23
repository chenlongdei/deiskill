"""dei-talking-head 各脚本共用：配置、工程读写、ffmpeg / whisper / HyperFrames 调用、UTF-8 输出。"""
import json, os, pathlib, re, shutil, subprocess, sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
HF_VERSION_DEFAULT = "0.9.85"

if os.environ.get("PYTHONUTF8") != "1":
    os.environ["PYTHONUTF8"] = "1"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def die(msg, code=1):
    print("错误：" + msg, file=sys.stderr)
    sys.exit(code)


def config():
    p = SKILL / "config.json"
    base = json.loads((SKILL / "config.example.json").read_text(encoding="utf-8"))
    if p.is_file():
        base.update(json.loads(p.read_text(encoding="utf-8")))
    return base


def expand(p):
    return pathlib.Path(os.path.expanduser(p)) if p else None


def eleven_key(required=True):
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    c = config()
    if not k:
        k = (c.get("elevenlabs_api_key") or "").strip()
    if not k and c.get("elevenlabs_key_file"):
        f = expand(c["elevenlabs_key_file"])
        if f.is_file():
            k = f.read_text(encoding="utf-8").strip()
    if not k and required:
        die("没有 ElevenLabs key：config.json 填 elevenlabs_api_key / elevenlabs_key_file，或设 ELEVENLABS_API_KEY")
    return k


def project(path):
    d = pathlib.Path(path).resolve()
    pj = d / "plan.json"
    if not pj.is_file():
        die(f"{d} 里没有 plan.json（先运行 new.py 建工程）")
    return d, json.loads(pj.read_text(encoding="utf-8"))


def save_plan(d, plan):
    (d / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def run(cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def ffdur(p):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                  text=True, encoding="utf-8", errors="replace")
    return float(out.strip())


def silences(wav, db=-35, dur=0.12, ss=None, to=None):
    """ffmpeg silencedetect → [(start, end)]，秒"""
    cmd = ["ffmpeg", "-v", "info"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    if to is not None:
        cmd += ["-to", str(to)]
    cmd += ["-i", str(wav), "-vn", "-af", f"silencedetect=n={db}dB:d={dur}", "-f", "null", "-"]
    err = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    off = ss or 0
    out, s = [], None
    for line in err.splitlines():
        m = re.search(r"silence_start: (-?[\d.]+)", line)
        if m:
            s = float(m.group(1)) + off
        m = re.search(r"silence_end: (-?[\d.]+)", line)
        if m and s is not None:
            out.append((round(max(0, s), 3), round(float(m.group(1)) + off, 3)))
            s = None
    return out


def whisper_bin():
    c = config()
    b = c.get("whisper_cli") or shutil.which("whisper-cli") or shutil.which("whisper-cli.exe")
    if not b:
        die("找不到 whisper-cli（whisper.cpp），见 references/setup.md")
    return b


def whisper_model():
    m = expand(config().get("whisper_model") or "~/.cache/whisper-models/ggml-large-v3-turbo.bin")
    if not m.is_file():
        die(f"找不到 whisper 模型 {m}，见 references/setup.md")
    return m


def to16k(src, dst, ss=None, to=None):
    cmd = ["ffmpeg", "-v", "error", "-y"]
    if ss is not None:
        cmd += ["-ss", str(ss)]
    if to is not None:
        cmd += ["-to", str(to)]
    run(cmd + ["-i", src, "-vn", "-ar", "16000", "-ac", "1", dst])


def transcribe(wav16k, out_prefix, prompt="", segments=True):
    """whisper.cpp 中文转写。segments=True 输出 JSON（-ml 1 -sow：短语级时间）；False 只返回纯文本"""
    cmd = [whisper_bin(), "-m", whisper_model(), "-l", "zh", "-f", wav16k, "--prompt", "以下是简体中文普通话。" + (prompt or "")]
    if segments:
        cmd += ["-ml", "1", "-sow", "-ojf", "-of", out_prefix]
        subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace")
        return json.loads(pathlib.Path(str(out_prefix) + ".json").read_text(encoding="utf-8"))["transcription"]
    r = subprocess.run([str(c) for c in cmd + ["-nt"]], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return "".join(r.stdout.split())


def hf(args, cwd, capture=False):
    """HyperFrames CLI：npx --yes hyperframes@<版本> <args>。Windows 上 npx 是 npx.cmd"""
    ver = config().get("hyperframes_version") or HF_VERSION_DEFAULT
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        die("找不到 npx：先装 Node.js 18+（见 references/setup.md）")
    cmd = [npx, "--yes", f"hyperframes@{ver}"] + list(args)
    if capture:
        return subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace", capture_output=True)
    return subprocess.run(cmd, cwd=str(cwd))


def open_file(p):
    p = str(p)
    if sys.platform == "darwin":
        subprocess.run(["open", p])
    elif sys.platform.startswith("win"):
        os.startfile(p)  # noqa
    else:
        subprocess.run(["xdg-open", p])


def fmt(t):
    """秒 → m:ss.s"""
    return f"{int(t // 60)}:{t % 60:04.1f}"
