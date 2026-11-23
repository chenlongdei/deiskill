#!/usr/bin/env python3
"""给素材里的车牌、路人脸打马赛克：按 project.json 的 masks 生成 assets/video/<名>_masked.mp4，build.py 会自动改用打码版。

用法：
  python3 scripts/mask.py <工程>

project.json 里这样写（时间是素材自己的秒数，坐标是素材原始像素，cx/cy 是马赛克框中心）：
  "masks": [
    {"clip": "plant.mp4", "w": 140, "h": 84, "keys": [[1.5, 627, 647], [1.75, 600, 627], [3.5, 478, 648]]}
  ]
两个关键帧之间直线插值；keys 第一帧之前、最后一帧之后不打码。先用 ffmpeg 每 0.25 秒抽帧找位置，框留够余量。
"""
import subprocess, sys
from common import project, die


def lerp_expr(keys, idx):
    """关键帧 → ffmpeg 分段线性表达式（t 为素材时间）"""
    expr = str(keys[-1][idx])
    for (t0, *a), (t1, *b) in reversed(list(zip(keys, keys[1:]))):
        v0, v1 = a[idx - 1], b[idx - 1]
        seg = f"({v0}+({v1}-({v0}))*(t-{t0})/({t1}-{t0}))"
        expr = f"if(lt(t,{t1}),{seg},{expr})"
    return expr


d, P = project(sys.argv[1] if len(sys.argv) > 1 else ".")
masks = P.get("masks", [])
if not masks:
    die("project.json 里没有 masks")
for m in masks:
    src = d / "assets/video" / m["clip"]
    if not src.is_file():
        die(f"找不到素材 {src}")
    keys = sorted(m["keys"])
    w, h = m.get("w", 140) // 2 * 2, m.get("h", 84) // 2 * 2
    block = m.get("block", 12)
    cx, cy = lerp_expr(keys, 1), lerp_expr(keys, 2)
    x, y = f"max(0,min(iw-{w},{cx}-{w // 2}))", f"max(0,min(ih-{h},{cy}-{h // 2}))"
    ox, oy = f"max(0,min(W-{w},{cx}-{w // 2}))", f"max(0,min(H-{h},{cy}-{h // 2}))"
    t0, t1 = keys[0][0], keys[-1][0]
    fc = (f"[0:v]split[a][b];[b]crop={w}:{h}:'{x}':'{y}',scale={max(2, w // block)}:{max(2, h // block)},"
          f"scale={w}:{h}:flags=neighbor[m];[a][m]overlay=x='{ox}':y='{oy}':enable='between(t,{t0},{t1})'[v]")
    out = src.with_name(src.stem + "_masked.mp4")
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-filter_complex", fc, "-map", "[v]", "-map", "0:a?",
                        "-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p", "-c:a", "copy", str(out)])
    if r.returncode:
        die(f"打码失败：{m['clip']}")
    print(f"已打码：{out.name}（{t0}–{t1} 秒）")
print("下一步：finalize.py --snap-only，看打码处的关键帧有没有漏出来")
