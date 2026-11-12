# 环境准备（macOS / Windows / Linux）

某个自检（`doctor`）报缺依赖时读本文，按用户的系统给出**一条**安装命令，用户同意后再执行。只装这次要用的，不一次装全。装完重新打开终端，再跑一次自检。

## Python 命令名

本 Skill 的命令写作 `python3`。Windows 上通常是 `python`（或 `py -3`）：先运行 `python --version`，能输出 3.9 以上就用 `python`。Windows 自带的「Microsoft Store 版 python」只是个跳转入口，运行后打开商店的，不算已安装。

## 按功能需要什么

| 功能 | 需要 |
| --- | --- |
| YouTube 搜索、频道、字幕 | Python 3.9+、yt-dlp；字幕常要一个已登录 YouTube 的浏览器 |
| YouTube 无字幕视频、本地音视频转写 | ffmpeg、whisper.cpp（`whisper-cli`）和模型文件 |
| 抖音链接出稿、盯博主 | Python 3.9+（只用标准库），以及 Monid 或 TikHub、大圣、阿里云百炼的凭证 |
| 抖音监控工作簿 | 上一行，加 openpyxl |
| 抖音博主全量导出（Get笔记） | playwright + chromium（扫码登录和自动续期用） |
| 社媒助手自动导出数据 | playwright、Google Chrome，以及装好社媒助手插件的专用 Chrome 实例 |

## 安装命令

| 依赖 | macOS（Homebrew） | Windows（PowerShell） | Linux（Debian/Ubuntu） |
| --- | --- | --- | --- |
| Python 3.9+ | `brew install python` | `winget install --id Python.Python.3.12 -e`（安装时勾选 Add to PATH） | `sudo apt install python3 python3-pip` |
| git | `xcode-select --install` | `winget install --id Git.Git -e` | `sudo apt install git` |
| yt-dlp | `brew install yt-dlp` | `winget install --id yt-dlp.yt-dlp -e` 或 `python -m pip install -U yt-dlp` | `python3 -m pip install --user -U yt-dlp` |
| ffmpeg | `brew install ffmpeg` | `winget install --id Gyan.FFmpeg -e` | `sudo apt install ffmpeg` |
| whisper.cpp | `brew install whisper-cpp` | 从 github.com/ggml-org/whisper.cpp 的 Releases 下载 Windows 版，把 `whisper-cli.exe` 所在目录加入 PATH，或把完整路径写进 `whisper.cmd` | 按 whisper.cpp 仓库说明编译 |
| openpyxl | `python3 -m pip install --user openpyxl` | `python -m pip install openpyxl` | 同 macOS |
| playwright | `python3 -m pip install --user playwright && python3 -m playwright install chromium` | `python -m pip install playwright; python -m playwright install chromium` | 同 macOS，另加 `python3 -m playwright install-deps` |
| Google Chrome | 官网下载 | `winget install --id Google.Chrome -e` | 官网下载 |

whisper 模型推荐 `ggml-large-v3-turbo-q5_0.bin`（约 550 MB），从 Hugging Face 的 ggerganov/whisper.cpp 仓库下载，存放位置问用户，路径写进 `whisper.model`。

## 常见问题

- **yt-dlp 报 `The page needs to be reloaded` 或格式不可用**：yt-dlp 版本太旧，升级（`brew upgrade yt-dlp` 或 `pip install -U yt-dlp`）。
- **读浏览器 cookies 失败**：
  - macOS 要给终端或 Agent「完全磁盘访问权限」（系统设置 → 隐私与安全性）。
  - Windows 上 Chrome 正在运行时常读不到，先完全退出 Chrome，或改用 Firefox（`cookies_from_browser` 写 `firefox`）。
- **Windows 上中文乱码**：脚本已强制 UTF-8 输出。仍乱码时，在 PowerShell 先运行 `$env:PYTHONUTF8=1` 再执行命令。
- **路径里有空格或中文**：命令里的路径一律加英文双引号。
- **pip 装完找不到命令**：用 `python -m <模块>` 的方式运行，或把提示里的 Scripts 目录加入 PATH。
