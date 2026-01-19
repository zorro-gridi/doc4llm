#!/bin/bash

# doc-retriever 快速修复脚本 - k8s 环境版本
# 解决最关键的问题，适用于紧急情况

set -e

echo "🚀 doc-retriever 快速修复开始 (k8s 环境)..."

# 激活 k8s conda 环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate k8s
echo "已激活 conda k8s 环境"

# 1. 修复 doc4llm 包（最关键）
echo "1. 检查 doc4llm 包..."
if ! python -c "import doc4llm" 2>/dev/null; then
    echo "   重新安装 doc4llm 包..."
    pip install -e . --quiet
    if python -c "import doc4llm" 2>/dev/null; then
        echo "   ✅ doc4llm 包修复成功"
    else
        echo "   ❌ doc4llm 包修复失败"
        exit 1
    fi
else
    echo "   ✅ doc4llm 包正常"
fi

# 2. 清理磁盘空间（如果需要）
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
echo "2. 检查磁盘空间: ${DISK_USAGE}%"
if [ "$DISK_USAGE" -gt 95 ]; then
    echo "   清理临时文件..."
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find /tmp -name "doc-retriever-*" -delete 2>/dev/null || true
    echo "   ✅ 磁盘清理完成"
else
    echo "   ✅ 磁盘空间充足"
fi

# 3. 确保日志目录存在
echo "3. 检查日志目录..."
mkdir -p .claude/logs
touch .claude/logs/doc-retrieval.log
touch .claude/logs/security-validation.log
touch .claude/logs/performance-monitor.log
echo "   ✅ 日志目录就绪"

# 4. 验证核心功能
echo "4. 验证核心功能..."
if python -c "
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
print('核心功能正常')
" 2>/dev/null; then
    echo "   ✅ 核心功能验证通过"
else
    echo "   ❌ 核心功能验证失败"
    exit 1
fi

echo ""
echo "🎉 快速修复完成！"
echo "系统现在应该可以正常工作了。"
echo ""
echo "如需完整优化，请运行: ./.claude/scripts/doc-retriever-optimize.sh"