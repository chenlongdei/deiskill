#!/usr/bin/env python3
"""对外日报自检：把 references/publish-standard.md 里能机械判断的规则跑一遍。

用法：python3 check_report.py <文字版.md> [<data.json>]
有错误时退出码为 1；只有提醒时为 0。规则改动时同步修改 publish-standard.md。
"""
import json, re, sys, pathlib

MIN_CHARS, MAX_CHARS = 5000, 8000
MODULES = ["今天最重要的一件事", "国家政策", "AI", "社会热点", "接下来值得关注", "主要资料来源"]
# 执行过程、内部判断和自用建议不进成品
FORBIDDEN = ["deiskill", "config", "未配置", "未取得", "未检索到", "运行记录", "unsupported", "partial",
             "研究补查", "值得验证", "商机", "课程素材", "对我的", "〔事实", "〔推断", "暂评", "A级", "B级", "S级",
             "表达角度", "开头句", "抖音"]


def body_chars(md: str) -> int:
    body = md.split("## 主要资料来源")[0]
    body = re.sub(r"\]\([^)]*\)", "]", body)
    return len(re.sub(r"[#>*|\-\s\[\]]", "", body))


def split_modules(md: str):
    mods, cur = [], None
    for line in md.splitlines():
        if line.startswith("## "):
            cur = {"title": re.sub(r"^[一二三四五六七八九十]+、", "", line[3:]).strip(), "lines": []}
            mods.append(cur)
        elif cur:
            cur["lines"].append(line)
    return mods


def check(md_path, data_path=None):
    errors, warns = [], []
    md = pathlib.Path(md_path).read_text(encoding="utf-8")

    n = body_chars(md)
    if not MIN_CHARS <= n <= MAX_CHARS:
        errors.append(f"正文 {n} 字，应在 {MIN_CHARS}—{MAX_CHARS} 之间")

    mods = split_modules(md)
    titles = [m["title"] for m in mods]
    for want in MODULES:
        if not any(t.startswith(want) for t in titles):
            errors.append(f"缺少模块「{want}」")
    for m in mods:
        if m["title"].startswith(("主要资料来源", "接下来值得关注")):
            continue
        h3 = [l for l in m["lines"] if l.startswith("### ")]
        if m["title"].startswith("今天最重要的一件事"):
            if len(h3) != 1:
                errors.append(f"「今天最重要的一件事」应只有 1 条，现在 {len(h3)} 条")
            elif h3[0].rstrip().endswith("。"):
                errors.append("头条标题不加句号")
        elif len(h3) % 2 == 0:
            errors.append(f"「{m['title']}」有 {len(h3)} 条，条目数应为单数（1、3、5）")
        elif len(h3) > 1 and not re.search(r"其他|另外|持续", h3[-1]):
            warns.append(f"「{m['title']}」最后一条通常是其他消息的合集")
        if m["title"].startswith("社会热点"):
            text = "\n".join(m["lines"])
            if "持续" in text and not re.search(r"^\|[^\n]*\|[^\n]*\|[^\n]*\|[^\n]*\|\s*$", text, re.M):
                errors.append("「本周持续在讨论的话题」应使用四列表格：话题 / 怎么开始的 / 一周进展 / 最新状态")

    for w in FORBIDDEN:
        if w in md:
            errors.append(f"出现内部用语「{w}」，执行过程和自用内容不进成品")
    if re.search(r"单看.{0,12}新闻", md):
        warns.append("头条不要用“单看今天的新闻”类铺垫开头，直接抛出问题和答案")

    if data_path:
        d = json.loads(pathlib.Path(data_path).read_text(encoding="utf-8"))
        hl = "".join(d.get("headline", []))
        if re.search(r"[。！.!]$", hl):
            errors.append("封面大标题不加句号")
        if len(hl.replace(" ", "")) > 18:
            warns.append(f"封面大标题 {len(hl)} 字，超过 18 字会被缩得很小")
        if len(d.get("headline", [])) > 2:
            warns.append("封面大标题最多分两行，应是一句话的判断，不是清单")
        if not isinstance(d.get("issue"), int) or d["issue"] < 1:
            errors.append("issue 应为从 1 开始的整数期号，用 publish/issue.py 生成")
        groups = d.get("contents", [])
        if [g.get("k") for g in groups] != ["国家政策", "AI", "社会热点"]:
            errors.append("封面目录 contents 应依次为国家政策、AI、社会热点")
        if sum(len(g.get("items", [])) for g in groups) < 8:
            warns.append("封面目录少于 8 条，引流图卡要让人看到这一期的信息量")
        for g in groups:
            for i in g.get("items", []):
                if i.strip() in ("国家政策", "AI", "社会热点", ""):
                    errors.append(f"封面「{g.get('k')}」目录要写具体条目")
                for line in i.split("\n"):
                    width = len(re.sub(r"[\x00-\x7f]", "", line)) + len(re.sub(r"[^\x00-\x7f]", "", line)) / 2
                    if width > 12:
                        warns.append(f"封面目录「{line}」一行放不下，会在词中间断开；缩短到 11 个字以内，或用 \\n 在自然停顿处换行")
        cards = d.get("cards", [])
        if len(cards) < 8:
            warns.append(f"速览只有 {len(cards)} 张卡片，每个模块应拆到多条，不只挑一个重点")
        for mod in ("国家政策", "AI", "社会热点"):
            n_mod = sum(1 for x in cards if x.get("kicker", "").startswith(mod))
            if n_mod < 2:
                warns.append(f"「{mod}」只有 {n_mod} 张卡片，引流图卡每个模块至少两张")
        if headline_dup := [x for x in cards if x.get("title", "").replace("\n", "") == "".join(d.get("headline", [])).replace(" ", "")]:
            errors.append("头条卡片标题和封面大标题重复")
        last = cards[-1] if cards else {}
        if not any(b.get("type") == "cta" for b in last.get("blocks", [])):
            errors.append("最后一张卡片要有 cta，引导去看完整版")
        elif d.get("community") and d["community"] not in json.dumps(last, ensure_ascii=False):
            warns.append("最后一张卡片没有写出完整版在哪里（community）")
        numbered = [t for t in titles if not t.startswith("主要资料来源")]
        if len(d.get("toc", [])) != len(numbered):
            errors.append(f"toc 有 {len(d.get('toc', []))} 条，长文有 {len(numbered)} 个模块，应一一对应")
        if not d.get("brand"):
            warns.append("brand 为空，报头只显示“日报”")

    return n, errors, warns


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    n, errors, warns = check(*sys.argv[1:3])
    print(f"正文 {n} 字")
    for e in errors:
        print("✗", e)
    for w in warns:
        print("·", w)
    if not errors:
        print("✓ 通过")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
