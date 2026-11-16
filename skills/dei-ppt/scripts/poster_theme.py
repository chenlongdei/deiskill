#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从一张主题图（海报）适配 PPT 风格。Windows 上把 python3 换成 python。

  python3 poster_theme.py palette <海报>                      打印 12 个主题色建议（JSON，贴进 createDeck({theme:{colors}})）
  python3 poster_theme.py backgrounds <海报> <assets 目录>     生成 bg_cover.jpg / bg_section.jpg / bg_content.jpg
  python3 poster_theme.py logo <图> <x0,y0,x1,y1> <输出.png> [--invert]
        从海报上抠 logo：去背景、改成墨黑色、透明底。--invert 用于深色底白字的 logo
依赖：pip install pillow numpy
"""
import sys, json, colorsys
import numpy as np
from PIL import Image, ImageFilter

W, H = 1920, 1080


def hexc(rgb): return "".join(f"{int(max(0, min(255, c))):02X}" for c in rgb)


def mix(a, b, t): return tuple(a[i] * (1 - t) + b[i] * t for i in range(3))


def dominant(path, k=8):
    im = Image.open(path).convert("RGB"); im.thumbnail((400, 400))
    q = im.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: k * 3]; counts = sorted(q.getcolors(), reverse=True)
    return [(n, tuple(pal[i * 3:i * 3 + 3])) for n, i in counts]


def palette(path):
    cols = dominant(path, 10)
    def sat(c): h, l, s = colorsys.rgb_to_hls(*[x / 255 for x in c]); return s, l
    # 主强调：饱和度够、亮度适中、占比高的那个
    cands = [(n * (sat(c)[0] + .05), c) for n, c in cols if .25 < sat(c)[1] < .7 and sat(c)[0] > .2]
    acc = max(cands)[1] if cands else (110, 95, 192)
    h, l, s = colorsys.rgb_to_hls(*[x / 255 for x in acc])
    acc = tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, min(max(l, .45), .55), max(s, .4)))
    acc2 = tuple(int(v * 255) for v in colorsys.hls_to_rgb((h + .04) % 1, .72, .6))
    ink = tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, .12, .15))
    grey = tuple(int(v * 255) for v in colorsys.hls_to_rgb(h, .37, .12))
    white = (255, 255, 255)
    t = {"dk1": hexc(ink), "lt1": "FFFFFF", "dk2": hexc(grey), "lt2": hexc(mix(white, acc, .05)),
         "accent1": hexc(acc), "accent2": hexc(acc2), "accent3": hexc(mix(white, acc, .13)), "accent4": "E5484D",
         "accent5": hexc(mix(white, acc, .45)), "accent6": hexc(mix(white, acc2, .25)), "hlink": hexc(acc), "folHlink": hexc(acc2)}
    print(json.dumps(t, ensure_ascii=False, indent=2))
    return t


def _blobs(cols, n, seed, base):
    r = np.random.default_rng(seed); img = np.ones((H, W, 3)) * np.array(base) / 255
    yy, xx = np.mgrid[0:H, 0:W]
    for _ in range(n):
        c = np.array(cols[r.integers(len(cols))]) / 255
        cx, cy = r.uniform(-.1, 1.1) * W, r.uniform(-.1, 1.1) * H
        sx, sy = r.uniform(.15, .45) * W, r.uniform(.15, .5) * H
        g = np.exp(-(((xx - cx) / sx) ** 2 + ((yy - cy) / sy) ** 2)) * r.uniform(.5, .95)
        img = img * (1 - g[..., None]) + c * g[..., None]
    return img


def _streak(img, seed, amt=1.0):
    """海报常见的横向拉丝：按行错位 + 横向模糊。主题图不是拉丝风格时把 amt 调小或设 0。"""
    r = np.random.default_rng(seed); out = img.copy(); y = 0
    while y < H:
        h = int(r.integers(2, 26)); s = int(r.integers(-160, 160) * amt)
        out[y:y + h] = np.roll(img[y:y + h], s, axis=1); y += h
    p = Image.fromarray((out * 255).clip(0, 255).astype(np.uint8)).resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BICUBIC)
    a = np.asarray(p).astype(float) / 255
    soft = np.asarray(Image.fromarray((img * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(40))).astype(float) / 255
    return soft * (1 - .55 * amt) + a * .55 * amt


def backgrounds(path, outdir, streak=0.9):
    # 取海报里有颜色的那几种（灰白不算），按「占比 × 饱和度」排；不够就用主色换色相、换亮度补齐
    def hls(c): return colorsys.rgb_to_hls(*[x / 255 for x in c])
    vivid = [c for n, c in sorted(dominant(path, 16), key=lambda t: -t[0] * (hls(t[1])[2] + .01)) if hls(t := c)[2] > .18 and .3 < hls(c)[1] < .9][:5]
    h0, _, s0 = hls(vivid[0]) if vivid else (.70, .5, .5)
    while len(vivid) < 4:
        k = len(vivid); vivid.append(tuple(int(v * 255) for v in colorsys.hls_to_rgb((h0 + (k - 2) * .03) % 1, .62 + .05 * k, max(s0, .5))))
    # 调到海报背景常见的亮度区间（0.6—0.85），再加白色让画面透气
    light = [tuple(int(v * 255) for v in colorsys.hls_to_rgb(hls(c)[0], min(max(hls(c)[1], .62), .85), max(hls(c)[2], .45))) for c in vivid]
    light += [(255, 255, 255), (250, 249, 255)]
    base = mix(light[0], (255, 255, 255), .82)
    for name, seed in (("bg_cover.jpg", 3), ("bg_section.jpg", 11)):
        img = _streak(_blobs(light, 20, seed, base), seed, streak) * .78 + .22
        Image.fromarray((img * 255).clip(0, 255).astype(np.uint8)).save(f"{outdir}/{name}", quality=92); print(name)
    yy, xx = np.mgrid[0:H, 0:W]
    img = np.ones((H, W, 3)) * np.array(mix(base, (255, 255, 255), .6)) / 255
    for (cx, cy, c, s) in [(W * 1.02, -H * .05, light[0], .32), (-W * .04, H * 1.05, light[min(1, len(light) - 1)], .30), (W, H * 1.1, light[min(2, len(light) - 1)], .22)]:
        g = np.exp(-(((xx - cx) / (s * W)) ** 2 + ((yy - cy) / (s * W * .8)) ** 2)) * .75
        img = img * (1 - g[..., None]) + np.array(c) / 255 * g[..., None]
    img = _streak(img, 5, streak * .4)
    Image.fromarray((img * 255).clip(0, 255).astype(np.uint8)).save(f"{outdir}/bg_content.jpg", quality=92); print("bg_content.jpg")


def logo(path, box, out, invert=False, ink=(30, 27, 36)):
    im = Image.open(path).convert("RGBA")
    if box: im = im.crop(tuple(int(v) for v in box.split(",")))
    im = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
    a = np.asarray(im).astype(float)
    if invert:  # 深色底白字：越亮越不透明
        lum = a[..., :3].min(axis=2)
        alpha = np.clip((lum - 95) / (235 - 95), 0, 1) * (a[..., 3] / 255)
    else:       # 浅色底深字：比周围背景暗多少就多不透明
        g = np.asarray(Image.fromarray(a[..., :3].mean(axis=2).astype(np.uint8)))
        bg = np.asarray(Image.fromarray(g).filter(ImageFilter.MaxFilter(31)).filter(ImageFilter.GaussianBlur(20))).astype(float)
        alpha = np.clip((bg - g - 18) / np.maximum(bg - 60, 1), 0, 1); alpha[alpha < .3] = 0
    o = np.zeros(a.shape, np.uint8); o[..., 0], o[..., 1], o[..., 2] = ink; o[..., 3] = (alpha * 255).astype(np.uint8)
    img = Image.fromarray(o); img = img.crop(img.getbbox()); img.save(out)
    print(out, img.size, "ratio =", round(img.width / img.height, 3))


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    if a[0] == "palette": palette(a[1])
    elif a[0] == "backgrounds": backgrounds(a[1], a[2])
    elif a[0] == "logo": logo(a[1], a[2] if a[2] != "-" else None, a[3], invert="--invert" in a)
    else: sys.exit(__doc__)
