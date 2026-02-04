# DolphinScheduler API 文档处理优化

## TL;DR

> **Quick Summary**: Create `ApiDocTitleFormatter` class to detect Sphinx API documentation and format titles with proper hierarchy (Module → Class → Method). Integrate into `DocContentCrawler` and `DocUrlCrawler` to ensure docTOC.md and docContent.md have consistent, clean titles with Unicode artifacts removed.
>
> **Deliverables**:
> - New: `doc4llm/crawler/api_doc_formatter.py` (formatter class)
> - Modified: `doc4llm/crawler/DocContentCrawler.py`
> - Modified: `doc4llm/crawler/DocUrlCrawler.py`
> - New: `tests/test_api_doc_formatter.py`
>
> **Estimated Effort**: Short (1-2 days)
> **Parallel Execution**: NO (sequential dependencies)
> **Critical Path**: ApiDocTitleFormatter → DocContentCrawler → DocUrlCrawler → Tests

---

## Context

### Original Request
User wants to optimize doc4llm's handling of Sphinx-generated API documentation, specifically for DolphinScheduler's Python API docs at https://dolphinscheduler.apache.org/python/main/api.html

### Interview Summary

**Key Discussions**:
- **Problem 1**: docToc.md uses flat `##` headings with numbered prefixes, losing hierarchy
- **Problem 2**: docContent.md has Unicode anchor symbols (``) from RST conversion
- **Problem 3**: doc_reader_api.py cannot correctly extract content due to format mismatches

**Research Findings**:
- Sphinx HTML patterns: `dl.py function`, `dl.py class`, `sig` class elements
- DolphinScheduler uses `pydolphinscheduler.xxx` module paths
- Existing test infrastructure: pytest in `tests/` directory
- Filter pattern exists but is for content removal, not title formatting

### Metis Review

**Identified Gaps (addressed)**:
- **Gap**: Edge cases like module-level functions, properties, inherited methods
  - **Resolution**: Include all, use sensible hierarchy defaults
- **Gap**: Unicode artifact list
  - **Resolution**: Target `` (anchor symbol) and common RST artifacts
- **Gap**: Private/protected methods handling
  - **Resolution**: Include all, user can filter later

---

## Work Objectives

### Core Objective
Fix title formatting in API documentation processing so that:
1. docTOC.md has hierarchical titles (Module → Class → Method)
2. docContent.md has matching titles without Unicode artifacts
3. doc_reader_api.py can correctly extract content by title

### Concrete Deliverables
- `doc4llm/crawler/api_doc_formatter.py`: New formatter class with detection, parsing, formatting
- `doc4llm/crawler/DocContentCrawler.py`: Modified to detect API docs and use formatter
- `doc4llm/crawler/DocUrlCrawler.py`: Modified to use formatter for consistent TOC entries
- `tests/test_api_doc_formatter.py`: Unit tests for formatter

### Definition of Done
- [ ] `ApiDocTitleFormatter` class fully implemented
- [ ] `DocContentCrawler` uses formatter for API docs
- [ ] `DocUrlCrawler` uses formatter for TOC
- [ ] docTOC.md shows hierarchical structure (H2→H3→H4)
- [ ] docContent.md has clean titles (no `` symbols)
- [ ] TOC and Content titles match format
- [ ] Non-API docs unchanged (backward compatible)
- [ ] Unit tests pass
- [ ] End-to-end test with DolphinScheduler API succeeds

### Must Have
- ApiDocTitleFormatter with all core methods
- Detection of Sphinx API docs
- Hierarchical title formatting
- Unicode artifact removal
- Backward compatibility for non-API docs

### Must NOT Have (Guardrails)
- **MUST NOT**: Modify `doc_reader_api.py`
- **MUST NOT**: Add new dependencies
- **MUST NOT**: Change existing output formats (CSV, etc.)
- **MUST NOT**: Break non-API documentation processing
- **MUST NOT**: Process non-API docs through formatter

---

## Verification Strategy

> **UNIVERSAL RULE: ZERO HUMAN INTERVENTION**
>
> ALL tasks in this plan MUST be verifiable WITHOUT any human action.
> This is NOT conditional — it applies to EVERY task.

### Test Decision
- **Infrastructure exists**: YES
- **Automated tests**: YES (tests/test_api_doc_formatter.py)
- **Framework**: pytest
- **Agent-Executed QA**: YES (end-to-end with DolphinScheduler URL)

### Agent-Executed QA Scenarios

**Scenario: Verify DolphinScheduler API doc formatting**
Tool: Bash
Preconditions: doc4llm installed, network access to dolphinscheduler.apache.org
Steps:
  1. Run: `python doc4llm/cli.py -u https://dolphinscheduler.apache.org/python/main/api.html -mode 3 -depth 0`
  2. Wait for crawl to complete
  3. Extract output directory from results
  4. `grep "## " md_docs/*/docTOC.md | head -20` - Verify hierarchy exists
  5. `grep "" md_docs/*/docContent.md | wc -l` - Should be 0
  6. `grep "^## " md_docs/*/docTOC.md | sort > /tmp/toc.txt`
  7. `grep "^## " md_docs/*/docContent.md | sort > /tmp/content.txt`
  8. `diff /tmp/toc.txt /tmp/content.txt` - Should be empty (matching format)
Expected Result: All checks pass
Evidence: grep output, diff result

**Scenario: Verify non-API docs unchanged**
Tool: Bash
Preconditions: doc4llm installed, test URL (e.g., https://example.com/docs)
Steps:
  1. Run: `python doc4llm/cli.py -u https://example.com -mode 3 -depth 0`
  2. Check output: `grep "ApiDocTitleFormatter" results/*.csv` - Should be empty
  3. Check markdown: `cat md_docs/*/docContent.md | head -50`
Expected Result: No formatter applied to non-API docs
Evidence: grep output showing no formatter output

**Scenario: Unit tests pass**
Tool: Bash
Preconditions: pytest installed
Steps:
  1. `python -m pytest tests/test_api_doc_formatter.py -v`
  2. Assert: "X passed, Y failed" shows all passing
Expected Result: 100% pass rate
Evidence: pytest output log

---

## Execution Strategy

### Sequential Execution

```
Step 1: Create ApiDocTitleFormatter core class
  - ApiDocItem dataclass
  - is_api_doc() detection method
  - parse_anchor() parsing method
  - parse_hierarchy() for list parsing
  - format_toc_title() for TOC output
  - format_content_title() for content output
  - clean_title() utility

Step 2: Modify DocContentCrawler
  - Import ApiDocTitleFormatter
  - Add _is_api_doc() detection in _convert_to_markdown()
  - Call formatter for title cleanup

Step 3: Modify DocUrlCrawler
  - Import ApiDocTitleFormatter
  - Call formatter in anchor extraction

Step 4: Create unit tests
  - Test detection patterns
  - Test hierarchy parsing
  - Test title formatting
  - Test Unicode removal

Step 5: End-to-end verification
  - Run with DolphinScheduler API URL
  - Verify output format
```

### Dependency Matrix

| Step | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | None (foundation) |
| 2 | 1 | 4, 5 | 3 |
| 3 | 1 | 4, 5 | 2 |
| 4 | 2, 3 | 5 | None (needs changes) |
| 5 | 4 | None | None (final) |

---

## TODOs

> Implementation + Test = ONE Task. NEVER separate.

- [ ] 1. Create ApiDocTitleFormatter core class

  **What to do**:
  - Create `doc4llm/crawler/api_doc_formatter.py`
  - Implement `ApiDocItem` dataclass with: level, anchor, raw_title, clean_title, number
  - Implement `is_api_doc()`: Detect Sphinx API docs by patterns
  - Implement `detect_doc_type()`: Return 'module', 'class', 'member', or 'unknown'
  - Implement `parse_anchor()`: Parse anchor text to ApiDocItem
  - Implement `parse_hierarchy()`: Parse list of anchors with hierarchy
  - Implement `format_toc_title()`: Format TOC title with number prefix
  - Implement `format_content_title()`: Format content title with hierarchy
  - Implement `clean_title()`: Remove Unicode artifacts, RST suffixes
  - Add Sphinx pattern detection: `dl.py function`, `dl.py class`, `sig` classes
  - Add DolphinScheduler module path detection: `pydolphinscheduler.*`

  **Must NOT do**:
  - **MUST NOT**: Process non-API docs
  - **MUST NOT**: Modify output formats
  - **MUST NOT**: Add dependencies

  **Recommended Agent Profile**:
  - **Category**: unspecified-low
    - Reason: Straightforward implementation following provided specification
  - **Skills**: []
    - No special skills needed for this task

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Step 1)
  - **Blocks**: Steps 2, 3
  - **Blocked By**: None

  **References**:
  - Sphinx HTML structure patterns from librarian research
  - DocContentCrawler._convert_to_markdown() for integration context
  - DocUrlCrawler._extract_anchor_links() for anchor handling

  **Acceptance Criteria**:

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: ApiDocTitleFormatter class exists and has required methods
    Tool: Bash
    Preconditions: Python 3.8+ available
    Steps:
      1. python -c "from doc4llm.crawler.api_doc_formatter import ApiDocTitleFormatter; f = ApiDocTitleFormatter(); print(hasattr(f, 'is_api_doc'), hasattr(f, 'parse_anchor'), hasattr(f, 'format_toc_title'))"
      2. Assert: Output shows "True True True"
    Expected Result: All methods exist
    Evidence: Python output

  Scenario: is_api_doc detects Sphinx patterns
    Tool: Bash
    Preconditions: ApiDocTitleFormatter instance
    Steps:
      1. python -c "
  from doc4llm.crawler.api_doc_formatter import ApiDocTitleFormatter
  f = ApiDocTitleFormatter()
  sphinx_html = '<dl class=\"py function\"><dt class=\"sig sig-object py\">'
  print(f.is_api_doc(sphinx_html))
      "
      2. Assert: Output shows "True"
    Expected Result: Sphinx pattern detected
    Evidence: Python output

  Scenario: clean_title removes Unicode artifacts
    Tool: Bash
    Preconditions: ApiDocTitleFormatter instance
    Steps:
      1. python -c "
  from doc4llm.crawler.api_doc_formatter import ApiDocTitleFormatter
  f = ApiDocTitleFormatter()
  dirty = 'Engine._get_attr()'
  clean = f.clean_title(dirty)
  print(clean)
  print('Has artifact:', '' in clean)
      "
      2. Assert: Output shows "Engine._get_attr()" and "Has artifact: False"
    Expected Result: Unicode artifact removed
    Evidence: Python output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Python class import verification
  - [ ] Method existence check output
  - [ ] Pattern detection test output
  - [ ] Clean title test output

- [ ] 2. Modify DocContentCrawler for API doc support

  **What to do**:
  - Import `ApiDocTitleFormatter` in DocContentCrawler.py
  - Add `_is_api_doc(url, soup)` method to detect API docs
  - Modify `_convert_to_markdown()` to:
    - Detect if page is API doc
    - Call formatter.clean_title() on page title
    - Ensure Content headings are hierarchical
  - Ensure backward compatibility for non-API docs

  **Must NOT do**:
  - **MUST NOT**: Break existing non-API doc processing
  - **MUST NOT**: Change output format

  **Recommended Agent Profile**:
  - **Category**: unspecified-low
    - Reason: Integration task following existing patterns
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Step 2 (with Step 3)
  - **Blocks**: Step 4, 5
  - **Blocked By**: Step 1

  **References**:
  - DocContentCrawler.py lines 860-932: _convert_to_markdown()
  - Existing imports and class structure

  **Acceptance Criteria**:
  - [ ] Import statement added
  - [ ] _is_api_doc() method added
  - [ ] _convert_to_markdown() calls formatter for API docs
  - [ ] Non-API docs pass through unchanged

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: DocContentCrawler can import formatter
    Tool: Bash
    Preconditions: Step 1 complete
    Steps:
      1. python -c "from doc4llm.crawler.DocContentCrawler import DocContentCrawler; print('Import OK')"
      2. Assert: No ImportError
    Expected Result: Import succeeds
    Evidence: Python output

  Scenario: Non-API docs unchanged after modification
    Tool: Bash
    Preconditions: doc4llm installed
    Steps:
      1. Create test HTML file with regular content
      2. python -c "
  from doc4llm.crawler.DocContentCrawler import DocContentCrawler
  from doc4llm.scanner.config import ScannerConfig
  config = ScannerConfig()
  crawler = DocContentCrawler(config)
  html = '<html><body><h1>Test Page</h1><p>Content</p></body></html>'
  result = crawler._convert_to_markdown(html, 'https://example.com', 'Test')
  print('Has hierarchy:', '##' in result)
      "
      3. Assert: Output shows "Has hierarchy: False" (no formatter applied)
    Expected Result: Non-API doc not processed by formatter
    Evidence: Python output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Import verification output
  - [ ] Non-API doc test output

- [ ] 3. Modify DocUrlCrawler for consistent TOC extraction

  **What to do**:
  - Import `ApiDocTitleFormatter` in DocUrlCrawler.py
  - Modify `_extract_anchor_links()` to use formatter for API docs
  - Ensure TOC headings are hierarchical
  - Ensure backward compatibility for non-API docs

  **Must NOT do**:
  - **MUST NOT**: Break existing non-API TOC extraction
  - **MUST NOT**: Change CSV output format

  **Recommended Agent Profile**:
  - **Category**: unspecified-low
    - Reason: Integration task following existing patterns
  - **Skills**: []
    - No special skills needed

  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Step 3 (with Step 2)
  - **Blocks**: Step 4, 5
  - **Blocked By**: Step 1

  **References**:
  - DocUrlCrawler.py lines 870-944: _extract_anchor_links()
  - Existing TOC extraction logic

  **Acceptance Criteria**:
  - [ ] Import statement added
  - [ ] _extract_anchor_links() uses formatter for API docs
  - [ ] TOC headings show hierarchy
  - [ ] Non-API TOC unchanged

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: DocUrlCrawler can import formatter
    Tool: Bash
    Preconditions: Step 1 complete
    Steps:
      1. python -c "from doc4llm.crawler.DocUrlCrawler import DocUrlCrawler; print('Import OK')"
      2. Assert: No ImportError
    Expected Result: Import succeeds
    Evidence: Python output

  Scenario: API doc anchors formatted correctly
    Tool: Bash
    Preconditions: Steps 1-3 complete
    Steps:
      1. python -c "
  from doc4llm.crawler.api_doc_formatter import ApiDocTitleFormatter
  f = ApiDocTitleFormatter()
  anchors = [
      'pydolphinscheduler.core',
      'pydolphinscheduler.core.Engine',
      'pydolphinscheduler.core.Engine._get_attr'
  ]
  items = f.parse_hierarchy(anchors)
  for item in items:
      print(f'Level {item.level}: {item.clean_title}')
      "
      2. Assert: Output shows hierarchical levels (1, 2, 3)
    Expected Result: Hierarchy detected correctly
    Evidence: Python output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Import verification output
  - [ ] Hierarchy parsing test output

- [ ] 4. Create unit tests for ApiDocTitleFormatter

  **What to do**:
  - Create `tests/test_api_doc_formatter.py`
  - Test `is_api_doc()` with various inputs
  - Test `detect_doc_type()` return values
  - Test `parse_anchor()` for different anchor formats
  - Test `parse_hierarchy()` for list of anchors
  - Test `format_toc_title()` output format
  - Test `format_content_title()` output format
  - Test `clean_title()` Unicode removal
  - Test DolphinScheduler module path detection

  **Must NOT do**:
  - **MUST NOT**: Break existing tests

  **Recommended Agent Profile**:
  - **Category**: unspecified-low
    - Reason: Standard pytest test writing
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Step 4)
  - **Blocks**: Step 5
  - **Blocked By**: Steps 2, 3

  **References**:
  - Existing tests in `tests/` directory for style reference
  - pytest documentation for test patterns

  **Acceptance Criteria**:
  - [ ] Test file created at `tests/test_api_doc_formatter.py`
  - [ ] All test methods defined
  - [ ] `pytest tests/test_api_doc_formatter.py` passes

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: All unit tests pass
    Tool: Bash
    Preconditions: Test file created
    Steps:
      1. python -m pytest tests/test_api_doc_formatter.py -v --tb=short
      2. Assert: "X passed, Y failed" shows 0 failures
    Expected Result: 100% pass rate
    Evidence: pytest output log
  \`\`\`

  **Evidence to Capture**:
  - [ ] pytest output showing all tests passing

- [ ] 5. End-to-end verification with DolphinScheduler API

  **What to do**:
  - Run doc4llm with DolphinScheduler API URL
  - Verify docTOC.md has hierarchical headings
  - Verify docContent.md has clean titles (no ``)
  - Verify TOC and Content titles match format
  - Document findings

  **Must NOT do**:
  - **MUST NOT**: Modify production files without backup

  **Recommended Agent Profile**:
  - **Category**: unspecified-low
    - Reason: Verification task following test plan
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential (Step 5)
  - **Blocks**: None (final)
  - **Blocked By**: Step 4

  **References**:
  - Target URL: https://dolphinscheduler.apache.org/python/main/api.html
  - Expected output directory structure

  **Acceptance Criteria**:
  - [ ] Crawl completes without errors
  - [ ] docTOC.md shows hierarchy
  - [ ] docContent.md no Unicode artifacts
  - [ ] Titles match between TOC and Content

  **Agent-Executed QA Scenarios**:

  \`\`\`
  Scenario: DolphinScheduler API docs formatted correctly
    Tool: Bash
    Preconditions: doc4llm installed, network access
    Steps:
      1. cd /tmp && rm -rf dolphin_test && mkdir dolphin_test && cd dolphin_test
      2. python /Users/zorro/project/doc4llm/doc4llm/cli.py -u https://dolphinscheduler.apache.org/python/main/api.html -mode 3 -depth 0 -doc-name DolphinScheduler_API -doc-version test
      3. Wait for completion (check output.log)
      4. TOC_FILE=$(find . -name "docTOC.md" | head -1)
      5. CONTENT_FILE=$(find . -name "docContent.md" | head -1)
      6. echo "=== TOC Hierarchy Check ===" && grep "^## " "$TOC_FILE" | head -10
      7. echo "=== Unicode Artifact Check ===" && grep "" "$CONTENT_FILE" | wc -l
      8. echo "=== Content Heading Check ===" && grep "^## " "$CONTENT_FILE" | head -10
    Expected Result:
      - TOC shows numbered hierarchy (## 1, ## 2, ### 2.1, etc.)
      - Unicode count = 0
      - Content shows matching headings
    Evidence: Terminal output captured

  Scenario: Verify title consistency between TOC and Content
    Tool: Bash
    Preconditions: DolphinScheduler test complete
    Steps:
      1. Extract unique titles from TOC: grep "^## " "$TOC_FILE" | sed 's/^## [0-9. ]*//' | sort -u > /tmp/toc_titles.txt
      2. Extract unique titles from Content: grep "^## " "$CONTENT_FILE" | sed 's/^## //' | sort -u > /tmp/content_titles.txt
      3. echo "=== Title Comparison ===" && diff /tmp/toc_titles.txt /tmp/content_titles.txt || true
    Expected Result: Minimal differences (some is expected due to URL vs anchor)
    Evidence: diff output
  \`\`\`

  **Evidence to Capture**:
  - [ ] Terminal output showing hierarchy
  - [ ] Unicode check output (count = 0)
  - [ ] Title comparison diff output

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 1 | `feat(crawler): add ApiDocTitleFormatter class` | api_doc_formatter.py | Import test |
| 2 | `feat(crawler): integrate API formatter in DocContentCrawler` | DocContentCrawler.py | Non-API test |
| 3 | `feat(crawler): integrate API formatter in DocUrlCrawler` | DocUrlCrawler.py | Import test |
| 4 | `test: add ApiDocTitleFormatter unit tests` | tests/test_api_doc_formatter.py | pytest |
| 5 | `chore: verify DolphinScheduler API formatting` | - | E2E test |

---

## Success Criteria

### Verification Commands
```bash
# Unit tests
python -m pytest tests/test_api_doc_formatter.py -v  # All pass

# End-to-end verification
python doc4llm/cli.py -u https://dolphinscheduler.apache.org/python/main/api.html -mode 3 -depth 0

# Check hierarchy in TOC
grep "^## " md_docs/*/docTOC.md | head -20  # Should show hierarchy

# Check no Unicode artifacts
grep "" md_docs/*/docContent.md | wc -l  # Should be 0

# Check backward compatibility
python doc4llm/cli.py -u https://example.com -mode 3  # Non-API still works
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent (guardrails followed)
- [ ] Unit tests pass
- [ ] E2E verification succeeds
- [ ] Non-API docs unchanged
- [ ] Code follows project conventions (black, flake8)
