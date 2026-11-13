#!/usr/bin/env python3
"""步骤4：合并「视频数据 + 逐字稿」→ 博主目录 Markdown + INDEX.md 索引

- 目录结构：博主/<博主名>/监控更新/<发布日期>-<标题>.md
- 每篇 md：YAML frontmatter（数据：点赞/评论/收藏/转发、链接、时长等）+ 逐字稿正文
- 博主/监控索引.md：全部视频总索引表（每次重建）
- 已合并条目默认跳过，--force 可重出（例如数据更新后重新合并）
"""
import argparse
import re
import sys
from pathlib import Path
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (blogger_dir, now_str, sanitize_filename, store_load, store_save,
                    load_config, yaml_str)

STATS_LABELS = [("likes", "点赞"), ("comments", "评论"), ("collects", "收藏"), ("shares", "转发")]


def paragraphs(text, per=3):
    """按句号/问号/感叹号切句，每 per 句合一段，便于阅读。"""
    sentences = re.split(r"(?<=[。！？!?])", text or "")
    sentences = [s for s in (x.strip() for x in sentences) if s]
    return "\n\n".join("".join(sentences[i:i + per]) for i in range(0, len(sentences), per))


def write_one(cfg, v):
    date = (v.get("publish_time") or "未知日期")[:10]
    title = v.get("title") or v.get("video_id")
    out_dir = blogger_dir(cfg, v.get("author_name"), "监控更新")
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{date}-{sanitize_filename(title)}.md"

    stats = v.get("stats") or {}
    asr = v.get("asr") or {}
    fm = [
        "---",
        f"video_id: {yaml_str(v.get('video_id'))}",
        f"title: {yaml_str(title)}",
        f"author: {yaml_str(v.get('author_name'))}",
        f"platform: {yaml_str(v.get('platform', 'douyin'))}",
        f"publish_time: {yaml_str(v.get('publish_time'))}",
        f"share_url: {yaml_str(v.get('share_url') or v.get('page_url'))}",
        f"video_file_url: {yaml_str(v.get('video_file_url'))}",
        "stats:",
    ]
    for k, _ in STATS_LABELS:
        fm.append(f"  {k}: {stats.get(k, 0)}")
    fm += [
        f"stats_time: {yaml_str(v.get('stats_time'))}",
        "transcript:",
        f"  source: {yaml_str(asr.get('source') or 'paraformer-v2')}",
        f"  duration_seconds: {asr.get('duration_seconds', 'null')}",
        f"  chars: {asr.get('transcript_chars', len(v.get('transcript') or ''))}",
        f"  file: {yaml_str(v.get('transcript_file'))}",
        f"merged_at: {yaml_str(now_str())}",
        "---",
    ]
    stat_line = " · ".join(f"{label} {stats.get(k, 0)}" for k, label in STATS_LABELS)
    body = [
        f"# {title}",
        "",
        f"> {v.get('author_name') or '未知博主'} · 发布于 {v.get('publish_time') or '未知时间'} · {stat_line}",
        f">",
        f"> 链接：{v.get('share_url') or v.get('page_url') or ''}",
        "",
        "## 逐字稿",
        "",
        paragraphs(v.get("transcript") or ""),
        "",
    ]
    path.write_text("\n".join(fm) + "\n" + "\n".join(body), encoding="utf-8")
    return path


def rebuild_index(ws, vids):
    rows = sorted(vids.values(),
                  key=lambda v: (v.get("publish_time") or "", v.get("video_id") or ""),
                  reverse=True)
    lines = ["# 视频索引", "",
             "| 发布时间 | 博主 | 标题 | 点赞 | 评论 | 收藏 | 转发 | 状态 | 文件 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for v in rows:
        stats = v.get("stats") or {}
        link = v.get("share_url") or v.get("page_url") or ""
        title = (v.get("title") or v.get("video_id") or "").replace("|", "\\|")
        author = (v.get("author_name") or "").replace("|", "\\|")
        rel = v.get("merged_file") or ""
        stage = v.get("stage", "")
        lines.append(
            f"| {v.get('publish_time') or ''} "
            f"| {author} "
            f"| [{title}]({link}) "
            f"| {stats.get('likes', '-')} | {stats.get('comments', '-')} "
            f"| {stats.get('collects', '-')} | {stats.get('shares', '-')} "
            f"| {stage} | {rel} |")
    ws.mkdir(parents=True, exist_ok=True)
    (ws / "监控索引.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="合并数据与逐字稿")
    ap.add_argument("--config", help="指定 config.json 路径")
    ap.add_argument("--force", action="store_true", help="已合并的也重新输出（数据更新后用）")
    args = ap.parse_args()

    cfg = load_config(args.config)
    ws = blogger_dir(cfg, "x").parent  # 博主/
    store = store_load(cfg)
    vids = store["videos"]

    merged = skipped = 0
    for v in vids.values():
        if v.get("stage") not in ("transcribed", "merged") or not v.get("transcript"):
            continue
        if v.get("merged") and not args.force:
            skipped += 1
            continue
        path = write_one(cfg, v)
        v["merged"] = True
        v["stage"] = "merged"
        v["merged_file"] = str(path.relative_to(ws))
        merged += 1
        print(f"  [已合并] {path.relative_to(ws)}")

    rebuild_index(ws, vids)
    store_save(cfg, store)
    print(f"[完成] 本次合并 {merged} 篇，跳过已合并 {skipped} 篇。索引：{ws / '监控索引.md'}")


if __name__ == "__main__":
    main()
