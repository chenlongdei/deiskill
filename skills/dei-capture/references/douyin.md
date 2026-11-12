# 抖音模块

把抖音博主的内容变成「逐字稿 + 点赞评论数据」的 Markdown 素材库：一个博主一个文件夹，每条视频一份带 frontmatter 的 Markdown，外加 INDEX 索引。

> 本模块源自 content-toolkit（作者 chenlongdei12-dev），协议为 CC BY-NC-SA 4.0，全文见 `scripts/douyin/LICENSE`。仅限个人学习研究，不得用于商业用途（包括收费代采集、打包进付费课程）。

## 两条流水线怎么选

| | 监控流水线 | 导出流水线 |
| --- | --- | --- |
| 适合 | 几条链接直接出稿；持续盯博主，只要最新 N 条 | 一次性导出博主**全部**历史内容 |
| 数据来源 | Monid 网关（抖音数据 + 无水印直链） | Get笔记（得到大脑）订阅 + 社媒助手插件 |
| 需要 | 阿里云百炼 Key + Monid Key（都计费，有免费额度） | 在 Get笔记订阅该博主并扫码登录一次；社媒助手插件 |
| 速度 | 每条约 1—2 分钟（主要是转写） | 约 3 篇/秒，700 篇约 6 分钟 |

用户只给链接 → 监控线 `--links`。要博主全部历史 → 先问用户是否在 Get笔记订阅了该博主；订阅了走导出线（免费、快），没订阅走监控线（按条计费，先报数量和费用）。

## 第一步：自检

```bash
python3 scripts/douyin/doctor.py
```

照 ↳ 提示补齐。key 都在 dei-capture 的 `config.json`：百炼 Key 在顶层 `dashscope.api_key`（sk- 开头，YouTube 本地转写之外的直链转写也用它）；Monid Key 在 `douyin.monid.token`（monid_live_ 开头）。用到哪条线才问对应的 key。

## 命令（在 dei-capture 目录下）

```bash
# 监控流水线
python3 scripts/douyin/run.py monitor --links "https://v.douyin.com/xxxx/,https://v.douyin.com/yyyy/"
python3 scripts/douyin/run.py monitor --blogger-sec-uid MS4wLjAB...   # 加入监控列表并拉最新视频
python3 scripts/douyin/run.py monitor                                  # 跑监控列表里所有博主

# 导出流水线
python3 scripts/douyin/biji_export.py login                     # 扫码，一次；之后无头自动刷新
python3 scripts/douyin/run.py export-biji "博主名" --with-data   # 名字模糊匹配，导完自动合并数据
python3 scripts/douyin/run.py export-data "https://www.douyin.com/user/MS4..."  # 社媒助手自动导数据
python3 scripts/douyin/run.py export-merge 博主名               # 单独合并逐字稿 + 数据
```

每一步也能单独跑，全部幂等、可断点续跑：

- 监控：`monid_fetch.py` → `parse_video_url.py` → `asr_transcribe.py` → `merge_output.py`
- 导出：`biji_export.py`（topics / follows / export / status）→ `social_stats.py` 或 `shejiao_export.py` → `merge_export.py`

`sec_user_id` 是博主主页链接 `/user/` 后面那一串。用户只给抖音号或昵称时，请用户给主页链接或任意一条作品链接。

## 核心机制

- **幂等状态库**：监控线所有步骤读写 `<监控>/videos.json`，阶段 collected → parsed → transcribed → merged；中断重跑不重复计费（task_id 都会保存）。导出线按文件名里的 post_id 去重、增量续传。
- **计费**：Monid 每次调用 $0.0012，每条视频约 2 次（列表 + 解析）；阿里云按语音时长，约每小时几毛钱。Monid 花费自动记在 `<监控>/.cost_log.json`，doctor 会显示累计。粗算：100 条视频约 $0.25 加几块钱转写费。
- **逐字稿复用**：`douyin.transcript_library` 指向导出线的素材库根目录时，监控线遇到库里已有的视频（按 aweme_id 匹配）直接复用逐字稿，不花转写费。
- **直链时效**：无水印直链几小时就失效，解析完要尽快转写，别隔天。
- 纯 BGM 无人声的视频转写返回 `SUCCESS_WITH_NO_VALID_FRAGMENT`，属正常，跳过。

## 导出流水线细节

**Get笔记**：API 是 `knowledge-api.trytalks.com`，JWT 30 分钟自动刷新。凭据和登录态在 `~/.biji_exporter/`（由脚本自己管理，不进任何仓库）。登录需要 playwright：`pip3 install --user playwright && python3 -m playwright install chromium`。开着代理软件报错时，关掉代理或设 `BIJI_USE_SYSTEM_PROXY=1`。

**社媒助手（自动）**：需要一个专用 Chrome 实例，一次性搭好：

```bash
open -na "Google Chrome" --args --user-data-dir="$HOME/.shejiao_automation" \
  --remote-debugging-port=9222 --no-first-run --no-default-browser-check
# 在这个实例里：装「社媒助手」插件 + 登录抖音 + 登录插件账号
```

**社媒助手（手动）**：在 Chrome 达人主页用插件「批量导出视频数据」，字段勾选标题、发布时间、点赞、评论、收藏、转发、视频链接；告诉 Agent 文件位置，或放进 `<抖音>/社媒数据/`。

**合并**：先按视频链接 ID 精确匹配，再按标题归一化、相似度 ≥ 0.75、包含关系；匹配不到的标 ❌ 并列在 INDEX 末尾（多数是已删稿）。

## 本地音视频文件

没有链接、只有文件时，用统一转写入口：`python3 scripts/transcribe.py <文件>`（本地 whisper）。

## 排错

| 现象 | 处理 |
| --- | --- |
| doctor ❌ | 照 ↳ 提示修；key 无效多半是类型填错（百炼要 sk-，Monid 要 monid_live_） |
| InvalidFile.DownloadFailed | 直链过期或防盗链 → 重跑 parse_video_url.py 后立即转写 |
| InvalidApiKey | 百炼 key 填错（要 sk- 开头的 DashScope Key，不是阿里云 RAM AccessKey） |
| Throttling / 限流 | 稍后重跑（断点续传，不重复计费） |
| Monid BLOCKED | 预算控制或余额不足 → app.monid.ai 调整或充值；告诉用户，不反复重试 |
| Get笔记 403 反复 / not_logged_in | `biji_export.py login`（需要用户在场扫码） |
| 「导出视频」按钮找不到 | 专用 Chrome 实例没开或插件没登录 → 让用户打开实例手动检查一次 |
| 空稿 skip_empty | 该篇没有逐字稿（图文等），正常 |
| 匹配率低 | 看 INDEX 末尾未匹配清单，必要时调 merge_export.py 阈值 |

## 输出

```text
<output_root>/抖音/
├── 监控/            videos.json（状态库）、transcripts/、<博主>/<日期>-<标题>.md、INDEX.md、.cost_log.json
├── Get笔记导出/     <博主>_<id>/ 逐字稿；merged/<博主>/ 合并了数据的版本
└── 社媒数据/        <博主>_作品数据_YYYYMMDD.xlsx
```
