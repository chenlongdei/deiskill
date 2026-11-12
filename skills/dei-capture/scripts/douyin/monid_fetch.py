#!/usr/bin/env python3
"""步骤1：采集视频简要信息（数据+链接）→ workspace/videos.json

数据来源由 douyin.provider 决定：TikHub 或 Monid（auto：有 TikHub Token 用 TikHub）。

三种来源（按优先级手动选择）：
  --links "url1,url2"  直接给视频链接（v.douyin.com 短链 / douyin.com/video 页面链接 / 文件直链）
  --file path.json     Monid 或其他工具导出的 JSON 文件（自动识别字段，无需配置）
  --monid（默认）      调用 config.json 中 monid 配置的 API 拉取

统一写入 videos.json，后续脚本基于该状态文件增量处理。
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (DEFAULT_FIELD_MAP, data_provider, extract_video_id, platform_of, first_value, is_direct_media_url,
                    normalize_time, deep_get, monid_run, now_str, sanitize_filename,
                    store_load, store_save, load_config)


def build_entry(item, field_map):
    """把一个原始 item 映射为统一格式。"""
    entry = {
        "video_id": first_value(item, field_map.get("video_id")),
        "title": first_value(item, field_map.get("title")),
        "author_name": first_value(item, field_map.get("author_name")),
        "author_id": first_value(item, field_map.get("author_id")),
        "publish_time": normalize_time(first_value(item, field_map.get("publish_time"))),
        "share_url": first_value(item, field_map.get("share_url")),
        "page_url": first_value(item, field_map.get("page_url")),
        "video_file_url": first_value(item, field_map.get("video_file_url")),
        "platform": "douyin",
    }
    stats = {}
    for k in ("likes", "comments", "shares", "collects"):
        v = first_value(item, field_map.get(k))
        if v is not None:
            try:
                stats[k] = int(v)
            except (TypeError, ValueError):
                stats[k] = v
    if stats:
        entry["stats"] = stats
        entry["stats_time"] = now_str()
    return {k: v for k, v in entry.items() if v not in (None, "")}


def upsert(store, entry):
    """按 video_id（无则从链接取抖音视频号，再不行用链接哈希）增量合入状态文件。返回 'new' / 'updated'。"""
    link = entry.get("share_url") or entry.get("page_url") or ""
    vid = entry.get("video_id") or extract_video_id(link) or hashlib.md5(
        (entry.get("share_url") or entry.get("page_url") or "").encode("utf-8")).hexdigest()[:16]
    entry["video_id"] = vid
    old = store["videos"].get(vid)
    if old:
        for k, v in entry.items():
            if v is not None:
                old[k] = v
        return "updated"
    entry.setdefault("stats", {})
    entry["stage"] = "collected"
    store["videos"][vid] = entry
    return "new"


def find_items(obj):
    """在任意 JSON 结构里找『视频对象列表』。"""
    if isinstance(obj, list):
        dicts = [x for x in obj if isinstance(x, dict)]
        return dicts if dicts else None
    if isinstance(obj, dict):
        for path in ("data.list", "data.items", "data.videos", "data", "list", "items",
                     "videos", "result", "results", "data.data"):
            v = deep_get(obj, path)
            if isinstance(v, list) and v and isinstance(v[0], dict):
                return v
        if any(k in obj for k in ("aweme_id", "video_id", "share_url", "url", "note_id")):
            return [obj]
    return None


def fetch_from_monid(cfg):
    """走 Monid 工具网关调 anyapi/douyin.user_posts，拉监控博主的最新视频。"""
    monid = cfg.get("monid", {})
    watch = monid.get("watch_sec_user_ids") or []
    if not (monid.get("enabled") and monid.get("token")):
        print("[跳过] config.json 中 monid 未启用或缺 token。可改用 --links / --file。")
        return []
    if not watch:
        print("[提示] monid.watch_sec_user_ids 为空。把要监控博主的 sec_user_id 填进去"
              "（打开博主抖音主页，链接 /user/ 后面那一长串就是）。也可先用 --links / --file。")
        return []
    raw_dir = Path(cfg["workspace"]) / ".raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for sec in watch:
        try:
            run = monid_run(cfg, monid.get("provider", "anyapi"),
                            monid.get("user_posts_endpoint", "/douyin.user_posts"),
                            {"secUserId": sec, "limit": monid.get("limit", 20),
                             "sort": monid.get("sort", "newest")})
        except Exception as e:
            print(f"  [拉取失败] {sec[:24]}…：{e}")
            continue
        raw_file = raw_dir / f"user_posts_{sec[-8:]}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        raw_file.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        posts = deep_get(run, "output.data.posts") or []
        cost = (run.get("cost") or {}).get("value")
        print(f"  [{deep_get(run, 'output.data.posts.0.authorNickname') or sec[:20]}…] "
              f"{len(posts)} 条 · ${cost}")
        items += posts
    return items


def tikhub_entry(v):
    """tikhub.aweme_to_video 的结果 → 状态库条目。"""
    return {"video_id": v["id"], "title": v["title"], "author_name": v.get("author") or None,
            "author_id": v.get("author_sec_uid") or None, "publish_time": v["publish"] or None,
            "share_url": v["url"], "platform": "douyin",
            "stats": {"likes": v["likes"], "comments": v["comments"], "collects": v["collects"], "shares": v["shares"]},
            "stats_time": now_str()}


def fetch_from_tikhub(cfg):
    """TikHub 拉监控列表里每个博主的最新 N 条。"""
    from tikhub import TikHub
    watch = (cfg.get("monid") or {}).get("watch_sec_user_ids") or []
    limit = int((cfg.get("monid") or {}).get("limit") or 20)
    if not watch:
        print("[提示] 监控列表为空：用 run.py monitor --blogger-sec-uid <id> 添加，或先用 --links。")
        return []
    tk, out = TikHub(cfg["tikhub_token"]), []
    for sec in watch:
        try:
            videos = tk.posts(sec, 0, pages=max(1, (limit + 19) // 20))[:limit]
        except Exception as e:
            if type(e).__name__ == "StopExternal":
                raise SystemExit(f"[停止] TikHub：{e}（Token 无效或余额不足）")
            print(f"  [拉取失败] {sec[:24]}…：{e}")
            continue
        print(f"  [{(videos[0].get('author') if videos else '') or sec[:20]}] {len(videos)} 条（TikHub）")
        out += [tikhub_entry(v) for v in videos]
    return out


def links_entries(cfg, urls):
    """链接 → 条目。TikHub 可用时，抖音链接顺带取标题、作者和数据。"""
    tk = None
    if data_provider(cfg) == "tikhub":
        from tikhub import TikHub, aweme_to_video
        tk = TikHub(cfg["tikhub_token"])
    out = []
    for u in urls:
        e = {"share_url": u, "platform": platform_of(u), "video_file_url": u if is_direct_media_url(u) else None}
        if tk and e["platform"] == "douyin" and not e["video_file_url"]:
            try:
                a = tk.one_video(u)
                if a.get("aweme_id"):
                    e.update(tikhub_entry(aweme_to_video(a)))
            except Exception as ex:
                if type(ex).__name__ == "StopExternal":
                    raise SystemExit(f"[停止] TikHub：{ex}（Token 无效或余额不足）")
                print(f"  [TikHub 未取到数据] {u}：{ex}（继续，数据由解析步骤回填）")
        out.append(e)
    return out


def main():
    ap = argparse.ArgumentParser(description="采集视频信息 → videos.json")
    ap.add_argument("--config", help="指定 config.json 路径（默认 skill 目录下）")
    ap.add_argument("--links", help="逗号/空格分隔的视频链接列表")
    ap.add_argument("--file", help="Monid/其他工具导出的 JSON 文件路径")
    ap.add_argument("--monid", action="store_true", help="强制走 Monid API（默认即如此）")
    args = ap.parse_args()

    cfg = load_config(args.config)
    store = store_load(cfg)
    field_map = cfg.get("monid", {}).get("field_map") or DEFAULT_FIELD_MAP

    items, entries = [], []
    if args.links:
        urls = [u.strip() for u in args.links.replace(",", " ").split() if u.strip()]
        print(f"[links] 收到 {len(urls)} 条链接")
        entries = links_entries(cfg, urls)
    elif args.file:
        data = json.loads(Path(args.file).expanduser().read_text(encoding="utf-8"))
        items = find_items(data)
        if items is None:
            raise SystemExit(f"[错误] 在 {args.file} 里没找到视频列表，请检查文件结构。")
        print(f"[file] 从文件识别出 {len(items)} 条记录")
    else:
        provider = data_provider(cfg)
        print(f"[数据来源] {provider}")
        if provider == "tikhub":
            entries = fetch_from_tikhub(cfg)
        elif provider == "monid":
            items = fetch_from_monid(cfg)
        else:
            raise SystemExit("[停止] 没有可用的数据来源：配置 TikHub Token（tikhub.token）或 Monid Key（douyin.monid.token）")

    if items:
        entries = [build_entry(item, field_map) for item in items]
    n_new = n_upd = 0
    for entry in entries:
        entry = {k: v for k, v in entry.items() if v not in (None, "")}
        if not entry.get("share_url") and not entry.get("page_url") and not entry.get("video_file_url"):
            # 既无链接也无 id 的脏数据跳过
            continue
        r = upsert(store, entry)
        n_new += r == "new"
        n_upd += r == "updated"

    store["updated_at"] = now_str()
    store_save(cfg, store)
    total = len(store["videos"])
    print(f"[完成] 新增 {n_new} / 更新 {n_upd} / 库存共 {total} 条 → {cfg['workspace']}/videos.json")
    for vid, v in store["videos"].items():
        if v.get("stage") == "collected":
            print(f"  - [{vid}] {sanitize_filename(v.get('title') or v.get('share_url') or '', 40)}")


if __name__ == "__main__":
    main()
