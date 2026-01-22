#!/bin/bash

# doc-retriever 性能监控脚本
# 收集和分析文档检索系统的性能指标

MONITOR_LOG=".claude/logs/performance-monitor.log"
STATS_LOG=".claude/logs/performance-stats.log"

# 创建日志目录
mkdir -p .claude/logs

# 获取当前时间戳
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# 收集系统指标
collect_system_metrics() {
    echo "[$TIMESTAMP] === 系统性能指标 ===" >> "$MONITOR_LOG"

    # CPU 使用率
    if command -v top >/dev/null 2>&1; then
        CPU_USAGE=$(top -l 1 -n 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//' 2>/dev/null || echo "N/A")
        echo "[$TIMESTAMP] CPU 使用率: ${CPU_USAGE}%" >> "$MONITOR_LOG"
    fi

    # 内存使用
    if command -v vm_stat >/dev/null 2>&1; then
        MEMORY_INFO=$(vm_stat | head -4 | tail -3)
        echo "[$TIMESTAMP] 内存信息:" >> "$MONITOR_LOG"
        echo "$MEMORY_INFO" | sed "s/^/[$TIMESTAMP]   /" >> "$MONITOR_LOG"
    fi

    # 磁盘使用
    DISK_USAGE=$(df -h . | tail -1 | awk '{print $5}')
    echo "[$TIMESTAMP] 磁盘使用率: $DISK_USAGE" >> "$MONITOR_LOG"
}

# 分析文档检索日志
analyze_retrieval_logs() {
    local retrieval_log=".claude/logs/doc-retrieval.log"

    if [ ! -f "$retrieval_log" ]; then
        echo "[$TIMESTAMP] 检索日志不存在" >> "$MONITOR_LOG"
        return
    fi

    echo "[$TIMESTAMP] === 检索活动分析 ===" >> "$MONITOR_LOG"

    # 今日活动统计
    TODAY=$(date '+%Y-%m-%d')
    TODAY_ACTIVITIES=$(grep "$TODAY" "$retrieval_log" | wc -l)
    echo "[$TIMESTAMP] 今日检索活动: $TODAY_ACTIVITIES 次" >> "$MONITOR_LOG"

    # 最近1小时活动
    HOUR_AGO=$(date -v-1H '+%Y-%m-%d %H:' 2>/dev/null || date -d '1 hour ago' '+%Y-%m-%d %H:' 2>/dev/null || echo "")
    if [ -n "$HOUR_AGO" ]; then
        RECENT_ACTIVITIES=$(grep "$HOUR_AGO" "$retrieval_log" | wc -l)
        echo "[$TIMESTAMP] 最近1小时活动: $RECENT_ACTIVITIES 次" >> "$MONITOR_LOG"
    fi

    # 错误统计
    ERROR_COUNT=$(grep -i "error\|failed\|exception" "$retrieval_log" | wc -l)
    echo "[$TIMESTAMP] 错误事件: $ERROR_COUNT 次" >> "$MONITOR_LOG"

    # 最常用的命令
    echo "[$TIMESTAMP] 最常用命令 (Top 5):" >> "$MONITOR_LOG"
    grep "Command:" "$retrieval_log" | awk -F'Command: ' '{print $2}' | sort | uniq -c | sort -nr | head -5 | sed "s/^/[$TIMESTAMP]   /" >> "$MONITOR_LOG"
}

# 检查文档集状态
check_document_status() {
    echo "[$TIMESTAMP] === 文档集状态 ===" >> "$MONITOR_LOG"

    if [ -d "md_docs" ]; then
        DOC_SETS=$(find md_docs -maxdepth 1 -type d | wc -l)
        echo "[$TIMESTAMP] 文档集数量: $((DOC_SETS - 1))" >> "$MONITOR_LOG"

        # 检查最大的文档集
        LARGEST_SET=$(du -sh md_docs/* 2>/dev/null | sort -hr | head -1)
        echo "[$TIMESTAMP] 最大文档集: $LARGEST_SET" >> "$MONITOR_LOG"

        # 检查最近修改的文档
        RECENT_DOCS=$(find md_docs -name "*.md" -mtime -1 | wc -l)
        echo "[$TIMESTAMP] 24小时内修改的文档: $RECENT_DOCS 个" >> "$MONITOR_LOG"
    else
        echo "[$TIMESTAMP] md_docs 目录不存在" >> "$MONITOR_LOG"
    fi
}

# 生成性能统计报告
generate_stats_report() {
    echo "[$TIMESTAMP] === 性能统计报告 ===" >> "$STATS_LOG"

    # 日志文件大小
    for log_file in .claude/logs/*.log; do
        if [ -f "$log_file" ]; then
            SIZE=$(ls -lh "$log_file" | awk '{print $5}')
            echo "[$TIMESTAMP] $(basename "$log_file"): $SIZE" >> "$STATS_LOG"
        fi
    done

    # 检索成功率（如果有错误日志）
    if [ -f ".claude/logs/doc-retrieval.log" ]; then
        TOTAL_OPERATIONS=$(grep "tool used" .claude/logs/doc-retrieval.log | wc -l)
        ERROR_OPERATIONS=$(grep -i "error\|failed" .claude/logs/doc-retrieval.log | wc -l)

        if [ "$TOTAL_OPERATIONS" -gt 0 ]; then
            SUCCESS_RATE=$(echo "scale=2; (($TOTAL_OPERATIONS - $ERROR_OPERATIONS) * 100) / $TOTAL_OPERATIONS" | bc 2>/dev/null || echo "N/A")
            echo "[$TIMESTAMP] 操作成功率: ${SUCCESS_RATE}%" >> "$STATS_LOG"
        fi
    fi
}

# 清理旧日志
cleanup_old_logs() {
    # 清理超过7天的监控日志
    find .claude/logs -name "*.log" -mtime +7 -exec rm {} \; 2>/dev/null

    # 压缩大型日志文件
    for log_file in .claude/logs/*.log; do
        if [ -f "$log_file" ] && [ $(stat -f%z "$log_file" 2>/dev/null || stat -c%s "$log_file" 2>/dev/null || echo 0) -gt 5242880 ]; then
            # 文件大于 5MB，保留最后1000行
            tail -n 1000 "$log_file" > "${log_file}.tmp"
            mv "${log_file}.tmp" "$log_file"
            echo "[$TIMESTAMP] 压缩日志文件: $(basename "$log_file")" >> "$MONITOR_LOG"
        fi
    done
}

# 主执行流程
main() {
    echo "🔍 开始性能监控..."

    collect_system_metrics
    analyze_retrieval_logs
    check_document_status
    generate_stats_report
    cleanup_old_logs

    echo "[$TIMESTAMP] 性能监控完成" >> "$MONITOR_LOG"
    echo "✅ 性能监控完成，日志已保存到 $MONITOR_LOG"
}

# 如果直接执行脚本
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    main "$@"
fi