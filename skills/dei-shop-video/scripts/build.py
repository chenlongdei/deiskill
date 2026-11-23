#!/usr/bin/env python3
"""project.json → HyperFrames 的 index.html（竖屏门店引流短视频）。

用法：python3 scripts/build.py <工程文件夹>
工程文件夹里要有：project.json、assets/audio/voN.mp3 + voN.json（tts.py 生成）、assets/video/*、assets/fonts/*。

时间点写法（所有 at / from / to 字段通用）：
  1.5                数字 = 秒
  "line:2"           第 2 句口播开始；"lineend:2" 第 2 句说完
  "word:9.9元就"      这几个字开始被说出的时刻；"word:新店开业@2" 只在第 2 句里找
  "end"              片尾
  任一写法后面加 "|-0.1" 或 "|+0.3" 表示提前 / 延后。
"""
import json, math, os, pathlib, subprocess, sys

if os.environ.get("PYTHONUTF8") != "1":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PUNCT = "，。！？、,.!? "


def die(msg):
    print("错误：" + msg, file=sys.stderr)
    sys.exit(1)


def ffdur(p):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                                  text=True, encoding="utf-8", errors="replace")
    return float(out.strip())


def main():
    if len(sys.argv) < 2:
        die("用法：python3 scripts/build.py <工程文件夹>")
    HERE = pathlib.Path(sys.argv[1]).resolve()
    P = json.loads((HERE / "project.json").read_text(encoding="utf-8"))
    W, H = P.get("size", [1080, 1920])
    V = P.get("voice", {})
    RATE, GAP, LEAD, TAIL = V.get("rate", 1.1), V.get("gap", 0.10), V.get("lead", 0.25), V.get("tail", 1.0)

    # ---------- 口播时间轴 ----------
    lines, t = [], LEAD
    n_lines = len(P["lines"])
    for i in range(1, n_lines + 1):
        jp, mp = HERE / f"assets/audio/vo{i}.json", HERE / f"assets/audio/vo{i}.mp3"
        if not jp.is_file() or not mp.is_file():
            die(f"缺少 {mp.name} 或 {jp.name}，先运行 tts.py")
        d = json.loads(jp.read_text(encoding="utf-8"))
        chars = d["chars"]
        speech_end = max(c["e"] for c in chars if c["c"] not in PUNCT) / RATE
        lines.append({"start": round(t, 3), "chars": chars, "text": d["text"], "end": round(t + speech_end, 3), "src_dur": ffdur(mp)})
        t += speech_end + GAP
    TOTAL = round(lines[-1]["end"] + TAIL, 2)

    def word_time(word, line=None):
        for li, L in enumerate(lines, 1):
            if line is not None and li != line:
                continue
            idx = L["text"].find(word)
            if idx >= 0:
                return L["start"] + L["chars"][idx]["s"] / RATE
        die(f"口播里找不到「{word}」" + (f"（第 {line} 句）" if line else ""))

    def at(spec):
        if isinstance(spec, (int, float)):
            return round(float(spec), 3)
        s, off = str(spec), 0.0
        if "|" in s:
            s, o = s.rsplit("|", 1)
            off = float(o)
        if s == "end":
            v = TOTAL
        elif s.startswith("line:"):
            v = lines[int(s[5:]) - 1]["start"]
        elif s.startswith("lineend:"):
            v = lines[int(s[8:]) - 1]["end"]
        elif s.startswith("word:"):
            w = s[5:]
            ln = None
            if "@" in w:
                w, ln = w.rsplit("@", 1)
                ln = int(ln)
            v = word_time(w, ln)
        else:
            v = float(s)
        return round(min(max(v + off, 0.0), TOTAL), 3)

    def snap(x):  # 吸附到 BGM 节拍网格（offset 已让节拍落在 0、60/bpm…）
        bpm = P.get("bgm", {}).get("bpm")
        if not bpm:
            return x
        step = 60.0 / bpm
        b = round(x / step) * step
        return round(b, 3) if abs(b - x) <= 0.18 else x

    # ---------- 镜头 ----------
    masked = {m["clip"] for m in P.get("masks", [])}

    def src_of(c):  # 有打码版就用打码版（mask.py 生成）
        mp = pathlib.Path(c)
        if c in masked:
            if not (HERE / "assets/video" / f"{mp.stem}_masked.mp4").is_file():
                die(f"{c} 要打码但还没有打码版：先运行 mask.py")
            return f"{mp.stem}_masked.mp4"
        return c

    shots = []
    for s in P["shots"]:
        st = at(s["at"])
        if s.get("snap"):
            st = snap(st)
        shots.append((st, s["clip"], s.get("from", 0.0)))
    shots.sort(key=lambda x: x[0])
    shot_end = lambda i: shots[i + 1][0] if i + 1 < len(shots) else TOTAL
    grade_attr = json.dumps(P.get("grade", {})).replace("'", "&#39;")
    shots_html = "\n".join(
        f'<video id="shot{i+1}" class="clip shot" src="assets/video/{src_of(c)}" muted playsinline data-start="{st}" '
        f'data-duration="{round(shot_end(i)-st,3)}" data-media-start="{ms}" data-track-index="{i%2}" '
        f"data-color-grading='{grade_attr}'></video>"
        for i, (st, c, ms) in enumerate(shots))
    shot_js = []
    for i, (st, _, _) in enumerate(shots):
        d = round(shot_end(i) - st, 3)
        if i == 0:
            shot_js.append(f'tl.fromTo("#shot1", {{scale:1.22}}, {{scale:1.04, duration:{min(0.7, d)}, ease:"expo.out"}}, 0);')
            if d > 0.7:
                shot_js.append(f'tl.to("#shot1", {{scale:1.0, duration:{round(d-0.7,3)}, ease:"none"}}, 0.7);')
        else:
            shot_js.append(f'tl.fromTo("#shot{i+1}", {{scale:1.14}}, {{scale:1.0, duration:{d}, ease:"power3.out"}}, {st});')

    def shot_at(tm):
        idx = 0
        for i, (st, _, _) in enumerate(shots):
            if st <= tm:
                idx = i
        return f"#shot{idx+1}"

    # ---------- 字幕 ----------
    def hl(s):
        out, on = "", False
        for part in s.split("*"):
            out += f"<em>{part}</em>" if on else part
            on = not on
        return out

    caps = []
    for L, segs in zip(lines, P["captions"]):
        pos, starts = 0, []
        for s in segs:
            clean = s.lstrip("#").replace("*", "")
            idx = L["text"].find(clean, pos)
            if idx < 0:
                die(f"字幕「{clean}」和口播对不上：{L['text']}")
            pos = idx + len(clean)
            starts.append(round(L["start"] + L["chars"][idx]["s"] / RATE, 3))
        for k, s in enumerate(segs):
            end = starts[k + 1] if k + 1 < len(segs) else L["end"] + 0.15
            if not s.startswith("#"):
                caps.append((starts[k], round(end - starts[k], 3), s))
    cap_html = "\n".join(
        f'<div id="cap{i+1}" class="clip cap" data-start="{s}" data-duration="{d}" data-track-index="10"><span>{hl(x)}</span></div>'
        for i, (s, d, x) in enumerate(caps))
    cap_js = [f'tl.fromTo("#cap{i+1} span", {{scale:0.8, y:16, opacity:0.3}}, {{scale:1, y:0, opacity:1, duration:0.14, ease:"back.out(3)"}}, {s});'
              for i, (s, _, _) in enumerate(caps)]

    # ---------- 图层（花字、贴纸、团购卡…） ----------
    css, html, js = [], [], []
    track = [11]

    def tr():
        track[0] = 11 + (track[0] - 10) % 6
        return track[0]

    def pop_in(sel, t0, rot):
        js.append(f'tl.fromTo("{sel}", {{scale:0.2, rotation:{rot*3}, opacity:0}}, {{scale:1, rotation:{rot}, opacity:1, duration:0.3, ease:"back.out(2.6)"}}, {t0});')

    def shake(sel, t0, n=5, amp=16):
        js.append(f'tl.to("{sel}", {{x:{amp}, y:{-amp//2}, duration:0.035, yoyo:true, repeat:{n}, ease:"none"}}, {t0});')
        js.append(f'tl.set("{sel}", {{x:0, y:0}}, {round(t0 + 0.04*(n+1) + 0.02, 3)});')

    def star(n=14, r1=250, r2=185, c=270):
        return " ".join(f"{c + (r1 if i%2==0 else r2)*math.cos(math.pi*i/n - math.pi/2):.0f},{c + (r1 if i%2==0 else r2)*math.sin(math.pi*i/n - math.pi/2):.0f}" for i in range(n*2))

    def rays(n=20, r=1400, c=700):
        return "".join(f'<polygon points="{c},{c} {c+r*math.cos(2*math.pi*i/n):.0f},{c+r*math.sin(2*math.pi*i/n):.0f} {c+r*math.cos(2*math.pi*(i+0.5)/n):.0f},{c+r*math.sin(2*math.pi*(i+0.5)/n):.0f}"/>' for i in range(n))

    def speedlines(n=36, c=700):
        out = []
        for i in range(n):
            a = 2*math.pi*i/n + (i % 3) * 0.03
            r0, w = 300 + (i * 53 % 140), 5 + (i * 7 % 9)
            x0, y0, x1, y1 = c + r0*math.cos(a), c + r0*math.sin(a), c + 1000*math.cos(a), c + 1000*math.sin(a)
            nx, ny = -math.sin(a)*w, math.cos(a)*w
            out.append(f'<polygon points="{x0:.0f},{y0:.0f} {x1+nx:.0f},{y1+ny:.0f} {x1-nx:.0f},{y1-ny:.0f}"/>')
        return "".join(out)

    COLORS = {  # 花字配色：字色 / 描边 / 阴影
        "yellow-red": ("var(--hl)", "var(--hot)", "#7a0000"),
        "yellow-black": ("var(--hl)", "var(--ink)", "rgba(0,0,0,.35)"),
        "white-brand": ("#fff", "var(--brand)", "rgba(0,0,0,.3)"),
        "white-red": ("#fff", "var(--hot)", "#7a0000"),
        "white-black": ("#fff", "var(--ink)", "rgba(0,0,0,.35)"),
    }

    for n, o in enumerate(P.get("overlays", []), 1):
        kind = o["type"]
        oid = o.get("id") or f"{kind}{n}"
        t0 = at(o.get("from", 0))
        t1 = at(o.get("to", "end"))
        dur = round(max(0.1, t1 - t0), 3)
        top = o.get("top")
        if kind == "pin":
            css.append(f'#{oid} {{{{ position:absolute; left:0; width:{W}px; top:{top or 190}px; z-index:41; text-align:center; }}}}')
            chars = "".join(f'<span class="ch">{c}</span>' for c in o["text"])
            html.append(f'<div id="{oid}" class="clip pin" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="pill">'
                        '<svg viewBox="0 0 64 80"><path d="M32 2C16 2 4 14 4 30c0 20 28 46 28 46s28-26 28-46C60 14 48 2 32 2z" fill="#ff2b2b" stroke="#fff" stroke-width="4"/><circle cx="32" cy="30" r="10" fill="#fff"/></svg>'
                        f'{chars}</div></div>')
            js += [f'tl.fromTo("#{oid} svg", {{y:-260, rotation:-20}}, {{y:0, rotation:0, duration:0.45, ease:"bounce.out"}}, {t0});',
                   f'tl.fromTo("#{oid} .pill", {{scaleX:0.55}}, {{scaleX:1, duration:0.35, ease:"back.out(2)"}}, {t0});',
                   f'tl.fromTo("#{oid} .ch", {{y:30}}, {{y:0, duration:0.2, stagger:0.04, ease:"back.out(3)"}}, {t0});',
                   f'tl.to("#{oid} .pill", {{scale:0.9, opacity:0, y:-30, duration:0.15, ease:"power2.in"}}, {round(t1-0.15,3)});']
        elif kind == "headline":
            css.append(f'#{oid} {{{{ top:{top or 700}px; }}}}')
            html.append(f'<div id="{oid}" class="clip fx headline" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="in">'
                        f'<span class="p">{o["big"]}</span><span class="s">{o.get("small","")}</span></div></div>')
            js += [f'tl.fromTo("#{oid} .in", {{scale:1.12, rotation:-7}}, {{scale:1, rotation:-4, duration:0.32, ease:"back.out(2.2)"}}, {t0});',
                   f'tl.fromTo("#{oid} .s", {{x:-60}}, {{x:0, duration:0.3, ease:"power3.out"}}, {round(t0+0.05,3)});']
            if o.get("slam"):
                ts = at(o["slam"])
                js.append(f'tl.fromTo("#{oid} .in", {{scale:1.22}}, {{scale:1, duration:0.2, ease:"power4.out"}}, {ts});')
                shake(shot_at(ts), round(ts + 0.05, 3), amp=18)
                idle0 = round(ts + 0.6, 3)
            else:
                idle0 = round(t0 + 0.6, 3)
            reps = int((t1 - 0.2 - idle0) / 0.3)
            if reps >= 1:
                js.append(f'tl.to("#{oid} .in", {{scale:1.04, duration:0.3, yoyo:true, repeat:{reps}, ease:"sine.inOut"}}, {idle0});')
            js.append(f'tl.to("#{oid} .in", {{scale:0, y:-120, opacity:0, duration:0.14, ease:"power2.in"}}, {round(t1-0.14,3)});')
        elif kind == "speedlines":
            css.append(f'#{oid} {{{{ position:absolute; left:-160px; top:{top or 150}px; width:1400px; height:1400px; z-index:35; opacity:0; }}}}\n#{oid} svg {{{{ width:1400px; height:1400px; }}}}')
            html.append(f'<div id="{oid}" class="clip" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}" data-layout-allow-overflow><svg viewBox="0 0 1400 1400"><g fill="#fff" opacity=".85">{speedlines()}</g></svg></div>')
            js += [f'tl.fromTo("#{oid}", {{opacity:0, scale:1.4}}, {{opacity:1, scale:1, duration:0.18, ease:"power2.out"}}, {t0});',
                   f'tl.to("#{oid} svg", {{rotation:8, duration:{dur}, ease:"none"}}, {t0});']
        elif kind == "flash":
            html.append(f'<div id="{oid}" class="clip flash" data-start="{round(t0-0.06,3)}" data-duration="0.4" data-track-index="2"></div>')
            js += [f'tl.fromTo("#{oid}", {{opacity:0}}, {{opacity:0.95, duration:0.06, ease:"none"}}, {round(t0-0.06,3)});',
                   f'tl.to("#{oid}", {{opacity:0, duration:0.3, ease:"power2.out"}}, {t0});']
        elif kind == "ribbon":
            css.append(f'#{oid} {{{{ position:absolute; left:0; top:{top or 330}px; z-index:41; }}}}')
            html.append(f'<div id="{oid}" class="clip ribbon" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="in">{o["text"]}</div></div>')
            js += [f'tl.fromTo("#{oid} .in", {{x:-560}}, {{x:0, duration:0.35, ease:"back.out(1.6)"}}, {t0});',
                   f'tl.to("#{oid} .in", {{x:-560, duration:0.2, ease:"power2.in"}}, {round(t1-0.2,3)});']
        elif kind == "burst":
            y = top or 430
            css.append(f'#{oid} {{{{ position:absolute; left:{(W-540)//2}px; top:{y}px; width:540px; height:540px; z-index:42; }}}}\n'
                       f'#{oid}sun {{{{ position:absolute; left:{(W-1400)//2}px; top:{y+270-700}px; width:1400px; height:1400px; z-index:36; }}}}')
            html.append(f'<div id="{oid}sun" class="clip sun" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}" data-layout-allow-overflow><div class="in"><svg viewBox="0 0 1400 1400"><g fill="#ffe600" opacity=".28">{rays()}</g></svg></div></div>')
            html.append(f'<div id="{oid}" class="clip burst" data-start="{round(t0-0.05,3)}" data-duration="{round(dur+0.05,3)}" data-track-index="{tr()}"><div class="in">'
                        f'<svg viewBox="0 0 540 540"><polygon points="{star()}" fill="#ffe600" stroke="#ff2b2b" stroke-width="14" stroke-linejoin="round"/></svg>'
                        f'<div class="price"><small>{o.get("prefix","¥")}</small>{o["text"]}</div></div></div>')
            coins = [(math.radians(a), d) for a, d in [(-150, 430), (-120, 520), (-95, 470), (-70, 540), (-40, 450), (-15, 400),
                                                        (200, 380), (170, 420), (10, 360), (-60, 300), (-130, 320), (-170, 300)]]
            html.append(f'<div id="{oid}coins" class="clip" data-start="{t0}" data-duration="1.4" data-track-index="{tr()}" data-layout-allow-overflow data-layout-allow-overlap style="position:absolute;inset:0;z-index:43">'
                        + "".join(f'<div class="coin" id="{oid}c{i}" data-layout-allow-overlap style="left:{W//2-42}px;top:{y+230}px"><i></i></div>' for i in range(len(coins))) + '</div>')
            js += [f'tl.fromTo("#{oid}sun .in", {{scale:0, opacity:0}}, {{scale:1, opacity:1, duration:0.35, ease:"power3.out"}}, {t0});',
                   f'tl.to("#{oid}sun svg", {{rotation:40, duration:{dur}, ease:"none"}}, {t0});',
                   f'tl.fromTo("#{oid} .in", {{scale:0, rotation:-40}}, {{scale:1, rotation:-8, duration:0.35, ease:"back.out(2.4)"}}, {round(t0-0.05,3)});']
            reps = int((dur - 0.8) / 0.4)
            if reps >= 1:
                js.append(f'tl.to("#{oid} .in", {{scale:1.06, duration:0.4, yoyo:true, repeat:{reps}, ease:"sine.inOut"}}, {round(t0+0.5,3)});')
            for i, (a, d) in enumerate(coins):
                js.append(f'tl.fromTo("#{oid}c{i}", {{x:0, y:0, scale:0.3, opacity:1, rotation:0}}, {{x:{d*math.cos(a):.0f}, y:{d*math.sin(a):.0f}, scale:1, rotation:{(i*67)%360-180}, duration:0.7, ease:"power3.out"}}, {round(t0+0.1+i*0.012,3)});')
                js.append(f'tl.to("#{oid}c{i}", {{y:"+=260", opacity:0, duration:0.4, ease:"power2.in"}}, {round(t0+0.8+i*0.012,3)});')
            js.append(f'tl.to(["#{oid} .in", "#{oid}sun .in"], {{scale:0, opacity:0, duration:0.18, ease:"power2.in"}}, {round(t1-0.18,3)});')
        elif kind == "tag":
            css.append(f'#{oid} {{{{ top:{top or 1000}px; z-index:44; }}}}')
            html.append(f'<div id="{oid}" class="clip fx tag" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="in">{o["text"]}</div></div>')
            js += [f'tl.fromTo("#{oid} .in", {{y:120, opacity:0}}, {{y:0, opacity:1, duration:0.3, ease:"back.out(2.2)"}}, {t0});',
                   f'tl.to("#{oid} .in", {{scale:0, opacity:0, duration:0.18, ease:"power2.in"}}, {round(t1-0.18,3)});']
        elif kind in ("pop", "strike"):
            fill, stroke, shadow = COLORS.get(o.get("color", "white-brand"), COLORS["white-brand"])
            css.append(f'#{oid} {{{{ top:{top or 500}px; font-size:{o.get("size",150)}px; }}}}\n'
                       f'#{oid} .in {{{{ color:{fill}; -webkit-text-stroke:18px {stroke}; paint-order:stroke fill; text-shadow:0 12px 0 {shadow}; }}}}')
            html.append(f'<div id="{oid}" class="clip fx f-{o.get("font","disp")}" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="in">{o["text"]}</div></div>')
            pop_in(f"#{oid} .in", t0, o.get("rot", -4))
            if kind == "strike":
                js.append(f'tl.fromTo("#{oid} .strike", {{scaleX:0}}, {{scaleX:1, duration:0.22, ease:"power2.out"}}, {at(o.get("strike_at", t0 + 0.85))});')
        elif kind == "impact":
            fill, stroke, shadow = COLORS.get(o.get("color", "yellow-black"), COLORS["yellow-black"])
            css.append(f'#{oid} {{{{ top:{top or 440}px; font-size:{o.get("size",200)}px; }}}}\n'
                       f'#{oid} .in {{{{ color:{fill}; -webkit-text-stroke:18px {stroke}; paint-order:stroke fill; text-shadow:0 12px 0 {shadow}; }}}}')
            sub = f'<span class="sub">{o["sub"]}</span>' if o.get("sub") else ""
            html.append(f'<div id="{oid}" class="clip fx f-{o.get("font","num")}" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="in">{o["text"]}{sub}</div></div>')
            js.append(f'tl.fromTo("#{oid} .in", {{scale:3.2, opacity:0}}, {{scale:1, opacity:1, duration:0.2, ease:"power4.in"}}, {t0});')
            js.append(f'tl.to("#{oid} .in", {{x:16, duration:0.035, yoyo:true, repeat:5, ease:"none"}}, {round(t0+0.2,3)});')
        elif kind == "card":
            css.append(f'#{oid} {{{{ position:absolute; left:70px; top:{top or 560}px; width:{W-140}px; z-index:45; }}}}')
            html.append(f'<div id="{oid}" class="clip card" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}"><div class="in"><img src="{o["img"]}" alt="团购卡片" /></div></div>')
            js.append(f'tl.fromTo("#{oid} .in", {{y:500, scale:0.6, opacity:0}}, {{y:0, scale:1, opacity:1, duration:0.45, ease:"back.out(1.8)"}}, {t0});')
        elif kind == "arrow":
            css.append(f'#{oid} {{{{ position:absolute; left:{o.get("left",110)}px; top:{top or 1330}px; width:220px; height:240px; z-index:46; }}}}')
            html.append(f'<div id="{oid}" class="clip" data-start="{t0}" data-duration="{dur}" data-track-index="{tr()}" data-layout-allow-overflow><div class="in" style="width:220px;height:240px">'
                        '<svg viewBox="0 0 220 240" width="220" height="240"><g transform="rotate(35 110 120)"><rect x="80" y="10" width="60" height="130" rx="10" fill="#ff2b2b" stroke="#fff" stroke-width="8"/><polygon points="20,130 200,130 110,230" fill="#ff2b2b" stroke="#fff" stroke-width="8" stroke-linejoin="round"/><rect x="84" y="118" width="52" height="24" fill="#ff2b2b"/></g></svg></div></div>')
            js.append(f'tl.fromTo("#{oid} .in", {{x:0, y:0}}, {{x:-18, y:26, duration:0.3, yoyo:true, repeat:{max(1,int(dur/0.3)-1)}, ease:"sine.inOut"}}, {t0});')
        else:
            die(f"不认识的图层类型：{kind}")

    # ---------- 音频 ----------
    vo_html = "\n".join(
        f'<audio id="vo{i+1}" class="clip" src="assets/audio/vo{i+1}.mp3" data-start="{L["start"]}" '
        f'data-duration="{round(min(L["src_dur"]/RATE, L["end"]-L["start"]+0.25),3)}" data-playback-rate="{RATE}" '
        f'data-track-index="{20 + i%2}" data-volume="{V.get("volume",1.6)}"></audio>'
        for i, L in enumerate(lines))
    B = P.get("bgm", {})
    bgm_html = ""
    if B.get("file"):
        duck = B.get("duck", 0.55)
        pts = [{"t": 0, "v": 1.0}, {"t": max(0.01, lines[0]["start"] - 0.02), "v": 1.0}, {"t": lines[0]["start"] + 0.15, "v": duck},
               {"t": round(lines[-1]["end"], 2), "v": duck}, {"t": round(lines[-1]["end"] + 0.3, 2), "v": 0.9}]
        auto = json.dumps({"version": 1, "lanes": [{"target": "volume", "points": pts}]}).replace('"', "&quot;")
        bgm_html = (f'<audio id="bgm" class="clip" src="{B["file"]}" data-start="0" data-duration="{TOTAL}" data-media-start="{B.get("offset",0)}" '
                    f'data-track-index="22" data-volume="{B.get("volume",0.75)}" data-fade-out="0.8" data-automation="{auto}"></audio>')
    sfx_dir = P.get("sfx_dir", "assets/audio/sfx")
    sfx_html = []
    for i, s in enumerate(P.get("sfx", [])):
        f = HERE / sfx_dir / f"{s['name']}.mp3"
        if not f.is_file():
            print(f"提示：缺音效 {f.name}，已跳过（先运行 sfx.py）")
            continue
        st = at(s["at"])
        d = round(min(ffdur(f), TOTAL - st), 3)
        if d <= 0.05:
            continue
        sfx_html.append(f'<audio id="sfx{i+1}" class="clip" src="{sfx_dir}/{s["name"]}.mp3" data-start="{st}" data-duration="{d}" '
                        f'data-track-index="{23 + i%4}" data-volume="{s.get("volume",0.6)}"></audio>')

    F = P.get("fonts", {})
    font_css = ""
    if F.get("caption"):
        font_css += f'@font-face {{ font-family: "Cap"; src: url("assets/fonts/{F["caption"]}"); }}\n'
    if F.get("display"):
        font_css += f'@font-face {{ font-family: "Disp"; src: url("assets/fonts/{F["display"]}"); }}\n'
    if F.get("number"):
        font_css += f'@font-face {{ font-family: "Num"; src: url("assets/fonts/{F["number"]}"); }}\n'
    C = P.get("colors", {})
    tmpl = (pathlib.Path(__file__).parent.parent / "templates" / "page.html").read_text(encoding="utf-8")
    page = (tmpl.replace("{{W}}", str(W)).replace("{{H}}", str(H)).replace("{{TOTAL}}", str(TOTAL))
            .replace("{{FONTS}}", font_css)
            .replace("{{BRAND}}", C.get("brand", "#1d5fd1")).replace("{{TEAL}}", C.get("accent", "#10b8a6"))
            .replace("{{CSS}}", "\n".join(css).replace("{{", "{").replace("}}", "}"))
            .replace("{{SHOTS}}", shots_html).replace("{{OVERLAYS}}", "\n".join(html)).replace("{{CAPTIONS}}", cap_html)
            .replace("{{AUDIO}}", "\n".join([vo_html, bgm_html] + sfx_html))
            .replace("{{JS}}", "\n".join(shot_js + js + cap_js)))
    (HERE / "index.html").write_text(page, encoding="utf-8")
    print(f"已生成 index.html：{TOTAL} 秒，{len(shots)} 个镜头，{len(caps)} 条字幕，{len(P.get('overlays',[]))} 个图层，{len(sfx_html)} 个音效")
    for i, L in enumerate(lines, 1):
        print(f"  第{i}句 {L['start']:.2f}–{L['end']:.2f}s  {L['text']}")


if __name__ == "__main__":
    main()
