#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对比「我生成的 PPTX」和「用户在 Keynote / PowerPoint 里改过的版本」，产出改稿差异报告。
用法：uv run --with python-pptx --with pillow python3 keynote_diff.py <原版.pptx> <用户改版.key|.pptx> <输出目录>
- .key 会先复制到输出目录，再用 Keynote 导出 PPTX 和逐页 PNG（不碰用户原文件，不保存）。
- 输出：diff.md（逐页：新增/删除/改字/换图/讲稿变化）、changed_*.png（改动页拼图，供肉眼看）。"""
import os, sys, json, shutil, subprocess, difflib, glob, re
from pptx import Presentation
from pptx.util import Emu

def export_key(key, out):
    os.makedirs(os.path.join(out, 'img'), exist_ok=True)
    k = os.path.join(out, 'user.key'); shutil.copy(key, k)
    pp = os.path.join(out, 'user.pptx')
    subprocess.run(['osascript', '-e', f'''tell application "Keynote"
  set d to open POSIX file "{k}"
  export d to POSIX file "{pp}" as Microsoft PowerPoint
  export d to POSIX file "{out}/img" as slide images with properties {{image format:PNG, skipped slides:false}}
  close d saving no
end tell'''], check=True)
    return pp

def _walk(shapes):
    for sh in shapes:
        if sh.shape_type == 6: yield from _walk(sh.shapes)  # 组：讲者常把卡片和字打组，要钻进去
        else: yield sh

def _norm(t):
    # Keynote 导出会去掉中西文之间的空格、换掉换行符：比较前统一，免得误报
    return re.sub(r'\s+', '', t.replace('\x0b', ''))

def dump(p):
    out = []
    for s in Presentation(p).slides:
        texts, imgs, shapes = [], 0, 0
        for sh in _walk(s.shapes):
            if sh.has_text_frame and sh.text_frame.text.strip():
                t = sh.text_frame.text.replace('\n', ' / ').strip()
                if re.fullmatch(r'\d+', t): continue  # 页码
                texts.append(t)
            elif sh.shape_type == 13: imgs += 1
            else: shapes += 1
        notes = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ''
        anim = s._element.find('{http://schemas.openxmlformats.org/presentationml/2006/main}timing') is not None
        out.append(dict(text=' | '.join(texts), key=_norm(' | '.join(texts)), imgs=imgs, shapes=shapes, notes=notes, anim=anim,
                        hidden=s._element.get('show') == '0'))
    return out

def main(old, new, out):
    os.makedirs(out, exist_ok=True)
    if new.endswith('.key'): new = export_key(new, out)
    A, B = dump(old), dump(new)
    sm = difflib.SequenceMatcher(None, [a['key'] for a in A], [b['key'] for b in B], autojunk=False)
    lines = [f'# 改稿差异：原 {len(A)} 页 → 改后 {len(B)} 页', '']
    changed = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            for a, b, j in zip(A[i1:i2], B[j1:j2], range(j1, j2)):
                d = []
                if a['imgs'] != b['imgs']: d.append(f"图 {a['imgs']}→{b['imgs']}")
                if a['notes'].strip() != b['notes'].strip(): d.append('讲稿改了')
                if b['anim'] and not a['anim']: d.append('加了动画')
                if a['text'] != b['text'] and a['key'] == b['key']: d.append('只改了空格/换行')
                if d:
                    lines.append(f"- 第 {j+1} 页：" + '，'.join(d))
                    changed.append(j + 1)
            continue
        if tag in ('delete', 'replace'):
            for i in range(i1, i2): lines.append(f"- 删除/替换 原第 {i+1} 页：{A[i]['text'][:120]}")
        if tag in ('insert', 'replace'):
            for j in range(j1, j2):
                lines.append(f"- 新/改 第 {j+1} 页（图 {B[j]['imgs']}）：{B[j]['text'][:160] or '（无文字，整页截图/图片）'}")
                changed.append(j + 1)
    open(os.path.join(out, 'diff.md'), 'w', encoding='utf-8').write('\n'.join(lines))
    json.dump(dict(old=A, new=B), open(os.path.join(out, 'dump.json'), 'w'), ensure_ascii=False)
    imgs = sorted(glob.glob(os.path.join(out, 'img', '*.png')))
    # Keynote 导出图片时跳过隐藏页：按可见页对应页码
    vis = [i + 1 for i, b in enumerate(B) if not b['hidden']]
    img_of = dict(zip(vis, imgs)) if len(imgs) != len(B) else {i + 1: f for i, f in enumerate(imgs)}
    shown = [j for j in changed if j in img_of]
    if shown:
        from PIL import Image
        tw, th = 800, 450
        for n, k in enumerate(range(0, len(shown), 6)):
            grp = shown[k:k + 6]
            S = Image.new('RGB', (3 * (tw + 10), ((len(grp) + 2) // 3) * (th + 10)), 'black')
            for q, j in enumerate(grp):
                S.paste(Image.open(img_of[j]).convert('RGB').resize((tw, th)), ((q % 3) * (tw + 10), (q // 3) * (th + 10)))
            S.save(os.path.join(out, f'changed_{n+1}.png'))
    print('\n'.join(lines)); print(f'\n改动页：{changed}')

if __name__ == '__main__':
    main(*sys.argv[1:4])
