# dei-ppt · 讲课 PPT

**把你的学员手册变成一套站上台就能讲的 PPT。每页只放一个重点，讲稿写进演讲者备注，卡片打好组、入场动画写好；给一张海报，配色和背景就按海报来。**

它是 [deiskill](https://github.com/chenlongdei/deiskill) 的一部分，也可以单独装、单独用。

## 最快拿到第一个结果

装好后对你的 Agent 说：

> 这是我的课程手册和活动海报，按海报的风格给我出一套讲课 PPT：<手册文件> <海报图片>

你会拿到：

- PPTX：每页带讲稿，卡片打好组，写好入场动画。
- 签到轮播：自动循环播放。
- 备用 PDF。
- 逐页讲稿。
- 每页的预览图。
- 课前准备清单：要实测什么、要补哪些截图、哪些数字和引文要核对。

**PPT 的内容只从你的手册来**：指令和手册原文逐字一致，动手页右下角标出手册章节；海报只决定样子。

## 安装

```bash
npx -y skills add chenlongdei/deiskill --skill dei-ppt
```

或者用一键安装（会检查环境，重装时保留你的配置）：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-ppt
```

Windows PowerShell：

```powershell
$env:DEISKILL_ONLY="dei-ppt"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

装好后第一次用，让 Agent 跑一遍环境自检：`python3 scripts/build.py --doctor`（Windows 用 `python`）。缺什么，它会给出一条安装命令。

## 能做什么

- **按手册出 PPT**：先列出「章节 → 页面」对照表，再按你的说话顺序和口吻逐页写，讲稿写成能直接念的句子。
- **两种风格**：
  - 白底版：适合政企、培训。
  - 主题版：给一张海报，自动取色、生成背景、从海报上抠出 logo。
- **讲台上的取舍**：
  - 一页最多三层：标题、一个主体、一行补充。
  - 手册章节和限时放到右下角写成一行小字；进度条做小、半透明。
  - 讲者口头会讲的步骤不上屏。
- **分组和动画**：每张卡片和上面的字打成一组。人物页一条条上浮，工具卡讲一张出一张，转折用擦除，Keynote 和 PowerPoint 都能读。
- **学你的改稿**：你在 Keynote 里改完交回来，它会比对出改了哪些字、哪些数字、加了哪些动画，总结成规律记进偏好，下次照着做。

## 用的是什么方法

见 `references/theme-mode.md`（主题版规范与验收标准）、`references/narrative.md`（讲者口吻）、`references/preferences.md`（改稿学到的规律）。

## 准备什么、花多少钱

- **必备**：
  - 你的学员手册或方案。
  - Node.js 和 Python 3.9+。
  - Keynote（macOS）或 LibreOffice，用来渲染预览图。
  - 思源黑体。
- **主题版**：还要一张海报或主视觉；有 logo 原图和讲者照片更好。
- **费用**：不用任何账号，不花钱。白底版要用 AI 生成主视觉图时，才需要图像接口的 Key。

## 结果存在哪里

存在你的课程文件夹里：`_scripts/`（内容文件）和 `PPT/`（PPTX、预览图、讲稿、清单）。

## 许可

MIT。
