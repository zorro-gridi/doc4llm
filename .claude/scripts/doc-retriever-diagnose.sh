#!/bin/bash

# doc-retriever 诊断工具
# 全面诊断文档检索系统的健康状态和潜在问题

echo "🔧 doc-retriever 系统诊断工具"
echo "=================================="

DIAGNOSTIC_LOG=".claude/logs/diagnostic-$(date +%Y%m%d-%H%M%S).log"
mkdir -p .claude/logs

# 记录诊断信息
log_diagnostic() {
    local level="$1"
    local message="$2"
    echo "[$level] $message" | tee -a "$DIAGNOSTIC_LOG"
}

# 检查基础环境
check_environment() {
    echo ""
    echo "🌍 环境检查"
    echo "----------"
    
    # 检查 Python 环境
    if command -v python >/dev/null 2>&1; then
        PYTHON_VERSION=$(python --version 2>&1)
        log_diagnostic "INFO" "Python 版本: $PYTHON_VERSION"
    else
        log_diagnostic "ERROR" "Python 未安装或不在 PATH 中"
    fi
    
    # 检查必要的 Python 包
    REQUIRED_PACKAGES=("jq")
    for package in "${REQUIRED_PACKAGES[@]}"; do
        if command -v "$package" >/dev/null 2>&1; then
            log_diagnostic "INFO" "$package 已安装"
        else
            log_diagnostic "WARN" "$package 未安装，某些功能可能受限"
        fi
    done
    
    # 检查 doc4llm 包
    if python -c "import doc4llm" 2>/dev/null; then
        log_diagnostic "INFO" "doc4llm 包可用"
        
        # 检查关键模块
        if python -c "from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor" 2>/dev/null; then
            log_diagnostic "INFO" "MarkdownDocExtractor 模块可用"
        else
            log_diagnostic "ERROR" "MarkdownDocExtractor 模块不可用"
        fi
    else
        log_diagnostic "ERROR" "doc4llm 包不可用"
    fi
}

# 检查文件系统结构
check_filesystem() {
    echo ""
    echo "📁 文件系统检查"
    echo "-------------"
    
    # 检查关键目录
    CRITICAL_DIRS=(
        ".claude"
        ".claude/agents"
        ".claude/skills"
        ".claude/scripts"
        ".claude/logs"
        "md_docs"
    )
    
    for dir in "${CRITICAL_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            PERMISSIONS=$(ls -ld "$dir" | awk '{print $1}')
            log_diagnostic "INFO" "$dir 存在 ($PERMISSIONS)"
        else
            log_diagnostic "ERROR" "$dir 不存在"
        fi
    done
    
    # 检查关键文件
    CRITICAL_FILES=(
        ".claude/agents/doc-retriever.md"
        ".claude/scripts/log-retrieval.sh"
        ".claude/scripts/validate-doc-operation.sh"
        ".claude/scripts/cleanup-doc-session.sh"
    )
    
    for file in "${CRITICAL_FILES[@]}"; do
        if [ -f "$file" ]; then
            if [ -x "$file" ]; then
                log_diagnostic "INFO" "$file 存在且可执行"
            else
                log_diagnostic "WARN" "$file 存在但不可执行"
            fi
        else
            log_diagnostic "ERROR" "$file 不存在"
        fi
    done
}

# 检查技能配置
check_skills() {
    echo ""
    echo "🎯 技能配置检查"
    echo "-------------"
    
    SKILLS=(
        "md-doc-query-optimizer"
        "md-doc-searcher"
        "md-doc-reader"
        "md-doc-processor"
    )
    
    for skill in "${SKILLS[@]}"; do
        SKILL_DIR=".claude/skills/$skill"
        SKILL_FILE="$SKILL_DIR/SKILL.md"
        
        if [ -d "$SKILL_DIR" ]; then
            if [ -f "$SKILL_FILE" ]; then
                # 检查技能文件的基本结构
                if grep -q "^name: $skill" "$SKILL_FILE"; then
                    log_diagnostic "INFO" "$skill 技能配置正确"
                else
                    log_diagnostic "WARN" "$skill 技能名称配置可能有误"
                fi
                
                if grep -q "^description:" "$SKILL_FILE"; then
                    log_diagnostic "INFO" "$skill 包含描述"
                else
                    log_diagnostic "WARN" "$skill 缺少描述"
                fi
            else
                log_diagnostic "ERROR" "$skill SKILL.md 文件不存在"
            fi
        else
            log_diagnostic "ERROR" "$skill 技能目录不存在"
        fi
    done
}

# 检查文档集
check_document_sets() {
    echo ""
    echo "📚 文档集检查"
    echo "-----------"
    
    if [ -d "md_docs" ]; then
        DOC_SETS=$(find md_docs -maxdepth 1 -type d | grep -v "^md_docs$" | wc -l)
        log_diagnostic "INFO" "发现 $DOC_SETS 个文档集"
        
        # 检查每个文档集的结构
        for doc_set in md_docs/*/; do
            if [ -d "$doc_set" ]; then
                SET_NAME=$(basename "$doc_set")
                DOC_COUNT=$(find "$doc_set" -name "docContent.md" | wc -l)
                TOC_COUNT=$(find "$doc_set" -name "docTOC.md" | wc -l)
                
                log_diagnostic "INFO" "$SET_NAME: $DOC_COUNT 个文档, $TOC_COUNT 个目录"
                
                if [ "$DOC_COUNT" -ne "$TOC_COUNT" ]; then
                    log_diagnostic "WARN" "$SET_NAME: 文档和目录数量不匹配"
                fi
            fi
        done
    else
        log_diagnostic "ERROR" "md_docs 目录不存在"
    fi
}

# 检查日志和监控
check_logs() {
    echo ""
    echo "📝 日志和监控检查"
    echo "---------------"
    
    LOG_FILES=(
        ".claude/logs/doc-retrieval.log"
        ".claude/logs/security-validation.log"
        ".claude/logs/performance-monitor.log"
    )
    
    for log_file in "${LOG_FILES[@]}"; do
        if [ -f "$log_file" ]; then
            SIZE=$(ls -lh "$log_file" | awk '{print $5}')
            LINES=$(wc -l < "$log_file")
            log_diagnostic "INFO" "$(basename "$log_file"): $SIZE, $LINES 行"
            
            # 检查最近的活动
            if [ "$LINES" -gt 0 ]; then
                LAST_ENTRY=$(tail -1 "$log_file" | cut -d']' -f1 | tr -d '[')
                log_diagnostic "INFO" "$(basename "$log_file") 最后活动: $LAST_ENTRY"
            fi
        else
            log_diagnostic "WARN" "$(basename "$log_file") 不存在"
        fi
    done
}

# 性能测试
performance_test() {
    echo ""
    echo "⚡ 性能测试"
    echo "--------"
    
    # 测试文档检索速度
    if [ -d "md_docs" ] && command -v python >/dev/null 2>&1; then
        log_diagnostic "INFO" "开始性能测试..."
        
        # 查找一个测试文档
        TEST_DOC=$(find md_docs -name "docContent.md" | head -1)
        if [ -n "$TEST_DOC" ]; then
            START_TIME=$(date +%s.%N)
            cat "$TEST_DOC" > /dev/null 2>&1
            END_TIME=$(date +%s.%N)
            
            DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "N/A")
            log_diagnostic "INFO" "文档读取测试: ${DURATION}s"
        fi
        
        # 测试目录遍历速度
        START_TIME=$(date +%s.%N)
        find md_docs -name "*.md" | wc -l > /dev/null
        END_TIME=$(date +%s.%N)
        
        DURATION=$(echo "$END_TIME - $START_TIME" | bc 2>/dev/null || echo "N/A")
        log_diagnostic "INFO" "目录遍历测试: ${DURATION}s"
    else
        log_diagnostic "WARN" "无法执行性能测试"
    fi
}

# 生成修复建议
generate_recommendations() {
    echo ""
    echo "💡 修复建议"
    echo "--------"
    
    # 分析诊断日志中的错误
    ERROR_COUNT=$(grep -c "ERROR" "$DIAGNOSTIC_LOG")
    WARN_COUNT=$(grep -c "WARN" "$DIAGNOSTIC_LOG")
    
    if [ "$ERROR_COUNT" -gt 0 ]; then
        echo "🚨 发现 $ERROR_COUNT 个严重问题:"
        grep "ERROR" "$DIAGNOSTIC_LOG" | sed 's/^/  /'
        echo ""
        echo "建议立即修复这些问题以确保系统正常运行。"
    fi
    
    if [ "$WARN_COUNT" -gt 0 ]; then
        echo "⚠️  发现 $WARN_COUNT 个警告:"
        grep "WARN" "$DIAGNOSTIC_LOG" | sed 's/^/  /'
        echo ""
        echo "建议关注这些警告以优化系统性能。"
    fi
    
    if [ "$ERROR_COUNT" -eq 0 ] && [ "$WARN_COUNT" -eq 0 ]; then
        echo "✅ 系统状态良好，未发现严重问题。"
    fi
}

# 主执行流程
main() {
    log_diagnostic "INFO" "开始系统诊断 - $(date)"
    
    check_environment
    check_filesystem
    check_skills
    check_document_sets
    check_logs
    performance_test
    generate_recommendations
    
    echo ""
    echo "📋 诊断完成"
    echo "==========="
    echo "详细诊断报告已保存到: $DIAGNOSTIC_LOG"
    
    log_diagnostic "INFO" "诊断完成 - $(date)"
}

# 执行诊断
main "$@"