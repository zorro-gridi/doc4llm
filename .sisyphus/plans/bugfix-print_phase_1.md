# Bug Fix: print_phase_1 执行和 optimized_queries 参数传递问题

## 问题描述

在 `doc4llm/doc_rag/orchestrator.py` 中存在两个问题：

### 问题 1: debug 模式下 print_phase_1 重复执行
- **位置**: 第 778-784 行
- **现象**: 
  - 第 778 行在所有模式下都调用 `print_phase_1(results=search_result, query=search_query, quiet=True)`
  - 第 781-784 行在 debug 模式下调用 `print_phase_1_debug`，其内部会再次调用 `print_phase_1`
  - **结果**: debug 模式下 `print_phase_1` 被执行两次，导致重复输出

### 问题 2: optimized_queries 参数传递丢失
- **位置**: 第 778 行和第 781-784 行
- **现象**: 
  - `print_phase_1` 和 `print_phase_1_debug` 函数都支持 `optimized_queries` 参数
  - 但当前调用中未传递该参数
  - **结果**: Phase 1 的输出无法显示优化后的查询列表

## 问题根因

1. **缺少条件判断**: 第 778 行应该在非 debug 模式下才执行
2. **参数遗漏**: 调用函数时未添加 `optimized_queries=optimized_queries`

## 修复方案

### 修改文件
`doc4llm/doc_rag/orchestrator.py`

### 修改内容

```python
# === 修改前 (第 778-784 行) ===
print_phase_1(results=search_result, query=search_query, quiet=True)

if self.config.debug:
    print_phase_1_debug(
        results=search_result,
        query=search_query,
    )

# === 修改后 ===
# 非 debug 模式：静默打印 Phase 1 结果
# debug 模式：由 print_phase_1_debug 内部调用 print_phase_1，避免重复输出
if not self.config.debug:
    print_phase_1(
        results=search_result,
        query=search_query,
        optimized_queries=optimized_queries,
        quiet=True,
    )

# Debug: 打印 Phase 1 结果（包含原始 JSON 输出）
if self.config.debug:
    print_phase_1_debug(
        results=search_result,
        query=search_query,
        optimized_queries=optimized_queries,
    )
```

## 修改说明

1. **添加条件判断**: 
   - 非 debug 模式：执行 `print_phase_1`
   - debug 模式：由 `print_phase_1_debug` 负责输出，避免重复

2. **补充参数传递**:
   - 两个函数调用都添加 `optimized_queries=optimized_queries` 参数
   - 确保 Phase 1 输出能显示优化后的查询列表

3. **保持功能等价**:
   - 非 debug 模式：静默输出（quiet=True）保持不变
   - debug 模式：详细输出包含原始 JSON 保持不变

## 验证方法

### 测试场景 1: 非 debug 模式
```bash
python -m doc4llm.doc_rag.orchestrator "如何安装 doc4llm?"
```
**预期**: 显示 Phase 1 静默输出，包含优化后的查询列表

### 测试场景 2: debug 模式
```bash
python -m doc4llm.doc_rag.orchestrator "如何安装 doc4llm?" --debug 1
```
**预期**: 
- Phase 1 只输出一次（通过 print_phase_1_debug）
- 显示原始 JSON 输出
- 包含优化后的查询列表

## 涉及文件

| 文件 | 修改类型 |
|------|---------|
| `doc4llm/doc_rag/orchestrator.py` | Bug fix |

## 注意事项

- 修改仅涉及 orchestrator.py 中的 6 行代码
- 不影响其他模块的功能
- 保持与现有代码风格一致
