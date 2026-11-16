#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dei-ppt 主题版：一条命令出 PPTX + 自查 + 预览图 + 逐页讲稿。

用法（在任意目录）：
  python3 build.py <内容文件.js> <PPT 输出目录> --name "<文件名>" [--checkin 签到轮播] [--no-render]
  python3 build.py --doctor            # 检查依赖，缺什么给一条安装命令

做的事：
  1. node 运行内容文件，生成 <name>.pptx（--checkin 时再生成一份自动循环的签到轮播）
  2. 自查：每页有讲稿、动画目标都找到、没有 #/8 位色值、文字没有明显溢出风险
  3. 渲染预览：macOS 有 Keynote 时用 Keynote（最接近讲者实际看到的），否则用 LibreOffice；
     隐藏页也出图，文件名带「_隐藏」
  4. 逐页讲稿.md（段落、页面文字、讲什么）+ 6 页一张的拼图 contact_*.png，供逐页目检
Windows 上把 python3 换成 python。
"""
import os, sys, json, shutil, subprocess, tempfile, glob, re, argparse, zipfile
os.environ.setdefault("PYTHONUTF8", "1")
HERE = os.path.dirname(os.path.abspath(__file__))
NM = os.environ.get("DEI_PPT_NODE_MODULES") or os.path.join(HERE, "node_modules")


def run(cmd, **kw):
    return subprocess.run(cmd, text=True, encoding="utf-8", errors="replace", capture_output=True, **kw)


def doctor():
    ok = True
    def need(name, good, fix):
        nonlocal ok
        print(("✅ " if good else "❌ ") + name + ("" if good else f"\n   安装：{fix}"))
        ok &= bool(good)
    need("Node.js", shutil.which("node"), "macOS: brew install node ｜ Windows: winget install OpenJS.NodeJS ｜ Linux: apt install nodejs npm")
    need("pptxgenjs（skill 自带 node_modules）", os.path.isdir(os.path.join(NM, "pptxgenjs")), f"cd \"{HERE}\" && npm install pptxgenjs@3.12.0")
    for mod in ("pptx", "PIL"):
        try: __import__(mod); good = True
        except Exception: good = False
        need(f"Python 包 {mod}", good, "pip install python-pptx pillow pymupdf")
    try: import fitz; good = True  # noqa
    except Exception: good = False
    need("Python 包 pymupdf（PDF 转预览图）", good, "pip install pymupdf")
    keynote = has_keynote()
    lo = find_soffice()
    need("渲染器（Keynote 或 LibreOffice，二选一）", keynote or lo, "macOS: brew install --cask libreoffice ｜ Windows: winget install TheDocumentFoundation.LibreOffice ｜ Linux: apt install libreoffice")
    fonts = font_check()
    need("思源黑体 Source Han Sans SC（或主题里指定的字体）", fonts, "下载 https://github.com/adobe-fonts/source-han-sans/releases（SC 子集），双击安装；或在内容文件 theme 里换成本机已有字体")
    return ok


def has_keynote():
    if sys.platform != "darwin" or os.environ.get("DEI_PPT_LIBREOFFICE"): return False
    r = run(["osascript", "-e", 'id of application "Keynote"'])
    return r.returncode == 0 and r.stdout.strip() != ""


def find_soffice():
    for c in [shutil.which("soffice"), "/Applications/LibreOffice.app/Contents/MacOS/soffice",
              r"C:\Program Files\LibreOffice\program\soffice.exe"]:
        if c and os.path.exists(c): return c
    return None


def lo_profile():
    """LibreOffice 在 macOS 上常看不到用户字体目录里的字体：建一个专用配置，把思源等字体复制进去。"""
    prof = os.path.join(os.path.expanduser("~"), ".cache", "dei-ppt", "lo_profile")
    fdir = os.path.join(prof, "user", "fonts"); os.makedirs(fdir, exist_ok=True)
    srcs = [os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", os.path.expanduser("~/.local/share/fonts"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Windows", "Fonts")]
    for d in srcs:
        for f in glob.glob(os.path.join(d, "*")):
            b = os.path.basename(f)
            if re.search(r"SourceHan|Source Han|NotoSansSC|NotoSansCJK|Bodoni", b) and not os.path.exists(os.path.join(fdir, b)):
                try: shutil.copy(f, fdir)
                except OSError: pass
    return "-env:UserInstallation=" + ("file:///" + prof.replace("\\", "/").lstrip("/"))


def font_check():
    if sys.platform == "darwin":
        r = run(["system_profiler", "SPFontsDataType"])
        return "Source Han Sans SC" in r.stdout or "SourceHanSansSC" in r.stdout
    if shutil.which("fc-list"):
        return "Source Han Sans" in run(["fc-list"]).stdout
    return any(glob.glob(os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "SourceHanSans*")))


def generate(content, out, checkin=False):
    env = dict(os.environ, DEI_PPT_ENGINE=os.path.join(HERE, "deck_engine.js"), DEI_PPT_NODE_MODULES=NM, NODE_PATH=NM)
    content, out = os.path.abspath(content), os.path.abspath(out)
    args = ["node", content, out] + (["checkin"] if checkin else [])
    r = run(args, env=env, cwd=os.path.dirname(os.path.abspath(content)))
    sys.stdout.write(r.stdout); sys.stderr.write(r.stderr)
    if r.returncode: sys.exit(f"生成失败：{content}")
    return [l for l in (r.stdout + r.stderr).splitlines() if "⚠️" in l]


def check(pptx):
    """轻量自查：讲稿、色值、溢出风险。返回问题列表。"""
    from pptx import Presentation
    from pptx.util import Emu
    probs = []
    with zipfile.ZipFile(pptx) as z:
        for n in z.namelist():
            if n.endswith(".xml"):
                x = z.read(n).decode("utf-8", "replace")
                bad = re.search(r'<a:srgbClr val="(?![0-9A-Fa-f]{6}")([^"]*)"', x)
                if bad: probs.append(f"{n}: 非法色值 {bad.group(1)}（只能 6 位十六进制、不带 #）")
    p = Presentation(pptx)
    for i, s in enumerate(p.slides, 1):
        if not (s.has_notes_slide and s.notes_slide.notes_text_frame.text.strip()):
            probs.append(f"第 {i} 页没有讲稿")
        for sh in iter_shapes(s.shapes):
            if not sh.has_text_frame or not sh.text_frame.text.strip() or sh.width is None: continue
            # 粗估：中文字宽 ≈ 字号、西文 ≈ 0.55 字号，行高 ≈ 1.25 字号；留 10% 余量
            w_pt, h_pt = Emu(sh.width).pt, Emu(sh.height).pt
            if w_pt < 20: continue
            lines, hmax = 0, 0
            for para in sh.text_frame.paragraphs:
                width, sz = 0, 18
                for r in para.runs:
                    sz = r.font.size.pt if r.font.size else sz
                    width += sum(sz if ord(ch) > 0x2E80 else sz * 0.55 for ch in r.text)
                    hmax = max(hmax, sz)
                lines += max(1, -(-int(width * 0.9) // int(w_pt)))
            size = hmax or 18
            if lines * size * 1.25 > h_pt * 1.6 + size:
                probs.append(f"第 {i} 页「{sh.text_frame.text[:16]}…」可能溢出（约 {int(lines)} 行，{size:.0f} 号）")
    return probs


def check_handbook(pptx, handbook):
    """内容从手册来：指令框的文字要在手册原文里逐字找得到；有进度条的动手页要标出手册章节。"""
    from pptx import Presentation
    norm = lambda t: re.sub(r"[\s　]+", "", t).replace("“", "「").replace("”", "」")
    hb = norm(open(handbook, encoding="utf-8").read())
    probs = []
    for i, s in enumerate(Presentation(pptx).slides, 1):
        if s._element.get("show") == "0": continue
        texts = [sh.text_frame.text for sh in iter_shapes(s.shapes) if sh.has_text_frame]
        for sh in s.shapes:
            if sh.shape_type == 6 and sh.name.startswith("指令"):
                for t in (x.text_frame.text for x in iter_shapes(sh.shapes) if x.has_text_frame and x.text_frame.text.strip()):
                    if norm(t) not in hb: probs.append(f"第 {i} 页指令和手册原文对不上：「{t[:30]}…」")
        is_hands = any(sh.name.startswith("progress-dot") for sh in iter_shapes(s.shapes))
        if is_hands and not any(t.startswith("手册") for t in texts):
            probs.append(f"第 {i} 页是动手页，但没标手册章节（foot(s, \"x.x\")）")
    return probs


def iter_shapes(shapes):
    for sh in shapes:
        if sh.shape_type == 6: yield from iter_shapes(sh.shapes)
        else: yield sh


def render(pptx, outdir, prefix):
    """渲染所有页（含隐藏页）为 PNG，返回按页排序的路径列表。"""
    from pptx import Presentation
    # Keynote 在沙盒里，写不进系统临时目录：临时文件放在输出目录旁边
    tmp = os.path.abspath(os.path.join(outdir, ".render_tmp")); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
    p = Presentation(pptx); hidden = [s._element.get("show") == "0" for s in p.slides]
    pngs = []
    if has_keynote():
        img = os.path.join(tmp, "img")
        r = run(["osascript", "-e", f'''tell application "Keynote"
  set d to open POSIX file "{os.path.abspath(pptx)}"
  export d to POSIX file "{img}" as slide images with properties {{image format:PNG, skipped slides:false}}
  close d saving no
end tell'''])
        pngs = sorted(glob.glob(os.path.join(img, "*.png")))
        if r.returncode: print("Keynote 渲染失败，改用 LibreOffice：", r.stderr.strip()[:200])
    pages = {}  # 页码 → png
    if pngs and len(pngs) == len(hidden): pages = {i + 1: f for i, f in enumerate(pngs)}
    elif pngs:  # Keynote 不导出隐藏页：按可见页顺序对应
        vis = [i + 1 for i, h in enumerate(hidden) if not h]
        pages = dict(zip(vis, pngs))
    if len(pages) < len(hidden):
        so = find_soffice()
        if not so:
            if not pages: print("没有渲染器，跳过预览（python3 build.py --doctor）"); return [], hidden
        else:
            # LibreOffice 也不导出隐藏页：另存一份取消隐藏的副本
            un = os.path.join(tmp, "deck.pptx")
            for s in p.slides: s._element.attrib.pop("show", None)
            p.save(un)
            run([so, lo_profile(), "--headless", "--convert-to", "pdf", "--outdir", tmp, un])
            import fitz
            d = fitz.open(os.path.join(tmp, "deck.pdf"))
            for i, pg in enumerate(d):
                if i + 1 in pages: continue
                f = os.path.join(tmp, f"lo-{i+1:03d}.png"); pg.get_pixmap(dpi=110).save(f); pages[i + 1] = f
    pngs = [pages[k] for k in sorted(pages)]
    os.makedirs(outdir, exist_ok=True)
    for f in glob.glob(os.path.join(outdir, f"{prefix}*.png")): os.remove(f)
    res = []
    for k in sorted(pages):
        dst = os.path.join(outdir, f"{prefix}{k:02d}{'_隐藏' if hidden[k - 1] else ''}.png")
        shutil.copy(pages[k], dst); res.append(dst)
    shutil.rmtree(tmp, ignore_errors=True)
    return res, hidden


def contact(pngs, outdir):
    from PIL import Image
    for f in glob.glob(os.path.join(outdir, "contact_*.png")): os.remove(f)
    for k in range(0, len(pngs), 6):
        ims = [Image.open(f).convert("RGB").resize((733, 412)) for f in pngs[k:k + 6]]
        g = Image.new("RGB", (733 * 2 + 10, 412 * 3 + 20), "white")
        for j, im in enumerate(ims): g.paste(im, ((j % 2) * 743, (j // 2) * 422))
        g.save(os.path.join(outdir, f"contact_{k // 6 + 1:02d}.png"))


def transcript(pptx, md, title):
    from pptx import Presentation
    p = Presentation(pptx)
    ns = {"p14": "http://schemas.microsoft.com/office/powerpoint/2010/main"}
    idsec = {}
    for sec in p.part._element.iterfind(".//p14:section", ns):
        for sid in sec.iterfind(".//p14:sldId", ns): idsec[sid.get("id")] = sec.get("name")
    rows, nh = [], 0
    for i, s in enumerate(p.slides, 1):
        hid = s._element.get("show") == "0"; nh += hid
        txt = " / ".join(sh.text_frame.text.replace("\n", " ").replace("\x0b", " ") for sh in iter_shapes(s.shapes)
                         if sh.has_text_frame and sh.text_frame.text.strip() and not re.fullmatch(r"\d+", sh.text_frame.text.strip()))[:90]
        note = s.notes_slide.notes_text_frame.text if s.has_notes_slide else ""
        rows.append(f"| {i}{'（隐藏）' if hid else ''} | {idsec.get(str(s.slide_id), '')} | {txt.replace('|', '｜')} | {note.replace('|', '｜').replace(chr(10), ' ')} |")
    head = [f"# 逐页讲稿｜{title}（{len(rows)} 页，其中 {nh} 页是隐藏备用页）", "",
            "> 由内容文件生成；讲稿也已写进 PPTX 的演讲者备注。（括号）里是给讲者的动作提示。", "",
            "| 页 | 段落 | 页面文字 | 讲什么 |", "|---|---|---|---|"]
    open(md, "w", encoding="utf-8").write("\n".join(head + rows) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("content", nargs="?"); ap.add_argument("outdir", nargs="?")
    ap.add_argument("--name", default="deck"); ap.add_argument("--checkin")
    ap.add_argument("--no-render", action="store_true"); ap.add_argument("--doctor", action="store_true")
    ap.add_argument("--handbook", help="学员手册（.md）：逐字核对指令、检查动手页有没有标章节")
    ap.add_argument("--pdf", action="store_true", help="另存一份备用 PDF（需要 LibreOffice）")
    a = ap.parse_args()
    if a.doctor: sys.exit(0 if doctor() else 1)
    if not (a.content and a.outdir): ap.error("需要 <内容文件.js> <输出目录>")
    os.makedirs(a.outdir, exist_ok=True)
    out = os.path.join(a.outdir, a.name + ".pptx")
    warns = generate(a.content, out)
    probs = warns + check(out)
    if a.handbook: probs += check_handbook(out, a.handbook)
    else: print("提示：没给 --handbook，跳过「指令和手册逐字一致」的核对")
    if a.checkin:
        ck = os.path.join(a.outdir, a.checkin + ".pptx"); generate(a.content, ck, checkin=True); probs += [f"[签到] {p}" for p in check(ck)]
    transcript(out, os.path.join(a.outdir, "逐页讲稿.md"), a.name)
    if not a.no_render:
        pngs, _ = render(out, os.path.join(a.outdir, "preview"), "")
        if pngs: contact(pngs, os.path.join(a.outdir, "preview"))
        if a.checkin: render(ck, os.path.join(a.outdir, "preview", "签到轮播"), "")
    if a.pdf and find_soffice():
        tmp = tempfile.mkdtemp(); r = run([find_soffice(), lo_profile(), "--headless", "--convert-to", "pdf", "--outdir", tmp, out])
        pdfs = glob.glob(os.path.join(tmp, "*.pdf"))
        if pdfs: shutil.move(pdfs[0], os.path.join(a.outdir, a.name + "（备用PDF）.pdf"))
    print("\n自查：" + ("全部通过" if not probs else f"{len(probs)} 处要看"))
    for p in probs: print("  - " + p)


if __name__ == "__main__":
    main()
