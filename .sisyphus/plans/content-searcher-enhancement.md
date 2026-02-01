# ContentSearcher 上下文增强计划

## TL;DR

> **目标**：增强 `ContentSearcher._extract_context()` 方法，限制上下文在 heading 边界内，清理代码块/内联代码中的 URL
>
> **主要变更**：
> - 添加 heading 边界检测（上下 heading 位置）
> - 上下文扩展不超出 heading 边界
> - 返回内容排除 heading 行
> - 增强 URL 清理（代码块、内联代码）
>
> **影响文件**：`doc4llm/doc_rag/searcher/content_searcher.py`, `doc4llm/doc_rag/searcher/common_utils.py`

---

## 背景

### 当前问题

`_extract_context` 方法存在以下问题：

1. **无边界限制**：向上下扩展时可能超过 heading 范围，包含多个 section 的内容
2. **包含 heading 行**：返回的上下文中可能包含 `# heading` 行
3. **URL 清理不完整**：代码块 ```` ```url``` ```` 和内联代码 `` `url` ```` 中的 URL 未清理

### 需求澄清

- **向上文扩展**：遇到 heading 立即停止（heading 不包含在上下文中）
- **向下文扩展**：遇到 heading 立即停止（heading 不包含在上下文中）
- **URL 清理增强**：清理代码块和内联代码中的 URL

---

## 工作目标

### 核心目标

1. 限制上下文在当前 heading 的内容范围内
2. 清理所有 markdown 格式的 URL（代码块、内联代码）
3. 保持词数限制（100 词）和对称截断逻辑

### 具体交付物

- 修改后的 `content_searcher.py`
- 修改后的 `common_utils.py`

### 完成定义

- [ ] 向上文扩展不包含 heading，遇到 heading 停止
- [ ] 向下文扩展不包含 heading，遇到 heading 停止
- [ ] 返回的上下文不包含 `# heading` 行
- [ ] 代码块 ```url``` 中的 URL 被清理
- [ ] 内联代码 `url` 中的 URL 被清理
- [ ] 原有测试通过

---

## 验证策略

### 测试基础设施

- **基础设施存在**：是
- **用户想要测试**：是（TDD）
- **测试框架**：pytest

### 单元测试场景

```python
# 1. Heading 边界测试
def test_context_stays_within_heading_boundaries():
    """上下文不应超出上下 heading 的范围"""
    content = """# Title
content before
## Subsection
matched content
## Next Subsection
content after
"""
    # 向上扩展到 "## Subsection" 停止
    # 向下扩展到 "## Next Subsection" 停止
    # 返回内容不包含任何 heading

# 2. Heading 排除测试
def test_context_excludes_headings():
    """返回的上下文中不应包含 heading 行"""
    # 验证 heading 行被过滤

# 3. URL 清理增强测试
def test_url_cleaning_in_code_blocks():
    """代码块中的 URL 应被清理"""
    content = "```\nhttps://example.com\n```"
    # 验证 URL 被清理

def test_url_cleaning_in_inline_code():
    """内联代码中的 URL 应被清理"""
    content = "Use `https://example.com` for testing"
    # 验证 URL 被清理

# 4. 边界情况测试
def test_no_previous_heading():
    """匹配行在文件开头时"""
    # 向上扩展到文件开头

def test_no_next_heading():
    """匹配行在文件末尾时"""
    # 向下扩展到文件末尾
```

---

## 执行策略

### 依赖关系

| 任务 | 依赖 | 阻塞 |
|------|------|------|
| 1. 创建边界检测方法 | 无 | 无 |
| 2. 修改 `_extract_context` | 1 | 无 |
| 3. 增强 URL 清理 | 无 | 无 |
| 4. 更新截断方法 | 2 | 无 |
| 5. 编写测试 | 2, 3, 4 | 无 |
| 6. 运行测试验证 | 5 | 无 |

### Agent 调度

| 阶段 | 任务 | 推荐代理 |
|------|------|----------|
| 1 | 边界检测实现 | `category=unspecified-low` |
| 2 | 上下文提取修改 | `category=unspecified-medium` |
| 3 | URL 清理增强 | `category=quick` |
| 4 | 截断方法更新 | `category=quick` |
| 5-6 | 测试编写与运行 | `category=unspecified-low` |

---

## 任务清单

### 任务 1: 创建 heading 边界检测方法

**添加方法 `_find_heading_boundaries`**：

```python
def _find_heading_boundaries(
    self, lines: List[str], match_line: int
) -> Tuple[int, int]:
    """查找当前 heading 的上下边界。

    向上查找最近的 heading 作为上边界，
    向下查找最近的 heading 作为下边界。

    Args:
        lines: 文件所有行
        match_line: 匹配行号（1-based）

    Returns:
        (上边界行号, 下边界行号)
        - 上边界：最近 heading 的下一行（不包含 heading）
        - 下边界：最近 heading 的上一行（不包含 heading）
    """
```

**逻辑**：
- 从 `match_line` 向前扫描，找到最近的 `# heading`，记录其下一行作为上边界
- 从 `match_line` 向后扫描，找到最近的 `# heading`，记录其上一行作为下边界
- 无 heading 时使用文件边界（0 和 len(lines)）

### 任务 2: 修改 `_extract_context` 方法

**修改参数和逻辑**：

```python
def _extract_context(
    self, lines: List[str], match_line: int, context_size: int = 2
) -> str:
    """提取匹配行周围的上下文（限制在 heading 边界内）。

    变更：
    - 上下文扩展不超出 heading 边界
    - 返回内容不包含 heading 行
    - 词数限制从 100 改为 80（因边界限制可能更短）
    """
```

**实现要点**：
1. 调用 `_find_heading_boundaries` 获取边界
2. 扩展时检查是否触及边界
3. 收集非 heading 行
4. 过滤 heading 行后统计词数
5. 超过词数限制时使用 `_truncate_symmetric`

### 任务 3: 增强 URL 清理方法

**修改 `clean_context_from_urls`**（`common_utils.py`）：

```python
def clean_context_from_urls(context: str) -> str:
    """清理上下文中的 URL 信息。

    增强清理：
    1. Markdown 链接: [text](url) -> text
    2. 尖括号链接: <url> -> url
    3. 锚点链接: : https://...
    4. 纯 URL: http://...
    5. 代码块中的 URL: ```url```
    6. 内联代码中的 URL: `url`
    """
```

### 任务 4: 更新 `_truncate_symmetric` 方法

**检查边界限制**：

```python
def _truncate_symmetric(
    self, lines: List[str], match_idx: int, max_words: int
) -> str:
    """截断文本到目标词数。

    增强：截断后仍需排除 heading 行
    """
    # 过滤 heading 行后再截断
```

### 任务 5: 编写测试

**测试文件**：`tests/test_content_searcher.py`

### 任务 6: 运行测试验证

```bash
pytest tests/test_content_searcher.py -v
```

---

## 关键实现细节

### Heading 边界检测算法

```python
def _find_heading_boundaries(self, lines: List[str], match_line: int) -> Tuple[int, int]:
    """返回 (start_idx, end_idx) 表示可扩展的上下文范围。"""
    match_idx = match_line - 1  # 0-based

    # 向上查找最近的 heading
    upper_bound = 0
    for i in range(match_idx - 1, -1, -1):
        line = lines[i].strip()
        if line.startswith("#"):
            upper_bound = i + 1  # heading 的下一行开始
            break

    # 向下查找最近的 heading
    lower_bound = len(lines)
    for i in range(match_idx + 1, len(lines)):
        line = lines[i].strip()
        if line.startswith("#"):
            lower_bound = i  # heading 的上一行结束
            break

    return (upper_bound, lower_bound)
```

### 上下文提取边界限制

```python
def _extract_context(self, lines: List[str], match_line: int, context_size: int = 2) -> str:
    # 获取 heading 边界
    upper_bound, lower_bound = self._find_heading_boundaries(lines, match_line)
    match_idx = match_line - 1

    # 扩展时检查边界
    current_size = context_size
    while current_size < max_context_size:
        start_idx = max(upper_bound, match_idx - current_size)
        end_idx = min(lower_bound, match_idx + current_size + 1)

        # 提取并过滤 heading 行
        context_lines = []
        for i in range(start_idx, end_idx):
            line = lines[i].strip()
            if line.startswith("#"):
                continue  # 排除 heading
            # 移除 leading --- 等
            line = re.sub(r"^---+\s*", "", line)
            if line:
                context_lines.append(line)

        # 检查词数...
```

### 代码块 URL 清理

```python
# 清理代码块中的 URL
code_block_pattern = re.compile(r'```[^`]*?https?://[^\s]*?```', re.DOTALL)
cleaned = code_block_pattern.sub("", cleaned)

# 清理内联代码中的 URL
inline_code_pattern = re.compile(r'`[^`]*?https?://[^\s]*?`')
cleaned = inline_code_pattern.sub("", cleaned)
```

---

## 提交策略

| 任务 | 提交信息 | 文件 |
|------|----------|------|
| 1 | `feat(searcher): add heading boundary detection method` | content_searcher.py |
| 2 | `feat(searcher): limit context within heading boundaries` | content_searcher.py |
| 3 | `feat(searcher): enhance URL cleaning for code blocks` | common_utils.py |
| 4 | `refactor(searcher): update truncation to exclude headings` | content_searcher.py |
| 5-6 | `test(searcher): add tests for boundary and URL cleaning` | test_content_searcher.py |

---

## 成功标准

1. **Heading 边界限制**：
   - [ ] 向上文扩展遇到 heading 立即停止
   - [ ] 向下文扩展遇到 heading 立即停止
   - [ ] 返回上下文不包含 heading 行

2. **URL 清理增强**：
   - [ ] 代码块 ```url``` 中的 URL 被清理
   - [ ] 内联代码 `url` 中的 URL 被清理

3. **功能兼容**：
   - [ ] 词数限制（80-100 词）正常工作
   - [ ] 对称截断逻辑正常
   - [ ] 所有现有测试通过

4. **代码质量**：
   - [ ] 类型注解完整
   - [ ] 注释清晰
   - [ ] 无 pylint/lint 警告
