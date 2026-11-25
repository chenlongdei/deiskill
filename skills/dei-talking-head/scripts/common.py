"""dei-talking-head 各脚本共用：配置、工程读写、ffmpeg / whisper / HyperFrames 调用、UTF-8 输出。"""
import array, json, math, os, pathlib, re, shutil, subprocess, sys

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


def loudness(wav):
    """整段的综合响度（LUFS，ffmpeg ebur128）；量不出来时返回 None。"""
    err = subprocess.run(["ffmpeg", "-nostats", "-i", str(wav), "-vn", "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(m[-1]) if m else None


def silence_db(wav, ratio=.45, lo=-58, hi=-30):
    """静音门限跟着这条录音走：底噪（50 ms 窗 RMS 的第 10 百分位）往上，
    到说话声（第 90 百分位）的 45% 处，夹在 [lo, hi]。
    写死 -35 dB 时，录得小声的原片（实测一条底噪 -61、说话 -34 dB，句尾轻声 -42~-47 dB）
    句尾会被当成静音，剪出来「话还没说完就切了」；按这个算法那条是 -48.8 dB。"""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-vn", "-f", "s16le", "-ac", "1", "-ar", "8000", "-"],
                         capture_output=True).stdout
    a = array.array("h"); a.frombytes(raw[:len(raw) // 2 * 2])
    n = 400   # 50 ms @ 8 kHz
    dbs = sorted(10 * math.log10(sum(x * x for x in a[i:i + n]) / n / 32768 ** 2 + 1e-12) for i in range(0, len(a) - n, n))
    if len(dbs) < 20:
        return -35.0
    p10, p90 = dbs[len(dbs) // 10], dbs[len(dbs) * 9 // 10]
    return round(max(lo, min(hi, p10 + ratio * (p90 - p10))), 1)


def silences(wav, db=None, dur=0.12, ss=None, to=None):
    """ffmpeg silencedetect → [(start, end)]，秒；db 不给就按这条录音的响度自适应（silence_db）"""
    if db is None:
        db = silence_db(wav)
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


_VENC = []
def venc(crf=16):
    """中间视频的编码参数。macOS 有 VideoToolbox 硬件编码就用它（实测 45 秒竖屏 28 秒 → 6 秒），
    否则 libx264 veryfast。config.json 的 video_encoder 可指定 "x264" / "videotoolbox"。"""
    if not _VENC:
        want = (config().get("video_encoder") or "auto").lower()
        hw = False
        if want in ("auto", "videotoolbox") and sys.platform == "darwin":
            r = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            hw = "h264_videotoolbox" in r.stdout
        _VENC.append(hw)
    if _VENC[0]:
        return ["-c:v", "h264_videotoolbox", "-b:v", "24M", "-maxrate", "30M", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast", "-pix_fmt", "yuv420p"]


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
