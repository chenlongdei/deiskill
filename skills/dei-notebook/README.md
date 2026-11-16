# dei-notebook · 资料知识库

**把一堆教程、书和文档变成一个能提问的知识库，用 7 个问题榨出一份从入门到精通的学习计划和一本照着就能做的实操手册。**

它是 [deiskill](https://github.com/chenlongdei/deiskill) 的一部分，也可以单独装、单独用。底层用的是 Google NotebookLM，所以每个回答都基于你给的资料，不是 AI 凭空发挥。

## 最快拿到第一个结果

需要 Python 3.9+、一个 Google 账号。第一次用时它会自检，带你装好 notebooklm-py、在浏览器里登录一次 Google。然后对你的 Agent 说：

> 把这几个 YouTube 视频建成知识库，告诉我它们分别讲了什么：<贴几个视频链接>

YouTube 链接直接导入就行，不用先扒字幕。

## 安装

**和装其他 Skill 一样**（需要 Node.js）：

```bash
npx -y skills add chenlongdei/deiskill --skill dei-notebook
```

**或者用一键安装**，它会顺便检查环境，重装时备份旧版本、保留你的配置：

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-notebook
```

Windows PowerShell（需要先装好 git 和 Python 3.9+）：

```powershell
$env:DEISKILL_ONLY="dei-notebook"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

不想敲命令：把这个页面的网址发给你的 Agent，说「帮我安装 `dei-notebook`，按 README 操作」。

它会自动识别 Claude Code、Codex、WorkBuddy 等 Agent 的 skills 目录；装好后重启 Agent。以后想要整套能力，装 [deiskill 全套](https://github.com/chenlongdei/deiskill)即可，本机配置和数据都会保留。

## 它能做什么

| 你说 | 你会拿到 |
| --- | --- |
| 「按这些视频给我做一份学习计划」 | 知识地图、分单元的学习计划（观看顺序、练习、验收标准）、一本不懂技术也能照着做的实操手册 |
| 「拿这几本书和视频，帮我把『私域运营』挖深」 | 一份研究综述：哪些是共识、哪里有分歧、各自的依据和证据强度、你可以怎么做、资料没覆盖到的盲区 |
| 「对这批资料问几个问题」 | 每轮一份问答存档，出处写在回答里 |
| 「每个单元给我做一期中文音频」「做个思维导图」 | 音频播客、思维导图（附 Markdown 大纲）、闪卡、测验等 |

## 用的是什么方法

- **7 问封顶**：一个完整任务最多问 7 个问题（资料盘点、道 + 法、器 + 术、真实案例、学习计划两问、实操手册一问），问题少而深，不写一长串没人回答的问题清单。
- **道、法、术、器、用分层**：先讲为什么（道）、底层规律（法），再讲具体技巧（术）、工具（器）和真实用法（用），学习计划按这个顺序排单元。
- **发现缺口自己补**：资料盘点发现某一层明显不够时，会告诉你缺什么、建议补搜什么关键词。
- **实操手册写给不懂技术的人**：每个任务一段可以直接复制的大白话指令，再加「怎么算成功」「翻车了怎么救」；AI 自己能生成的配置不贴代码，只教你怎么跟它说。
- **研究要先问目的**：主题研究先问清你为什么要研究，问题树经你确认后才开始追问。

## 成品示例

一次真实运行，主题「学会 Claude Code」，依据 29 个 YouTube 教程：

- [知识地图](examples/学习路线-Claude-Code/01_知识地图.md)：按道法术器用分层，标出只有一个来源支持的说法和已经过时的做法
- [学习计划](examples/学习路线-Claude-Code/02_学习计划.md)：5 个单元，另附一条给非程序员的路线
- [实操手册](examples/学习路线-Claude-Code/实操手册.md)：写给内容创作者、运营、老师

## 要准备什么、花多少钱

| 需要准备 | 费用 |
| --- | --- |
| Python 3.9+、notebooklm-py 0.8.5+（含 playwright chromium）、Google 账号 | NotebookLM 免费 |

## 结果存在哪里

第一次用时，它会问你「dei 工作区」放在哪里，你确认后才创建。知识库的问答、学习路线和研究综述在工作区的 `04_知识库/<主题>/` 下。

## 许可

MIT，见仓库根目录的 LICENSE。
