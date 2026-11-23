# 准备环境

运行 `python3 scripts/doctor.py`（Windows 上 `python3` 通常换成 `python`），按提示补齐。安装命令要先问用户。

| 需要 | 用来 | 安装 |
| --- | --- | --- |
| Python 3.9+ | 跑脚本 | macOS 自带；Windows `winget install Python.Python.3.12` |
| ffmpeg / ffprobe | 读素材、缩略图、响度 | macOS `brew install ffmpeg`；Windows `winget install Gyan.FFmpeg`；Linux `sudo apt install ffmpeg` |
| Node.js 18+ | 运行 HyperFrames（`npx --yes hyperframes@0.9.84`，第一次自动下载） | macOS `brew install node`；Windows `winget install OpenJS.NodeJS.LTS`；Linux `sudo apt install nodejs npm` |
| Chrome 或 Chromium | HyperFrames 渲染、截帧 | 一般已装；没有时 `npx --yes hyperframes@0.9.84 doctor` 会提示 |
| ElevenLabs key | 中文配音、语音核对、音效生成 | elevenlabs.io → API Keys 新建；勾上 Text to Speech、Speech to Text、Sound Effects，最好再勾 Voices 读取（能搜音色） |

## 凭证与配置

把 `config.example.json` 复制成同目录的 `config.json`：

- `elevenlabs_api_key`：填 key；或者 `elevenlabs_key_file` 写一个存 key 的文件路径；也可以用环境变量 `ELEVENLABS_API_KEY`。key 不打印、不写进工程和成片。
- `voice_id`、`tts_model`：默认音色和模型，新工程从这里取。
- `font_caption`、`font_display`、`font_number`：字幕、花字、价格数字三种字体的文件路径。推荐照对标视频的搭配：字幕和花字用**思源宋体 Heavy**（粗宋体，开源免费商用，文件 `SourceHanSerifSC-Heavy.otf`），价格数字、定位钉、标签用**抖音美好体**（免费商用，`DouyinSansBold.ttf`）。没有这两个时退回阿里巴巴普惠体 Black。用户自己有字体就用自己的，交付前确认字体能商用。
- `loudness_lufs`：成片响度，默认 -11。

## HyperFrames

这个 Skill 用 HyperFrames 把 HTML 渲染成视频，所有命令都走 `npx --yes hyperframes@<版本>`，不依赖任何 Agent 的插件。想在网页里手动微调时，在工程文件夹运行 `npx --yes hyperframes@0.9.84 preview`。

## 费用（2026-11 参考）

- ElevenLabs：一条 26 秒视频的配音约 150 个汉字、试音 5 条、语音核对 6 次、音效 14 个；按套餐额度计。
- HyperFrames 本地渲染不收费。
