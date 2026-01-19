#!/bin/bash

# doc-retriever 系统全面优化脚本 - k8s 环境版本
# 一键执行所有优化步骤

set -e

# 激活 k8s conda 环境
source ~/miniconda3/etc/profile.d/conda.sh
conda activate k8s
echo "已激活 conda k8s 环境"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
OPTIMIZATION_LOG=".claude/logs/optimization-$(date '+%Y%m%d-%H%M%S').log"

echo "=== doc-retriever 系统优化开始 (k8s 环境) ===" | tee "$OPTIMIZATION_LOG"
echo "时间: $TIMESTAMP" | tee -a "$OPTIMIZATION_LOG"
echo "日志文件: $OPTIMIZATION_LOG" | tee -a "$OPTIMIZATION_LOG"
echo "" | tee -a "$OPTIMIZATION_LOG"

# 步骤计数器
STEP=1
TOTAL_STEPS=6

run_step() {
    local step_name="$1"
    local script_path="$2"
    
    echo "[$STEP/$TOTAL_STEPS] $step_name" | tee -a "$OPTIMIZATION_LOG"
    echo "执行: $script_path" | tee -a "$OPTIMIZATION_LOG"
    
    if [ -x "$script_path" ]; then
        if "$script_path" >> "$OPTIMIZATION_LOG" 2>&1; then
            echo "✅ $step_name 完成" | tee -a "$OPTIMIZATION_LOG"
        else
            echo "❌ $step_name 失败" | tee -a "$OPTIMIZATION_LOG"
            return 1
        fi
    else
        echo "⚠️  脚本不存在或不可执行: $script_path" | tee -a "$OPTIMIZATION_LOG"
        return 1
    fi
    
    STEP=$((STEP + 1))
    echo "" | tee -a "$OPTIMIZATION_LOG"
}

# 执行优化步骤
echo "开始执行优化步骤..." | tee -a "$OPTIMIZATION_LOG"
echo "" | tee -a "$OPTIMIZATION_LOG"

# Step 1: 系统恢复
run_step "系统依赖修复" "./.claude/scripts/system-recovery.sh"

# Step 2: 性能优化
run_step "性能优化" "./.claude/scripts/performance-optimizer.sh"

# Step 3: 健康检查
run_step "系统健康检查" "./.claude/scripts/doc-retriever-health-check.sh"

# Step 4: 诊断检查
run_step "系统诊断" "./.claude/scripts/doc-retriever-diagnose.sh"

# Step 5: 监控启动
run_step "性能监控" "./.claude/scripts/doc-retriever-monitor.sh"

# Step 6: 最终验证
echo "[$STEP/$TOTAL_STEPS] 最终验证" | tee -a "$OPTIMIZATION_LOG"
echo "验证核心功能..." | tee -a "$OPTIMIZATION_LOG"

if python -c "
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor
extractor = MarkdownDocExtractor()
result = extractor.extract_by_titles_with_metadata(['test'], threshold=100)
print('✅ 核心功能验证通过')
" 2>/dev/null; then
    echo "✅ 最终验证通过" | tee -a "$OPTIMIZATION_LOG"
else
    echo "❌ 最终验证失败" | tee -a "$OPTIMIZATION_LOG"
fi

echo "" | tee -a "$OPTIMIZATION_LOG"

# 生成优化报告
echo "=== 优化报告 ===" | tee -a "$OPTIMIZATION_LOG"
echo "优化完成时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$OPTIMIZATION_LOG"

# 系统状态检查
if [ -d "md_docs" ]; then
    DOC_COUNT=$(find md_docs -name "*.md" -type f | wc -l)
    echo "文档数量: $DOC_COUNT" | tee -a "$OPTIMIZATION_LOG"
fi

DISK_USAGE=$(df . | tail -1 | awk '{print $5}')
echo "磁盘使用率: $DISK_USAGE" | tee -a "$OPTIMIZATION_LOG"

if python -c "import doc4llm" 2>/dev/null; then
    echo "doc4llm 包状态: ✅ 可用" | tee -a "$OPTIMIZATION_LOG"
else
    echo "doc4llm 包状态: ❌ 不可用" | tee -a "$OPTIMIZATION_LOG"
fi

echo "" | tee -a "$OPTIMIZATION_LOG"
echo "=== 优化完成 ===" | tee -a "$OPTIMIZATION_LOG"
echo "详细日志: $OPTIMIZATION_LOG"
echo ""
echo "建议："
echo "1. 定期运行此脚本进行系统维护"
echo "2. 监控 .claude/logs/ 目录中的日志文件"
echo "3. 如遇问题，查看 $OPTIMIZATION_LOG 获取详细信息"

exit 0