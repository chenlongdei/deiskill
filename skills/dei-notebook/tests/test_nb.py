"""离线测试：资料展开、标题提取，以及用假 CLI 跑通导入和提问。运行：python3 tests/test_nb.py"""

import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
import nb  # noqa: E402

FAKE_CLI = r'''#!/usr/bin/env python3
import json, sys, os
from pathlib import Path
state = Path(os.environ["FAKE_NB_STATE"])
db = json.loads(state.read_text()) if state.exists() else {"books": [], "sources": []}
a = [x for x in sys.argv[1:] if x != "--json"]
def out(d): print(json.dumps(d)); state.write_text(json.dumps(db)); sys.exit(0)
if a[0] == "list": out({"notebooks": db["books"]})
if a[0] == "create":
    b = {"id": "nb123456789", "title": a[1]}; db["books"].append(b); out({"notebook": b})
if a[:2] == ["source", "list"]: out({"sources": db["sources"]})
if a[:2] == ["source", "add"]:
    title = a[a.index("--title") + 1] if "--title" in a else a[2]
    if "bad" in a[2]: print(json.dumps({"error": True, "message": "rpc_code=9"})); sys.exit(1)
    s = {"id": "s%d" % len(db["sources"]), "title": title, "url": a[2] if a[2].startswith("http") else None, "status": "ready"}
    db["sources"].append(s); out({"source": s})
if a[:2] == ["source", "wait"]: out({"source_id": a[2], "status": "ready"})
if a[:2] == ["source", "delete"]: out({})
if a[0] == "ask":
    out({"answer": "答案 [1]", "conversation_id": "c1", "references": [{"source_id": "s0", "citation_number": 1, "cited_text": "原文"}]})
print("unknown", a, file=sys.stderr); sys.exit(1)
'''


class ExpandTests(unittest.TestCase):
    def test_expand_dir_filters_and_titles(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a.md").write_text('---\ntitle: "视频标题"\nchannel: "频道"\n---\n正文', encoding="utf-8")
            (root / "b.pdf").write_bytes(b"%PDF")
            (root / "c.mp3").write_bytes(b"x")
            (root / "_log.jsonl").write_text("{}")
            src, skipped = nb.expand([d, "https://youtu.be/bjdBVZa66oU", "https://example.com/x", str(root / "c.mp3")])
            titles = sorted(s["title"] or s["content"] for s in src)
            self.assertEqual(titles, ["b", "https://youtu.be/bjdBVZa66oU", "视频标题-频道"])
            reasons = " ".join(s["reason"] for s in skipped)
            self.assertIn("网页链接", reasons)
            self.assertIn(".mp3", reasons)


class MindMapTests(unittest.TestCase):
    def test_outline(self):
        tree = {"name": "根", "children": [{"name": "甲", "children": [{"name": "甲1"}]}, {"name": "乙"}]}
        self.assertEqual(nb.mindmap_markdown(tree), "# 根\n\n- 甲\n  - 甲1\n- 乙\n")


class FakeCliTests(unittest.TestCase):
    def test_import_then_ask(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cli = root / "fake_nb.py"
            cli.write_text(FAKE_CLI)
            cli.chmod(cli.stat().st_mode | stat.S_IEXEC)
            (root / "docs").mkdir()
            (root / "docs" / "one.md").write_text("hello", encoding="utf-8")
            (root / "docs" / "bad.txt").write_text("x", encoding="utf-8")
            data = root / "data"
            data.mkdir()
            env = dict(os.environ, FAKE_NB_STATE=str(root / "state.json"), DEI_NOTEBOOK_DATA_DIR=str(data))
            cfg = SCRIPTS.parent / "config.json"
            backup = cfg.read_text() if cfg.exists() else None
            cfg.write_text(json.dumps({"notebooklm_cmd": f"{sys.executable} {cli}"}))
            try:
                run = lambda *args: subprocess.run([sys.executable, str(SCRIPTS / "nb.py"), *args],
                                                   capture_output=True, text=True, env=env)
                r = run("import", "--new", "测试库", str(root / "docs"), "https://youtu.be/bjdBVZa66oU")
                summary = json.loads(r.stdout.strip().splitlines()[-1])
                self.assertEqual(summary["ok"], 2, r.stderr)
                self.assertEqual(len(summary["failed"]), 1)
                r2 = run("import", "-n", "nb1234", str(root / "docs"))
                self.assertEqual(json.loads(r2.stdout.strip().splitlines()[-1])["ok"], 1)  # one.md exists
                r3 = run("ask", "-n", "测试库", "这批资料讲了什么？")
                s3 = json.loads(r3.stdout.strip().splitlines()[-1])
                text = Path(s3["results"][0]["file"]).read_text(encoding="utf-8")
                self.assertIn("## 回答\n\n答案\n", text)  # 存档不带 [n] 编号和引用列表
                self.assertNotIn("[1]", text)
                self.assertNotIn("引用", text)
                self.assertEqual(s3["results"][0]["references"], 1)
                qfile = root / "q.md"
                qfile.write_text("# 单元1\n---\n问题一\n---\n问题二\n", encoding="utf-8")
                r4 = run("ask", "-n", "nb1234", "--batch", str(qfile), "--chain", "--dir", "学习路线/单元1")
                s4 = json.loads(r4.stdout.strip().splitlines()[-1])
                self.assertEqual((s4["asked"], s4["ok"]), (2, 2), r4.stderr)
                files = sorted(Path(s4["dir"]).glob("*.md"))
                self.assertEqual(len(files), 2)
                self.assertTrue(json.loads(r4.stdout.strip().splitlines()[-1])["results"][1]["follow_up"])
            finally:
                if backup is None:
                    cfg.unlink()
                else:
                    cfg.write_text(backup)


if __name__ == "__main__":
    unittest.main()
