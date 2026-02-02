# Draft: Fix Silent Flag in Doc-RAG Orchestrator

## Issue Description
When calling `retrieve(silent=True, debug=True)`, the console still prints intermediate debug output because debug print statements only check `self.config.debug` without also checking `self.config.silent`.

## Root Cause
The `silent` parameter is defined in `DocRAGConfig` (line 131) as:
```python
silent: bool = True  # 静默模式，不打印任何输出
```

However, debug print statements throughout `orchestrator.py` use:
```python
if self.config.debug:  # Missing: and not self.config.silent
    print(...)
```

## Problematic Locations (Identified in Code Review)

| Line Range | Phase | Issue |
|------------|-------|-------|
| 489-504 | Phase 0a | `if self.config.debug:` without silent check |
| 533-550 | Phase 0b | `if self.config.debug:` without silent check |
| 631-641 | Phase 0a debug output | `if self.config.debug:` without silent check |
| 660-669 | Phase 0b debug output | `if self.config.debug:` without silent check |
| 713-721 | Phase 0a→1 debug | `if self.config.debug:` without silent check |
| 802-807 | Phase 1 stop debug | `if self.config.debug:` without silent check |
| 841-846 | Phase 1 debug | `if self.config.debug:` without silent check |
| 916-932 | Phase 1.5 record separation | `if self.config.debug:` without silent check |
| 935-936 | Phase 1.5 save input | `if self.config.debug:` without silent check |
| 1083-1099 | Phase 1.5 LLM rerank debug | `if self.config.debug:` without silent check |
| 1101-1103 | Phase 1.5 save input | `if self.config.debug:` without silent check |

## Technical Decisions
- **Fix Pattern**: Change all `if self.config.debug:` to `if self.config.debug and not self.config.silent:`
- **Scope**: Only modify `doc4llm/doc_rag/orchestrator.py`
- **Test Strategy**: Manual verification by running main.py with debug=True, silent=True

## Scope Boundaries
- IN: Fix silent flag in orchestrator.py
- EXCLUDE: No changes to debug output functions themselves, only condition checks
- EXCLUDE: No changes to print_phase_* functions (they handle their own quiet parameter)

## Metis Review Findings

### Additional Files Requiring Fixes
1. **Primary**: `doc4llm/doc_rag/orchestrator.py` - 18 locations
2. **Secondary**: `doc4llm/doc_rag/searcher/anchor_searcher.py` (line 61)
   - `_debug_print` method needs silent check
   - `AnchorSearcherConfig` lacks `silent` attribute (inconsistency)

### Edge Cases Identified
- **anchor_searcher.py**: No `silent` in config but receives it from caller
- **Config consistency**: `AnchorSearcherConfig` missing `silent` unlike other configs
- **Build artifacts**: `build/lib/` duplicates (ignore - auto-generated)

### Files NOT requiring changes
- `build/lib/` directory (auto-generated)
- `print_phase_*` functions (already have their own `quiet` parameter)

## Scope Boundaries
- IN: `doc4llm/doc_rag/orchestrator.py` (18 fixes)
- IN: `doc4llm/doc_rag/searcher/anchor_searcher.py` (config + debug print fix)
- IN: `doc4llm/doc_rag/searcher/config.py` (AnchorSearcherConfig silent attribute)
- EXCLUDE: `build/lib/` directory
- EXCLUDE: `print_phase_*` functions

## Test Strategy
Manual verification by running main.py with various combinations:
- `silent=True, debug=True` → NO output
- `silent=False, debug=True` → ALL debug + progress
- `silent=False, debug=False` → progress only
- `silent=True, debug=False` → NO output
