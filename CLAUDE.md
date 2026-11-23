# deiskill · 目标、进度与管理约定

> 最后更新：2026-11-17。新开窗口先读这份文件，再继续任务。
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
| router | 总入口 `dei` | 🔧 2026-11-14 升级为路由：全部请求先到它，按意图交给子 Skill（先轻后重）；配方 A 学习路线、B 主题研究、C 做课、D 朋友圈发售、E 找选题 |
| input | 采集、转写、检索、日报 | `dei-daily-report` ✅；`dei-capture` ✅（YouTube、抖音、统一转写） |
| process | 理解、提问、诊断、学习 | dbs-diagnosis / learning / chatroom / deconstruct ✅（上游）；`dei-notebook` ✅ |
| output | 把结论变成成品 | `dei-course` 🔧（课程手册 + 发布）；`dei-moments` 🔧（朋友圈风格、诊断、浪潮式发售）；`dei-profile` 🔧（个人介绍与案例库）；`dei-ppt` 🔧（讲课 PPT）；`dei-shop-video` 🔧（门店引流短视频，2026-11-23 从一次医疗门店 9.9 引流视频实做封装）；已有模板 `templates/dei-选题表.xlsx` |

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
| 5 | 输出层 Skill | 🔧 2026-11-13 第一个：`dei-course`（由用户的 course-handbook-creator 并入），发布线按用户设定的平台分飞书 / Notion / 钉钉 |
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

- **发布平台是共用设置**（用户 2026-11-13 要求，取代 11-12 的「飞书或 Notion 每次问」）：安装 deiskill 时先问用户常用哪个在线分享工具，记在 `~/.deiskill/config.json` 的 `publish_platform`（feishu / notion / dingtalk / local）；是飞书就接 `lark-cli`，Notion 接 `ntn` 或连接器，钉钉接 `dws`。读写用 `dei_workspace.py publish [set]`，安装器 `--publish`。规则见 `docs/skill-spec.md` §6b
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

### dei-course（2026-11-13 加入）

- 来源：用户自己的 course-handbook-creator（创作线八步 + 13 章模板 + Win/Mac 双 zip 打包器，原样保留）；发布线从「只推 Notion」改为按平台分 `publish.md`（通用）+ `publish-feishu|notion|dingtalk.md`
- 案例：`examples/AI夜校四节课/`（用户 2026-11-13 要求放入，四节主手册 + 讲师卡 + Win/Mac 物料包 + Notion 发布记录，约 1MB；课程方案原文含商业打法，没放）
- 课程文件夹默认 `05_成品/课程/<课程名>/`，用户指定了就用指定的；每门课一份 `发布记录.json`（原 Skill 里写死的 Notion page_id 档案已移到用户自己的课程文件夹，不进仓库）
- 实测状态：打包脚本未在本仓库重新跑；飞书发布线未实测（本机 lark-cli 1.0.82 已装）；Notion 线：本机 2026-11-13 装好 `ntn` 0.23.30 并登录，读课程页实测通过，新建/附件未实测；钉钉线未实测（本机没有 dws）

### dei-moments（2026-11-13 加入）

- 来源：和用户一起为一次真实课程发售做的诊断、改写、排期，以及一份 10 张运营表融合成的朋友圈方法论（七模块）；用户反馈过的写法规则写进 `references/copy-rules.md`（干货要有分量、开头两行、主角是自己、不被原文框住、产品用「以前 → 之后」讲）
- 用户的私人素材（风格提示词、素材库、每期发售方案和数据）只放工作区 `05_成品/朋友圈/`，不进仓库
- 方法论里的模板框架是对通用运营方法的重述，没有照搬原表格；浪潮式发售概念出自杰夫·沃克《浪潮式发售》
- 实测状态：方法和文案在一次真实发售里用过；Skill 本身的流程还没有端到端跑过
- 2026-11-17 加入私域标签（`references/tags.md`，用户要求）：五个维度（身·单选 / 源· / 买· / 阶· / 禁·），因为朋友圈可见范围只取并集，身份必须单选；铁律 8「每条都标给谁看」；发售方案排期加可见范围列、A/B/C 对到标签、复盘按来源统计并更新标签。用户自己的标签体系在工作区 `<moments>/标签体系.md`（不进仓库），方法文件不写任何人的渠道和价格

### dei-profile（2026-11-14 加入）

- 来源：和用户一起做的一次个人定位梳理（去粗取精、去伪存真 → 三层证据 → 按读者分版本 → 客户视角三轮优化 → 课程命名 → 政企社区版 → 四类对象 × 1/3/10 分钟话术 → PPT 人物页 → PDF 排版 → Notion 同步）。用户的定位：介绍和案例本质上是个人的 RAG / 知识库，讲课、见人时按主题筛案例
- 介绍库位置：Skill 自己的 `config.json` 的 `library_root`（用户已有文件夹时直接用，不搬动）；没有时默认工作区 `05_成品/个人介绍/`。用户的介绍、案例卡片、PDF 都不进仓库
- 脚本 `scripts/profile_lib.py`：where / init / cases（按关键词、读者、谁做的给卡片打分）/ index（重建案例索引）/ pdf（白底墨黑荧光绿版式，品牌读介绍库 `profile.json`，附录不进 PDF，自动找 Chrome / Chromium / Edge）
- `dei` 路由表已加一行，配方 C、D 补了取案例的衔接（2026-11-14，随本轮其他 `dei` 改动一起未安装）
- 实测状态：本机用作者的介绍库跑过 where / cases / index / pdf；Windows 未测；新建库（init）流程未端到端跑过

### dei-ppt（2026-11-16 加入）

- 来源：两次真实交付——一场政务单位专场（白底版，Python 引擎）和一场创业者沙龙（主题版，`deck_engine.js`）。沙龙那版生成第 2 版后，讲者在 Keynote 里只改了字、数字、照片和动画，版式没动，定为主题版标杆
- 铁律：内容只从学员手册来（指令逐字照抄、动手页标手册章节，`build.py --handbook` 自动核对）；主题图只管样子；一页一个重点
- `scripts/build.py`：生成 → 自查 → 预览（Keynote 优先，含隐藏页）→ 逐页讲稿；`--doctor` 自检依赖。`poster_theme.py` 从海报取色、生成背景、抠 logo；`keynote_diff.py` 比对讲者改稿
- 示例 `examples/` 含讲者个人信息和报价，本机私有（.gitignore），不进仓库；公开的是 `templates/theme_deck_template.js`
- 实测状态：两场真实交付跑通；Windows 未测（LibreOffice 渲染分支在 macOS 上测过）

### dei-shop-video（2026-11-23 加入）

- 来源：一条健康馆 9.9 新店引流视频，照抖音本地生活爆款复刻，五版迭代。用户反馈全部写进 `references/method.md` 和铁律：中文母语音色 + eleven_v4（multilingual_v2 有外国腔被否）、音效是核心（每个动作一个、名字说不清的不用）、开头 5 秒首帧画面就在动、价格和服务大字跟着口播出（不在第 0 帧摆出来）、有大花字就不出重复字幕、必须有 BGM、成片约 -11 LUFS（-14.7 被嫌小）、别人的车牌和路人脸打码（`mask.py`）、字体照对标用粗宋体 + 圆黑数字（思源宋体 Heavy + 抖音美好体）、Pixabay 有 Cloudflare 验证不绕过
- 引擎：HyperFrames，全部走 `npx --yes hyperframes@0.9.84`，不依赖任何 Agent 插件；一条视频 = 一份 `project.json`（口播、字幕、镜头、图层、音效、BGM、调色），时间点按「哪个字被说出」定位（ElevenLabs with-timestamps 逐字时间）
- 脚本：doctor / mask（按关键帧给车牌、人脸打马赛克）/ new（复制素材、缩略图拼板、project.json 草稿）/ tts（搜音色、试音、生成 + scribe 语音核对，列出不同处）/ sfx（ElevenLabs 音效生成，提示词在 templates/sfx_prompts.json）/ bgm（测 BPM 对强拍）/ build / finalize（检查、关键帧、渲染、压缩 + 响度、整片核对）
- 实测：2026-11-23 本机从零跑通全流程（新工程 → 配音核对 → 14 个音效 → BGM → 渲染 -11.3 LUFS → 整片核对 97%，差异只有店名同音字）；装到 Claude Code、Codex、WorkBuddy、通用 Agents 四个目录。Windows 未测
- 已知：安装器在 Skill 仓库目录里有 config.json 时，会在 Codex 目录里多嵌一层；仓库里不要放 config.json（校验器也会拦）

## 单独安装与总入口（2026-11-14 用户要求）

- 用户判断：大多数人装整套，只跟 `dei` 说话，所以 `dei` 要做真正的路由——任何请求先到它，交给对的子 Skill，读子 Skill 的 SKILL.md 后按它的规则执行；先走不用账号、不花钱的路。
- 同时，一节课可能只讲一个子 Skill：给学员一个子 Skill 的仓库或链接，只装它、只用它就能拿到结果。规则见 `docs/skill-spec.md` §8。
- 用户 2026-11-14 定：**不建独立仓库**，像 dbskill 一样给文件夹链接就能装。`npx skills add chenlongdei/deiskill --list` 实测识别 6 个 Skill，嵌套模块没被误认；`--skill <name>` 单装未实测。
- 已做：每个子 Skill 有自己的 README（最快结果、三种装法、方法、费用）；catalog 加 `first_prompt` / `quick_needs` / `publishes`；安装器装完打印第一句话，只装不发布的 Skill 时不问文档平台；Windows 用 `DEISKILL_ONLY` 也能只装一个。
- 未做：`dei` 新路由和配方 C/D/E 还没在真实对话里跑过。

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

- **只在仓库里改 Skill，不直接改安装目录。** 2026-11-16 复盘发现：dei-daily-report 的配色、模块、写法调整（11-13—11-15）只改在了本机安装版里，三天没回到仓库；dei 的路由升级反过来只在仓库里、没装到本机。改完一律：仓库改 → `validate_repo.py` → 提交推送 → 安装到 Agent。收尾时用 `diff -rq skills/<名> <安装目录>/<名>` 对一遍。

- 写或改 Skill 前先读 [docs/skill-spec.md](docs/skill-spec.md)：命名（自有 `dei-` 前缀，dbs 保持原名）、`dei-handoff`、正文骨架、叶子不点名、dei 工作区的结构与命名（§6a）。改结构时同步 `scripts/migrate_workspace.py`。
- 自有 Skill 放 `skills/<name>/` 并登记 `catalog.json`；上游内容登记 `external.json`，不把文件提交进来。
- 需要本机路径的写进 Skill 的 `config.json`（不进 Git），仓库里只放 `config.example.json`。
- commit 前跑校验；推到公开仓库前确认没有本机路径、凭证和个人草稿。
- 进度变化后更新本文件的「迁移进度」「当前状态」「下一步」。
- **README 是给人看的落地页**（2026-11-14 按用户要求改为价值先行）：一句话定位 + 「找机会 → 学透 → 做产品 → 卖出去」循环图 → 为什么不直接问 AI（方法与来源、不编、越用越积累、说结果就行）→ 一条完整的链 → 按四环分组的场景 → 成品展示 → 两种装法（全套 / 只装一个）→ Skill 表 → 依赖成本许可 → 安装细节 → 工作区 → 更新记录。循环图讲的是用户的生意怎么走，不是技术分层；不放「规划中」的半成品。新增或改动 Skill 时同步：所属环节的场景、「只装一个」表、Skill 表、成本表、更新记录，以及该 Skill 自己的 README。校验器会检查 README 写到每个 Skill、子 Skill 有自己的说明页，且相对链接有效。
- 成品示例放 `examples/`（只放基于公开资料、不含个人信息的真实产出）和 `docs/images/`；日报图卡用 `publish/render.py` 渲染 `publish/example/data.json` 得到。
- 许可：仓库根目录 MIT；`skills/dei-capture/scripts/douyin/` 例外（CC BY-NC-SA 4.0），`aihot/` 保留自带的 MIT。新增第三方代码时在根目录 LICENSE 的 Exceptions 里登记。
