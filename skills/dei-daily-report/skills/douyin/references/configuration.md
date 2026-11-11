# 配置与迁移

随 dei-daily-report 整体迁移，本模块位于 skills/douyin/。将 config.example.json 复制为本模块的 config.json 后在本机填写，或使用对应环境变量。发布包不携带 config.json；保持本机私有，权限设为 `600`。

依赖 Python 3.10+、`openpyxl`，并可访问 TikHub、大圣和阿里云百炼。安装：`python3 -m pip install openpyxl`。

`config.json` 包含 `tikhub_api_key`、`dasheng_uid`、`dasheng_api_key`、`dashscope_api_key` 和 `timezone`。同名大写环境变量可覆盖文件值。

`account_overrides.json` 的键为 Sheet 名；值可填写 `unique_id`、`sec_uid` 或 `share_url`。Sheet 与总表不同、账号改名、总表缺失或公开抖音号无法解析时必须添加覆盖。

示例：

```json
{
  "LEO剧场": {"unique_id": "Leooneno"},
  "某博主": {"share_url": "https://www.douyin.com/video/123456789"}
}
```

工作簿第2行预期列：A序号、C标题、D BGM、E视频链接、F发布时间、G抓取时间、H视频文案、K结尾、L前5秒钩子、N粉丝量、O点赞、P评论、Q收藏、R转发、S赞粉比。
