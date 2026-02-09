# Fix: DolphinScheduler API文档格式化问题

## TL;DR

> **Quick Summary**: 修复 `api_doc_formatter.py` 中的4个关键问题，使其能正确处理Sphinx生成的Python API文档（如DolphinScheduler）
> 
> **Deliverables**: 
> - 修复CSS选择器匹配（多词类名）
> - 修复嵌套结构处理（递归解析）
> - 修复标题插入位置（在`<dd>`内部而非`<dt>`之前）
> - 修复Markdown匹配精度（避免误匹配）
> 
> **Estimated Effort**: Medium (4-6小时)
> **Parallel Execution**: NO - 顺序修复
> **Critical Path**: Task 1 → Task 2 → Task 3 → Task 4

---

## Context

### Original Request
用户提供了一份详细的分析报告，指出 `api_doc_formatter.py` 在处理 DolphinScheduler API 文档时存在多个问题，导致无法正确生成Markdown标题结构。

### Interview Summary
**Key Discussions**:
- 用户已详细分析4个具体问题（见附录分析报告）
- 确认问题存在于生产代码中
- 需要修复以支持DolphinScheduler和其他Sphinx文档

**Research Findings** (from Oracle consultation):
1. **CSS选择器问题**: `soup.select('dl.py.class')` 对多词类名处理不稳定
2. **嵌套结构**: 需要使用 `find()` 而不是 `find_all()` 来避免递归问题
3. **标题插入**: 应该在 `<dd>` 内部而不是 `<dt>` 之前
4. **Markdown匹配**: 需要添加上下文验证避免误匹配

**Additional Findings** (from Librarian research):
- Sphinx生成HTML使用 `<dl class="py class">` 等结构
- BeautifulSoup的CSS选择器对多词类名支持有限
- html2text不原生支持定义列表(dl/dt/dd)

### Metis Review
**Identified Gaps** (addressed in plan):
- 需要同步更新测试文件（当前引用旧类名）
- 应添加单元测试用例
- 需要考虑性能影响（嵌套遍历）

---

## Work Objectives

### Core Objective
修复 `api_doc_formatter.py` 中的4个关键问题，使其能正确检测和处理Sphinx生成的Python API文档结构。

### Concrete Deliverables
- 文件 `doc4llm/crawler/api_doc_formatter.py` - 修复后的代码
- 文件 `tests/test_api_doc_formatter.py` - 更新测试（类名匹配）
- 修复验证：通过 debug_api_enhancement.py 测试

### Definition of Done
- [ ] CSS选择器能正确匹配 `class="py class"`
- [ ] 嵌套结构（类包含方法）被完整解析
- [ ] 标题插入到 `<dd>` 内部
- [ ] Markdown匹配无明显的误匹配
- [ ] debug_api_enhancement.py 测试通过
- [ ] 所有现有测试通过

### Must Have
- Sphinx Python文档（DolphinScheduler）能正确增强
- 向后兼容（不影响其他文档类型）
- 调试输出保持清晰

### Must NOT Have (Guardrails)
- 不引入破坏性API变更
- 不过度重构（保持现有架构）
- 不降低性能（复杂度保持O(n)）

---

## Verification Strategy (MANDATORY)

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.

### Test Decision
- **Infrastructure exists**: YES (pytest in tests/)
- **Automated tests**: Tests-after (先修复后补测试)
- **Framework**: pytest (通过测试文件验证)

### Agent-Executed QA Scenarios (MANDATORY — ALL tasks)

**Verification Tools**:
| Type | Tool | How Agent Verifies |
|------|------|-------------------|
| **Library/Module** | Bash (bun/node REPL) | Import, call functions, compare output |
| **Test Execution** | Bash (pytest) | Run tests, verify PASS status |

---

## Execution Strategy

### Sequential Execution
```
Task 1: Fix CSS selector matching (高优先级)
    ↓
Task 2: Fix nested structure handling (依赖 Task 1)
    ↓
Task 3: Fix title insertion location (依赖 Task 2)
    ↓
Task 4: Fix markdown matching precision (依赖 Task 3)
    ↓
Task 5: Update tests and verify (最终验证)
```

### Dependency Matrix
| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3, 4 | None |
| 2 | 1 | 3, 4 | None |
| 3 | 1, 2 | 4 | None |
| 4 | 1, 2, 3 | 5 | None |
| 5 | All | None | None |

---

## TODOs

- [ ] 1. Fix CSS selector matching for multi-word class names

  **What to do**:
  - 修改 `is_api_documentation()` 方法 (lines 523-530)
  - 修改 `_detect_dolphinscheduler_structure()` 中的选择器 (lines 166, 184)
  - 将 `'dl.py.class'` 改为 `soup.find_all('dl', class_=re.compile(r'\bpy\b'))`
  - 或使用 `soup.find_all('dl', class_=['py', 'class'])` (AND逻辑)

  **Must NOT do**:
  - 不要改变API检测的URL模式部分
  - 不要删除现有的检测指标

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain` (需要理解BeautifulSoup选择器逻辑)
  - **Skills**: `python`, `beautifulsoup4`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: None (can start immediately)
  - **Blocks**: Task 2, Task 3, Task 4

  **References** (CRITICAL):
  - `doc4llm/crawler/api_doc_formatter.py:506-537` - `is_api_documentation()`
  - `doc4llm/crawler/api_doc_formatter.py:162-211` - `_detect_dolphinscheduler_structure()`
  - Research: BeautifulSoup `class_` 参数支持列表（AND逻辑）

  **Acceptance Criteria**:
  - [ ] 运行测试 `python debug_api_enhancement.py` 时，`is_api_documentation()` 返回 True
  - [ ] `soup.find_all('dl', class_=re.compile(r'\bpy\b'))` 能找到所有py类元素

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Verify CSS selector matches Sphinx HTML
    Tool: Bash (python REPL)
    Preconditions: None
    Steps:
      1. cd /Users/zorro/project/doc4llm
      2. python3 -c "
          from bs4 import BeautifulSoup
          import re
          html = '<dl class=\"py class\"><dt id=\"Test\">Test</dt></dl>'
          soup = BeautifulSoup(html, 'html.parser')
          # Test 1: CSS selector
          result1 = soup.select('dl.py.class')
          print(f'CSS selector found: {len(result1)} items')
          # Test 2: find_all with regex
          result2 = soup.find_all('dl', class_=re.compile(r'\bpy\b'))
          print(f'Regex found: {len(result2)} items')
          # Test 3: find_all with list
          result3 = soup.find_all('dl', class_=['py', 'class'])
          print(f'List found: {len(result3)} items')
          assert len(result1) > 0 or len(result2) > 0, 'No elements found!'
          print('SUCCESS: Selector works')
      "
    Expected Result: All three methods find the dl element
    Failure Indicators: Assertion error or 0 items found
  ```

  **Commit**: YES
  - Message: `fix(api_formatter): fix CSS selector for multi-word class names`
  - Files: `doc4llm/crawler/api_doc_formatter.py`
  - Pre-commit: `python debug_api_enhancement.py`

---

- [ ] 2. Fix nested dl structure handling

  **What to do**:
  - 修改 `_detect_dolphinscheduler_structure()` (lines 166-211)
  - 将 `soup.find_all('dl', ...)` 改为对每个顶级dl使用 `dl.find('dt', id=True)`
  - 确保只处理直接子元素，避免递归问题
  - 添加父级跟踪以保持层级关系

  **Must NOT do**:
  - 不要修改通用API模式检测逻辑（lines 116-144）
  - 不要改变返回的数据结构格式

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain` (需要理解嵌套遍历逻辑)
  - **Skills**: `python`, `beautifulsoup4`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 1
  - **Blocks**: Task 3, Task 4

  **References** (CRITICAL):
  - `doc4llm/crawler/api_doc_formatter.py:166-211` - `_detect_dolphinscheduler_structure()`
  - 关键：使用 `dl.find('dt', id=True)` 而不是 `dl.find_all('dt')`

  **Acceptance Criteria**:
  - [ ] 方法能正确识别嵌套在类dl中的方法dl
  - [ ] 返回的api_items包含正确的层级关系
  - [ ] 类的子方法被正确关联到类

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Verify nested structure detection
    Tool: Bash (python)
    Preconditions: Task 1 completed
    Steps:
      1. python3 -c "
          from doc4llm.crawler.api_doc_formatter import APIDocFormatter
          from bs4 import BeautifulSoup
          html = '''
          <dl class=\"py class\">
            <dt id=\"Engine\"><em class=\"sig-name\">Engine</em></dt>
            <dd>
              <dl class=\"py method\">
                <dt id=\"method1\"><em class=\"sig-name\">method1</em></dt>
              </dl>
            </dd>
          </dl>
          '''
          soup = BeautifulSoup(html, 'html.parser')
          formatter = APIDocFormatter(debug_mode=True)
          items = formatter._detect_dolphinscheduler_structure(soup)
          print(f'Found {len(items)} items')
          for item in items:
              print(f'  - {item[\"type\"]}: {item[\"title\"]} (level {item[\"level\"]})')
          assert len(items) >= 2, f'Expected at least 2 items, got {len(items)}'
          class_items = [i for i in items if i['type'] == 'class']
          method_items = [i for i in items if i['type'] == 'method']
          assert len(class_items) == 1, f'Expected 1 class, got {len(class_items)}'
          assert len(method_items) == 1, f'Expected 1 method, got {len(method_items)}'
          print('SUCCESS: Nested structure handled correctly')
      "
    Expected Result: Found 2 items (1 class + 1 method)
    Failure Indicators: Missing method or incorrect count
  ```

  **Commit**: YES
  - Message: `fix(api_formatter): fix nested dl structure handling`
  - Files: `doc4llm/crawler/api_doc_formatter.py`
  - Pre-commit: `python debug_api_enhancement.py`

---

- [ ] 3. Fix title insertion location

  **What to do**:
  - 修改 `format_api_content()` 方法 (lines 444-459)
  - 创建新方法 `_insert_heading_in_dd()`
  - 使用 `dt.find_next_sibling('dd')` 找到对应的 dd 元素
  - 在 dd 内部插入标题作为第一个子元素
  - 添加fallback：如果找不到dd，则在dt之前插入

  **Must NOT do**:
  - 不要删除现有的 insert_before 调用（改为fallback）
  - 不要改变返回值的结构

  **Recommended Agent Profile**:
  - **Category**: `quick` (简单修改，但需小心测试)
  - **Skills**: `python`, `beautifulsoup4`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 1, Task 2
  - **Blocks**: Task 4

  **References** (CRITICAL):
  - `doc4llm/crawler/api_doc_formatter.py:444-459` - 标题插入逻辑
  - BeautifulSoup: `element.find_next_sibling()`, `element.insert()`

  **Acceptance Criteria**:
  - [ ] 标题被插入到 `<dd>` 内部
  - [ ] 标题出现在文档内容之前
  - [ ] Fallback机制在找不到dd时正常工作

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Verify title insertion location
    Tool: Bash (python)
    Preconditions: Task 1, 2 completed
    Steps:
      1. python3 -c "
          from doc4llm.crawler.api_doc_formatter import APIDocFormatter
          from bs4 import BeautifulSoup
          html = '''
          <dl class=\"py class\">
            <dt id=\"Engine\"><em class=\"sig-name\">Engine</em></dt>
            <dd>
              <p>Class description</p>
            </dd>
          </dl>
          '''
          formatter = APIDocFormatter(debug_mode=True)
          result_html, info = formatter.format_api_content(html, 'test://url')
          soup = BeautifulSoup(result_html, 'html.parser')
          dd = soup.find('dd')
          h2 = dd.find('h2')
          print(f'DD content: {dd}')
          assert h2 is not None, 'h2 not found inside dd!'
          assert h2.get_text() == 'Engine', f'Wrong title: {h2.get_text()}'
          print('SUCCESS: Title inserted inside dd correctly')
      "
    Expected Result: h2 element found inside dd element
    Failure Indicators: h2 not found or wrong location
  ```

  **Commit**: YES
  - Message: `fix(api_formatter): insert headings inside dd instead of before dt`
  - Files: `doc4llm/crawler/api_doc_formatter.py`
  - Pre-commit: `python debug_api_enhancement.py`

---

- [ ] 4. Fix markdown matching precision

  **What to do**:
  - 修改 `enhance_markdown_content()` 方法 (lines 607-626)
  - 创建验证方法 `_is_valid_api_match()`
  - 添加检查：跳过代码块（包含```或`）
  - 添加检查：跳过URLs（包含http://或https://）
  - 使用负向回顾/前瞻确保精确匹配
  - 保留现有的单词边界匹配逻辑

  **Must NOT do**:
  - 不要完全重写匹配逻辑，保持向后兼容
  - 不要移除对括号后参数的处理

  **Recommended Agent Profile**:
  - **Category**: `quick` (添加验证逻辑)
  - **Skills**: `python`, `regex`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 1, 2, 3
  - **Blocks**: Task 5

  **References** (CRITICAL):
  - `doc4llm/crawler/api_doc_formatter.py:607-626` - Markdown增强逻辑
  - Oracle建议：使用 `(?&lt;![.\w])` 和 `(?![(\w])` 作为边界

  **Acceptance Criteria**:
  - [ ] 不会匹配代码块内的API名称
  - [ ] 不会匹配URL中的API名称
  - [ ] 不会匹配描述性文本（如 "The Engine class" 不会匹配 "Engine"）

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Verify markdown matching precision
    Tool: Bash (python)
    Preconditions: Task 1, 2, 3 completed
    Steps:
      1. python3 -c "
          from doc4llm.crawler.api_doc_formatter import APIDocEnhancer
          markdown = '''
Engine description here.
```python
# This is Engine class
class Engine:
    pass
```
See https://example.com/Engine for details.
          '''
          api_info = {'api_items': [{'title': 'Engine', 'level': 2}]}
          enhancer = APIDocEnhancer(None, debug_mode=True)
          result = enhancer.enhance_markdown_content(markdown, api_info, 'test://url')
          print(f'Result: {result}')
          # Should NOT insert heading in code block or URL
          code_block = result.count('```python')
          assert code_block > 0, 'Code block was modified!'
          url_intact = 'https://example.com/Engine' in result
          assert url_intact, 'URL was modified!'
          print('SUCCESS: Matching is precise')
      "
    Expected Result: Code block and URL remain unchanged
    Failure Indicators: Heading inserted in wrong places
  ```

  **Commit**: YES
  - Message: `fix(api_formatter): improve markdown matching precision`
  - Files: `doc4llm/crawler/api_doc_formatter.py`
  - Pre-commit: `python debug_api_enhancement.py`

---

- [ ] 5. Update tests and final verification

  **What to do**:
  - 更新 `tests/test_api_doc_formatter.py`
  - 将 `ApiDocTitleFormatter` 引用改为 `APIDocFormatter`
  - 添加新的测试用例覆盖修复的问题
  - 运行 `pytest tests/test_api_doc_formatter.py -v`
  - 运行 `python debug_api_enhancement.py` 验证完整流程

  **Must NOT do**:
  - 不要删除现有测试（即使它们引用旧类名，先更新引用）
  - 不要引入破坏性测试变更

  **Recommended Agent Profile**:
  - **Category**: `quick` (测试更新)
  - **Skills**: `python`, `pytest`

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocked By**: Task 1, 2, 3, 4
  - **Blocks**: None (final task)

  **References** (CRITICAL):
  - `tests/test_api_doc_formatter.py` - 测试文件
  - `debug_api_enhancement.py` - 完整流程验证

  **Acceptance Criteria**:
  - [ ] `pytest tests/test_api_doc_formatter.py` 全部通过
  - [ ] `python debug_api_enhancement.py` 无错误
  - [ ] 检测到API项数量正确
  - [ ] 标题结构完整

  **Agent-Executed QA Scenarios**:
  ```
  Scenario: Run all tests and verification
    Tool: Bash
    Preconditions: All previous tasks completed
    Steps:
      1. cd /Users/zorro/project/doc4llm
      2. pytest tests/test_api_doc_formatter.py -v
      3. echo $?
      4. python debug_api_enhancement.py 2>&1 | tail -20
    Expected Result: 
      - pytest exit code 0
      - debug_api_enhancement.py 输出 "SUCCESS" 或无错误
    Failure Indicators: 
      - pytest exit code != 0
      - 检测到0个API项
      - 异常堆栈
  ```

  **Commit**: YES
  - Message: `test(api_formatter): update tests for APIDocFormatter`
  - Files: `tests/test_api_doc_formatter.py`
  - Pre-commit: `pytest tests/test_api_doc_formatter.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `fix(api_formatter): fix CSS selector for multi-word class names` | api_doc_formatter.py | python debug_api_enhancement.py |
| 2 | `fix(api_formatter): fix nested dl structure handling` | api_doc_formatter.py | python debug_api_enhancement.py |
| 3 | `fix(api_formatter): insert headings inside dd instead of before dt` | api_doc_formatter.py | python debug_api_enhancement.py |
| 4 | `fix(api_formatter): improve markdown matching precision` | api_doc_formatter.py | python debug_api_enhancement.py |
| 5 | `test(api_formatter): update tests for APIDocFormatter` | test_api_doc_formatter.py | pytest tests/test_api_doc_formatter.py |

---

## Success Criteria

### Verification Commands
```bash
# 1. Run unit tests
pytest tests/test_api_doc_formatter.py -v

# 2. Run debug script
python debug_api_enhancement.py

# 3. Manual verification (if needed)
python -c "
from doc4llm.crawler.api_doc_formatter import APIDocEnhancer
# Test code here
"
```

### Final Checklist
- [ ] All unit tests pass
- [ ] debug_api_enhancement.py runs without errors
- [ ] DolphinScheduler API structure detected correctly
- [ ] Titles inserted at correct locations
- [ ] Markdown enhanced with proper headings
- [ ] No false positive matches in markdown

---

## Appendix: User's Analysis Report Summary

### Problem 1: CSS Selector Mismatch
- **Location**: `is_api_documentation()` lines 523-530
- **Issue**: `'dl.py.class'` CSS selector doesn't match `class="py class"`
- **Impact**: API detection fails for Sphinx docs

### Problem 2: Nested Structure Handling
- **Location**: `_detect_dolphinscheduler_structure()` lines 166-211
- **Issue**: `find_all()` returns all matching dl elements, flattening hierarchy
- **Impact**: Methods nested inside classes are not associated correctly

### Problem 3: Title Insertion Location
- **Location**: `format_api_content()` lines 444-459
- **Issue**: `insert_before()` puts title before `<dt>` instead of inside `<dd>`
- **Impact**: Headings appear in wrong place in output

### Problem 4: Loose Markdown Matching
- **Location**: `enhance_markdown_content()` lines 607-626
- **Issue**: `'Engine' in line` matches any occurrence, not just API definitions
- **Impact**: False positive heading insertions

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| BeautifulSoup版本差异 | Medium | Medium | 测试多种选择器方法 |
| Sphinx版本HTML差异 | Low | Low | 使用通用模式+容错 |
| 性能下降 | Low | Low | 保持O(n)复杂度 |
| 向后兼容性破坏 | Low | High | 保持现有API不变 |

---

*Plan generated by Prometheus (Plan Builder)*
*Based on user analysis and Oracle consultation*
*Last updated: 2026-02-05*
