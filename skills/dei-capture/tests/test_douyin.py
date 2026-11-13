"""抖音模块与统一转写的离线测试：不联网、不碰本机真实配置。"""

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
    """临时 config.json + 临时 output_root。"""

    def __init__(self, douyin=None, dashscope=None):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.out = base / "采集"
        self.out.mkdir()
        self.config = base / "config.json"
        self.config.write_text(json.dumps({"output_root": str(self.out), "douyin": douyin or {},
                                           "dashscope": dashscope or {}}, ensure_ascii=False), encoding="utf-8")
        self.env = {**os.environ, "DEI_CAPTURE_CONFIG": str(self.config)}
        self.env.pop("DEI_CAPTURE_DATA_DIR", None)
        self.env.pop("DASHSCOPE_API_KEY", None)

    def run(self, *args):
        return subprocess.run([sys.executable, *args], capture_output=True, text=True, env=self.env, cwd=ROOT)

    def py(self, code):
        return self.run("-c", f"import sys; sys.path.insert(0, {str(SCRIPTS / 'douyin')!r}); {code}")


class Base(unittest.TestCase):
    def make_env(self, **kw):
        e = Env(**kw)
        self.addCleanup(e.tmp.cleanup)
        return e


class DouyinTests(Base):
    def test_config_defaults_under_output_root(self):
        e = self.make_env(douyin={"monid": {"token": "x"}}, dashscope={"api_key": "sk-test"})
        r = e.py("import common, json; c = common.load_config(); "
                 "print(json.dumps([c['workspace'], c['biji_export_base'], c['dashscope']['api_key'], "
                 "c['dashscope']['model'], c['monid']['token']], ensure_ascii=False))")
        self.assertEqual(r.returncode, 0, r.stderr)
        ws, biji, key, model, token = json.loads(r.stdout)
        self.assertEqual(Path(ws), e.out / "抖音" / "_原始数据")
        self.assertEqual(Path(biji), e.out / "抖音" / "博主")
        self.assertEqual((key, model, token), ("sk-test", "paraformer-v2", "x"))

    def test_missing_output_root_stops(self):
        e = self.make_env()
        e.config.write_text("{}", encoding="utf-8")
        r = e.py("import common; common.load_config()")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("output_root", r.stderr)

    def test_watch_list_written_to_douyin_section(self):
        e = self.make_env()
        r = e.py("import common; print(common.save_watch_list('MS4wLjABtest'), common.save_watch_list('MS4wLjABtest'))")
        self.assertEqual(r.stdout.split(), ["True", "False"], r.stderr)
        cfg = json.loads(e.config.read_text(encoding="utf-8"))
        self.assertEqual(cfg["douyin"]["monid"]["watch_sec_user_ids"], ["MS4wLjABtest"])
        self.assertIn("output_root", cfg)  # 其他配置不丢

    def test_merge_output_writes_markdown_and_index(self):
        e = self.make_env()
        ws = e.out / "抖音" / "_原始数据"
        ws.mkdir(parents=True)
        store = {"videos": {"7300000000000000001": {
            "video_id": "7300000000000000001", "title": "测试视频", "author_name": "测试博主",
            "publish_time": "2026-11-01 10:00:00", "share_url": "https://www.douyin.com/video/7300000000000000001",
            "stats": {"likes": 120, "comments": 8, "collects": 5, "shares": 2},
            "asr": {"status": "done"}, "transcript": "第一句。第二句！第三句？", "stage": "transcribed"}}}
        (ws / "videos.json").write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")
        r = e.run("scripts/douyin/merge_output.py")
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        bloggers = e.out / "抖音" / "博主"
        files = list((bloggers / "测试博主" / "监控更新").glob("*.md"))
        self.assertEqual(len(files), 1)
        text = files[0].read_text(encoding="utf-8")
        self.assertIn("第一句。", text)
        self.assertIn("120", text)
        self.assertTrue((bloggers / "监控索引.md").exists())

    def test_social_stats_csv(self):
        e = self.make_env()
        csv_file = e.out / "数据.csv"
        csv_file.write_text("视频描述,发布时间,点赞量,评论量,视频链接\n标题一,2026-11-01,1.2万,30,"
                            "https://www.douyin.com/video/7300000000000000001\n", encoding="utf-8")
        r = e.run("scripts/douyin/social_stats.py", str(csv_file))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("12000", r.stdout)


class TranscribeTests(Base):
    def test_rejects_page_links_and_missing_files(self):
        e = self.make_env()
        r = e.run("scripts/transcribe.py", "https://v.douyin.com/abc/", str(e.out / "不存在.mp3"))
        summary = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(summary["ok"], 0)
        self.assertIn("平台页面链接", summary["results"][0]["error"])
        self.assertEqual(summary["results"][1]["error"], "文件不存在")
        self.assertEqual(Path(summary["dir"]), e.out / "转写")

    def test_srt_and_paragraphs(self):
        sys.path.insert(0, str(SCRIPTS))
        import asr
        cues = asr.parse_srt("1\n00:00:01,000 --> 00:00:02,000\n你好\n\n2\n00:01:05,500 --> 00:01:06,000\n再见\n")
        self.assertEqual(cues, [(1.0, "你好"), (65.5, "再见")])
        self.assertEqual(asr.paragraphs(cues), ["[0:01] 你好", "[1:05] 再见"])


if __name__ == "__main__":
    unittest.main()
