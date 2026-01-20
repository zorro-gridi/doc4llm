#!/bin/bash

# 日志模块健康检查脚本
# 定期检查日志系统的健康状态

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
HEALTH_LOG=".claude/logs/logs-health.log"

# 创建日志目录
mkdir -p .claude/logs

echo "[$TIMESTAMP] === 日志模块健康检查开始 ===" >> "$HEALTH_LOG"

# 1. 检查日志目录权限
if [ -w ".claude/logs" ]; then
    echo "[$TIMESTAMP] ✅ 日志目录可写" >> "$HEALTH_LOG"
else
    echo "[$TIMESTAMP] ❌ 日志目录不可写" >> "$HEALTH_LOG"
    chmod 755 .claude/logs
fi

# 2. 检查关键日志文件
CRITICAL_LOGS=(
    "doc-retrieval.log"
    "security-validation.log"
    "performance-monitor.log"
)

for log_name in "${CRITICAL_LOGS[@]}"; do
    log_path=".claude/logs/$log_name"
    
    if [ -f "$log_path" ]; then
        # 检查文件权限
        if [ -w "$log_path" ]; then
            echo "[$TIMESTAMP] ✅ $log_name 可写" >> "$HEALTH_LOG"
        else
            echo "[$TIMESTAMP] ⚠️  $log_name 权限问题，正在修复" >> "$HEALTH_LOG"
            chmod 644 "$log_path"
        fi
        
        # 检查文件大小
        size=$(stat -f%z "$log_path" 2>/dev/null || stat -c%s "$log_path" 2>/dev/null || echo 0)
        if [ "$size" -gt 10485760 ]; then  # 10MB
            echo "[$TIMESTAMP] ⚠️  $log_name 文件过大 (${size} bytes)，执行轮转" >> "$HEALTH_LOG"
            tail -n 500 "$log_path" > "${log_path}.tmp" && mv "${log_path}.tmp" "$log_path"
        fi
    else
        echo "[$TIMESTAMP] ⚠️  $log_name 不存在，正在创建" >> "$HEALTH_LOG"
        touch "$log_path"
        chmod 644 "$log_path"
    fi
done

# 3. 检查日志脚本
LOG_SCRIPTS=(
    ".claude/scripts/log-retrieval.sh"
    ".claude/scripts/validate-doc-operation.sh"
)

for script in "${LOG_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        if [ -x "$script" ]; then
            echo "[$TIMESTAMP] ✅ $(basename "$script") 可执行" >> "$HEALTH_LOG"
        else
            echo "[$TIMESTAMP] ⚠️  $(basename "$script") 权限问题，正在修复" >> "$HEALTH_LOG"
            chmod +x "$script"
        fi
    else
        echo "[$TIMESTAMP] ❌ $(basename "$script") 不存在" >> "$HEALTH_LOG"
    fi
done

# 4. 测试日志记录功能
test_input='{"tool_name": "Test", "tool_input": {"command": "echo health-check"}}'
if echo "$test_input" | .claude/scripts/log-retrieval.sh 2>/dev/null; then
    echo "[$TIMESTAMP] ✅ 日志记录功能正常" >> "$HEALTH_LOG"
else
    echo "[$TIMESTAMP] ❌ 日志记录功能异常" >> "$HEALTH_LOG"
fi

# 5. 检查磁盘空间
disk_usage=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$disk_usage" -gt 90 ]; then
    echo "[$TIMESTAMP] ⚠️  磁盘空间不足: ${disk_usage}%" >> "$HEALTH_LOG"
    
    # 清理压缩日志
    find .claude/logs -name "*.gz" -mtime +7 -delete 2>/dev/null
    find .claude/logs -name "diagnostic-*.log" -mtime +3 -delete 2>/dev/null
    find .claude/logs -name "optimization-*.log" -mtime +3 -delete 2>/dev/null
    
    echo "[$TIMESTAMP] 🧹 执行了日志清理" >> "$HEALTH_LOG"
else
    echo "[$TIMESTAMP] ✅ 磁盘空间充足: ${disk_usage}%" >> "$HEALTH_LOG"
fi

# 6. 检查日志活动
recent_activity=$(find .claude/logs -name "*.log" -mmin -60 | wc -l)
if [ "$recent_activity" -gt 0 ]; then
    echo "[$TIMESTAMP] ✅ 最近1小时有日志活动" >> "$HEALTH_LOG"
else
    echo "[$TIMESTAMP] ⚠️  最近1小时无日志活动" >> "$HEALTH_LOG"
fi

# 7. 生成健康状态摘要
{
    echo ""
    echo "=== 健康状态摘要 ==="
    echo "检查时间: $TIMESTAMP"
    echo "磁盘使用: ${disk_usage}%"
    echo "日志文件数: $(ls -1 .claude/logs/*.log 2>/dev/null | wc -l)"
    echo "最近活动: $recent_activity 个文件"
    echo "==================="
} >> "$HEALTH_LOG"

echo "[$TIMESTAMP] === 日志模块健康检查完成 ===" >> "$HEALTH_LOG"

# 保持健康日志文件大小
if [ -f "$HEALTH_LOG" ] && [ $(wc -l < "$HEALTH_LOG") -gt 200 ]; then
    tail -n 150 "$HEALTH_LOG" > "${HEALTH_LOG}.tmp" && mv "${HEALTH_LOG}.tmp" "$HEALTH_LOG"
fi

exit 0