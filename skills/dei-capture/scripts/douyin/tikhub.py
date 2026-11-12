"""TikHub 抖音接口（REST，计费）：解析账号、拉作品列表、按分享链接取单条作品。

来自原 dei-daily-report 抖音模块，并入 dei-capture 后供监控流水线和监控工作簿共用。
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

API = "https://api.tikhub.io"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36"


class StopExternal(RuntimeError):
    """凭证无效或余额不足：停止后续外部调用。"""


def req(url, headers=None, data=None, method=None, retries=4):
    h = {"Accept": "application/json", "User-Agent": UA, "Accept-Encoding": "identity"}
    h.update(headers or {})
    if isinstance(data, dict):
        data = json.dumps(data).encode()
        h.setdefault("Content-Type", "application/json")
    for n in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=h, method=method),
                                        timeout=45) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (401, 402, 403):
                raise StopExternal(f"HTTP {e.code} ({urllib.parse.urlparse(url).hostname})")
            if n == retries - 1:
                raise
        except Exception:
            if n == retries - 1:
                raise
        time.sleep(min(2 ** n * 2, 12))


def find(x, keys):
    if isinstance(x, dict):
        for k in keys:
            if x.get(k) not in (None, ""):
                return x[k]
        for v in x.values():
            z = find(v, keys)
            if z not in (None, ""):
                return z
    elif isinstance(x, list):
        for v in x:
            z = find(v, keys)
            if z not in (None, ""):
                return z
    return None


def num(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        return max(0, int(x))
    m = re.search(r"([\d.]+)\s*([万亿KMB]?)", str(x or "").replace(",", ""), re.I)
    if not m:
        return 0
    return int(float(m.group(1)) * {"万": 1e4, "亿": 1e8, "K": 1e3, "M": 1e6, "B": 1e9}.get(m.group(2).upper(), 1))


def norm(x):
    return re.sub(r"[^0-9a-z一-鿿]+", "", str(x or "").casefold())


def aweme_to_video(a: dict) -> dict:
    """TikHub 的 aweme 对象 → 统一的作品字典。"""
    t = int(a.get("create_time") or 0)
    vid = str(a.get("aweme_id") or a.get("id") or "")
    st = a.get("statistics") or a.get("stats") or {}
    mu = a.get("music") or {}
    author = a.get("author") or {}
    followers_raw = author.get("follower_count") or author.get("mplatform_followers_count")
    return {"id": vid, "title": str(a.get("desc") or ""), "url": f"https://www.douyin.com/video/{vid}", "ts": t,
            "publish": datetime.fromtimestamp(t).strftime("%Y-%m-%d %H:%M:%S") if t else "",
            "bgm": str(mu.get("title") or ""), "author": str(author.get("nickname") or ""),
            "author_sec_uid": str(author.get("sec_uid") or ""),
            "likes": num(st.get("digg_count")), "comments": num(st.get("comment_count")),
            "collects": num(st.get("collect_count")), "shares": num(st.get("share_count")),
            "_followers": num(followers_raw) if followers_raw not in (None, "") else None}


class TikHub:
    def __init__(self, key: str):
        if not key:
            raise StopExternal("未配置 TikHub Token（config 顶层 tikhub.token）")
        self.h = {"Authorization": "Bearer " + key}

    def get(self, path, p=None):
        return req(API + path + ("?" + urllib.parse.urlencode(p) if p else ""), self.h)

    def resolve(self, ident):
        """抖音号 → (sec_uid, 昵称, 粉丝数)。"""
        p = self.get("/api/v1/douyin/web/handler_user_profile_v2", {"unique_id": ident})
        s = str(find(p, ("sec_uid", "sec_user_id")) or "")
        if not s.startswith("MS4wLjAB"):
            raise RuntimeError("无法解析sec_uid")
        return s, str(find(p, ("nickname",)) or ident), num(find(p, ("follower_count", "mplatform_followers_count")))

    def resolve_sec(self, sec):
        p = self.get("/api/v1/douyin/web/handler_user_profile", {"sec_user_id": sec})
        raw = find(p, ("follower_count", "mplatform_followers_count"))
        return sec, str(find(p, ("nickname", "unique_id")) or sec), num(raw) if raw not in (None, "") else None

    def one_video(self, share_url):
        """分享链接 → 单条作品的 aweme 对象（含作者和数据）。"""
        p = self.get("/api/v1/douyin/app/v3/fetch_one_video_by_share_url", {"share_url": share_url})
        detail = find(p, ("aweme_detail",)) or (p.get("data") or {})
        return detail if isinstance(detail, dict) else {}

    def from_share(self, url):
        a = self.one_video(url)
        s = str(find(a, ("sec_uid", "sec_user_id")) or "")
        if not s.startswith("MS4wLjAB"):
            raise RuntimeError("作品无法反查账号")
        return s, str(find(a, ("nickname",)) or ""), num(find(a, ("follower_count", "mplatform_followers_count")))

    def posts(self, sec, since=0, pages=10):
        """sec_uid → 作品列表（新到旧）；since 为 unix 秒，只要此后发布的。"""
        out, seen, cur = [], set(), 0
        for _ in range(pages):
            p = self.get("/api/v1/douyin/app/v3/fetch_user_post_videos",
                         {"sec_user_id": sec, "max_cursor": cur, "count": 20, "sort_type": 0})
            d = (p.get("data") or {}).get("data") or p.get("data") or {}
            items = d.get("aweme_list") or d.get("items") or []
            ts = []
            for a in items:
                v = aweme_to_video(a)
                ts.append(v["ts"])
                if not v["id"] or v["id"] in seen or v["ts"] < since:
                    continue
                seen.add(v["id"])
                out.append(v)
            nxt = d.get("max_cursor") or d.get("next_cursor")
            if not items or (since and ts and min(ts) < since) or not d.get("has_more", True) or nxt in (None, cur):
                break
            cur = nxt
        return sorted(out, key=lambda x: x["ts"], reverse=True)


def dasheng_media(url, uid, key):
    """大圣去水印：任意短视频分享链接 → (无水印直链, 接口返回的 data)。"""
    form = urllib.parse.urlencode({"type": "dsp", "uid": uid, "key": key, "url": url}).encode()
    p = req("https://api.zhuceka.cn/home/api", {"Content-Type": "application/x-www-form-urlencoded"}, form, "POST", 2)
    if p.get("code") != 200:
        raise RuntimeError(str(p.get("msg") or "大圣失败"))
    d = p.get("data") or {}
    for k in ("video", "video_url", "url", "play_url", "video4k"):
        if isinstance(d.get(k), str) and d[k].startswith("http"):
            return d[k], d
    raise RuntimeError("大圣无直链")
