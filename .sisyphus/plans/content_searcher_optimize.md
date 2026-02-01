# Content Searcher Context Extraction Optimization

## TL;DR

> **Quick Summary**: Optimize `_extract_context` method to dynamically extract context around match lines, ensuring result never exceeds 100 words (punctuation excluded) while progressively expanding context_size from 2 to max 50.
>
> **Deliverables**: Modified `_extract_context` method in `doc4llm/doc_rag/searcher/content_searcher.py`
>
> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential implementation
> **Critical Path**: Implement helper methods → Implement main logic → Test edge cases

---

## Context

### Original Request
Optimize `_extract_context` method with:
1. Context centered on match line
2. Max 100 words (excluding punctuation)
3. Progressive expansion from context_size=2, +5 per iteration
4. Max context_size=50
5. Symmetric truncation if exceeding limit

### Interview Summary
**Key Discussions**:
- Truncation strategy: Symmetric truncation from both ends towards match line
- Expansion step: +5 lines per iteration
- Max context_size: 50 lines
- Word limit: 100 words (punctuation excluded)

**Research Findings**:
- Test infrastructure: pytest exists in tests/ directory
- Target method: lines 234-260 in content_searcher.py
- Method signature: `_extract_context(self, lines: List[str], match_line: int, context_size: int = 2) -> str`
- No existing tests specifically for this method in test_content_searcher.py (empty test directory)

### Metis Review
**Identified Gaps** (addressed):
- **Word counting definition**: Use `len(re.sub(r'[^\w\s]', '', text).split())` to exclude punctuation
- **Boundary handling**: If symmetric truncation impossible (match at document start/end), truncate from one side only
- **Single-line document**: Return full content regardless of word count
- **Calling code compatibility**: Preserve existing behavior for non-truncated cases

---

## Work Objectives

### Core Objective
Optimize `_extract_context` method to:
- Start with context_size=2
- Progressively expand by +5 lines per iteration until context ≤100 words or max context_size=50
- If exceeding 100 words, truncate symmetrically from both ends towards match line

### Concrete Deliverables
- Modified `_extract_context` method in `content_searcher.py`

### Definition of Done
- [ ] Method signature unchanged (backward compatible)
- [ ] Context ≤100 words when truncated
- [ ] Symmetric truncation preserves match line position
- [ ] Progressive expansion up to context_size=50
- [ ] Edge cases handled: boundaries, empty inputs, invalid match_line

### Must Have
- Word counting excluding punctuation
- Symmetric truncation from both ends
- Progressive context expansion
- Boundary handling for match line near document edges

### Must NOT Have (Guardrails)
- Do NOT modify method signature
- Do NOT change calling code behavior
- Do NOT add new dependencies
- Do NOT modify other methods in the file

---

## Verification Strategy (MANDATORY)

### Test Decision
- **Infrastructure exists**: YES (pytest)
- **User wants tests**: NO - manual verification only
- **Framework**: N/A

### Automated Verification (NO User Intervention)

**For Library/Module changes** (using Bash):
```bash
# Test 1: Word counting with punctuation excluded
python3 -c "
import re
def count_words(text):
    return len(re.sub(r'[^\w\s]', '', text).split())

text = 'Hello, world! This is a test.'
print(count_words(text))  # Expected: 6 (not 8)
"

# Test 2: Symmetric truncation
python3 -c "
def truncate_symmetric(lines, max_words):
    # Simulate truncation from both ends
    pass
"

# Test 3: Full method test
python3 -c "
import sys
sys.path.insert(0, '.')
from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher
searcher = ContentSearcher('/tmp')
lines = ['word ' * 200]  # 200 words
result = searcher._extract_context(lines, 0, context_size=50)
word_count = len(re.sub(r'[^\w\s]', '', result).split())
print(f'Word count: {word_count}')
assert word_count <= 100, f'Expected <=100 words, got {word_count}'
"
```

---

## Execution Strategy

### Sequential Execution
```
Task 1: Implement _count_words helper method
Task 2: Implement _truncate_symmetric helper method
Task 3: Rewrite _extract_context main logic
Task 4: Verify edge cases and boundary handling
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With |
|------|------------|--------|---------------------|
| 1 | None | 2, 3 | None |
| 2 | None | 3 | None |
| 3 | 1, 2 | 4 | None |
| 4 | 3 | None | None |

---

## TODOs

- [ ] 1. Implement `_count_words` helper method

  **What to do**:
  - Add `_count_words(self, text: str) -> int` method
  - Use regex to strip punctuation: `re.sub(r'[^\w\s]', '', text)`
  - Split on whitespace and return word count
  - Handle edge cases: empty string, None, whitespace-only

  **Must NOT do**:
  - Do NOT modify existing method signatures
  - Do NOT add new imports beyond `re`

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple helper method implementation
  - **Skills**: []
    - No special skills needed for basic string manipulation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 3
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `content_searcher.py:316-333` - `_remove_url_from_heading` uses regex for text cleaning

  **API/Type References** (contracts to implement against):
  - Input: `text: str`
  - Output: `int` (word count)

  **Acceptance Criteria**:
  - [ ] Method returns 0 for empty string
  - [ ] Method returns 0 for None
  - [ ] `"Hello, world!"` returns 2 (punctuation excluded)
  - [ ] `"word " * 150` returns 150
  - [ ] `"  multiple   spaces  "` returns 2

  **Evidence to Capture**:
  - Terminal output from test commands showing word counts

  **Commit**: NO

---

- [ ] 2. Implement `_truncate_symmetric` helper method

  **What to do**:
  - Add `_truncate_symmetric(self, lines: List[str], match_idx: int, max_words: int) -> str` method
  - Takes lines list and match line index (0-based)
  - Truncates from both ends towards match line to fit max_words
  - Returns concatenated string of truncated lines

  **Must NOT do**:
  - Do NOT modify original lines list
  - Do NOT change line order

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward algorithm implementation
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 3
  - **Blocked By**: None (can start immediately)

  **References**:

  **Pattern References** (existing code to follow):
  - `content_searcher.py:247-256` - Original context extraction logic

  **Algorithm**:
  ```
  1. Start with all lines from start_idx to end_idx
  2. While word_count > max_words:
     a. If more lines on left side: remove first line
     b. If more lines on right side: remove last line
     c. If only match line left: truncate match line to max_words
  3. Return joined lines
  ```

  **Acceptance Criteria**:
  - [ ] Returns empty string for empty lines
  - [ ] Preserves match line position in result
  - [ ] Truncates from both ends equally when possible
  - [ ] Truncates from one side if match at boundary
  - [ ] Result word count ≤ max_words

  **Evidence to Capture**:
  - Test output showing symmetric truncation behavior

  **Commit**: NO

---

- [ ] 3. Rewrite `_extract_context` main logic

  **What to do**:
  - Rewrite `_extract_context(self, lines: List[str], match_line: int, context_size: int = 2) -> str`
  - Start with initial context_size=2
  - Loop: expand context by +5 lines per iteration
  - Check word count after each expansion
  - If word_count > 100: call `_truncate_symmetric` to truncate to 100 words
  - Stop when: word_count ≤100 OR context_size ≥50

  **Algorithm**:
  ```
  1. context_size = 2
  2. While context_size <= 50:
     a. Extract lines from max(0, match_line-context_size) to min(len(lines), match_line+context_size+1)
     b. Join lines and clean URLs
     c. word_count = _count_words(result)
     d. If word_count <= 100: return result
     e. If word_count > 100:
        - If context_size == 50: truncate to 100 words and return
        - Else: context_size += 5, continue
  3. Return result (truncated to 100 words if needed)
  ```

  **Must NOT do**:
  - Do NOT change method signature
  - Do NOT modify caller behavior

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Straightforward refactoring of existing method
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 4
  - **Blocked By**: 1, 2

  **References**:

  **Pattern References** (existing code to follow):
  - `content_searcher.py:234-260` - Original implementation (lines 247-256 for context extraction logic)
  - `content_searcher.py:335-347` - `_clean_context_from_urls` method

  **API/Type References** (contracts to implement against):
  - Input: `lines: List[str]`, `match_line: int`, `context_size: int = 2`
  - Output: `str` (context text, ≤100 words when truncated)

  **Acceptance Criteria**:
  - [ ] Returns ≤100 words for long content
  - [ ] Returns full context for short content (no truncation needed)
  - [ ] Match line is centered when possible
  - [ ] Stops expanding at context_size=50 even if still >100 words
  - [ ] Handles match_line at document boundaries correctly
  - [ ] Preserves URL cleaning behavior from original method

  **Automated Verification**:
  ```bash
  # Test 1: Short content (no truncation)
  python3 -c "
  import sys
  sys.path.insert(0, '.')
  from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher
  searcher = ContentSearcher('/tmp')
  lines = ['word1 word2 word3', 'word4 word5 word6', 'word7 word8 word9']
  result = searcher._extract_context(lines, 2, context_size=2)
  print(f'Result: {result}')
  print(f'Word count: {len(result.split())}')
  "

  # Test 2: Long content (truncation needed)
  python3 -c "
  import sys
  sys.path.insert(0, '.')
  from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher
  import re
  searcher = ContentSearcher('/tmp')
  lines = ['word ' * 200]  # 200 words
  result = searcher._extract_context(lines, 0, context_size=50)
  word_count = len(re.sub(r'[^\w\s]', '', result).split())
  print(f'Word count: {word_count}')
  assert word_count <= 100, f'Expected <=100, got {word_count}'
  print('PASS: Truncation works')
  "
  ```

  **Evidence to Capture**:
  - Terminal output from verification commands
  - Comparison of original vs new behavior for backward compatibility

  **Commit**: NO

---

- [ ] 4. Verify edge cases and boundary handling

  **What to do**:
  - Test boundary conditions:
    - match_line = 0 (first line)
    - match_line = len(lines)-1 (last line)
    - lines = [] (empty)
    - Single line with 100+ words
  - Verify symmetric truncation works near boundaries
  - Confirm backward compatibility for short content

  **Must NOT do**:
  - Do NOT modify any production code

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Testing and verification only
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: 3

  **Acceptance Criteria**:
  - [ ] match_line=0: truncates from right side only
  - [ ] match_line=last: truncates from left side only
  - [ ] Empty lines: returns empty string
  - [ ] Single long line: truncates to 100 words
  - [ ] Short content: returns full context (no truncation)

  **Automated Verification**:
  ```bash
  # Test boundary conditions
  python3 -c "
  import sys
  sys.path.insert(0, '.')
  from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher
  import re
  searcher = ContentSearcher('/tmp')

  # Test 1: match_line at start
  lines = ['word ' * 50, 'word ' * 50]
  result = searcher._extract_context(lines, 0, context_size=2)
  print(f'Test 1 (match_line=0): {len(result.split())} words')

  # Test 2: match_line at end
  result = searcher._extract_context(lines, 1, context_size=2)
  print(f'Test 2 (match_line=end): {len(result.split())} words')

  # Test 3: Empty lines
  result = searcher._extract_context([], 0, context_size=2)
  print(f'Test 3 (empty): \"{result}\"')

  # Test 4: Single long line
  lines = ['word ' * 200]
  result = searcher._extract_context(lines, 0, context_size=50)
  word_count = len(re.sub(r'[^\w\s]', '', result).split())
  print(f'Test 4 (single long): {word_count} words')
  assert word_count <= 100
  "
  ```

  **Evidence to Capture**:
  - All test outputs showing edge cases handled correctly

  **Commit**: NO

---

## Success Criteria

### Verification Commands
```bash
# Run all verification tests
python3 -c "
import sys
sys.path.insert(0, '.')
from doc4llm.doc_rag.searcher.content_searcher import ContentSearcher
import re

searcher = ContentSearcher('/tmp')

# Test 1: Word counting
def count_words(text):
    return len(re.sub(r'[^\w\s]', '', text).split())

assert count_words('Hello, world!') == 2
assert count_words('') == 0
print('✓ Word counting works')

# Test 2: Short content (no truncation)
lines = ['word1 word2 word3', 'word4 word5 word6']
result = searcher._extract_context(lines, 1, context_size=2)
print(f'✓ Short content: {len(result.split())} words')

# Test 3: Long content (truncation)
lines = ['word ' * 200]
result = searcher._extract_context(lines, 0, context_size=50)
word_count = len(re.sub(r'[^\w\s]', '', result).split())
assert word_count <= 100, f'Expected <=100, got {word_count}'
print(f'✓ Long content truncated to {word_count} words')

# Test 4: Boundary (match_line=0)
lines = ['word ' * 50, 'word ' * 50]
result = searcher._extract_context(lines, 0, context_size=10)
print(f'✓ Boundary start: {len(result.split())} words')

# Test 5: Boundary (match_line=end)
result = searcher._extract_context(lines, 1, context_size=10)
print(f'✓ Boundary end: {len(result.split())} words')

print()
print('All verification tests passed!')
"
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] Word count ≤100 for truncated content
- [ ] Symmetric truncation preserves match line
- [ ] Edge cases handled correctly
