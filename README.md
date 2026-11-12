# deiskill

**一句话说出你想要的结果，剩下的步骤让 AI 去跑。** 找资料、扒字幕、建知识库、写学习计划、出日报，这些平时要切好几个工具、花一下午的事，现在在对话里说一句就能开始。

一套中文 AI Skills，能装在 Claude Code、Codex、WorkBuddy 等支持 Skills 的 Agent 上。采用 [MIT 许可](LICENSE)，少数目录例外，见[依赖、成本与许可](#依赖成本与许可)。

## 你可以这样用

### 「我想学会 Claude Code，给我一份从入门到精通的学习计划」

1. 用中英文关键词搜 YouTube，按播放量和频道去重，筛出 15—30 个精选教程，**先给你确认**；
2. 把这些视频导入 NotebookLM，建成一个知识库；
3. 用 7 个问题把它们整理成知识地图，按「道、法、术、器、用」分层；
4. 交给你一份分单元的学习计划（观看顺序、练习、验收标准），外加一本**不懂技术也能照着做**的实操手册。某一层资料不够时，它会自己回去补搜。

全程你只需要确认 3 次：精选清单、单元划分、手册任务。想在通勤路上听，还可以给每个单元生成一期中文音频。
→ 实际产出见[成品展示](#成品展示)。

### 「拿这几本书和这些视频，帮我把『私域运营』这个主题挖深」

先问清你的研究目的，列出问题树给你确认，再用 7 个问题交叉追问所有资料。最后交出一份研究综述：哪些是共识，哪里有分歧，各自的依据是什么，你可以怎么做。遇到说不清的概念，可以接着把它拆开讲清楚；研究的是你自己的生意，可以接着做商业诊断。

### 「给我今天的日报」

一份报告看完四个渠道：前一天新闻联播里的政策和商机、AI 圈的新动向、知乎热榜上值得写的选题、你关注的抖音博主发了什么。每个渠道都会回看近 7 天，告诉你**哪些变化单看一天是看不出来的**。还能做成可以直接发出去的图卡和长图。

### 「把这几条视频转成文字」「导出这个博主的全部文案和点赞数据」

抖音、快手、小红书、B 站的短视频链接，YouTube 视频，本地录音，都能转成逐字稿。也可以盯住几个博主的更新，或者把一个抖音博主的全部历史作品导成一张表，文案和点赞、评论数据一一对齐。要花钱的操作，批量超过 20 条时会先报条数和大概费用。

## 成品展示

**日报速览图卡**（3:4，一期 13 张，这里是其中 4 张）：

![日报速览图卡示例](docs/images/daily-report-cards.jpg)

对应的文字版：[report.md](skills/dei-daily-report/publish/example/report.md)

**学习路线**：下面是一次真实运行的产出，主题是「学会 Claude Code」，依据 29 个 YouTube 教程。

| 文件 | 内容 |
| --- | --- |
| [知识地图](skills/dei-notebook/examples/学习路线-Claude-Code/01_知识地图.md) | 按道、法、术、器、用分层；标出只有一个来源支持的说法，以及已经过时的做法 |
| [学习计划](skills/dei-notebook/examples/学习路线-Claude-Code/02_学习计划.md) | 5 个单元，每个单元有观看顺序、练习、验收标准和常见卡点；另附一条给非程序员的路线 |
| [实操手册](skills/dei-notebook/examples/学习路线-Claude-Code/实操手册.md) | 写给内容创作者、运营、老师：每个任务一段可以直接复制的大白话指令，再加上「怎么算成功」「翻车了怎么救」 |

学习计划节选：

> | 单元 | 主题 | 学完能做到 | 建议用时 |
> | --- | --- | --- | --- |
> | 1 | 上手：最小闭环 | 装好、做出第一个小工具、截图修 UI、中断和回滚 | 1—2 天 |
> | 2 | 核心操作 | 精简 CLAUDE.md、权限保护凭证、管理上下文、建立验证闭环 | 3 天 |
> | 3 | 工作流 | 规范地启动项目、用 Issue 驱动开发、并行开发 | 1 周 |
>
> **给非程序员的路线**：单元 1 用桌面端，单元 2 学会 CLAUDE.md、权限和上下文管理就够……

## 5 分钟尝鲜

只装依赖最少的 `dei-capture`。需要 Python 3.9+ 和 [yt-dlp](https://github.com/yt-dlp/yt-dlp)（`pip install yt-dlp`），不用注册任何账号：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei12-dev/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-capture
```

重启 Agent，然后对它说：

> 搜一下 YouTube 上关于 Claude Code 的入门教程

它会先问一次结果存在哪里，然后交给你一份 `清单.md`：

```text
## 推荐（66）

### 1. CLAUDE CODE FULL COURSE 4 HOURS: Build & Sell (2026)
- 频道：Nick Saraev
- 播放：2.9M · 时长：4:10:43
- 链接：https://www.youtube.com/watch?v=…
- 命中关键词：Claude Code build real project
```

接下来可以说「把第 3 个视频的字幕扒下来」。第一次扒字幕时，它可能会请你允许读取一个已登录 YouTube 的浏览器的 cookies。想把这些视频变成学习计划，再装上 `dei-notebook` 和 `dei`。

## 全部 Skill

| Skill | 你可以这样说 | 你会拿到 |
| --- | --- | --- |
| `dei` | 「找一批教程，帮我做学习计划和实操手册」「下一步该做什么」 | 它自己挑选并串联下面的 Skill，在关键节点停下来等你确认；完成后可以同步到飞书或 Notion |
| `dei-capture` | 「搜 YouTube 上关于 X 的视频」「扒这几个视频的字幕」「把这几条抖音转成文字」「盯住这个博主」「导出这个博主的全部文案和数据」「把这段录音转成文字」 | 视频清单、逐字稿、博主作品数据表、更新后的监控表 |
| `dei-notebook` | 「把这些资料建成知识库」「按这些视频给我做学习计划」「围绕这个主题深挖」 | 带出处的问答、学习计划和实操手册、研究综述、中文音频、思维导图 |
| `dei-daily-report` | 「给我今天的日报」「只看 AI 的」「做成能发出去的图卡」 | 四个渠道的综合日报（含近 7 天变化），以及对外发布用的文字版、图卡和长图 |

**一起安装的上游 Skill**（安装时从 [dbskill](https://github.com/dontbesilent2025/dbskill) 拉取，版权归 dontbesilent 所有）：

| Skill | 你可以这样说 |
| --- | --- |
| `dbs-diagnosis` | 「帮我看看这门生意哪里有问题」 |
| `dbs-learning` | 「我想系统学一下 X，一篇一篇来」 |
| `dbs-chatroom` | 「请几位专家聊聊这个话题」 |
| `dbs-deconstruct` | 「『私域』这个词到底指什么」 |

**模板**

- [选题策划表](templates/dei-选题表.xlsx)：开头、主体叙事、结尾、标题、选题理由，以及点赞、评论、收藏、转发。
- [抖音监控工作簿](skills/dei-capture/templates/抖音监控工作簿模板.xlsx)：只填博主名称和主页链接，每个博主的分页自动建；左边是对方近 7 天视频的数据和逐字稿，右边留给你写自己的创作与复盘。装好 `dei-capture` 后说「帮我建一个抖音监控表」即可。

**参考成品**：[学习路线案例](skills/dei-notebook/examples/学习路线-Claude-Code/)随 `dei-notebook` 一起安装，Agent 写学习计划和手册前会先看它。

## 依赖、成本与许可

安装前先看清楚代价。下表没列到的都免费。

| 用到什么 | 需要准备 | 费用 | 不准备会怎样 |
| --- | --- | --- | --- |
| YouTube 搜索、频道清单、字幕 | Python 3.9+、yt-dlp；扒字幕时通常要一个已登录 YouTube 的浏览器 | 免费 | — |
| YouTube 按时间筛选、风控兜底 | TikHub Token | 按次付费 | 可以跳过，只是不能按发布时间筛选 |
| 本地音视频转写 | whisper.cpp + ffmpeg | 免费 | 本地文件无法转写 |
| 抖音博主全部历史 | 在 Get笔记订阅该博主；社媒助手插件导出数据 | 免费 | 不能导出全部历史作品 |
| 盯博主、短视频链接出稿（抖音、快手、小红书、B 站） | TikHub 或 Monid、大圣去水印、阿里云百炼 | 都按量付费 | 可以改成自己在 Get笔记粘贴链接，手动拿逐字稿 |
| 知识库、学习计划、研究综述 | Google 账号、notebooklm-py | NotebookLM 免费 | `dei-notebook` 不可用 |
| 日报 · 政策 | 当前 Agent 的账户 | 消耗 Agent 额度 | — |
| 日报 · AI | Node.js | 免费 | — |
| 日报 · 知乎 | 知乎开放平台凭证 | 免费，有调用额度 | 跳过知乎模块 |
| 日报 · 抖音 | 抖音监控工作簿，由 `dei-capture` 更新 | 同上方「盯博主」 | 跳过抖音模块 |
| 日报 · 图卡和长图 | playwright、Pillow | 免费 | 只出文字版 |

**许可**

- 本仓库自有代码采用 [MIT](LICENSE)。
- ⚠️ `skills/dei-capture/scripts/douyin/` 源自 [content-toolkit](https://github.com/chenlongdei12-dev/content-toolkit)，采用 **CC BY-NC-SA 4.0，仅限非商业使用**，不能用于收费代采集或打包进付费课程。
- ⚠️ **dbs 系列不在本仓库里，安装时从 dbskill 拉取，只能安装自用，禁止再分发。** 不要把装好的 skills 目录打包转给别人。follow-builders、知乎官方 CLI 等上游内容同理，见 [external.json](external.json)。

## 安装

**macOS / Linux** 一键安装（仓库会放在 `~/.deiskill/repo`）：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei12-dev/deiskill/main/scripts/bootstrap.sh | bash
```

**Windows**：在 PowerShell 里运行（需要先装好 git 和 Python 3.9+，缺哪个脚本会告诉你用 winget 怎么装）：

```powershell
irm https://raw.githubusercontent.com/chenlongdei12-dev/deiskill/main/scripts/bootstrap.ps1 | iex
```

不想敲命令：把这个仓库的网址发给你的 Agent，说「帮我安装 deiskill，按 README 操作」。

也可以手动安装：

```bash
git clone https://github.com/chenlongdei12-dev/deiskill.git
cd deiskill
bash scripts/install.sh                 # 检测本机已有的 Agent；有多个时会问你装到哪些
bash scripts/install.sh dei-capture     # 只装指定的 Skill
bash scripts/install.sh --target ~/.claude/skills --target ~/.workbuddy/skills   # 指定目录
bash scripts/install.sh --list          # 查看全部 Skill
```

Windows 上把 `bash scripts/install.sh` 换成 `python scripts\install.py`，参数相同。

- **支持哪些 Agent**：安装器会自动识别 Claude Code（`~/.claude/skills`）、Codex（`~/.codex/skills`）、WorkBuddy（`~/.workbuddy/skills`）和 `~/.agents/skills`。其他支持 Skills 的 Agent，用 `--target <它的 skills 目录>` 指定；实在不行，把 `skills/` 下对应的文件夹整个复制进去也能用。
- **缺依赖怎么办**：不用提前装全。第一次用到某个功能时，Skill 会先自检，告诉你缺什么，并按你的系统（macOS / Windows / Linux）给出一条安装命令，你同意后再装。

- **第一次用某个 Skill 时**，它会问你结果存在哪里，给出 2—3 个建议，你确认后才创建文件夹，以后不再重复问。报告和数据放在你选的位置，不放进 Agent 的安装目录。
- **重装或升级时**，旧版本会备份到 `~/.deiskill/backups/<时间>/`，你的配置和运行数据会自动保留。
- 凭证只写进本机的 `config.json`，不进 Git。各 Skill 的 `config.example.json` 列出了全部配置项。

## 更新记录

- **2026-11-12**　支持 Windows：一键安装脚本、UTF-8 输出、各 Skill 的环境准备说明；新增抖音监控工作簿模板；学习路线案例随 `dei-notebook` 安装
- **2026-11-12**　`dei-capture` 新增抖音：链接出稿、盯博主、导出博主全部文案并合并点赞评论数据；音视频转写合并成一个入口
- **2026-11-12**　新增 `dei-capture`（YouTube）、`dei-notebook`，以及总入口 `dei`（学习路线、主题研究两套流程）
- **2026-11-11**　`dei-daily-report` 新增对外成品：文字版、速览图卡、长图；头条原文存档为 PDF
- **2026-11-11**　建立仓库，迁移 `dei-daily-report`；每个渠道至少回看近 7 天

## 参与维护

- 规范：[docs/skill-spec.md](docs/skill-spec.md)
- 自有 Skill 登记在 [catalog.json](catalog.json)，上游内容登记在 [external.json](external.json)
- 修改后运行 `python3 scripts/validate_repo.py`。它也会检查 README 有没有写到 catalog 和 external.json 里的每个 Skill
