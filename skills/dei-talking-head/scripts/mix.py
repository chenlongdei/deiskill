#!/usr/bin/env python3
"""音频床：音效 + 配乐 → hf/assets/sfx.wav（人声单独一条 voice.wav，不进这里）。
配乐：先把曲子自身的响度起伏拉平；人声在说话时压到 bgm_talk，停顿时 bgm_gap（两者只差约 2 dB，停顿时音乐不「涌」上来），
口播结束后抬到 bgm_end；约 1 秒平滑。音效按「相对人声 RMS」定音量，宁轻勿冲。

用法：python3 scripts/mix.py <工程>
可调（plan.json）：bgm（配乐文件路径）、bgm_talk / bgm_gap / bgm_end（相对人声 dB，默认 -25 / -23 / -16）、sfx_levels（如 {"pop": -20}）
"""
import json, subprocess, sys
from common import project, die

try:
    import numpy as np, soundfile as sf
except ImportError:
    die("缺 numpy / soundfile：pip install numpy soundfile（见 references/setup.md）")

d, plan = project(sys.argv[1] if len(sys.argv) > 1 else ".")
SR = 48000
ev = json.loads((d / "work/sfx_events.json").read_text(encoding="utf-8"))
DUR, AROLL = ev["dur"], ev["aroll"]
LEVEL = dict(whoosh=-17, pop=-18, tap=-20, ding=-19, strike=-16, sparkle=-20, text_slam=-19, riser=-20, impact=-20, typing=-26)
LEVEL.update(plan.get("sfx_levels", {}))

voice, vsr = sf.read(str(d / "hf/assets/voice.wav"))
if voice.ndim > 1:
    voice = voice.mean(1)
v_rms = np.sqrt(np.mean(voice[np.abs(voice) > 1e-3] ** 2))

N = int(DUR * SR)
out = np.zeros((N + SR * 3, 2), np.float32)
used, missing = {}, set()
for e in ev["ev"]:
    k = e["kind"]
    f = d / "work/sfx" / f"{k}.wav"
    if not f.is_file():
        missing.add(k); continue
    x, sr = sf.read(str(f), always_2d=True)
    if sr != SR:
        die(f"{f.name} 不是 48 kHz：用 sfx.py 重新生成或先转码")
    if x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    m = x.mean(1); act = m[np.abs(m) > np.abs(m).max() * .05]
    x = (x * (v_rms * 10 ** (LEVEL.get(k, -20) / 20) / max(np.sqrt(np.mean(act ** 2)), 1e-6) * e.get("v", 1.0))).astype(np.float32)
    i = int(e["t"] * SR)
    out[i:i + len(x)] += x[:len(out) - i]
    used[k] = used.get(k, 0) + 1
out = out[:N]
if missing:
    print("⚠ 缺音效（先跑 sfx.py）：", ", ".join(sorted(missing)))

bgm = plan.get("bgm")
if bgm:
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", bgm, "-t", str(DUR + 1), "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"],
                         capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.float32).reshape(-1, 2)[:N].copy()
    if len(m) < N:   # 曲子比片子短：循环
        m = np.tile(m, (N // max(len(m), 1) + 1, 1))[:N]
    win = SR * 4
    cs = np.concatenate([[0], np.cumsum(m.mean(1) ** 2)])
    idx = np.arange(0, N, SR // 10)
    lo, hi = np.clip(idx - win // 2, 0, N), np.clip(idx + win // 2, 0, N)
    env = np.sqrt((cs[hi] - cs[lo]) / np.maximum(hi - lo, 1)) + 1e-6
    env = np.maximum(env, np.median(env) * .3)
    m = m * np.interp(np.arange(N), idx, np.median(env) / env).astype(np.float32)[:, None]
    m_rms = np.sqrt(np.mean(m ** 2))
    hop = vsr // 20
    venv = np.sqrt(np.convolve(voice ** 2, np.ones(hop) / hop, 'same'))[::hop]
    talk = np.convolve((venv > v_rms * .1).astype(float), np.ones(11), 'same') > 0
    db = np.where(talk, plan.get("bgm_talk", -25), plan.get("bgm_gap", -23)).astype(float)
    tc = np.arange(len(db)) / 20
    db[tc >= AROLL] = plan.get("bgm_end", -16)
    db = np.convolve(np.pad(db, 10, mode='edge'), np.ones(21) / 21, 'valid')
    g = np.interp(np.arange(N) / SR, tc, v_rms * 10 ** (db / 20) / m_rms, right=v_rms * 10 ** (db[-1] / 20) / m_rms).astype(np.float32)
    fade = np.clip(np.arange(N) / (SR * 1.5), 0, 1) * np.clip((DUR - np.arange(N) / SR) / 1.2, 0, 1)
    out += m * (g * fade)[:, None]
else:
    print("⚠ plan.json 没有 bgm：这一版没有配乐")

peak = float(np.abs(out).max())
if peak > .5:
    out *= .5 / peak
sf.write(str(d / "hf/assets/sfx.wav"), out, SR, subtype="PCM_16")
print("sfx.wav", round(N / SR, 1), "秒；音效", used, "；峰值", round(peak, 3))
