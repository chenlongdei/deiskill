# 抖音模块

把抖音博主的内容变成「逐字稿 + 点赞评论数据」的 Markdown 素材库：一个博主一个文件夹，每条视频一份带 frontmatter 的 Markdown，外加 INDEX 索引。

> 全量导出线和监控线源自 content-toolkit（作者 chenlongdei12-dev），协议为 CC BY-NC-SA 4.0，全文见 `scripts/douyin/LICENSE`。仅限个人学习研究，不得用于商业用途（包括收费代采集、打包进付费课程）。

## 三条线怎么选

| | 全量导出线 | 监控线 | 监控工作簿 |
| --- | --- | --- | --- |
| 适合 | 一个博主的**全部**历史 | 几条链接出稿；盯几个博主的最新 N 条 | 日报用的「相似博主」表，按近 7 天增量更新 |
| 数据 | Get笔记订阅 + 社媒助手插件 | TikHub 或 Monid（`douyin.provider`） | TikHub 或 Monid |
| 去水印 / 转写 | 不需要（Get笔记自带逐字稿） | 大圣（或 Monid）/ 阿里云 | 大圣（或 Monid）/ 阿里云 |
| 费用 | 免费 | 计费 | 计费 |

全量只走 Get笔记：用户没订阅时，告诉他先在 Get笔记订阅该博主再导出，不用计费接口硬抓全量。监控线也能处理快手、小红书、B 站等平台的短视频链接（大圣去水印 → 阿里云转写），这些平台的点赞等数据视大圣返回而定。

## 第一步：自检

```bash
python3 scripts/douyin/doctor.py
```

照 ↳ 提示补齐。凭证都在 dei-capture 的 `config.json`：百炼 Key 在顶层 `dashscope.api_key`（sk- 开头）；TikHub 在顶层 `tikhub.token`；大圣在 `douyin.dasheng` 的 `uid`、`key`；Monid 在 `douyin.monid.token`（monid_live_ 开头）。用到哪条线才问对应的凭证。

## 命令（在 dei-capture 目录下）

```bash
# 监控线（数据来源看 douyin.provider；去水印顺序：Monid（仅数据来源是 Monid 时）→ 大圣 → 自定义接口）
python3 scripts/douyin/run.py monitor --links "https://v.douyin.com/xxxx/,https://v.douyin.com/yyyy/"
python3 scripts/douyin/run.py monitor --blogger-sec-uid MS4wLjAB...   # 加入监控列表并拉最新视频
python3 scripts/douyin/run.py monitor                                  # 跑监控列表里所有博主

# 全量导出线
python3 scripts/douyin/biji_export.py login                     # 扫码，一次；之后无头自动刷新
python3 scripts/douyin/run.py export-biji "博主名" --with-data   # 名字模糊匹配，导完自动合并数据
python3 scripts/douyin/run.py export-data "https://www.douyin.com/user/MS4..."  # 社媒助手自动导数据
python3 scripts/douyin/run.py export-merge 博主名               # 单独合并逐字稿 + 数据
```

每一步也能单独跑，全部幂等、可断点续跑：

- 监控：`monid_fetch.py` → `parse_video_url.py` → `asr_transcribe.py` → `merge_output.py`
- 导出：`biji_export.py`（topics / follows / export / status）→ `social_stats.py` 或 `shejiao_export.py` → `merge_export.py`

`sec_user_id` 是博主主页链接 `/user/` 后面那一串。用户只给抖音号或昵称时，请用户给主页链接或任意一条作品链接。

## 监控工作簿

一张 Excel 表盯一组对标博主：第一页「相似博主总表」列出博主，后面每个博主一页，记录他近 7 天的视频（客观数据 + 逐字稿），右边留给用户写自己的创作与复盘。日报的抖音部分读的就是它。

```bash
python3 scripts/douyin/workbook.py init        # 第一次：从模板生成 <output_root>/抖音/监控工作簿/抖音监控工作簿.xlsx
python3 scripts/douyin/workbook.py --input <工作簿.xlsx> [--days 7] [--only-sheets 页签1,页签2] [--replace-sheets 页签1]
```

- 用户只填总表：C 列博主名称、E 列主页链接（浏览器打开博主主页，复制地址栏，里面带 `/user/MS4wLjAB…`）；D 列抖音号可选，只有 TikHub 能用抖音号反查账号。总表里有、还没有分页的博主，运行时自动从隐藏的「_博主页模板」建分页。
- 模板在本 Skill 的 `templates/抖音监控工作簿模板.xlsx`，由 `scripts/douyin/make_template.py` 生成。
- 数据来源跟 `douyin.provider`：Monid 没有 BGM 和粉丝量（这两列留空，赞粉比也就空着）；TikHub 都有。去水印用大圣，没配置大圣时用 Monid。时间一律按北京时间写。

输出是输入文件旁 `outputs/douyin-weekly-workbook/<原名>_更新_<日期>.xlsx`，不覆盖原文件；同名 `.report.json` 是失败清单。账号覆盖表在 `<output_root>/抖音/监控工作簿/account_overrides.json`（或 `--overrides` 指定），优先级高于总表；转写任务记录在同目录 `asr_tasks.json`，重跑不重复转写。

固定规则：

- 只录入客观数据：标题、BGM、链接、发布时间、抓取时间、粉丝量、点赞、评论、收藏、转发、赞粉比、逐字稿、前 5 秒和结尾。不生成分类、内容逻辑、钩子类型等主观字段，除非用户另行要求。
- 分页名就是总表的博主名称；账号以主页链接里的 `sec_uid` 为准。改名、拼写错误用账号覆盖表修正（值可填 `sec_uid`、`share_url` 或 `unique_id`，后两种只有 TikHub 能用），不要凭相似度猜账号。
- 跑完核对分页里视频的作者是不是这个博主；覆盖表里的 `sec_uid` 优先级最高。发现表内旧视频作者与目标账号不一致时，用 `--only-sheets` 加 `--replace-sheets` 替换该页（只清 A:S 的对方视频区，T:AJ 的个人创作与复盘区保留），不能继续增量追加。
- 优先抓滚动近 7 天；某账号为 0 条时，取消时间限制补抓最近 7 条；近 7 天已有 1 条以上时不补足。
- 视频 ID 是唯一键。已有视频只刷新客观指标和抓取时间，人工字段和已有逐字稿不覆盖；新视频追加并延续模板样式与公式。同一视频出现在多个 Sheet 只转写一次；中断后恢复同一任务，不重复提交。
- 单账号或单视频失败不中断整批；缺失不能写成 0。401/403 凭证无效、402 余额不足：停止外部调用并报告。
- 工作簿第 2 行预期列：A 序号、C 标题、D BGM、E 视频链接、F 发布时间、G 抓取时间、H 视频文案、K 结尾、L 前 5 秒钩子、N 粉丝量、O 点赞、P 评论、Q 收藏、R 转发、S 赞粉比。依赖 `openpyxl`（`python3 -m pip install openpyxl`）。

## 核心机制

- **幂等状态库**：监控线所有步骤读写 `<监控>/videos.json`，阶段 collected → parsed → transcribed → merged；中断重跑不重复计费（task_id 都会保存）。导出线按文件名里的 post_id 去重、增量续传。
- **计费**：TikHub、大圣按次计费；Monid 每次调用 $0.0012，每条视频约 2 次（列表 + 解析）；阿里云按语音时长，约每小时几毛钱。Monid 花费自动记在 `<监控>/.cost_log.json`，doctor 会显示累计。粗算：100 条视频约 $0.25 加几块钱转写费。
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
├── 监控工作簿/      account_overrides.json、asr_tasks.json（更新后的工作簿在输入文件旁）
├── Get笔记导出/     <博主>_<id>/ 逐字稿；merged/<博主>/ 合并了数据的版本
└── 社媒数据/        <博主>_作品数据_YYYYMMDD.xlsx
```

## 监控工作簿：已验证的问题与解决办法

### TikHub

- Python 默认 User-Agent 曾触发 Cloudflare 1010。统一使用浏览器 User-Agent 和 `Accept-Encoding: identity`，避免大响应解压截断。
- `unique_id` 解析失败时，用作品分享链接调用 `fetch_one_video_by_share_url` 反查作者 `sec_uid`。
- 返回结构存在 `data.data` 和字段名变体；递归查找 `sec_uid`，作品列表兼容 `aweme_list`、`items`。
- 置顶旧视频会混入第一页，必须按 `create_time` 本地过滤。
- 400、429 和偶发上游失败按账号隔离并有限退避重试。

### 大圣与百炼

- 大圣用 POST 表单调用，优先取 `video`、`video_url`、`url`、`play_url`，最后才取 `video4k`。
- Paraformer-v2 必须设置 `X-DashScope-Async: enable`，批量先提交再轮询。
- 同一视频按视频 ID 去重提交，避免重复 Sheet 重复计费。
- 前5秒使用 `begin_time < 5000` 的句子；结尾取最后3个有效语音句。没有时间戳时用首60字、末80字降级。

### 工作簿

- 模板可能预留格式化空行，优先复用视频链接为空的预留行，而非一律从 `max_row + 1` 追加。
- 抓取时间可能显示为 Excel 日期序列，必须应用 `yyyy-mm-dd hh:mm:ss` 并视觉检查。
- Excel 不接受带 `tzinfo` 的 Python datetime。写入前先转换为目标时区，再执行 `.replace(tzinfo=None)`；时区语义由本地时间和显示格式保留。
- 已有视频只更新客观数据；人工字段必须保留。
- 使用 `sec_uid` 覆盖时若拿不到账号资料，优先从作品作者对象补取粉丝数；仍缺失则留空，禁止写成0。
- 历史表曾出现 `dontebeslient` 页混入“行者”文稿：原因是旧视频已经写入错误 Sheet，后续增量逻辑又刻意保留已有逐字稿。解决方案是用主页 `sec_uid` 锁定账号，并以 `--replace-sheets` 清空 A:S 后重建；不能靠追加修复污染数据。
- 24h、7d、30d指标不能用当前快照冒充历史快照，没有定时历史数据时保持空白。
