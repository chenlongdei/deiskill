"""dei-capture 的配置与数据目录。

采集结果不放在 Agent 的 skills 安装目录里，统一放在用户首次运行时确认的 output_root 下：

    <output_root>/YouTube/搜索/     关键词搜索清单
    <output_root>/YouTube/频道/     频道视频清单（增量合并）
    <output_root>/YouTube/逐字稿/   单视频逐字稿（Markdown，带 frontmatter）

优先级：环境变量 DEI_CAPTURE_DATA_DIR（测试或临时运行） > config.json 的 output_root。
都没有时报错退出，由 Agent 按 SKILL.md「首次配置」询问用户。
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
CONFIG = SKILL_ROOT / "config.json"
MODULE_DIRS = {"youtube": "YouTube"}


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
        sys.exit(
            f"未配置采集结果保存位置：请先按 SKILL.md「首次配置」询问用户，把 output_root 写入 {CONFIG}"
        )
    path = Path(root).expanduser()
    if not path.is_dir():
        sys.exit(f"保存位置不存在：{path}。请用户确认是新建、改路径，还是本次跳过（不静默新建）。")
    return path / MODULE_DIRS[module]


def slug(text: str, limit: int = 40) -> str:
    text = re.sub(r"[\\/:*?\"<>|\n\r\t]+", " ", text).strip()
    text = re.sub(r"\s+", "-", text)
    return text[:limit].rstrip("-.") or "untitled"
