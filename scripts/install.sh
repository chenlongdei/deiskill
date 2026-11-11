#!/usr/bin/env bash
# 安装 deiskill。参数见：bash scripts/install.sh --help
set -euo pipefail
exec python3 "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/install.py" "$@"
