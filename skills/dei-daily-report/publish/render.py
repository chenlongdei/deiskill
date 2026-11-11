#!/usr/bin/env python3
"""对外日报渲染：速览图卡 + 深度长文。

用法：
  python3 render.py <data.json> --out <输出目录> [--theme red]

data.json 的结构见 references/visual-standard.md；其中 "article" 指向文字版
Markdown（相对 data.json 所在目录）。输出：
  速览.html  速览/01_封面.png …      3:4 图卡，2160×2880
  长文.html  长文.png  长文分块/*.png   手机阅读宽度长文，1080 宽
渲染需要 playwright；优先用本机 Google Chrome，没有则用 playwright 自带的 Chromium。
字体从 Google Fonts 加载，渲染时需要联网。长图分段截图后用 Pillow 拼接；没有 Pillow 时按段保存。
"""
import argparse, json, pathlib, shutil, sys
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).resolve().parent
THEMES = ["red", "orange", "yellow", "blue", "green", "pink", "mint"]


def inject(tpl, data, md=None):
    s = (HERE / tpl).read_text(encoding="utf-8")
    s = s.replace("/*__REPORT__*/null", json.dumps(data, ensure_ascii=False).replace("</", "<\\/"), 1)
    if md is not None:
        s = s.replace("/*__MD__*/", md.replace("</script", "<\\/script"), 1)
    return s


def launch(p):
    try:
        return p.chromium.launch(channel="chrome")
    except Exception:
        return p.chromium.launch()


def ready(page, url):
    page.goto(url, wait_until="networkidle")
    page.wait_for_function("window.__ready === true", timeout=90000)


def shoot_tall(page, selector, path, chunk=3000):
    """长元素分段截图再拼接。Chrome 一次截图超过约 16000 像素会从头重复内容。"""
    box = page.locator(selector).bounding_box()
    scale = page.evaluate("devicePixelRatio")
    if box["height"] * scale <= 14000:
        page.locator(selector).screenshot(path=str(path))
        return
    parts, y = [], 0
    while y < box["height"]:
        h = min(chunk, box["height"] - y)
        parts.append(page.screenshot(clip={"x": box["x"], "y": box["y"] + y, "width": box["width"], "height": h}, full_page=True))
        y += h
    try:
        from PIL import Image
        import io
    except ImportError:
        for i, png in enumerate(parts, 1):
            path.with_name(f"{path.stem}_{i}{path.suffix}").write_bytes(png)
        return
    imgs = [Image.open(io.BytesIO(p)) for p in parts]
    out = Image.new("RGB", (imgs[0].width, sum(i.height for i in imgs)))
    top = 0
    for im in imgs:
        out.paste(im, (0, top)); top += im.height
    out.save(path)


def safe(name):
    return "".join(c for c in name if c not in '\\/:*?"<>|').strip() or "版块"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out", required=True, help="输出目录，放在用户确认的保存位置下")
    ap.add_argument("--theme", choices=THEMES)
    a = ap.parse_args()

    data_path = pathlib.Path(a.data).resolve()
    data = json.loads(data_path.read_text(encoding="utf-8"))
    if a.theme:
        data["theme"] = a.theme
    md = (data_path.parent / data["article"]).read_text(encoding="utf-8")

    out = pathlib.Path(a.out).resolve()
    if HERE.parent in out.parents or out == HERE.parent:
        sys.exit("输出目录不能放在 Skill 安装目录里，请改到用户确认的保存位置。")
    for d in ("速览", "长文分块"):
        shutil.rmtree(out / d, ignore_errors=True)
        (out / d).mkdir(parents=True)
    cards, article = out / "速览.html", out / "长文.html"
    cards.write_text(inject("cards.html", data), encoding="utf-8")
    article.write_text(inject("article.html", data, md), encoding="utf-8")

    names = ["封面"] + [c["kicker"] for c in data["cards"]]
    with sync_playwright() as p:
        b = launch(p)
        pg = b.new_page(viewport={"width": 1080, "height": 1440}, device_scale_factor=2)
        ready(pg, cards.as_uri() + "?export=1")
        for i, el in enumerate(pg.locator(".card").all()):
            el.screenshot(path=str(out / "速览" / f"{i+1:02d}_{safe(names[i])}.png"))
        pg = b.new_page(viewport={"width": 540, "height": 960}, device_scale_factor=2)
        ready(pg, article.as_uri() + "?export=1")
        shoot_tall(pg, "#wrap", out / "长文.png")
        pg.locator("#hero").screenshot(path=str(out / "长文分块" / "00_报头.png"))
        for i, el in enumerate(pg.locator("section.mod").all()):
            title = el.locator("h2").inner_text().strip()
            shoot_tall(pg, f"section.mod >> nth={i}", out / "长文分块" / f"{i+1:02d}_{safe(title)}.png")
        b.close()
    print(out)


if __name__ == "__main__":
    main()
