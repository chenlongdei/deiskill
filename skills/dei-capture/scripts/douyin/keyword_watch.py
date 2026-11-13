#!/usr/bin/env python3
"""抖音关键词巡检：抖音指数「视频」搜索 → 每个关键词看前几页 → 逐条打开视频页取详情 → 阿里云转写。

跑的时候不需要 AI：装好、自检、登录、设定时都是命令，Claude Code、Codex、WorkBuddy 或手动在终端里都一样。

  python3 keyword_watch.py doctor                      # 开跑前自检：依赖、Chrome、登录、阿里云 Key、保存位置、定时
  python3 keyword_watch.py login                       # 在专用 Chrome 里扫码登录抖音（一次）
  python3 keyword_watch.py run                         # 跑配置里的全部关键词（不写 run 也一样）
  python3 keyword_watch.py run --only 商业思维          # 只跑指定关键词（逗号分隔），结果计入去重
  python3 keyword_watch.py run --per-keyword 2 --fast  # 试跑：少量、短停留，不计入去重和定时状态
  python3 keyword_watch.py schedule --every-days 3 --at 02:00   # 登记系统定时（本机时间），macOS/Windows/Linux
  python3 keyword_watch.py schedule --run-now          # 登记后立刻按定时的方式跑一轮
  python3 keyword_watch.py unschedule

流程（在专用 Chrome 实例里模拟真人：逐字输入、点选筛选、每页看完再翻页、视频停留观看、关键词之间休息）：
  1. 创作者中心 → 抖音指数 → 视频 搜索（接口 api/v2/index/itemQuery，一次返回最多 1000 条，前端每页 10 条）
  2. 点选垂类（按关键词配置）、时长、类型、发布时间。页面点不动时（抖音改版），用学到的筛选参数直接调同一个接口
  3. 每页把本页视频逐条打开，截获 aweme/detail（等同社媒助手「复制视频信息」的全部字段），看完再翻下一页
  4. 每看完一条立刻提交阿里云转写（链接新鲜）：原声交音频链接，配乐视频交视频链接；都失败再走去水印接口
  5. 出当天汇总表 + 逐字稿；更新跨期总表（首次出现、最近出现、上榜次数）

配置：dei-capture config.json 的 douyin.keyword_watch（见 config.example.json）。
产出：02_采集/抖音/关键词/关键词总表.xlsx，以及每次一个批次文件夹 YYYY-MM-DD_HHMM/（北京时间）：
汇总.xlsx、逐字稿/<关键词>/*.md、_原始数据/运行记录.json。试跑写到 99_系统/测试/抖音关键词巡检/。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("PYTHONUTF8", "1"); os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from common import douyin_root, load_config, read_full_config, sanitize_filename  # noqa: E402

try:
    from zoneinfo import ZoneInfo
    BJ = ZoneInfo("Asia/Shanghai")
except Exception:  # pragma: no cover
    from datetime import timezone
    BJ = timezone(timedelta(hours=8))

TASK_NAME = "douyin-keyword-watch"
CDP = "http://127.0.0.1:9222"
CREATOR = "https://creator.douyin.com"
INDEX_URL = CREATOR + "/creator-micro/creator-count/arithmetic-index?type=2&source=creator"
DEFAULTS = {
    "keywords": [],
    "date": "近3天",            # 发布时间不限 / 近3天 / 近7天 / 近一个月
    "duration": "大于180秒",     # 页面时长选项（平台这项筛选实测不生效，点上只为贴近真人操作）
    "min_duration": 0,           # >0 时脚本自己再按秒数筛（大于）；0 = 不按时长筛
    "label": "",                 # 类型：低粉爆款 / 高完播率 / 高涨粉率 / 高点赞率，空 = 不限
    "pages": 2,                  # 看前几页（每页 10 条）
    "per_keyword": 20,
    "dwell_seconds": [20, 45],
    "between_videos_seconds": [3, 8],
    "keyword_pause_seconds": [90, 180],
    "transcribe_workers": 4,
    "fix_words": {},             # 转写后的固定替换，如 {"沃克巴迪": "WorkBuddy"}；英文不分大小写
}
# 筛选项 → 接口参数。页面每次成功点选后会把实际发出的值记进 <关键词>/.filter_values.json，供改版时直接调接口
KNOWN_VALUES = {
    "date": {"发布时间不限": 0, "近3天": 3, "近7天": 7, "近一个月": 30},
    "duration": {"时长不限": 0, "大于180秒": 9},
    "label": {"类型不限": 0, "": 0},
    "category": {"垂类不限": "0", "": "0", "情感": "623"},
}
REQ_FIELD = {"date": "dateType", "duration": "durationType", "label": "labelType", "category": "categoryId"}


def now_bj():
    return datetime.now(BJ)


def log(msg):
    print(f"[{now_bj():%H:%M:%S}] {msg}", flush=True)


def nap(rng):
    time.sleep(random.uniform(*rng))


def notify(title, text):
    if sys.platform == "darwin":
        subprocess.run(["osascript", "-e", f'display notification {json.dumps(text)} with title {json.dumps(title)}'],
                       check=False, capture_output=True)


def settings():
    full = read_full_config()
    kw = {**DEFAULTS, **((full.get("douyin") or {}).get("keyword_watch") or {})}
    kw["keywords"] = [{"word": k} if isinstance(k, str) else k for k in kw["keywords"]]
    return kw


def base_dir(create=True) -> Path | None:
    root = douyin_root()
    if root is None:
        return None
    base = root / "关键词"
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def load_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- 浏览器 ----------

def cdp_up():
    try:
        with urllib.request.urlopen(CDP + "/json/version", timeout=2):
            return True
    except Exception:
        return False


def ensure_chrome():
    """专用 Chrome 实例（独立用户目录 + 调试端口 9222）。只需要抖音登录，不需要社媒助手插件。"""
    if cdp_up():
        return
    from shejiao_export import launch_instance
    log("专用 Chrome 实例没开，正在拉起")
    launch_instance()
    for _ in range(30):
        time.sleep(2)
        if cdp_up():
            return
    raise SystemExit("专用 Chrome 实例没能启动（端口 9222）：确认已安装 Google Chrome")


class Blocked(Exception):
    """登录失效或出现验证码，需要用户处理。"""


def logged_in(ctx) -> bool:
    return any(c["name"] == "sessionid" and c.get("value") for c in ctx.cookies("https://www.douyin.com"))


def check_page(pg):
    url = pg.url
    if "login" in url or "passport" in url:
        raise Blocked(f"需要登录：运行 keyword_watch.py login")
    # 页面常驻一个隐藏的无感验证 iframe（rmc-nocaptcha），只有真正显示出来的验证框才算
    try:
        loc = pg.locator("#captcha_container, .captcha_verify_container, iframe[src*='verify']")
        visible = any(loc.nth(i).is_visible() for i in range(loc.count()))
    except Exception:
        visible = False
    if visible:
        raise Blocked("出现验证码：在专用 Chrome 窗口里完成验证后重跑")


def dismiss_popups(pg):
    for text in ("确认", "我知道了", "知道了"):
        btn = pg.locator(f".byted-modal button:has-text('{text}'), [role=dialog] button:has-text('{text}')")
        if btn.count():
            try:
                btn.first.click(timeout=3000)
                pg.wait_for_timeout(800)
            except Exception:
                pass


# ---------- 搜索 ----------

def search_ui(pg, word, kw, category, values):
    """真人方式：逐字输入、点选筛选。返回 (请求参数, 结果列表)，并把学到的筛选参数写进 values。"""
    state = {"req": None, "items": None}

    def on_req(r):
        if "itemQuery" in r.url:
            state["req"] = r.post_data

    def on_resp(r):
        if "itemQuery" in r.url:
            try:
                state["items"] = r.json()["data"]["data"]
            except Exception:
                pass

    pg.on("request", on_req)
    pg.on("response", on_resp)
    try:
        pg.goto(INDEX_URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(random.randint(3500, 6000))
        check_page(pg)
        dismiss_popups(pg)
        box = pg.locator("input[placeholder*='视频id']").first
        box.click(timeout=15000)
        box.fill("")
        pg.keyboard.type(word, delay=random.randint(120, 260))
        pg.wait_for_timeout(random.randint(800, 1600))
        pg.keyboard.press("Enter")
        pg.wait_for_url("**/videosearch**", timeout=20000)
        pg.wait_for_timeout(random.randint(3000, 5000))
        dismiss_popups(pg)

        def pick(idx, kind, text):
            if not text or text.endswith("不限"):   # 默认就是不限，不用点
                return
            before = state["req"]
            pg.locator(".byted-select").nth(idx).click(timeout=10000)
            pg.wait_for_timeout(random.randint(700, 1500))
            pg.locator(".byted-select-option-inner-wrapper:visible",
                       has_text=re.compile(f"^{re.escape(text)}$")).first.click(timeout=10000)
            for _ in range(20):
                pg.wait_for_timeout(500)
                if state["req"] != before:
                    break
            pg.wait_for_timeout(random.randint(1500, 3000))
            if state["req"] != before:
                values.setdefault(kind, {})[text] = json.loads(state["req"]).get(REQ_FIELD[kind])

        pick(0, "category", category)
        pick(1, "duration", kw["duration"])
        pick(2, "label", kw["label"])
        pick(3, "date", kw["date"])
        pg.wait_for_timeout(1500)
        req = json.loads(state["req"] or "{}")
        if req.get("query") != word or req.get("dateType") != KNOWN_VALUES["date"].get(kw["date"], 0) \
                or (category and req.get("categoryId") in (None, "0")):
            raise RuntimeError(f"筛选没生效：{req}")
        return req, state["items"] or []
    finally:
        pg.remove_listener("request", on_req)
        pg.remove_listener("response", on_resp)


def search_api(pg, word, kw, category, values):
    """页面点不动时的后备：在已登录的创作者中心页面里直接调同一个接口。"""
    def val(kind, text):
        v = values.get(kind, {}).get(text, KNOWN_VALUES[kind].get(text))
        if v is None:
            raise RuntimeError(f"不知道「{text}」对应的接口参数（页面成功点选过一次后会记住）")
        return v
    body = {"query": word, "authorIds": [], "categoryId": str(val("category", category or "")),
            "dateType": val("date", kw["date"]), "labelType": val("label", kw["label"] or ""),
            "durationType": val("duration", kw["duration"] or "时长不限")}
    if not pg.url.startswith(CREATOR):
        pg.goto(INDEX_URL, wait_until="domcontentloaded")
        pg.wait_for_timeout(3000)
    check_page(pg)
    status, text = pg.evaluate("""async (b) => {
        const r = await fetch('/api/v2/index/itemQuery', {method: 'POST', credentials: 'include',
            headers: {'content-type': 'application/json'}, body: JSON.stringify(b)});
        return [r.status, await r.text()];
    }""", body)
    if status != 200:
        raise RuntimeError(f"接口返回 {status}")
    return body, json.loads(text)["data"]["data"]


def search(pg, word, kw, category, values):
    """返回 (请求参数, 结果列表, 是否页面方式)。"""
    try:
        req, items = search_ui(pg, word, kw, category, values)
        return req, items, True
    except Blocked:
        raise
    except Exception as e:
        log(f"  页面方式没成功（{str(e)[:80]}），改用接口直接查")
        req, items = search_api(pg, word, kw, category, values)
        return req, items, False


# ---------- 视频页 ----------

def open_video(ctx, vid, kw):
    """打开视频页，停留观看，返回 aweme_detail。"""
    pg = ctx.new_page()
    got = {}

    def on_resp(r):
        if "aweme/detail" in r.url and vid in r.url:
            try:
                got["a"] = r.json().get("aweme_detail")
            except Exception:
                pass

    pg.on("response", on_resp)
    try:
        pg.goto(f"https://www.douyin.com/video/{vid}", wait_until="domcontentloaded", timeout=45000)
        for _ in range(40):
            if got.get("a"):
                break
            pg.wait_for_timeout(500)
        check_page(pg)
        pg.wait_for_timeout(int(random.uniform(*kw["dwell_seconds"]) * 1000))
        return got.get("a")
    finally:
        pg.close()


def bj_time(ts):
    return datetime.fromtimestamp(ts, BJ).strftime("%Y-%m-%d %H:%M") if ts else ""


def media_choice(a):
    """原声 → 音频链接（小、快）；配乐 → 视频文件链接。返回 [(来源, 链接), ...] 按优先级。"""
    v, m = a.get("video") or {}, a.get("music") or {}
    video_url = ((v.get("play_addr") or {}).get("url_list") or [""])[0]
    audio_url = ((m.get("play_url") or {}).get("url_list") or [""])[0]
    vdur = (v.get("duration") or a.get("duration") or 0) / 1000
    original = m.get("is_original_sound") or m.get("owner_id") == (a.get("author") or {}).get("uid")
    out = []
    if audio_url and original and abs((m.get("duration") or 0) - vdur) <= 3:
        out.append(("音频", audio_url))
    if video_url:
        out.append(("视频", video_url))
    if audio_url and not out:
        out.append(("音频", audio_url))
    return out


def labels_of(it):
    return [n for k, n in (("isLowFansButHot", "低粉爆款"), ("isHighLikeRate", "高点赞率"),
                           ("isHighPlayOverRate", "高完播率"), ("isHighFansRiseRate", "高涨粉率")) if it.get(k)]


def record(word, rank, it, a):
    a = a or {}
    st, au = a.get("statistics") or {}, a.get("author") or {}
    sugg = []
    for blk in ((a.get("suggest_words") or {}).get("suggest_words") or []):
        sugg += [w.get("word") for w in blk.get("words") or [] if w.get("word")]
    return {
        "关键词": word, "排名": rank, "视频ID": it["itemId"], "视频指数": int(it.get("index") or 0),
        "标题": a.get("desc") or it.get("title", ""), "达人": au.get("nickname") or it.get("nickname", ""),
        "粉丝": au.get("follower_count") or it.get("fans"),
        "发布时间": bj_time(a.get("create_time")) or it.get("createTime", "")[:16],
        "时长秒": round(((a.get("video") or {}).get("duration") or 0) / 1000) or it.get("duration"),
        "点赞": st.get("digg_count"), "评论": st.get("comment_count"), "收藏": st.get("collect_count"),
        "分享": st.get("share_count"), "推荐": st.get("recommend_count"),
        "指数标签": "、".join(labels_of(it)), "视频标签": "、".join(t.get("tag_name", "") for t in a.get("video_tag") or []),
        "大家都在搜": "、".join(sugg[:3]), "视频链接": it.get("url") or f"https://www.douyin.com/video/{it['itemId']}",
        "达人链接": f"https://www.douyin.com/user/{au['sec_uid']}" if au.get("sec_uid") else "",
        "转写来源": "", "逐字稿": "", "逐字稿开头": "", "转写备注": "" if a else "视频页没取到详情",
        "_media": media_choice(a) if a else [],
    }


# ---------- 转写 ----------

def fix_text(text, fix_words):
    for wrong, right in (fix_words or {}).items():
        if re.fullmatch(r"[\x00-\x7f]+", wrong):
            text = re.sub(re.escape(wrong), right, text, flags=re.I)
        else:
            text = text.replace(wrong, right)
    return text


def transcribe(rec, outdir: Path, fix_words):
    """依次试：音频/视频链接 → 去水印接口。rec 原地更新，失败原因记在「转写备注」。"""
    from asr import paraformer_url, paragraphs
    errors = []
    tries = list(rec["_media"])
    i = 0
    while True:
        if i == len(tries):           # 最后一招：去水印接口（Monid / 大圣，配置了才有）
            try:
                from parse_video_url import parse_one
                media, src, _ = parse_one(load_config(), rec["视频链接"])
                if not isinstance(media, str) or not media.startswith("http"):
                    errors.append(f"去水印：{src}")
                    break
                tries.append((f"去水印({src})", media))
            except Exception as e:
                errors.append(f"去水印：{e}")
                break
        src, url = tries[i]
        i += 1
        try:
            cues, dur = paraformer_url(url)
        except Exception as e:
            if "NO_VALID_FRAGMENT" in str(e):   # 阿里云：整段没有人声，换链接也一样
                rec.update(转写来源=f"{src}（无口播）", 逐字稿开头="没有识别到人声（可能是字幕加配乐）")
                rec["转写备注"] = "；".join(errors)
                return rec
            errors.append(f"{src}：{str(e)[:120]}")
            continue
        body = fix_text("\n\n".join(paragraphs(cues)), fix_words) or "（没有识别到语音）"
        # 中文字数每分钟不到 40：多半是纯字幕 + 配乐、没有人说话，识别出来的是乱码
        cjk = len(re.findall(r"[一-鿿]", body))
        if cjk < 40 * max((dur or rec.get("时长秒") or 60) / 60, 1):
            src += "（无口播）"
            body = "> 这条视频基本没有人声口播（可能是字幕加配乐），下面的识别结果不可用。\n\n" + body
        name = f"{rec['排名']:02d}_{sanitize_filename(rec['标题'], 40)}.md"
        fm = {k: rec[k] for k in ("关键词", "视频ID", "标题", "达人", "发布时间", "时长秒", "视频指数",
                                  "点赞", "评论", "收藏", "分享", "视频链接")}
        fm["转写来源"] = src
        head = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items())
        (outdir / name).write_text(f"---\n{head}\n---\n\n# {rec['标题']}\n\n{body}\n", encoding="utf-8")
        rec.update(转写来源=src, 逐字稿=f"{outdir.name}/{name}",
                   逐字稿开头=re.sub(r"^(>.*\n\n)?\[\d+:\d+\]\s*", "", body)[:80])
        rec["转写备注"] = "；".join(errors)
        return rec
    rec.update(转写来源="失败", 逐字稿="", 逐字稿开头="")
    rec["转写备注"] = "；".join(errors)[:300]
    return rec


# ---------- 翻页 ----------

def walk_pages(pg, ctx, word, items, kw, seen, ui, submit):
    """一页一页来：本页视频逐条打开看完（每条看完立刻提交转写），再点下一页。"""
    recs, skipped, shown = [], {"时长不够": 0, "以前采过": 0}, []
    pages = min(kw["pages"], (len(items) + 9) // 10)
    for page in range(1, pages + 1):
        if page > 1 and ui:
            try:
                pg.locator(".byted-pager-item", has_text=re.compile(f"^{page}$")).first.click(timeout=10000)
                pg.wait_for_timeout(random.randint(2000, 3500))
            except Exception:
                ui = False   # 翻页按钮点不动就不点了，结果列表已经在手上
        for it in items[(page - 1) * 10: page * 10]:
            shown.append(it)
            if len(recs) >= kw["per_keyword"]:
                continue
            if kw["min_duration"] and (it.get("duration") or 0) <= kw["min_duration"]:
                skipped["时长不够"] += 1
                continue
            if it["itemId"] in seen:
                skipped["以前采过"] += 1
                continue
            log(f"  第 {page} 页 [{len(recs) + 1}] {it['title'][:30]}")
            try:
                a = open_video(ctx, it["itemId"], kw)
            except Blocked:
                raise
            except Exception as e:
                log(f"    打开失败：{e}")
                a = None
            rec = record(word, len(recs) + 1, it, a)
            recs.append(rec)
            submit(rec)
            nap(kw["between_videos_seconds"])
    return recs, pages, skipped, shown


# ---------- 表格 ----------

DAY_COLUMNS = ["关键词", "排名", "视频指数", "标题", "达人", "粉丝", "发布时间", "时长秒", "点赞", "评论", "收藏",
               "分享", "推荐", "指数标签", "视频标签", "大家都在搜", "逐字稿开头", "转写来源", "逐字稿", "转写备注",
               "视频链接", "达人链接"]
MASTER_COLUMNS = ["最近出现", "首次出现", "上榜次数", "关键词", "视频指数", "标题", "达人", "粉丝", "发布时间", "时长秒",
                  "点赞", "评论", "收藏", "分享", "指数标签", "视频标签", "大家都在搜", "逐字稿开头", "逐字稿",
                  "视频链接", "达人链接"]
WIDE = {"标题": 42, "逐字稿开头": 50, "视频标签": 22, "大家都在搜": 30, "视频链接": 20, "达人链接": 20,
        "逐字稿": 28, "转写备注": 30, "关键词": 14}


def write_xlsx(rows, columns, path: Path, sheet):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(columns)
    for r in rows:
        ws.append([r.get(c, "") for c in columns])
    for c in ws[1]:
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F4E79")
    for i, col in enumerate(columns, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = WIDE.get(col, 10)
    for row in ws.iter_rows(min_row=2):
        for c in row:
            col = columns[c.column - 1]
            c.alignment = Alignment(vertical="top", wrap_text=col in ("标题", "逐字稿开头"))
            if col in ("视频链接", "达人链接") and c.value:
                c.hyperlink = c.value
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)


def update_master(base: Path, day: str, recs, shown_by_word, folder: str = ""):
    """跨期总表：新采的视频补全资料；本次又出现在前几页的旧视频，上榜次数 +1、更新最新视频指数。"""
    store_path = base / ".master.json"
    store = load_json(store_path, {})
    for word, shown in shown_by_word.items():
        for it in shown:
            m = store.get(it["itemId"])
            if m is None:
                continue
            if m.get("最近出现") != day:
                m["上榜次数"] = m.get("上榜次数", 1) + 1
                m["最近出现"] = day
            m["视频指数"] = int(it.get("index") or m.get("视频指数") or 0)
            if word not in m["关键词"].split("、"):
                m["关键词"] += "、" + word
    for r in recs:
        m = store.get(r["视频ID"])
        keep = {k: r.get(k, "") for k in MASTER_COLUMNS if k in r}
        if r.get("逐字稿"):
            keep["逐字稿"] = f"{folder or day}/逐字稿/{r['逐字稿']}"
        if m is None:
            store[r["视频ID"]] = {**keep, "首次出现": day, "最近出现": day, "上榜次数": 1}
        else:
            m.update({k: v for k, v in keep.items() if v not in ("", None) and k != "关键词"})
    save_json(store_path, store)
    rows = sorted(store.values(), key=lambda m: (m.get("最近出现", ""), m.get("上榜次数", 0), m.get("视频指数", 0)),
                  reverse=True)
    write_xlsx(rows, MASTER_COLUMNS, base / "关键词总表.xlsx", "总表")
    return len(store)


# ---------- run ----------

def cmd_run(args):
    import signal
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))

    kw = settings()
    trial = bool(args.per_keyword or args.fast)   # 试跑不记去重、不算定时运行
    if args.per_keyword:
        kw["per_keyword"] = args.per_keyword
    if args.fast:
        kw.update(dwell_seconds=[4, 6], between_videos_seconds=[1, 2], keyword_pause_seconds=[5, 10])
    if not kw["keywords"]:
        raise SystemExit("config.json 的 douyin.keyword_watch.keywords 为空：先问用户要搜哪些词")
    if args.only:
        only = {w.strip() for w in args.only.split(",")}
        kw["keywords"] = [k for k in kw["keywords"] if k["word"] in only]
    base = base_dir()
    if base is None:
        raise SystemExit("未配置 output_root：先按 SKILL.md「首次配置」问用户保存位置")
    last_file, seen_file, lock = base / ".last_run", base / ".seen.json", base / ".lock"
    values_file = base / ".filter_values.json"

    if args.every_days and last_file.exists():
        last = datetime.fromisoformat(last_file.read_text().strip())
        if now_bj() - last < timedelta(days=args.every_days) - timedelta(hours=2):
            print(f"上次成功运行 {last:%Y-%m-%d %H:%M}，未满 {args.every_days:g} 天，跳过")
            return 0
    if lock.exists() and time.time() - lock.stat().st_mtime < 6 * 3600:
        raise SystemExit("已有一次运行在进行（.lock 不到 6 小时），跳过")
    lock.write_text(str(os.getpid()))

    seen = load_json(seen_file, {})
    values = load_json(values_file, {})
    today = f"{now_bj():%Y-%m-%d}"
    import dei_workspace
    if trial:
        try:
            trial_base = dei_workspace.system("测试") / "抖音关键词巡检"
        except SystemExit:
            trial_base = base / "_试跑"
        day = dei_workspace.batch_dir(trial_base, "试跑")
    else:
        day = dei_workspace.batch_dir(base)
    run = {"开始": now_bj().isoformat(timespec="seconds"), "设置": {k: v for k, v in kw.items() if k != "keywords"},
           "关键词": {}, "状态": "ok"}
    rows, shown_by_word = [], {}
    try:
        ensure_chrome()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p, ThreadPoolExecutor(kw["transcribe_workers"]) as ex:
            ctx = p.chromium.connect_over_cdp(CDP).contexts[0]
            if not logged_in(ctx):
                raise Blocked("专用 Chrome 里没有登录抖音：运行 keyword_watch.py login")
            pg = ctx.new_page()
            try:
                for n, k in enumerate(kw["keywords"]):
                    word, cat = k["word"], k.get("category", "")
                    kwk = {**kw, **{x: k[x] for x in ("min_duration", "duration", "label") if x in k}}
                    if n:
                        log("关键词之间休息一会儿")
                        nap(kw["keyword_pause_seconds"])
                    log(f"搜索「{word}」{'（垂类：' + cat + '）' if cat else ''}")
                    info = {"垂类": cat or "不限"}
                    try:
                        req, items, ui = search(pg, word, kwk, cat, values)
                        save_json(values_file, values)
                        info.update({"请求参数": req, "结果总数": len(items), "方式": "页面" if ui else "接口"})
                    except Blocked:
                        raise
                    except Exception as e:
                        info["错误"] = str(e)[:300]
                        run["状态"] = "partial"
                        log(f"「{word}」搜索失败：{e}")
                        run["关键词"][word] = info
                        continue
                    tdir = day / "逐字稿" / sanitize_filename(word, 30)
                    tdir.mkdir(parents=True, exist_ok=True)
                    futures = []
                    submit = (lambda r: None) if args.no_transcribe else \
                        (lambda r: futures.append(ex.submit(transcribe, r, tdir, kw["fix_words"])))
                    recs, pages, skipped, shown = walk_pages(pg, ctx, word, items, kwk, {} if trial else seen, ui, submit)
                    log(f"「{word}」共 {len(items)} 条，看了 {pages} 页，入选 {len(recs)} 条，跳过 {skipped}")
                    for f in futures:
                        f.result()
                    ok = sum(1 for r in recs if r.get("转写来源") != "失败")
                    info.update({"翻页": pages, "入选": len(recs), "跳过": skipped, "转写成功": ok})
                    if ok < len(recs):
                        run["状态"] = "partial"
                    if not trial:
                        for r in recs:
                            if r.get("转写来源") != "失败" or args.no_transcribe:
                                seen[r["视频ID"]] = today
                        save_json(seen_file, seen)
                        shown_by_word[word] = shown
                    rows += recs
                    run["关键词"][word] = info
            finally:
                pg.close()
    except Blocked as e:
        run["状态"] = "blocked"
        run["阻断"] = str(e)
        log(f"停下：{e}")
        notify("抖音关键词巡检停下了", str(e))
    finally:
        for r in rows:
            r.pop("_media", None)
        if rows:
            write_xlsx(rows, DAY_COLUMNS, day / "汇总.xlsx", "汇总")
            if not trial:
                run["总表条数"] = update_master(base, today, rows, shown_by_word, day.name)
        run["结束"] = now_bj().isoformat(timespec="seconds")
        run["条数"] = len(rows)
        save_json(day / "_原始数据" / "运行记录.json", run)
        lock.unlink(missing_ok=True)
        dei_workspace.log_run("dei-capture", "douyin-keyword-watch",
                              {"ok": "completed"}.get(run["状态"], run["状态"]), [day])

    if run["状态"] in ("ok", "partial") and rows and not trial and not args.only:
        last_file.write_text(now_bj().isoformat(timespec="seconds"))
    log(f"完成：{len(rows)} 条，状态 {run['状态']}，结果在 {day}")
    if run["状态"] != "ok":
        notify("抖音关键词巡检", f"状态 {run['状态']}，{len(rows)} 条")
    print(json.dumps({"command": "keyword_watch", "status": run["状态"], "rows": len(rows), "dir": str(day)},
                     ensure_ascii=False))
    return 0 if run["状态"] == "ok" else 1


# ---------- doctor / login / schedule ----------

def dashscope_check():
    from asr import dashscope_config
    d = dashscope_config()
    key = (d.get("api_key") or "").strip()
    if not key:
        return False, "没有阿里云百炼 Key：在 dei-capture config.json 顶层 dashscope.api_key 填 sk- 开头的 Key"
    req = urllib.request.Request(d["base_url"].rstrip("/") + "/api/v1/tasks/00000000-0000-0000-0000-000000000000",
                                 data=b"{}", method="POST",
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20):
            return True, "阿里云百炼 Key 有效"
    except urllib.error.HTTPError as e:
        return False, f"阿里云百炼 Key 无效（HTTP {e.code}）：去百炼控制台重新创建，sk- 开头"
    except Exception as e:
        return False, f"连不上阿里云：{e}"


def cmd_doctor(args):
    import scheduler
    checks = []

    def add(name, ok, msg, required=True):
        checks.append({"项目": name, "通过": ok, "说明": msg, "必需": required})

    add("Python", sys.version_info >= (3, 9), f"{sys.version.split()[0]}（需要 3.9+）")
    for mod, pip in (("playwright", "playwright"), ("openpyxl", "openpyxl")):
        try:
            __import__(mod)
            add(mod, True, "已安装")
        except ImportError:
            add(mod, False, f"缺少：python3 -m pip install {pip}（不需要 playwright install，用的是本机 Chrome）")
    kw = settings()
    add("关键词", bool(kw["keywords"]), "、".join(k["word"] for k in kw["keywords"]) or
        "没配置：在 config.json 的 douyin.keyword_watch.keywords 填要搜的词")
    base = base_dir()
    if base is None:
        add("保存位置", False, "没配置 output_root：按 SKILL.md「首次配置」问用户")
    else:
        try:
            (base / ".w").write_text("ok")
            (base / ".w").unlink()
            add("保存位置", True, str(base))
        except Exception as e:
            add("保存位置", False, f"写不进去：{e}")
    ok, msg = dashscope_check()
    add("阿里云转写", ok, msg)
    full = read_full_config()
    dy = full.get("douyin") or {}
    backup = bool((dy.get("dasheng") or {}).get("key") or (dy.get("monid") or {}).get("token"))
    add("去水印备用", backup, "已配置（阿里云下载不了原链接时才用）" if backup else
        "没配置也能跑；偶尔有视频转写会失败。需要时在 douyin.dasheng 或 douyin.monid 填凭证", required=False)
    try:
        ensure_chrome()
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            ctx = p.chromium.connect_over_cdp(CDP).contexts[0]
            add("专用 Chrome", True, "已打开（调试端口 9222）")
            add("抖音登录", logged_in(ctx), "已登录" if logged_in(ctx) else "没登录：运行 keyword_watch.py login 扫码")
    except SystemExit as e:
        add("专用 Chrome", False, str(e))
    except Exception as e:
        add("专用 Chrome", False, f"连不上：{e}")
    st = scheduler.status(TASK_NAME)
    add("定时", bool(st), f"已登记 {st.get('任务')}" if st else
        "没登记：keyword_watch.py schedule --every-days 3 --at 02:00", required=False)
    if base is not None and scheduler.protected(base) and args.write_test:
        ok, msg = scheduler.mac_write_test(base)
        add("后台写入权限", ok, msg if ok else
            f"{msg}。打开「系统设置 → 隐私与安全性 → 完全磁盘访问权限」，点 +，按 Cmd+Shift+G 粘贴：{scheduler.disk_access_app()}")
    for c in checks:
        mark = "✓" if c["通过"] else ("✗" if c["必需"] else "·")
        print(f"{mark} {c['项目']}：{c['说明']}")
    bad = [c for c in checks if c["必需"] and not c["通过"]]
    print(json.dumps({"command": "doctor", "ok": not bad, "failed": [c["项目"] for c in bad]}, ensure_ascii=False))
    return 1 if bad else 0


def cmd_login(args):
    ensure_chrome()
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = p.chromium.connect_over_cdp(CDP).contexts[0]
        if logged_in(ctx):
            print("已经登录了，不用再扫码")
            return 0
        pg = ctx.new_page()
        pg.goto(CREATOR + "/", wait_until="domcontentloaded")
        pg.bring_to_front()
        print("请在弹出的 Chrome 窗口里用抖音 App 扫码登录（最多等 5 分钟）……", flush=True)
        for _ in range(150):
            time.sleep(2)
            if logged_in(ctx):
                print("✓ 登录成功。登录状态保存在专用 Chrome 里，以后自动沿用")
                return 0
    print("✗ 5 分钟内没检测到登录，请重新运行 login")
    return 1


def cmd_schedule(args):
    import scheduler
    base = base_dir()
    if base is None:
        raise SystemExit("未配置 output_root：先按 SKILL.md「首次配置」问用户保存位置")
    if scheduler.protected(base):
        ok, msg = scheduler.mac_write_test(base)
        if not ok:
            print(f"✗ 后台任务写不进保存位置：{msg}")
            print("  打开「系统设置 → 隐私与安全性 → 完全磁盘访问权限」，点 +，按 Cmd+Shift+G 粘贴下面的路径，添加后打开开关，再运行一次 schedule：")
            print(f"  {scheduler.disk_access_app()}")
            return 1
        print(f"✓ {msg}")
    info = scheduler.install(TASK_NAME, [str(Path(__file__).resolve()), "run", "--every-days", f"{args.every_days:g}"],
                             args.at, SKILL_DIR)
    h, m = map(int, args.at.split(":"))
    local = datetime.now().astimezone().replace(hour=h, minute=m, second=0, microsecond=0)
    info["北京时间"] = local.astimezone(BJ).strftime("%H:%M")
    info["说明"] = f"每天本机 {args.at}（北京时间 {info['北京时间']}）检查一次，距上次成功运行满 {args.every_days:g} 天才真正跑"
    for k, v in info.items():
        print(f"{k}：{v}")
    if args.run_now:
        print("已触发一轮（和定时走同一条路），进度看日志：", info["日志"]) if scheduler.run_now(TASK_NAME) else \
            print("触发失败，可以手动运行 keyword_watch.py run")
    return 0


def cmd_unschedule(args):
    import scheduler
    scheduler.remove(TASK_NAME)
    print("已删除定时任务")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", nargs="?", default="run", choices=["run", "doctor", "login", "schedule", "unschedule"])
    ap.add_argument("--only", help="run：只跑这些关键词，逗号分隔")
    ap.add_argument("--every-days", type=float, default=None, help="run：距上次成功运行不足 N 天就退出；schedule：间隔天数，默认 3")
    ap.add_argument("--no-transcribe", action="store_true")
    ap.add_argument("--per-keyword", type=int, help="试跑：临时覆盖每个关键词的条数")
    ap.add_argument("--fast", action="store_true", help="试跑：缩短停留时间")
    ap.add_argument("--at", default="02:00", help="schedule：每天几点（本机时间 HH:MM）")
    ap.add_argument("--run-now", action="store_true", help="schedule：登记后立刻跑一轮")
    ap.add_argument("--write-test", action="store_true", help="doctor：macOS 上测试后台任务能否写保存位置")
    args = ap.parse_args()
    if args.action == "schedule" and args.every_days is None:
        args.every_days = 3
    if args.action == "run" and args.every_days is None:
        args.every_days = 0
    return {"run": cmd_run, "doctor": cmd_doctor, "login": cmd_login,
            "schedule": cmd_schedule, "unschedule": cmd_unschedule}[args.action](args)


if __name__ == "__main__":
    sys.exit(main())
