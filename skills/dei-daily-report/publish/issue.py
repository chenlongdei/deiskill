#!/usr/bin/env python3
"""对外日报期号：第一次发布为第 1 期，之后每个新报告日加 1；同一天重跑沿用同一期号。

用法：python3 issue.py <output_root> <YYYY-MM-DD>
期号记录在 <output_root>/对外日报期号.json，打印本期期号。
"""
import json, pathlib, re, sys

if len(sys.argv) != 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[2]):
    sys.exit(__doc__)
root, day = pathlib.Path(sys.argv[1]), sys.argv[2]
if not root.is_dir():
    sys.exit(f"保存位置不存在：{root}")
f = root / "对外日报期号.json"
book = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
if day not in book:
    book[day] = max(book.values(), default=0) + 1
    f.write_text(json.dumps(dict(sorted(book.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(book[day])
