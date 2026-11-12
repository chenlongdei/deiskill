# notebooklm-py CLI

NotebookLM 没有公开 API；notebooklm-py（github.com/teng-lin/notebooklm-py）是逆向工程的方案，Google 改版后可能需要升级。本文按 0.8.6 编写（最低 0.8.5）。在 SKILL.md Step 0 自检失败，或要用脚本没包装的命令时读。

## 安装

用户用什么管理 Python 工具就用什么，不写死路径。常见方式：

```bash
uv tool install "notebooklm-py[browser]"      # 或：pipx install / pip install --user
playwright install chromium                    # 浏览器登录需要；uv 安装的用 uv tool run --from notebooklm-py playwright install chromium
notebooklm --version
```

命令不在 PATH 里时，把完整路径写进 `config.json` 的 `notebooklm_cmd`。

还没有 uv 时：macOS / Linux 用 `curl -LsSf https://astral.sh/uv/install.sh | sh`；Windows（PowerShell）用 `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`，装完重开终端。Windows 上 notebooklm 的命令是 `notebooklm.exe`，`uv tool install` 后通常在 `%USERPROFILE%\.local\bin`。

## 登录

登录要用户本人在浏览器里完成，Agent 只负责启动命令和说明步骤：

```bash
notebooklm login --browser-timeout 600
```

1. 弹出的浏览器里登录 Google 账号；
2. **登录后不要关窗口**，等终端提示保存成功（写入 `~/.notebooklm/profiles/<profile>/storage_state.json`）；
3. `notebooklm list` 能列出笔记本即正常。

已在本机浏览器登录 Google 时，也可以直接读浏览器 cookie：`notebooklm login --browser-cookies chrome`（可加 `--account <邮箱>` 选账号）。

| 现象 | 处理 |
| --- | --- |
| `Auth: not authenticated`，但明明登录过 | 多半是窗口被提前关掉，凭证没写入。再跑一次 `notebooklm login`（不加 `--fresh`），持久化的浏览器资料会立刻检测到已登录并保存 |
| `CSRF token not found in HTML` | 会话 cookie 过期。先 `notebooklm auth refresh --verify`；不行就重新 `notebooklm login` |
| login 显示 `Already logged in.`，但紧接着警告 `Missing required cookies: SID, __Secure-1PSIDTS`，之后命令仍失败 | 版本太旧（< 0.8.5）。NotebookLM 改域名后对未登录用户显示介绍页、不再跳转登录页，旧版把它误判成已登录。先升级 notebooklm-py（用户用什么装就用什么升级，如 `uv tool upgrade notebooklm-py`），再装一次 playwright chromium，然后 `notebooklm login --fresh` |
| 长时间没用后失效 | `notebooklm auth refresh --verify` |
| 多个 Google 账号 | `notebooklm profile create <名字>` 后用 `-p <名字>` 登录；在 config 写 `profile` |
| 其他 | `notebooklm doctor`（`--fix` 尝试自动修复） |

## 命令速查

脚本没包装的操作直接用 CLI。大多数命令支持 `-n <笔记本ID>`（可用 ID 前缀）和 `--json`。

| 动作 | 命令 |
| --- | --- |
| 列出 / 新建 / 改名 / 删除笔记本 | `list`、`create "<名>"`、`rename`、`delete`（删除前必须问用户） |
| 笔记本摘要 / 元数据 | `summary`、`metadata --json` |
| 添加来源 | `source add <文件或链接> --type file|youtube|url|text [--title]` |
| 来源列表 / 等待就绪 / 删除 | `source list --json`、`source wait <来源ID>`、`source delete <来源ID> -y` |
| 来源全文 / 导读 | `source fulltext <来源ID>`、`source guide <来源ID>` |
| 提问 | `ask "<问题>" [--json] [-c <对话ID>] [-s <来源ID>...]`；`-s` 只问指定来源 |
| 建议问题 | `suggest-prompts` |
| 对话历史 | `history` |
| 回答语言 / 风格 | `language set zh_Hans`；`configure --help` |
| 生成 / 下载 | `generate <类型> [--wait]`（mind-map 是同步生成，没有 `--wait`）；`download <类型> [输出路径] [--latest]`，导图下载为 JSON |

## 限制与坑

- **来源上限**：按账号档位 50/100/300/600 个/笔记本，config 的 `source_limit` 默认 50。
- **本地文件类型**：pdf、doc、docx、md、markdown、txt、csv、tsv、epub、pptx、odt、rtf。音频、视频、图片、旧版 .ppt 不在清单内。
- **符号链接**默认拒绝上传（防止误传链接指向的文件）。
- **YouTube 来源**直接用链接导入，NotebookLM 会自己识别标题并读取字幕（2026-11-11 实测）；它依赖视频字幕，`rpc_code=9` 之类的错误多是无字幕或地区限制，重试一次仍失败就换视频，残留的 error 来源用 `source delete` 清掉。
- **ask 的 `--new`** 会删除当前对话历史，脚本不用它；需要新话题时直接不加 `--follow-up`。
- 单轮深度提问 1—5 分钟；音频、视频生成 5—20 分钟。
- **`RPC response exceeded 268435456 bytes`**：回答以流式返回，每个片段都带完整的引用数据，来源多（约 25 个以上）又要求上万字回答时会超出 256 MB 缓冲。把问题拆小（如道、法、器各问一题），或用 `-s` 只问相关来源。
