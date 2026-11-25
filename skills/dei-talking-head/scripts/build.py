#!/usr/bin/env python3
"""把工程的 scenes.py（这条视频的画面）套进市场版画面系统，生成 HyperFrames 工程，检查并出关键帧。

用法：
  python3 scripts/build.py <工程>                    生成 + check
  python3 scripts/build.py <工程> --snap 3,36,82     另外在这些成片秒数截图（拼图在 work/snap/）
  python3 scripts/build.py <工程> --snap auto        自动挑：首帧 + 每段图解 / 横条 / 砸屏 / 贴纸各一张（一次看全，少跑几轮）
  python3 scripts/build.py <工程> --overlay          另外生成 hf_overlay/（只有图解、贴纸、标题的透明层，给剪映草稿用，export.py 会调）
画面系统（references/scenes.md）：全屏人像 + 跳切交替推近（两次至少隔 2 秒）+ 常驻标题和进度条 + 大粗字幕
+ 讲结构时整屏切图解（墨黑 + 荧光绿）。scenes.py 里能用的函数见 scenes.md，例子见 templates/scenes_example.py。
"""
import argparse, html, json, os, pathlib, re, shutil, sys
from common import project, hf, die

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--snap", default="")
ap.add_argument("--overlay", action="store_true")
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
    """W() 算出的时间已经是当前剪辑的，不再换算。加减一个秒数后仍然是 _Now（W("某字") - .15 不能被当成旧剪辑的时间再换算一次）"""
    def __add__(self, o): return _Now(float(self) + float(o))
    __radd__ = __add__
    def __sub__(self, o): return _Now(float(self) - float(o)) if not isinstance(o, _Now) else float(self) - float(o)
    def __rsub__(self, o): return float(o) - float(self)
    def __mul__(self, o): return float(self) * float(o)
    __rmul__ = __mul__
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

# ---- 每条视频自己的样式（用户：「不要每个视频都一个样式」「位置、呈现形式要有自由度」）
# 按工程名定随机种子：同一条反复 build 不变，换一条就不同；同一文件夹里最近两条用过的样式尽量不再用。plan.json 可以写死。
import hashlib, random
RNG = random.Random(int(hashlib.md5((D.name + TITLE).encode("utf-8")).hexdigest()[:8], 16))
TITLE_STYLES = ["box", "tape", "marker", "kicker", "bar"]          # 常驻标题
SCENE_HEADS = ["left", "center", "bignum"]                         # 整屏图解的章节 + 大标题
STICKER_LOOKS = ["card", "tilt", "note", "outline", "bubble"]       # 人像贴纸的外观
def _recent(key):
    out = []
    for lp in sorted(D.parent.glob("*/work/layout.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if lp.parent.parent == D:
            continue
        try:
            v = json.loads(lp.read_text(encoding="utf-8")).get(key)
        except Exception:
            v = None
        if v:
            out.append(v)
        if len(out) >= 2:
            break
    return out
def _pick(key, options):
    if PLAN.get(key):
        return PLAN[key]
    fresh = [o for o in options if o not in _recent(key)] or options
    return RNG.choice(fresh)
TITLE_STYLE, SCENE_HEAD = _pick("title_style", TITLE_STYLES), _pick("scene_head", SCENE_HEADS)

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

PUTS = []   # (成片秒数, x, y, id)：查有没有放进字幕区
def put(t, inner, x, y, kind='up', sfx=None, v=1.0, z=None, cls=''):
    """在 (x, y)（画布坐标，元素中心）放一个元素，t 秒出现。kind：up / pop / slam / drop / left"""
    i = nid('e')
    PUTS.append((round(_t(t), 2), x, y, i))
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
AUTO_SNAP = []   # --snap auto：每段画面挑一个时刻
SEQ = []         # 实际用到的版式序列（variety.py 查重用）
def scene(t_in, t_out, chap, title):
    """整屏图解开始（盖住人像，口播继续）。chap：左上角小字章节；title：大标题。配 end_scene()"""
    sid = nid('sc')
    _cur[0] = dict(id=sid, t_in=t_in, t_out=t_out, start=len(els)); scenes.append(_cur[0]); SEQ.append((_t(t_in), 'scene'))
    m = re.match(r"\s*(\d+)\s*[·.、]?\s*(.*)", chap or "")
    if SCENE_HEAD == "bignum" and m:
        chap = f'<span class="bn">{m.group(1)}</span><span class="cr">{m.group(2)}</span>'
    els.append(f'<div class="chap">{chap}</div><div class="stitle">{title}</div>')
def end_scene():
    c = _cur[0]
    body = els[c['start']:]; del els[c['start']:]
    els.append(f'<div id="{c["id"]}" class="scene h-{SCENE_HEAD}" style="opacity:0"><div class="glow"></div>{"".join(body)}</div>')
    a, b, i = c['t_in'], c['t_out'], c['id']
    A(a - .12, f'#{i}', {'opacity': 0, 'y': 120, 'scale': 1.04}, {'opacity': 1, 'y': 0, 'scale': 1}, .32, 'power3.out')
    A(a - .12, f'#{i} .stitle', {'opacity': 0, 'x': -40} if SCENE_HEAD == "left" else {'opacity': 0, 'y': 24}, {'opacity': 1, 'x': 0, 'y': 0}, .35, 'power3.out')
    T(b - .18, f'#{i}', {'opacity': 0, 'scale': .96}, .2, 'power2.in')
    S(a - .16, 'whoosh', .8)
    AUTO_SNAP.append(_t(a + .75 * (b - a)))
    if TITLE:   # 图解有自己的标题：常驻标题和进度条让位，顶部只留一层，留出呼吸感（用户：「过于拥挤，没有呼吸感」）
        T(a - .12, '#ttl,#prog', {'opacity': 0}, .2, 'power2.out')
        T(b - .18, '#ttl,#prog', {'opacity': 1}, .25, 'power2.out')

# 人像上能放贴纸的位置（元素中心）：都在平台安全区里，避开眼睛和右侧按钮栏
# 不放下巴下方：脸在画面里偏低的原片会压住嘴（2026-11-24 实测）
SLOTS = {"左中": (175, 650), "左下": (210, 1000), "顶中": (540, 505), "右上": (765, 505)}
SLOT_KIND = {"左中": "left", "左下": "left", "顶中": "drop", "右上": "drop"}
_last = {"slot": None, "look": None}
USED = []   # (槽位, 外观)，写进 layout.json 给 variety.py
def sticker(t_in, t_out, inner, y=None, x=None, kind=None, sfx='pop', look=None, slot=None):
    """人像上的贴纸。不写 x 时自动轮换位置（左中 / 左下 / 顶中 / 右上 / 下巴，不连续两次同位置），外观也轮换
    （card 深底描边 / tilt 歪一点 / note 白纸 / outline 透明描边 / bubble 对话框），入场动作跟着位置变。
    要固定时写 slot="右上" 或 x、y；look="note"；kind="pop"。"""
    AUTO_SNAP.append(_t(t_in + .5 * (t_out - t_in))); SEQ.append((_t(t_in), 'sticker'))
    if x is None:
        fb = PLAN.get("face_box")   # [x0, y0, x1, y1]：眼睛到下巴那一块，近景时脸大，落在里面的位置不用
        ok = [k for k in SLOTS if not (fb and fb[0] <= SLOTS[k][0] <= fb[2] and fb[1] <= SLOTS[k][1] <= fb[3])] or list(SLOTS)
        slot = slot or RNG.choice([k for k in ok if k != _last["slot"]] or ok)
        x, y = SLOTS[slot]
        kind = kind or SLOT_KIND[slot]
    look = look or RNG.choice([k for k in STICKER_LOOKS if k != _last["look"]])
    _last.update(slot=slot, look=look); USED.append((slot or f"{x},{y}", look))
    i = put(t_in, f'<div class="lk lk-{look}">{inner}</div>', x, y, kind or 'pop', sfx)
    # 至少停 1.2 秒，淡出不能早于入场结束；否则入场动画最后执行，贴纸会一直挂到片尾（WorkBuddy 版的「读 TA 的传记」）
    a0, b0 = _t(t_in), _t(t_out)
    if b0 - a0 < 1.2:
        print(f"⚠ 贴纸只停 {b0 - a0:.2f} 秒（{a0:.1f} 秒处），已延长到 1.2 秒；检查 W() 是不是找到了更早的同一个词")
        b0 = a0 + 1.2
    T(_Now(max(b0 - .2, a0 + .55)), f'#{i} > .in', {'opacity': 0, 'scale': .8}, .2, 'power2.in')
    return i
def band(t_in, t_out, inner, y=575, kind='drop', sfx='whoosh'):
    """人像 + 横条：人脸留在画面里，图解放在标题下面一条宽卡里（默认 y≈485–665，压额头不压眼睛）。
    适合短的结构点（一个对比、一串 3 个节点、一个数字），不想整屏切走人脸时用。
    和左侧贴纸不同时出现；脸偏高的原片（看 --snap）把 y 往上挪或改放下巴下方（y≈1000，离字幕 30 像素以上）"""
    AUTO_SNAP.append(_t(t_in + .6 * (t_out - t_in))); SEQ.append((_t(t_in), 'band'))
    i = put(t_in, f'<div class="band">{inner}</div>', 540, y, kind, sfx, .7)
    T(_Now(max(_t(t_out) - .22, _t(t_in) + .6)), f'#{i} > .in', {'opacity': 0, 'y': 30}, .22, 'power2.in')
    return i
def punch(t_in, t_out, text, sub='', color=None, sfx='impact'):
    """大字砸屏：整屏只有一个词或数字（≤1.5 秒），给反常识、结论、转折用；一条视频最多 1–2 次"""
    AUTO_SNAP.append(_t(t_in + .5 * (t_out - t_in))); SEQ.append((_t(t_in), 'punch'))
    i = nid('pu')
    fs = min(220, int(860 / max(len(re.sub(r'<[^>]+>', '', text)), 1)))   # 一行放下
    els.append(f'<div id="{i}" class="punch" style="opacity:0"><div class="pw" style="color:{color or NEON};font-size:{fs}px">{text}</div>'
               f'{f"<div class=ps>{sub}</div>" if sub else ""}</div>')
    A(t_in, f'#{i}', {'opacity': 0}, {'opacity': 1}, .08, 'none')
    A(t_in, f'#{i} .pw', {'scale': 2.4, 'opacity': 0}, {'scale': 1, 'opacity': 1}, .26, 'power3.in')
    T(t_out - .15, f'#{i}', {'opacity': 0}, .15, 'power2.in')
    S(t_in, sfx, .8)
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
BROLL = []
def broll(t_in, t_out, file, media_start=0.0):
    """空镜：t_in–t_out 整屏换成空镜画面（口播继续），文件放 hf/assets/broll/（Mixkit 等可商用素材）。淡入、轻推近、淡出"""
    if not (HF / "assets/broll" / file).is_file():
        die(f"没有空镜 {file}：放进 hf/assets/broll/")
    BROLL.append((_t(t_in), _t(t_out), file, media_start)); SEQ.append((_t(t_in), 'broll'))
def raw_js(code):
    """直接写 GSAP（tl 是时间轴）；里面的时间用 {R(秒数)} 换算"""
    js.append(code)

# ---- 跑这条视频的 scenes.py
sp = D / "scenes.py"
if not sp.is_file():
    die(f"没有 {sp}：照 scenes_example.py 写这条视频的画面")
exec(compile(sp.read_text(encoding="utf-8"), str(sp), "exec"), globals())

# ---- UI 层
if "|" in TITLE:   # 「小字|大字」：kicker 样式上下两行，其他样式连成一行
    _k, _m = TITLE.split("|", 1)
    _ttl = f'<small>{_k}</small>{_m}' if TITLE_STYLE == "kicker" else f'{_k}，{_m}'
else:
    _ttl = TITLE
top = f'<div id="ttl" class="t-{TITLE_STYLE}"><span>{_ttl}</span></div><div id="prog"><i id="pbar"></i></div>' if TITLE else ''
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
# caption_style："bold"（默认，市场版：粗黑体 + 黑描边 + 弹出）/ "clean"（苹果风：细一档、不描边、柔和阴影、淡入）
CLEAN = PLAN.get("caption_style", "bold") == "clean"
CAP_CSS = ('font-weight:700;-webkit-text-stroke:0;text-shadow:0 2px 6px rgba(0,0,0,.55),0 6px 28px rgba(0,0,0,.45)' if CLEAN else
           '-webkit-text-stroke:12px #000;paint-order:stroke fill;text-shadow:0 6px 18px rgba(0,0,0,.5)')
for k, g in enumerate(CAPS):
    fs = min(66 if CLEAN else 78, int(900 / max(width(g['text']), 1)))
    cd.append(f'<div class="cap" id="cap{k}"><span style="font-size:{fs}px">{hi(g["text"])}</span></div>')
    s, e = g['start'], min(g['end'], AROLL - .02)
    if CLEAN:
        cj.append(f'tl.set("#cap{k}",{{visibility:"visible"}},{s});tl.fromTo("#cap{k} span",{{y:10,opacity:0}},{{y:0,opacity:1,duration:.18,ease:"power2.out"}},{s});tl.set("#cap{k}",{{visibility:"hidden"}},{e});')
    else:
        cj.append(f'tl.set("#cap{k}",{{visibility:"visible"}},{s});tl.fromTo("#cap{k} span",{{scale:.86,opacity:0}},{{scale:1,opacity:1,duration:.12,ease:"back.out(2)"}},{s});tl.set("#cap{k}",{{visibility:"hidden"}},{e});')
(COMP / "captions.html").write_text(f'''<template>
<style>{FONT_CSS}
#root{{position:absolute;inset:0}}
.cap{{position:absolute;left:0;right:0;top:{CAP_TOP}px;text-align:center;visibility:hidden}}
.cap span{{display:inline-block;font-family:{FALLBACK};font-weight:900;color:#fff;line-height:1.2;letter-spacing:.02em;{CAP_CSS}}}
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
br_tags, br_js = "", []
for k, (a, b, f, ms) in enumerate(BROLL):
    br_tags += (f'<video id="br{k}" class="clip broll" src="assets/broll/{f}" muted playsinline data-start="{a - .3:.2f}" data-duration="{b - a + .6:.2f}" '
                f'data-media-start="{max(0, ms - .3):.2f}" data-track-index="5"></video>')
    br_js += [f'tl.fromTo("#br{k}",{{opacity:0,scale:1.08}},{{opacity:1,scale:1.0,duration:.35,ease:"power2.out"}},{a - .3:.2f});',
              f'tl.to("#br{k}",{{opacity:0,duration:.3,ease:"power2.in"}},{b:.2f});']
(HF / "index.html").write_text(f'''<!doctype html>
<html lang="zh-CN" data-resolution="portrait">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:#000}}
#cam{{position:absolute;inset:0;transform-origin:540px {FY}px}}
#aroll{{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover}}
.broll{{position:absolute;left:0;top:0;width:1080px;height:1920px;object-fit:cover;z-index:2}}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1080" data-height="1920">
<div id="cam"><video id="aroll" class="clip" src="assets/aroll.mp4" muted playsinline data-start="0" data-duration="{AROLL}" data-track-index="0"></video></div>
{br_tags}
<div id="ui" data-composition-id="ui" data-composition-src="compositions/ui.html" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920" style="position:absolute;inset:0;z-index:5"></div>
<div id="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" class="clip" data-start="0" data-duration="{AROLL}" data-track-index="2" data-track-kind="captions" data-width="1080" data-height="1920" style="position:absolute;inset:0;z-index:6"></div>
<audio id="voice" class="clip" src="assets/voice.wav" data-start="0" data-duration="{AROLL}" data-track-index="3" data-volume="1"></audio>
<audio id="sfx" class="clip" src="assets/sfx.wav" data-start="0" data-duration="{TOTAL}" data-track-index="4" data-volume="1"></audio>
</div>
<script>
const tl = gsap.timeline({{ paused: true }});
{chr(10).join(pj)}
{chr(10).join(br_js)}
tl.set({{}},{{}},{TOTAL});
window.__timelines["main"] = tl;
</script></body></html>
''', encoding="utf-8")
(D / "work/sfx_events.json").write_text(json.dumps(dict(dur=TOTAL, aroll=AROLL, ev=sorted(SFX, key=lambda e: e['t'])), indent=0), encoding="utf-8")
punch_ev = [(float(x.split(",")[-1].rstrip(");")), float(re.search(r"scale:([\d.]+)", x).group(1))) for x in pj if x.startswith('tl.set("#cam"')]
(D / "work/layout.json").write_text(json.dumps(dict(aroll=AROLL, total=TOTAL, face_y=FY, punch=sorted(punch_ev), broll=BROLL, caps=CAPS,
                                                    caption_top=CAP_TOP, seq=[k for _, k in sorted(SEQ)], title_style=TITLE_STYLE,
                                                    scene_head=SCENE_HEAD, stickers=USED), ensure_ascii=False), encoding="utf-8")
if args.overlay:
    OV = D / "hf_overlay"
    (OV / "compositions").mkdir(parents=True, exist_ok=True)
    for f in ("hyperframes.json", "meta.json", "package.json"):
        shutil.copy2(HF / f, OV / f)
    shutil.copy2(COMP / "ui.html", OV / "compositions/ui.html")
    for sub in ("icons", "logos", "fonts"):
        shutil.rmtree(OV / "assets" / sub, ignore_errors=True)
        shutil.copytree(HF / "assets" / sub, OV / "assets" / sub)
    (OV / "index.html").write_text(f'''<!doctype html>
<html lang="zh-CN" data-resolution="portrait">
<head><meta charset="UTF-8" /><meta name="viewport" content="width=1080, height=1920" />
<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
<style>*{{margin:0;padding:0;box-sizing:border-box}} html,body{{margin:0;width:1080px;height:1920px;overflow:hidden;background:transparent}}</style></head>
<body><div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1080" data-height="1920">
<div id="ui" data-composition-id="ui" data-composition-src="compositions/ui.html" class="clip" data-start="0" data-duration="{TOTAL}" data-track-index="1" data-track-kind="graphics" data-width="1080" data-height="1920" style="position:absolute;inset:0"></div>
</div>
<script>const tl = gsap.timeline({{ paused: true }}); tl.set({{}},{{}},{TOTAL}); window.__timelines["main"] = tl;</script></body></html>
''', encoding="utf-8")
    print("透明图层工程：", OV)
if not (HF / "assets/sfx.wav").exists():   # 混音前先放一条静音，check 才过得去
    import subprocess
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(TOTAL), str(HF / "assets/sfx.wav")], check=True)
print(f"生成：{len(scenes)} 段图解（共 {sum(b - a for a, b in GRAPHIC):.1f} 秒）、{len(SFX)} 个音效点、{len(CAPS)} 组字幕，成片 {TOTAL} 秒")
print(f"样式：常驻标题 {TITLE_STYLE}，图解标题 {SCENE_HEAD}，贴纸 {len(USED)} 个（位置 {sorted({u[0] for u in USED})}，外观 {sorted({u[1] for u in USED})}）")
# 字幕区不放东西（用户：WorkBuddy 版「字幕遮挡后面动画」）：元素中心离字幕顶部不到 60 像素的都报出来
_bad = [(t, y, i) for t, x, y, i in PUTS if y > CAP_TOP - 60]
for t, y, i in _bad:
    print(f"⚠ 压字幕：{t:.1f} 秒的元素 {i} 放在 y={y}，字幕从 y={CAP_TOP} 开始。图解内容放在 560–1060，或者改 plan.json 的 caption_top")
def _zone(u):
    x, y = SLOTS[u] if u in SLOTS else map(float, u.split(","))
    return (round(x / 300), round(y / 250))
if len(USED) >= 4 and len({_zone(u[0]) for u in USED}) < 3:
    print("⚠ 贴纸位置太集中（少于 3 个位置）：去掉 sticker() 里写死的 x、y，让它自动轮换")

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
    at = args.snap
    if at == "auto":
        pts = sorted({round(x, 1) for x in [.5] + AUTO_SNAP if 0 <= x < TOTAL})
        at = ",".join(str(x) for x in pts[:16])
        print("自动关键帧：", at)
    hf(["snapshot", "--at", at, "--no-end", "-o", str(out)], HF, capture=True)
    print("关键帧：", *sorted(str(p) for p in out.glob("contact-sheet*.jpg")))
