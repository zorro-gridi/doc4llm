# Progressive Fallback Strategy (ACTUAL IMPLEMENTATION)

> **Note**: This document describes the **actual implemented** fallback strategy in `doc_searcher_api.py`.
> The previous version of this document described a deprecated semantic matching approach that was never implemented.

## Actual Current Implementation

The current md-doc-searcher uses a **multi-stage BM25-based retrieval** with transformer-based semantic re-ranking:

1. **Stage 1**: Jaccard similarity for doc-set matching
2. **Stage 2**: BM25 for page title matching
3. **Stage 3**: BM25 for heading matching
4. **Stage 4**: Transformer re-ranking (BGE models)
5. **Fallback**: Grep-based search + BM25 re-scoring

### Search Scope

- **Doc-set boundary**: Searches within specified doc-sets via `target_doc_sets` parameter
- **Auto-detection**: Falls back to Jaccard-based doc-set matching when `target_doc_sets` not provided
- **Grep fallback**: Falls back to grep-based search when BM25 retrieval fails

---

## Retrieval Pipeline Overview

```
                    ┌─────────────────┐
                    │   输入查询      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │ Stage 1: Jaccard│
                    │  匹配 Doc-set   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │    找到目标 doc-set?         │
              └──────────────┬──────────────┘
                    │ Yes   │ No → 返回第一个
                             │
                    ┌────────▼────────┐
                    │ Stage 2: BM25   │
                    │  匹配 Page Title│
                    └────────┬────────┘
                             │ score >= 0.6
                    ┌────────▼────────┐
                    │ Stage 3: BM25   │
                    │  匹配 Headings  │
                    └────────┬────────┘
                             │ score >= 0.25
              ┌──────────────┴──────────────┐
              │    reranker_enabled?        │
              └──────────────┬──────────────┘
                    │ Yes   │ No
                     │       │
            ┌────────▼┐   ┌──▼─────────┐
            │Transformer│  │ 过滤结果   │
            │  重排序   │  │ 返回       │
            └────┬─────┘  └────────────┘
                 │ score >= 0.68
              ┌──┴────────────┐
              │ 结果不足或失败？│
              └───────┬────────┘
                  Yes │ No
                      │
         ┌────────────┴────────────┐
         │  FALLBACK_1: Grep + BM25│
         └────────────┬────────────┘
                      │
         ┌────────────┴────────────┐
         │  结果仍不足？            │
         └────────────┬────────────┘
                  Yes │ No
                      │
         ┌────────────▼────────────┐
         │ FALLBACK_2: Grep+BM25   │
         │ (带上下文 -B 5/-B 20)   │
         └─────────────────────────┘
```

---

## Stage 1: Doc-set Matching (Jaccard Similarity)

**Purpose:** Find the best matching doc-set when `target_doc_sets` not provided

**Algorithm:**
```python
def _calculate_jaccard(set1: List[str], set2: List[str]) -> float:
    s1, s2 = set(set1), set(set2)
    if not s1 or not s2:
        return 0.0
    return len(s1 & s2) / len(s1 | s2)
```

**Keyword Extraction:**
```python
def _extract_keywords(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z]+", text.lower())
```

**Threshold:** `threshold_doc_set = 0.6`

**When triggered:** When `target_doc_sets` is `None` (auto-detection mode)

**Behavior:**
- If only one doc-set available: return it directly (skip matching)
- Otherwise: compute Jaccard similarity between query keywords and doc-set names
- Return best match if score >= 0.6, else return first doc-set

---

## Stage 2: BM25 Page Title Matching

**Purpose:** Find relevant page titles using BM25 scoring

**BM25 Parameters:**
```python
k1: float = 1.2  # Term frequency saturation
b: float = 0.75  # Length normalization
threshold_page_title: float = 0.6
```

**BM25 Scoring Formula:**
```
score = Σ IDF(term) × (tf × (k1 + 1)) / (tf + k1 × (1 - b + b × doc_len/avg_doc_len))
IDF(term) = log((N - df + 0.5) / (df + 0.5) + 1.0)
```

**Text Preprocessing:**
- Tokenization: `r"\b\w+\b"`
- Lowercasing: enabled
- Stop words filtered: the, a, an, and, or, is, are, to, for, with...
- **Stemming disabled** for page title matching

**Threshold:** `threshold_page_title = 0.6`

**Success Condition:**
```python
is_basic = score >= threshold_page_title  # 0.6
```

---

## Stage 3: BM25 Heading Matching

**Purpose:** Find relevant headings within matched pages

**Threshold:** `threshold_headings = 0.25`

**Additional Thresholds:**
- `threshold_precision = 0.7` (precision match)
- `min_headings = 2` (minimum headings per page)

**Parsing Headings:**
```python
heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
# Extracts level (# to ######) and text content
# Removes markdown links: [text](url) → text
# Removes anchor URLs: ：https://... or : https://...
```

---

## Stage 4: Transformer Re-ranking (Semantic Matching)

**Purpose:** Re-rank BM25 results using semantic similarity

**Language Detection:**
```python
ratio = chinese_chars / total_chars
return "zh" if ratio >= 0.3 else "en"
```

**Models:**
- Chinese: `BAAI/bge-large-zh-v1.5`
- English: `BAAI/bge-large-en-v1.5`

**Similarity Calculation:**
```python
# Cosine similarity via normalized dot product
query_emb = self._normalize(query_emb)
candidate_embs = self._normalize(candidate_embs)
scores = query_emb @ candidate_embs.T  # dot product = cosine
```

**Reranker Configuration:**
```python
reranker_threshold: float = 0.5  # Default, configurable
reranker_top_k: Optional[int] = None  # Keep all if None
```

**Text Preprocessing for Rerank:**
```python
def _preprocess_for_rerank(text, domain_nouns, predicate_verbs):
    # Rule 1: If text contains domain_nouns, keep original
    # Rule 2: If no domain_nouns, remove predicate_verbs
    # Rule 3: Return processed text
```

**Key Insight:** Reranker is called **at most twice**:
1. Once in main flow (if success)
2. Once in fallback flow (if main fails)

These two are mutually exclusive!

---

## Fallback Strategies

### Fallback Mode: Parallel (Default)

Both FALLBACK_1 and FALLBACK_2 execute in parallel, then results are merged.

### Fallback Mode: Serial (Backward Compatible)

FALLBACK_1 executes first; FALLBACK_2 only if FALLBACK_1 fails.

---

## FALLBACK_1: Grep TOC Search

**Purpose:** Search TOC files directly using grep when BM25 fails

**Trigger:** Main flow fails (success = False)

**Command:**
```bash
grep -r -i -E "pattern" {base_dir}/{doc_set} --include=docTOC.md
```

**Keyword Extraction:**
```python
# Uses extract_keywords from bm25_recall.py
# Supports Chinese and English keywords
# Removes stop words
```

**Results Processing:**
- Parse grep output to extract: `toc_path`, `match_content`
- Extract page title from path: `docTOC.md` parent directory
- Extract heading from match: find `#` pattern in match content
- **Apply BM25 re-scoring** to filtered headings

**BM25 Re-scoring:**
```python
score = calculate_bm25_similarity(
    combined_query,
    heading_text,
    BM25Config(k1=1.2, b=0.75, stemming=True)
)
```

**Success Condition:**
```python
is_basic = score >= threshold_headings  # 0.25
is_precision = score >= threshold_precision  # 0.7
```

---

## FALLBACK_2: Grep Context + BM25

**Purpose:** Get context around matches and score nearest heading

**Trigger:** FALLBACK_1 fails or PARALLEL mode

**Command with Context:**
```bash
# First attempt: -B 5
grep -r -i -B 5 -E "pattern" {base_dir}/{doc_set} --include=docTOC.md

# Fallback: -B 20 (if no results)
grep -r -i -B 20 -E "pattern" {base_dir}/{doc_set} --include=docTOC.md
```

**Processing:**
1. Find all headings in grep context (lines starting with `#`)
2. Take the **nearest heading** to the match
3. Apply BM25 scoring to that heading

**Success Condition:**
```python
is_basic = score >= threshold_headings  # 0.25
is_precision = score >= threshold_precision  # 0.7
```

---

## Result Merging (PARALLEL Mode)

When both fallbacks succeed, results are merged:

```python
def _merge_fallback_results(results):
    # 1. Merge pages with same (doc_set, page_title)
    # 2. Deduplicate headings within each page
    # 3. Keep highest BM25 score for duplicates
    # 4. Aggregate heading_count and precision_count
```

---

## Hierarchical Heading Filter

After all matching, apply hierarchical filtering:

```python
def filter_headings_hierarchically(headings, page_title):
    # Keep only highest-level headings per section
    # Removes nested subheadings under same parent
```

---

## Complete Decision Flow

```python
# Main flow
success = len(all_results) >= min_page_titles and any(
    r["score"] >= threshold_precision for r in all_results
)

if not success:
    if fallback_mode == "parallel":
        # Execute both fallbacks
        # Merge results
        # Apply reranker once to merged results
    else:  # serial
        # Try FALLBACK_1
        # If fails, try FALLBACK_2
```

---

## Threshold Summary

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `bm25_k1` | 1.2 | TF saturation |
| `bm25_b` | 0.75 | Length normalization |
| `threshold_page_title` | 0.6 | Page title match threshold |
| `threshold_headings` | 0.25 | Heading match threshold |
| `threshold_precision` | 0.7 | Precision match threshold |
| `threshold_doc_set` | 0.6 | Doc-set match threshold |
| `min_page_titles` | 2 | Minimum pages per doc-set |
| `min_headings` | 2 | Minimum headings per page |
| `reranker_threshold` | 0.5 | Transformer re-rank threshold |
| `reranker_lang_threshold` | 0.3 | Chinese detection ratio |

---

## Reranker Call Count Analysis

**Key Insight: At most 2 calls total**

| Scenario | Call Count | Reason |
|----------|------------|--------|
| Main flow success | 1 | Processed all doc_set pages |
| Main flow fails → Fallback success | 1 | Processed fallback results |
| Both fail | 1 | Reranker applied but results filtered out |

**Explanation:**
- Main flow and fallback are **mutually exclusive**
- If main flow `success = True`, returns immediately (no fallback)
- If main flow `success = False`, enters fallback (1 reranker call)
- **Total reranker calls ≤ 2** (in practice 1 for any given search)

---

## Output Format

### Success Response
```json
{
    "success": true,
    "doc_sets_found": ["@docset1"],
    "results": [
        {
            "doc_set": "@docset1",
            "page_title": "Page Name",
            "toc_path": "path/to/docTOC.md",
            "headings": [
                {
                    "text": "## Heading Text",
                    "level": 2,
                    "score": 0.85,
                    "bm25_sim": 0.32
                }
            ]
        }
    ],
    "fallback_used": null,
    "message": "Search completed"
}
```

### Fallback Response
```json
{
    "success": true,
    "toc_fallback": true,
    "grep_fallback": true,
    "doc_sets_found": ["@docset1"],
    "results": [...],
    "fallback_used": "FALLBACK_1+FALLBACK_2",
    "message": "Search completed"
}
```

### Failure Response
```json
{
    "success": false,
    "doc_sets_found": [],
    "results": [],
    "fallback_used": "FALLBACK_1+FALLBACK_2",
    "message": "No results found after all fallbacks"
}
```
