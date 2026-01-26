---
name: md-doc-llm-reranker
description: "Pure LLM prompt-based skill. Analyze retrieval results and assign semantic similarity scores (rerank_sim) to headings based on query relevance. Filters out irrelevant results and returns re-ranked results in the original input format."
allowed-tools: []
disable-model-invocation: true
context: fork
---

# Markdown Document LLM Reranker

Analyze and re-rank document retrieval results using pure LLM prompt-based semantic similarity scoring.

---

## Purpose

Improve retrieval quality by:

- Analyzing semantic relevance between query and retrieved headings
- Assigning similarity scores (`rerank_sim`) to each heading
- Filtering out irrelevant results based on score threshold
- Preserving the original input structure in output

---

## When to Use

Use this skill when:

1. `md-doc-searcher` returns results that need semantic re-ranking
2. Results contain `rerank_sim: null` fields that need to be populated
3. Irrelevant results need to be filtered out from retrieval results

---

## Input Format

The skill receives JSON data with the following structure:

```json
{
  "success": true,
  "toc_fallback": true,
  "grep_fallback": true,
  "query": [
    "opencode skills creation guide",
    "opencode skills setup tutorial",
    "how to create skills in opencode",
    "opencode skills configuration"
  ],
  "doc_sets_found": [
    "OpenCode_Docs@latest"
  ],
  "results": [
    {
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "GitHub",
      "toc_path": "/path/to/OpenCode_Docs@latest/GitHub/docTOC.md",
      "headings": [
        {
          "level": 2,
          "text": "4. Configuration",
          "rerank_sim": null,
          "bm25_sim": null
        }
      ]
    },
    {
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "Plugins",
      "toc_path": "/path/to/OpenCode_Docs@latest/Plugins/docTOC.md",
      "headings": [
        {
          "level": 2,
          "text": "3. Create a plugin",
          "rerank_sim": null,
          "bm25_sim": null
        }
      ]
    }
  ]
}
```

---

## Processing Logic

### Step 1: Query Intent Analysis

Analyze all queries to understand the core information need:

- Identify common themes across multiple query variations
- Extract key concepts, entities, and actions
- Determine the primary and secondary information goals

### Step 2: Heading Semantic Analysis

For each heading in each result:

1. **Extract heading text** from `headings[].text`
2. **Extract page context** from `page_title`
3. **Analyze relevance** to the query intent
4. **Assign similarity score** based on semantic match quality

### Step 3: Similarity Scoring Criteria

| Score Range | Meaning | Criteria |
|-------------|---------|----------|
| `0.9 - 1.0` | Perfect match | Heading directly answers the query, contains exact key terms |
| `0.7 - 0.89` | Strong match | Heading is highly relevant, contains most key terms |
| `0.5 - 0.69` | Moderate match | Heading is somewhat relevant, partial term overlap |
| `0.3 - 0.49` | Weak match | Heading has minor relevance, tangential connection |
| `0.1 - 0.29` | Poor match | Heading barely relates to query |
| `0.0` | No match | Heading is completely unrelated |

### Step 4: Relevance Decision Factors

**High Score Indicators:**

- Heading contains exact query keywords or synonyms
- Heading matches query intent (e.g., "create", "setup", "configure" for creation queries)
- Heading is at appropriate section level for the topic
- Page title provides relevant context

**Low Score Indicators:**

- Heading is generic/menu navigation text
- Heading covers unrelated topics
- Heading is too specific to a different use case
- No semantic connection to query concepts

### Step 5: Filtering

**Filter Threshold:** `rerank_sim >= 0.5`

- **Keep:** Headings with `rerank_sim >= 0.5`
- **Remove:** Headings with `rerank_sim < 0.5`

**Important:** If ALL headings in a result have `rerank_sim < 0.5`, remove the entire result object from `results` array.

---

## Scoring Examples

### Example 1: High Relevance

**Query:** "how to create skills in opencode"

**Heading:** "3. Create a skill"

**Analysis:**
- Contains action verb "Create" matching query intent
- Contains noun "skill" exactly matching query term
- Page context "Plugins" provides relevant framework

**Score:** `0.85`

### Example 2: Moderate Relevance

**Query:** "opencode skills configuration"

**Heading:** "4. Configuration"

**Analysis:**
- Contains "Configuration" matching query keyword
- Heading is generic without "skills" mention
- Page title provides some context

**Score:** `0.55`

### Example 3: Low Relevance

**Query:** "opencode skills creation guide"

**Heading:** "GitHub Integration"

**Analysis:**
- No connection to skills or creation
- Completely different topic

**Score:** `0.15` → Filter out

---

## Output Format

Return the **exact same JSON structure** with:

1. **`rerank_sim` populated**: Fill in `null` values with calculated scores (0.0 - 1.0)
2. **`headings` filtered**: Remove headings with `rerank_sim < 0.5`
3. **`results` filtered**: Remove results with empty `headings` array after filtering

```json
{
  "success": true,
  "toc_fallback": true,
  "grep_fallback": true,
  "query": [
    "opencode skills creation guide",
    "opencode skills setup tutorial"
  ],
  "doc_sets_found": [
    "OpenCode_Docs@latest"
  ],
  "results": [
    {
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "Plugins",
      "toc_path": "/path/to/OpenCode_Docs@latest/Plugins/docTOC.md",
      "headings": [
        {
          "level": 2,
          "text": "3. Create a skill",
          "rerank_sim": 0.85,
          "bm25_sim": null
        },
        {
          "level": 2,
          "text": "4. Configure skills",
          "rerank_sim": 0.72,
          "bm25_sim": null
        }
      ]
    }
  ]
}
```

---

## Scoring Guidelines

### Do:

- Consider **all queries** in the array when scoring (query variations indicate intent)
- Use **page_title** as additional context for scoring
- Assign **conservative scores** when uncertain (prefer 0.5-0.7 over 0.9)
- **Filter aggressively** to reduce noise (better to remove borderline cases)
- Consider **semantic meaning**, not just keyword matching

### Don't:

- Score based solely on keyword presence
- Assign high scores to generic headings like "Overview", "Introduction"
- Keep results that have no relevant headings
- Modify any fields other than `rerank_sim` in headings
- Change the overall JSON structure

---

## Edge Cases

### No Matching Results

If all headings are filtered out:

```json
{
  "success": false,
  "reason": "No relevant results found after LLM reranking",
  "query": [...],
  "doc_sets_found": [...],
  "results": []
}
```

### Single Query vs Multiple Queries

When scoring with multiple queries:
- Find **common intent** across all queries
- Score based on how well heading serves the **shared intent**
- If queries have **different intents**, score based on **best match**

### Mixed Language Queries

Score headings based on **semantic relevance** regardless of language.

---

## Quality Checklist

Before returning output, verify:

- [ ] All `rerank_sim` values are filled (no `null`)
- [ ] No headings with `rerank_sim < 0.5` remain
- [ ] No results with empty `headings` arrays remain
- [ ] Original JSON structure is preserved
- [ ] Only `rerank_sim` values have been modified