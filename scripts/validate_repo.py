#!/usr/bin/env python3
"""deiskill 结构校验。规则见 docs/skill-spec.md；它只检查结构，不能代替真实任务测试。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^dei(-[a-z0-9]+)*$")
LAYERS = {"router", "input", "process", "output"}
LOCAL_PATH_RE = re.compile(r"(?<![\w.])/(?:Users|home)/[\w.-]+/|(?<![\w.])/Volumes/[^/\s]")
PATH_CHECK_EXEMPT = {Path("scripts/validate_repo.py"), Path("docs/skill-spec.md")}
TEXT_SUFFIXES = {".md", ".json", ".py", ".sh", ".yaml", ".yml", ".js", ".txt", ".example", ".ps1"}
# 允许叶子 Skill 点名的工具依赖：{"点名方": {"被点名的 Skill"}}
NAMING_ALLOWLIST: dict[str, set[str]] = {}


def frontmatter(text: str) -> str:
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError("缺少 YAML frontmatter")
    return match.group(1)


def field(block: str, key: str) -> str | None:
    match = re.search(rf"^{key}:[ \t]*(.*)$", block, re.MULTILINE)
    return match.group(1).strip().strip("\"'") if match else None


def handoff(block: str) -> list[str] | None:
    match = re.search(r"^  dei-handoff: \|\n((?:    .*\n?)+)", block, re.MULTILINE)
    if not match:
        return None
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def check_handoff(name: str, lines: list[str] | None, errors: list[str]) -> None:
    if lines is None:
        errors.append(f"{name}: 缺少 metadata.dei-handoff")
        return
    if not lines[-1].startswith("- 不交出："):
        errors.append(f"{name}: dei-handoff 最后一行须以「- 不交出：」开头")
    body = lines[:-1]
    if not body:
        errors.append(f"{name}: dei-handoff 至少需要一条「接手 → 交出」")
    for line in body:
        if not line.startswith("- ") or "→" not in line:
            errors.append(f"{name}: dei-handoff 行格式应为「- 接手 → 交出」：{line}")


def main() -> int:
    errors: list[str] = []
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    externals = json.loads((ROOT / "external.json").read_text(encoding="utf-8"))["externals"]
    names = [item["name"] for item in catalog["skills"]]
    all_names = set(names) | {e["name"] for e in externals if e["kind"] == "skill"}

    if len(names) != len(set(names)):
        errors.append("catalog.json 有重复名称")
    on_disk = {p.name for p in SKILLS.iterdir() if p.is_dir()} if SKILLS.is_dir() else set()
    for extra in sorted(on_disk - set(names)):
        errors.append(f"skills/{extra} 未登记在 catalog.json")

    for item in catalog["skills"]:
        name = item["name"]
        skill_dir = SKILLS / name
        if not NAME_RE.fullmatch(name):
            errors.append(f"{name}: 名称须为 dei- 前缀的小写 kebab-case")
        if item.get("layer") not in LAYERS:
            errors.append(f"{name}: layer 须为 {sorted(LAYERS)} 之一")
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            errors.append(f"{name}: 缺少 skills/{name}/SKILL.md")
            continue
        text = skill_file.read_text(encoding="utf-8")
        try:
            block = frontmatter(text)
        except ValueError as exc:
            errors.append(f"{name}: {exc}")
            continue
        if field(block, "name") != name:
            errors.append(f"{name}: frontmatter name 为 {field(block, 'name')!r}")
        if not field(block, "description"):
            errors.append(f"{name}: 缺少 description")
        if item.get("layer") != "router":
            check_handoff(name, handoff(block), errors)
            others = all_names - {name} - NAMING_ALLOWLIST.get(name, set())
            for other in sorted(others):
                if re.search(rf"(?<![\w-]){re.escape(other)}(?![\w-])", text.split("\n---\n", 1)[1]):
                    errors.append(f"{name}: 叶子 Skill 正文点名了 {other}（工具依赖请登记 NAMING_ALLOWLIST）")
        ui = skill_dir / "agents" / "openai.yaml"
        if not ui.is_file():
            errors.append(f"{name}: 缺少 agents/openai.yaml")
        elif f"${name}" not in ui.read_text(encoding="utf-8"):
            errors.append(f"{name}: agents/openai.yaml 的 default_prompt 须包含 ${name}")

    for item in externals:
        if item["kind"] in {"vendor", "manual"}:
            if item["owner"] not in names:
                errors.append(f"external {item['name']}: owner {item['owner']} 不是自有 Skill")
            elif (SKILLS / item["owner"] / item["install_into"]).exists():
                errors.append(f"external {item['name']}: 上游内容不得提交到 skills/{item['owner']}/{item['install_into']}")

    for path in sorted(ROOT.rglob("*")):
        if ".git" in path.parts or not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if path.suffix in TEXT_SUFFIXES or path.name.endswith(".example"):
            text = path.read_text(encoding="utf-8", errors="ignore")
            if relative not in PATH_CHECK_EXEMPT and LOCAL_PATH_RE.search(text):
                errors.append(f"{relative}: 含本机绝对路径")
        if path.suffix == ".py":
            try:
                compile(path.read_text(encoding="utf-8"), str(relative), "exec")
            except SyntaxError as exc:
                errors.append(f"{relative}: Python 语法错误 第 {exc.lineno} 行 {exc.msg}")

    if errors:
        print("校验未通过：")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"校验通过：{len(names)} 个自有 Skill，{len(externals)} 个上游依赖。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
