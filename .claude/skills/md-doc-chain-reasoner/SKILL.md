---
name: md-doc-chain-reasoner
description: "Multi-hop reasoning for complex document queries. Decomposes complex questions into sub-queries, executes multi-step retrieval, tracks information sources, and synthesizes comprehensive answers. Use when user asks complex questions requiring information from multiple documents or reasoning across documents."
allowed-tools:
  - Read
  - Bash
---

# Markdown Document Chain Reasoner

Multi-hop reasoning system for complex document queries requiring information synthesis from multiple sources.

## Purpose

Enable agentic reasoning for complex queries by:
- **Decomposing** complex questions into reasoning chains
- **Planning** multi-step retrieval strategies
- **Executing** sequential document searches
- **Tracking** source attribution across reasoning steps
- **Synthesizing** comprehensive answers with citations

## When to Use

Use this skill when:
1. User query contains **multiple concepts** (conjunctions: "and", "or", "as well as")
2. User query requires **comparison** between concepts
3. User query asks **"how X relates to Y"**
4. User query requires **procedural reasoning** (step-by-step)
5. Single document search returns **insufficient results**

## Quick Start

```python
from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor, AgenticDocMatcher
from doc4llm.tool.md_doc_extractor.chain_reasoner import ChainReasoner

# Initialize components
extractor = MarkdownDocExtractor()
matcher = AgenticDocMatcher(extractor)
reasoner = ChainReasoner(extractor, matcher)

# Perform multi-hop reasoning
result = reasoner.reason(
    query="Claude Code 中 hooks 如何配置，以及部署时的注意事项",
    max_hops=3,
    max_documents_per_hop=5
)

# Result contains:
# - decomposition: Reasoning chain
# - steps: Individual reasoning steps with sources
# - answer: Synthesized answer
# - citations: Source attribution
```

---

## Multi-Hop Reasoning Workflow

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT: Complex User Query                                   │
│  "Claude Code 中 hooks 如何配置，以及部署时的注意事项"          │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Query Analysis│
                    │ - Complexity  │
                    │ - Concepts    │
                    │ - Relations   │
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Decomposition │
                    │ Sub-queries:  │
                    │ 1. hooks config│
                    │ 2. deployment  │
                    └───────────────┘
                            │
            ┌───────────────┴───────────────┐
            │                               │
            ▼                               ▼
    ┌───────────────┐             ┌───────────────┐
    │   Hop 1       │             │   Hop 2       │
    │ hooks config  │             │  deployment   │
    │ ↓ Search      │             │  ↓ Search     │
    │ ↓ Retrieve    │             │  ↓ Retrieve   │
    │ ↓ Extract     │             │  ↓ Extract    │
    └───────────────┘             └───────────────┘
            │                               │
            └───────────────┬───────────────┘
                            ▼
                    ┌───────────────┐
                    │  Synthesis    │
                    │  - Merge info │
                    │  - Resolve    │
                    │  - Structure  │
                    └───────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Output       │
                    │  - Answer     │
                    │  - Citations  │
                    │  - Confidence │
                    └───────────────┘
```

---

## Query Decomposition Patterns

### Pattern 1: Conjunction (AND)

**Query:** "hooks 配置以及部署注意事项"

**Decomposition:**
```
Hop 1: "hooks configuration"
Hop 2: "deployment hooks注意事项"
Synthesis: Combine configuration steps with deployment considerations
```

### Pattern 2: Comparison

**Query:** "Agent Skills 和 Custom Skills 的区别"

**Decomposition:**
```
Hop 1: "Agent Skills"
Hop 2: "Custom Skills"
Hop 3: "skills comparison" (if needed)
Synthesis: Compare features, use cases, capabilities
```

### Pattern 3: Procedural

**Query:** "如何创建 skill 并配置 hooks"

**Decomposition:**
```
Hop 1: "create skill"
Hop 2: "configure hooks"
Synthesis: Sequential procedural guide
```

### Pattern 4: Causal

**Query:** "为什么 hooks 失败了"

**Decomposition:**
```
Hop 1: "hooks troubleshooting"
Hop 2: "common hooks errors"
Synthesis: Identify root causes and solutions
```

---

## Implementation Guide

### Step 1: Analyze Query Complexity

```python
def analyze_query_complexity(query: str) -> dict:
    """Determine if query requires multi-hop reasoning."""
    return {
        "is_complex": has_conjunctions(query),
        "num_concepts": count_distinct_concepts(query),
        "requires_comparison": has_comparison_words(query),
        "requires_procedural": has_procedural_words(query),
        "estimated_hops": estimate_required_hops(query)
    }
```

### Step 2: Decompose Query

```python
def decompose_query(query: str) -> list:
    """Decompose complex query into sub-queries."""
    sub_queries = []

    # Split by conjunctions
    for pattern in CONJUNCTION_PATTERNS:
        parts = re.split(pattern, query)
        if len(parts) > 1:
            sub_queries.extend(parts)
            break

    # If no conjunctions, check for comparison
    if not sub_queries and has_comparison_words(query):
        sub_queries = extract_comparison_terms(query)

    return sub_queries
```

### Step 3: Execute Sequential Retrieval

```python
def execute_retrieval_chain(
    sub_queries: list,
    matcher: AgenticDocMatcher,
    max_docs_per_hop: int
) -> list:
    """Execute sequential retrieval for each sub-query."""
    reasoning_steps = []

    for i, sub_query in enumerate(sub_queries, start=1):
        # Search for documents
        results = matcher.match(sub_query, max_results=max_docs_per_hop)

        # Extract relevant content
        documents = [extract_content(r) for r in results]

        reasoning_steps.append({
            "hop": i,
            "query": sub_query,
            "results": results,
            "documents": documents
        })

    return reasoning_steps
```

### Step 4: Synthesize Answer

```python
def synthesize_answer(reasoning_steps: list, original_query: str) -> dict:
    """Synthesize comprehensive answer from reasoning steps."""
    # Merge information from all steps
    all_content = []
    sources = []

    for step in reasoning_steps:
        for doc in step["documents"]:
            all_content.append(doc["content"])
            sources.append({
                "title": doc["title"],
                "hop": step["hop"],
                "relevance": doc.get("similarity", 0)
            })

    # Structure the answer
    answer = {
        "summary": generate_summary(all_content),
        "detailed_sections": organize_by_concept(all_content),
        "sources": deduplicate_sources(sources),
        "confidence": calculate_confidence(reasoning_steps)
    }

    return answer
```

---

## Output Format

```python
{
    "original_query": "Claude Code 中 hooks 如何配置，以及部署时的注意事项",
    "decomposition": {
        "num_hops": 2,
        "sub_queries": [
            "Claude Code hooks configuration",
            "deployment hooks注意事项"
        ]
    },
    "reasoning_steps": [
        {
            "hop": 1,
            "query": "Claude Code hooks configuration",
            "documents_found": 2,
            "key_info": [
                "Hooks are configured in .claude/hooks.json",
                "Each hook has name, command, and timeout fields"
            ],
            "sources": [
                {"title": "Hooks reference", "similarity": 0.92},
                {"title": "Get started with hooks", "similarity": 0.85}
            ]
        },
        {
            "hop": 2,
            "query": "deployment hooks注意事项",
            "documents_found": 1,
            "key_info": [
                "Deployment hooks run before deployment",
                "Use for validation, testing, and build steps"
            ],
            "sources": [
                {"title": "Deployment guide", "similarity": 0.78}
            ]
        }
    ],
    "answer": {
        "summary": "Hooks in Claude Code are configured...",
        "sections": [
            {
                "title": "Configuration",
                "content": "Hooks are configured in .claude/hooks.json...",
                "sources": ["Hooks reference"]
            },
            {
                "title": "Deployment Considerations",
                "content": "For deployment, consider the following...",
                "sources": ["Deployment guide"]
            }
        ]
    },
    "citations": [
        {
            "source": "Hooks reference",
            "location": "Configure Hooks section",
            "relevance": 0.92
        },
        {
            "source": "Deployment guide",
            "location": "Pre-deployment hooks",
            "relevance": 0.78
        }
    ],
    "confidence": 0.85
}
```

---

## Citation Format

When synthesizing answers, use proper citation format:

```markdown
## Hooks Configuration

According to **[Hooks reference > Configure Hooks]**:

> Hooks are configured in the `.claude/hooks.json` file. Each hook
> requires:
> - `name`: Hook identifier
> - `command`: Command to execute
> - `timeout`: Maximum execution time

## Deployment Considerations

**[Deployment guide > Pre-deployment hooks]** notes:

> Deployment hooks run before the actual deployment. Use them for:
> - Validation checks
> - Running tests
> - Build preparation

**Sources:**
- Hooks reference (similarity: 0.92)
- Deployment guide (similarity: 0.78)
```

---

## Configuration

```python
config = {
    "max_hops": 3,                      # Maximum reasoning steps
    "max_documents_per_hop": 5,         # Documents to retrieve per step
    "min_similarity_threshold": 0.6,    # Minimum relevance for inclusion
    "enable_citation_tracking": True,   # Track source attribution
    "enable_cross_hop_refinement": True,# Refine searches based on previous hops
    "synthesis_strategy": "comprehensive",  # "concise" or "comprehensive"
}

reasoner = ChainReasoner(extractor, matcher, config=config)
```

---

## Advanced Features

### Cross-Hop Refinement

Use results from previous hops to refine subsequent searches:

```python
# Hop 1: Search for "Agent Skills"
hop1_results = matcher.match("Agent Skills")

# Hop 2: Search for "hooks" but filter to Agent Skills context
hop2_query = "hooks in Agent Skills"
hop2_results = matcher.match(hop2_query)

# This ensures Hop 2 results are relevant to Agent Skills context
```

### Confidence Scoring

Calculate overall confidence based on:
- Document relevance scores
- Source diversity
- Information completeness
- Cross-validation between sources

```python
confidence = (
    avg_similarity * 0.4 +
    source_diversity * 0.3 +
    completeness * 0.2 +
    cross_validation * 0.1
)
```

### Conflict Detection

Identify conflicting information across sources:

```python
def detect_conflicts(reasoning_steps: list) -> list:
    """Detect conflicting information across sources."""
    conflicts = []

    # Compare statements across documents
    for i, step1 in enumerate(reasoning_steps):
        for step2 in reasoning_steps[i+1:]:
            if has_contradiction(step1, step2):
                conflicts.append({
                    "statement": step1["key_info"],
                    "source1": step1["sources"][0]["title"],
                    "source2": step2["sources"][0]["title"]
                })

    return conflicts
```

---

## Usage Examples

### Example 1: Conjunction Query

**Input:** "Claude Code 中 hooks 如何配置，以及部署时的注意事项"

**Process:**
1. Decompose into 2 sub-queries
2. Hop 1: Retrieve hooks configuration docs
3. Hop 2: Retrieve deployment considerations
4. Synthesize combined answer

**Output:**
```python
{
    "answer": {
        "summary": "Claude Code hooks are configured in .claude/hooks.json...",
        "sections": [...]
    },
    "reasoning_chain": ["hooks configuration", "deployment hooks注意事项"],
    "sources": ["Hooks reference", "Deployment guide"]
}
```

### Example 2: Comparison Query

**Input:** "Agent Skills 和 Custom Skills 的区别"

**Process:**
1. Decompose into comparison
2. Hop 1: Retrieve Agent Skills docs
3. Hop 2: Retrieve Custom Skills docs
4. Hop 3: Retrieve comparison information
5. Synthesize comparison table

**Output:**
```python
{
    "answer": {
        "summary": "Agent Skills and Custom Skills serve different purposes...",
        "comparison_table": {
            "Agent Skills": "Pre-built for common tasks",
            "Custom Skills": "User-defined for specific needs"
        }
    },
    "reasoning_chain": ["Agent Skills", "Custom Skills", "skills comparison"],
    "sources": [...]
}
```

---

## Best Practices

1. **Limit hops**: More hops = more complexity, aim for 2-3
2. **Track sources**: Always maintain citation trail
3. **Detect conflicts**: Flag contradictory information
4. **Provide context**: Explain reasoning steps to user
5. **Handle failures**: Gracefully degrade if a hop fails

---

## Limitations

- Requires multiple document searches (slower than single-hop)
- May retrieve redundant information
- Synthesis quality depends on individual hop quality
- Complex reasoning may still require human validation
