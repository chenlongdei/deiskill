#!/bin/bash
# Default: initialize only. Scheduling and model execution are explicit options.
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKFILL=0
SCHEDULE=0
RUN_NOW=0
for arg in "$@"; do
    case "$arg" in
        --backfill) BACKFILL=1 ;;
        --launchd) SCHEDULE=1 ;;
        --run-now) RUN_NOW=1 ;;
        --no-launchd) SCHEDULE=0 ;;
        *) echo "Usage: bash install.sh [--backfill] [--run-now] [--launchd] [--no-launchd]"; exit 1 ;;
    esac
done
command -v python3 >/dev/null || { echo 'Python 3.9+ required'; exit 1; }
command -v curl >/dev/null || { echo 'curl required'; exit 1; }
python3 -c 'import sys; from zoneinfo import ZoneInfo; assert sys.version_info >= (3,9); ZoneInfo("Asia/Shanghai")'
DATA_DIR="$(python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from dei_paths import data_dir; print(data_dir("policy"))' "$SKILL_DIR/../../scripts")"
mkdir -p "$DATA_DIR/transcripts" "$DATA_DIR/reports" "$DATA_DIR/logs" "$DATA_DIR/revisions" "$DATA_DIR/sources"
if [ "$SCHEDULE" = 1 ] || [ "$RUN_NOW" = 1 ]; then
    if [ ! -f "$SKILL_DIR/agent.conf" ] && ! command -v codex >/dev/null && ! command -v claude >/dev/null; then
        echo 'Configure agent.conf or install/login to a supported CLI first.'; exit 1
    fi
fi
if [ "$BACKFILL" = 1 ]; then python3 "$SKILL_DIR/scripts/fetch_xwlb.py" --days 31; fi
if [ "$SCHEDULE" = 1 ]; then
    [ "$(uname)" = Darwin ] || { echo '--launchd requires macOS; use your scheduler on Linux.'; exit 1; }
    python3 -c 'from datetime import datetime; assert datetime.now().astimezone().utcoffset().total_seconds() == 28800, "launchd 按本机时区触发；本机不是北京时间时，请按 references/scheduling.md 换算时间后另行配置"'
    python3 - "$SKILL_DIR" "$DATA_DIR" <<'PY'
import os, plistlib, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]); data=Path(sys.argv[2]); label='com.codex.xwlb-analysis'  # 标签沿用旧名，避免与已注册任务重复
path=Path.home()/'Library/LaunchAgents'/f'{label}.plist'
path.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['launchctl','unload',str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
node={'Label':label,'ProgramArguments':['/bin/bash',str(root/'scripts/run_daily.sh')],
      'EnvironmentVariables':{'PATH':os.environ['PATH']},
      'StartCalendarInterval':{'Hour':5,'Minute':0},
      'StandardOutPath':str(data/'logs/launchd.out.log'),
      'StandardErrorPath':str(data/'logs/launchd.err.log')}
with path.open('wb') as f: plistlib.dump(node,f)
subprocess.run(['launchctl','load',str(path)],check=True)
print('Registered launchd 05:00; do not also enable agent scheduling.')
PY
fi
if [ "$RUN_NOW" = 1 ]; then bash "$SKILL_DIR/scripts/run_daily.sh"; fi
echo "Initialized: $SKILL_DIR"
echo 'Read README.md for agent deployment and scheduling.'
