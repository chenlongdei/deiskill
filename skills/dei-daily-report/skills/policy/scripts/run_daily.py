#!/usr/bin/env python3
"""Portable macOS/Linux morning-report entry point; stdlib only."""
import argparse
import fcntl
import os
from pathlib import Path
import re
import shutil
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# Windows 中文系统默认 GBK：本脚本和它调用的 Python 工具（yt-dlp、notebooklm 等）一律用 UTF-8 输入输出
import os as _os, sys as _sys
_os.environ.setdefault("PYTHONUTF8", "1"); _os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _s in (_sys.stdout, _sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent


def _data_dir(module):
    """数据目录：见 dei-daily-report/scripts/dei_paths.py。"""
    import sys as _sys
    env = os.environ.get('DEI_DAILY_DATA_DIR')
    if env:
        return Path(env).expanduser()
    _sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
    from dei_paths import data_dir
    return data_dir(module)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', help='Broadcast date: YYYY-MM-DD or YYYYMMDD')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    now = datetime.now(ZoneInfo('Asia/Shanghai'))
    try:
        day = datetime.strptime(args.date.replace('-', ''), '%Y%m%d').date() if args.date else now.date() - timedelta(days=1)
    except ValueError:
        parser.error('Invalid broadcast date')
    data = _data_dir('policy')
    for name in ('logs', 'reports', 'transcripts', 'revisions', 'sources'):
        (data / name).mkdir(parents=True, exist_ok=True)
    with (data / 'logs/run.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another report run is active; skipped.')
            return 0
        report = data / 'reports' / f'{day}_分析报告.md'
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        version = re.search(r'version:\s*"([^"]+)"', skill).group(1)
        marker = f'<!-- method-version: {version} -->'
        if report.exists() and marker in report.read_text(encoding='utf-8') and not args.force:
            print(f'Existing report: {report}')
            return 0
        if report.exists():
            backup = data / 'revisions' / now.strftime('%Y%m%dT%H%M%S%f')
            backup.mkdir()
            shutil.move(str(report), str(backup / report.name))
        with (data / 'logs/daily.log').open('a', encoding='utf-8') as log:
            log.write(f'\n[{now.isoformat()}] START {day}\n')
            log.flush()
            # Fetch exact dates, including missing history; never substitute latest for yesterday.
            for n in range(31):
                target = day - timedelta(days=n)
                file = data / 'transcripts' / target.strftime('%Y/%m/%Y%m%d.md')
                if file.exists() and file.stat().st_size:
                    continue
                result = subprocess.run(['python3', str(ROOT / 'scripts/fetch_xwlb.py'), '--root', str(data), '--date', target.strftime('%Y%m%d')], stdout=log, stderr=log)
                if n == 0 and (result.returncode or not file.exists() or not file.stat().st_size):
                    print(f'FAIL: transcript unavailable for {day}; see {data / "logs/daily.log"}')
                    return 1
            prompt = f'''Read SKILL.md, references/analysis-method.md and templates/daily-report.md in this directory. Generate the full policy and business-opportunity report for broadcast date {day}; morning date is {day + timedelta(days=1)}. Transcripts have been fetched; inspect actual history coverage. Follow the hypothesis-driven method, verify public sources with your network tools, preserve marginal-change tables and prose elsewhere, with no industry preference or fixed card count. Data directory is {data}: transcripts, sources and revisions live there. Update {data / 'topics.json'} and record substantive revisions under {data / 'revisions'}. Write the finished report to {report} and include the exact metadata marker {marker}. If browsing is unavailable disclose that limitation, do not claim verification. Do not install schedules or call other agents.'''
            try:
                result = subprocess.run(['bash', str(ROOT / 'scripts/run_agent.sh')], input=prompt, text=True, encoding="utf-8", errors="replace", stdout=log, stderr=log, timeout=int(os.environ.get('XWLB_AGENT_TIMEOUT', '1800')))
            except subprocess.TimeoutExpired:
                print(f'FAIL: agent timed out; see {data / "logs/daily.log"}')
                return 1
            if result.returncode or not report.exists() or not report.stat().st_size:
                print(f'FAIL: agent did not produce a report; see {data / "logs/daily.log"}')
                return 1
            text = report.read_text(encoding='utf-8')
            if marker not in text:
                print('FAIL: report missing method-version metadata; rerun or inspect agent output.')
                return 1
            print(f'Report generated: {report}')
            return 0


if __name__ == '__main__':
    raise SystemExit(main())
