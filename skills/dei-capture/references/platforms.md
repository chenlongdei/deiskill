# 各类内容怎么采集

用户要采集的内容不在已建模块里时，先查这张表，告诉用户可行的做法和要人工的环节。不支持的就如实说，不硬凑。

| 内容 | 做法 | 本 Skill 能做到哪 |
| --- | --- | --- |
| YouTube 视频、频道、搜索 | yt-dlp 为主，TikHub 补充 | ✅ `youtube.py`，见 youtube.md |
| 抖音视频、博主 | Monid + 阿里云转写；或 Get笔记导出 + 社媒助手数据 | ✅ `douyin/run.py`，见 douyin.md |
| 本地音视频文件（下载的、自己录的） | 本地 whisper；或阿里云（需公网直链） | ✅ `transcribe.py` |
| B 站、小宇宙、小红书视频 | Get笔记粘贴链接得逐字稿（手动）；有直链时可用 `transcribe.py` | 部分：给出直链才能自动转写 |
| 公众号文章、网页 | 浏览器剪藏插件存成 Markdown | 不自动采集，告诉用户做法 |
| 图片（小红书图文等） | 下载或截图后交给多模态模型提取文字 | 不自动采集 |
| 作品数据（点赞、评论数） | 社媒助手插件批量导出 Excel → `douyin/social_stats.py` 解析 | ✅ 抖音 |
| 评论区 | 社媒助手自带「批量评论导出」；单条深抓可用第三方工具 [douyin-comments](https://github.com/Pluviobyte/douyin-comments)（需浏览器已登录抖音） | 不自动采集 |
| 微信聊天记录、朋友圈 | 手动多选合并转发，或截图后多模态提取 | 不采集 |
| 直播回放 | 先拿到录像文件，再用 `transcribe.py` | 拿到文件后 ✅ |
| 持续盯账号更新 | 抖音用监控流水线（Monid）；YouTube 用 `channel` 增量合并 | ✅ |
