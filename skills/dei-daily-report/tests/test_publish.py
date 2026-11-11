import importlib.util, json, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("check_report", ROOT / "publish/check_report.py")
cr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cr)
EXAMPLE = ROOT / "publish/example"


class PublishCheckTests(unittest.TestCase):
    def run_check(self, md=None, data=None):
        md = md if md is not None else (EXAMPLE / "report.md").read_text(encoding="utf-8")
        data = data if data is not None else json.loads((EXAMPLE / "data.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            m, j = Path(d) / "r.md", Path(d) / "r.json"
            m.write_text(md, encoding="utf-8"); j.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            return cr.check(m, j)

    def test_example_passes(self):
        _, errors, _ = self.run_check()
        self.assertEqual(errors, [])

    def test_internal_words_rejected(self):
        md = (EXAMPLE / "report.md").read_text(encoding="utf-8").replace("## 二、AI", "本期未配置抖音。\n\n## 二、AI")
        _, errors, _ = self.run_check(md=md)
        self.assertTrue(any("未配置" in e for e in errors))

    def test_even_items_rejected(self):
        md = (EXAMPLE / "report.md").read_text(encoding="utf-8").replace("### 3. 其他值得知道的", "### 3. 补充\n\n### 4. 其他值得知道的", 1)
        _, errors, _ = self.run_check(md=md)
        self.assertTrue(any("单数" in e for e in errors))

    def test_cover_headline_rules(self):
        data = json.loads((EXAMPLE / "data.json").read_text(encoding="utf-8"))
        data["headline"] = ["学时记账。", "智能体挑工具。", "旧闻重播。"]
        data["contents"][0]["items"][0] = "国家政策"
        data["issue"] = "1112"
        _, errors, warns = self.run_check(data=data)
        self.assertTrue(any("句号" in e for e in errors))
        self.assertTrue(any("具体条目" in e for e in errors))
        self.assertTrue(any("期号" in e for e in errors))
        self.assertTrue(any("清单" in w for w in warns))

    def test_too_short_rejected(self):
        md = (EXAMPLE / "report.md").read_text(encoding="utf-8").split("## 一、国家政策")[0]
        _, errors, _ = self.run_check(md=md)
        self.assertTrue(any("字" in e for e in errors))




class TrafficDeckTests(unittest.TestCase):
    def test_single_card_per_module_warns(self):
        data = json.loads((EXAMPLE / "data.json").read_text(encoding="utf-8"))
        data["cards"] = [c for c in data["cards"] if c["id"] in ("core-1", "policy-1", "ai-1", "social-1", "next")]
        _, _, warns = PublishCheckTests().run_check(data=data)
        self.assertTrue(any("至少两张" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
