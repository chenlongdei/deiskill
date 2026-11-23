# dei-talking-head 真人口播剪辑

**把自己随手录的一条口播，剪成刷到就想看完的竖屏成片：删停顿、口误和重录，提速，大号粗字幕，讲到结构就切整屏图解，配音效和配乐、处理人声；剪完再让 Gemini 听一遍，查出的问题逐条核实后修改。**

## 最快拿到第一个结果

装好后对 Agent 说：

> 这是我录的口播原片，帮我剪成能发抖音的竖屏成片，先给我看删改清单。

它会先转写，列出要删的每一段（原片时间 + 理由）等你确认；剪完给你一份刀口核对，再做画面、出关键帧给你看，最后本地渲染。

## 安装

只装这一个：

```bash
npx -y skills add chenlongdei/deiskill --skill dei-talking-head
```

或者：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-talking-head
```

Windows PowerShell：

```powershell
$env:DEISKILL_ONLY="dei-talking-head"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

装在 Claude Code、Codex、WorkBuddy 等支持 Skills 的 Agent 上都可以。

## 能做什么

- 原片 → 逐字稿 + 删改清单（你确认）→ 剪辑工程 + 成片 MP4（1080×1920，-14 LUFS）+ 刀口核对
- 看完片说「这里卡了」「这个音效太冲」「这个对比看不懂」→ 只改那一处，出新版本，旧版保留
- 剪完让 Gemini 按 30 秒一段听审 → 每条回原片核实 → 改
- 想自己在剪映里拖：导出字幕.srt、透明图层.mov 和剪映多轨草稿

## 用的是什么方法

一条 3 分钟的知识口播剪了 9 版，用户的每条反馈都写进了规则：见 [references/method.md](references/method.md)。

- 每一步用当下最好用的工具，靠固定的交接件串起来，哪一格有更好的就只换那一格
- 删改先给清单、用户拍板；刀口落在静音里，句中小停顿不切，被删的词不留尾音
- 市场版画面：全屏人像 + 跳切交替推近 + 常驻标题 + 大粗字幕 + 讲结构时整屏图解（写法见 [references/scenes.md](references/scenes.md)）
- 图解画结构不复述口播；对比要同屏、具体、用同一组卡片接力
- 音效宁轻勿冲，配乐明亮大调，人声按频谱处理
- 剪完听审：Agent 听不到真实的声音，交给能听音频的模型抓卡顿和音效问题（[references/review.md](references/review.md)）

## 准备什么、花多少钱

- Python 3.9+（jieba、numpy、soundfile）、ffmpeg、whisper.cpp 和模型、Node.js 18+、Chrome（见 [references/setup.md](references/setup.md)）
- 全部本地运行不花钱；可选 ElevenLabs key（生成音效）、Antigravity CLI（Gemini 听审，用你自己的 Google 账号）
- 推荐免费商用字体：阿里巴巴普惠体、抖音美好体

## 结果存在哪里

这件事已有项目文件夹的放在它下面；没有的放 dei 工作区的输出位置 `口播剪辑/日期_主题/`。改版只改工程里的 `plan.json`（剪什么）和 `scenes.py`（画什么）。

## 许可

MIT，见仓库根目录。`templates/icons/` 是字节跳动 IconPark 图标（Apache-2.0，许可文件在同目录）。配乐、音效、字体按各自许可使用。
