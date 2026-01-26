# Doc-RAG Pipeline Data Interface Specification

This document specifies the data interfaces between phases in the doc-rag retrieval workflow.

## Phase 0a: md-doc-query-optimizer

### Output Schema

```json
{
  "query_analysis": {
    "doc_set": ["OpenCode_Docs@latest"],
    "domain_nouns": ["hooks", "function"],
    "predicate_verbs": ["create", "register"]
  },
  "optimized_queries": [
    {"rank": 1, "query": "create hooks", "strategy": "translation"},
    {"rank": 2, "query": "register function hooks", "strategy": "expansion"}
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `query_analysis.doc_set` | array | Target documentation sets |
| `query_analysis.domain_nouns` | array | Domain-specific nouns |
| `query_analysis.predicate_verbs` | array | Action verbs |
| `optimized_queries[].rank` | integer | Query ranking |
| `optimized_queries[].query` | string | Optimized query text |
| `optimized_queries[].strategy` | string | Query optimization strategy |

---

## Phase 0b: md-doc-query-router

### Output Schema

```json
{
  "scene": "fact_lookup",
  "reranker_threshold": 0.63,
  "reranker_enabled": true,
  "confidence": 0.85
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `scene` | string | Query classification (fact_lookup, tutorial, api_reference, troubleshooting) |
| `reranker_threshold` | number | LLM reranking threshold (default: 0.63) |
| `reranker_enabled` | boolean | Whether to enable LLM reranking |
| `confidence` | number | Classification confidence |

---

## Transition: Phase 0a + Phase 0b → Phase 1

### Input Format

Array containing outputs from both Phase 0a and Phase 0b:

```json
[
  {
    "phase": "0a",
    "output": {
      "query_analysis": {
        "doc_set": ["OpenCode_Docs@latest"],
        "domain_nouns": ["hooks"],
        "predicate_verbs": ["create"]
      },
      "optimized_queries": [
        {"rank": 1, "query": "create hooks"}
      ]
    }
  },
  {
    "phase": "0b",
    "output": {
      "scene": "fact_lookup",
      "reranker_threshold": 0.63
    }
  }
]
```

### Output Format

```json
{
  "query": ["create hooks"],
  "doc_sets": "OpenCode_Docs@latest",
  "domain_nouns": ["hooks"],
  "predicate_verbs": ["create"],
  "reranker_threshold": 0.63,
  "scene": "fact_lookup"
}
```

### Fields

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `query` | array | 0a | Optimized query text |
| `doc_sets` | string | 0a | Comma-separated doc set names |
| `domain_nouns` | array | 0a | Domain-specific nouns |
| `predicate_verbs` | array | 0a | Action verbs |
| `reranker_threshold` | number | 0b | LLM reranking threshold |
| `scene` | string | 0b | Query classification scene |

---

## Phase 1: md-doc-searcher

### Input Schema (from CLI)

```json
{
  "query": ["create hooks"],
  "base_dir": "/path/to/docs",
  "doc_sets": "OpenCode_Docs@latest",
  "reranker": false,
  "domain_nouns": ["hooks"],
  "predicate_verbs": ["create"],
  "json": true
}
```

### Output Schema

```json
{
  "success": true,
  "total_hits": 10,
  "results": [
    {
      "doc_set": "OpenCode_Docs@latest",
      "file_path": "docs/skills.md",
      "page_title": "Agent Skills",
      "headings": [
        {
          "level": 2,
          "text": "## Create Skills",
          "score": 0.85,
          "rerank_sim": null
        }
      ]
    }
  ],
  "search_stats": {
    "query_time_ms": 125,
    "total_docs_searched": 150
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether search succeeded |
| `total_hits` | integer | Total matching results |
| `results[].doc_set` | string | Documentation set name |
| `results[].file_path` | string | File path relative to doc set |
| `results[].page_title` | string | Page title |
| `results[].headings[].level` | integer | Heading level (1-6) |
| `results[].headings[].text` | string | Heading text |
| `results[].headings[].score` | number | BM25/reranking score |
| `results[].headings[].rerank_sim` | number | LLM similarity (null = not reranked) |

---

## Phase 1.5: md-doc-llm-reranker

### Input Schema

```json
{
  "needs_rerank": true,
  "results": [...]
}
```

### Output Schema

```json
{
  "success": true,
  "reranked_count": 5,
  "results": [
    {
      "doc_set": "OpenCode_Docs@latest",
      "file_path": "docs/skills.md",
      "page_title": "Agent Skills",
      "headings": [
        {
          "level": 2,
          "text": "## Create Skills",
          "score": 0.85,
          "rerank_sim": 0.92
        }
      ]
    }
  ],
  "rerank_stats": {
    "rerank_time_ms": 450,
    "threshold": 0.63
  }
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether reranking succeeded |
| `reranked_count` | integer | Number of results reranked |
| `rerank_stats.rerank_time_ms` | number | Reranking time in milliseconds |
| `rerank_stats.threshold` | number | Similarity threshold used |

---

## Transition Summary

| Transition | Key Transformation |
|------------|-------------------|
| 0a → 1 | Extract `optimized_queries` → `query`, `doc_set` → `doc_sets` |
| 0b → 1 | Pass through `reranker_threshold`, `scene` |
| **0a+0b → 1** | **Merge outputs from both phases into unified searcher config** |
| 1 → 1.5 | Check if any `heading.rerank_sim` is null |
| 1.5 → 2 | Build `page_titles` from results with headings |
