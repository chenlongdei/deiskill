#!/usr/bin/env python3
"""画面查重：这条视频的 scenes.py 和同一文件夹下最近几条比，看是不是「一个模子刻出来的」。

比三样：① 版式序列（scene / band / sticker / punch / broll 按时间排）② 开头 4 秒的钩子用了什么 ③ 图解里的写法（对比卡、节点箭头、步骤行……）。
用法：python3 scripts/variety.py <工程> [--n 3] [--with <别的工程> ...]
版式序列优先读 build.py 写的 work/layout.json（自己包的函数也算得到），没有 build 过才从 scenes.py 里猜。
相似度 ≥ 0.6 的报 ⚠，要回去改画面方案；用户说过「重复有价值，但位置、顺序、模块几乎一样就太单调了」。
"""
import argparse, difflib, json, pathlib, re
from common import project

ap = argparse.ArgumentParser()
ap.add_argument("project")
ap.add_argument("--n", type=int, default=3, help="和最近几条比")
ap.add_argument("--with", dest="others", action="append", default=[], help="另外指定要比的工程（不在同一文件夹的）")
a = ap.parse_args()
d, _ = project(a.project)

LAYOUT = re.compile(r"^\s*(?:\w+\s*=\s*)?(scene|band|sticker|punch|broll)\(\s*([\d.]+|W\()", re.M)
MOTIF = {"对比卡": r"\.cmp|vcard|VS", "节点+箭头": r"node\(|class=\"arrow", "步骤行": r"class=\"step", "划掉": r"strike",
         "计数": r"counter\(", "打字": r"typewrite\(", "气泡": r"class=\"bub", "柱条": r"class=\"bars", "标签胶囊": r"pill\(",
         "logo": r"logo\(", "空镜": r"broll\(", "砸屏": r"punch\(", "横条": r"band\("}


def profile(p):
    s = p.read_text(encoding="utf-8")
    lay = p.parent / "work/layout.json"
    seq = None
    if lay.is_file():
        seq = json.loads(lay.read_text(encoding="utf-8")).get("seq")
    if not seq:
        seq = [m.group(1) for m in LAYOUT.finditer(s)]
    head = seq[:2]
    motifs = {k for k, rx in MOTIF.items() if re.search(rx, s)}
    return seq, head, motifs


me = d / "scenes.py"
if not me.is_file():
    raise SystemExit(f"{me} 还没写")
seq, head, motifs = profile(me)
others = sorted((p for p in d.parent.glob("*/scenes.py") if p.parent != d), key=lambda p: p.stat().st_mtime, reverse=True)[:a.n]
others += [pathlib.Path(o).resolve() / "scenes.py" for o in a.others if (pathlib.Path(o) / "scenes.py").is_file()]
tpl = pathlib.Path(__file__).resolve().parent.parent / "templates/scenes_example.py"
if tpl.is_file():
    others.append(tpl)

kinds = {k: seq.count(k) for k in dict.fromkeys(seq)}
print(f"这条：{len(seq)} 段画面 {kinds}；开头 {head}；写法 {sorted(motifs)}")
bad = 0
if len(set(seq)) < 3:
    print("⚠ 版式少于 3 种（scene / band / sticker / punch / broll / 纯人像留白），整条会一个节奏"); bad += 1
for p in others:
    s2, h2, m2 = profile(p)
    r = difflib.SequenceMatcher(None, seq, s2).ratio()
    j = len(motifs & m2) / max(len(motifs | m2), 1)
    same_head = head == h2
    flag = "⚠" if r >= .6 or j >= .75 or same_head else "✓"
    bad += flag == "⚠"
    name = "Skill 示例" if p == tpl else p.parent.name
    print(f"{flag} 对比 {name}：版式序列相似 {r:.2f}，写法重合 {j:.2f}{'，开头钩子一样' if same_head else ''}")
# 样式：常驻标题、图解标题、贴纸位置
def styles(p):
    lay = p.parent / "work/layout.json"
    if not lay.is_file():
        return None
    L = json.loads(lay.read_text(encoding="utf-8"))
    return L.get("title_style"), L.get("scene_head"), [u[0] for u in L.get("stickers", [])]
mine = styles(me)
if mine:
    t, h, slots = mine
    print(f"样式：常驻标题 {t}，图解标题 {h}，贴纸位置 {dict((k, slots.count(k)) for k in dict.fromkeys(slots))}")
    if slots and max(slots.count(k) for k in set(slots)) / len(slots) > .6:
        print("⚠ 贴纸一大半挤在同一个位置：去掉写死的 x、y"); bad += 1
    for p in others:
        o = styles(p)
        if o and o[0] == t and o[1] == h:
            print(f"⚠ 和 {p.parent.name} 的常驻标题、图解标题样式完全一样：plan.json 换 title_style / scene_head"); bad += 1
print("结论：" + ("太像了，回 画面方案.md 换版式、换顺序、换钩子" if bad else "够不一样"))
