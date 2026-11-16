#!/usr/bin/env python3
"""个人介绍库工具：定位介绍库、建骨架、筛案例、重建案例索引、生成 PDF。

    python3 scripts/profile_lib.py where
    python3 scripts/profile_lib.py init <路径>
    python3 scripts/profile_lib.py cases --query "餐饮 获客" [--audience 老板] [--who 学员] [--top 5] [--all]
    python3 scripts/profile_lib.py index
    python3 scripts/profile_lib.py pdf <介绍.md> [--out x.pdf] [--label "封面右上角"] [--short "页眉"]

介绍库位置：本 Skill 的 config.json 里的 library_root；没有时用 dei 工作区的 05_成品/个人介绍/。
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
CONFIG = Path(os.environ.get("DEI_PROFILE_CONFIG") or SKILL_DIR / "config.json")
SUBDIRS = ("01_个人介绍/定制", "01_个人介绍/历史版本", "02_PDF", "03_参考资料/00_原始文件", "05_案例库")
CASE_DIR = "05_案例库"
INDEX = "案例索引.md"
APPENDIX_RE = re.compile(r"\n#\s*附录")


# ---------------- 介绍库位置 ----------------

def _config() -> dict:
    if CONFIG.is_file():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {}


def library(must_exist: bool = True) -> Path:
    value = _config().get("library_root", "").strip()
    if value:
        path = Path(value).expanduser()
    else:
        sys.path.insert(0, str(HERE))
        import dei_workspace  # noqa: E402
        path = dei_workspace.stage("profile", create=False)
    if must_exist and not path.is_dir():
        hint = "上一级目录也不在，多半是外接盘或云盘没有挂载/同步。" if not path.parent.exists() else ""
        raise SystemExit(
            f"找不到介绍库：{path}。{hint}"
            "还没建库的话，按 SKILL.md Step 0 问用户放在哪，确认后运行 profile_lib.py init <路径>；不要静默新建。"
        )
    return path


def profile_info(lib: Path) -> dict:
    p = lib / "profile.json"
    info = json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}
    info.setdefault("name", lib.name)
    info.setdefault("brand_en", "")
    info.setdefault("city", "")
    info.setdefault("contact", "")
    return info


def cmd_where(_a) -> int:
    lib = library(must_exist=False)
    cards = sorted((lib / CASE_DIR).glob("*.md")) if (lib / CASE_DIR).is_dir() else []
    print(json.dumps({
        "library": str(lib),
        "exists": lib.is_dir(),
        "configured": bool(_config().get("library_root")),
        "cases": len([c for c in cards if c.name != INDEX]),
        "intro_docs": [p.name for p in sorted((lib / "01_个人介绍").glob("*.md"))] if lib.is_dir() else [],
        "pdfs": [p.name for p in sorted((lib / "02_PDF").glob("*.pdf"))] if lib.is_dir() else [],
        "profile": profile_info(lib) if lib.is_dir() else None,
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_init(a) -> int:
    lib = Path(a.path).expanduser().resolve()
    lib.mkdir(parents=True, exist_ok=True)
    made = []
    for sub in SUBDIRS:
        d = lib / sub
        if not d.exists():
            d.mkdir(parents=True)
            made.append(sub)
    prof = lib / "profile.json"
    if not prof.exists():
        prof.write_text(json.dumps({"name": "", "brand_en": "", "city": "", "contact": ""}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        made.append("profile.json")
    tpl = SKILL_DIR / "templates" / "案例卡片模板.md"
    if tpl.is_file() and not (lib / CASE_DIR / "_案例卡片模板.md").exists():
        shutil.copy(tpl, lib / CASE_DIR / "_案例卡片模板.md")
        made.append(f"{CASE_DIR}/_案例卡片模板.md")
    cfg = _config()
    cfg["library_root"] = str(lib)
    CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"library": str(lib), "created": made, "config": str(CONFIG)}, ensure_ascii=False, indent=2))
    return 0


# ---------------- 案例卡片 ----------------

def parse_card(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    meta: dict = {}
    for line in m.group(1).splitlines():
        line = re.sub(r"\s+#.*$", "", line)
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        if v.startswith("[") and v.endswith("]"):
            meta[k.strip()] = [x.strip().strip("\"'") for x in v[1:-1].split(",") if x.strip()]
        else:
            meta[k.strip()] = v.strip("\"'")
    meta["body"] = text[m.end():]
    meta["file"] = path.name
    return meta


def load_cards(lib: Path) -> list[dict]:
    d = lib / CASE_DIR
    if not d.is_dir():
        return []
    cards = []
    for p in sorted(d.glob("*.md")):
        if p.name == INDEX or p.name.startswith("_"):
            continue
        c = parse_card(p)
        if c:
            cards.append(c)
    return cards


def _aslist(v) -> list[str]:
    return v if isinstance(v, list) else ([v] if v else [])


def cmd_cases(a) -> int:
    lib = library()
    terms = [t for t in re.split(r"[\s,，、;；]+", a.query or "") if t]
    out = []
    for c in load_cards(lib):
        if c.get("public") == "不对外" and not a.all:
            continue
        if a.who and c.get("who") != a.who:
            continue
        aud = _aslist(c.get("audience"))
        score, hits = 0, []
        if a.audience:
            if a.audience in aud:
                score += 3
                hits.append(f"读者:{a.audience}")
            elif not terms:
                continue
        tags = " ".join(_aslist(c.get("problems")) + _aslist(c.get("industry")))
        for t in terms:
            s = 0
            if t in c.get("title", ""):
                s += 3
            if t in tags:
                s += 2
            if t in c["body"]:
                s += 1
            if s:
                score += s
                hits.append(t)
        if terms and not any(h for h in hits if not h.startswith("读者:")):
            continue
        # 老板、政企更信亲手交付和授课；个人、学员、社区更能代入学员的结果
        who = c.get("who", "")
        if (a.audience in ("老板", "政企") and who in ("亲手交付", "授课")) or \
           (a.audience in ("个人", "学员", "社区") and who == "学员"):
            score += 2
        if any(n.strip("—- ") for n in _aslist(c.get("numbers"))):
            score += 1
        if c.get("public") == "可点名":
            score += 0.5
        out.append({
            "score": score, "title": c.get("title", ""), "who": c.get("who", ""),
            "audience": aud, "problems": _aslist(c.get("problems")),
            "numbers": _aslist(c.get("numbers")), "public": c.get("public", ""),
            "file": f"{CASE_DIR}/{c['file']}", "matched": hits,
        })
    out.sort(key=lambda x: -x["score"])
    print(json.dumps({"library": str(lib), "query": terms, "results": out[: a.top]}, ensure_ascii=False, indent=2))
    return 0


def cmd_index(_a) -> int:
    lib = library()
    cards = load_cards(lib)
    order = {"亲手交付": 0, "个人成绩": 1, "授课": 2, "学员": 3}
    cards.sort(key=lambda c: (order.get(c.get("who", ""), 9), c["file"]))
    rows = ["# 案例索引", "", f"> 由 `profile_lib.py index` 生成，共 {len(cards)} 个案例。改卡片后重新生成，不要手改本文件。", "",
            "| 一句话结果 | 谁做的 | 讲给谁 | 解决什么 | 关键数字 | 点名 | 卡片 |", "|---|---|---|---|---|---|---|"]
    for c in cards:
        rows.append("| {} | {} | {} | {} | {} | {} | [{}]({}) |".format(
            c.get("title", ""), c.get("who", ""), "、".join(_aslist(c.get("audience"))),
            "、".join(_aslist(c.get("problems"))), "；".join(_aslist(c.get("numbers"))),
            c.get("public", ""), c["file"].removesuffix(".md"), c["file"]))
    (lib / CASE_DIR / INDEX).write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"✓ {lib / CASE_DIR / INDEX}（{len(cards)} 个案例）")
    return 0


# ---------------- PDF ----------------

def _md():
    try:
        import markdown  # noqa: F401
        return markdown
    except ImportError:
        raise SystemExit("缺少 Python 包 markdown：请运行 pip install markdown（Windows 上用 python -m pip install markdown）")


def _chrome() -> str:
    env = os.environ.get("PROFILE_CHROME")
    cands = [env] if env else []
    if sys.platform == "darwin":
        cands += ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                  "/Applications/Chromium.app/Contents/MacOS/Chromium",
                  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    elif sys.platform.startswith("win"):
        for base in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
            if base:
                cands += [os.path.join(base, "Google", "Chrome", "Application", "chrome.exe"),
                          os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe")]
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            cands.append(found)
    for c in cands:
        if c and Path(c).exists():
            return c
    raise SystemExit("找不到 Chrome / Chromium / Edge：请安装其一，或用环境变量 PROFILE_CHROME 指定可执行文件路径")


def _normalize(md: str) -> str:
    out, prev = [], ""
    for line in md.splitlines():
        if re.match(r"^  [-*] ", line):
            line = "  " + line
        is_item = re.match(r"^\s*([-*]|\d+\.) ", line)
        prev_item = re.match(r"^\s*([-*]|\d+\.) ", prev) or prev.startswith("  ")
        if is_item and prev.strip() and not prev_item and not prev.startswith(">"):
            out.append("")
        out.append(line)
        prev = line
    return "\n".join(out)


def _inline(markdown, text: str) -> str:
    s = markdown.markdown(text)
    return s[3:-4] if s.startswith("<p>") and s.endswith("</p>") else s


def _ph(label: str, quote: bool = False, extra: str = "") -> str:
    label = re.sub(r"^【(配图|学员原话)】", "", label).strip()
    kind = "学员原话 / 反馈截图" if quote else "插图位"
    return (f'<div class="ph{" quote" if quote else ""}{extra}"><div class="ic">{"💬" if quote else "🖼"}</div>'
            f"<b>{kind}</b><div>{html.escape(label)}</div></div>")


def _post(s: str) -> str:
    def bq(m):
        inner = m.group(1)
        paras = re.findall(r"<p>(.*?)</p>", inner, flags=re.S)
        if paras and all(p.strip().startswith(("📷", "💬")) for p in paras):
            return "".join(_ph(re.sub(r"<.*?>", "", p.strip()[1:]).strip(), quote=p.strip().startswith("💬")) for p in paras)
        if paras and paras[0].strip().startswith("👉"):
            return f'<blockquote class="cta">{inner}</blockquote>'
        if paras and paras[0].strip().startswith("🙋"):
            return f'<blockquote class="me">{inner}</blockquote>'
        return m.group(0)

    s = re.sub(r"<blockquote>(.*?)</blockquote>", bq, s, flags=re.S)
    flow = ('<div class="flow"><div class="node">个人培训</div><div class="arr">→</div>'
            '<div class="node">筛选优秀学员</div><div class="arr">→</div>'
            '<div class="node hl">讲师 / 交付伙伴</div><div class="arr">→</div>'
            '<div class="node">企业项目</div></div>'
            '<div class="flow-back">↺ 企业的真实问题，变成下一期课程的案例</div>')
    s = re.sub(r"<pre><code>[^<]*个人培训.*?</code></pre>", flow, s, flags=re.S)
    s = re.sub(r"<code>(\[[^<]*\])</code>", r'<span class="todo">\1</span>', s)

    def li(m):
        inner = m.group(1)
        if "<ul" in inner or "<ol" in inner:
            return m.group(0)
        return "<li>" + inner.strip().replace("\n", "<br>") + "</li>"
    return re.sub(r"<li>(\s*(?:<p>)?<strong>.*?)</li>", li, s, flags=re.S)


def build_pdf(src: Path, out: Path, label: str, short: str, info: dict) -> Path:
    markdown = _md()
    text = APPENDIX_RE.split(src.read_text(encoding="utf-8"))[0].rstrip().rstrip("-").rstrip()
    lines = text.splitlines()
    title = lines[0].lstrip("# ").strip()
    parts = re.split(r"\n---\n", "\n".join(lines[1:]), maxsplit=1)
    hero, body = (parts + [""])[:2]

    intro, stats, creds, photo, to_body = [], [], "", None, []
    for para in re.split(r"\n\s*\n", hero.strip()):
        p = para.strip()
        if p.startswith(">"):
            t = "\n".join(l.lstrip(">").strip() for l in p.splitlines())
            if t.startswith("📷"):
                photo = photo or t.lstrip("📷 ").strip()
            elif t.startswith(("🙋", "👉")):
                to_body.append(p)
            else:
                intro += [x for x in t.split("\n") if x.strip()]
        elif p.startswith("- "):
            for l in p.splitlines():
                mm = re.match(r"-\s*\*\*(.+?)\*\*[：:](.+)", l)
                if mm:
                    stats.append((mm.group(1).strip(), mm.group(2).strip()))
        elif p:
            creds = p

    facts = []
    if not stats:
        m = re.match(r"\s*##\s*一眼看懂\s*\n(.*?)\n---\n", body, flags=re.S)
        if m:
            for l in m.group(1).splitlines():
                mm = re.match(r"-\s*\*\*(.+?)\*\*[：:](.+)", l)
                if mm:
                    facts.append((mm.group(1).strip(), mm.group(2).strip()))
            body = body[m.end():]

    sep = "｜" if "｜" in title else (" · " if " · " in title else None)
    headline = title.split(sep, 1)[1] if sep else title
    sub = ""
    pm = re.match(r"(.+?)（(.+)）$", headline)
    if pm:
        headline, sub = pm.group(1), pm.group(2)
    h_html = "<br>".join(f'<span class="hl">{html.escape(x)}</span>' for x in re.split(r"(?<=，)", headline) if x)
    if sub:
        h_html += f'<div class="sub">{html.escape(sub)}</div>'

    body_html = _post(markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"]).convert(
        _normalize("\n\n".join(to_body) + "\n\n" + body)))
    stats_html = "".join(f'<div class="stat"><div class="n">{_inline(markdown, n)}</div><div class="d">{_inline(markdown, d)}</div></div>' for n, d in stats)
    intro_html = "".join(f"<p>{_inline(markdown, t)}</p>" for t in intro)
    facts_html = "".join(f'<div class="fact"><b>{_inline(markdown, k)}</b><span>{_inline(markdown, v)}</span></div>' for k, v in facts)

    name = info["name"] or "我"
    mark = html.escape(name[:2])
    brand_line = " · ".join(x for x in (name, info["brand_en"]) if x)
    contact = html.escape(info["contact"]) if info["contact"] else '<span class="todo">[微信 / 电话]</span>'
    foot_left = " · ".join(x for x in (name, info["city"]) if x)
    cover = f"""
<section class="cover">
  <div class="cover-top">
    <div style="display:flex;align-items:center">
      <div class="logo"><div class="mark">{mark}</div><div class="word"><b>{html.escape(name)}</b><span>{html.escape(info['brand_en'])}</span></div></div>
      <span class="logo-slot">正式 logo 替换位</span>
    </div>
    <div class="cover-label">{html.escape(label)}</div>
  </div>
  <div class="cover-main">
    <div><h1>{h_html}</h1><div class="intro">{intro_html}</div></div>
    {_ph(photo or "个人照", extra=" photo")}
  </div>
  {f'<div class="stats">{stats_html}</div>' if stats else ''}
  {f'<div class="creds">{_inline(markdown, creds)}</div>' if creds else ''}
  {f'<div class="facts">{facts_html}</div>' if facts else ''}
  <div class="cover-foot"><span>{html.escape(foot_left)}</span><span>联系方式：{contact}</span></div>
</section>"""
    css = (HERE / "style.css").read_text(encoding="utf-8")
    page_css = (f'@page {{ @top-left {{ content: "{brand_line}"; }} @top-right {{ content: "{short}"; }} }}'
                '@page :first { @top-left { content: none; } @top-right { content: none; } }')
    page = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f"<style>{css}\n{page_css}</style></head><body>{cover}<main>{body_html}</main></body></html>")

    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        tmp_html = Path(tmp) / "page.html"
        tmp_html.write_text(page, encoding="utf-8")
        subprocess.run([_chrome(), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                        f"--user-data-dir={Path(tmp) / 'profile'}", f"--print-to-pdf={out}", tmp_html.as_uri()],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def cmd_pdf(a) -> int:
    src = Path(a.src).expanduser().resolve()
    if not src.is_file():
        raise SystemExit(f"找不到文件：{src}")
    lib = library(must_exist=False)
    lib = lib if lib.is_dir() else src.parent
    info = profile_info(lib)
    out = Path(a.out).expanduser().resolve() if a.out else lib / "02_PDF" / f"{info['name'] or '介绍'}_{src.stem}.pdf"
    print("✓", build_pdf(src, out, a.label or src.stem, a.short or "个人介绍", info))
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="个人介绍库工具")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("where").set_defaults(fn=cmd_where)
    p = sp.add_parser("init"); p.add_argument("path"); p.set_defaults(fn=cmd_init)
    p = sp.add_parser("cases")
    p.add_argument("--query", default=""); p.add_argument("--audience", default="")
    p.add_argument("--who", default=""); p.add_argument("--top", type=int, default=8)
    p.add_argument("--all", action="store_true", help="包含 public: 不对外 的卡片")
    p.set_defaults(fn=cmd_cases)
    sp.add_parser("index").set_defaults(fn=cmd_index)
    p = sp.add_parser("pdf"); p.add_argument("src"); p.add_argument("--out", default="")
    p.add_argument("--label", default=""); p.add_argument("--short", default="")
    p.set_defaults(fn=cmd_pdf)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
