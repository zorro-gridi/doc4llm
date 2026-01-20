#!/bin/bash

# doc-retriever 操作验证脚本 v2.0
# 在执行 Bash 命令前进行全面的安全性和有效性检查

# 安全配置
MAX_COMMAND_LENGTH=2000  # 增加命令长度限制以支持复杂查询
ALLOWED_PATHS_PATTERN="^(md_docs/|\.claude/logs/|\.claude/temp/)"
LOG_FILE=".claude/logs/security-validation.log"

# 创建日志目录
mkdir -p .claude/logs

# 记录函数
log_security_event() {
    local level="$1"
    local message="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $message" >> "$LOG_FILE"
}

# 从 stdin 读取 hook 输入
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null || echo "")

# 如果无法解析命令，记录并允许执行
if [ -z "$COMMAND" ] || [ "$COMMAND" = "null" ]; then
    log_security_event "INFO" "无法解析命令，允许执行"
    exit 0
fi

log_security_event "INFO" "验证命令: $COMMAND"

# 1. 命令长度检查
if [ ${#COMMAND} -gt $MAX_COMMAND_LENGTH ]; then
    log_security_event "ERROR" "命令过长 (${#COMMAND} > $MAX_COMMAND_LENGTH): $COMMAND"
    echo "❌ 安全检查失败: 命令过长" >&2
    exit 2
fi

# 2. 危险操作检查（增强版）
DANGEROUS_PATTERNS=(
    "rm -rf"
    "sudo"
    "chmod 777"
    ">/dev/null 2>&1 &"     # 后台进程
    "curl.*|.*sh"           # 管道执行
    "wget.*|.*sh"           # 管道执行
    "eval"                  # 动态执行
    "exec"                  # 进程替换
    "\$\("                  # 命令替换
    "\`"                     # 反引号命令替换
    "&&.*rm"                # 链式删除
    "||.*rm"                # 条件删除
    ">"                     # 重定向（可能覆盖文件）
    ">>"                    # 追加重定向
    "nc -l"                 # 网络监听
    "python -c.*os\."       # Python 系统调用
    "python -c.*subprocess" # Python 子进程
    "/etc/"                 # 系统配置目录
    "/usr/"                 # 系统程序目录
    "/var/"                 # 系统变量目录
    "~/"                    # 用户主目录
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        log_security_event "CRITICAL" "检测到危险操作: $pattern in $COMMAND"
        echo "❌ 安全检查失败: 检测到危险操作模式 '$pattern'" >&2
        echo "🚫 命令被阻止: $COMMAND" >&2
        exit 2
    fi
done

# 3. 路径遍历检查
PATH_TRAVERSAL_PATTERNS=(
    "\.\./\.\."             # 路径遍历
    "/\.\."                 # 路径遍历
    "\.\.\\"                # Windows 路径遍历
    "%2e%2e"                # URL 编码路径遍历
    "%252e%252e"            # 双重编码路径遍历
)

for pattern in "${PATH_TRAVERSAL_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        log_security_event "CRITICAL" "检测到路径遍历尝试: $pattern in $COMMAND"
        echo "❌ 安全检查失败: 检测到路径遍历尝试" >&2
        exit 2
    fi
done

# 4. 允许的文档操作白名单
ALLOWED_DOC_OPERATIONS=(
    "^ls -[la1]+ md_docs/"
    "^find md_docs/ -name"
    "^grep -[rEin]+ .* md_docs/"
    "^python .*/extract_md_doc\.py"
    "^python -m doc4llm"
    "^cat md_docs/.*/doc(Content|TOC)\.md$"
    "^head -n [0-9]+ md_docs/"
    "^tail -n [0-9]+ md_docs/"
    "^wc -l md_docs/"
    "^echo"
    "^mkdir -p \.claude/(logs|temp)"
)

IS_ALLOWED_OPERATION=false
for pattern in "${ALLOWED_DOC_OPERATIONS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        IS_ALLOWED_OPERATION=true
        log_security_event "INFO" "匹配允许操作: $pattern"
        break
    fi
done

# 5. 如果不是预定义的安全操作，进行额外检查
if [ "$IS_ALLOWED_OPERATION" = false ]; then
    # 检查是否访问允许的路径
    if echo "$COMMAND" | grep -qE "$ALLOWED_PATHS_PATTERN"; then
        log_security_event "WARN" "非标准但路径安全的操作: $COMMAND"
    else
        log_security_event "ERROR" "不允许的操作: $COMMAND"
        echo "❌ 安全检查失败: 操作不在允许列表中" >&2
        echo "🚫 命令被阻止: $COMMAND" >&2
        exit 2
    fi
fi

# 6. 文档目录存在性检查
if echo "$COMMAND" | grep -q "md_docs" && [ ! -d "md_docs" ]; then
    log_security_event "WARN" "md_docs 目录不存在，操作可能失败"
    echo "⚠️  警告: md_docs 目录不存在，操作可能失败" >&2
fi

# 7. 资源使用检查（防止资源耗尽）
if echo "$COMMAND" | grep -qE "(find.*-exec|grep.*-r.*\*|cat.*\*)"; then
    log_security_event "WARN" "可能的高资源消耗操作: $COMMAND"
    echo "⚠️  警告: 操作可能消耗大量资源" >&2
fi

# 所有检查通过
log_security_event "INFO" "安全验证通过: $COMMAND"
exit 0