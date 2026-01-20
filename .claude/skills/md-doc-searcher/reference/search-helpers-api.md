# SearchHelpers API Reference

Semantic retrieval functions for document search operations.

## Import

```python
# Import from skill's scripts directory
import sys
sys.path.insert(0, '.claude/skills/md-doc-searcher/scripts')
from search_helpers import SearchHelpers
```

---

## Content Extraction

### `extract_headings_with_levels(toc_content: str) -> List[dict]`

Extracts headings from TOC content with level, text, and anchor.

```python
headings = SearchHelpers.extract_headings_with_levels("# Agent Skills\n## 1. Create")
# → [{"level": 1, "text": "Agent Skills", ...}, {"level": 2, "text": "1. Create", ...}]
```

---

### `extract_keywords(query: str) -> List[str]`

Extracts core keywords, filtering stop words and preserving technical terms.

```python
keywords = SearchHelpers.extract_keywords("how to configure hooks for deployment")
# → ['configure', 'hooks', 'deployment']
```

---

## Intent & Scoring Framework

### `analyze_query_intent(original_query: str) -> dict`

Returns intent framework - LLM populates semantic fields.

```python
intent = SearchHelpers.analyze_query_intent("如何配置 hooks")
# → {"primary_intent": "UNKNOWN", "specificity_keywords": [...], ...}
```

---

### `calculate_page_title_relevance_score(query: str, toc_content: str = None) -> dict`

PageTitle scoring framework - LLM provides semantic evaluation.

```python
relevance = SearchHelpers.calculate_page_title_relevance_score(query, toc_content)
# → {"score": 0.0, "is_basic": False, "is_precision": False, "rationale": "..."}
```

---

### `calculate_heading_relevance_score(heading_text: str, query: str, query_intent: dict = None) -> dict`

Heading scoring framework - LLM provides semantic evaluation.

```python
relevance = SearchHelpers.calculate_heading_relevance_score("Configure Skills", query, intent)
# → {"score": 0.0, "intent_match": 0.0, "rationale": "..."}
```

---

### `calculate_relevance_score(doc_title: str, doc_context: Optional[str], query_intent: dict) -> dict`

General document scoring framework.

```python
score = SearchHelpers.calculate_relevance_score(title, context, intent)
# → {"score": 0.0, "intent_match": 0.0, "scope_alignment": 0.0, ...}
```

---

## Validation

### `check_heading_requirement(results: list, min_count: int = 2) -> Tuple[bool, int]`

```python
valid, count = SearchHelpers.check_heading_requirement(results, min_count=2)
# → (True, 5)
```

---

### `check_precision_requirement(results: list, precision_threshold: float = 0.7) -> Tuple[bool, int]`

```python
valid, count = SearchHelpers.check_precision_requirement(results, threshold=0.7)
# → (True, 2)
```

---

### `validate_cross_docset_coverage(target_doc_sets: list[str], matched_doc_sets: list[str]) -> dict`

```python
coverage = SearchHelpers.validate_cross_docset_coverage(["A:latest", "B:v1"], ["A:latest"])
# → {"complete": False, "missing": ["B:v1"], "coverage_percentage": 50.0}
```

---

### `get_docset_match_status(doc_set_name: str, page_title_count: int, heading_count: int, precision_count: int, min_page_title: int = 2, min_heading: int = 2) -> dict`

```python
status = SearchHelpers.get_docset_match_status("A:latest", 3, 8, 2)
# → {"doc_set": "A:latest", "page_title_valid": True, "overall_valid": True, ...}
```

---

## Fallback Support

### `annotate_headings_with_page_title(grep_results: list[dict], doc_set: str) -> list[dict]`

Annotates grep results with PageTitle ownership.

```python
annotated = SearchHelpers.annotate_headings_with_page_title(results, "A:latest")
# → [{"heading_text": "...", "page_title": "Agent Skills", ...}]
```

---

### `traceback_to_heading(content_path: str, match_line: int, context_lines: int = 10) -> dict`

Traces content match back to nearest heading.

```python
traceback = SearchHelpers.traceback_to_heading(path, line=50)
# → {"heading_text": "...", "page_title": "Agent Skills", ...}
```
