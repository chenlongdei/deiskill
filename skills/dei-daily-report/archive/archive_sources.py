#!/usr/bin/env python3
"""头条原文存档：按 sources.json 抓取官方原文，验证关键句，转 Word 并打包。

用法：python3 archive_sources.py <sources.json> --out <输出目录>

sources.json 由 Agent 按 references/source-archive.md 第一、二步写好（识别文件、检索链接、挑关键句），
本脚本只做第三到五步：三层降级抓取、关键句验证、转 Word、打包索引。格式：

{
  "date": "2026-11-12",
  "topic": "头条标题",
  "documents": [
    {"title": "文件全称", "doc_no": "文号", "agency": "发文机关", "kind": "原文|官方解读|发布会|前序文件|媒体解读",
     "written": "成文日期", "published": "发布日期", "effective": "施行日期", "summary": "一句话要点",
     "urls": ["首选官方链接", "备用链接 …"], "check": ["关键句 1", "关键句 2"]}
  ],
  "tracking": [{"title": "待出台文件", "status": "截至某日未检索到发布", "note": ""}]
}

抓取层级：① 直连（浏览器 User-Agent）② 浏览器渲染 ③ 换下一个链接。每层都用 check 里的关键句核对，
全部命中才算成功；都失败就标记失败并写明卡在哪一层，不拿摘要凑数。需要 playwright。
"""
import argparse, datetime, html, json, pathlib, re, sys, urllib.request, zipfile
from playwright.sync_api import sync_playwright
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 取正文：先试政府网站常见容器，再取段落文字最多的块
EXTRACT_JS = r"""
() => {
  const sels = ['#UCAP-CONTENT', '.pages_content', '#zoom', '.TRS_Editor', '.article-content', '.article', 'article',
                '#detail', '.detail', '.content', '#content', '.main-content', '.left_zw', '#p-detail', '.rm_txt_con'];
  const textOf = el => (el.innerText || '').replace(/\n{3,}/g, '\n\n').trim();
  let best = null, score = 0;
  for (const s of sels) for (const el of document.querySelectorAll(s)) {
    const t = textOf(el); if (t.length > score) { best = el; score = t.length; }
  }
  if (score < 300) {
    for (const el of document.querySelectorAll('div,section,td')) {
      const ps = [...el.querySelectorAll(':scope > p, :scope > div > p')];
      const n = ps.reduce((a, p) => a + (p.innerText || '').length, 0);
      if (n > score) { best = el; score = n; }
    }
  }
  const title = (document.querySelector('h1') || {}).innerText || document.title || '';
  return {title: title.trim(), text: best ? textOf(best) : textOf(document.body)};
}
"""


def norm(s):
    return re.sub(r"[\s　]+", "", s or "")


def verify(text, checks):
    t = norm(text)
    missing = [c for c in checks if norm(c) not in t]
    return not missing and len(t) > 200, missing


def fetch_direct(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"})
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        charset = r.headers.get_content_charset()
    for enc in [charset, "utf-8", "gb18030"]:
        if not enc:
            continue
        try:
            return raw.decode(enc)
        except (LookupError, UnicodeDecodeError):
            pass
    return raw.decode("utf-8", "replace")


def extract(page, html_text=None, url=None):
    if html_text is not None:
        page.set_content(html_text, wait_until="domcontentloaded")
    else:
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(1500)
    return page.evaluate(EXTRACT_JS)


# ---------------- 极简 docx 生成（不依赖第三方库） ----------------
def _run(text, bold=False, size=24):
    t = html.escape(text, quote=False)
    b = "<w:b/>" if bold else ""
    return (f'<w:r><w:rPr><w:rFonts w:ascii="FangSong" w:hAnsi="FangSong" w:eastAsia="仿宋"/>{b}'
            f'<w:sz w:val="{size}"/></w:rPr><w:t xml:space="preserve">{t}</w:t></w:r>')


def _p(inner, heading=False):
    style = '<w:pStyle w:val="Heading1"/>' if heading else ""
    return f'<w:p><w:pPr>{style}<w:spacing w:line="336" w:lineRule="auto" w:after="120"/></w:pPr>{inner}</w:p>'


class Docx:
    def __init__(self):
        self.body, self.links = [], []

    def h1(self, text):
        self.body.append(_p(_run(text, True, 32), heading=True))

    def para(self, text, bold=False):
        self.body.append(_p(_run(text, bold)))

    def link(self, label, url):
        rid = f"rIdL{len(self.links) + 1}"
        self.links.append((rid, url))
        r = _run(url).replace("<w:rPr>", '<w:rPr><w:color w:val="1F4FD8"/><w:u w:val="single"/>', 1)
        self.body.append(_p(_run(label) + f'<w:hyperlink r:id="{rid}">{r}</w:hyperlink>'))

    def table(self, rows):
        def cell(t, bold):
            return (f'<w:tc><w:tcPr><w:tcW w:w="0" w:type="auto"/></w:tcPr>'
                    f'{_p(_run(t, bold, 18))}</w:tc>')
        trs = "".join("<w:tr>" + "".join(cell(c, i == 0) for c in r) + "</w:tr>" for i, r in enumerate(rows))
        borders = "".join(f'<w:{s} w:val="single" w:sz="4" w:color="999999"/>'
                          for s in ("top", "left", "bottom", "right", "insideH", "insideV"))
        self.body.append(f'<w:tbl><w:tblPr><w:tblW w:w="5000" w:type="pct"/><w:tblBorders>{borders}'
                         f'</w:tblBorders></w:tblPr>{trs}</w:tbl>')

    def save(self, path):
        ns = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
              'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"')
        doc = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document {ns}><w:body>{"".join(self.body)}<w:sectPr/></w:body></w:document>'
        rels = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" '
                       f'Target="{html.escape(u)}" TargetMode="External"/>' for rid, u in self.links)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml",
                       '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                       '<Default Extension="xml" ContentType="application/xml"/>'
                       '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                       '</Types>')
            z.writestr("_rels/.rels",
                       '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                       '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                       '</Relationships>')
            z.writestr("word/_rels/document.xml.rels",
                       f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')
            z.writestr("word/document.xml", doc)


def safe(name):
    return re.sub(r'[\\/:*?"<>|\s]+', "", name)[:60] or "文件"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sources")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    src = json.loads(pathlib.Path(a.sources).read_text(encoding="utf-8"))
    out = pathlib.Path(a.out).resolve()
    if pathlib.Path(__file__).resolve().parent.parent in out.parents:
        sys.exit("输出目录不能放在 Skill 安装目录里。")
    for d in ("word", "html", "md"):
        (out / d).mkdir(parents=True, exist_ok=True)
    today = datetime.date.today().isoformat()
    log = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome")
        except Exception:
            browser = p.chromium.launch()
        page = browser.new_page(user_agent=UA, locale="zh-CN")
        for i, d in enumerate(src["documents"], 1):
            no = f"{i:02d}"
            name = f"{no}_{safe(d['title'])}" + (f"（{safe(d['doc_no'])}）" if d.get("doc_no") else "")
            rec = {"no": no, "title": d["title"], "kind": d.get("kind", "原文"), "ok": False, "tries": []}
            checks = d.get("check", [])
            if not d.get("urls"):
                rec["tries"].append({"url": "—", "layer": "检索", "result": d.get("note") or "未找到可用的官方链接"})
            for url in d.get("urls", []):
                for layer in ("直连", "渲染"):
                    try:
                        if layer == "直连":
                            raw = fetch_direct(url)
                            got = extract(page, html_text=raw)
                        else:
                            got = extract(page, url=url)
                            raw = page.content()
                    except Exception as e:
                        rec["tries"].append({"url": url, "layer": layer, "result": f"失败：{type(e).__name__} {str(e)[:80]}"})
                        continue
                    ok, missing = verify(got["text"], checks)
                    tag = "" if ok else "_未通过"
                    (out / "html" / f"{name}_{layer}{tag}.html").write_text(raw, encoding="utf-8")
                    rec["tries"].append({"url": url, "layer": layer, "chars": len(got["text"]),
                                         "result": "通过" if ok else f"关键句缺失 {len(missing)} 条：{'；'.join(missing)[:80]}"})
                    if ok:
                        rec.update(ok=True, url=url, layer=layer, chars=len(got["text"]))
                        text = got["text"]
                        break
                if rec["ok"]:
                    break
            if rec["ok"]:
                doc = Docx()
                doc.h1(d["title"] + (f"（{d['doc_no']}）" if d.get("doc_no") else ""))
                doc.para(f"来源：{d.get('agency', '')} · {d.get('published', '')}".rstrip(" ·"))
                doc.link("原文链接：", rec["url"])
                doc.para(f"抓取日期：{today}（{rec['layer']}，关键句核对通过）")
                if d.get("kind") not in (None, "原文"):
                    doc.para(f"性质：{d['kind']}（不是文件原文）", bold=True)
                doc.para("")
                for line in text.splitlines():
                    if line.strip():
                        doc.para(line.strip())
                doc.save(out / "word" / f"{name}.docx")
                (out / "md" / f"{name}.md").write_text(
                    f"# {d['title']}\n\n- 原文链接：{rec['url']}\n- 抓取：{today} · {rec['layer']}\n\n{text}\n", encoding="utf-8")
                rec["file"] = f"{name}.docx"
            log.append(rec)
            print(f"{'✓' if rec['ok'] else '✗'} {name}  " + (f"{rec['layer']} · {rec['chars']} 字" if rec["ok"] else "未抓到，见链接总览"))
        browser.close()

    # 00 总览与链接索引
    idx = Docx()
    idx.h1(f"原文存档总览 · {src.get('date', '')}")
    idx.para(f"头条：{src.get('topic', '')}")
    idx.para(f"抓取日期：{today}；成功 {sum(r['ok'] for r in log)} / {len(log)} 份")
    rows = [["序号", "名称", "文号", "发文机关", "成文 / 发布", "施行", "性质", "要点", "存档文件", "状态"]]
    for d, r in zip(src["documents"], log):
        rows.append([r["no"], d["title"], d.get("doc_no", ""), d.get("agency", ""),
                     f"{d.get('written', '')} / {d.get('published', '')}".strip(" /"), d.get("effective", ""),
                     d.get("kind", "原文"), d.get("summary", ""), r.get("file", "—"),
                     "已核对" if r["ok"] else ("未抓到：" + d["note"] if d.get("note") else "未抓到")])
    idx.table(rows)
    idx.para("")
    idx.para("官方链接", bold=True)
    for d, r in zip(src["documents"], log):
        for u in d.get("urls", []):
            idx.link(f"{r['no']} ", u)
    if src.get("tracking"):
        idx.para("")
        idx.para("待出台文件跟踪清单", bold=True)
        idx.table([["文件", "状态", "备注"]] + [[t["title"], t.get("status", ""), t.get("note", "")] for t in src["tracking"]])
    idx.save(out / "word" / "00_总览与链接索引.docx")

    lines = [f"# 链接总览 · {src.get('date', '')}", "", f"头条：{src.get('topic', '')}", ""]
    for d, r in zip(src["documents"], log):
        lines.append(f"## {r['no']} {d['title']}" + (f"（{d['doc_no']}）" if d.get("doc_no") else ""))
        lines.append(f"- 性质：{d.get('kind', '原文')} · 状态：{'已核对（' + r['layer'] + '）' if r['ok'] else '未抓到'}")
        if d.get("note"):
            lines.append(f"- 备注：{d['note']}")
        for t in r["tries"]:
            lines.append(f"- {t['layer']} {t['url']} → {t['result']}")
        lines.append("")
    if src.get("tracking"):
        lines += ["## 待出台文件跟踪", ""] + [f"- {t['title']}：{t.get('status', '')} {t.get('note', '')}".rstrip() for t in src["tracking"]]
    (out / "链接总览.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (out / "抓取记录.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    sys.exit(0 if all(r["ok"] for r in log) else 2)


if __name__ == "__main__":
    main()
