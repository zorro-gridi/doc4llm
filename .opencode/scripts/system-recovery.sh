#!/bin/bash

# doc-retriever 系统恢复脚本
# 解决核心依赖和资源问题

set -e

echo "=== doc-retriever 系统恢复开始 ==="

# 1. 修复 doc4llm 包依赖
echo "[1/6] 修复 doc4llm 包依赖..."
if ! python -c "import doc4llm" 2>/dev/null; then
    echo "重新安装 doc4llm 包..."
    pip install -e . --quiet
    if python -c "import doc4llm" 2>/dev/null; then
        echo "✅ doc4llm 包安装成功"
    else
        echo "❌ doc4llm 包安装失败"
        exit 1
    fi
else
    echo "✅ doc4llm 包已可用"
fi

# 2. 清理磁盘空间
echo "[2/6] 清理磁盘空间..."
INITIAL_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
echo "当前磁盘使用率: ${INITIAL_USAGE}%"

if [ "$INITIAL_USAGE" -gt 95 ]; then
    echo "清理 Python 缓存文件..."
    find . -name "*.pyc" -delete 2>/dev/null || true
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    
    echo "清理日志文件 (保留最近3天)..."
    find .claude/logs -name "*.log" -mtime +3 -delete 2>/dev/null || true
    
    echo "清理构建文件..."
    rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true
    
    FINAL_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    echo "清理后磁盘使用率: ${FINAL_USAGE}%"
    
    if [ "$FINAL_USAGE" -gt 90 ]; then
        echo "⚠️  磁盘空间仍然紧张，建议手动清理更多文件"
    else
        echo "✅ 磁盘空间清理完成"
    fi
else
    echo "✅ 磁盘空间充足"
fi

# 3. 修复文档集一致性
echo "[3/6] 检查文档集一致性..."
DOC_COUNT=$(find md_docs/Claude_Code_Docs:latest -name "*.md" -type f | wc -l)
DIR_COUNT=$(find md_docs/Claude_Code_Docs:latest -type d | wc -l)
echo "文档数量: $DOC_COUNT, 目录数量: $DIR_COUNT"

if [ "$DOC_COUNT" -ne "$((DIR_COUNT - 1))" ]; then
    echo "⚠️  文档和目录数量不匹配，建议检查文档集完整性"
else
    echo "✅ 文档集一致性正常"
fi

# 4. 创建缺失的日志文件
echo "[4/6] 初始化日志文件..."
mkdir -p .claude/logs
touch .claude/logs/doc-retrieval.log
touch .claude/logs/security-validation.log
touch .claude/logs/performance-monitor.log
echo "✅ 日志文件初始化完成"

# 5. 修复会话状态追踪
echo "[5/6] 更新会话管理脚本..."
# 这将在后续步骤中实现

# 6. 验证系统状态
echo "[6/6] 验证系统状态..."
if python -c "
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
print('✅ MarkdownDocExtractor 可用')
" 2>/dev/null; then
    echo "✅ 核心功能验证通过"
else
    echo "❌ 核心功能验证失败"
    exit 1
fi

echo "=== 系统恢复完成 ==="
echo "建议运行: ./.claude/scripts/doc-retriever-health-check.sh 进行全面检查"