#!/bin/bash

# doc-retriever 检索活动日志记录脚本
# 用于记录文档检索操作的详细信息

# 创建日志目录（如果不存在）
mkdir -p .claude/logs

# 日志文件路径
LOG_FILE=".claude/logs/doc-retrieval.log"
ERROR_LOG=".claude/logs/doc-retrieval-errors.log"

# 获取当前时间戳
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 从 stdin 读取 hook 输入（JSON 格式）
INPUT=$(cat)

# 提取工具输入信息
TOOL_INPUT=$(echo "$INPUT" | jq -r '.tool_input // empty' 2>/dev/null || echo "N/A")
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "Bash")

# 记录检索活动
echo "[$TIMESTAMP] doc-retriever: $TOOL_NAME tool used" >> "$LOG_FILE"

# 如果是 Bash 工具，记录命令详情
if [ "$TOOL_NAME" = "Bash" ]; then
    COMMAND=$(echo "$TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null || echo "N/A")
    echo "[$TIMESTAMP] Command: $COMMAND" >> "$LOG_FILE"
    
    # 检查是否是文档检索相关命令
    if echo "$COMMAND" | grep -qE "(extract_md_doc|MarkdownDocExtractor|md_docs)"; then
        echo "[$TIMESTAMP] Document extraction detected: $COMMAND" >> "$LOG_FILE"
    fi
fi

# 记录会话信息（如果可用）
if [ -n "${CLAUDE_SESSION_ID:-}" ]; then
    echo "[$TIMESTAMP] Session: $CLAUDE_SESSION_ID" >> "$LOG_FILE"
fi

# 日志轮转（保持最近1000行）
if [ -f "$LOG_FILE" ] && [ $(wc -l < "$LOG_FILE") -gt 1000 ]; then
    tail -n 800 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

exit 0