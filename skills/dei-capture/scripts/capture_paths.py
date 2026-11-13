"""dei-capture 的配置与数据目录。

采集结果放在 dei 工作区的 02_采集/ 下（工作区见 dei_workspace.py），不放进 Agent 的 skills 安装目录：

    02_采集/YouTube/搜索/<YYYY-MM-DD_HHMM_关键词>/   关键词搜索清单
    02_采集/YouTube/频道/<频道名>/                   频道视频清单（增量合并）
    02_采集/YouTube/逐字稿/                          单视频逐字稿（Markdown，带 frontmatter）
    02_采集/抖音/博主/<博主名>/                      逐字稿、作品数据、文案与数据、监控更新
    02_采集/抖音/关键词/                             关键词巡检（见 references/douyin.md）
    02_采集/转写/                                    统一转写入口的产出

优先级：环境变量 DEI_CAPTURE_DATA_DIR（测试或临时运行） > config.json 的 output_root（旧版单独指定）
> dei 工作区。都没有时报错退出，由 Agent 按 SKILL.md「首次配置」询问用户。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(os.environ.get("DEI_CAPTURE_CONFIG") or SKILL_ROOT / "config.json")  # 环境变量供测试用
MODULE_DIRS = {"youtube": "YouTube", "douyin": "抖音", "transcribe": "转写"}


def load_config() -> dict:
    if CONFIG.is_file():
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    return {}


def section(name: str) -> dict:
    value = load_config().get(name) or {}
    return value if isinstance(value, dict) else {}


def data_dir(module: str) -> Path:
    override = os.environ.get("DEI_CAPTURE_DATA_DIR")
    if override:
        return Path(override).expanduser() / MODULE_DIRS[module]
    root = load_config().get("output_root", "")
    if not root:
        import dei_workspace
        return dei_workspace.stage("capture") / MODULE_DIRS[module]
    path = Path(root).expanduser()
    if not path.is_dir():
        sys.exit(f"保存位置不存在：{path}。请用户确认是新建、改路径，还是本次跳过（不静默新建）。")
    return path / MODULE_DIRS[module]


def slug(text: str, limit: int = 40) -> str:
    text = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", text).strip()
    text = re.sub(r"\s+", "-", text)
    return text[:limit].rstrip("-.") or "untitled"
