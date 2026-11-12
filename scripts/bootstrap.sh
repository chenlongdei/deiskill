#!/usr/bin/env bash
# deiskill 一键安装：把仓库克隆或更新到 ~/.deiskill/repo，再运行安装器。
#
#   curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash
#   curl -fsSL https://raw.githubusercontent.com/chenlongdei/deiskill/main/scripts/bootstrap.sh | bash -s -- dei-capture
#
# "bash -s --" 后面的参数原样交给安装器（见 bash scripts/install.sh --help）。
set -euo pipefail

REPO_URL="${DEISKILL_REPO:-https://github.com/chenlongdei/deiskill.git}"
DEST="${DEISKILL_HOME:-$HOME/.deiskill}/repo"

for cmd in git python3; do
  command -v "$cmd" >/dev/null 2>&1 || { echo "缺少 $cmd，请先安装后再运行。" >&2; exit 1; }
done

if [ -d "$DEST/.git" ]; then
  echo "更新 $DEST"
  git -C "$DEST" pull --ff-only --quiet
else
  echo "下载到 $DEST"
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 --quiet "$REPO_URL" "$DEST"
fi

# 通过管道运行时标准输入是脚本本身；有终端时把它接回来，安装器才能询问装到哪个 Agent。
if [ -t 0 ] || ! { : </dev/tty; } 2>/dev/null; then
  exec python3 "$DEST/scripts/install.py" "$@"
else
  exec python3 "$DEST/scripts/install.py" "$@" </dev/tty
fi
