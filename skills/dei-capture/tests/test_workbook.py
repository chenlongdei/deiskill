"""监控工作簿（原日报抖音模块）的离线测试。"""
import unittest
import importlib.util
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch
import urllib.error
try:
    import openpyxl
except ImportError:  # 监控工作簿依赖 openpyxl；没装时跳过整组测试
    raise unittest.SkipTest("需要 openpyxl：python3 -m pip install openpyxl")
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT / "scripts/douyin"))
import tikhub  # noqa: E402
spec = importlib.util.spec_from_file_location("pipeline", ROOT / "scripts/douyin/workbook.py")
pipeline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline)
class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.journal=patch.object(pipeline,"ASR_JOURNAL",Path(self.temp.name)/"tasks.json")
        self.journal.start()
    def tearDown(self):
        self.journal.stop(); self.temp.cleanup()
    def test_incremental_metrics_preserve_manual_text(self):
        with tempfile.TemporaryDirectory() as temp:
            source, output = Path(temp)/"source.xlsx", Path(temp)/"output.xlsx"
            book=openpyxl.Workbook(); sheet=book.active; sheet.title="author"
            sheet.cell(3,1,1); sheet.cell(3,5,"https://www.douyin.com/video/123")
            for col,value in [(8,"人工逐字稿"),(11,"人工结尾"),(12,"人工开头"),(20,"个人创作"),(36,"复盘")]:sheet.cell(3,col,value)
            book.save(source)
            video={"id":"123","title":"新标题","bgm":"音乐","url":"https://www.douyin.com/video/123","publish":datetime(2026,9,14),"likes":12,"comments":2,"collects":1,"shares":1,"transcript":"新转写"}
            pipeline.write_book(source,output,[{"sheet":"author","followers":100,"videos":[video]}],datetime.now())
            sheet=openpyxl.load_workbook(output).active
            self.assertEqual(sheet.cell(3,15).value,12)
            self.assertEqual(sheet.cell(3,8).value,"人工逐字稿")
            self.assertEqual(sheet.cell(3,11).value,"人工结尾")
            self.assertEqual(sheet.cell(3,20).value,"个人创作")
            self.assertEqual(sheet.cell(3,36).value,"复盘")
            self.assertEqual(sum("/video/" in str(sheet.cell(row,5).value) for row in range(3,sheet.max_row+1)),1)
    def test_duplicate_new_video_only_has_one_row(self):
        with tempfile.TemporaryDirectory() as temp:
            source,output=Path(temp)/"source.xlsx",Path(temp)/"output.xlsx"
            book=openpyxl.Workbook(); book.active.title="author"; book.save(source)
            video={"id":"123","title":"标题","bgm":"","url":"https://www.douyin.com/video/123","publish":datetime.now(),"likes":1,"comments":0,"collects":0,"shares":0}
            pipeline.write_book(source,output,[{"sheet":"author","followers":100,"videos":[video,video]}],datetime.now())
            sheet=openpyxl.load_workbook(output).active
            self.assertEqual(sum("/video/" in str(sheet.cell(row,5).value) for row in range(3,sheet.max_row+1)),1)
    def test_credentials_stop_without_retry(self):
        for status in [401,402,403]:
            with patch.object(tikhub.urllib.request,"urlopen",side_effect=urllib.error.HTTPError("https://example.com",status,"blocked",{},None)) as request:
                with self.assertRaises(tikhub.StopExternal): tikhub.req("https://example.com")
                self.assertEqual(request.call_count,1)
    def test_transcription_stops_before_second_video(self):
        with patch.object(pipeline,"submit",side_effect=pipeline.StopExternal("HTTP 401")) as submit:
            with self.assertRaises(pipeline.StopExternal):pipeline.transcribe([{"id":"1","media":"url"},{"id":"2","media":"url"}],"test")
            self.assertEqual(submit.call_count,1)
    def test_transcription_query_and_restart_reuse(self):
        replies=[{"output":{"task_status":"SUCCEEDED","results":[{"transcription_url":"https://example.com/result"}]}},{"transcripts":[{"text":"hello","sentences":[{"text":"hello","begin_time":0}]}]}]
        videos=[{"id":"1","media":"url"}]
        with patch.object(pipeline,"submit",return_value="task") as submit, patch.object(pipeline,"req",side_effect=replies) as request, patch.object(pipeline.time,"sleep"):
            result=pipeline.transcribe(videos,"test")
            self.assertEqual(result["1"][0],"hello")
            self.assertEqual(request.call_args_list[0].kwargs["method"],"GET")
            resumed=pipeline.transcribe(videos,"test")
            self.assertEqual(resumed,result)
            self.assertEqual(submit.call_count,1)
    def test_pending_journal_resumes_without_submission(self):
        pipeline.ASR_JOURNAL.write_text('{"1":{"task_id":"prior-task"}}')
        replies=[{"output":{"task_status":"SUCCEEDED","results":[{"transcription_url":"https://example.com/result"}]}},{"transcripts":[{"text":"done"}]}]
        with patch.object(pipeline,"submit") as submit, patch.object(pipeline,"req",side_effect=replies), patch.object(pipeline.time,"sleep"):
            self.assertEqual(pipeline.transcribe([{"id":"1","media":"url"}],"test")["1"][0],"done")
            submit.assert_not_called()
if __name__ == "__main__":unittest.main()


class TemplateTests(unittest.TestCase):
    def test_template_creates_blogger_sheets(self):
        with tempfile.TemporaryDirectory() as temp:
            src, out = Path(temp) / "监控.xlsx", Path(temp) / "out.xlsx"
            book = openpyxl.load_workbook(pipeline.TEMPLATE)
            total = book["相似博主总表"]
            total.cell(3, 3, "博主甲"); total.cell(3, 5, "https://www.douyin.com/user/MS4wLjABAAAAabc-_x?from=web")
            total.cell(4, 3, "博主乙")
            book.save(src)
            path, created = pipeline.prepare(src, out)
            self.assertEqual((path, created), (out, ["博主甲", "博主乙"]))
            wb = openpyxl.load_workbook(out)
            self.assertEqual(pipeline.blogger_sheets(wb), ["博主甲", "博主乙"])  # 隐藏模板页和示例行不算
            self.assertEqual(wb["博主甲"].cell(2, 3).value, "标题")
            self.assertEqual(dict((n, s) for n, _, s in pipeline.read_total(wb))["博主甲"], "MS4wLjABAAAAabc-_x")
            again, created2 = pipeline.prepare(out, Path(temp) / "x.xlsx")
            self.assertEqual((again, created2), (out, []))

    def test_monid_posts_mapping_and_window(self):
        page = {"output": {"data": {"hasMore": False, "posts": [
            {"id": "111", "caption": "新视频", "createdUtc": 2_000_000_000, "likes": 10, "comments": 2, "saves": 3, "shares": 1},
            {"id": "222", "caption": "旧视频", "createdUtc": 1_000_000_000, "likes": 5}]}}}
        with patch.object(pipeline, "monid_run", return_value=page):
            videos = pipeline.MonidSource({}).posts("sec", since=1_500_000_000)
        self.assertEqual([v["id"] for v in videos], ["111"])
        v = videos[0]
        self.assertEqual((v["collects"], v["bgm"], v["_followers"]), (3, "", None))
        self.assertEqual(v["url"], "https://www.douyin.com/video/111")


class BackupTests(unittest.TestCase):
    def test_backup_keeps_latest(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / "表.xlsx"
            src.write_bytes(b"x")
            d = Path(temp) / "备份"
            d.mkdir()
            for i in range(12):
                (d / f"表_20260101_0000{i:02d}.xlsx").write_bytes(b"old")
            dst = pipeline.backup_copy(src, keep=10)
            self.assertTrue(dst.exists())
            self.assertEqual(len(list(d.glob("表_*.xlsx"))), 10)
