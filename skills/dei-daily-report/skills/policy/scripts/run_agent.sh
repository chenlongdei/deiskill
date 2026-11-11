#!/bin/bash
# Agent 适配层：调用任意支持"非交互执行提示词"的 AI agent CLI 完成分析。
# 用法: run_agent.sh   （提示词从 stdin 读入）
#
# 解析顺序：
# 1. 本目录 agent.conf 中自定义 AGENT_CMD 模板（最高优先级）
# 2. 自动探测 claude CLI（Claude Code）
# 3. 自动探测 codex CLI
#
# 协议约定：本脚本会 cd 到 skill 根目录再执行命令，提示词通过 stdin 传入。
# 只要你的 agent CLI 支持「从 stdin 读任务 + 在当前目录读写文件」即可接入。

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SKILL_DIR"

if [ -f agent.conf ]; then
    # shellcheck disable=SC1091
    source agent.conf
    if [ -z "${AGENT_CMD:-}" ]; then
        echo "agent.conf 存在但未设置 AGENT_CMD" >&2
        exit 1
    fi
    eval "$AGENT_CMD"
    exit 0
fi

if command -v claude >/dev/null 2>&1; then
    exec claude -p --permission-mode acceptEdits
fi

if command -v codex >/dev/null 2>&1; then
    exec codex exec --sandbox workspace-write --skip-git-repo-check -
fi

cat >&2 <<'EOF'
未找到可用的 AI agent CLI。

请在本目录创建 agent.conf，写入一行命令模板，例如：

  # Codex（默认自动探测，通常无需配置）
  AGENT_CMD='codex exec --sandbox workspace-write --skip-git-repo-check -'

  # Claude Code
  AGENT_CMD='claude -p --permission-mode acceptEdits'

  # workbuddy 或其他 agent：请按其文档填写无头（非交互）调用命令，
  # 要求：能从 stdin 读取提示词，并允许在当前目录读写文件。
  AGENT_CMD='your-agent-cli --headless -'

EOF
exit 1
