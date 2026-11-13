#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch CCTV Xinwenlianbo transcripts. Stdlib only, no external deps."""

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from html.parser import HTMLParser
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


BASE_URL = "https://cn.govopendata.com/xinwenlianbo"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
    )
}


def fetch_html(url, attempts=4):
    last_error = None
    for attempt in range(attempts):
        try:
            result = subprocess.run(
                [
                    "curl", "-sS", "--fail", "--max-time", "30",
                    "-A", HEADERS["User-Agent"], url,
                ],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40,
            )
            if result.returncode == 0:
                return result.stdout
            raise RuntimeError(f"curl exit {result.returncode}: {result.stderr.strip()}")
        except Exception as exc:
            last_error = exc
            time.sleep(10 * (attempt + 1))
    raise last_error


class DayPageParser(HTMLParser):
    """Extract articles: title from h2/h3/h4, body from div.content-body."""

    def __init__(self):
        super().__init__()
        self.items = []
        self._in_article = False
        self._in_title = False
        self._in_body = False
        self._title_parts = []
        self._body_parts = []
        self._body_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")
        if tag == "article" and "content-section" in cls:
            self._in_article = True
            self._title_parts = []
            self._body_parts = []
        elif self._in_article:
            if self._in_body:
                if tag == "div":
                    self._body_depth += 1
                if tag in ("p", "br"):
                    self._body_parts.append("\n")
                return
            if tag in ("h2", "h3", "h4") and not self._in_body:
                self._in_title = True
            elif tag == "div" and "content-body" in cls:
                self._in_body = True
                self._body_depth = 1

    def handle_endtag(self, tag):
        if tag in ("h2", "h3", "h4") and self._in_title:
            self._in_title = False
        elif tag == "div" and self._in_body:
            self._body_depth -= 1
            if self._body_depth == 0:
                self._in_body = False
        elif tag == "article" and self._in_article:
            self._in_article = False
            title = "".join(self._title_parts).strip()
            content = "".join(self._body_parts).strip()
            if content:
                self.items.append({"title": title, "content": content})

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        elif self._in_body:
            self._body_parts.append(data)


def parse_day(content):
    parser = DayPageParser()
    parser.feed(content)
    return parser.items


def parse_dates(content):
    return set(re.findall(r'href="/xinwenlianbo/(\d{8})/"', content))


def available_dates(required):
    dates = set()
    for page_number in range(1, 100):
        url = f"{BASE_URL}/" if page_number == 1 else f"{BASE_URL}/?page={page_number}"
        content = fetch_html(url)
        found = parse_dates(content)
        if not found:
            break
        dates.update(found)
        if len(dates) >= required:
            break
        time.sleep(1)
    return sorted(dates, reverse=True)


def existing_days(root):
    directory = os.path.join(root, "逐字稿")
    result = set()
    if not os.path.isdir(directory):
        return result
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if re.match(r"^\d{8}\.md$", filename):
                result.add(filename[:-3])
    return result


def save_day(root, day, items):
    if not items:
        return False
    output_dir = os.path.join(root, "逐字稿", day[:4], day[4:6])
    os.makedirs(output_dir, exist_ok=True)
    date_text = f"{day[:4]}-{day[4:6]}-{day[6:]}"
    lines = [f"# 新闻联播 {date_text} 逐字稿", ""]
    for order, item in enumerate(items, 1):
        title = item["title"] or f"条目{order}"
        lines.extend([f"## {order}. {title}", "", item["content"], ""])
    path = os.path.join(output_dir, f"{day}.md")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))
    return True


def _log_dir(root):
    """默认数据目录的日志在 99_系统/日志/政策与商机/；--root 指到别处时放在 <root>/日志/。"""
    try:
        paths = _paths()
        if Path(root).resolve() == paths.data_dir("policy").resolve():
            return str(paths.log_dir("policy"))
    except SystemExit:
        pass
    return os.path.join(root, "日志")


def log(root, message):
    log_dir = _log_dir(root)
    os.makedirs(log_dir, exist_ok=True)
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}"
    print(line, flush=True)
    with open(os.path.join(log_dir, "fetch.log"), "a", encoding="utf-8") as handle:
        handle.write(line + "\n")



def _paths():
    """数据目录与子目录名：见 dei-daily-report/scripts/dei_paths.py。"""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
    import dei_paths
    return dei_paths


def _data_dir(module):
    return _paths().data_dir(module)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.environ.get("XWLB_ROOT"), help="数据目录；默认按 dei_paths 解析")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--date", help="指定日期 YYYYMMDD")
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()
    if not args.root:
        args.root = str(_data_dir("policy"))

    os.makedirs(args.root, exist_ok=True)
    if args.days < 1:
        parser.error("--days must be positive")
    if args.date:
        try:
            datetime.strptime(args.date, "%Y%m%d")
        except ValueError:
            parser.error("--date must be a valid YYYYMMDD date")
        targets = [args.date]
    else:
        dates = available_dates(1 if args.incremental else args.days)
        targets = dates[:1] if args.incremental else dates[:args.days]

    existing = existing_days(args.root)
    todo = [day for day in targets if day not in existing]
    log(args.root, f"目标日期 {len(targets)} 个，待抓取 {len(todo)} 个")
    failed = 0
    for day in sorted(todo):
        try:
            content = fetch_html(f"{BASE_URL}/{day}/")
            items = parse_day(content)
            if save_day(args.root, day, items):
                log(args.root, f"已保存 {day}.md ({len(items)}条)")
            else:
                failed += 1
                log(args.root, f"{day}: 无内容")
        except Exception as exc:
            failed += 1
            log(args.root, f"{day}: 失败 {exc}")
        time.sleep(1.5)
    log(args.root, f"抓取完成，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
