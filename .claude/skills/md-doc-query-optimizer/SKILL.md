---
name: md-doc-query-optimizer
description: "Optimize and rewrite user queries for better document retrieval. Use when the user's query is ambiguous, complex, or could benefit from expansion. Supports query decomposition, expansion, synonym replacement, and multi-query generation. Returns optimized queries for document search."
allowed-tools:
  - Read
  - Bash
---

# Markdown Document Query Optimizer

Optimize user queries to improve document retrieval quality in the doc4llm system.

## Purpose

Improve search relevance by:
- **Decomposing** complex queries into simpler sub-queries
- **Expanding** queries with synonyms and related terms
- **Generating** multiple query variations for broader coverage
- **Rewriting** ambiguous queries for clarity

## When to Use

Use this skill when:
1. User query is **complex** (multiple concepts/conjunctions)
2. User query is **ambiguous** (could mean multiple things)
3. Initial search results are **poor quality** (low similarity)
4. User query uses **colloquial language** that doesn't match documentation terminology

## Quick Start

```python
from doc4llm.tool.md_doc_extractor.query_optimizer import QueryOptimizer

optimizer = QueryOptimizer()

# Single query optimization
optimized = optimizer.optimize("如何配置 hooks")
# Returns: ["hooks configuration", "setup hooks", "hooks settings"]

# Complex query decomposition
sub_queries = optimizer.decompose("Claude Code 中 hooks 如何配置，以及部署时的注意事项")
# Returns:
# [
#   "Claude Code hooks configuration",
#   "deployment hooks注意事项",
#   "Claude Code deployment setup"
# ]
```

---

## Query Optimization Strategies

### Strategy 1: Query Expansion

Add synonyms and related terms to improve recall.

**Example:**
```
Original: "如何配置 hooks"
→ Expanded:
  - "hooks configuration"
  - "setup hooks"
  - "hooks settings"
  - "configure hooks"
  - "hooks setup guide"
```

**Expansion Rules:**
| Pattern | Expansion |
|---------|-----------|
| "配置" | configuration, setup, settings, configure |
| "部署" | deployment, deploy, production, release |
| "安全" | security, secure, authentication, authorization |
| "API" | API, interface, endpoint, REST |
| "文档" | documentation, docs, guide, reference |

### Strategy 2: Query Decomposition

Break complex queries into simpler sub-queries.

**Example:**
```
Original: "Claude Code 中 hooks 如何配置，以及部署时的注意事项"

Decomposition:
1. "Claude Code hooks configuration"
2. "deployment hooks注意事项"
3. "Claude Code deployment setup"

Rationale:
- The query has two main concepts: hooks configuration AND deployment
- Breaking into sub-queries allows targeted retrieval
- Results can be merged in the reasoning phase
```

**Decomposition Patterns:**

| Pattern | Decomposition |
|---------|---------------|
| `A 和 B` | Query A, Query B |
| `A 以及 B` | Query A, Query B |
| `A 与 B` | Query A, Query B, "A B" |
| `A 如何做，B 注意什么` | "A how to", "B best practices" |
| `关于 A 的 B` | "A B", "B for A" |

### Strategy 3: Multi-Query Generation

Generate multiple query variations for parallel search.

**Example:**
```
Original: "skills相关"

Multi-Query:
1. "Agent Skills"          (Direct match)
2. "skills reference"      (Documentation type)
3. "using skills"          (Action-oriented)
4. "skills guide"          (Tutorial type)
```

**Query Variations:**
- **Exact match**: Original query
- **Documentation type**: Add "reference", "guide", "tutorial"
- **Action-oriented**: Add "using", "how to", "configure"
- **Concept-focused**: Extract core concept

### Strategy 4: Query Rewriting

Rewrite ambiguous or colloquial queries for clarity.

**Example:**
```
Original: "那个hook咋弄来着"

Rewritten:
1. "hooks configuration"
2. "setup hooks"
3. "configure hooks"

Rationale:
- "咋弄" is colloquial for "how to"
- "来着" indicates a reminder/forgot context
- Formal: "hooks configuration"
```

---

## Optimization Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: User Query                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Query Analysis│
                    │ - Complexity  │
                    │ - Ambiguity   │
                    │ - Terminology │
                    └───────────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
            ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ Decomposition│ │  Expansion  │ │  Rewriting  │
    │ (Complex)    │ │ (Ambiguous) │ │ (Colloquial)│
    └─────────────┘ └─────────────┘ └─────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                    ┌───────────────┐
                    │ Multi-Query   │
                    │ Generation    │
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Query Ranking │
                    │ (by relevance)│
                    └───────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │ Optimized Queries (Ranked)   │
              └─────────────────────────────┘
```

---

## Implementation Guide

### Step 1: Analyze Query Type

Determine which optimization strategy to apply:

```python
def analyze_query(query: str) -> dict:
    """Analyze query characteristics."""
    return {
        "is_complex": contains_conjunctions(query),
        "is_ambiguous": has_multiple_meanings(query),
        "is_colloquial": uses_informal_language(query),
        "language": detect_language(query),  # "zh", "en", "mixed"
        "domain": infer_domain(query),  # "claude", "python", etc.
        "has_technical_terms": extract_technical_terms(query)
    }
```

### Step 2: Apply Optimization Strategy

Based on analysis, choose the appropriate strategy:

| Query Type | Strategy | Example |
|------------|----------|---------|
| Complex with conjunctions | Decomposition | "A and B" → ["A", "B"] |
| Ambiguous single term | Expansion | "hooks" → ["hooks", "webhooks", "hooks configuration"] |
| Colloquial | Rewriting | "咋弄" → "how to configure" |
| Technical term | Expansion + Synonyms | "API" → ["API", "interface", "endpoint"] |
| Well-formed specific query | No optimization needed | "Hooks reference" → ["Hooks reference"] |

### Step 3: Generate Optimized Queries

Return ranked list of optimized queries:

```python
def generate_optimized_queries(original_query: str, max_queries: int = 5) -> list:
    """Generate optimized queries ranked by expected relevance."""
    analysis = analyze_query(original_query)

    optimized = []

    # Add original query (always first)
    optimized.append(original_query)

    # Apply strategies based on analysis
    if analysis["is_complex"]:
        optimized.extend(decompose_query(original_query))

    if analysis["is_ambiguous"] or analysis["is_colloquial"]:
        optimized.extend(rewrite_query(original_query))

    # Always add expansions for technical terms
    if analysis["has_technical_terms"]:
        optimized.extend(expand_query(original_query))

    # Remove duplicates and rank
    optimized = list(set(optimized))
    optimized = rank_queries(optimized, analysis)

    return optimized[:max_queries]
```

---

## Language Support

### Chinese Query Patterns

| Pattern | Optimization |
|---------|--------------|
| "如何{verb}" | "{verb} configuration", "how to {verb}" |
| "{noun}相关" | "{noun}", "{noun} guide", "{noun} reference" |
| "关于{topic}" | "{topic}", "{topic} overview" |
| "怎么{verb}" | "how to {verb}", "{verb} tutorial" |
| "{noun}的{feature}" | "{feature} in {noun}", "{noun} {feature}" |

### English Query Patterns

| Pattern | Optimization |
|---------|--------------|
| "how to {verb}" | "{verb} guide", "{verb} tutorial", "{verb} configuration" |
| "{noun} related" | "{noun}", "{noun} reference", "{noun} guide" |
| "about {topic}" | "{topic}", "{topic} overview", "{topic} introduction" |
| "what is {noun}" | "{noun}", "{noun} definition", "{noun} explained" |

---

## Usage Examples

### Example 1: Complex Query Decomposition

**Input:** "Claude Code 中 hooks 如何配置，以及部署时的注意事项"

**Process:**
1. Detect conjunction: "以及" (and/as well as)
2. Split into sub-queries:
   - "Claude Code hooks configuration"
   - "deployment hooks注意事项"
3. Generate variations:
   - "hooks setup Claude Code"
   - "deployment hooks best practices"

**Output:**
```python
[
    "Claude Code hooks configuration",  # Primary
    "deployment hooks注意事项",          # Secondary
    "hooks setup Claude Code",          # Variation
    "deployment hooks best practices"   # Translation
]
```

### Example 2: Ambiguous Query Expansion

**Input:** "skills"

**Process:**
1. Detect ambiguity: "skills" is generic
2. Context inference: Assuming "Agent Skills" (most common)
3. Generate variations:
   - "Agent Skills" (specific)
   - "skills reference" (documentation type)
   - "using skills" (action-oriented)

**Output:**
```python
[
    "skills",
    "Agent Skills",
    "skills reference",
    "using skills",
    "skills guide"
]
```

### Example 3: Colloquial Query Rewriting

**Input:** "那个hook咋弄来着"

**Process:**
1. Detect colloquialism: "咋弄" (how to), "来着" (forgot/remind)
2. Extract technical term: "hook" → "hooks"
3. Rewrite formally:
   - "hooks configuration"
   - "setup hooks"
   - "how to configure hooks"

**Output:**
```python
[
    "hooks configuration",
    "setup hooks",
    "how to configure hooks",
    "hooks setup guide"
]
```

---

## Integration with md-doc-searcher

After optimizing queries, pass them to `AgenticDocMatcher`:

```python
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor
from doc4llm.tool.md_doc_extractor.agentic_matcher import AgenticDocMatcher
from doc4llm.tool.md_doc_extractor.query_optimizer import QueryOptimizer

# Initialize components
extractor = MarkdownDocExtractor()
matcher = AgenticDocMatcher(extractor)
optimizer = QueryOptimizer()

# User query
user_query = "Claude Code 中 hooks 如何配置，以及部署时的注意事项"

# Optimize query
optimized_queries = optimizer.optimize(user_query)

# Search with all optimized queries
all_results = []
for query in optimized_queries:
    results = matcher.match(query, max_results=3)
    all_results.extend(results)

# Deduplicate and re-rank
final_results = deduplicate_and_rerank(all_results)
```

---

## Output Format

Return optimized queries as a ranked list:

```python
{
    "original_query": "如何配置 hooks",
    "optimized_queries": [
        {
            "query": "hooks configuration",
            "rank": 1,
            "strategy": "translation",
            "confidence": 0.95
        },
        {
            "query": "setup hooks",
            "rank": 2,
            "strategy": "expansion",
            "confidence": 0.85
        },
        {
            "query": "hooks settings",
            "rank": 3,
            "strategy": "expansion",
            "confidence": 0.75
        }
    ],
    "applied_strategies": ["translation", "expansion"],
    "query_analysis": {
        "language": "zh",
        "complexity": "low",
        "ambiguity": "medium"
    }
}
```

---

## Configuration

```python
config = {
    "max_optimized_queries": 5,
    "min_confidence_threshold": 0.6,
    "enable_decomposition": True,
    "enable_expansion": True,
    "enable_rewriting": True,
    "language_priority": ["zh", "en"],  # Priority for translation
    "domain_mapping": {
        "claude": ["Claude Code", "Claude"],
        "python": ["Python", "python3"],
        "react": ["React", "ReactJS"]
    }
}

optimizer = QueryOptimizer(config=config)
```

---

## Best Practices

1. **Preserve intent**: Never change the user's core intent
2. **Add, don't replace**: Optimized queries should supplement, not replace, the original
3. **Respect context**: Use conversation context when available
4. **Limit expansion**: Don't generate too many variations (3-5 is optimal)
5. **Rank by confidence**: Help the retriever prioritize which queries to use first

---

## Limitations

- Does not perform actual semantic understanding of query meaning
- Relies on pattern matching and heuristics
- May not handle domain-specific jargon correctly
- Translation quality depends on predefined pattern tables
