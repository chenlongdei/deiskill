"""离线测试：字幕解析、去重推荐、链接识别。运行：python3 tests/test_youtube.py"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import youtube as yt  # noqa: E402

AUTO_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.160 --> 00:00:02.869 align:start position:0%
 
hello<00:00:00.480><c> everyone</c>

00:00:02.869 --> 00:00:02.879 align:start position:0%
hello everyone
 

00:00:02.879 --> 00:00:05.430 align:start position:0%
hello everyone
today<00:00:03.120><c> we</c><c> talk</c>

00:01:05.000 --> 00:01:07.000
second &amp; paragraph
"""

SRT = """1
00:00:01,000 --> 00:00:02,000
你好

2
00:00:02,000 --> 00:00:03,000
世界
"""


class SubtitleTests(unittest.TestCase):
    def test_auto_vtt_dedupes_rolling_lines(self):
        cues = yt.parse_subtitles(AUTO_VTT)
        self.assertEqual([t for _, t in cues], ["hello everyone", "today we talk", "second & paragraph"])
        paras = yt.paragraphs(cues)
        self.assertEqual(paras, ["[0:00] hello everyone today we talk", "[1:05] second & paragraph"])

    def test_srt_chinese_join_without_spaces(self):
        self.assertEqual(yt.paragraphs(yt.parse_subtitles(SRT)), ["[0:01] 你好世界"])

    def test_pick_subtitle_prefers_manual_then_original_auto(self):
        info = {"language": "en", "subtitles": {}, "automatic_captions": {"en-orig": [], "zh-Hans": [], "en": []}}
        self.assertEqual(yt.pick_subtitle(info, ["zh-Hans", "en"]), ("en-orig", "auto"))
        info["subtitles"] = {"en": []}
        self.assertEqual(yt.pick_subtitle(info, ["zh-Hans", "en"]), ("en", "manual"))
        self.assertIsNone(yt.pick_subtitle({"subtitles": {"live_chat": []}}, ["en"]))


class HelperTests(unittest.TestCase):
    def test_video_id(self):
        self.assertEqual(yt.video_id("https://www.youtube.com/watch?v=bjdBVZa66oU&t=3"), "bjdBVZa66oU")
        self.assertEqual(yt.video_id("https://youtu.be/bjdBVZa66oU"), "bjdBVZa66oU")
        self.assertEqual(yt.video_id("https://www.youtube.com/shorts/bjdBVZa66oU"), "bjdBVZa66oU")
        self.assertIsNone(yt.video_id("https://www.youtube.com/@claude"))

    def test_numbers(self):
        self.assertEqual(yt.to_int("1.2M"), 1200000)
        self.assertEqual(yt.to_int("3,400"), 3400)
        self.assertEqual(yt.to_int("2.5万"), 25000)
        self.assertEqual(yt.to_seconds("1:02:03"), 3723)
        self.assertEqual(yt.fmt_duration(3723), "1:02:03")
        self.assertEqual(yt.fmt_views(15300), "15.3K")

    def test_recommend_caps_channel_and_views(self):
        vids = [{"id": str(i), "channel": "A" if i < 3 else "B", "views": v}
                for i, v in enumerate([90000, 80000, 70000, 60000, 500])]
        self.assertEqual([v["id"] for v in yt.recommend(vids, 10000, 2)], ["0", "1", "3"])

    def test_channel_url(self):
        self.assertEqual(yt.channel_url("@claude"), "https://www.youtube.com/@claude")
        self.assertEqual(yt.channel_url("https://www.youtube.com/@claude/videos/"), "https://www.youtube.com/@claude")

    def test_find_dicts_nested(self):
        payload = {"data": {"items": {"list": [{"video_id": "x"}, {"video_id": "y"}]}}}
        self.assertEqual(len(yt.find_dicts(payload, "video_id")), 2)


if __name__ == "__main__":
    unittest.main()
