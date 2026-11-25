# 准备环境

运行 `python3 scripts/doctor.py`（Windows 上 `python3` 换成 `python`），按提示补齐。**安装命令要先问用户。**

| 需要 | 用来 | 安装 |
| --- | --- | --- |
| Python 3.9+ 和 jieba、numpy、soundfile | 跑脚本、字幕分词、混音 | `python3 -m pip install jieba numpy soundfile`（系统 Python 不让装时，建一个虚拟环境：`python3 -m venv ~/.deiskill/venv-talking-head`，之后用它的 python 跑脚本） |
| ffmpeg / ffprobe | 剪切、人声、响度 | macOS `brew install ffmpeg`；Windows `winget install Gyan.FFmpeg`；Linux `sudo apt install ffmpeg` |
| whisper.cpp（`whisper-cli`） | 本地中文转写 | macOS `brew install whisper-cpp`；Windows 从 github.com/ggml-org/whisper.cpp 的 Releases 下载；Linux 按官方 README 编译 |
| whisper 模型 `ggml-large-v3-turbo.bin`（约 1.6 GB） | 同上 | 从 huggingface.co/ggerganov/whisper.cpp 下载，放到 `~/.cache/whisper-models/`（或在 config.json 的 `whisper_model` 写路径）。下载大文件中断过，下完核对文件大小 |
| Node.js 18+ | 运行 HyperFrames（`npx --yes hyperframes@0.9.85`，第一次自动下载） | macOS `brew install node`；Windows `winget install OpenJS.NodeJS.LTS` |
| Chrome 或 Chromium | HyperFrames 渲染、截帧 | 一般已装 |
| 字体（推荐） | 字幕、标题、数字 | 阿里巴巴普惠体 3.0 Bold / Black（免费商用）、抖音美好体（免费商用）。文件路径写进 config.json 的 `font_bold` / `font_black` / `font_number` |
| ElevenLabs key（可选） | 按提示词生成音效；不配就自动用 Mixkit 免费音效 | elevenlabs.io → API Keys，勾 Sound Effects |
| Antigravity CLI `agy`（可选） | Gemini 听审 | 按 Google Antigravity 官方说明安装并登录 Google 账号 |
| pyJianYingDraft（可选） | 生成剪映多轨草稿（Apache-2.0） | `python3 -m pip install pyJianYingDraft`；没有它也能出字幕.srt 和透明图层.mov，在剪映里手动拼 |

## 配置

把 `config.example.json` 复制成同目录的 `config.json`（不进 Git）：

- `whisper_cli`、`whisper_model`：找不到时填路径。
- `font_*`：三个字体文件路径；`new.py` 建工程时复制进 `hf/assets/fonts/`。
- `elevenlabs_api_key` 或 `elevenlabs_key_file`，或环境变量 `ELEVENLABS_API_KEY`。key 不打印、不写进工程。
- `speed`（默认 1.1）、`split_gap`（默认 0.45 秒）、`loudness_lufs`（默认 -14）：新工程的默认值，每条视频在自己的 plan.json 里还能改。
- `reviewer_cli`、`reviewer_timeout`：听审工具和超时（默认 `agy`、900s）。

## 坑

- HyperFrames 自带的转写默认英文模型，会把中文翻成英文；本 Skill 用 whisper.cpp 指定中文，不用它。
- whisper.cpp 的逐字时间戳在一些机器上不可用：字幕按「句级时间 + 字数分配 + 对齐句内停顿」排，普通字幕够用，不做卡拉 OK 逐字高亮。
- 中文字幕断句必须先分词（jieba），否则会切成「找不 / 到」。
- ffmpeg 9 去掉了 `-filter_complex_script`，`cut.py` 两种写法都试。
- 字体用 `@font-face` 引工程里的文件；没有字体文件时退回系统字体，换电脑会变样。
- 剪映草稿是按 pyJianYingDraft 支持的格式写的，新版剪映可能打不开（作者这台机器没装剪映，草稿还没在剪映里实际打开过）；打不开就用 `交接/` 里的人物、图层、字幕手动拼。草稿里素材是绝对路径，工程文件夹不要挪。

## 费用

全部本地运行时不花钱。音效默认 Mixkit 免费；可选：ElevenLabs 音效（一条视频 10 个左右，用很少的额度）；Gemini 听审走用户自己的 Google 账号额度。
