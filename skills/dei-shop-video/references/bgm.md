# 背景音乐：去哪找、怎么下、版权

## 首选：Pixabay（用户手动点下载）

- Pixabay 音乐可免费商用，但**每次下载都有 Cloudflare 人机验证**，自动化浏览器过不了（带上用户的登录态也一样，2026-11 实测）。不要尝试绕过验证。
- 做法：Agent 先挑好 3–5 首，给用户链接 → 用户在自己的浏览器里点「下载」→ 用户说「下好了」→ `python3 scripts/bgm.py <工程> --latest` 取「下载」文件夹里最新的文件。
- **避开页面上写着「已注册内容ID」（Content ID）的曲子**：投抖音、视频号可能被平台认领。热门曲大多带内容ID，挑的时候逐个打开页面看。
- 搜索词：`upbeat advertising`、`happy commercial`、`cheerful vlog`、`funk upbeat`；时长 1–3 分钟、开头 5 秒内有鼓点的优先。

## 备选：Openverse / Jamendo（可以直接下载）

- `https://api.openverse.org/v1/audio/?q=<关键词>&license=cc0,by,by-sa&category=music` 能搜到 Jamendo 上 CC0 / CC BY 的曲子，返回的 `url` 可以直接下载。
- CC BY 要署名：交付说明里写「曲名 — 作者（平台，CC BY）」。不要用 NC（非商用）许可的曲子给客户投放。

## 用户自己的音乐库

用户给了本地音乐文件夹时，可以从里面挑；先确认这批音乐的授权能不能用于客户投放，不确定就说明，让用户决定。

## 混音

- `bgm.py` 测 BPM，跳过前奏（默认 4 秒）后从第一个节拍开始用。
- 人声出来时压到 `duck`（默认 0.55），片头片尾回到满音量。用户嫌 BGM 小就调 `bgm.volume`（0.75 → 0.9），嫌盖人声就降 `duck`。
