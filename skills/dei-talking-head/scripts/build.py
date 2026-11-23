#!/usr/bin/env python3
"""把工程的 scenes.py（这条视频的画面）套进市场版画面系统，生成 HyperFrames 工程，检查并出关键帧。

用法：
  python3 scripts/build.py <工程>                    生成 + check
  python3 scripts/build.py <工程> --snap 3,36,82     另外在这些成片秒数截图（拼图在 work/snap/）
画面系统（references/scenes.md）：全屏人像 + 跳切交替推近（两次至少隔 2 秒）+ 常驻标题和进度条 + 大粗字幕
+ 讲结构时整屏切图解（墨黑 + 荧光绿）。scenes.py 里能用的函数见 scenes.md，例子见 templates/scenes_example.py。
"""
import argparse, html, json, os, pathlib, re, shutil, sys
from common import project, hf, die

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--snap", default="")
args = ap.parse_args()
D, PLAN = project(args.project)
HF = D / "hf"
COMP = HF / "compositions"
edl = json.loads((D / "work/edl.json").read_text(encoding="utf-8"))
SPEED = edl["speed"]
AROLL = edl["aroll"]
TOTAL = round(AROLL + PLAN.get("tail", 1.0), 2)
JUMPS = [s["out"][0] / SPEED for s in edl["segments"][1:]]
CAPS = json.loads((D / "work/captions.json").read_text(encoding="utf-8"))

# ---- 时间：scenes.py 里写的秒数按 edl_base（第一次剪）算；改过剪辑后自动换算到当前剪辑（按原片时间对齐）
_base = json.loads((D / "work/edl_base.json").read_text(encoding="utf-8"))["segments"] if (D / "work/edl_base.json").exists() else None
def R(t):
    if not _base:
        return t
    for sg in _base:
        a, b = sg["out"][0] / SPEED, sg["out"][1] / SPEED
        if a - 1e-6 <= t < b + 1e-6:
            src = sg["src"][0] + (t - a) * SPEED
            break
    else:
        last = _base[-1]["out"][1] / SPEED
        return t + (AROLL - last) if t >= last else t
    for sg in edl["segments"]:
        if sg["src"][0] - 1e-6 <= src <= sg["src"][1] + 1e-6:
            return round((sg["out"][0] + src - sg["src"][0]) / SPEED, 3)
    best = min(edl["segments"], key=lambda g: min(abs(g["src"][0] - src), abs(g["src"][1] - src)))
    near0 = abs(best["src"][0] - src) < abs(best["src"][1] - src)
    return round((best["out"][0] if near0 else best["out"][1]) / SPEED, 3)

def W(text, n=1, off=0.0):
    """字幕里第 n 次出现 text 的时刻（成片秒数）+ off。按字数在字幕组里插值，改了剪辑也跟着走"""
    k = 0
    for g in CAPS:
        i = g["text"].find(text)
        while i >= 0:
            k += 1
            if k == n:
                return round(g["start"] + (g["end"] - g["start"]) * i / max(len(g["text"]), 1) + off, 3)
            i = g["text"].find(text, i + 1)
    die(f"W(): 字幕里找不到第 {n} 个「{text}」")
_W = W
class _Now(float):
    """W() 算出的时间已经是当前剪辑的，不再换算"""
def W(text, n=1, off=0.0):  # noqa: F811
    return _Now(_W(text, n, off))
def _t(t):
    return float(t) if isinstance(t, _Now) else R(t)

# ---- 配色与字体（plan.json 的 colors 可覆盖）
C = dict(INK='#0B0C0A', TILE='#1E211B', LINE='#2E322A', WHITE='#F4F5EF', GRAY='#8C9085', NEON='#C8FF2E', RED='#FF4B3E')
C.update(PLAN.get("colors", {}))
INK, TILE, LINE, WHITE, GRAY, NEON, RED = (C[k] for k in ("INK", "TILE", "LINE", "WHITE", "GRAY", "NEON", "RED"))
def _font(stem):
    f = next(iter(sorted((HF / "assets/fonts").glob(stem + ".*"))), None)
    return f"assets/fonts/{f.name}" if f else None
FONT_CSS = ""
for fam, stem, wt in (("PH", "Bold", 700), ("PH", "Black", 900), ("DY", "Number", 400)):
    p = _font(stem)
    if p:
        FONT_CSS += f'@font-face{{font-family:"{fam}";font-weight:{wt};src:url("{p}")}}'
FALLBACK = '"PH",sans-serif' if _font("Bold") or _font("Black") else 'sans-serif'
TITLE = PLAN.get("title", "")

els, js, SFX, EXTRA_CSS = [], [], [], []
def A(t, sel, frm, to, dur=.3, ease='power2.out'):
    js.append(f'tl.fromTo("{sel}",{json.dumps(frm)},{json.dumps({**to, "duration": dur, "ease": ease})},{_t(t):.2f});')
def T(t, sel, to, dur=.3, ease='power2.out'):
    js.append(f'tl.to("{sel}",{json.dumps({**to, "duration": dur, "ease": ease})},{_t(t):.2f});')
def S(t, kind, v=1.0):
    SFX.append(dict(t=round(_t(t), 3), kind=kind, v=v))
_n = [0]
def nid(p):
    _n[0] += 1
    return f'{p}{_n[0]}'

_ic = {}
def ic(name, size, color=None, sw=None):
    """IconPark 线性图标（hf/assets/icons/<name>.svg），内联，颜色可动画"""
    color = color or WHITE
    if name not in _ic:
        f = HF / "assets/icons" / f"{name}.svg"
        if not f.is_file():
            die(f"没有图标 {name}.svg：从 IconPark 导出放进 hf/assets/icons/")
        _ic[name] = re.sub(r'<\?xml[^>]*\?>', '', f.read_text(encoding="utf-8"))
    s = _ic[name].replace('width="100%" height="100%"', f'width="{size}" height="{size}"', 1)
    if sw:
        s = s.replace('stroke-width="3"', f'stroke-width="{sw}"')
    return f'<span class="ic" style="color:{color};width:{size}px;height:{size}px">{s}</span>'
def logo(name, size, r=.24):
    """品牌 logo（hf/assets/logos/<name>.svg|png），白底圆角"""
    f = next(iter(sorted((HF / "assets/logos").glob(name + ".*"))), None)
    if not f:
        die(f"没有 logo {name}：放进 hf/assets/logos/（官方素材或 theSVG）")
    return (f'<div class="logo" style="width:{size}px;height:{size}px;border-radius:{size * r:.0f}px;padding:{size * .16:.0f}px">'
            f'<img src="assets/logos/{f.name}"></div>')

def put(t, inner, x, y, kind='up', sfx=None, v=1.0, z=None, cls=''):
    """在 (x, y)（画布坐标，元素中心）放一个元素，t 秒出现。kind：up / pop / slam / drop / left"""
    i = nid('e')
    els.append(f'<div id="{i}" class="el {cls}" style="left:{x}px;top:{y}px;{f"z-index:{z};" if z else ""}"><div class="in" style="opacity:0">{inner}</div></div>')
    sel = f'#{i} > .in'
    if kind == 'pop': A(t, sel, {'opacity': 0, 'scale': .4}, {'opacity': 1, 'scale': 1}, .38, 'back.out(2)')
    elif kind == 'slam': A(t, sel, {'opacity': 0, 'scale': 2.2}, {'opacity': 1, 'scale': 1}, .28, 'power3.in')
    elif kind == 'drop': A(t, sel, {'opacity': 0, 'y': -90}, {'opacity': 1, 'y': 0}, .5, 'bounce.out')
    elif kind == 'left': A(t, sel, {'opacity': 0, 'x': -80}, {'opacity': 1, 'x': 0}, .32, 'power3.out')
    else: A(t, sel, {'opacity': 0, 'y': 40}, {'opacity': 1, 'y': 0}, .32, 'power3.out')
    if sfx:
        S(t, sfx, v)
    return i
def hide(t, i, dur=.2):
    T(t, f'#{i} > .in', {'opacity': 0}, dur, 'power2.in')

scenes, _cur = [], [None]
def scene(t_in, t_out, chap, title):
    """整屏图解开始（盖住人像，口播继续）。chap：左上角小字章节；title：大标题。配 end_scene()"""
    sid = nid('sc')
    _cur[0] = dict(id=sid, t_in=t_in, t_out=t_out, start=len(els)); scenes.append(_cur[0])
    els.append(f'<div class="chap">{chap}</div><div class="stitle">{title}</div>')
def end_scene():
    c = _cur[0]
    body = els[c['start']:]; del els[c['start']:]
    els.append(f'<div id="{c["id"]}" class="scene" style="opacity:0"><div class="glow"></div>{"".join(body)}</div>')
    a, b, i = c['t_in'], c['t_out'], c['id']
    A(a - .12, f'#{i}', {'opacity': 0, 'y': 120, 'scale': 1.04}, {'opacity': 1, 'y': 0, 'scale': 1}, .32, 'power3.out')
    A(a - .12, f'#{i} .stitle', {'opacity': 0, 'x': -40}, {'opacity': 1, 'x': 0}, .35, 'power3.out')
    T(b - .18, f'#{i}', {'opacity': 0, 'scale': .96}, .2, 'power2.in')
    S(a - .16, 'whoosh', .8)

def sticker(t_in, t_out, inner, y=640, x=170, kind='pop', sfx='pop'):
    """人像上的贴纸：默认左侧一列（避开脸和右侧按钮栏）"""
    i = put(t_in, inner, x, y, kind, sfx)
    T(t_out - .2, f'#{i} > .in', {'opacity': 0, 'scale': .8}, .2, 'power2.in')
    return i
def pill(text, bg=None, fg=None, fs=40):
    return f'<div class="pill" style="background:{bg or NEON};color:{fg or INK};font-size:{fs}px">{text}</div>'
def node(inner, size, bg=None, border=None, extra=''):
    return (f'<div class="node" style="width:{size}px;height:{size}px;border-radius:{size / 2:.0f}px;background:{bg or TILE};'
            f'border:4px solid {border or LINE};{extra}">{inner}</div>')
def lab(text, color=None, fs=40):
    return f'<div class="lab" style="color:{color or WHITE};font-size:{fs}px">{text}</div>'
def counter(t, el_id, to, dur=1.0):
    """数字从 0 数到 to（元素 id=el_id）"""
    v = nid('cv')
    js.append(f'const {v}={{v:0}};tl.to({v},{{v:{to},duration:{dur},ease:"power2.out",onUpdate:()=>{{const e=document.getElementById("{el_id}");'
              f'if(e)e.textContent=Math.round({v}.v)}}}},{_t(t):.2f});')
def typewrite(t, el_id, text, dur=2.5):
    """打字机效果（元素 id=el_id）"""
    v = nid('tw')
    js.append(f'const {v}={{v:0}};const {v}s={json.dumps(text)};tl.to({v},{{v:{v}s.length,duration:{dur},ease:"none",onUpdate:()=>'
              f'{{const e=document.getElementById("{el_id}");if(e)e.textContent={v}s.slice(0,Math.round({v}.v))}}}},{_t(t):.2f});')
def settext(t, el_id, text):
    """t 秒把元素文字换成 text（往回拖也对）"""
    js.append(f'tl.call(()=>{{const e=document.getElementById("{el_id}");if(e)e.textContent={json.dumps(text)}}},null,{_t(t):.2f});')
def raw_js(code):
    """直接写 GSAP（tl 是时间轴）；里面的时间用 {R(秒数)} 换算"""
    js.append(code)

# ---- 跑这条视频的 scenes.py
sp = D / "scenes.py"
if not sp.is_file():
    die(f"没有 {sp}：照 scenes_example.py 写这条视频的画面")
exec(compile(sp.read_text(encoding="utf-8"), str(sp), "exec"), globals())

# ---- UI 层
top = f'<div id="ttl"><span>{TITLE}</span></div><div id="prog"><i id="pbar"></i></div>' if TITLE else ''
if TITLE:
    js.append(f'tl.fromTo("#pbar",{{scaleX:0}},{{scaleX:1,duration:{AROLL},ease:"none"}},0);')
CSS = (pathlib.Path(__file__).parent / "scenes.css").read_text(encoding="utf-8")
for k, v in C.items():
    CSS = CSS.replace("{" + k + "}", v)
ui = f'''<template>
<style>{FONT_CSS}
#root{{position:absolute;inset:0;font-family:{FALLBACK};color:{WHITE}}}
{CSS}
{chr(10).join(EXTRA_CSS)}
</style>
<div id="root" data-composition-id="ui" data-width="1080" data-height="1920" data-layout-allow-overflow data-layout-allow-overlap>
{"".join(els)}
{top}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(js)}
tl.set({{}},{{}},{TOTAL});
window.__timelines["ui"] = tl;
</script>
</template>
'''
COMP.mkdir(parents=True, exist_ok=True)
(COMP / "ui.html").write_text(ui, encoding="utf-8")

# ---- 字幕：大号粗黑体 + 黑描边，关键词荧光绿；有整屏图解时位置不变
KW = sorted(set(PLAN.get("keywords", [])), key=len, reverse=True)
def hi(t):
    t = html.escape(t)
    for k in KW:
        if k in t and f'>{k}' not in t:
            t = t.replace(k, f'<em>{k}</em>', 1)
    return t
def width(t): return sum(.55 if re.match(r'[A-Za-z0-9 ]', c) else 1 for c in t)
cd, cj = [], []
CAP_TOP = PLAN.get("caption_top", 1130)
for k, g in enumerate(CAPS):
    fs = min(78, int(900 / max(width(g['text']), 1)))
    cd.append(f'<div class="cap" id="cap{k}"><span style="font-size:{fs}px">{hi(g["text"])}</span></div>')
    s, e = g['start'], min(g['end'], AROLL - .02)
    cj.append(f'tl.set("#cap{k}",{{visibility:"visible"}},{s});tl.fromTo("#cap{k} span",{{scale:.86,opacity:0}},{{scale:1,opacity:1,duration:.12,ease:"back.out(2)"}},{s});tl.set("#cap{k}",{{visibility:"hidden"}},{e});')
(COMP / "captions.html").write_text(f'''<template>
<style>{FONT_CSS}
#root{{position:absolute;inset:0}}
.cap{{position:absolute;left:0;right:0;top:{CAP_TOP}px;text-align:center;visibility:hidden}}
.cap span{{display:inline-block;font-family:{FALLBACK};font-weight:900;color:#fff;line-height:1.2;letter-spacing:.02em;
 -webkit-text-stroke:12px #000;paint-order:stroke fill;text-shadow:0 6px 18px rgba(0,0,0,.5)}}
.cap em{{font-style:normal;color:{NEON}}}
</style>
<div id="root" data-composition-id="captions" data-width="1080" data-height="1920">
{chr(10).join(cd)}
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(cj)}
window.__timelines["captions"] = tl;
</script>
</template>
''', encoding="utf-8")

# ---- 主合成：人像跳切处换景别（1.0 / 1.12 交替，两次至少隔 2 秒）+ 开头慢推
GRAPHIC = [(_t(s['t_in']), min(_t(s['t_out']), TOTAL)) for s in scenes]
def hidden(t): return any(a <= t < b for a, b in GRAPHIC)
PUNCH, GAPMIN = PLAN.get("punch", 1.12), PLAN.get("punch_gap", 2.0)
pj, z, last = [], 1.0, PLAN.get("hook_push", 4.4)
for t in sorted([t for t in JUMPS if not hidden(t + .05)] + [b - .05 for a, b in GRAPHIC]):
    if t - last < GAPMIN:
        continue
    z = PUNCH if z == 1.0 else 1.0
    pj.append(f'tl.set("#cam",{{scale:{z}}},{t:.3f});'); last = t
if PLAN.get("hook_push", 4.4):
    pj.append(f'tl.fromTo("#cam",{{scale:1.0}},{{scale:1.1,duration:{PLAN.get("hook_push", 4.4)},ease:"power1.inOut"}},0);')
FY = PLAN.get("face_y", 760)
(HF / "index.html").write_text(f'''<!doctype html>
<html lang="zh-CN" data-resolution="portrait">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}}
#cam{{position:absolute;inset:0;transform-origin:540px {FY}px}}
#aroll{{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1080" data-height="1920">
<div id="cam"><video id="aroll" class="clip" src="assets/aroll.mp4" muted playsinline data-start="0" data-duration="{AROLL}" data-track-index="0"></video></div>
<div id="ui" data-composition-id="ui" data-composition-src="compositions/ui.html" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920" style="position:absolute;inset:0;z-index:5"></div>
<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" class="clip" data-start="0" data-duration="{AROLL}" data-track-index="2" data-track-kind="captions" data-width="1080" data-height="1920" style="position:absolute;inset:0;z-index:6"></div>
<audio id="voice" class="clip" src="assets/voice.wav" data-start="0" data-duration="{AROLL}" data-track-index="3" data-volume="1"></audio>
<audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{TOTAL}" data-track-index="4" data-volume="1"></audio>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(pj)}
tl.set({{}},{{}},{TOTAL});
window.__timelines["main"] = tl;
</script></body></html>
''', encoding="utf-8")
(D / "work/sfx_events.json").write_text(json.dumps(dict(dur=TOTAL, aroll=AROLL, ev=sorted(SFX, key=lambda e: e['t'])), indent=0), encoding="utf-8")
if not (HF / "assets/sfx.wav").exists():   # 混音前先放一条静音，check 才过得去
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(TOTAL), str(HF / "assets/sfx.wav")], check=True)
print(f"生成：{len(scenes)} 段图解（共 {sum(b - a for a, b in GRAPHIC):.1f} 秒）、{len(SFX)} 个音效点、{len(CAPS)} 组字幕，成片 {TOTAL} 秒")

r = hf(["check", "--json"], HF, capture=True)
try:
    rep = json.loads(r.stdout[r.stdout.find("{"):])
    errs = [f for f in rep.get("lint", {}).get("findings", []) if f.get("severity") == "error"]
    print("检查", "通过" if rep.get("ok") and not errs else "未通过")
    for f in errs:
        print(" -", f.get("code"), f.get("message", "")[:200])
except Exception:
    print(r.stdout[-1500:], r.stderr[-800:])
if args.snap:
    out = D / "work/snap"
    shutil.rmtree(out, ignore_errors=True)
    hf(["snapshot", "--at", args.snap, "--no-end", "-o", str(out)], HF, capture=True)
    print("关键帧：", *sorted(str(p) for p in out.glob("contact-sheet*.jpg")))
