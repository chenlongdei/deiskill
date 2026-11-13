# deiskill · 目标、进度与管理约定

> 最后更新：2026-11-13。新开窗口先读这份文件，再继续任务。
> 这是公开仓库：本文件不写本机绝对路径、凭证和个人草稿（校验器会检查）。

这个文件夹是 deiskill 的唯一维护位置（GitHub：chenlongdei/deiskill）。新增、修改、删除 Skill 都在这里做，改完再安装到 Agent。

## 总目标

建一套覆盖日常「输入 → 处理 → 输出」的个人中文 Skill 体系，逐步替代旧仓库 chenlongdei/dei-skill。

设计参考 dontbesilent 的 dbskill：

- 每个 Skill 在 frontmatter 声明 `dei-handoff`（「接手 → 交出」，最后一行写「不交出：」）；
- 叶子 Skill 不点名其他 Skill，组合关系只由总入口 `dei` 掌握；
- 总入口从最终交付倒推，决定单个、串行、并行或循环组合；
- references 按需加载，不一次读完。

分层（见 `catalog.json` 的 `layers`）：

| 层 | 职责 | 现有 / 计划 |
| --- | --- | --- |
| router | 总入口 `dei` | 🔧 最小版：配方 A「YouTube 教程 → 学习路线」、配方 B「多渠道资料 → 主题研究」 |
| input | 采集、转写、检索、日报 | `dei-daily-report` ✅；`dei-capture` ✅（YouTube、抖音、统一转写） |
| process | 理解、提问、诊断、学习 | dbs-diagnosis / learning / chatroom / deconstruct ✅（上游）；`dei-notebook` ✅ |
| output | 把结论变成成品 | 计划；已有模板 `templates/dei-选题表.xlsx` |

## 必须遵守的原则（用户已明确）

1. **不写死任何 Agent**：Skill 要能装在 Claude Code、Codex、WorkBuddy 等任意支持 Skills 的 Agent 上。安装目录、定时工具、命令都用用户实际使用的或指定的；安装器检测到多个 Agent 时询问。
2. **不假设用户有任何文件夹**：首次运行询问 dei 工作区放在哪（所有 Skill 共用一个，记在 `~/.deiskill/config.json`），给 2—3 个建议，确认后再创建；输入文件同样先问。结构和命名见 `docs/skill-spec.md` §6a。
3. **报告和数据不放进 Agent 的 skills 安装目录**，放在用户确认的位置。
4. **日报每个渠道至少回补近 7 天**，报告必须有「近 N 天变化」；token 和预算允许时可到 30 天以上（`history_days`）。
5. **上游内容不提交进仓库**（dbskill 禁止再分发；follow-builders、知乎官方工具同理），登记在 `external.json`，安装时拉取。
6. 公开仓库只放模板，不放个人草稿（如选题表只推表头）。

## 迁移进度

| 步骤 | 内容 | 状态 |
| --- | --- | --- |
| 0 | 仓库骨架：规范、catalog/external、安装器（保留本机状态、备份、检测 Agent）、校验器 | ✅ |
| 1 | `dei-daily-report`：政策、AI、知乎、抖音四模块；首次配置；7 天回补；数据目录外置 | ✅ 已安装并完整跑过一次 |
| 1a | 日报对外成品：对外文字版、速览图卡、长文图片（`publish/`），头条原文存档为 PDF（`archive/`） | ✅ 2026-11-11 加入 |
| 1b | dbs-diagnosis / dbs-learning / dbs-chatroom / dbs-deconstruct | ✅ 登记为上游，安装时从 dbskill 拉取 |
| 2 | 旧 `yt-research` 并入 `dei-capture` 的 YouTube 模块；旧 `notebooklm-kb` 升级为 `dei-notebook`（导入任意文档资料并提问，不只服务视频） | ✅ 2026-11-11 已安装并端到端实测：搜索 → 逐字稿 → 导入 NotebookLM（本地文件 + YouTube 链接）→ 带引用提问 → 思维导图 |
| 3 | `dei-capture`：合并旧 `douyin-paraformer-transcriber` 与 chenlongdei/content-toolkit。子模块：抖音博主全量、抖音监控/链接转写、第三方渠道（小红书、YouTube、抖音；TikHub 与 Monid 按渠道选）。之后日报的抖音模块改为调用它 | ✅ 2026-11-12 content-toolkit 已并入（`scripts/douyin/`，保留 LICENSE 和署名），统一转写入口 `scripts/transcribe.py` + `scripts/asr.py`；链接出稿实测通过。旧 douyin-paraformer-transcriber 在本机已找不到，功能已被覆盖。日报抖音模块尚未改接 |
| 4 | 总入口 `dei`：按 handoff 从最终交付倒推组合 | 🔧 2026-11-11 先做最小版（用户要求），配方 A 实测进行中 |
| 5 | 输出层 Skill | 规划中 |
| 6 | dei 工作区：所有 Skill 共用一个数据根目录（01_我的清单 / 02_采集 / 03_日报 / 04_知识库 / 05_成品 / 99_系统），中文子目录、北京时间批次名、运行总账、外置盘检查、试跑隔离；`scripts/migrate_workspace.py` 迁移旧数据 | ✅ 2026-11-13 本机 1577 个文件迁入并实测（政策抓取、AI 采集、YouTube 试跑搜索、NotebookLM 自检、关键词巡检自检） |

旧仓库其余 Skill（topic-extraction、content-writing-system、course-poster-review-safe、bluebook-factory、daily-notes-sync、hunan-etax-invoice）是否迁移，用户还没决定。

## 当前状态

### dei-daily-report

| 模块 | 状态 | 备注 |
| --- | --- | --- |
| 政策 | ✅ | 新闻联播逐字稿，可回补 30 天；分析须读官方原文 |
| AI | ✅ | AIHOT + Follow Builders；AIHOT 接口最多回补 7 天，`collect.py --date` 输出 `aihot_selected_in_window` |
| 知乎 | ✅ | 官方 CLI 0.6.3；官方无历史热榜，近 7 天用 justjavac/zhihu-trending-top-search 热搜归档作参照 |
| 抖音 | ⛔ 本机未配置 | 2026-11-12 起只读工作簿写摘要，抓取改由 dei-capture `douyin/workbook.py` 负责；仍缺监控工作簿（`douyin_default_input`）；TikHub Token 已失效（401） |
| 对外成品 | ✅ | 渲染依赖 playwright；成品只交给用户，不自动发布 |

本机安装位置以 Agent 的 skills 目录为准，数据在 dei 工作区（`~/.deiskill/config.json` 的 `workspace_root`，不进 Git）。工作区根目录另有一份 `CLAUDE.md`，记录本机运行情况。

### dei-capture

用户已确定：数据 yt-dlp 优先、TikHub 补充；本次做搜索、频道清单、单视频逐字稿（评论暂不做）。

| 能力 | 状态 | 备注 |
| --- | --- | --- |
| 关键词搜索 | ✅ 实测 | yt-dlp 扁平结果没有发布日期；按时间筛选需要 TikHub |
| 频道清单 | ✅ 实测 | 增量合并，标出本次新增 |
| 逐字稿 | ✅ 实测 | 单视频请求要带浏览器 cookies（macOS 需给终端「完全磁盘访问权限」）；yt-dlp 须保持较新（旧版报 `The page needs to be reloaded`）；取信息时加 `--ignore-no-formats-error`，否则缺 JS 运行环境会报格式不可用。无字幕视频的本地 whisper 转写需配置模型，未实测 |

抖音模块（2026-11-12 并入 content-toolkit）：

| 能力 | 状态 | 备注 |
| --- | --- | --- |
| 链接出稿（Monid → 去水印 → Paraformer → 合并） | ✅ 实测 | 1 条约 25 秒；Monid 余额 2026-11-12 为 $0.90 |
| 盯博主（监控列表） | 未实测 | 与链接出稿共用后三步 |
| Get笔记全量导出 + 社媒助手数据合并 | ✅ 导出实测 | 2026-11-12 用户已登录；导出现在在工作区 `02_采集/抖音/博主/<博主>/逐字稿/`，谢胜子增量导出 13 篇、跳过 695 篇。社媒助手合并未测 |
| 统一转写 `transcribe.py` | ✅ 直链实测 | 本地文件走 whisper，模型未配置 |
| 监控工作簿 `workbook.py`（原日报抖音模块） | ✅ 2026-11-12 Monid 实测 | 支持 Monid / TikHub（`douyin.provider`，本机设为 monid，TikHub 无余额）；模板 `templates/抖音监控工作簿模板.xlsx`，`workbook.py init` 生成，用户只填总表（名称 + 主页链接），分页自动建；时间按北京时间。本机工作簿在工作区 `01_我的清单/抖音监控工作簿.xlsx`，已写入日报的 `douyin_default_input` |
| 大圣去水印 | ✅ 实测 | 返回直链和标题，没有作者和数据 |
| 关键词巡检 `keyword_watch.py`（抖音指数视频搜索） | ✅ 2026-11-13 五个词完整实测 98 条；doctor / login / schedule 命令化，新电脑模拟安装通过 | 用户定：5 个关键词、近 3 天、页面选「大于180秒」、女性成长和女性情感限垂类「情感」、每页看完再翻下一页、固定抓前 2 页全部 20 条（2026-11-13 改：平台时长筛选不生效，用户决定不再按时长筛，`min_duration` 设 0）、模拟真人停留、每 3 天跑一次；纯字幕配乐视频标「无口播」。边看边转写；页面点不动时直接调接口；跨期总表；`fix_words` 固定替换。定时由 `scripts/scheduler.py` 登记（macOS launchd / Windows 任务计划 / Linux cron），本机已登记 02:00 检查、满 3 天才跑；外接盘的权限坑见 douyin.md |

**渠道分工（用户 2026-11-12 定）**：① 抖音单博主全量 = Get笔记订阅导出 + 社媒助手数据（没订阅就让用户去订阅，不用计费接口硬抓）；② YouTube 走原渠道；③ 监控和各平台单条/多条 = TikHub 或 Monid 取数据 + 大圣去水印 + 阿里云转写；④ 其他平台零散单条、用户不想花钱 = 让用户自己在 Get笔记粘贴链接。TikHub 凭证失效时停用该路，链接出稿继续走大圣，盯博主改用 Monid。

并入时修了两处原工具的问题：链接入口没取抖音视频号就用了哈希；`merge_output.py --force` 跳过已合并条目。

用户明确：**YouTube → NotebookLM 直接导入链接即可**，NotebookLM 自己读字幕；逐字稿只在需要本地文字稿、导入失败或下游读不了链接时才做。

### dei-notebook

用户已确定：只用 NotebookLM（不做本地兜底）；资料来源先支持本地文件和 YouTube（网页、得到笔记导出暂不做）。

- 脚本 `scripts/nb.py`：doctor / import / ask / make / status；思维导图同时输出 Markdown 大纲
- notebooklm-py 最低 0.8.5：旧版在 NotebookLM 改域名后会把未登录误判成已登录（显示 Already logged in 但缺 SID）。本机已升到 0.8.6 并重新登录
- 回答可能跟着资料用繁体或外文；`notebooklm language set zh_Hans` 是账号级设置，需用户同意

### 用户的两条核心工作流（2026-11-11 明确）

- **A：YouTube 教程 → 学会一个软件**：搜索 → 直接导入 NotebookLM → 资料盘点、查缺口、补搜 → 知识地图 → 5 单元学习计划 → 实操手册
- **B：多渠道资料 → 主题研究**：导入书、视频、文档 → 概念地图 → 问题树（用户确认）→ 4 个分支各一问 → 研究综述
- 贯穿框架：**道法术器用**；实操手册和综述以 Markdown 形式存进知识库
- 方法写在 `dei-notebook/references/learning-path.md`、`topic-research.md`，串联写在 `dei`

- **文档同步给两个选项：飞书或 Notion**（用户 2026-11-12 要求）：目前写在 `dei` 的收尾步骤里，借用 Agent 已接好的连接器；以后做输出层 Skill 时再固化成脚本
- **7 问封顶**（用户 2026-11-12 要求）：盘点、道+法、器+术、用（案例）、计划×2、手册。不写没有答案的问题清单；加问要先告诉用户
- **问答存档只放问题和回答**（用户 2026-11-12 要求）：[n] 编号和引用列表对读者没用，脚本已去掉；出处要求 NotebookLM 写视频或文档名
- **实操手册是教人用的**（用户 2026-11-12 要求）：读者默认不懂技术；AI 能自己生成的东西（配置、技能、Hook、权限）只教「怎么跟它说」，不贴代码；要有「看看别人怎么玩」案例。写法参考用户自己的 handbook-writing 仓库（三段式指令、结果先行、比喻、不编数）

实测经验：
- `notebooklm ask` 默认接着服务器上的上一个对话问，接续时常不带引用。脚本对本 Skill 新建的笔记本（notebook.json 里 `owned`）默认 `--new` 开新对话；用户原有的笔记本需要 `--fresh` 并先问用户
- 来源 25 个以上又要求长回答时，会报 `RPC response exceeded 268435456 bytes`。要收窄范围，字数要求它常常不遵守
- NotebookLM 给的配置写法可能是错的（如 Claude Code 的 `read:.env*`、`post_tool_use`），Agent 综合时必须核对
- 直接导入的 YouTube 来源带时间轴，NotebookLM 给的时间点经抽查基本准确
- 音频生成用 `--language zh_Hans` 按次指定语言，不用改账号设置

### 待办与已知问题

- [x] 配方 A 实测 ①NotebookLM 本身（20 个来源，做到学习计划）②Claude Code（29 个来源，端到端：知识地图、学习计划、实操手册，在工作区 `04_知识库/Claude-Code-学习路线-2026-11-11/学习路线/`）
- [ ] 配方 B（主题研究）尚未实测
- [ ] 本轮所有改动尚未 commit

- [ ] TikHub 字幕、频道接口的返回结构未实测（没有 Token），脚本按 inputSchema 自动填参并兼容解析
- [ ] 旧 Codex 里的 `notebooklm-kb` 与 `dei-notebook` 重复，清理前需用户确认

- [ ] 抖音监控工作簿待用户提供
- [ ] 定时还没创建（用户没要求）。本机时区是 UTC−6，「北京时间 05:00」要按 `skills/dei-daily-report/references/scheduling.md` 换算；policy 的 `install.sh --launchd` 要求本机为北京时间，不能直接用
- [ ] 知乎 CLI 0.6.3 的额度列表不再单列「问题回答」，计量方式待官方说明
- [ ] Codex 的 skills 目录里还有以前的旧 Skill（ai-sources-brief、follow-builders、zhihu-hot-expression、douyin-weekly-workbook、news-broadcast-analysis 等），和 deiskill 重复，清理前需用户确认

## 跨平台（2026-11-12）

目标是学员在任何电脑、任何 Agent 上装好就能用。规则见 [docs/skill-spec.md](docs/skill-spec.md)「跨平台」。已做：Windows 一键安装 `scripts/bootstrap.ps1`；全部入口脚本强制 UTF-8；外部命令按 UTF-8 解码；北京时间用固定 +8；社媒助手 Chrome 在三个系统都能拉起；`dei-capture/references/setup.md` 给出三个系统的安装命令；学习路线案例移到 `dei-notebook/examples/`，抖音监控工作簿模板在 `dei-capture/templates/`，都随 Skill 安装。未在真实 Windows 机器上实测。

## 下一步从这里开始

第 3 步收尾：用户更新 TikHub Token、提供监控工作簿后实测 `workbook.py` 和日报抖音模块；Get笔记导出线实测（需用户扫码登录）。之后是第 5 步输出层。日报抖音模块已改为只读工作簿（不点名采集 Skill，按 handoff 找「接手监控工作簿」的能力），由 `dei` 串联。

## 常用操作

```bash
python3 scripts/validate_repo.py        # 每次修改后必跑
bash scripts/install.sh --list          # 查看全部 Skill
bash scripts/install.sh                 # 检测本机 Agent 并安装（覆盖安装会保留本机配置与凭证）
bash scripts/install.sh <skill-name>    # 只装一个
bash scripts/install.sh --target <目录>  # 指定装到哪个 Agent 的 skills 目录
```

## 管理规则

- 写或改 Skill 前先读 [docs/skill-spec.md](docs/skill-spec.md)：命名（自有 `dei-` 前缀，dbs 保持原名）、`dei-handoff`、正文骨架、叶子不点名、dei 工作区的结构与命名（§6a）。改结构时同步 `scripts/migrate_workspace.py`。
- 自有 Skill 放 `skills/<name>/` 并登记 `catalog.json`；上游内容登记 `external.json`，不把文件提交进来。
- 需要本机路径的写进 Skill 的 `config.json`（不进 Git），仓库里只放 `config.example.json`。
- commit 前跑校验；推到公开仓库前确认没有本机路径、凭证和个人草稿。
- 进度变化后更新本文件的「迁移进度」「当前状态」「下一步」。
- **README 是给人看的落地页**（2026-11-12 按用户要求重写）：开头是场景故事（用户说一句话 → 拿到什么），然后是成品展示、5 分钟尝鲜、Skill 表（「你可以这样说 / 你会拿到」）、依赖与成本总表、许可、安装、更新记录。不写分层架构，不放「规划中」的半成品；新增或改动 Skill 时同步 Skill 表、成本表和更新记录。校验器会检查 README 写到了每个可安装的 Skill，且相对链接有效。
- 成品示例放 `examples/`（只放基于公开资料、不含个人信息的真实产出）和 `docs/images/`；日报图卡用 `publish/render.py` 渲染 `publish/example/data.json` 得到。
- 许可：仓库根目录 MIT；`skills/dei-capture/scripts/douyin/` 例外（CC BY-NC-SA 4.0），`aihot/` 保留自带的 MIT。新增第三方代码时在根目录 LICENSE 的 Exceptions 里登记。
