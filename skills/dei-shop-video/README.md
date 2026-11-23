# dei-shop-video 门店引流短视频

**把门店随手拍的几段素材和一段口播，剪成抖音本地生活「9.9 引流」风格的竖屏短视频：首帧就抓人、中文配音、花字贴纸、逐个动作配音效、BGM 卡点、团购卡和左下角箭头。**

## 最快拿到第一个结果

装好后对 Agent 说：

> 这个文件夹是门店的原始素材，这是口播文案，照着对标视频剪一条 9.9 引流短视频。

它会先检查环境、给你 3–5 个中文配音试音让你挑，再出关键帧让你看画面，最后渲染成片。

## 安装

只装这一个：

```bash
npx -y skills add chenlongdei/deiskill --skill dei-shop-video
```

或者：

```bash
curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-shop-video
```

Windows PowerShell：

```powershell
$env:DEISKILL_ONLY="dei-shop-video"; irm https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.ps1 | iex
```

装在 Claude Code、Codex、WorkBuddy 等支持 Skills 的 Agent 上都可以；剪辑引擎是 HyperFrames（`npx` 自动下载），不依赖某个 Agent 的插件。

## 能做什么

- 给素材 + 文案 → 剪辑工程 + 成片 MP4（1080×1920，约 -11 LUFS）
- 只给素材 → 按 5 段结构先写一版口播给你确认
- 看完片说「声音小」「换个配音」「这里音效不对」「BGM 换成这首」→ 只改对应设定，重出新版本
- 换一家店：复制工程，改 `project.json` 里的文案、镜头和文字，就是新的一条

## 用的是什么方法

一条真实的健康馆 9.9 新店引流视频，照抖音爆款复刻，改了四版，用户的反馈都写进了规则：见 [references/method.md](references/method.md)。

- 5 段结构：地域钩子 → 低价 → 环境背书 → 原价对比加限量 → 点左下角
- 开头 5 秒：首帧大标题、定位钉、速度线砸字加震屏、闪白转场、彩带、低价爆炸贴加金币
- 配音只用中文母语音色，生成后自动用语音识别核对
- 每个动作一个音效（ElevenLabs 音效生成，提示词在 [templates/sfx_prompts.json](templates/sfx_prompts.json)）
- 镜头切点对齐 BGM 节拍，有大花字的句子不重复出底部字幕

工程怎么写见 [references/project-json.md](references/project-json.md)，例子 [templates/project.example.json](templates/project.example.json)。

## 准备什么、花多少钱

- Python 3.9+、ffmpeg、Node.js 18+、Chrome（见 [references/setup.md](references/setup.md)）
- ElevenLabs key（配音、语音核对、音效）：一条 26 秒的视频用很少的额度
- 字体文件（字幕和花字、价格数字），推荐免费商用的思源宋体 Heavy、抖音美好体
- BGM：Pixabay 需要你自己点下载（网站有人机验证），见 [references/bgm.md](references/bgm.md)

## 结果存在哪里

这件事已有项目文件夹的放在它下面；没有的放 dei 工作区的输出位置 `门店短视频/日期_店名/`。工程里只有 `project.json` 需要改，其余都由脚本生成。

## 许可

MIT，见仓库根目录。生成的配音、音效受 ElevenLabs 条款约束；BGM 和字体按各自许可使用。
