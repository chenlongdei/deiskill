#!/usr/bin/env python3
"""ElevenLabs 配音：口播 → assets/audio/voN.mp3 + voN.json（逐字时间戳），并用语音识别核对读得对不对。

用法：
  python3 scripts/tts.py voices [--gender male|female] [--search 关键词]   搜中文母语音色
  python3 scripts/tts.py sample <工程> --voices id1,id2,... [--line 1]      每个音色试读一句，存到 <工程>/配音试音/
  python3 scripts/tts.py make <工程> [--only 2,3]                            按 project.json 生成全部（或指定几句）
  python3 scripts/tts.py check <音频文件> "<原文>"                            单独核对一段音频
"""
import argparse, base64, difflib, json, re, sys, urllib.parse, urllib.request
from common import eleven_key, project, die

API = "https://api.elevenlabs.io"


def call(method, path, body=None, form=None):
    key = eleven_key()
    headers = {"xi-api-key": key}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if form is not None:
        boundary = "----deishopvideo"
        parts = []
        for k, v in form.items():
            if isinstance(v, tuple):
                fn, content = v
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode() + content + b"\r\n")
            else:
                parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode("utf-8"))
        data = b"".join(parts) + f"--{boundary}--\r\n".encode()
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:300]
        if e.code == 401:
            die(f"ElevenLabs 401：key 无效或没有这项权限。{msg}")
        if e.code in (402, 429) or "quota" in msg:
            die(f"ElevenLabs 额度不足或限流（{e.code}）：{msg}")
        die(f"ElevenLabs {e.code}：{msg}")


# ---------- 数字转中文（只为核对读音，够用即可） ----------
DIG = "零一二三四五六七八九"


def int_cn(n):
    if n == 0:
        return "零"
    units = [(1000, "千"), (100, "百"), (10, "十")]
    s, zero = "", False
    for u, ch in units:
        q, n = divmod(n, u)
        if q:
            if zero:
                s += "零"
            s += ("" if (u == 10 and q == 1 and not s) else DIG[q]) + ch
            zero = False
        elif s:
            zero = True
    if n:
        s += ("零" if zero else "") + DIG[n]
    return s


def num_cn(m):
    t = m.group(0)
    if "." in t:
        a, b = t.split(".", 1)
        return int_cn(int(a)) + "点" + "".join(DIG[int(x)] for x in b)
    return int_cn(int(t)) if len(t) <= 4 else "".join(DIG[int(x)] for x in t)


def norm(s):
    s = re.sub(r"\d+(\.\d+)?", num_cn, s)
    return re.sub(r"[^一-鿿A-Za-z]", "", s)


def check(mp3_bytes, text):
    r = call("POST", "/v1/speech-to-text", form={"model_id": "scribe_v1", "language_code": "zho", "file": ("a.mp3", mp3_bytes)})
    heard = re.sub(r"[\[（(][^\]）)]*[\]）)]", "", r.get("text", "")).strip()  # 去掉 [背景音乐] 这类声音标签
    x, y = norm(text), norm(heard)
    sm = difflib.SequenceMatcher(None, x, y)
    diffs = [f"{x[i1:i2] or '（漏）'}→{y[j1:j2] or '（多）'}" for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"]
    return heard, sm.ratio(), diffs


def tts(text, voice, model, prev=None, nxt=None, settings=None):
    body = {"text": text, "model_id": model, "language_code": "zh", "voice_settings": settings or {"stability": 0.4, "similarity_boost": 0.8}}
    if prev:
        body["previous_text"] = prev
    if nxt:
        body["next_text"] = nxt
    r = call("POST", f"/v1/text-to-speech/{voice}/with-timestamps?output_format=mp3_44100_128", body)
    a = r["alignment"]
    chars = [{"c": c, "s": s, "e": e} for c, s, e in zip(a["characters"], a["character_start_times_seconds"], a["character_end_times_seconds"])]
    return base64.b64decode(r["audio_base64"]), chars


def cmd_voices(a):
    q = {"page_size": 30, "language": "zh", "sort": "usage_character_count_1y"}
    if a.gender:
        q["gender"] = a.gender
    if a.search:
        q["search"] = a.search
    r = call("GET", "/v1/shared-voices?" + urllib.parse.urlencode(q))
    print("voice_id | 名字 | 口音 | 年龄 | 用途 | 近一年用量")
    for v in r.get("voices", []):
        print(v["voice_id"], "|", v["name"][:40], "|", v.get("accent"), "|", v.get("age"), "|", v.get("use_case"), "|", v.get("usage_character_count_1y"))
    print("\n挑口音写 beijing mandarin / standard 且描述里是中文母语的；Taiwan、Cantonese、英文名+「Asian」描述的通常不是大陆普通话母语。")


def cmd_sample(a):
    d, P = project(a.project)
    text = P["lines"][a.line - 1]
    model = P.get("voice", {}).get("model", "eleven_v4")
    out = d / "配音试音"
    out.mkdir(exist_ok=True)
    for v in a.voices.split(","):
        v = v.strip()
        mp3, _ = tts(text, v, model)
        (out / f"{v}.mp3").write_bytes(mp3)
        heard, ratio, diffs = check(mp3, text)
        print(f"{v}  一致度 {ratio:.0%}  不同处：{'、'.join(diffs) or '无'}")
    print(f"试音在 {out}，请用户自己听，挑一个写进 project.json 的 voice.voice_id")


def cmd_make(a):
    d, P = project(a.project)
    V = P.get("voice", {})
    voice, model = V.get("voice_id"), V.get("model", "eleven_v4")
    if not voice:
        die("project.json 的 voice.voice_id 为空：先用 voices / sample 选音色")
    lines = P["lines"]
    only = {int(x) for x in a.only.split(",")} if a.only else None
    bad = []
    for i, text in enumerate(lines, 1):
        if only and i not in only:
            continue
        mp3, chars = tts(text, voice, model, lines[i - 2] if i > 1 else None, lines[i] if i < len(lines) else None, V.get("settings"))
        (d / f"assets/audio/vo{i}.mp3").write_bytes(mp3)
        (d / f"assets/audio/vo{i}.json").write_text(json.dumps({"text": text, "chars": chars}, ensure_ascii=False), encoding="utf-8")
        heard, ratio, diffs = check(mp3, text)
        flag = "✅" if not diffs else "⚠"
        if diffs:
            bad.append(i)
        print(f"{flag} 第{i}句 {chars[-1]['e']:.2f}s 一致度 {ratio:.0%}" + (f"  不同处：{'、'.join(diffs)}" if diffs else "") + f"\n   原文：{text}\n   听到：{heard}")
    if bad:
        print(f"\n第 {bad} 句有不同处。店名、人名等专有名词被识别成同音字（如 鑫韦伊→新唯一）是正常的，不用重做；"
              "其他字不同说明读错、多音字读错或卡顿：改写法（数字写成汉字、换同义词）后用 --only 重生成，或请用户听一下这句。")


def cmd_check(a):
    heard, ratio, diffs = check(open(a.file, "rb").read(), a.text)
    print(f"一致度 {ratio:.0%}  不同处：{'、'.join(diffs) or '无'}\n听到：{heard}")


ap = argparse.ArgumentParser()
sp = ap.add_subparsers(dest="cmd", required=True)
p = sp.add_parser("voices"); p.add_argument("--gender"); p.add_argument("--search"); p.set_defaults(f=cmd_voices)
p = sp.add_parser("sample"); p.add_argument("project"); p.add_argument("--voices", required=True); p.add_argument("--line", type=int, default=1); p.set_defaults(f=cmd_sample)
p = sp.add_parser("make"); p.add_argument("project"); p.add_argument("--only"); p.set_defaults(f=cmd_make)
p = sp.add_parser("check"); p.add_argument("file"); p.add_argument("text"); p.set_defaults(f=cmd_check)
a = ap.parse_args()
a.f(a)
