"""dei-capture 的语音转写引擎，供各平台模块和 transcribe.py 共用。

- whisper：本地转写（whisper.cpp 的 whisper-cli + ffmpeg），免费，适合本地文件；配置在 config 顶层 whisper 段
- paraformer：阿里云百炼录音文件转写，按时长计费，只收公网可访问的音视频直链；配置在 config 顶层 dashscope 段

两个引擎都返回 [(秒, 文本), ...] 句子列表，由调用方排版。
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from capture_paths import load_config  # noqa: E402

WHISPER_KEYS = ("whisper_model", "whisper_cmd", "whisper_language", "whisper_prompt")


def whisper_config() -> dict:
    """顶层 whisper 段；兼容旧版写在 youtube 段里的 whisper_* 配置。"""
    full = load_config()
    w = dict(full.get("whisper") or {})
    legacy = full.get("youtube") or {}
    for key in WHISPER_KEYS:
        short = key.removeprefix("whisper_")
        if not w.get(short) and legacy.get(key):
            w[short] = legacy[key]
    w.setdefault("cmd", "whisper-cli")
    w.setdefault("language", "auto")
    return w


def dashscope_config() -> dict:
    d = dict(load_config().get("dashscope") or {})
    d.setdefault("base_url", "https://dashscope.aliyuncs.com")
    d.setdefault("model", "paraformer-v2")
    d.setdefault("language_hints", ["zh", "en"])
    return d


def whisper_ready() -> tuple[bool, str]:
    w = whisper_config()
    model = w.get("model") or ""
    if not model or not Path(model).expanduser().is_file():
        return False, "未配置本地转写模型（config 的 whisper.model）"
    if not shutil.which(w["cmd"]) or not shutil.which("ffmpeg"):
        return False, f"本地转写需要 {w['cmd']} 和 ffmpeg"
    return True, model


def parse_srt(text: str) -> list[tuple[float, str]]:
    cues = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->", block)
        if not m:
            continue
        h, mi, s, ms = (int(x) for x in m.groups())
        lines = block.splitlines()
        at = next(i for i, line in enumerate(lines) if "-->" in line)
        body = " ".join(line.strip() for line in lines[at + 1:] if line.strip())
        if body:
            cues.append((h * 3600 + mi * 60 + s + ms / 1000, body))
    return cues


def whisper_file(media: Path, workdir: Path) -> list[tuple[float, str]]:
    """本地音视频文件 → 句子列表。"""
    ok, why = whisper_ready()
    if not ok:
        raise RuntimeError(why)
    w = whisper_config()
    wav = workdir / "audio16k.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(media), "-ar", "16000", "-ac", "1", str(wav)],
                   check=True)
    cmd = [w["cmd"], "-m", str(Path(w["model"]).expanduser()), "-f", str(wav), "-l", w.get("language") or "auto",
           "-osrt", "-of", str(workdir / "whisper")]
    if w.get("prompt"):
        cmd += ["--prompt", w["prompt"]]
    subprocess.run(cmd, check=True, capture_output=True)
    return parse_srt((workdir / "whisper.srt").read_text(encoding="utf-8", errors="replace"))


def _post(url: str, key: str, body: dict | None = None, extra: dict | None = None) -> dict:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", **(extra or {})}
    data = json.dumps(body or {}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method="POST"),
                                timeout=60) as r:
        return json.loads(r.read())


def paraformer_url(media_url: str, max_wait: int = 1800) -> tuple[list[tuple[float, str]], float | None]:
    """公网音视频直链 → (句子列表, 时长秒)。"""
    d = dashscope_config()
    key = (d.get("api_key") or "").strip()
    if not key:
        raise RuntimeError("未配置阿里云百炼 Key（config 顶层 dashscope.api_key，sk- 开头）")
    base = d["base_url"].rstrip("/")
    resp = _post(base + "/api/v1/services/audio/asr/transcription", key,
                 {"model": d["model"], "input": {"file_urls": [media_url]},
                  "parameters": {"channel_id": [0], "language_hints": d["language_hints"]}},
                 {"X-DashScope-Async": "enable"})
    task = (resp.get("output") or {}).get("task_id")
    if not task:
        raise RuntimeError(f"提交失败：{json.dumps(resp, ensure_ascii=False)[:200]}")
    deadline = time.time() + max_wait
    while time.time() < deadline:
        out = _post(f"{base}/api/v1/tasks/{task}", key).get("output") or {}
        status = out.get("task_status")
        if status == "SUCCEEDED":
            res = (out.get("results") or [{}])[0]
            if res.get("subtask_status") != "SUCCEEDED":
                raise RuntimeError(f"{res.get('code')}: {res.get('message', '')}")
            with urllib.request.urlopen(res["transcription_url"], timeout=120) as r:
                data = json.loads(r.read())
            tr = (data.get("transcripts") or [{}])[0]
            cues = [(s.get("begin_time", 0) / 1000, s.get("text", "")) for s in tr.get("sentences", [])]
            if not cues and tr.get("text"):
                cues = [(0.0, tr["text"])]
            ms = (data.get("properties") or {}).get("original_duration_in_milliseconds")
            return cues, (round(ms / 1000, 1) if ms else None)
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            raise RuntimeError(f"任务失败：{json.dumps(out, ensure_ascii=False)[:200]}")
        time.sleep(5)
    raise RuntimeError(f"转写超时（{max_wait} 秒），任务 ID {task}")


def paragraphs(cues: list[tuple[float, str]], span: int = 60) -> list[str]:
    """按约 span 秒合并成段，每段前面标 [m:ss]。"""
    out, start, buf = [], None, []
    for sec, text in cues:
        if start is None:
            start = sec
        if sec - start >= span and buf:
            out.append(f"[{int(start // 60)}:{int(start % 60):02d}] " + "".join(buf))
            start, buf = sec, []
        buf.append(text if re.search(r"[一-鿿]$", text) else text + " ")
    if buf:
        out.append(f"[{int(start // 60)}:{int(start % 60):02d}] " + "".join(buf).strip())
    return out
