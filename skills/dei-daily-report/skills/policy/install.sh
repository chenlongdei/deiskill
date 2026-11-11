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
mkdir -p "$SKILL_DIR/data/transcripts" "$SKILL_DIR/data/reports" "$SKILL_DIR/data/logs" "$SKILL_DIR/data/revisions" "$SKILL_DIR/data/sources"
if [ "$SCHEDULE" = 1 ] || [ "$RUN_NOW" = 1 ]; then
    if [ ! -f "$SKILL_DIR/agent.conf" ] && ! command -v codex >/dev/null && ! command -v claude >/dev/null; then
        echo 'Configure agent.conf or install/login to a supported CLI first.'; exit 1
    fi
fi
if [ "$BACKFILL" = 1 ]; then python3 "$SKILL_DIR/scripts/fetch_xwlb.py" --days 31; fi
if [ "$SCHEDULE" = 1 ]; then
    [ "$(uname)" = Darwin ] || { echo '--launchd requires macOS; use your scheduler on Linux.'; exit 1; }
    python3 -c 'from datetime import datetime; assert datetime.now().astimezone().utcoffset().total_seconds() == 28800, "Set system timezone to Asia/Shanghai for launchd 05:00; otherwise use a timezone-aware agent scheduler"'
    python3 - "$SKILL_DIR" <<'PY'
import os, plistlib, subprocess, sys
from pathlib import Path
root=Path(sys.argv[1]); label='com.codex.xwlb-analysis'
path=Path.home()/'Library/LaunchAgents'/f'{label}.plist'
path.parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['launchctl','unload',str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
node={'Label':label,'ProgramArguments':['/bin/bash',str(root/'scripts/run_daily.sh')],
      'EnvironmentVariables':{'PATH':os.environ['PATH']},
      'StartCalendarInterval':{'Hour':5,'Minute':0},
      'StandardOutPath':str(root/'data/logs/launchd.out.log'),
      'StandardErrorPath':str(root/'data/logs/launchd.err.log')}
with path.open('wb') as f: plistlib.dump(node,f)
subprocess.run(['launchctl','load',str(path)],check=True)
print('Registered launchd 05:00; do not also enable agent scheduling.')
PY
fi
if [ "$RUN_NOW" = 1 ]; then bash "$SKILL_DIR/scripts/run_daily.sh"; fi
echo "Initialized: $SKILL_DIR"
echo 'Read README.md for agent deployment and scheduling.'
