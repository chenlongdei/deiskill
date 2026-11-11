# 已验证的问题与解决方案

## TikHub

- Python 默认 User-Agent 曾触发 Cloudflare 1010。统一使用浏览器 User-Agent 和 `Accept-Encoding: identity`，避免大响应解压截断。
- `unique_id` 解析失败时，用作品分享链接调用 `fetch_one_video_by_share_url` 反查作者 `sec_uid`。
- 返回结构存在 `data.data` 和字段名变体；递归查找 `sec_uid`，作品列表兼容 `aweme_list`、`items`。
- 置顶旧视频会混入第一页，必须按 `create_time` 本地过滤。
- 400、429 和偶发上游失败按账号隔离并有限退避重试。

## 大圣与百炼

- 大圣用 POST 表单调用，优先取 `video`、`video_url`、`url`、`play_url`，最后才取 `video4k`。
- Paraformer-v2 必须设置 `X-DashScope-Async: enable`，批量先提交再轮询。
- 同一视频按视频 ID 去重提交，避免重复 Sheet 重复计费。
- 前5秒使用 `begin_time < 5000` 的句子；结尾取最后3个有效语音句。没有时间戳时用首60字、末80字降级。

## 工作簿

- 模板可能预留格式化空行，优先复用视频链接为空的预留行，而非一律从 `max_row + 1` 追加。
- 抓取时间可能显示为 Excel 日期序列，必须应用 `yyyy-mm-dd hh:mm:ss` 并视觉检查。
- Excel 不接受带 `tzinfo` 的 Python datetime。写入前先转换为目标时区，再执行 `.replace(tzinfo=None)`；时区语义由本地时间和显示格式保留。
- 已有视频只更新客观数据；人工字段必须保留。
- 使用 `sec_uid` 覆盖时若拿不到账号资料，优先从作品作者对象补取粉丝数；仍缺失则留空，禁止写成0。
- 历史表曾出现 `dontebeslient` 页混入“行者”文稿：原因是旧视频已经写入错误 Sheet，后续增量逻辑又刻意保留已有逐字稿。解决方案是用主页 `sec_uid` 锁定账号，并以 `--replace-sheets` 清空 A:S 后重建；不能靠追加修复污染数据。
- 24h、7d、30d指标不能用当前快照冒充历史快照，没有定时历史数据时保持空白。
