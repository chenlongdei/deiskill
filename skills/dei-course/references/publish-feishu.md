# 发布到飞书

> 发布平台是飞书时加载。先读 `publish.md`（确认点、发布记录、校对）。

## 通道

- **飞书官方命令行 `lark-cli`**（npm 包 `@larksuite/cli`）。检查：`lark-cli --version`、`lark-cli auth status`。
- 没登录：请用户在终端运行 `lark-cli auth login`（设备码授权，要用户本人在浏览器或飞书里点确认）。
- 当前 Agent 已接好飞书连接器时也可以用连接器，规则相同。

## 第 0 步：读命令行自带的说明

`lark-cli` 的文档命令要求先读它内置的说明，参数以内置说明为准，不凭记忆写：

```bash
lark-cli skills read lark-doc
lark-cli skills read lark-doc references/lark-doc-create.md
lark-cli skills read lark-doc references/lark-doc-md.md      # 用 Markdown 写正文时
```

带 `high-risk-write` 标记的命令需要 `--yes`，只有用户确认后才加。每个写操作先用 `--dry-run` 看一遍请求。

## 第 1 步：新建页面

- 正文用 Markdown 写入：`lark-cli docs +create --doc-format markdown --content @<手册.md>`。
- 位置：`--parent-token <文件夹或知识库节点>`；用户没给位置时问，不默认放进「我的空间」以外的地方。
- 手册 Markdown 要先按 `publish.md` 第 5 节和 `lark-doc-md.md` 支持的写法转换：提示块、折叠块、表格、代码块逐一核对，不支持的退回成引用块。

## 第 2 步：附件

物料包 Win 版、Mac 版各插一次：

```bash
lark-cli docs +media-insert --doc <文档链接> --type file --file <…-Win版.zip>
lark-cli docs +media-insert --doc <文档链接> --type file --file <…-Mac版.zip>
```

默认插在文末；要放到顶部附件区时，用 `--selection-with-ellipsis` 定位到下载说明那一段（参数细节以 `--help` 为准）。

## 第 3 步：更新已有页面

- 先读 `发布记录.json` 拿到文档链接，再 `lark-cli docs +fetch` 看当前内容。
- 改几处：用 `docs +update`，按 `lark-doc` 说明里的定位方式逐处改。
- 大改版：和用户确认后整页重写，或新建一份并在发布记录里替换链接；飞书有历史版本（`docs +history-list`），改坏了可以回滚。

## 第 4 步：验证

`lark-cli docs +fetch` 读回顶部，核对附件、顺序、重复块；把文档链接写进 `发布记录.json`。

## 常见问题

| 症状 | 处理 |
| --- | --- |
| 权限不足、scope 缺失 | `lark-cli auth check` 看缺哪个权限，告诉用户需要开通什么，停下 |
| 文件名变成了链接 | 正文里的文件名包成行内代码后重新更新 |
| 附件超过 20MB | `media-insert` 会自动分片上传，等它完成再验证 |
