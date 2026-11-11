"""dei-daily-report 各模块共用的数据目录解析。

数据（原始采集、逐字稿、报告、主题状态、日志）不放在 Agent 的 skills 安装目录里，
统一放在用户首次运行时确认的 output_root 下，按模块分子目录：

    <output_root>/政策与商机/   policy
    <output_root>/AI情报/       ai
    <output_root>/抖音监控/     douyin（转写任务日志等状态）
    <output_root>/知乎热榜表达空间/  zhihu（由模块说明直接使用）

优先级：环境变量 DEI_DAILY_DATA_DIR（测试或临时运行） > config.json 的 output_root。
都没有时报错退出，由 Agent 按 SKILL.md「首次配置」询问用户，不静默写进安装目录。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
MODULE_DIRS = {"policy": "政策与商机", "ai": "AI情报", "douyin": "抖音监控", "zhihu": "知乎热榜表达空间"}


def data_dir(module: str) -> Path:
    override = os.environ.get("DEI_DAILY_DATA_DIR")
    if override:
        return Path(override).expanduser()
    config = SKILL_ROOT / "config.json"
    root = ""
    if config.is_file():
        root = json.loads(config.read_text(encoding="utf-8")).get("output_root", "")
    if not root:
        sys.exit(
            f"未配置日报保存位置：请先按 dei-daily-report/SKILL.md「首次配置」询问用户，"
            f"把 output_root 写入 {config}"
        )
    return Path(root).expanduser() / MODULE_DIRS[module]
