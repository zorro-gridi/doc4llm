#!/bin/bash

# doc-retriever 会话清理脚本 - 增强版
# 在子代理完成时执行清理操作并记录详细统计

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SESSION_ID="${CLAUDE_SESSION_ID:-unknown}"
SESSION_STATUS="${1:-completed}"  # completed, failed, interrupted

# 记录会话结束
echo "[$TIMESTAMP] doc-retriever session ended: $SESSION_ID (status: $SESSION_STATUS)" >> .claude/logs/doc-retrieval.log

# 清理临时文件（如果有）
TEMP_PATTERNS=(
    "/tmp/doc-retriever-*"
    "/tmp/md-doc-*"
    ".claude/temp/doc-*"
)

CLEANED_FILES=0
for pattern in "${TEMP_PATTERNS[@]}"; do
    if ls $pattern 2>/dev/null; then
        rm -f $pattern
        CLEANED_FILES=$((CLEANED_FILES + 1))
        echo "[$TIMESTAMP] 清理临时文件: $pattern" >> .claude/logs/doc-retrieval.log
    fi
done

# 压缩旧日志（如果日志文件过大）
LOG_FILE=".claude/logs/doc-retrieval.log"
if [ -f "$LOG_FILE" ] && [ $(stat -f%z "$LOG_FILE" 2>/dev/null || stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -gt 1048576 ]; then
    # 文件大于 1MB，进行压缩
    tail -n 500 "$LOG_FILE" > "${LOG_FILE}.tmp"
    mv "${LOG_FILE}.tmp" "$LOG_FILE"
    echo "[$TIMESTAMP] 日志文件已压缩" >> "$LOG_FILE"
fi

# 生成详细会话统计
if [ -f "$LOG_FILE" ]; then
    # 统计操作数量
    OPERATION_COUNT=$(grep -c "doc-retriever:" "$LOG_FILE" 2>/dev/null || echo "0")
    ERROR_COUNT=$(grep -c "ERROR\|FAILED" "$LOG_FILE" 2>/dev/null || echo "0")
    EXTRACTION_COUNT=$(grep -c "Document extraction detected" "$LOG_FILE" 2>/dev/null || echo "0")
    
    # 计算成功率
    if [ "$OPERATION_COUNT" -gt 0 ]; then
        SUCCESS_RATE=$(( (OPERATION_COUNT - ERROR_COUNT) * 100 / OPERATION_COUNT ))
    else
        SUCCESS_RATE=0
    fi
    
    # 记录详细统计
    echo "[$TIMESTAMP] 会话统计: $SESSION_ID | 状态: $SESSION_STATUS | 操作: $OPERATION_COUNT | 提取: $EXTRACTION_COUNT | 错误: $ERROR_COUNT | 成功率: ${SUCCESS_RATE}% | 清理文件: $CLEANED_FILES" >> .claude/logs/doc-session-stats.log
    
    # 如果会话失败，记录到错误日志
    if [ "$SESSION_STATUS" = "failed" ]; then
        echo "[$TIMESTAMP] SESSION FAILURE: $SESSION_ID - 操作数: $OPERATION_COUNT, 错误数: $ERROR_COUNT" >> .claude/logs/error.log
    fi
fi

exit 0