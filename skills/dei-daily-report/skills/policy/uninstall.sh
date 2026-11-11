#!/bin/bash
# 卸载定时任务。数据目录（data/）保留，确认不需要后可手动删除。

PLIST_LABEL="com.codex.xwlb-analysis"
PLIST_PATH="$HOME/Library/LaunchAgents/${PLIST_LABEL}.plist"

if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" 2>/dev/null || true
    rm -f "$PLIST_PATH"
    echo "已移除每日定时任务。"
else
    echo "未找到定时任务配置。"
fi
echo "数据目录已保留，如确认不再需要可手动删除 data/ 目录。"
