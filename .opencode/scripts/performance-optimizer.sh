#!/bin/bash

# doc-retriever 性能优化脚本
# 实时监控和优化系统性能

set -e

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE=".claude/logs/performance-monitor.log"

echo "[$TIMESTAMP] === 性能优化开始 ===" >> "$LOG_FILE"

# 1. 系统资源检查
check_system_resources() {
    echo "[$TIMESTAMP] 检查系统资源..." >> "$LOG_FILE"
    
    # CPU 使用率
    if command -v top >/dev/null 2>&1; then
        CPU_USAGE=$(top -l 1 -s 0 | grep "CPU usage" | awk '{print $3}' | sed 's/%//' 2>/dev/null || echo "0")
        echo "[$TIMESTAMP] CPU 使用率: ${CPU_USAGE}%" >> "$LOG_FILE"
        
        if [ "${CPU_USAGE%.*}" -gt 80 ]; then
            echo "[$TIMESTAMP] ⚠️  CPU 使用率过高: ${CPU_USAGE}%" >> "$LOG_FILE"
        fi
    fi
    
    # 内存使用情况
    if command -v vm_stat >/dev/null 2>&1; then
        FREE_PAGES=$(vm_stat | grep "Pages free" | awk '{print $3}' | sed 's/\.//')
        echo "[$TIMESTAMP] 可用内存页: $FREE_PAGES" >> "$LOG_FILE"
    fi
    
    # 磁盘使用率
    DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    echo "[$TIMESTAMP] 磁盘使用率: ${DISK_USAGE}%" >> "$LOG_FILE"
    
    if [ "$DISK_USAGE" -gt 90 ]; then
        echo "[$TIMESTAMP] ⚠️  磁盘空间不足: ${DISK_USAGE}%" >> "$LOG_FILE"
        return 1
    fi
    
    return 0
}

# 2. 文档缓存优化
optimize_doc_cache() {
    echo "[$TIMESTAMP] 优化文档缓存..." >> "$LOG_FILE"
    
    # 清理过期的临时文件
    find /tmp -name "doc-retriever-*" -mtime +1 -delete 2>/dev/null || true
    find /tmp -name "md-doc-*" -mtime +1 -delete 2>/dev/null || true
    
    # 统计文档集大小
    if [ -d "md_docs" ]; then
        DOC_SIZE=$(du -sh md_docs 2>/dev/null | awk '{print $1}')
        echo "[$TIMESTAMP] 文档集大小: $DOC_SIZE" >> "$LOG_FILE"
    fi
}

# 3. 日志文件管理
manage_log_files() {
    echo "[$TIMESTAMP] 管理日志文件..." >> "$LOG_FILE"
    
    # 压缩大日志文件
    for log in .claude/logs/*.log; do
        if [ -f "$log" ] && [ $(stat -f%z "$log" 2>/dev/null || stat -c%s "$log" 2>/dev/null || echo 0) -gt 1048576 ]; then
            echo "[$TIMESTAMP] 压缩日志文件: $log" >> "$LOG_FILE"
            tail -n 1000 "$log" > "${log}.tmp"
            mv "${log}.tmp" "$log"
        fi
    done
    
    # 删除过期日志
    find .claude/logs -name "diagnostic-*.log" -mtime +7 -delete 2>/dev/null || true
}

# 4. Python 环境优化
optimize_python_env() {
    echo "[$TIMESTAMP] 优化 Python 环境..." >> "$LOG_FILE"
    
    # 清理 Python 缓存
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    # 验证 doc4llm 包
    if python -c "import doc4llm" 2>/dev/null; then
        echo "[$TIMESTAMP] ✅ doc4llm 包可用" >> "$LOG_FILE"
    else
        echo "[$TIMESTAMP] ❌ doc4llm 包不可用，尝试重新安装..." >> "$LOG_FILE"
        pip install -e . --quiet 2>/dev/null || true
    fi
}

# 5. 性能基准测试
run_performance_benchmark() {
    echo "[$TIMESTAMP] 运行性能基准测试..." >> "$LOG_FILE"
    
    # 文档读取测试
    if [ -d "md_docs" ]; then
        START_TIME=$(date +%s.%N)
        ls -la md_docs/ >/dev/null 2>&1
        END_TIME=$(date +%s.%N)
        DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "0")
        echo "[$TIMESTAMP] 文档列表测试: ${DURATION}s" >> "$LOG_FILE"
    fi
    
    # Python API 测试
    START_TIME=$(date +%s.%N)
    python -c "
try:
    from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
    extractor = MarkdownDocExtractor()
    print('API 测试通过')
except Exception as e:
    print(f'API 测试失败: {e}')
" 2>/dev/null
    END_TIME=$(date +%s.%N)
    DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "0")
    echo "[$TIMESTAMP] Python API 测试: ${DURATION}s" >> "$LOG_FILE"
}

# 执行优化步骤
main() {
    if ! check_system_resources; then
        echo "[$TIMESTAMP] 系统资源不足，执行清理..." >> "$LOG_FILE"
        optimize_doc_cache
        manage_log_files
    fi
    
    optimize_python_env
    run_performance_benchmark
    
    echo "[$TIMESTAMP] === 性能优化完成 ===" >> "$LOG_FILE"
}

# 运行主函数
main

exit 0