#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dei-ppt 幻灯片引擎（白底黑字，可编辑）。
一份页面定义 → ①可编辑 PPTX（每行文字独立段落、配图独立对象、演讲者备注）②预览 PNG（自查用）③逐页讲稿 md
用法：内容文件 `from deck_engine import *`，用 S(讲稿, 元素, 段落) 逐页定义，最后调用 build(PPT目录, 文件名)。
运行：uv run --with python-pptx --with pillow python3 <内容文件>.py <PPT目录>
文字标记：{红色}  [蓝色]  ~删除线~"""
import os, re, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 13.333, 7.5
BLACK, GREY, LIGHT, RED, BLUE = '1A1A1A', '8A8A8A', 'C8C8C8', 'E60012', '1F5BD6'
FONT = 'Source Han Sans SC'
FONT_FILES = {False: os.path.expanduser('~/Library/Fonts/SourceHanSansSC-Regular.otf'),
              True: os.path.expanduser('~/Library/Fonts/SourceHanSansSC-Bold.otf')}
LS = 1.45  # 行距倍数（PPTX 与预览一致）

# ---------------- 元素 ----------------
def T(x, y, w, h, lines, size=28, bold=False, align='l', color=BLACK, anchor='t', ls=LS):
    if isinstance(lines, str): lines = lines.split('\n')
    return dict(k='text', x=x, y=y, w=w, h=h, lines=lines, size=size, bold=bold, align=align, color=color, anchor=anchor, ls=ls)
def IMG(path, x, y, w, h, border=False):
    return dict(k='img', path=path, x=x, y=y, w=w, h=h, border=border)
def R(x, y, w, h, fill='F5F5F7', line=None, dash=False, rounded=True, lw=1.5):
    return dict(k='rect', x=x, y=y, w=w, h=h, fill=fill, line=line, dash=dash, rounded=rounded, lw=lw)
def PH(x, y, w, h, label):
    return [R(x, y, w, h, fill='F4F4F4', line='B0B0B0', dash=True),
            T(x, y, w, h, ['截图位', label, '（课前用 WorkBuddy 实际跑一遍后替换）'], size=18, align='c', color=GREY, anchor='m')]

def parse(line, base):
    """{红} [蓝] ~删~ → [(text, color, strike)]"""
    out = []
    for m in re.finditer(r'\{([^}]*)\}|\[([^\]]*)\]|~([^~]*)~|([^{\[~]+)', line):
        if m.group(1) is not None: out.append((m.group(1), RED, False))
        elif m.group(2) is not None: out.append((m.group(2), BLUE, False))
        elif m.group(3) is not None: out.append((m.group(3), GREY, True))
        else: out.append((m.group(4), base, False))
    return out

# ---------------- 页面模板 ----------------
def statement(lines, sub=None, size=44):
    els = [T(1, 0.6, W - 2, 5.2 if sub else 6.3, lines, size=size, bold=True, align='c', anchor='m')]
    if sub: els.append(T(1, 5.6, W - 2, 1.2, sub, size=22, align='c', color=GREY, anchor='t'))
    return els

def titled(title, lines=None, size=28, img=None, img_box=None, top=2.0, width=None, ls=1.7):
    els = [T(0.9, 0.65, W - 1.8, 1.0, title, size=38, bold=True)]
    if lines:
        els.append(T(0.9, top, width or (6.6 if img else W - 1.8), H - top - 0.5, lines, size=size, ls=ls))
    if img:
        els.append(IMG(img, *(img_box or (8.2, 1.7, 4.4, 4.9))))
    return els

def bubble(text, x=6.2, y=1.9, w=6.2, size=20):
    n = len(text.split('\n'))
    h = n * size * LS / 72 + 0.5
    return [R(x, y, w, h, fill='E8EEF9'), T(x + 0.3, y + 0.25, w - 0.6, h - 0.4, text, size=size)]

def code(text, x=0.9, y=1.7, w=W - 1.8, size=17, hl=None):
    n = len(text.split('\n'))
    h = n * size * 1.5 / 72 + 0.6
    return [R(x, y, w, h, fill='F5F5F7'), T(x + 0.4, y + 0.3, w - 0.8, h - 0.4, text, size=size, ls=1.5)]

# ---------------- 素材路径 ----------------
def A(p): return os.path.join('assets', p)
IL = lambda n: A(f'il/il_{n}.png')
HERO = lambda n: A(f'hero/{n}.png')
def hero(img, title, sub=None, eyebrow=None, size=50, sub_size=22, top=None):
    """整页主视觉：右侧 AI 生成的纸艺画面，左侧留白放可编辑文字"""
    els = [IMG(HERO(img), 0, 0, W, H)]
    if eyebrow: els.append(T(0.9, 1.2, 5.4, 0.6, eyebrow, size=20, color=RED, bold=True))
    els.append(T(0.9, top or 1.9, 5.6, 2.6, title, size=size, bold=True, anchor='m', ls=1.3))
    if sub: els.append(T(0.9, (top or 1.9) + 2.8, 5.4, 2.4, sub, size=sub_size, color=GREY, ls=1.7))
    return els
def summary(img, eyebrow, title, points, foot=None):
    """模块总结页：右侧主视觉，左侧一句话 + 三条要点（拍照友好）"""
    els = [IMG(HERO(img), 0, 0, W, H),
           T(0.9, 0.8, 5.4, 0.6, eyebrow, size=18, color=RED, bold=True),
           T(0.9, 1.4, 5.8, 1.6, title, size=38, bold=True, anchor='m', ls=1.3)]
    for i, (a, b) in enumerate(points):
        y = 3.25 + i * 1.05
        els += [R(0.9, y + 0.12, 0.08, 0.7, fill=RED, rounded=False),
                T(1.2, y, 5.2, 0.5, a, size=22, bold=True),
                T(1.2, y + 0.48, 5.2, 0.45, b, size=16, color=GREY)]
    if foot: els.append(T(0.9, 6.55, 5.6, 0.5, foot, size=15, color=GREY))
    return els

# ---------------- 逐页 ----------------
SLIDES = []
def S(say, els, sec=''):
    flat = []
    for e in els: flat.extend(e if isinstance(e, list) else [e])
    SLIDES.append(dict(say=say, els=flat, sec=sec))
def EB(t):  # 页眉小字：当前在哪个模块
    return T(0.9, 0.3, 8, 0.5, t, size=15, color=GREY)

def progress(k, sections, subs=None, head='今天就讲三件事'):
    """路线图页：k=-1 全部点亮（总览），k=i 高亮第 i 段"""
    els = [T(0.9, 0.65, 6, 0.8, head, size=22, color=GREY)]
    gap = min(1.6, 4.8 / max(len(sections), 1))
    for i, s in enumerate(sections):
        cur = i == k; on = cur or k < 0
        els.append(T(1.6, 1.9 + i * gap, 10.5, 0.8, [f'{"{"}{i + 1}{"}"}　{s}' if cur else f'{i + 1}　{s}'],
                     size=36 if cur else 30, bold=on, color=BLACK if on else LIGHT, anchor='m'))
        if subs: els.append(T(2.25, 2.7 + i * gap, 10, 0.5, subs[i], size=18, color=GREY if on else LIGHT))
    return els

# ---------------- 输出：PPTX ----------------
def build_pptx(path, base):
    from pptx import Presentation
    from pptx.util import Inches, Pt, Emu
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.oxml.ns import qn
    prs = Presentation(); prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    AL = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}
    AN = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE}
    for s in SLIDES:
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        sl.background.fill.solid(); sl.background.fill.fore_color.rgb = RGBColor.from_string('FFFFFF')
        for e in s['els']:
            if e['k'] == 'rect':
                shp = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if e['rounded'] else MSO_SHAPE.RECTANGLE,
                                          Inches(e['x']), Inches(e['y']), Inches(e['w']), Inches(e['h']))
                if e['rounded']: shp.adjustments[0] = 0.08
                shp.fill.solid(); shp.fill.fore_color.rgb = RGBColor.from_string(e['fill'])
                if e['line']:
                    shp.line.color.rgb = RGBColor.from_string(e['line']); shp.line.width = Pt(e['lw'])
                    if e['dash']:
                        from pptx.enum.dml import MSO_LINE
                        shp.line.dash_style = MSO_LINE.DASH
                else: shp.line.fill.background()
                shp.shadow.inherit = False
            elif e['k'] == 'img':
                p = os.path.join(base, e['path'])
                iw, ih = Image.open(p).size
                sc = min(e['w'] / iw, e['h'] / ih); w, h = iw * sc, ih * sc
                x, y = e['x'] + (e['w'] - w) / 2, e['y'] + (e['h'] - h) / 2
                pic = sl.shapes.add_picture(p, Inches(x), Inches(y), Inches(w), Inches(h))
                if e['border']:
                    pic.line.color.rgb = RGBColor.from_string('D0D0D0'); pic.line.width = Pt(1)
            else:
                tb = sl.shapes.add_textbox(Inches(e['x']), Inches(e['y']), Inches(e['w']), Inches(e['h']))
                tf = tb.text_frame; tf.word_wrap = True
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                tf.vertical_anchor = AN[e['anchor']]
                for i, line in enumerate(e['lines']):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.alignment = AL[e['align']]; para.line_spacing = Pt(e['size'] * e['ls'])
                    for txt, col, strike in parse(line, e['color']) or [(' ', e['color'], False)]:
                        r = para.add_run(); r.text = txt
                        f = r.font; f.size = Pt(e['size']); f.bold = e['bold']; f.name = FONT
                        f.color.rgb = RGBColor.from_string(col)
                        rPr = r._r.get_or_add_rPr()
                        for tag in ('a:ea', 'a:cs'):
                            el = rPr.find(qn(tag))
                            if el is None:
                                el = rPr.makeelement(qn(tag), {}); rPr.append(el)
                            el.set('typeface', FONT)
                        if strike: rPr.set('strike', 'sngStrike')
        sl.notes_slide.notes_text_frame.text = s['say']
    prs.save(path)

# ---------------- 输出：预览 PNG ----------------
DPI = 120
def px(v): return int(round(v * DPI))
def hexc(c): return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
_fc = {}
def font(size, bold):
    k = (size, bold)
    if k not in _fc: _fc[k] = ImageFont.truetype(FONT_FILES[bold], int(size * DPI / 72))
    return _fc[k]

def wrap_runs(runs, f, maxw):
    """按宽度断行，返回 [[(text,color,strike)],...]"""
    lines, cur, cw = [], [], 0
    for txt, col, st in runs:
        for ch in txt:
            w = f.getlength(ch)
            if cw + w > maxw and cur:
                lines.append(cur); cur, cw = [], 0
            if cur and cur[-1][1] == col and cur[-1][2] == st:
                cur[-1] = (cur[-1][0] + ch, col, st)
            else: cur.append((ch, col, st))
            cw += w
    lines.append(cur)
    return lines

def render(s, base, out):
    im = Image.new('RGB', (px(W), px(H)), 'white'); d = ImageDraw.Draw(im)
    for e in s['els']:
        x, y, w, h = px(e['x']), px(e['y']), px(e['w']), px(e['h'])
        if e['k'] == 'rect':
            kw = dict(fill=hexc(e['fill']), outline=hexc(e['line']) if e['line'] else None, width=2 if e['line'] else 0)
            if e['rounded']: d.rounded_rectangle((x, y, x + w, y + h), radius=int(min(w, h) * 0.08), **kw)
            else: d.rectangle((x, y, x + w, y + h), **kw)
        elif e['k'] == 'img':
            p = Image.open(os.path.join(base, e['path'])).convert('RGB')
            sc = min(w / p.width, h / p.height); p = p.resize((int(p.width * sc), int(p.height * sc)))
            ox, oy = x + (w - p.width) // 2, y + (h - p.height) // 2
            im.paste(p, (ox, oy))
            if e['border']: d.rectangle((ox, oy, ox + p.width, oy + p.height), outline=(208, 208, 208), width=1)
        else:
            f = font(e['size'], e['bold']); lh = e['size'] * e['ls'] * DPI / 72
            rows = []
            for line in e['lines']:
                rows += wrap_runs(parse(line, e['color']) or [(' ', e['color'], False)], f, w)
            total = lh * len(rows)
            yy = y + (h - total) / 2 if e['anchor'] == 'm' else y
            for row in rows:
                rw = sum(f.getlength(t) for t, _, _ in row)
                xx = x + {'l': 0, 'c': (w - rw) / 2, 'r': w - rw}[e['align']]
                ty = yy + (lh - e['size'] * DPI / 72) / 2
                for t, col, st in row:
                    d.text((xx, ty), t, font=f, fill=hexc(col))
                    tw = f.getlength(t)
                    if st:
                        my = ty + e['size'] * DPI / 72 * 0.55
                        d.line((xx, my, xx + tw, my), fill=hexc(RED), width=max(2, int(e['size'] / 12)))
                    xx += tw
                yy += lh
                if yy > y + h + lh: print(f'  ⚠️ 文本溢出：{e["lines"][0][:12]}')
    im.save(out)

def build(base, filename, title='逐页讲稿'):
    os.makedirs(os.path.join(base, 'preview'), exist_ok=True)
    for i, s in enumerate(SLIDES, 1):
        render(s, base, os.path.join(base, 'preview', f'{i:02d}.png'))
    build_pptx(os.path.join(base, filename), base)
    md = [f'# {title}（{len(SLIDES)} 页）', '', '> 由 dei-ppt 内容文件生成；讲稿也已写进 PPTX 的演讲者备注。', '',
          '| 页 | 段落 | 页面文字 | 讲什么 |', '|---|---|---|---|']
    for i, s in enumerate(SLIDES, 1):
        txt = ' / '.join(re.sub(r'[{}\[\]~]', '', l) for e in s['els'] if e['k'] == 'text' for l in e['lines'] if l.strip())[:80]
        md.append(f"| {i} | {s['sec']} | {txt} | {s['say']} |")
    open(os.path.join(base, '逐页讲稿.md'), 'w', encoding='utf-8').write('\n'.join(md))
    print(f'✅ {len(SLIDES)} 页')

