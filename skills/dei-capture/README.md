# dei-capture · 内容采集

**把各平台上的视频变成你电脑里能搜、能读、能分析的素材：清单告诉你哪些值得看，逐字稿告诉你它说了什么，数据告诉你它表现得怎么样。**

它是 [deiskill](https://github.com/chenlongdei/deiskill) 的一部分，也可以单独装、单独用。

## 最快拿到第一个结果

只需要 Python 3.9+ 和 [yt-dlp](https://github.com/yt-dlp/yt-dlp)（`pip install yt-dlp`），不用注册任何账号。装好后对你的 Agent 说：

> 搜一下 YouTube 上关于 Claude Code 的入门教程

它会用中英文关键词去搜，去重、按播放量排序，交给你一份推荐清单：

```text
## 推荐（66）

### 1. CLAUDE CODE FULL COURSE 4 HOURS: Build & Sell (2026)
- 频道：Nick Saraev
- 播放：2.9M · 时长：4:10:43
- 链接：https://www.youtube.com/watch?v=…
```

接着可以说「把第 3 个视频的字幕扒下来」。

## 安装

**和装其他 Skill 一样**（需要 Node.js）：

```bash
npx -y skills add chenlongdei/deiskill --skill dei-capture
```

**或者用一键安装**，它会顺便检查环境，重装时备份旧版本、保留你的配置：

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-capture
```

Windows PowerShell（需要先装好 git 和 Python 3.9+）：

```powershell
$env:DEISKILL_ONLY="dei-capture"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

不想敲命令：把这个页面的网址发给你的 Agent，说「帮我安装 `dei-capture`，按 README 操作」。

它会自动识别 Claude Code、Codex、WorkBuddy 等 Agent 的 skills 目录；装好后重启 Agent。以后想要整套能力，装 [deiskill 全套](https://github.com/chenlongdei/deiskill)即可，本机配置和数据都会保留。

## 它还能做什么

| 你说 | 你会拿到 |
| --- | --- |
| 「每 3 天帮我扒一次抖音上这几个关键词的热门视频」 | 每个词前 20 条的汇总表（视频指数、点赞、收藏、分享、推荐量、标签、「大家都在搜」、逐字稿），外加一张跨期总表：哪些视频反复上榜，一眼看出什么在持续火 |
| 「帮我建一个抖音监控表，盯住这几个博主」 | 一张工作簿：每个博主一个分页，左边是对方近 7 天视频的数据和逐字稿，右边留给你写自己的创作和复盘 |
| 「导出这个博主的全部文案和点赞数据」 | 一个抖音博主全部历史作品的逐字稿，文案和点赞、评论数据一一对齐 |
| 「把这几条抖音 / 快手 / 小红书 / B 站视频转成文字」 | 每条一份「逐字稿 + 数据」 |
| 「把这个 YouTube 频道的视频列出来」 | 频道视频清单，再跑一次只标出新增的 |
| 「把这段录音转成文字」 | 本地音视频的逐字稿 |

**关键词巡检**是它最省心的功能：第一次花几分钟做完自检、用抖音 App 扫码、试跑两条、登记定时，之后电脑按时自己跑，**不用开 Agent，不花 AI 额度**。它像真人一样一条条点开视频，按真人的节奏停留和翻页；没人说话的视频标「无口播」；常错的词自动改正；采过的视频不重复转写。一次实测：5 个词、98 条视频，84 分钟跑完，转写费约 1 元。

## 为什么用它

- **不编**：拿不到字幕就写明失败原因，不拿标题和简介拼一段「逐字稿」；缺的数据留空，不写成 0。
- **免费优先，花钱先报数**：能走免费渠道就不走计费接口；批量超过 20 条要花钱时，先告诉你条数和大概费用。
- **固定动作都是脚本**：换 Agent、换电脑结果都一样，定时任务跑起来也不花 AI 额度。

## 要准备什么、花多少钱

| 功能 | 需要准备 | 费用 |
| --- | --- | --- |
| YouTube 搜索、频道清单、字幕 | Python 3.9+、yt-dlp；扒字幕时通常要一个已登录 YouTube 的浏览器 | 免费 |
| YouTube 按时间筛选 | TikHub Token | 按次付费，可以不用 |
| 抖音关键词巡检 | Google Chrome、抖音账号（扫码一次）、阿里云百炼 Key | 搜索和数据免费；转写约每小时音频 0.3 元 |
| 抖音博主全部历史 | Get笔记订阅该博主；社媒助手插件导出数据 | 免费 |
| 盯博主、短视频链接出稿 | TikHub 或 Monid、大圣去水印、阿里云百炼 | 按量付费；也可以自己在 Get笔记粘贴链接，免费 |
| 本地音视频转写 | whisper.cpp + ffmpeg | 免费 |

不用提前装全：第一次用到某个功能时，它会先自检，按你的系统（macOS / Windows / Linux）告诉你缺什么、怎么装。

## 结果存在哪里

第一次用时，它会问你「dei 工作区」放在哪里，给出 2—3 个建议，你确认后才创建。采集结果在工作区的 `02_采集/` 下，按平台分文件夹。

## 许可

- MIT，见仓库根目录的 LICENSE。
- ⚠️ `scripts/douyin/` 源自 [content-toolkit](https://github.com/chenlongdei/content-toolkit)，采用 **CC BY-NC-SA 4.0，仅限非商业使用**，不能用于收费代采集或打包进付费课程。
