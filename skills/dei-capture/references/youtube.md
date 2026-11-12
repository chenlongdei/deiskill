# YouTube 模块

在 dei-capture 流程的 Step 0 读本文。命令都在 Skill 的 `scripts/` 目录下运行。

## 依赖与配置

| 项 | 必需 | 说明 |
| --- | --- | --- |
| `yt-dlp` | 是 | 搜索、频道、字幕都靠它。命令名不同时写 `youtube.yt_dlp_cmd` |
| `youtube.cookies_from_browser` | 遇到风控时 | 已登录 YouTube 的浏览器名：`chrome`、`safari`、`firefox`、`edge`、`brave`，可写 `chrome:Profile 1` 指定资料夹。只在用户同意后填写；macOS 读 Chrome 时可能弹出钥匙串授权 |
| `youtube.tikhub_token` | 可选 | TikHub 用户中心获取；也可用环境变量 `TIKHUB_TOKEN`。写不写 `Bearer ` 前缀都可以 |
| `youtube.whisper_model` | 可选 | 本地 whisper.cpp 模型文件的绝对路径。推荐 `ggml-large-v3-turbo-q5_0.bin`（约 550 MB，准确度接近完整版）或 `ggml-large-v3-turbo.bin`（约 1.6 GB），从 Hugging Face 的 ggerganov/whisper.cpp 仓库下载，存放位置问用户；small、base 等小模型中文错字多，不推荐；视频没有字幕时才用。需要 `whisper-cli`（命令名不同写 `whisper_cmd`）和 `ffmpeg` |
| `youtube.whisper_prompt` | 可选 | 转写时给 Whisper 的提示句。默认「以下是普通话的句子。」，让中文输出简体；转写英文视频时 `whisper_language` 设为 `en`，或清空此项 |
| `youtube.subtitle_langs` | 可选 | 人工字幕语言优先级，默认中文 → 英文 |
| `youtube.min_views` / `per_channel` | 可选 | 搜索推荐门槛，默认 10000 播放、同频道最多 2 条 |

自检：`python3 youtube.py doctor`，加 `--probe <视频ID>` 会实际访问一个视频，检查是否被风控。

## 命令

```bash
# 搜索：多个关键词合并去重，按播放量排序
python3 youtube.py search "claude code" "agent skills" [--limit 20] [--within this_month] [--engine auto|ytdlp|tikhub]

# 频道：@handle / UC... / 频道链接；--limit 0 为全部；再次运行会增量合并并标出新增
python3 youtube.py channel @claude [--limit 50] [--tabs videos,shorts,streams]

# 逐字稿：链接或 11 位视频 ID，可多个；已存在的跳过（--force 重做）
python3 youtube.py transcript <链接...> [--from-list urls.txt] [--langs zh-Hans,en]

# 查看 TikHub 可用工具和参数名（调试用，需要 Token）
python3 youtube.py tikhub-tools [subtitle]
```

## 数据来源怎么选（脚本自动处理）

| 能力 | 先用 | 再用 |
| --- | --- | --- |
| 搜索 | yt-dlp `ytsearch`（相关度）；指定 `--within` 时用 `ytsearchdate`（按最新，**不能**精确限定时间） | 指定 `--within` 且有 Token 时直接用 TikHub `youtube_web_search_video`（`order_by`）；yt-dlp 失败时用 TikHub |
| 频道 | yt-dlp `--flat-playlist` 频道分区 | yt-dlp 拿不到时用 TikHub `youtube_web_get_channel_videos_v2` |
| 逐字稿 | yt-dlp 人工字幕 → 视频原语言的自动字幕 | TikHub `youtube_web_get_video_subtitles` → 本地 whisper 转写 |

说明：

- 搜索和频道的扁平列表一般**没有发布日期**，清单里留空，不要猜。需要日期时对少量视频跑 `transcript`（逐字稿 frontmatter 里有 `upload_date`）。
- 自动字幕只取视频原语言（`<lang>-orig`），不取 YouTube 机器翻译的版本。
- 「Sign in to confirm you're not a bot」是 YouTube 对单视频请求的风控，搜索和频道列表通常不受影响。解决办法按顺序：配置 `cookies_from_browser` → 配置 TikHub Token → 稍后再试。
- TikHub 的字幕和频道接口按工具的 inputSchema 自动填参数名，返回结构不统一，脚本做了兼容解析；如果解析为空，用 `tikhub-tools` 看参数，再把返回样例记到本文。

## 筛选标准（给用户精选时）

脚本的「推荐」只按播放量和同频道上限机械筛选。交给用户前再人工过一遍：

1. **主题强相关**：标题和简介明确围绕目标主题，剔除蹭热点、标题党、泛泛盘点。
2. **去重创作者**：同一频道最多 1—2 条最好的。
3. **播放门槛**：默认 >10K；发布不到 7 天的可放宽到 >5K。
4. **时效**：重大发布事件用 `--within this_week`。
5. 默认 3—4 组关键词效果最好（中英文各半），去重后 30—40 条。

### 学习用途（学会一个软件或技能）

目的是学会，不是找热门，所以选片标准不同：

1. **覆盖层级**：关键词同时覆盖入门（beginner / tutorial / 入门 / 教程）、进阶（advanced / tips / workflow / 进阶 / 技巧）和实战（project / case / 实战 / 案例），各层都要有。
2. **版本新**：软件类加上年份或版本号（如 `2026`）；用 `--within this_year` 或最新排序补一轮，旧版教程只保留讲原理的。
3. **官方 + 高手**：官方频道必收；其他按讲得深、有完整演示优先，播放门槛可放宽到 >3K。
4. **数量**：去重后精选 15—30 条，单个频道不超过 3 条；长课程（>40 分钟）至少 1—2 条。
5. 交付时按「入门 / 进阶 / 实战」分组列出，并说明缺哪一层。

## 逐字稿格式

```markdown
---
title: "…"
video_id: "…"
url: "https://www.youtube.com/watch?v=…"
channel: "…"
upload_date: "2026-11-01"
duration: "12:34"
views: 123456
language: "en"
transcript_source: "yt-dlp 自动字幕"
captured_at: "…"
---

# 标题
## 视频简介
## 逐字稿
[0:00] 每 60 秒一段，段首是时间戳……
```

文件名 `<视频ID>_<标题>.md`，可以直接作为文档资料导入知识库或交给后续处理。

## 已知问题

- yt-dlp 太旧时 YouTube 可能解析失败：先升级 yt-dlp（用户用什么装的就用什么升级）。
- 会员、私享、年龄限制视频需要 cookies；直播回放可能只有自动字幕。
- macOS 上报 `could not find chrome cookies database`，同时 `ls ~/Library/Application Support/Google/Chrome` 显示 `Operation not permitted`：这是系统隐私保护挡住了终端，不是没装浏览器。让用户在「系统设置 → 隐私与安全性 → 完全磁盘访问权限」里给运行 Agent 的终端或应用打开权限，然后重启它；或改用 Safari、Firefox 等其他已登录 YouTube 的浏览器。
