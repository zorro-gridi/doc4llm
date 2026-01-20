#!/bin/bash

# 日志模块修复脚本
# 检查并修复 .claude/logs 模块的问题

echo "🔧 开始检查和修复日志模块..."
echo "=================================="

# 创建日志目录
echo "1. 确保日志目录存在..."
mkdir -p .claude/logs
echo "   ✅ 日志目录已创建"

# 检查并修复日志文件权限
echo "2. 检查日志文件权限..."
LOG_FILES=(
    ".claude/logs/doc-retrieval.log"
    ".claude/logs/security-validation.log"
    ".claude/logs/performance-monitor.log"
    ".claude/logs/doc-session-stats.log"
)

for log_file in "${LOG_FILES[@]}"; do
    if [ ! -f "$log_file" ]; then
        touch "$log_file"
        echo "   ✅ 创建 $log_file"
    fi
    chmod 644 "$log_file"
done

# 检查日志脚本权限
echo "3. 检查日志脚本权限..."
LOG_SCRIPTS=(
    ".claude/scripts/log-retrieval.sh"
    ".claude/scripts/doc-retriever-monitor.sh"
    ".claude/scripts/performance-optimizer.sh"
)

for script in "${LOG_SCRIPTS[@]}"; do
    if [ -f "$script" ]; then
        chmod +x "$script"
        echo "   ✅ $script 权限已修复"
    else
        echo "   ⚠️  $script 不存在"
    fi
done

# 测试日志记录功能
echo "4. 测试日志记录功能..."
TEST_INPUT='{"tool_name": "Bash", "tool_input": {"command": "echo test"}}'
if echo "$TEST_INPUT" | .claude/scripts/log-retrieval.sh 2>/dev/null; then
    echo "   ✅ 日志记录功能正常"
else
    echo "   ❌ 日志记录功能异常"
fi

# 检查日志文件大小和轮转
echo "5. 检查日志文件状态..."
for log_file in "${LOG_FILES[@]}"; do
    if [ -f "$log_file" ]; then
        SIZE=$(wc -l < "$log_file")
        FILE_SIZE=$(ls -lh "$log_file" | awk '{print $5}')
        echo "   📄 $log_file: $SIZE 行, $FILE_SIZE"
        
        # 如果日志文件过大，进行轮转
        if [ "$SIZE" -gt 2000 ]; then
            echo "   🔄 轮转大日志文件: $log_file"
            tail -n 1000 "$log_file" > "${log_file}.tmp" && mv "${log_file}.tmp" "$log_file"
        fi
    fi
done

# 清理过期的诊断日志
echo "6. 清理过期日志..."
find .claude/logs -name "diagnostic-*.log" -mtime +7 -delete 2>/dev/null
find .claude/logs -name "optimization-*.log" -mtime +7 -delete 2>/dev/null
echo "   ✅ 过期日志已清理"

# 检查磁盘空间
echo "7. 检查磁盘空间..."
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 95 ]; then
    echo "   ⚠️  磁盘空间不足: ${DISK_USAGE}%"
    echo "   🧹 执行日志清理..."
    
    # 压缩旧日志
    find .claude/logs -name "*.log" -mtime +3 -exec gzip {} \;
    echo "   ✅ 旧日志已压缩"
else
    echo "   ✅ 磁盘空间充足: ${DISK_USAGE}%"
fi

# 验证核心功能
echo "8. 验证核心功能..."

# 测试 doc4llm 包
if python -c "import doc4llm; from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor" 2>/dev/null; then
    echo "   ✅ doc4llm 包和核心模块可用"
else
    echo "   ❌ doc4llm 包或核心模块不可用"
    echo "   🔧 尝试重新安装..."
    pip install -e . 2>/dev/null || echo "   ❌ 安装失败"
fi

# 测试文档集
if [ -d "md_docs" ]; then
    DOC_SETS=$(find md_docs -maxdepth 1 -type d | grep -v "^md_docs$" | wc -l)
    echo "   ✅ 发现 $DOC_SETS 个文档集"
else
    echo "   ⚠️  md_docs 目录不存在"
fi

echo ""
echo "🎉 日志模块检查和修复完成！"
echo "=================================="

# 生成状态报告
REPORT_FILE=".claude/logs/module-status-$(date +%Y%m%d-%H%M%S).log"
{
    echo "=== 日志模块状态报告 ==="
    echo "时间: $(date)"
    echo "磁盘使用: ${DISK_USAGE}%"
    echo "日志文件数量: $(ls -1 .claude/logs/*.log 2>/dev/null | wc -l)"
    echo "doc4llm 状态: $(python -c "import doc4llm; print('OK')" 2>/dev/null || echo 'ERROR')"
    echo "文档集数量: $DOC_SETS"
    echo "========================"
} > "$REPORT_FILE"

echo "📊 状态报告已保存到: $REPORT_FILE"