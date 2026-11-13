"""关键词巡检与定时模块的离线测试：不联网、不开浏览器、不碰本机真实配置和系统定时。"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class Env:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.out = base / "采集"
        self.out.mkdir()
        self.config = base / "config.json"
        self.config.write_text(json.dumps({"output_root": str(self.out), "douyin": {"keyword_watch": {
            "keywords": ["商业思维", {"word": "女性成长", "category": "情感"}]}}}, ensure_ascii=False), encoding="utf-8")
        self.env = {**os.environ, "DEI_CAPTURE_CONFIG": str(self.config)}
        self.env.pop("DEI_CAPTURE_DATA_DIR", None)

    def py(self, code):
        pre = f"import sys; sys.path.insert(0, {str(SCRIPTS / 'douyin')!r}); sys.path.insert(0, {str(SCRIPTS)!r}); "
        r = subprocess.run([sys.executable, "-c", pre + code], capture_output=True, text=True, env=self.env, cwd=ROOT)
        if r.returncode:
            raise AssertionError(r.stderr)
        return r.stdout.strip()


class KeywordWatchTest(unittest.TestCase):
    def setUp(self):
        self.e = Env()
        self.addCleanup(self.e.tmp.cleanup)

    def test_settings_normalizes_keywords(self):
        out = self.e.py("import keyword_watch as k, json; s = k.settings(); "
                        "print(json.dumps([s['keywords'], s['pages'], s['min_duration']], ensure_ascii=False))")
        kws, pages, mind = json.loads(out)
        self.assertEqual(kws[0], {"word": "商业思维"})
        self.assertEqual(kws[1]["category"], "情感")
        self.assertEqual((pages, mind), (2, 0))

    def test_fix_text(self):
        out = self.e.py("import keyword_watch as k; "
                        "print(k.fix_text('用 workbuddy 和 Workbuddy，还有沃克巴迪', {'workbuddy': 'WorkBuddy', '沃克巴迪': 'WorkBuddy'}))")
        self.assertEqual(out, "用 WorkBuddy 和 WorkBuddy，还有WorkBuddy")

    def test_media_choice(self):
        code = ("import keyword_watch as k, json; "
                "a = {'author': {'uid': '1'}, 'video': {'duration': 60000, 'play_addr': {'url_list': ['V']}}, "
                "'music': {'is_original_sound': True, 'duration': 60, 'play_url': {'url_list': ['A']}}}; "
                "b = json.loads(json.dumps(a)); b['music'].update(is_original_sound=False, owner_id='2'); "
                "print(json.dumps([k.media_choice(a), k.media_choice(b)]))")
        orig, bgm = json.loads(self.e.py(code))
        self.assertEqual([x[0] for x in orig], ["音频", "视频"])
        self.assertEqual([x[0] for x in bgm], ["视频"])

    def test_master_counts_reappearance(self):
        code = (
            "import keyword_watch as k, json; base = k.base_dir(); "
            "r = {'视频ID': '1', '关键词': '商业思维', '标题': 'T', '视频指数': 10, '逐字稿': '商业思维/01_T.md'}; "
            "k.update_master(base, '2026-01-01', [r], {}); "
            "k.update_master(base, '2026-01-04', [], {'女性成长': [{'itemId': '1', 'index': '99'}]}); "
            "k.update_master(base, '2026-01-04', [], {'女性成长': [{'itemId': '1', 'index': '99'}]}); "
            "m = json.loads((base / '.master.json').read_text(encoding='utf-8'))['1']; "
            "print(json.dumps(m, ensure_ascii=False)); print((base / '关键词总表.xlsx').exists())")
        line, exists = self.e.py(code).splitlines()
        m = json.loads(line)
        self.assertEqual(m["上榜次数"], 2)          # 同一天重复出现只算一次
        self.assertEqual(m["首次出现"], "2026-01-01")
        self.assertEqual(m["最近出现"], "2026-01-04")
        self.assertEqual(m["视频指数"], 99)
        self.assertEqual(m["关键词"], "商业思维、女性成长")
        self.assertEqual(m["逐字稿"], "2026-01-01/逐字稿/商业思维/01_T.md")
        self.assertEqual(exists, "True")

    def test_help(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "douyin" / "keyword_watch.py"), "--help"],
                           capture_output=True, text=True, env=self.e.env)
        self.assertEqual(r.returncode, 0)
        for word in ("doctor", "login", "schedule"):
            self.assertIn(word, r.stdout)


class SchedulerTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(SCRIPTS))
        import scheduler
        self.s = scheduler

    def test_parse_at(self):
        self.assertEqual(self.s._parse_at("02:05"), (2, 5))
        with self.assertRaises(ValueError):
            self.s._parse_at("25:00")

    def test_protected_only_on_mac(self):
        p = Path("/Volumes") / "外接盘" / "x"
        self.assertEqual(self.s.protected(p), sys.platform == "darwin")
        self.assertFalse(self.s.protected(Path(tempfile.gettempdir())))

    def test_scheduler_python_exists(self):
        self.assertTrue(Path(self.s.scheduler_python()).exists())


if __name__ == "__main__":
    unittest.main()
