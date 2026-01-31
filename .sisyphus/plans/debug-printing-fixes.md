# Debug 打印问题修复计划

## TL;DR

> 修复 doc4llm/doc_rag 模块 debug 模式下 5 个重复/错误打印问题

**5 个问题**:
1. Phase 1 打印原始 query，应打印预处理后的 query 列表
2. Headings 为空时应显示"整页匹配"，而非显示 0 个 heading
3. Phase 1.5 统计信息被打印两次（print_phase_1_5 + print_phase_1_5_debug 重复）
4. Phase 2 timing 被打印两次
5. Phase 2 debug 模式不显示 "[原始输出]"（已取消）

**新增问题**:
6. Phase 2 debug 模式不能什么都不打印，需要显示 doc-meta 统计信息

**预计工作量**: 小型修复（2-3 个文件，30 行代码修改）

---

## 问题分析

### 问题 1: Phase 1 查询显示问题

**位置**: `output_formatter.py:167`

**当前行为**:
```python
print(f"检索查询: {query}")  # 只打印字符串
```

**期望行为**: 显示预处理后的查询列表（来自 ParamsParserAPI）

**修复方案**: 添加 `optimized_queries` 参数，支持显示预处理后的查询列表

### 问题 2: 空 headings 显示问题

**位置**: `output_formatter.py:178-185`

**当前行为**:
```python
heading_count = page.get("heading_count", 0)
print(f"     📊 标题: {heading_count} 个heading, ...")
```

**问题**: 如果 `headings` 列表为空，表示整页匹配（所有 heading 都会被提取），但当前显示为 "0 个heading"

**修复方案**: 检查 `headings` 列表是否为空，为空时显示 "整页匹配 (全部 heading)"

### 问题 3: Phase 1.5 重复打印

**位置**: `orchestrator.py:959-974`

**当前行为**:
```python
elif rerank_executed:
    print_phase_1_5(..., quiet=False)  # 第1次打印统计
    if self.config.debug:
        print_phase_1_5_debug(...)     # 第2次打印（内部又调用 print_phase_1_5）
```

**修复方案**: debug 模式下只调用 `print_phase_1_5_debug()`，不再单独调用 `print_phase_1_5()`

### 问题 4: Phase 2 重复打印 timing

**位置**: `orchestrator.py:1107` 和 `orchestrator.py:1135`

**当前行为**:
```python
# Line 1107: 正常流程中打印
print(f"▶ [Phase 2] Content Extraction 耗时: {timing['phase_2']:.2f}ms")

# Line 1135: 早期退出时再次打印（stop_at_phase == "2"）
print(f"▶ [Phase 2] Content Extraction 耗时: {timing['phase_2']:.2f}ms")
```

**修复方案**: Line 1135 的 print 移到 debug 模式下，或者在 Line 1107 前增加条件判断

### 需求 5: Phase 1 debug 模式打印原始 JSON

**位置**: `output_formatter.py` - `print_phase_1_debug` 函数

**当前行为**: `print_phase_1_debug()` 只打印统计信息和 thinking/raw_response

**期望行为**: debug 模式下还应打印完整的原始 JSON 输出结果

**修复方案**: 在 `print_phase_1_debug()` 中添加 JSON 原始输出打印

---

## 修复计划

### 修复 1: output_formatter.py - print_phase_1

**文件**: `doc4llm/doc_rag/output_formatter.py`

**修改内容**:
1. 函数签名添加 `optimized_queries` 参数
2. 如果 `optimized_queries` 有值，显示预处理后的查询列表
3. 否则显示原始查询字符串
4. 检查 headings 列表是否为空，为空时显示"整页匹配"

```python
def print_phase_1(
    results: Dict[str, Any],
    query: str,
    optimized_queries: Optional[List[Dict[str, Any]]] = None,
    quiet: bool = False,
) -> None:
    # ... 实现 ...
```

### 修复 2: output_formatter.py - print_phase_1_debug

**文件**: `doc4llm/doc_rag/output_formatter.py`

**修改内容**: 传递 `optimized_queries` 参数给 `print_phase_1`

```python
def print_phase_1_debug(
    results: Dict[str, Any],
    query: str,
    optimized_queries: Optional[List[Dict[str, Any]]] = None,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    print_phase_1(results, query, optimized_queries, quiet=False)
    # ... 其余代码 ...
```

### 修复 3: orchestrator.py - Phase 1.5 打印逻辑

**文件**: `doc4llm/doc_rag/orchestrator.py`

**修改内容**:
- `rerank_executed` 分支：移除 `print_phase_1_5()` 调用，只保留 `print_phase_1_5_debug()`
- `embedding_rerank_executed` 分支：同上
- `print_phase_1_5_failed` 分支：同上

```python
elif rerank_executed:
    # 移除 print_phase_1_5(..., quiet=False)
    if self.config.debug:
        print_phase_1_5_debug(...)
```

### 修复 4: orchestrator.py - Phase 2 打印逻辑

**文件**: `doc4llm/doc_rag/orchestrator.py`

**修改内容**:
- Line 1163: 移除重复的 timing print（Line 1125 已打印）
- Lines 1164-1179: 移除整个 "[原始输出]" 区块（Phase 2 不需要原始输出）

### 修复 6: orchestrator.py - Phase 2 debug 打印统计信息

**文件**: `doc4llm/doc_rag/orchestrator.py`

**修改内容**:
- 在 stop_at_phase == "2" 分支添加 debug 统计信息打印
- 显示：文档数量、总行数、总字符数、使用率

**设计格式**:
```python
if self.config.debug:
    # 计算总字符数
    total_chars = sum(len(content) for content in extraction_result.contents.values())
    usage_rate = extraction_result.total_line_count / extraction_result.threshold * 100
    
    print(f"\n{'─' * 60}")
    print(f"▶ Phase 2: Content Extraction [Debug Info]")
    print(f"{'─' * 60}")
    print(f"  文档数量: {extraction_result.document_count} 个 section")
    print(f"  总行数: {extraction_result.total_line_count:,} 行")
    print(f"  总字符数: {total_chars:,} 字")
    print(f"  阈值: {extraction_result.threshold:,} 行 ({usage_rate:.1f}% 使用率)")
    print(f"{'─' * 60}\n")
```

```python
# 修复前 (Line 1162-1179):
if self.config.debug:
    print(f"▶ [Phase 2] Content Extraction 耗时: {timing['phase_2']:.2f}ms")  # 重复！
    print(f"\n{'─' * 60}")
    print(f"▶ Phase 2: Content Extraction [原始输出]")  # 取消！
    print(f"{'─' * 60}")
    json_output = json.dumps(...)
    print(json_output)
    print(f"{'─' * 60}\n")

# 修复后:
if self.config.debug:
    # 移除重复的 timing print（Line 1125 已打印）
    # 移除整个 "[原始输出]" 区块（Phase 2 不需要）
    pass  # 或直接删除整个 if debug 块
```

### 需求 5: Phase 2 debug 模式使用统一格式打印原始输出

**位置**: `orchestrator.py:1162-1179`

**当前行为**: 手动构建 JSON 输出，格式与其他阶段不统一

**期望行为**: 使用统一的 debug 输出格式

**修复方案**:
1. 移除 Line 1163 的重复 timing print
2. 将手动 JSON 输出替换为统一的格式

### 修复 5: output_formatter.py - Phase 1 debug 打印原始 JSON

**文件**: `doc4llm/doc_rag/output_formatter.py`

**修改内容**:
- 在 `print_phase_1_debug()` 中添加原始 JSON 输出打印
- 使用 `json.dumps(results, ensure_ascii=False, indent=2)` 格式化输出

```python
def print_phase_1_debug(
    results: Dict[str, Any],
    query: str,
    optimized_queries: Optional[List[Dict[str, Any]]] = None,
    raw_response: Optional[str] = None,
    thinking: Optional[str] = None,
) -> None:
    print_phase_1(results, query, optimized_queries, quiet=False)

    # 打印原始 JSON 输出
    print(f"\n{'─' * 60}")
    print(f"▶ Phase 1: 文档检索 (Document Search) [原始输出]")
    print(f"{'─' * 60}")
    json_output = json.dumps(results, ensure_ascii=False, indent=2)
    print(json_output)
    print(f"{'─' * 60}\n")

    if thinking:
        print("\n[Thinking Process]")
        print(thinking)

    if raw_response:
        print("\n[Raw LLM Response]")
        print(raw_response)
```

### 修复 6: orchestrator.py - Phase 2 timing 重复打印

**文件**: `doc4llm/doc_rag/orchestrator.py`

**修改内容**:
- Line 1163: 移除重复的 timing print（Line 1125 已打印）

---

## 验证策略

### 自动化验证

**测试命令**:
```bash
# 运行 debug 模式，验证 4 个问题已修复
python -c "
from doc4llm.doc_rag.orchestrator import retrieve

result = retrieve(
    query='如何创建 ray cluster?',
    base_dir='path/to/knowledge_base',
    debug=True
)
"
```

### 验证要点

1. **Phase 1**: 显示预处理后的查询列表，而非原始 query 字符串
2. **Phase 1**: 空 headings 时显示 "整页匹配 (全部 heading)"
3. **Phase 1**: debug 模式显示原始 JSON 输出
4. **Phase 1.5**: 统计信息只打印一次
5. **Phase 2**: timing 只打印一次
6. **Phase 2**: debug 模式显示统计信息（文档数量、总行数、字符数、使用率）

---

## 风险评估

| 风险 | 级别 | 缓解措施 |
|------|------|----------|
| 修改 output_formatter 影响其他调用者 | 低 | 参数有默认值，API 向后兼容 |
| Phase 1.5 debug 输出不完整 | 中 | 确保 print_phase_1_5_debug 内部调用 print_phase_1_5 |

---

## 执行步骤

### Step 1: 修复 output_formatter.py - print_phase_1

- 添加 `optimized_queries` 参数
- 修改查询显示逻辑
- 修改 headings 空列表显示逻辑

### Step 2: 修复 output_formatter.py - print_phase_1_debug

- 添加 `optimized_queries` 参数
- 传递参数给 print_phase_1

### Step 3: 修复 orchestrator.py - Phase 1.5 打印

- 移除重复的 print_phase_1_5 调用

### Step 4: 修复 orchestrator.py - Phase 2 打印

- 移除 Line 1163 的重复 timing print（Line 1125 已打印）
- 移除整个 "[原始输出]" 区块（Phase 2 不需要）
- 添加 debug 统计信息打印（文档数量、总行数、字符数、使用率）

### Step 5: 修复 orchestrator.py - Phase 2 timing 重复打印

- 移除 Line 1163 的重复 timing print（Line 1125 已打印）

### Step 6: 修复 output_formatter.py - Phase 1 debug 打印原始 JSON

- 添加原始 JSON 输出打印

### Step 7: 运行验证测试

- 执行测试命令
- 验证所有 6 个问题已修复

---

## 成功标准

- [ ] Phase 1 显示预处理后的查询列表
- [ ] Phase 1 空 headings 显示 "整页匹配 (全部 heading)"
- [ ] Phase 1 debug 模式显示原始 JSON 输出
- [ ] Phase 1.5 统计信息只打印一次
- [ ] Phase 2 timing 只打印一次（移除 Line 1163 的重复打印）
- [ ] Phase 2 debug 模式显示统计信息（文档数量、总行数、字符数、使用率）
- [ ] 所有修改向后兼容，不影响现有调用者
