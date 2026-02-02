# Work Plan: Add Silent CLI Parameter to orchestrator.py

## TL;DR

> **Quick Summary**: Add `--silent` CLI flag to `orchestrator.py` with default `true`, fixing existing bug where `silent` variable was undefined in `_main()` function.
> 
> **Deliverables**:
> - Modified `doc4llm/doc_rag/orchestrator.py` with:
>   - `silent` default changed to `True` in `DocRAGConfig` and `retrieve()`
>   - `--silent` CLI argument added to `_parse_args()`
>   - `silent` variable properly defined in `_main()` from parsed args
> 
> **Estimated Effort**: Quick | **Parallel Execution**: NO (sequential) | **Critical Path**: All tasks sequential

---

## Context

### Original Request
User request: "给 @doc4llm/doc_rag/orchestrator.py 增加一个 silent cli 参数，默认为 true"

### Interview Summary
**Key Discussions**:
- Existing `silent` field in `DocRAGConfig` defaults to `False`
- CLI parser exists but incomplete - missing `--silent` argument
- `_main()` function has bug: references undefined `silent` variable

### Metis Review
**Identified Gaps**:
1. `DocRAGConfig.silent` default is `False`, need to change to `True`
2. `retrieve()` `silent` parameter default is `False`, need to change to `True`
3. `_parse_args()` missing `--silent` CLI argument
4. `_main()` references undefined `silent` variable (NameError bug)

**Guardrails Applied**:
- Maintain backward compatibility where possible
- Keep existing behavior when `--silent` is explicitly provided
- Default to silent mode for CLI usage

---

## Work Objectives

### Core Objective
Add `--silent` CLI parameter to `orchestrator.py` with default value of `True`, fixing the existing undefined variable bug.

### Concrete Deliverables
- Modified `doc4llm/doc_rag/orchestrator.py`:
  - Line 131: `DocRAGConfig.silent` default `False` → `True`
  - Line 1529: `retrieve()` `silent` parameter default `False` → `True`
  - Lines 1694-1696: Add `--silent` argument to `_parse_args()`
  - Lines 1699-1703: Define `silent` variable in `_main()` from parsed args

### Definition of Done
- [ ] `python -c "from doc4llm.doc_rag.orchestrator import _parse_args; args = _parse_args(['test']); print(hasattr(args, 'silent'))"` → `True`
- [ ] CLI accepts `--silent` flag without error
- [ ] CLI defaults to silent mode when no flag provided
- [ ] Python API still accepts explicit `silent` parameter

### Must Have
- Silent mode defaults to `True`
- CLI `--silent` flag works correctly
- Existing Python API backward compatible

### Must NOT Have
- No breaking changes to existing Python API signatures
- No new dependencies added

---

## Verification Strategy

### Test Decision
- **Infrastructure exists**: N/A (no tests in this repo)
- **User wants tests**: Manual verification only
- **Framework**: N/A

### Manual Verification Procedures

**For Python module changes**:
```bash
# Verify 1: Check that _parse_args accepts --silent
python -c "
from doc4llm.doc_rag.orchestrator import _parse_args
import sys
sys.argv = ['test', '--silent']
args = _parse_args()
print(f'silent value: {args.silent}')
"

# Verify 2: Check default silent value in DocRAGConfig
python -c "
from doc4llm.doc_rag.orchestrator import DocRAGConfig
config = DocRAGConfig(base_dir='/tmp')
print(f'DocRAGConfig.silent default: {config.silent}')
"

# Verify 3: Check retrieve() function signature
python -c "
import inspect
from doc4llm.doc_rag.orchestrator import retrieve
sig = inspect.signature(retrieve)
print(f'retrieve signature: {sig}')
"
```

---

## TODOs

- [ ] 1. Change `DocRAGConfig.silent` default from `False` to `True` (line 131)

  **What to do**:
  - Edit line 131 in `doc4llm/doc_rag/orchestrator.py`
  - Change `silent: bool = False` to `silent: bool = True`
  - Update docstring comment if needed

  **Must NOT do**:
  - Do not change the field type
  - Do not remove the field

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple one-line change in known location
  - **Skills**: []
    - No special skills needed for this trivial edit
  - **Skills Evaluated but Omitted**:
    - None - this is a straightforward edit

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 2, Task 3
  - **Blocked By**: None (can start immediately)

  **References**:
  - `doc4llm/doc_rag/orchestrator.py:131` - Current location of `silent: bool = False`

  **Acceptance Criteria**:
  - [ ] Line 131 reads: `silent: bool = True`

  **Evidence to Capture**:
  - [ ] Terminal output: grep showing changed line

  **Commit**: NO (grouped with Task 4)

- [ ] 2. Change `retrieve()` function `silent` parameter default from `False` to `True` (line 1529)

  **What to do**:
  - Edit line 1529 in `doc4llm/doc_rag/orchestrator.py`
  - Change `silent: bool = False` to `silent: bool = True`
  - Update any docstring that mentions the default

  **Must NOT do**:
  - Do not change the parameter name or type
  - Do not remove the parameter

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple one-line change in known location
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 3, Task 4
  - **Blocked By**: Task 1

  **References**:
  - `doc4llm/doc_rag/orchestrator.py:1529` - Current location of `silent` parameter in `retrieve()`

  **Acceptance Criteria**:
  - [ ] Line 1529 reads: `silent: bool = True`

  **Evidence to Capture**:
  - [ ] Terminal output: grep showing changed line

  **Commit**: NO (grouped with Task 4)

- [ ] 3. Add `--silent` CLI argument to `_parse_args()` function

  **What to do**:
  - Read lines 1690-1700 to find exact location to insert
  - Add `parser.add_argument("--silent", ...)` before `return parser.parse_args()`
  - Set default to `True` so silent mode is on by default
  - Add help text: "Enable silent mode, suppress all output (default: true)"

  **Must NOT do**:
  - Do not remove existing arguments
  - Do not change existing argument behavior

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Adding one argument to existing parser
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 4
  - **Blocked By**: Task 2

  **References**:
  - `doc4llm/doc_rag/orchestrator.py:1680-1696` - `_parse_args()` function structure
  - `doc4llm/doc_rag/orchestrator.py:34` - argparse import
  - Python argparse documentation - `add_argument()` with `action="store_true"` or `default=True`

  **Acceptance Criteria**:
  - [ ] `_parse_args()` accepts `--silent` argument
  - [ ] When no `--silent` provided, `args.silent` is `True`
  - [ ] When `--silent` provided, `args.silent` is `True` (flag is present)

  **Evidence to Capture**:
  - [ ] Terminal output showing argument parsing works

  **Commit**: NO (grouped with Task 4)

- [ ] 4. Fix `_main()` function to define `silent` variable from parsed args

  **What to do**:
  - Read lines 1699-1756 to find exact code structure
  - After `args = _parse_args()`, add: `silent = getattr(args, 'silent', True)`
  - This fixes the NameError bug where `silent` was used but never defined

  **Must NOT do**:
  - Do not remove existing logic
  - Do not change how other variables are defined

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Bug fix - one line addition to define existing variable
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - None

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Task 3

  **References**:
  - `doc4llm/doc_rag/orchestrator.py:1699-1756` - `_main()` function
  - Lines 1704, 1709, 1752 - Places where `silent` is referenced without definition

  **Acceptance Criteria**:
  - [ ] `_main()` runs without NameError
  - [ ] `silent` variable is properly defined from `args.silent`
  - [ ] Default value is `True` when `args.silent` not present

  **Evidence to Capture**:
  - [ ] Terminal output showing `_main()` runs without errors

  **Commit**: YES
  - Message: `feat(doc_rag): add silent CLI parameter with default true`
  - Files: `doc4llm/doc_rag/orchestrator.py`

---

## Commit Strategy

| After Task | Message | Files | Verification |
|------------|---------|-------|--------------|
| 4 | `feat(doc_rag): add silent CLI parameter with default true` | orchestrator.py | Verify CLI works |

---

## Success Criteria

### Verification Commands
```bash
# Test 1: Verify default silent is True in config
python -c "from doc4llm.doc_rag.orchestrator import DocRAGConfig; c = DocRAGConfig(base_dir='/tmp'); print(f'silent={c.silent}')"
# Expected: silent=True

# Test 2: Verify _parse_args includes --silent
python -c "from doc4llm.doc_rag.orchestrator import _parse_args; args = _parse_args(['test']); print(f'has silent: {hasattr(args, \"silent\")}')"
# Expected: has silent: True

# Test 3: Verify _main() doesn't crash
python -c "from doc4llm.doc_rag.orchestrator import _main; _main()" 2>&1 | head -5
# Expected: No NameError, runs without crash
```

### Final Checklist
- [ ] All "Must Have" present
- [ ] All "Must NOT Have" absent
- [ ] CLI accepts `--silent` flag
- [ ] Silent mode defaults to `True`
- [ ] No breaking changes to Python API
