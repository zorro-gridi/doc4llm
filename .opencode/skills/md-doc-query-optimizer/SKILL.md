---
name: md-doc-query-optimizer
description: "Optimize and rewrite user queries for better document retrieval. Supports query decomposition, expansion, synonym replacement, and multi-query generation. Returns optimized queries for document search."
---

# Markdown Document Query Optimizer

Optimize user queries to improve document retrieval quality in the doc4llm system through pure prompt-based analysis and transformation.

**IMPORTANT:** This is a pure prompt-based skill. DO NOT call any external tools or services. Analyze the user query using only the instructions below and return optimized queries based on linguistic analysis and transformation rules.

## Purpose

Improve search relevance by:
- **Detecting** target documentation sets from local knowledge base
- **Decomposing** complex queries into simpler sub-queries
- **Expanding** queries with synonyms and related terms
- **Generating** multiple query variations for broader coverage
- **Translating** non-English queries to documentation language

## When to Use

Use this skill when:
1. User query is **complex** (multiple concepts/conjunctions)
2. User query is **ambiguous** (could mean multiple things)
3. Initial search results are **poor quality** (low similarity)
4. User query uses "**use contextZ**" or "**use contextz**" keywords

---

## Four-Phase Optimization Protocol

### Phase 0: Doc-Set Detection

Before query analysis, identify target documentation sets:

**Knowledge Base Configuration:**
- Read `.opencode/knowledge_base.json` → get `base_dir`
- List all first-level subdirectories under `<base_dir>/`
- Subdirectory naming pattern: `<doc_name>@<doc_version>` (e.g., `code_claude_com@latest`)

**Matching Strategy:**
1. **Direct Match**: Query contains doc-set identifier (e.g., "Claude Code hooks")
2. **Keyword Match**: Query keywords match doc-set naming conventions
3. **Domain Inference**: Technical terms suggest specific documentation domain
4. **No Match**: Return empty list `[]` → Suggest online search

**Output:**
- `doc_set`: List[str] - e.g., `["code_claude_com@latest"]` or `[]` (empty = suggest online search)

### Phase 1: Intent Recognition

For each user query, analyze:

1. **Complexity Check**: Scan for conjunctions (和、以及、与、还有 / and, as well as, along with, also) that indicate multiple distinct concepts
2. **Ambiguity Check**: Identify generic terms (skills, hooks, features) or context-dependent terms (setup, configuration)
3. **Language Detection**: Determine primary language - Chinese, English, or mixed (e.g., "hooks 配置")
4. **Technical Term Extraction**: Identify domain vocabulary (product names, technical concepts, special terms)

### Phase 2: Strategy Selection

| Analysis Result | Primary Strategy | Secondary Actions |
|----------------|------------------|-------------------|
| Has conjunctions | Decomposition | Expand each sub-query |
| Generic/ambiguous term | Expansion | Generate multiple variations |
| Chinese query | Translation | Expand translated terms |
| Mixed language | Translation + preserve | Keep technical terms intact |
| Well-formed specific | None | Return as-is or minor expansion |

### Phase 3: Query Generation

Generate 3-5 optimized queries following:

1. **Prioritize direct translations** for Chinese queries (docs are often English)
2. **Add domain-specific variations** (e.g., "configuration", "setup", "settings")
3. **Include documentation-type modifiers** ("reference", "guide", "tutorial")
4. **Preserve core technical terms** exactly as they appear
5. **Rank by expected relevance** (most direct match first)

---

## Strategy Rules

### Decomposition Rules

When detecting conjunctions (和、以及、与、and):
- Create a focused query for each distinct concept
- Generate variations for each sub-query
- Include combined queries that capture relationships
- Rank sub-queries by specificity (technical > general)

### Expansion Rules

For Chinese terms:
- "配置" + noun → "{noun} configuration", "setup {noun}", "{noun} settings"
- "部署" → "deployment", "deploy", "production setup", "release"
- "安全" → "security", "secure", "authentication", "authorization"
- noun + "相关" → "{noun}", "{noun} guide", "{noun} reference", "using {noun}"

For English terms:
- "how to {verb}" → "{verb} guide", "{verb} tutorial", "{verb} configuration"
- "{noun} related" → "{noun}", "{noun} reference", "{noun} guide", "using {noun}"
- "setup/configure {noun}" → "{noun} configuration", "{noun} setup"

### Translation Rules

- Translate non-technical words to target language (usually English for docs)
- Preserve technical terms in original form (API, hooks, middleware, etc.)
- Handle mixed language by transliterating only non-technical words

---

## Representative Examples

### Example 1: Complex Query Decomposition

**Input:** "Claude Code 中 hooks 如何配置，以及部署时的注意事项"

**Analysis:** Contains "以及" (conjunction), Chinese, two concepts: (1) hooks configuration, (2) deployment considerations

**Optimized Queries:**
```
1. Claude Code hooks configuration
2. deployment hooks best practices
3. hooks setup Claude Code
4. Claude Code deployment setup
5. deployment hooks注意事项
```

### Example 2: Ambiguous Query Expansion

**Input:** "skills"

**Analysis:** Generic term, English, likely "Agent Skills" in documentation context

**Optimized Queries:**
```
1. Agent Skills
2. skills reference
3. using skills
4. skills guide
5. skills
```

### Example 3: Mixed Language Processing

**Input:** "hooks 配置相关"

**Analysis:** Mixed language, technical term "hooks" to preserve, "配置相关" → configuration/setup

**Optimized Queries:**
```
1. hooks configuration
2. setup hooks
3. hooks settings
4. configure hooks
5. hooks setup guide
```

---

## Integration Protocol (Updated)

This skill works with `md-doc-searcher` in the following workflow:

**Step 1:** Receive user query
**Step 2:** Phase 0 - Detect target doc-sets from local knowledge base
**Step 3:** Apply optimization protocol to generate 3-5 queries
**Step 4:** Output BOTH formats:
   - Human-readable format (for display)
   - JSON format (for md-doc-searcher)
**Step 5:**
   - If `doc_set` is empty → Suggest online search, DO NOT call doc_searcher_cli.py
   - If `doc_set` has values → Proceed with md-doc-searcher CLI
**Step 6:** md-doc-searcher searches specified doc-sets
**Step 7:** Aggregate and deduplicate results
**Step 8:** Present most relevant documents to user

---

## Output Format

**Dual Output Support:**
- **Human-readable**: For user display (default)
- **JSON format**: For machine parsing by downstream skills

### Human-Readable Format (Default)

```
## Query Analysis Summary
- Original: "{original_query}"
- Language: {detected_language}
- Complexity: {low/medium/high}
- Ambiguity: {low/medium/high}
- Applied Strategies: {strategy_list}
- Doc-Set: <doc_name>@<doc_version>  [can be multiple, comma-separated]

## Optimized Queries (Ranked)
1. "{primary_query}" - {strategy_applied}: {rationale}
2. "{secondary_query}" - {strategy_applied}: {rationale}
3. "{tertiary_query}" - {strategy_applied}: {rationale}
...

## Search Recommendation
Perform online search - No matching documentation set found in local knowledge base.
```

### JSON Output Format (For md-doc-searcher)

```json
{
  "query_analysis": {
    "original": "{original_query}",
    "language": "{detected_language}",
    "complexity": "{low|medium|high}",
    "ambiguity": "{low|medium|high}",
    "strategies": ["{strategy1}", "{strategy2}"],
    "doc_set": ["<doc_name>@<doc_version>"]
  },
  "optimized_queries": [
    {
      "rank": 1,
      "query": "{primary_query}",
      "strategy": "{strategy_applied}",
      "rationale": "{rationale}"
    },
    {
      "rank": 2,
      "query": "{secondary_query}",
      "strategy": "{strategy_applied}",
      "rationale": "{rationale}"
    }
  ],
  "search_recommendation": {
    "online_suggested": true,
    "reason": "Only when after no matching documentation set found - perform online search"
  }
}
```

**Usage Rules:**
- If `doc_set` is empty array → Do NOT call doc_searcher_cli.py
- Output recommendation for online search
- If `doc_set` has values → Proceed with md-doc-searcher CLI

**Example Output (JSON):**

```json
{
  "query_analysis": {
    "original": "如何配置 hooks",
    "language": "Chinese",
    "complexity": "low",
    "ambiguity": "medium",
    "strategies": ["translation", "expansion"],
    "doc_set": ["code_claude_com@latest"]
  },
  "optimized_queries": [
    {
      "rank": 1,
      "query": "hooks configuration",
      "strategy": "translation",
      "rationale": "Direct English translation"
    },
    {
      "rank": 2,
      "query": "setup hooks",
      "strategy": "expansion",
      "rationale": "Action-oriented variation"
    },
    {
      "rank": 3,
      "query": "hooks settings",
      "strategy": "expansion",
      "rationale": "Synonym for configuration"
    }
  ]
}
```

**Example Output (No Match with empty doc-sest - JSON):**

```json
{
  "query_analysis": {
    "original": "machine learning basics",
    "language": "English",
    "complexity": "low",
    "ambiguity": "high",
    "strategies": ["expansion"],
    "doc_set": []
  },
  "optimized_queries": [
    {
      "rank": 1,
      "query": "machine learning basics",
      "strategy": "none",
      "rationale": "No optimization needed"
    }
  ],
  "search_recommendation": {
    "online_suggested": true,
    "reason": "Only when after no matching documentation set found - perform online search"
  }
}
```
