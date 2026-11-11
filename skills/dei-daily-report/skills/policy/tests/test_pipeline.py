import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from datetime import date, timedelta

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    item = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(item)
    return item


class FetchTests(unittest.TestCase):
    def test_nested_body_and_paragraphs(self):
        fetch = module('fetch_xwlb')
        parsed = fetch.parse_day('<article class="content-section"><h2>Title</h2><div class="content-body"><p>First</p><div>Nested</div><p>Last</p></div></article>')
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]['title'], 'Title')
        self.assertIn('Nested', parsed[0]['content'])
        self.assertIn('Last', parsed[0]['content'])
        self.assertIn('\n', parsed[0]['content'])

    def test_exact_date_does_not_require_index(self):
        fetch = module('fetch_xwlb')
        with tempfile.TemporaryDirectory() as temp, patch('sys.argv', ['fetch', '--root', temp, '--date', '20260913']), patch.object(fetch, 'available_dates', side_effect=AssertionError('index called')), patch.object(fetch, 'fetch_html', return_value='<article class="content-section"><h2>Title</h2><div class="content-body">Body</div></article>'), patch.object(fetch.time, 'sleep'):
            self.assertEqual(fetch.main(), 0)
            self.assertTrue((Path(temp) / 'transcripts/2026/09/20260913.md').exists())

    def test_missing_content_returns_failure(self):
        fetch = module('fetch_xwlb')
        with tempfile.TemporaryDirectory() as temp, patch('sys.argv', ['fetch', '--root', temp, '--date', '20260913']), patch.object(fetch, 'fetch_html', return_value=''), patch.object(fetch.time, 'sleep'):
            self.assertEqual(fetch.main(), 1)

    def test_bad_date_is_rejected(self):
        fetch = module('fetch_xwlb')
        with tempfile.TemporaryDirectory() as temp, patch('sys.argv', ['fetch', '--root', temp, '--date', '20260230']):
            with self.assertRaises(SystemExit) as error:
                fetch.main()
            self.assertEqual(error.exception.code, 2)


class DailyTests(unittest.TestCase):
    def test_generation_then_dedup_then_force_backup(self):
        daily = module('run_daily')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'SKILL.md').write_text('version: "3.3.0"')
            day = date(2026, 9, 13)
            for i in range(31):
                p = root / 'data/transcripts' / (day - timedelta(days=i)).strftime('%Y/%m/%Y%m%d.md')
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('Transcript')
            report = root / 'data/reports/2026-09-13_分析报告.md'
            def agent(args, **kwargs):
                self.assertIn('broadcast date 2026-09-13', kwargs['input'])
                report.write_text('<!-- method-version: 3.3.0 -->\nComplete report')
                return subprocess.CompletedProcess(args, 0)
            with patch.object(daily, 'ROOT', root), patch('sys.argv', ['daily', '--date', '2026-09-13']), patch.object(daily.subprocess, 'run', side_effect=agent) as run:
                self.assertEqual(daily.main(), 0)
                self.assertEqual(daily.main(), 0)
                self.assertEqual(run.call_count, 1)
            with patch.object(daily, 'ROOT', root), patch('sys.argv', ['daily', '--date', '2026-09-13', '--force']), patch.object(daily.subprocess, 'run', side_effect=agent):
                self.assertEqual(daily.main(), 0)
                self.assertEqual(len(list((root / 'data/revisions').glob('*/2026-09-13_分析报告.md'))), 1)

    def test_missing_target_does_not_call_agent(self):
        daily = module('run_daily')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'SKILL.md').write_text('version: "3.3.0"')
            with patch.object(daily, 'ROOT', root), patch('sys.argv', ['daily', '--date', '2026-09-13']), patch.object(daily.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)) as run:
                self.assertEqual(daily.main(), 1)
                self.assertEqual(run.call_count, 1)
                self.assertIn('fetch_xwlb.py', run.call_args.args[0][1])


if __name__ == '__main__':
    unittest.main()
