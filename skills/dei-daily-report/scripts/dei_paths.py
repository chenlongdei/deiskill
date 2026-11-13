"""dei-daily-report 各模块共用的数据目录解析。

数据放在 dei 工作区的 03_日报/ 下（工作区见 dei_workspace.py），不放进 Agent 的 skills 安装目录：

    03_日报/综合/YYYY/YYYY-MM-DD_HHMM/   每次综合运行：综合日报.md、对外日报、成品/、原文存档/、_原始数据/运行记录.json
    03_日报/政策与商机/                  policy：逐字稿/YYYY/MM/、报告/YYYY/、原件/YYYY/YYYY-MM-DD/、修订/、主题状态.json
    03_日报/AI情报/                      ai：原始采集/YYYY/YYYY-MM-DD/、线索/YYYY/MM/、报告/YYYY/、修订/、主题状态.json
    03_日报/知乎热榜/YYYY/YYYY-MM-DD_HHMM/   zhihu：报告.md、_原始数据/
    03_日报/对外日报期号.json
    99_系统/日志/<模块>/                 抓取日志、运行锁

模块内部的子目录统一用中文，名称只在这里定义（SUBDIRS），脚本和模块说明都按这里来。

优先级：环境变量 DEI_DAILY_DATA_DIR（测试或临时运行，直接作为模块目录，日志放在其下 日志/）
> config.json 的 output_root（旧版单独指定）> dei 工作区。
都没有时报错退出，由 Agent 按 SKILL.md「首次配置」询问用户，不静默写进安装目录。
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dei_workspace  # noqa: E402

MODULE_DIRS = {"policy": "政策与商机", "ai": "AI情报", "zhihu": "知乎热榜", "combined": "综合"}
SUBDIRS = {
    "transcripts": "逐字稿",
    "reports": "报告",
    "revisions": "修订",
    "feeds": "线索",
    "logs": "日志",
    "topics": "主题状态.json",
    "sources": {"policy": "原件", "ai": "原始采集"},
}


def _legacy_root() -> str:
    config = SKILL_ROOT / "config.json"
    if config.is_file():
        return json.loads(config.read_text(encoding="utf-8")).get("output_root", "") or ""
    return ""


def daily_root() -> Path:
    """03_日报/（或旧版 output_root）。"""
    legacy = _legacy_root()
    if legacy:
        return Path(legacy).expanduser()
    return dei_workspace.stage("daily")


def data_dir(module: str) -> Path:
    override = os.environ.get("DEI_DAILY_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return daily_root() / MODULE_DIRS[module]


def sub(module: str, key: str) -> str:
    name = SUBDIRS[key]
    return name[module] if isinstance(name, dict) else name


def path(module: str, key: str) -> Path:
    """模块目录下的某个子目录或文件，例如 path("policy", "reports")。日志见 log_dir。"""
    if key == "logs":
        return log_dir(module)
    return data_dir(module) / sub(module, key)


def log_dir(module: str) -> Path:
    """日志和运行锁：99_系统/日志/<模块>/；测试或旧版配置时放在模块目录的 日志/。"""
    if os.environ.get("DEI_DAILY_DATA_DIR") or _legacy_root():
        d = data_dir(module) / SUBDIRS["logs"]
    else:
        d = dei_workspace.system("日志") / MODULE_DIRS[module]
    d.mkdir(parents=True, exist_ok=True)
    return d


def report_path(module: str, day) -> Path:
    """报告按年分一层：报告/YYYY/YYYY-MM-DD_分析报告.md。"""
    day = str(day)
    return path(module, "reports") / day[:4] / f"{day}_分析报告.md"


def sources_dir(module: str, day) -> Path:
    """原件（policy）或原始采集（ai）按年分一层：<子目录>/YYYY/YYYY-MM-DD/。"""
    day = str(day)
    return path(module, "sources") / day[:4] / day


def new_run(module: str = "combined") -> Path:
    """新建一次运行的批次目录：综合/YYYY/YYYY-MM-DD_HHMM/ 或 知乎热榜/YYYY/YYYY-MM-DD_HHMM/，带 _原始数据/。"""
    run = dei_workspace.batch_dir(daily_root() / MODULE_DIRS[module], yearly=True)
    dei_workspace.raw_dir(run)
    return run


def main(argv: list[str]) -> int:
    """命令行：
    python3 scripts/dei_paths.py [模块 ...]          打印各目录（JSON）
    python3 scripts/dei_paths.py new-run [combined|zhihu]   新建本次运行目录并打印路径
    """
    if argv[:1] == ["new-run"]:
        print(new_run(argv[1] if len(argv) > 1 else "combined"))
        return 0
    mods = argv or list(MODULE_DIRS)
    out = {"daily_root": str(daily_root())}
    for m in mods:
        out[m] = {"dir": str(data_dir(m))}
        if m in ("policy", "ai"):
            keys = ["reports", "sources", "revisions", "topics", "logs"] + (["transcripts"] if m == "policy" else ["feeds"])
            out[m].update({k: str(path(m, k)) for k in keys})
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
