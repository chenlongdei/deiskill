# dei-daily-report · 日报

**每天一份报告看完四个渠道：新闻联播里的政策和商机、AI 圈的新动向、知乎上值得写的选题、你关注的抖音博主发了什么。每个渠道都回看近 7 天，告诉你单看一天看不出来的变化。**

它是 [deiskill](https://github.com/chenlongdei/deiskill) 的一部分，也可以单独装、单独用。

## 最快拿到第一个结果

政策模块不用注册任何账号，只要 Python 3.10+。装好后对你的 Agent 说：

> 给我今天的政策与商机日报

它会取前一天新闻联播的逐字稿，逐条拆开，查官方原文和前序文件，再给出商机判断。其他三个渠道用到时再配置。

## 安装

**和装其他 Skill 一样**（需要 Node.js）：

```bash
npx -y skills add chenlongdei/deiskill --skill dei-daily-report
```

这种装法不会拉取 AI 模块和知乎模块依赖的上游工具（Follow Builders、知乎官方 CLI），这两个模块会被跳过；要用它们，请用下面的一键安装。

**或者用一键安装**，它会顺便检查环境，重装时备份旧版本、保留你的配置：

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-daily-report
```

Windows PowerShell（需要先装好 git 和 Python 3.9+）：

```powershell
$env:DEISKILL_ONLY="dei-daily-report"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

不想敲命令：把这个页面的网址发给你的 Agent，说「帮我安装 `dei-daily-report`，按 README 操作」。

它会自动识别 Claude Code、Codex、WorkBuddy 等 Agent 的 skills 目录；装好后重启 Agent。以后想要整套能力，装 [deiskill 全套](https://github.com/chenlongdei/deiskill)即可，本机配置和数据都会保留。

## 它能做什么

| 你说 | 你会拿到 |
| --- | --- |
| 「给我今天的日报」 | 四个渠道的综合日报，每个渠道一节「近 7 天变化」 |
| 「只看 AI 的」「只看政策」 | 选中渠道的日报 |
| 「做成能发出去的图卡」 | 对外文字版、3:4 速览图卡和长图，可以直接发社群和朋友圈 |
| 「帮我设成每天早上 7 点自动跑」 | 系统定时配置 |

## 用的是什么方法

政策和 AI 两个模块的分析方法，来自一门资本思维课程，并用真实日报校准过：

- **完整拆新闻**：每条报道都拆开编号，分清预算、投资、销售额、目标和实绩。「签约不是到账，高增长不是高利润。」
- **政策分级**：S / A / B / C，看有没有原始来源、真金白银和可观察的执行证据，不是看新闻篇幅。
- **商机成熟度**：观察 → 验证 → 可进入 → 兑现。政策是 A 级，不等于你现在就能进场。
- **谁付钱**：从政策目标一路推到具体买方、谁拍板、谁付钱、哪个环节赚钱，每个箭头标明是已证实还是假设。
- **边际变化**：和此前 30 天的报道、官方前序文件逐条对比，只把真正新增的东西当新闻。
- **事实、观察、推断、待验证分开标**，没有强机会就写没有，不为每天有商机而凑数。

## 成品示例

对外文字版示例：[report.md](publish/example/report.md)

## 要准备什么、花多少钱

| 模块 | 需要准备 | 费用 |
| --- | --- | --- |
| 政策 | Python 3.10+ | 消耗 Agent 额度 |
| AI | Node.js | 免费 |
| 知乎 | 知乎开放平台凭证 | 免费，有调用额度 |
| 抖音 | 一份已更新的抖音监控工作簿（整套里由内容采集能力更新） | 取决于采集方式 |
| 图卡和长图 | playwright、Pillow | 免费 |

缺哪个模块的配置，就跳过哪个模块，其他照常出。

## 结果存在哪里

第一次用时，它会问你「dei 工作区」放在哪里，你确认后才创建。日报在工作区的 `03_日报/` 下，按年分文件夹。

## 许可

MIT，见仓库根目录的 LICENSE。AI 模块里的 `aihot/` 保留它自带的 MIT；Follow Builders 和知乎官方 CLI 安装时从上游拉取，不随本仓库分发。
