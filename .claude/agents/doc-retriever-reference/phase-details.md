# doc-retriever Phase Details (Detailed Reference)

This document provides detailed specifications for each phase in the doc-retriever workflow.

## Phase 0: Query Optimization

**Skill:** `md-doc-query-optimizer`

**Your Action:** Invoke md-doc-query-optimizer with the raw user query

### What It Does

1. Analyzes query complexity, ambiguity, and language
2. Applies optimization strategies (decomposition, expansion, translation)
3. Generates 3-5 optimized queries ranked by relevance
4. Returns optimized queries with annotations explaining the transformation

### Output

3-5 optimized queries with strategy annotations

### Why This Phase Matters

- **Ambiguity resolution**: "skills" → "Agent Skills", "skills reference"
- **Complex query decomposition**: "hooks配置以及部署" → ["hooks configuration", "deployment hooks"]
- **Language translation**: "如何配置" → "configure", "setup", "settings"
- **Domain-specific expansion**: Adds technical variations and documentation-type modifiers

### Example

```
Input: "hooks 配置相关"
Output:
1. "hooks configuration" - translation: Direct English translation
2. "setup hooks" - expansion: Action-oriented variation
3. "hooks settings" - expansion: Synonym for configuration
```

---

## Phase 1: Document Discovery

**Skill:** `md-doc-searcher`

**Your Action:** Invoke md-doc-searcher with **optimized queries from Phase 0**

### Input

3-5 optimized queries (from md-doc-query-optimizer)

### What It Does

1. Lists available documentation sets
2. Applies intent filtering based on query context
3. Lists document directories within selected set
4. Reads `docTOC.md` files for semantic context
5. Performs progressive fallback (Level 1 → 2 → 3) if initial matches are poor
6. Returns semantically matching document titles with coverage verification

### Output

List of relevant document titles with TOC paths and coverage notes

### Data Flow

This phase receives optimized queries from Phase 0, not the raw user query. The optimized queries provide multiple search perspectives that improve recall and precision.

### Progressive Fallback Levels

- **Level 1:** Semantic title matching (default)
- **Level 2:** TOC content grep (when Level 1 fails)
- **Level 3.1:** Cross-set TOC search (when Level 2 fails)
- **Level 3.2:** Content search with context traceback (last resort)

---

## Phase 2: Content Extraction

**Skill:** `md-doc-reader`

**Your Action:** Use `extract_by_titles_with_metadata()` for multi-document scenarios

### CRITICAL: Multi-Document Extraction

For multi-document scenarios, you MUST use the new `extract_by_titles_with_metadata()` method:

```python
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor, ExtractionResult

extractor = MarkdownDocExtractor()

# For multiple documents - ALWAYS use this method
result = extractor.extract_by_titles_with_metadata(
    titles=["Doc1", "Doc2", "Doc3"],  # From Phase 1 results
    threshold=2100
)

# The result contains:
# - result.contents: Dict[str, str] - All document content
# - result.total_line_count: int - Cumulative line count (sum of ALL docs)
# - result.requires_processing: bool - Whether threshold exceeded
# - result.individual_counts: Dict[str, int] - Each doc's line count
```

### What It Does

1. Uses `MarkdownDocExtractor.extract_by_titles_with_metadata()` Python API
2. **Always extracts complete content** for all documents
3. **Automatically calculates cumulative line count** across ALL documents
4. Returns `ExtractionResult` dataclass with metadata

### Output

`ExtractionResult` containing:
- `contents`: Complete document content (dict mapping titles to content)
- `total_line_count`: **Cumulative line count (sum of ALL extracted documents)**
- `individual_counts`: Line count for each document
- `requires_processing`: Boolean flag indicating if threshold exceeded
- `to_summary()`: Human-readable summary for debugging

### Why This Method is Critical

- **Prevents threshold bypass bugs** - Forces cumulative line count calculation
- **Hard constraint enforcement** - Returns `requires_processing` flag that must be checked
- **Debug visibility** - Provides `to_summary()` for troubleshooting

### Source Citation Information to Extract

Each document contains source metadata at the beginning:
```
# Page Title

> **原文链接**: https://code.claude.com/docs/en/...
```

You MUST extract and preserve:
- **Original URL** (from `> **原文链接**`)
- **Document path** (from md_docs directory structure)
- **Document set name and version**

### Critical Constraint

Do NOT apply compression at this phase. Always extract full content.

---

## Phase 2.5: Conditional Check (Your Decision)

After Phase 2 completes, check the `ExtractionResult.requires_processing` flag:

### Decision Flow

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: ExtractionResult from Phase 2                       │
│         - result.requires_processing: bool                   │
│         - result.total_line_count: int                       │
│         - result.contents: Dict[str, str]                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Conditional   │
                    │   Check       │
                    └───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
    [SKIP Phase 3]                [INVOKE Phase 3]
    Return content directly      Need processing
            │                               │
            ▼                               ▼
    ┌───────────────┐           ┌──────────────────────┐
    │ Return Full   │           │ md-doc-processor     │
    │ Content       │           │ for decision         │
    │ + Citation    │           │ + Citation           │
    └───────────────┘           └──────────────────────┘
```

### Skip Phase 3 (Return content directly) WHEN

```python
# After Phase 2, you have ExtractionResult
result = extractor.extract_by_titles_with_metadata(titles, threshold=2100)

# Check the flag
if not result.requires_processing and user_has_not_requested_compression():
    # Within threshold - safe to return directly
    SKIP Phase 3
    Return full content directly to user WITH source citations
```

### Required Citation Format (AOP-FINAL)

```markdown
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines={actual_count} | source={doc_dir} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

[Document content here - from result.contents]

---

**Source:** [Original URL from document]
**Path:** md_docs/<doc_set>:<version>/<PageTitle>/docContent.md
**Document Set:** <doc_set>:<version>

=== END-AOP-FINAL ===
```

### Invoke Phase 3 (Need md-doc-processor) WHEN

```python
# After Phase 2, you have ExtractionResult
result = extractor.extract_by_titles_with_metadata(titles, threshold=2100)

# Check the flag
if result.requires_processing or user_has_requested_compression():
    # Threshold exceeded OR user wants compression
    INVOKE Phase 3 (md-doc-processor)
    md-doc-processor will handle citation formatting
```

### CRITICAL - Why This is Mandatory

The `ExtractionResult.requires_processing` flag is a **hard constraint** that prevents threshold bypass bugs in multi-document scenarios:

```python
# Example: Multi-document scenario
result = extractor.extract_by_titles_with_metadata([
    "Hooks reference",      # 1200 lines
    "Deployment guide",     # 1100 lines
    "Best practices"        # 900 lines
], threshold=2100)

# ExtractionResult automatically calculates:
# - total_line_count: 3200 (cumulative!)
# - requires_processing: True (3200 > 2100)
# - individual_counts: {"Hooks reference": 1200, ...}

# You MUST check the flag:
if result.requires_processing:
    # → MANDATORY: Invoke md-doc-processor
    # DO NOT skip this step!
    invoke_md_doc_processor(result.contents, result.total_line_count)
else:
    # → Safe to return directly
    return format_with_citations(result.contents)
```

### User Compression Request Indicators

| Language | Keywords |
|----------|----------|
| Chinese | "压缩", "总结", "摘要", "精简" |
| English | "compress", "summarize", "summary", "condense" |

**Note:** If user explicitly requests full content ("不压缩", "完整内容", "full content", "don't compress"), that's handled by md-doc-processor, not here. This check is only for detecting when user **wants** compression on small documents.

---

## Phase 3: Post-Processing Decision

**Skill:** `md-doc-processor`

**Your Action:** Invoke md-doc-processor with:
- User's original query
- Complete document content from Phase 2
- Line count from Phase 2

### What md-doc-processor Does

#### Step A: User Intent Analysis

Detects explicit full-content requests:
- Chinese: "不压缩", "完整内容", "完整版", "原文", "全部内容", "不要压缩"
- English: "full content", "don't compress", "no compression", "complete", "original", "uncompressed"

#### Step B: Decision Logic

| User Intent | Document Size | Action |
|-------------|---------------|--------|
| **Explicit full-content request** | Any size | Return original content unchanged |
| **No explicit request** | <= 2000 lines | Return original content unchanged |
| **No explicit request** | > 2000 lines | Perform intelligent compression/summary |

#### Step C: Intelligent Compression (when triggered)

When compression is required, md-doc-processor:

1. **Preserves semantic fidelity** - Absolutely faithful to original content, no tampering
2. **Optimizes for user query** - Structures summary based on user's search intent
3. **Uses smart summarization** - NOT crude truncation, but query-relevant extraction

### Compression Requirements

- Maintain original meaning and accuracy
- Prioritize content relevant to user's query
- Preserve code blocks and critical examples
- Maintain document structure (headings, sections)
- No crude truncation or cutting mid-sentence
- No altering technical meaning

### CRITICAL: md-doc-processor Output is FINAL

- **md-doc-processor returns the FINAL output that goes directly to the user**
- **DO NOT modify, summarize, or restructure md-doc-processor's output**
- **DO NOT add any additional commentary or analysis**
- **Return md-doc-processor's output EXACTLY as received**
