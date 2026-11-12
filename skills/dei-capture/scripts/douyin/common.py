#!/usr/bin/env python3
"""抖音模块公共工具：配置加载、状态存取(videos.json)、HTTP、字段映射。仅用标准库，Python 3.9+。

源自 content-toolkit（chenlongdei12-dev，CC BY-NC-SA 4.0，见同目录 LICENSE），并入 dei-capture 时改了配置读取：
配置在 dei-capture 的 config.json 里（douyin 段 + 顶层共用的 dashscope 段），数据默认放在 <output_root>/抖音/ 下。
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[2]          # dei-capture 根目录
CONFIG_PATH = Path(os.environ.get("DEI_CAPTURE_CONFIG") or SKILL_DIR / "config.json")
EXAMPLE_CONFIG_PATH = SKILL_DIR / "config.example.json"
sys.path.insert(0, str(SKILL_DIR / "scripts"))
DEFAULT_DASHSCOPE = {"api_key": "", "base_url": "https://dashscope.aliyuncs.com", "model": "paraformer-v2",
                     "language_hints": ["zh", "en"], "poll_interval_seconds": 10, "max_wait_seconds": 1800}

# 字段候选路径：未知 API/导出文件按顺序自动匹配，config.json 的 monid.field_map 可覆盖
# 前面的候选是 Monid anyapi 端点的 normalized 字段名（实测 2026-11）
DEFAULT_FIELD_MAP = {
    "video_id": ["video_id", "aweme_id", "id", "note_id"],
    "title": ["caption", "title", "desc", "description", "note_desc", "text"],
    "author_name": ["authorNickname", "author_name", "author.nickname", "nickname", "author.name", "author"],
    "author_id": ["authorSecUserId", "author_id", "author.uid", "author.sec_uid", "uid"],
    "publish_time": ["createdUtc", "publish_time", "create_time", "published_at", "createTime"],
    "share_url": ["share_url", "url", "link", "short_url"],
    "page_url": ["page_url", "video_url", "web_url"],
    "video_file_url": ["videoUrl", "video_file_url", "play_url", "play_addr", "download_url"],
    "likes": ["likes", "like_count", "digg_count", "statistics.digg_count", "liked_count"],
    "comments": ["comments", "comment_count", "statistics.comment_count"],
    "shares": ["shares", "share_count", "statistics.share_count"],
    "collects": ["saves", "collects", "collect_count", "statistics.collect_count"],
}


def log_cost(cfg, endpoint, cost):
    """Monid 花费台账：追加到 workspace/.cost_log.json。"""
    try:
        if not cost:
            return
        p = Path(cfg["workspace"]) / ".cost_log.json"
        ledger = []
        if p.exists():
            try:
                ledger = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                ledger = []
        ledger.append({"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "endpoint": endpoint,
                       "cost": cost})
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def cost_total(cfg):
    """返回 (总花费, 条数)。"""
    try:
        p = Path(cfg["workspace"]) / ".cost_log.json"
        if not p.exists():
            return 0.0, 0
        ledger = json.loads(p.read_text(encoding="utf-8"))
        return sum(x.get("cost", 0) for x in ledger), len(ledger)
    except Exception:
        return 0.0, 0


def monid_run(cfg, provider, endpoint, body, max_wait=180):
    """调用 Monid 工具网关：POST /v1/run 提交，READY/RUNNING 时轮询 /v1/runs/{id}。
    返回完整 run 对象（结果在 output 字段；成本在 cost）。"""
    m = cfg.get("monid", {})
    token = m.get("token") or os.environ.get("MONID_API_KEY", "")
    base = (m.get("api_base") or "https://api.monid.ai").rstrip("/")
    if not token:
        raise HttpError("缺少 Monid token：填 config.json 的 monid.token，或设环境变量 MONID_API_KEY")
    run = http_json("POST", base + "/v1/run",
                    headers={"Authorization": f"Bearer {token}"},
                    body={"provider": provider, "endpoint": endpoint, "input": {"body": body}},
                    timeout=90)
    deadline = time.time() + max_wait
    while run.get("status") in ("READY", "RUNNING", "STOPPING") and time.time() < deadline:
        time.sleep(4)
        run = http_json("GET", f"{base}/v1/runs/{run['runId']}",
                        headers={"Authorization": f"Bearer {token}"}, timeout=60)
    if run.get("status") != "COMPLETED":
        raise HttpError(f"Monid run {run.get('runId')} 状态 {run.get('status')}："
                        f"{str(run.get('reason') or run.get('providerResponse'))[:200]}")
    return run


class HttpError(Exception):
    pass


def read_full_config(path=None):
    """读取整份 dei-capture 配置；没有 config.json 时用模板（在线步骤会因缺少 key 不可用）。"""
    p = Path(path).expanduser() if path else (CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH)
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def douyin_root():
    """<output_root>/抖音；没配置保存位置时返回 None。"""
    try:
        from capture_paths import data_dir
        return data_dir("douyin")
    except SystemExit:
        return None


def load_config(path=None, need_dirs=True):
    """返回抖音模块的扁平配置：douyin 段 + dashscope 段 + 解析好的 workspace、biji_export_base。"""
    full = read_full_config(path)
    cfg = json.loads(json.dumps(full.get("douyin") or {}))
    cfg["dashscope"] = {**DEFAULT_DASHSCOPE, **(full.get("dashscope") or {})}
    env_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if env_key:
        cfg["dashscope"]["api_key"] = env_key
    tk = (os.environ.get("TIKHUB_TOKEN") or (full.get("tikhub") or {}).get("token")
          or (full.get("youtube") or {}).get("tikhub_token") or "").strip()
    cfg["tikhub_token"] = tk
    cfg.setdefault("dasheng", {})
    root = douyin_root()
    for key, sub in (("workspace", "监控"), ("biji_export_base", "Get笔记导出")):
        if cfg.get(key):
            cfg[key] = str(Path(cfg[key]).expanduser())
        elif root is not None:
            cfg[key] = str(root / sub)
        elif need_dirs:
            raise SystemExit("未配置采集结果保存位置：请先按 dei-capture 的 SKILL.md「首次配置」询问用户，"
                             f"把 output_root 写入 {CONFIG_PATH}")
        else:
            cfg[key] = ""
    return cfg


def data_provider(cfg):
    """抖音数据来源：douyin.provider = tikhub / monid / auto（auto：有 TikHub Token 用 TikHub，否则 Monid）。"""
    want = (cfg.get("provider") or "auto").lower()
    if want in ("tikhub", "monid"):
        return want
    if cfg.get("tikhub_token"):
        return "tikhub"
    m = cfg.get("monid") or {}
    return "monid" if m.get("enabled") and m.get("token") else "none"


def platform_of(url):
    """按链接域名判断平台。"""
    host = urllib.parse.urlparse(url or "").hostname or ""
    for name, keys in (("douyin", ("douyin.com", "iesdouyin.com")), ("kuaishou", ("kuaishou.com", "gifshow.com")),
                       ("xiaohongshu", ("xiaohongshu.com", "xhslink.com")), ("bilibili", ("bilibili.com", "b23.tv")),
                       ("weibo", ("weibo.com", "weibo.cn")), ("tiktok", ("tiktok.com",)),
                       ("youtube", ("youtube.com", "youtu.be"))):
        if any(host == k or host.endswith("." + k) for k in keys):
            return name
    return "other"


def save_watch_list(sec_uid):
    """把博主加入 config.json 的 douyin.monid.watch_sec_user_ids；已在列表里返回 False。"""
    full = read_full_config(CONFIG_PATH) if CONFIG_PATH.exists() else read_full_config(EXAMPLE_CONFIG_PATH)
    watch = full.setdefault("douyin", {}).setdefault("monid", {}).setdefault("watch_sec_user_ids", [])
    if sec_uid in watch:
        return False
    watch.append(sec_uid)
    CONFIG_PATH.write_text(json.dumps(full, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def store_path(cfg):
    return Path(cfg["workspace"]) / "videos.json"


def store_load(cfg):
    p = store_path(cfg)
    if not p.exists():
        return {"videos": {}, "updated_at": None}
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise SystemExit(f"[错误] {p} 已损坏（{e}）。可先备份后删除重建。")


def store_save(cfg, store):
    p = store_path(cfg)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    tmp.replace(p)


def http_json(method, url, headers=None, body=None, timeout=60, retries=2):
    """发起 HTTP 请求并解析 JSON 响应。body 为 dict 时自动 JSON 编码。"""
    hdrs = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        if isinstance(body, dict):
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            hdrs.setdefault("Content-Type", "application/json")
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = body
    last_err = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                try:
                    return json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    raise HttpError(f"响应不是 JSON：{raw[:300]!r}")
        except urllib.error.HTTPError as e:
            detail = e.read()[:500].decode("utf-8", "replace")
            raise HttpError(f"HTTP {e.code} {e.reason}：{detail}")
        except urllib.error.URLError as e:
            last_err = e
            if attempt < retries:
                time.sleep(2 * (attempt + 1))
    raise HttpError(f"网络错误（已重试 {retries} 次）：{last_err}")


def http_download(url, dest, headers=None, timeout=300):
    """下载 URL 内容到文件（用于 ASR 结果 JSON）。"""
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        f.write(resp.read())


def deep_get(obj, dotted):
    """按 a.b.c 路径取值，支持数组下标 a.0.b。取不到返回 None。"""
    cur = obj
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        elif isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        else:
            return None
    return cur


def first_value(item, candidates):
    """按候选路径顺序取第一个非空标量值。"""
    for path in candidates or []:
        if not path:
            continue
        v = deep_get(item, path)
        if isinstance(v, (str, int, float)) and v != "" and v is not None:
            return v
    return None


def sanitize_filename(name, max_len=50):
    name = re.sub(r'[\\/:*?"<>|\r\n\t]', " ", str(name or ""))
    name = re.sub(r"\s+", " ", name).strip().strip(".")
    return name[:max_len].strip() or "untitled"


def yaml_str(v):
    """生成 YAML 安全的标量（JSON 编码是合法 YAML；None → null）。"""
    return "null" if v is None else json.dumps(str(v), ensure_ascii=False)


def normalize_time(v):
    """unix 秒/毫秒时间戳或字符串 → 'YYYY-MM-DD HH:MM:SS'（本地时区）。"""
    if v is None or v == "":
        return None
    s = str(v).strip()
    if re.fullmatch(r"\d{9,13}", s):
        n = int(s)
        if n > 10 ** 12:
            n //= 1000
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(n))
    return s


def extract_video_id(url_or_text):
    """从链接或文本里抽抖音视频 aweme_id（video/123... 或 modal_id=123...）。"""
    m = re.search(r"(?:iesdouyin|douyin)\.com/(?:\S*?/)?video/(\d{15,})", url_or_text or "")
    if not m:
        m = re.search(r"modal_id=(\d{15,})", url_or_text or "")
    return m.group(1) if m else None


def is_direct_media_url(url):
    """判断 URL 是否已经是音视频文件直链（按扩展名，或 ?mime_type=video_mp4 这类无后缀直链）。"""
    u = (url or "").lower()
    return bool(re.search(r"\.(mp4|m4a|mp3|wav|aac|mov|flv)(\?|$)", u)) or "mime_type=video" in u


def scan_media_urls(obj, out=None, limit=5):
    """递归扫描 JSON 里所有像音视频直链的字符串（解析接口返回结构未知时的兜底）。"""
    if out is None:
        out = []
    if isinstance(obj, dict):
        for v in obj.values():
            scan_media_urls(v, out, limit)
    elif isinstance(obj, list):
        for v in obj:
            scan_media_urls(v, out, limit)
    elif isinstance(obj, str) and obj.startswith("http") and is_direct_media_url(obj):
        if obj not in out:
            out.append(obj)
            if len(out) >= limit:
                return out
    return out


def now_str():
    return time.strftime("%Y-%m-%d %H:%M:%S")
