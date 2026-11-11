#!/bin/bash
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
exec python3 "$SKILL_DIR/scripts/run_daily.py" "$@"
