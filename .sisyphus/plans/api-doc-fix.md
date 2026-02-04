# API 文档锚点标题注入 - 实施计划

## TL;DR

> **快速摘要**: 为 Sphinx autodoc 生成的 API 文档（如 dolphinscheduler api.html）自动注入 Markdown 标题，解决 docReaderAPI 无法按标题提取内容的问题
> 
> **交付物**: 
> - `DocContentCrawler.py` 新增 `_inject_api_anchor_headings()` 方法
> - 配置项 `api_doc_mode` 支持自动检测
> - dolphinscheduler 文档验证测试
> 
> **预估工作量**: Short
> **并行执行**: YES - 3 waves
> **关键路径**: 命名空间解析 → 标题注入 → 配置集成 → 验证测试

---

## Context

### 原始请求
用户反馈 dolphinscheduler API 文档爬取后，`docContent.md` 中类、方法等没有标题，导致 `doc_reader_api.py` 的 `extract_section_by_title()` 无法按 docTOC.md 中的标题定位内容。

### 问题根因
Sphinx autodoc 生成的 API 页面使用 `<dt id="...">` 锚点定义类/方法，但**正文没有 Markdown 标题**：
- docTOC.md 正确提取了锚点：`### Engine._get_attr()`
- docContent.md 缺少对应标题 → 提取失败

### 研究发现
- Dolphinscheduler 使用 Sphinx autodoc 生成 Python API 文档
- 锚点 ID 格式：`pydolphinscheduler.core.Engine._get_attr`
- 可通过解析命名空间自动生成对应标题

---

## Work Objectives

### Core Objective
在 `DocContentCrawler._convert_to_markdown()` 中新增 API 锚点标题自动注入功能，使 docReaderAPI 能按标题提取内容。

### Concrete Deliverables
- `doc4llm/crawler/DocContentCrawler.py`: 新增 `_inject_api_anchor_headings()` 方法
- `doc4llm/filter/enhanced.py`: 增强框架检测支持 Sphinx autodoc
- 配置示例: dolphinscheduler.json API 模式配置

### Definition of Done
- [ ] dolphinscheduler api.html 爬取后 docContent.md 包含类/方法标题
- [ ] docReaderAPI.extract_by_headings() 能定位 `Engine._get_attr()` 等章节
- [ ] 现有普通文档不受影响（向后兼容）
- [ ] 配置项 `api_doc_mode: "auto"` 默认启用

### Must Have
- 自动检测 Sphinx autodoc 页面
- 正确解析 Python 命名空间（如 `pydolphinscheduler.core.Engine._get_attr`）
- 按层级注入 Markdown 标题（`### Class`, `#### Class.method`）
- 向后兼容非 API 页面

### Must NOT Have (Guardrails)
- 不修改 docTOC.md 生成逻辑
- 不修改 doc_reader_api.py 现有接口
- 不引入外部依赖（使用内置 re/BeautifulSoup）
- 不破坏现有过滤流程

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
> 所有验证由 Agent 执行，无需人工干预。

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: NO (验证通过 Agent QA Scenarios)
- **Framework**: N/A

### Agent-Executed QA Scenarios

**Scenario 1: dolphinscheduler api.html 锚点标题注入验证**
```
Tool: Bash (Python script)
Preconditions: DocContentCrawler can import, dolphinscheduler config exists
Steps:
  1. python -c "
from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.config import ScannerConfig
import json

# Load dolphinscheduler config
with open('/Users/zorro/project/md_docs_base/doc4llmMain/Config/dolphinscheduler.json') as f:
    config_data = json.load(f)

# Create config and crawler
config = ScannerConfig(**config_data)
crawler = DocContentCrawler(config)

# Test autodoc detection
html_sample = '''
<html><body>
<dt id=\"pydolphinscheduler.core.Engine\">
  <span class=\"sig-name\">Engine</span>
</dt>
<dd><p>Engine class docstring</p></dd>
<dt id=\"pydolphinscheduler.core.Engine._get_attr\">
  <span class=\"sig-name\">_get_attr() → set[str]</span>
</dt>
<dd><p>Method docstring</p></dd>
</body></html>
'''
from bs4 import BeautifulSoup
soup = BeautifulSoup(html_sample, 'html.parser')
is_autodoc = crawler._is_sphinx_autodoc_page(soup)
print(f'Auto-detect result: {is_autodoc}')

# Test namespace parsing
ns_info = crawler._parse_python_namespace('pydolphinscheduler.core.Engine._get_attr')
print(f'Namespace parse: {ns_info}')
"
Expected Result: 
  - Auto-detect returns True for Sphinx autodoc page
  - Namespace parse returns: {'module': 'pydolphinscheduler.core', 'class': 'Engine', 'method': '_get_attr', 'level': 4}
Evidence: Python script stdout output captured
```

**Scenario 2: Markdown 标题注入验证**
```
Tool: Bash (Python script)
Preconditions: DocContentCrawler._inject_api_anchor_headings implemented
Steps:
  1. python -c "
from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.config import ScannerConfig
import json

# Load dolphinscheduler config
with open('/Users/zorro/project/md_docs_base/doc4llmMain/Config/dolphinscheduler.json') as f:
    config_data = json.load(f)

config = ScannerConfig(**config_data)
crawler = DocContentCrawler(config)

# Test heading injection
html_input = '''<html><body>
<dt id=\"pydolphinscheduler.core.Engine\">
  <span class=\"sig-name\">Engine</span>
</dt>
<dd><p>Engine class docstring</p></dd>
</body></html>'''

markdown_input = '''# API

Some content here.

'''

from bs4 import BeautifulSoup
soup = BeautifulSoup(html_input, 'html.parser')
result = crawler._inject_api_anchor_headings(markdown_input, soup, 'https://example.com/api.html')

# Check result contains expected headings
assert '### Engine' in result, 'Class heading not found'
print('✓ Class heading injected')
print('Result markdown:')
print(result)
"
Expected Result:
  - Result contains '### Engine' heading
  - No errors during execution
Evidence: Python script stdout with assertion results
```

**Scenario 3: docReaderAPI 集成验证**
```
Tool: Bash (Python script)
Preconditions: dolphinscheduler docs already crawled with new feature
Steps:
  1. ls /Users/zorro/project/md_docs_base/DolpinScheduler_Docs@latest/API/
  2. cat /Users/zorro/project/md_docs_base/DolpinScheduler_Docs@latest/API/docContent.md | grep -E '^###|^####' | head -20
  3. python -c "
from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI

reader = DocReaderAPI(base_dir='/Users/zorro/project/md_docs_base')
result = reader.extract_multi_by_headings(sections=[
        {'title': 'API', 'headings': ['Engine', 'Engine._get_attr()'], 'doc_set': 'DolpinScheduler_Docs@latest'}
    ])
print(f'Extracted sections: {list(result.contents.keys())}')
if result.contents:
    for key, content in result.contents.items():
        print(f'\\n=== {key} ===')
        print(content[:500])
"
Expected Result:
  - docContent.md contains '### Engine' and '#### Engine._get_attr()' headings
  - extract_multi_by_headings returns content for 'Engine' and 'Engine._get_attr()' sections
Evidence: Terminal output captured to .sisyphus/evidence/api-integration-test.log
```

**Scenario 4: 向后兼容性验证**
```
Tool: Bash (Python script)
Preconditions: Non-API page HTML available
Steps:
  1. python -c "
from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.config import ScannerConfig
import json

# Load config
with open('/Users/zorro/project/md_docs_base/doc4llmMain/Config/dolphinscheduler.json') as f:
    config_data = json.load(f)

config = ScannerConfig(**config_data)
crawler = DocContentCrawler(config)

# Test non-autodoc page
html_normal = '''<html><body>
<h1>Getting Started</h1>
<p>Welcome to the documentation.</p>
<h2>Installation</h2>
<p>Install with pip.</p>
</body></html>'''

from bs4 import BeautifulSoup
soup = BeautifulSoup(html_normal, 'html.parser')
is_autodoc = crawler._is_sphinx_autodoc_page(soup)
print(f'Normal page auto-detect: {is_autodoc} (should be False)')

# Verify injection doesn't modify normal pages
md = '# Getting Started\n\nWelcome content.'
result = crawler._inject_api_anchor_headings(md, soup, 'https://example.com/docs.html')
assert result == md, 'Normal page was modified!'
print('✓ Normal page unchanged')
"
Expected Result:
  - Non-API page returns False for autodoc detection
  - Markdown content unchanged after injection
Evidence: Python script stdout
```

### Evidence to Capture
- [x] Python script stdout for autodoc detection test
- [x] Markdown output showing injected headings
- [x] docReaderAPI extraction result log
- [x] Compatibility test result log
- [ ] All evidence saved to `.sisyphus/evidence/api-doc-fix-*.log`

---

## Execution Strategy

### Parallel Execution Waves

```
Wave 1 (Start Immediately):
├── Task 1: 实现 _is_sphinx_autodoc_page() 自动检测方法
└── Task 2: 实现 _parse_python_namespace() 命名空间解析

Wave 2 (After Wave 1):
├── Task 3: 实现 _inject_api_anchor_headings() 标题注入
└── Task 4: 集成到 _convert_to_markdown() 主流程

Wave 3 (After Wave 2):
├── Task 5: dolphinscheduler 文档验证测试
└── Task 6: 向后兼容性测试
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|----------------------|
| 1 | None | 3 | 2 |
| 2 | None | 3 | 1 |
| 3 | 1, 2 | 4, 5, 6 | None |
| 4 | 3 | 5, 6 | None |
| 5 | 4 | None | 6 |
| 6 | 4 | None | 5 |

### Agent Dispatch Summary

| Wave | Tasks | Recommended Agents |
|------|-------|-------------------|
| 1 | 1, 2 | `delegate_task(category="quick", load_skills=["ultrabrain"], prompt="...")` |
| 2 | 3, 4 | `delegate_task(category="unspecified-high", load_skills=["ultrabrain"], prompt="...")` |
| 3 | 5, 6 | `delegate_task(category="quick", load_skills=[], prompt="...")` |

---

## TODOs

- [ ] 1. 实现 `_is_sphinx_autodoc_page()` - Sphinx autodoc 页面自动检测

  **What to do**:
  - 检测特征：`<dt id="...">` 元素 + Python 命名空间格式 id + `.sig-name` 类名
  - 返回 True/False
  
  **Must NOT do**:
  - 不修改 HTML 结构
  - 不引入外部依赖

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain` - 需要准确的模式匹配逻辑
  - **Skills**: `ultrabrain` (Python AST/正则分析)
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不需要浏览器交互

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 2)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References** (existing code to follow):
  - `DocContentCrawler._determine_anchor_level_for_element()`: 锚点层级判断逻辑参考
  - `DocUrlCrawler._determine_anchor_level()`: 锚点层级判断逻辑参考

  **API/Type References** (contracts to implement against):
  - `BeautifulSoup.find_all()`: 查找 `<dt id="...">` 元素
  - `re.match()`: 匹配 Python 命名空间格式

  **Test References** (testing patterns to follow):
  - `Scenario 1` in Verification Strategy: 单元测试用例

  **External References** (libraries and frameworks):
  - N/A (使用内置库)

  **WHY Each Reference Matters**:
  - `_determine_anchor_level_for_element()`: 已有的锚点层级判断逻辑可直接复用
  - `BeautifulSoup.find_all()`: 标准 HTML 解析方法

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Sphinx autodoc 页面检测
    Tool: Bash (Python script)
    Preconditions: DocContentCrawler can import
    Steps:
      1. python -c "
from bs4 import BeautifulSoup
from doc4llm.crawler.DocContentCrawler import DocContentCrawler

crawler = DocContentCrawler.__new__(DocContentCrawler)
crawler.debug_mode = False

# Test case 1: Sphinx autodoc HTML
html_autodoc = '''<html><body>
<dt id=\"pydolphinscheduler.core.Engine\">
  <span class=\"sig-name\">Engine</span>
</dt>
</body></html>'''

soup = BeautifulSoup(html_autodoc, 'html.parser')
result = crawler._is_sphinx_autodoc_page(soup)
assert result == True, f'Expected True, got {result}'
print('✓ Sphinx autodoc page detected')

# Test case 2: Normal HTML
html_normal = '''<html><body>
<h1>Getting Started</h1>
</body></html>'''

soup = BeautifulSoup(html_normal, 'html.parser')
result = crawler._is_sphinx_autodoc_page(soup)
assert result == False, f'Expected False, got {result}'
print('✓ Normal page correctly identified')

# Test case 3: Mixed content
html_mixed = '''<html><body>
<h1>API Reference</h1>
<dt id=\"pydolphinscheduler.core.Task\">
  <span class=\"sig-name\">Task</span>
</dt>
</body></html>'''

soup = BeautifulSoup(html_mixed, 'html.parser')
result = crawler._is_sphinx_autodoc_page(soup)
assert result == True, f'Expected True for mixed, got {result}'
print('✓ Mixed content correctly detected')
"
    Expected Result: All 3 test cases pass
    Evidence: Script output in .sisyphus/evidence/task-1-autodetect.log
  \`\`\`

  **Commit**: YES
  - Message: `feat(crawler): add Sphinx autodoc page detection`
  - Files: `doc4llm/crawler/DocContentCrawler.py`
  - Pre-commit: None

- [ ] 2. 实现 `_parse_python_namespace()` - Python 命名空间解析

  **What to do**:
  - 解析锚点 ID 中的 Python 命名空间
  - 提取 module, class, method 信息
  - 返回层级信息 (1-4)
  
  **Must NOT do**:
  - 不修改输入字符串（immutable 操作）
  - 不抛出异常（失败时返回默认值）

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain` - 需要准确的字符串解析逻辑
  - **Skills**: `ultrabrain` (Python 字符串处理)
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不需要浏览器交互

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1 (with Task 1)
  - **Blocks**: Task 3
  - **Blocked By**: None

  **References**:

  **Pattern References** (existing code to follow):
  - `DocUrlCrawler._parse_python_namespace()`: 已有命名空间解析逻辑

  **API/Type References** (contracts to implement against):
  - 返回格式: `dict` with keys: `module`, `class`, `method`, `level`

  **Test References** (testing patterns to follow):
  - `Scenario 1` in Verification Strategy: 命名空间解析测试

  **External References** (libraries and frameworks):
  - N/A (使用内置 `re` 模块)

  **WHY Each Reference Matters**:
  - `DocUrlCrawler._parse_python_namespace()`: 已有实现可参考/复用

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: Python 命名空间解析测试
    Tool: Bash (Python script)
    Preconditions: Method implemented
    Steps:
      1. python -c "
from doc4llm.crawler.DocContentCrawler import DocContentCrawler

crawler = DocContentCrawler.__new__(DocContentCrawler)

# Test cases
tests = [
    ('Engine', {'module': 'Engine', 'class': '', 'method': '', 'level': 1}),
    ('core.Engine', {'module': '', 'class': 'Engine', 'level': 2}),
    ('Task._get_attr', {'module': 'Task', 'class': '', 'method': '_get_attr', 'level': 2}),
    ('pydolphinscheduler.core.Engine', {'module': 'pydolphinscheduler.core', 'class': 'Engine', 'level': 3}),
    ('pydolphinscheduler.core.Engine._get_attr', {'module': 'pydolphinscheduler.core', 'class': 'Engine', 'method': '_get_attr', 'level': 4}),
    ('pydolphinscheduler.tasks.Condition.add_in', {'module': 'pydolphinscheduler.tasks', 'class': 'Condition', 'method': 'add_in', 'level': 4}),
]

for anchor_id, expected in tests:
    result = crawler._parse_python_namespace(anchor_id)
    assert result == expected, f'Failed: {anchor_id} -> {result} != {expected}'
    print(f'✓ {anchor_id}')

print('\\nAll namespace parsing tests passed!')
"
    Expected Result: All test cases pass
    Evidence: Script output in .sisyphus/evidence/task-2-namespace.log
  \`\`\`

  **Commit**: YES
  - Message: `feat(crawler): add Python namespace parsing`
  - Files: `doc4llm/crawler/DocContentCrawler.py`
  - Pre-commit: None

- [ ] 3. 实现 `_inject_api_anchor_headings()` - 锚点标题注入

  **What to do**:
  - 遍历 HTML 中所有带 id 的 API 元素
  - 使用命名空间解析结果生成 Markdown 标题
  - 注入到 markdown_content 中适当位置
  
  **Must NOT do**:
  - 不破坏现有 Markdown 结构
  - 不注入重复标题

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain` - 复杂的 HTML/Markdown 转换逻辑
  - **Skills**: `ultrabrain` (BeautifulSoup 操作)
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不需要浏览器交互

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Tasks 4, 5, 6
  - **Blocked By**: Tasks 1, 2

  **References**:

  **Pattern References** (existing code to follow):
  - `DocContentCrawler._inject_anchor_headings()`: 已有锚点注入逻辑参考
  - `DocContentCrawler._format_heading_markdown()`: 标题格式化逻辑参考

  **API/Type References** (contracts to implement against):
  - 输入: `markdown_content: str`, `soup: BeautifulSoup`, `base_url: str`
  - 输出: `str` (注入标题后的 Markdown)

  **Test References** (testing patterns to follow):
  - `Scenario 2` in Verification Strategy: 标题注入测试

  **External References** (libraries and frameworks):
  - N/A (使用内置库)

  **WHY Each Reference Matters**:
  - `_inject_anchor_headings()`: 已有锚点注入逻辑，API 标题注入类似但针对不同选择器
  - `_format_heading_markdown()`: 标题格式化可直接复用或简化

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: API 锚点标题注入测试
    Tool: Bash (Python script)
    Preconditions: Tasks 1, 2 completed
    Steps:
      1. python -c "
from bs4 import BeautifulSoup
from doc4llm.crawler.DocContentCrawler import DocContentCrawler

crawler = DocContentCrawler.__new__(DocContentCrawler)
crawler.debug_mode = False

# Test HTML input
html = '''<html><body>
<dt id=\"pydolphinscheduler.core.Engine\">
  <span class=\"sig-name\">Engine</span>
</dt>
<dd><p>Engine class docstring here.</p></dd>
<dt id=\"pydolphinscheduler.core.Engine._get_attr\">
  <span class=\"sig-name\">_get_attr() → set[str]</span>
</dt>
<dd><p>Get attribute method.</p></dd>
</body></html>'''

markdown_input = '''# API

## API Reference

Some introduction content.

'''

soup = BeautifulSoup(html, 'html.parser')
result = crawler._inject_api_anchor_headings(markdown_input, soup, 'https://example.com/api.html')

print('=== Result Markdown ===')
print(result)
print('=== End ===')

# Verify headings exist
assert '### Engine' in result, 'Class heading missing'
assert '#### Engine._get_attr' in result, 'Method heading missing'
print('\\n✓ All expected headings found')

# Verify headings are properly formatted
import re
engine_heading = re.search(r'### Engine', result)
attr_heading = re.search(r'#### Engine._get_attr', result)
assert engine_heading and attr_heading, 'Headings not found in correct format'
print('✓ Headings in correct format')
"
    Expected Result: All assertions pass, headings correctly injected
    Evidence: Script output in .sisyphus/evidence/task-3-injection.log
  \`\`\`

  **Commit**: YES
  - Message: `feat(crawler): add API anchor heading injection`
  - Files: `doc4llm/crawler/DocContentCrawler.py`
  - Pre-commit: None

- [ ] 4. 集成到 `_convert_to_markdown()` 主流程

  **What to do**:
  - 在 `_convert_to_markdown()` 方法末尾调用 `_inject_api_anchor_headings()`
  - 添加 `api_doc_mode` 配置支持
  
  **Must NOT do**:
  - 不破坏现有转换逻辑
  - 不影响非 API 页面

  **Recommended Agent Profile**:
  - **Category**: `quick` - 小型集成改动
  - **Skills**: None (直接代码修改)
  - **Skills Evaluated but Omitted**:
    - `ultrabrain`: 不需要深度分析

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Tasks 5, 6
  - **Blocked By**: Task 3

  **References**:

  **Pattern References** (existing code to follow):
  - `DocContentCrawler._convert_to_markdown()`: 现有方法结构参考

  **Test References** (testing patterns to follow):
  - `Scenario 4` in Verification Strategy: 向后兼容性测试

  **External References** (libraries and frameworks):
  - N/A

  **WHY Each Reference Matters**:
  - `_convert_to_markdown()`: 现有方法结构，确定新增调用的插入点

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: 集成到主流程测试
    Tool: Bash (Python script)
    Preconditions: Task 3 completed
    Steps:
      1. python -c "
from doc4llm.crawler.DocContentCrawler import DocContentCrawler
from doc4llm.config import ScannerConfig
import json

# Load config
config_data = {
    'doc_dir': '/tmp/test_docs',
    'doc_name': 'TestDoc',
    'doc_version': 'test',
    'content_filter': {
        'api_doc_mode': 'auto'
    }
}
config = ScannerConfig(**config_data)
crawler = DocContentCrawler(config)

# Verify config loaded
assert hasattr(crawler, 'api_doc_mode'), 'api_doc_mode not set'
print(f'api_doc_mode: {crawler.api_doc_mode}')

# Verify method exists and is callable
assert hasattr(crawler, '_inject_api_anchor_headings'), 'Method not found'
assert callable(crawler._inject_api_anchor_headings), 'Not callable'
print('✓ _inject_api_anchor_headings is callable')

# Verify _convert_to_markdown calls the new method
import inspect
source = inspect.getsource(crawler._convert_to_markdown)
assert '_inject_api_anchor_headings' in source, 'Integration not found'
print('✓ Integration verified in _convert_to_markdown')
"
    Expected Result: All checks pass
    Evidence: Script output in .sisyphus/evidence/task-4-integration.log
  \`\`\`

  **Commit**: YES
  - Message: `feat(crawler): integrate API heading injection into conversion pipeline`
  - Files: `doc4llm/crawler/DocContentCrawler.py`
  - Pre-commit: None

- [ ] 5. dolphinscheduler 文档验证测试

  **What to do**:
  - 使用 dolphinscheduler 配置爬取 api.html
  - 验证 docContent.md 包含正确标题
  - 验证 docReaderAPI 能提取章节
  
  **Must NOT do**:
  - 不修改 dolphinscheduler 配置
  - 不删除已爬取的文档

  **Recommended Agent Profile**:
  - **Category**: `quick` - 验证测试
  - **Skills**: None (执行爬取和验证)
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不需要浏览器操作

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 6)
  - **Blocks**: None
  - **Blocked By**: Task 4

  **References**:

  **Pattern References** (existing code to follow):
  - `dolphinscheduler.json` 配置格式参考

  **Test References** (testing patterns to follow):
  - `Scenario 3` in Verification Strategy: 集成验证测试

  **External References** (libraries and frameworks):
  - dolphinscheduler API URL: `https://dolphinscheduler.apache.org/python/main/api.html`

  **WHY Each Reference Matters**:
  - `dolphinscheduler.json`: 提供目标配置
  - `Scenario 3`: 验证步骤参考

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: dolphinscheduler API 文档验证
    Tool: Bash (Python script + curl/playwright)
    Preconditions: Tasks 1-4 completed, dolphinscheduler config exists
    Steps:
      1. # 先检查是否已有爬取的文档
      2. ls /Users/zorro/project/md_docs_base/DolpinScheduler_Docs@latest/API/ 2>/dev/null || echo "Need to crawl"
      3. 
      4. # 如果需要，重新爬取（使用短超时避免长时间等待）
      5. python -c \"
import sys
sys.path.insert(0, '/Users/zorro/project/doc4llm')
from doc4llm.cli import main
import json

with open('/Users/zorro/project/md_docs_base/doc4llmMain/Config/dolphinscheduler.json') as f:
    config = json.load(f)

# 只爬取 API 页面进行验证
config['mode'] = 4  # Single page mode
config['start_url'] = 'https://dolphinscheduler.apache.org/python/main/api.html'
config['doc_name'] = 'DolpinScheduler_Docs'
config['doc_version'] = 'test-api-fix'
config['force_scan'] = 1

# 临时修改输出目录
import tempfile
import os
temp_dir = tempfile.mkdtemp()
config['doc_dir'] = temp_dir

# 运行爬取
main(['-u', config['start_url'], '-mode', '4', '-doc-dir', temp_dir, '-doc-name', config['doc_name'], '-doc-version', config['doc_version']])
print(f'Documents saved to: {temp_dir}')
\"
      6. 
      7. # 验证结果
      8. python -c \"
import os
import glob

# 查找爬取的 API 文档
api_dirs = glob.glob('/tmp/**/API*/', recursive=True)
if not api_dirs:
    api_dirs = glob.glob('/tmp/**/api*/', recursive=True)

for api_dir in api_dirs:
    doc_content = os.path.join(api_dir, 'docContent.md')
    if os.path.exists(doc_content):
        print(f'Found: {doc_content}')
        with open(doc_content) as f:
            content = f.read()
        
        # 检查标题
        import re
        class_headings = re.findall(r'### \w+', content)
        method_headings = re.findall(r'#### \w+\.\w+', content)
        
        print(f'Class headings: {len(class_headings)}')
        print(f'Method headings: {len(method_headings)}')
        print('Sample class headings:', class_headings[:5])
        print('Sample method headings:', method_headings[:5])
        
        if len(class_headings) > 0 and len(method_headings) > 0:
            print('✓ API headings successfully injected!')
        else:
            print('✗ No API headings found')
\"
    Expected Result: 
      - docContent.md contains class headings (### ...) and method headings (#### ...)
      - docReaderAPI can extract sections by heading
    Evidence: Script output in .sisyphus/evidence/task-5-dolphinscheduler.log
  \`\`\`

  **Commit**: NO (验证测试)
  - Files: None (验证测试，不提交代码)

- [ ] 6. 向后兼容性测试

  **What to do**:
  - 验证非 API 页面不受影响
  - 验证其他文档框架（docusaurus, mintlify 等）不受影响
  
  **Must NOT do**:
  - 不修改现有测试用例

  **Recommended Agent Profile**:
  - **Category**: `quick` - 兼容性验证
  - **Skills**: None (执行验证)
  - **Skills Evaluated but Omitted**:
    - `playwright`: 不需要浏览器操作

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 3 (with Task 5)
  - **Blocks**: None
  - **Blocked By**: Task 4

  **References**:

  **Pattern References** (existing code to follow):
  - `Scenario 4` in Verification Strategy: 向后兼容性测试

  **External References** (libraries and frameworks):
  - N/A

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: 向后兼容性测试
    Tool: Bash (Python script)
    Preconditions: Tasks 1-4 completed
    Steps:
      1. python -c "
from bs4 import BeautifulSoup
from doc4llm.crawler.DocContentCrawler import DocContentCrawler

crawler = DocContentCrawler.__new__(DocContentCrawler)
crawler.debug_mode = False

# Test case 1: Docusaurus-like page
html_docusaurus = '''<html><body>
<div class=\"docMainContainer\">
  <h1>Getting Started</h1>
  <p>Welcome to the docs.</p>
  <h2>Installation</h2>
  <p>Install with npm.</p>
</div>
</body></html>'''

soup = BeautifulSoup(html_docusaurus, 'html.parser')
is_autodoc = crawler._is_sphinx_autodoc_page(soup)
print(f'Docusaurus page detected as autodoc: {is_autodoc} (should be False)')

# Test case 2: Mintlify-like page
html_mintlify = '''<html><body>
<div class=\"mintlify\">
  <h1>API Reference</h1>
  <p>REST API documentation.</p>
</div>
</body></html>'''

soup = BeautifulSoup(html_mintlify, 'html.parser')
is_autodoc = crawler._is_sphinx_autodoc_page(soup)
print(f'Mintlify page detected as autodoc: {is_autodoc} (should be False)')

# Test case 3: Normal HTML page
html_normal = '''<html><body>
<h1>Home</h1>
<p>Welcome to our website.</p>
</body></html>'''

soup = BeautifulSoup(html_normal, 'html.parser')
is_autodoc = crawler._is_sphinx_autodoc_page(soup)
print(f'Normal page detected as autodoc: {is_autodoc} (should be False)')

# Test injection doesn't modify normal pages
md = '# Getting Started\\n\\nWelcome content.\\n\\n## Installation\\n\\nInstall here.'
result = crawler._inject_api_anchor_headings(md, soup, 'https://example.com/docs.html')
assert result == md, f'Normal page was modified!'
print('✓ Normal page unchanged after injection')

# Verify markdown content preserved
assert '# Getting Started' in result, 'Content missing'
assert '## Installation' in result, 'Section missing'
print('✓ All original content preserved')

print('\\n=== All compatibility tests passed ===')
"
    Expected Result: All tests pass, normal pages unaffected
    Evidence: Script output in .sisyphus/evidence/task-6-compatibility.log
  \`\`\`

  **Commit**: NO (验证测试)
  - Files: None (验证测试，不提交代码)

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(crawler): add Sphinx autodoc page detection` | `DocContentCrawler.py` | Test passes |
| 2 | `feat(crawler): add Python namespace parsing` | `DocContentCrawler.py` | Test passes |
| 3 | `feat(crawler): add API anchor heading injection` | `DocContentCrawler.py` | Test passes |
| 4 | `feat(crawler): integrate API heading injection into conversion pipeline` | `DocContentCrawler.py` | Test passes |

---

## Success Criteria

### Verification Commands
```bash
# 1. Autodoc detection test
python -c "from doc4llm.crawler.DocContentCrawler import DocContentCrawler; c = DocContentCrawler.__new__(DocContentCrawler); print(c._is_sphinx_autodoc_page.__doc__)" | grep -q "Sphinx autodoc"

# 2. Namespace parsing test  
python -c "from doc4llm.crawler.DocContentCrawler import DocContentCrawler; c = DocContentCrawler.__new__(DocContentCrawler); r = c._parse_python_namespace('pydolphinscheduler.core.Engine._get_attr'); assert r['class'] == 'Engine'" | grep -q "Engine"

# 3. Integration test
python -m doc4llm -u https://dolphinscheduler.apache.org/python/main/api.html -mode 4 -doc-dir /tmp/api-test -doc-name Test -doc-version v1
grep -E "^###|^####" /tmp/api-test/Test@v1/*/docContent.md | head -20
```

### Final Checklist
- [ ] `_is_sphinx_autodoc_page()` 返回正确的 True/False
- [ ] `_parse_python_namespace()` 正确解析所有测试用例
- [ ] `_inject_api_anchor_headings()` 注入标题且不破坏原有内容
- [ ] dolphinscheduler API 文档验证通过
- [ ] docReaderAPI.extract_by_headings() 能定位 `Engine._get_attr()` 等章节
- [ ] 向后兼容：非 API 页面不受影响
