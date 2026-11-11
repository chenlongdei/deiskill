import importlib.util
import tempfile
from pathlib import Path
from datetime import datetime
import unittest
from unittest.mock import patch
import urllib.error
import openpyxl
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pipeline", ROOT / "skills/douyin/scripts/run_pipeline.py")
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
            with patch.object(pipeline.urllib.request,"urlopen",side_effect=urllib.error.HTTPError("https://example.com",status,"blocked",{},None)) as request:
                with self.assertRaises(pipeline.StopExternal): pipeline.req("https://example.com")
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
