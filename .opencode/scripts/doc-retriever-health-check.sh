#!/bin/bash

# doc-retriever 健康检查脚本
# 验证所有依赖和配置的完整性

echo "🔍 doc-retriever 健康检查开始..."

# 检查必要目录
REQUIRED_DIRS=(
    ".claude/agents"
    ".claude/skills/md-doc-query-optimizer"
    ".claude/skills/md-doc-searcher"
    ".claude/skills/md-doc-reader"
    ".claude/skills/md-doc-processor"
    "md_docs"
)

echo "📁 检查必要目录..."
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (缺失)"
    fi
done

# 检查技能文件
echo "📄 检查技能文件..."
SKILL_FILES=(
    ".claude/skills/md-doc-query-optimizer/SKILL.md"
    ".claude/skills/md-doc-searcher/SKILL.md"
    ".claude/skills/md-doc-reader/SKILL.md"
    ".claude/skills/md-doc-processor/SKILL.md"
)

for skill in "${SKILL_FILES[@]}"; do
    if [ -f "$skill" ]; then
        echo "  ✅ $skill"
    else
        echo "  ❌ $skill (缺失)"
    fi
done

# 检查 Python 依赖
echo "🐍 检查 Python 依赖..."
if python -c "from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor" 2>/dev/null; then
    echo "  ✅ MarkdownDocExtractor 可用"
else
    echo "  ❌ MarkdownDocExtractor 不可用"
fi

# 检查文档集
echo "📚 检查文档集..."
if [ -d "md_docs" ]; then
    DOC_SETS=$(ls -1 md_docs/ 2>/dev/null | wc -l)
    echo "  📊 发现 $DOC_SETS 个文档集"
    ls -1 md_docs/ | head -5 | sed 's/^/    - /'
    if [ "$DOC_SETS" -gt 5 ]; then
        echo "    ... 还有 $((DOC_SETS - 5)) 个"
    fi
else
    echo "  ❌ md_docs 目录不存在"
fi

# 检查日志目录权限
echo "📝 检查日志配置..."
if [ -w ".claude/logs" ]; then
    echo "  ✅ 日志目录可写"
else
    echo "  ⚠️  日志目录权限问题"
fi

echo "✨ 健康检查完成"