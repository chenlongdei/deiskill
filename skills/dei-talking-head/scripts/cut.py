#!/usr/bin/env python3
"""按 plan.json 剪：语义保留段 ∩ 说话段 → 句间收气口 → 提速（音高不变）→ 人声处理 → 重新转写 → 中文字幕分组。
同时写 删改清单.md（给用户审）和 刀口核对.md（每个语义刀口前后转写一遍）。

用法：python3 scripts/cut.py <工程> [--no-verify]
产出：hf/assets/aroll.mp4（画面）、hf/assets/voice.wav（人声）、work/edl.json、work/captions.json
第一次剪的 edl 另存为 work/edl_base.json：scenes.py 里写死的时间都按它算，以后改剪辑，build.py 会自动把动画挪到新位置。
"""
import argparse, json, re, shutil, subprocess
from common import project, venc, run, ffdur, silences, to16k, transcribe, fmt, die

VOICE_CHAIN = ("highpass=f=75,afftdn=nr=10:nf=-50:tn=1,volume=12dB,equalizer=f=280:t=q:w=1.2:g=-2.5,"
               "equalizer=f=3800:t=q:w=0.9:g=4,highshelf=f=9000:g=2.5,deesser=i=0.35,"
               "acompressor=threshold=-20dB:ratio=3:attack=8:release=120:knee=4,alimiter=limit=0.7:level=false")

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--no-verify", action="store_true")
a = ap.parse_args()
d, plan = project(a.project)
src = next((d / "source").glob("原片.*"))
W = d / "work"
speech = json.loads((W / "speech.json").read_text(encoding="utf-8"))
PAD, SPEED, GAP = plan.get("pad", .07), plan.get("speed", 1.1), plan.get("split_gap", .45)
# 句尾多留一点：中文句尾常是降调轻声，能量低、拖得长，只留 0.07 秒容易把最后一个字削掉
PAD_TAIL = plan.get("pad_tail", .15)
NO_SPLIT = plan.get("no_split", [])
keep = sorted(plan["keep"], key=lambda k: k[0])

# 1. 每个保留段内，只留说话段（前面留 PAD、后面留 PAD_TAIL 的气口）
segs = []
for ki, (k0, k1, *_) in enumerate(keep):
    for s, e in speech:
        s2, e2 = max(k0, s - PAD), min(k1, e + PAD_TAIL)
        if e2 - s2 > .12:
            segs.append([round(s2, 3), round(e2, 3), ki])
# 保留段两头：plan 里写到哪就剪到哪（差 0.15 秒以内时）——用来给尾字留余量、把入点放进静音
for ki, (k0, k1, *_) in enumerate(keep):
    mine = [sg for sg in segs if sg[2] == ki]
    if mine and 0 < mine[0][0] - k0 < .15: mine[0][0] = k0
    if mine and 0 < k1 - mine[-1][1] < .15: mine[-1][1] = k1
# 2. 句中小停顿不切：同一保留段里，间隔 < split_gap（或落在 no_split 里）就并成一段
m = [segs[0]]
for s, e, ki in segs[1:]:
    g = s - m[-1][1]
    if ki == m[-1][2] and (g < GAP or any(x <= s <= y for x, y in NO_SPLIT)):
        m[-1][1] = e
    else:
        m.append([s, e, ki])
segs = m

# 3. 剪（画面 + 原声，每段两头 12–15 ms 淡入淡出防爆音）
fc = []
for i, (s, e, _) in enumerate(segs):
    fc.append(f"[0:v]trim={s}:{e},setpts=PTS-STARTPTS[v{i}];")
    fc.append(f"[0:a]atrim={s}:{e},asetpts=PTS-STARTPTS,afade=t=in:d=0.012,afade=t=out:st={e - s - .015:.3f}:d=0.015[a{i}];")
fc.append("".join(f"[v{i}][a{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=1[v][a]")
fp = W / "cut.filter"
fp.write_text("".join(fc), encoding="utf-8")
base = ["ffmpeg", "-v", "error", "-y", "-i", src]
tail = ["-map", "[v]", "-map", "[a]"] + venc(16) + ["-g", "30", "-c:a", "aac", "-b:a", "256k", W / "cut.mp4"]
r = subprocess.run([str(x) for x in base + ["-/filter_complex", fp] + tail], capture_output=True, text=True)
if r.returncode:  # ffmpeg 8 及以前没有 -/filter_complex
    run(base + ["-filter_complex_script", fp] + tail)

# 4. 提速 + 人声处理
run(["ffmpeg", "-v", "error", "-y", "-i", W / "cut.mp4", "-an", "-vf", f"setpts=PTS/{SPEED}", "-r", "30"] + venc(15) + ["-g", "30", d / "hf/assets/aroll.mp4"])
run(["ffmpeg", "-v", "error", "-y", "-i", W / "cut.mp4", "-vn", "-ac", "1", "-ar", "48000", "-af", f"atempo={SPEED}," + plan.get("voice_chain", VOICE_CHAIN),
     "-c:a", "pcm_s16le", d / "hf/assets/voice.wav"])
to16k(d / "hf/assets/voice.wav", W / "v16k.wav")

t, mp = 0.0, []
for s, e, ki in segs:
    mp.append(dict(src=[s, e], out=[round(t, 3), round(t + e - s, 3)], keep=ki))
    t += e - s
edl = dict(speed=SPEED, segments=mp, duration=round(t, 3), aroll=round(t / SPEED - .02, 2))
(W / "edl.json").write_text(json.dumps(edl, ensure_ascii=False, indent=1), encoding="utf-8")
if not (W / "edl_base.json").exists():
    shutil.copy2(W / "edl.json", W / "edl_base.json")

# 5. 删改清单
srcdur = ffdur(src)
L = [f"# 删改清单", "", f"原片 {fmt(srcdur)} → 剪后 {fmt(t)} → 提速 {SPEED} 倍后 {fmt(t / SPEED)}", "", "## 删掉的", "", "| 原片时间 | 内容 / 理由 |", "| --- | --- |"]
for c in plan.get("cut", []):
    L.append(f"| {c[0]:.2f}–{c[1]:.2f} | {c[2] if len(c) > 2 else ''} |")
L += ["", "## 保留的", "", "| 原片时间 | 内容 |", "| --- | --- |"]
for k in keep:
    L.append(f"| {k[0]:.2f}–{k[1]:.2f} | {k[2] if len(k) > 2 else ''} |")
L += ["", f"另外：每个保留段内去掉了 {GAP} 秒以上的停顿，每刀留 {PAD} 秒气口；句中更短的停顿不切。"]
(d / "删改清单.md").write_text("\n".join(L) + "\n", encoding="utf-8")

# 6. 重新转写剪后的人声 → 字幕分组
names = plan.get("names", [])
tr = transcribe(W / "v16k.wav", W / "tr", "、".join(names) + "。" if names else "")
sil = silences(W / "v16k.wav", None, .12)
import jieba  # noqa: E402  只有这一步要 jieba
jieba.setLogLevel(60)
MAXW = plan.get("caption_max", 11)
BAD_HEAD = ('的', '了', '到', '不到', '中', '嘛', '来', '式', '上', '起来', '进行')
BAD_TAIL = ('在', '把', '以', '和', '对', '这', '那', '一个', '的话')
def w(s): return sum(.55 if re.match(r'[A-Za-z0-9 ]', ch) else 1 for ch in s)
def split(p):
    if w(p) <= MAXW:
        return [p]
    toks = list(jieba.cut(p)); best = None
    for i in range(1, len(toks)):
        Lp, Rp = ''.join(toks[:i]), ''.join(toks[i:])
        sc = abs(w(Lp) - w(Rp)) + (4 if toks[i] in BAD_HEAD else 0) + (4 if toks[i - 1] in BAD_TAIL else 0)
        if best is None or sc < best[0]:
            best = (sc, Lp, Rp)
    return split(best[1]) + split(best[2])
FIX = [tuple(x) for x in plan.get("caption_fixes", [])]
groups = []
for sg in tr:
    t0, t1 = sg["offsets"]["from"] / 1000, sg["offsets"]["to"] / 1000
    txt = sg["text"].strip()
    for x, y in FIX:
        txt = txt.replace(x, y)
    for s, e in sil:
        if abs(e - t0) < .35: t0 = e - .02
        if abs(s - t1) < .35: t1 = s + .05
    parts = [q for p in re.split(r'[，,。？?！!；;]', txt) if p.strip() for q in split(p.strip())]
    if not parts:
        continue
    Wt = [w(p) for p in parts]; tot = sum(Wt); tt = t0; bounds = [t0]
    for x in Wt[:-1]:
        tt += (t1 - t0) * x / tot
        cands = [(abs((s + e) / 2 - tt), (s + e) / 2) for s, e in sil if t0 < s < t1 and abs((s + e) / 2 - tt) < .45]
        if cands: tt = min(cands)[1]
        bounds.append(tt)
    bounds.append(t1)
    for i, p in enumerate(parts):
        groups.append({"text": p.replace("、", " ").strip(), "start": round(bounds[i], 2), "end": round(bounds[i + 1], 2)})
# 被拆开的英文词、单独的「因为」「好吧」并回去
merged = []
for g in groups:
    if merged and (re.match(r'^[A-Za-z]', g["text"]) and re.search(r'[A-Za-z]$', merged[-1]["text"]) or g["text"] in ("好吧", "对吧")
                   or merged[-1]["text"] in ("因为", "所以", "然后", "但是")):
        sep = " " if re.match(r'^[A-Za-z]', g["text"]) else ""
        merged[-1]["text"] += sep + g["text"]; merged[-1]["end"] = g["end"]
    else:
        merged.append(dict(g))
if merged:
    merged[0]["start"] = max(.1, merged[0]["start"])
for x, y in zip(merged, merged[1:]):
    if y["start"] < x["end"]: x["end"] = y["start"]
for g in merged:
    g["end"] = min(g["end"], edl["aroll"])
(W / "captions.json").write_text(json.dumps(merged, ensure_ascii=False, indent=0), encoding="utf-8")

# 7. 刀口核对：每个语义刀口（两个保留段的接缝）前后 2.5 秒转写一遍（窗口太短 whisper 会漏字）
if not a.no_verify:
    V = ["# 刀口核对", "", "每个语义刀口前后各 2.5 秒（成片时间），转写出来读一遍：有没有吞字、多出半个字、被删的词留了尾音。", "",
         "| 成片时间 | 原片接缝 | 听到 |", "| --- | --- | --- |"]
    for x, y in zip(mp, mp[1:]):
        if x["keep"] == y["keep"]:
            continue
        at = y["out"][0] / SPEED
        to16k(d / "hf/assets/voice.wav", W / "probe.wav", ss=max(0, at - 2.5), to=at + 2.5)
        V.append(f"| {fmt(at)} | {x['src'][1]:.2f} → {y['src'][0]:.2f} | {transcribe(W / 'probe.wav', None, '、'.join(names), segments=False)} |")
    (d / "刀口核对.md").write_text("\n".join(V) + "\n", encoding="utf-8")

print(f"{len(segs)} 段，剪后 {fmt(t)}，成片约 {fmt(t / SPEED)}；字幕 {len(merged)} 组")
print("读：删改清单.md、刀口核对.md（不对就用 probe.py 找静音改 plan.json，再跑一次）")
