#!/usr/bin/env python3
"""对外日报期号：第一次发布为第 1 期，之后每个新报告日加 1；同一天重跑沿用同一期号。

用法：python3 publish/issue.py <YYYY-MM-DD>            期号记在 03_日报/对外日报期号.json
      python3 publish/issue.py <目录> <YYYY-MM-DD>     期号记在 <目录>/对外日报期号.json（测试或旧版）
打印本期期号。
"""
import json, pathlib, re, sys

args = sys.argv[1:]
if not args or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args[-1]) or len(args) > 2:
    sys.exit(__doc__)
day = args[-1]
if len(args) == 2:
    root = pathlib.Path(args[0])
else:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
    import dei_paths
    root = dei_paths.daily_root()
if not root.is_dir():
    sys.exit(f"保存位置不存在：{root}")
f = root / "对外日报期号.json"
book = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
if day not in book:
    book[day] = max(book.values(), default=0) + 1
    f.write_text(json.dumps(dict(sorted(book.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(book[day])
