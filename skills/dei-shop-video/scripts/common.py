"""dei-shop-video 各脚本共用：读配置、取 ElevenLabs key、调 HyperFrames CLI、UTF-8 输出。"""
import json, os, pathlib, shutil, subprocess, sys

SKILL = pathlib.Path(__file__).resolve().parent.parent
HF_VERSION_DEFAULT = "0.9.84"

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
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads((SKILL / "config.example.json").read_text(encoding="utf-8"))


def eleven_key(required=True):
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    c = config()
    if not k:
        k = (c.get("elevenlabs_api_key") or "").strip()
    if not k and c.get("elevenlabs_key_file"):
        f = pathlib.Path(os.path.expanduser(c["elevenlabs_key_file"]))
        if f.is_file():
            k = f.read_text(encoding="utf-8").strip()
    if not k and required:
        die("没有 ElevenLabs key：在 Skill 目录的 config.json 填 elevenlabs_api_key，或设环境变量 ELEVENLABS_API_KEY（见 references/setup.md）")
    return k


def project(path):
    d = pathlib.Path(path).resolve()
    pj = d / "project.json"
    if not pj.is_file():
        die(f"{d} 里没有 project.json（先运行 new.py 建工程）")
    return d, json.loads(pj.read_text(encoding="utf-8"))


def save_project(d, data):
    (d / "project.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def hf(args, cwd, capture=False):
    """运行 HyperFrames CLI：npx --yes hyperframes@<版本> <args>。Windows 上 npx 是 npx.cmd。"""
    ver = config().get("hyperframes_version") or HF_VERSION_DEFAULT
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        die("找不到 npx：先装 Node.js 18+（见 references/setup.md）")
    cmd = [npx, "--yes", f"hyperframes@{ver}"] + list(args)
    if capture:
        return subprocess.run(cmd, cwd=str(cwd), text=True, encoding="utf-8", errors="replace", capture_output=True)
    return subprocess.run(cmd, cwd=str(cwd))


def ffdur(p):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                  text=True, encoding="utf-8", errors="replace")
    return float(out.strip())


def open_file(p):
    p = str(p)
    if sys.platform == "darwin":
        subprocess.run(["open", p])
    elif sys.platform.startswith("win"):
        os.startfile(p)  # noqa
    else:
        subprocess.run(["xdg-open", p])
