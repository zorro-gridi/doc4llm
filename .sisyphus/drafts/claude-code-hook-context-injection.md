# Claude Code Hook 机制与上下文注入研究

## 研究目标
研究如何利用 Claude Code 的 hook 机制，将 `doc4llm/doc_rag/main.py` 代码执行结果注入到上下文中。

---

## 一、Claude Code Hook 机制概述

### 1. Hook 类型

Claude Code 支持多种 Hook 类型，从 `hooks.json` 配置文件中可以看到：

| Hook 类型 | 触发时机 | 用途 |
|-----------|----------|------|
| `PreToolUse` | 工具执行前 | 验证、警告、阻止操作 |
| `PostToolUse` | 工具执行后 | 格式化、测试、清理 |
| `Stop` | 会话停止时 | 完成检查、总结 |
| `UserPromptSubmit` | 用户提交提示时 | 提示预处理、上下文注入 |
| `Notification` | 发送通知时 | 权限提醒、空闲通知 |

### 2. Hook 配置结构

```json
{
  "description": "Hook description",
  "hooks": {
    "HookType": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/script.py",
            "timeout": 10
          }
        ],
        "matcher": "Edit|Write|MultiEdit"  // 可选，匹配特定工具
      }
    ]
  }
}
```

### 3. Hook 脚本工作原理

从 `security_reminder_hook.py` 和 `pretooluse.py` 可以看到：

**输入输出机制：**
- **输入**: Hook 脚本通过 `stdin` 接收 JSON 格式的上下文数据
- **输出**: 通过 `stdout` 输出 JSON 格式的结果
- **退出码**:
  - `0`: 允许操作继续
  - `1`: 阻止操作（某些类型）
  - `2`: 阻止 PreToolUse 操作

**示例输入数据结构：**
```json
{
  "session_id": "session_xxx",
  "tool_name": "Bash",
  "tool_input": {"command": "..."}
}
```

---

## 二、上下文注入机制

### 1. 注入方法

从分析来看，有以下几种方式可以向上下文注入内容：

#### 方法 A: systemMessage 字段

```json
{
  "systemMessage": "注入的系统消息内容"
}
```

**示例** (来自 `pretooluse.py` 第 22-23 行):
```python
error_msg = {"systemMessage": f"Hookify import error: {e}"}
print(json.dumps(error_msg), file=sys.stdout)
```

#### 方法 B: stderr 输出

通过 `print(message, file=sys.stderr)` 输出警告信息，这些信息会显示在上下文中。

**示例** (来自 `security_reminder_hook.py` 第 272-273 行):
```python
print(reminder, file=sys.stderr)
sys.exit(2)  # 阻止操作
```

### 2. 推荐的 Hook 类型

对于 `doc_rag` 结果注入上下文，有两个最佳时机：

| 时机 | Hook 类型 | 优点 | 缺点 |
|------|----------|------|------|
| 用户提交提示时 | `UserPromptSubmit` | 每次提示前自动检索 | 可能增加延迟 |
| 特定工具执行前 | `PreToolUse` | 按需触发，灵活 | 需要手动配置触发条件 |

---

## 三、doc_rag 输出格式分析

从 `orchestrator.py` 的 `DocRAGResult` 数据类可以看到：

```python
@dataclass
class DocRAGResult:
    success: bool                           # 是否成功
    output: str                             # 最终格式化输出（Markdown）
    scene: str                              # 场景分类
    documents_extracted: int                # 提取的文档数
    total_lines: int                        # 总行数
    requires_processing: bool               # 是否需要处理
    sources: List[Dict[str, Any]] = ...     # 来源列表
    raw_response: Optional[str] = None      # 原始 LLM 响应
    thinking: Optional[str] = None          # 思考过程
    timing: Dict[str, float] = ...          # 各阶段耗时
```

**输出格式特点：**
- `output` 字段包含 AOP-FINAL 包装的 Markdown 内容
- 包含 `=== AOP-FINAL | agent=rag | format=markdown | ... ===` 包装器
- 末尾包含 Sources 部分（文档来源信息）

---

## 四、实现方案

### 方案 1: UserPromptSubmit Hook（推荐）

创建一个 Hook，在用户每次提交提示时自动调用 doc_rag 检索相关文档。

#### 步骤 1: 创建 Hook 脚本

**文件**: `.claude/hooks/doc_rag_context.py`

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook to inject doc_rag results into context."""

import json
import os
import sys
from pathlib import Path

# 添加 doc4llm 到 Python 路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from doc4llm.doc_rag.orchestrator import retrieve

def main():
    """Main hook entry point."""
    try:
        # 从 stdin 读取输入
        input_data = json.load(sys.stdin)
        user_prompt = input_data.get("user_input", "")

        if not user_prompt:
            print(json.dumps({}), file=sys.stdout)
            return

        # 调用 doc_rag 检索相关文档
        result = retrieve(
            query=user_prompt,
            base_dir="~/project/md_docs_base",
            skiped_keywords_path=f"{PROJECT_ROOT}/doc4llm/doc_rag/searcher/skiped_keywords.txt",
            threshold=3000,
            embedding_reranker=False,
            searcher_reranker=True,
            llm_reranker=True,
            searcher_config={
                'embedding_provider': 'ms',
                'threshold_page_title': 3.0,
            }
        )

        if result.success:
            # 注入上下文
            context_output = {
                "systemMessage": f"""【文档检索结果】

{result.output}

---
*此上下文由 doc_rag 自动检索生成*"""
            }
            print(json.dumps(context_output), file=sys.stdout)
        else:
            print(json.dumps({}), file=sys.stdout)

    except Exception as e:
        error_output = {"systemMessage": f"doc_rag 检索失败: {str(e)}"}
        print(json.dumps(error_output), file=sys.stdout)

    finally:
        sys.exit(0)

if __name__ == '__main__':
    main()
```

#### 步骤 2: 创建 Hook 配置文件

**文件**: `.claude/settings.json`

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_HOOK_ROOT}/doc_rag_context.py"
          }
        ]
      }
    ]
  }
}
```

### 方案 2: PreToolUse Hook（按需触发）

当用户使用特定工具（如 Read, Grep）时触发 doc_rag 检索。

#### 步骤 1: 创建条件触发脚本

**文件**: `.claude/hooks/doc_rag_pretool.py`

```python
#!/usr/bin/env python3
"""PreToolUse hook to inject doc_rag context for specific tools."""

import json
import os
import sys

# 添加路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from doc4llm.doc_rag.orchestrator import retrieve

# 需要触发 doc_rag 的工具
TRIGGER_TOOLS = ["Read", "Grep", "lsp_symbols"]

def should_trigger(tool_name, tool_input):
    """判断是否应该触发 doc_rag 检索。"""
    if tool_name not in TRIGGER_TOOLS:
        return False

    # 检查文件路径是否在知识库范围内
    file_path = tool_input.get("filePath", "") or tool_input.get("path", "")
    if not file_path:
        return False

    # 这里可以添加更复杂的触发条件
    return True

def main():
    """Main hook entry point."""
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    if not should_trigger(tool_name, tool_input):
        print(json.dumps({}), file=sys.stdout)
        sys.exit(0)

    # 构建查询
    file_path = tool_input.get("filePath", "") or tool_input.get("path", "")
    query = f"查找 {file_path} 相关的文档和上下文"

    try:
        result = retrieve(
            query=query,
            base_dir="~/project/md_docs_base",
            # ... 其他参数
        )

        if result.success:
            context_output = {
                "systemMessage": f"""【相关文档上下文】

{result.output}"""
            }
            print(json.dumps(context_output), file=sys.stdout)

    except Exception as e:
        print(json.dumps({"systemMessage": f"doc_rag 失败: {e}"}), file=sys.stdout)

    sys.exit(0)

if __name__ == '__main__':
    main()
```

### 方案 3: 技能集成（Skill-based）

利用现有的 `rag` skill，通过 Agent 调用来检索文档。

**优势**:
- 无需配置 Hook
- 用户可以控制何时触发
- 更好的错误处理

**劣势**:
- 需要手动调用
- 不是自动化的

---

## 五、最佳实践建议

### 1. 性能考虑

| 策略 | 优点 | 缺点 |
|------|------|------|
| 每次提示前检索 | 上下文总是最新 | 延迟增加 |
| 缓存检索结果 | 速度快 | 可能过时 |
| 按需触发 | 灵活可控 | 需要手动触发 |

### 2. 缓存策略建议

```python
# 伪代码示例
CACHE_DIR = ".claude/.doc_rag_cache"

def get_cached_result(query):
    """获取缓存的检索结果。"""
    cache_key = hash(query)
    cache_file = f"{CACHE_DIR}/{cache_key}.json"

    if os.path.exists(cache_file):
        # 检查缓存是否过期 (例如 1 小时)
        if os.path.getmtime(cache_file) > time.time() - 3600:
            with open(cache_file) as f:
                return json.load(f)

    # 执行检索
    result = retrieve(query)

    # 缓存结果
    os.makedirs(CACHE_DIR, exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(result, f)

    return result
```

### 3. 上下文大小控制

doc_rag 输出可能很大，需要控制注入上下文的大小：

```python
def truncate_context(output, max_chars=8000):
    """截断过长的上下文。"""
    if len(output) <= max_chars:
        return output

    # 保留开头和 Sources 部分
    lines = output.split('\n')
    sources_start = None

    for i, line in enumerate(lines):
        if '### 文档来源' in line or '### Sources' in line:
            sources_start = i
            break

    if sources_start:
        header = '\n'.join(lines[:sources_start])
        sources = '\n'.join(lines[sources_start:])
        # 截断头部
        header = header[:max_chars - len(sources) - 100]
        return header + '\n...[内容截断]...\n' + sources

    return output[:max_chars] + '\n...[内容截断]...'
```

### 4. 错误处理

```python
try:
    result = retrieve(query)
    if result.success:
        context_output = {"systemMessage": result.output}
    else:
        context_output = {"systemMessage": f"doc_rag 检索无结果: {result.output}"}
except Exception as e:
    context_output = {"systemMessage": f"doc_rag 错误: {str(e)}"}
    # 记录详细错误到日志
    logging.error(f"doc_rag hook 错误: {traceback.format_exc()}")
```

---

## 六、文件位置和配置

### 项目级 Hook 配置

```
项目目录/
├── .claude/
│   ├── settings.json          # Hook 配置文件
│   └── hooks/
│       ├── doc_rag_context.py # UserPromptSubmit hook
│       └── doc_rag_pretool.py # PreToolUse hook
├── doc4llm/
│   └── doc_rag/
│       ├── orchestrator.py    # 检索主入口
│       └── ...
└── ...
```

### 环境变量

可以在 `settings.json` 中使用环境变量：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 ${CLAUDE_HOOK_ROOT}/doc_rag_context.py",
            "env": {
              "DOC_RAG_BASE_DIR": "~/project/md_docs_base"
            }
          }
        ]
      }
    ]
  }
}
```

---

## 七、测试和调试

### 1. 手动测试 Hook

```bash
# 测试 hook 脚本
echo '{"user_input": "如何创建 ray cluster?"}' | python3 .claude/hooks/doc_rag_context.py
```

### 2. 调试日志

```python
import logging

logging.basicConfig(
    filename='.claude/hooks/debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
```

### 3. 验证上下文注入

在 Claude Code 中，可以通过查看系统消息来验证上下文是否成功注入。

---

## 八、总结

### 推荐方案

1. **首选方案**: `UserPromptSubmit` Hook
   - 自动化程度高
   - 每次提示都能获得相关文档上下文
   - 适合知识库密集型项目

2. **备选方案**: `PreToolUse` Hook
   - 按需触发，性能更好
   - 适合特定场景的上下文增强

3. **简单方案**: 使用现有 `rag` skill
   - 无需配置 Hook
   - 手动控制触发时机

### 下一步行动

1. 创建 `.claude/` 目录和基础配置文件
2. 实现 `doc_rag_context.py` Hook 脚本
3. 添加缓存和错误处理
4. 测试并调优性能
5. 监控和优化用户体验
