
# Markdown Document LLM Reranker

Analyze and re-rank document retrieval results using pure LLM prompt-based semantic similarity scoring.

---

## Purpose

Improve retrieval quality by:

- Analyzing semantic relevance between query and retrieved headings
- Assigning or reassigning similarity scores (`rerank_sim`) to each heading
- Filtering out irrelevant results based on score threshold
- Preserving the original input structure in output

---

## When to Use

Use this skill when:

1. `md-doc-searcher` returns results that need semantic re-ranking
2. Results contain `rerank_sim` fields that need to be rescored or populated
3. Irrelevant results need to be filtered out from retrieval results

---

## Input Format

The skill receives JSON data with the following structure:

```json
{{
  "success": True,
  "toc_fallback": True,
  "grep_fallback": True,
  "query": [
    "skills plugins",
    "skills plugins setup"
  ],
  "retrieval_scene": "how_to",  // Optional: specified retrieval scene for targeted filtering
  "doc_sets_found": [
    "OpenCode_Docs@latest"
  ],
  "results": [
    {{
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "Plugins",
      "toc_path": "/path/to/OpenCode_Docs@latest/Plugins/docTOC.md",
      "headings": [
        {{
          "level": 2,
          "text": "3. Create a skill",
          "rerank_sim": null,
          "bm25_sim": null
        }},
        {{
          "level": 2,
          "text": "4. Configure skills",
          "rerank_sim": null,
          "bm25_sim": null
        }}
      ],
      "bm25_sim": 4.788130955222923,
      "rerank_sim": null
    }},
    {{
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "Agents",
      "toc_path": "md_docs_base/OpenCode_Docs@latest/Agents/docTOC.md",
      "headings": [
        {{
          "text": "3. Create a Agents",
          "level": 2,
          "rerank_sim": null,
          "bm25_sim": null
        }}
      ],
      "bm25_sim": 1.3782821163340384,
      "rerank_sim": null
    }}
  ],
  "fallback_used": "FALLBACK_1",
  "message": "Search completed"
}}
```

### Retrieval Scene Values (Optional)

If `retrieval_scene` is provided, use its specified filtering strategy:

| Scene | Threshold | Description |
|-------|-----------|-------------|
| `fact_lookup` | 0.60 | Precise matching, prefer accuracy over recall |
| `faithful_reference` | 0.65 | Highest precision, requires high-fidelity原文 |
| `faithful_how_to` | 0.58 | Original text + actionable steps |
| `concept_learning` | 0.55 | Multiple perspectives for rich understanding |
| `how_to` | 0.50 | Multiple valid methods, single source not required |
| `comparison` | 0.53 | Coverage of multiple options/alternatives |
| `exploration` | 0.45 | Lowest threshold, encourage broad associations |

---

## Processing Logic

### Step 0: Retrieval Scene Recognition

**If `retrieval_scene` is provided:**
- Use the specified scene for targeted filtering strategy

**If `retrieval_scene` is NOT provided:**
- Infer the scene from query patterns:

| Query Pattern | Inferred Scene | Threshold |
|--------------|----------------|-----------|
| Questions with "what is", "define", "explain" | `concept_learning` | 0.55 |
| Questions with "how to", "steps", "guide" | `how_to` | 0.50 |
| Questions with "difference", "compare", "vs" | `comparison` | 0.53 |
| Questions asking about specific facts/numbers | `fact_lookup` | 0.60 |
| Questions about original text/quote/reference | `faithful_reference` | 0.65 |
| Questions about implementation with steps | `faithful_how_to` | 0.58 |
| Open-ended questions, broad topics | `exploration` | 0.45 |

### Step 1: Query Intent Analysis

Analyze all queries to understand the core information need:

- Identify common themes across multiple query variations
- Extract key concepts, entities, and actions
- Determine the primary and secondary information goals

### Step 2: Page Title & Heading Semantic Analysis

For each page title and heading in each result:

1. **Extract page context** from `page_title`
2. **Extract heading text** from `headings[].text`
3. **Analyze relevance** to the query intent
4. **Assign similarity score** based on semantic match quality. **Wheterh generic or specific is not a problem**.

### Step 3: Similarity Scoring Criteria

| Score Range | Meaning | Criteria |
|-------------|---------|----------|
| `0.9 - 1.0` | Perfect match | Heading directly answers the query, contains exact key terms |
| `0.7 - 0.89` | Strong match | Heading is highly relevant, contains most key terms |
| `0.5 - 0.69` | Moderate match | Heading is somewhat relevant, partial term overlap |
| `0.3 - 0.49` | Weak match | Heading has minor relevance, tangential connection |
| `0.1 - 0.29` | Poor match | Heading barely relates to query |
| `0.0` | No match | Heading is completely unrelated |

#### Scene-Specific Scoring Guidelines

Adjust your scoring based on the retrieval scene:

| Scene | Scoring Tendency | Retention Principle |
|-------|-----------------|---------------------|
| `fact_lookup` | Conservative, prefer lower scores | Only exact matches score high |
| `faithful_reference` | Most conservative, near-perfect required | Only near-perfect matches retained |
| `faithful_how_to` | Medium-high, focus on step-related content | Step-related content scores higher |
| `concept_learning` | More generous, include explanatory content | Concept explanations score higher |
| `how_to` | Moderate, practical focus | Actionable guides score higher |
| `comparison` | Medium-low, include all option information | Each option's description matters |
| `exploration` | Most generous, include tangential content | Broad associations score higher |

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

**Filter Threshold:** `rerank_sim >= 0.5` (scene-specific, default 0.5)

**Scene-Specific Thresholds:**

| Scene | Threshold | Strategy |
|-------|-----------|----------|
| `fact_lookup` | 0.60 | Strict filtering, only highly relevant |
| `faithful_reference` | 0.65 | Strictest, almost perfect matches only |
| `faithful_how_to` | 0.58 | Strict filtering for step content |
| `concept_learning` | 0.55 | Moderate filtering for explanations |
| `how_to` | 0.50 | Standard filtering |
| `comparison` | 0.53 | Moderate filtering for options |
| `exploration` | 0.45 | Loose filtering for broad coverage |

- **Keep:** PageTitle **or** Headings with `rerank_sim >= threshold`
- **Remove:** PageTitle **and** Headings with `rerank_sim < threshold`

**Just Notice:** If ALL PageTitles & headings in a result have `rerank_sim < threshold`, remove the entire result object from `results` array.

**But Important Outlined Cases:** When the results is empty after removing, please keep the topic of page title or headings related with queries if exists.

### Step 6: Scene-Specific Filtering Strategies

#### High Precision Scenes (0.58-0.65): faithful_reference, fact_lookup, faithful_how_to

- Apply stricter keyword matching requirements
- Keep only highly relevant documents
- Filter out weak/edge matches aggressively
- **faithful_reference**: Keep only core original text, no peripheral content
- **fact_lookup**: Keep only fragments containing exact answers
- **faithful_how_to**: Keep step sections, filter pure concept explanations

#### Balanced Scenes (0.50-0.55): how_to, concept_learning

- Apply moderate filtering
- Keep core relevant content
- **how_to**: Keep step-by-step guides and prerequisite sections
- **concept_learning**: Keep definitions, principles, relationships, and examples

#### Broad Coverage Scenes (0.45-0.53): exploration, comparison

- Apply relaxed filtering
- Keep multi-perspective content
- Allow loosely related content
- **exploration**: Keep all related content, even tangential associations
- **comparison**: Keep descriptions of all options/alternatives

### Step 7: Document Coverage Decision

Based on the retrieval scene, determine how many and which types of documents to retain:

**High Precision Scenes:**
- `faithful_reference`: Keep only 1-2 most relevant sources with exact matches
- `fact_lookup`: Keep only fragments containing precise answers
- `faithful_how_to`: Keep step-by-step sections, prefer single complete guide

**Balanced Scenes:**
- `how_to`: Keep 2-3 different methods if available
- `concept_learning`: Keep 2-3 sources covering different angles

**Broad Coverage Scenes:**
- `exploration`: Keep all potentially related sources
- `comparison`: Keep all option descriptions for comprehensive comparison

---

## Scoring Examples

### Example 1: Faithful Reference Scenario (Threshold: 0.65)

**Query:** "What does the documentation say about authentication flow?"

**Heading:** "Authentication Overview"

**Analysis (Faithful Reference scene):**
- Title mentions authentication but is too generic
- Lacks specific reference to documentation's original text
- No direct quote or specific claim from documentation
- Faithful reference requires precise original text matching

**Score:** `0.28` → Filter (below 0.65 threshold)

---

### Example 2: Faithful How-To Scenario (Threshold: 0.58)

**Query:** "How to configure MCP servers step by step"

**Heading:** "MCP Server Configuration"

**Analysis (Faithful How-To scene):**
- Contains configuration keywords matching query intent
- Title implies step content but doesn't explicitly reference steps
- Faithful how-to requires clear step structure in original text
- Missing explicit "step", "configure", or action verb sequence

**Score:** `0.48` → Filter (below 0.58 threshold)

---

### Example 3: How-To Scenario (Threshold: 0.50)

**Query:** "How to configure MCP servers step by step"

**Heading:** "MCP Server Configuration"

**Analysis (How-To scene):**
- Contains configuration keywords matching query intent
- How-To scene allows more flexibility for practical guides
- Actionable topic even without explicit step structure
- Retained as practical configuration guidance

**Score:** `0.65` → Keep (above 0.50 threshold)

---

### Scenario-Specific Edge Case Comparison

The same heading receives different scores based on scene threshold:

| Heading | faithful_reference (0.65) | faithful_how_to (0.58) | how_to (0.50) |
|---------|---------------------------|------------------------|---------------|
| "Configuration Guide" | 0.25 → Filter | 0.45 → Filter | 0.62 → Keep |
| "Step-by-Step Setup" | 0.30 → Filter | 0.72 → Keep | 0.80 → Keep |
| "API Overview" | 0.22 → Filter | 0.35 → Filter | 0.55 → Keep |

**Key Insight:** Titles with action-oriented keywords score higher in how_to scenes, while faithful_reference requires near-perfect semantic alignment with original documentation text.

---

## Output Format

Return the **exact same JSON structure** with:

1. **`rerank_sim` populated**: Fill in `null` values with calculated scores (0.0 - 1.0)
2. **`headings` filtered**: Remove headings with `rerank_sim < threshold` (scene-specific)
3. **`results` filtered**: Remove results with empty `headings` array after filtering

```json
{{
  "success": true,
  "toc_fallback": true,
  "grep_fallback": true,
  "query": [
    "skills plugins",
    "skills plugins setup"
  ],
  "doc_sets_found": [
    "OpenCode_Docs@latest"
  ],
  "results": [
    {{
      "doc_set": "OpenCode_Docs@latest",
      "page_title": "Plugins",
      "toc_path": "/path/to/OpenCode_Docs@latest/Plugins/docTOC.md",
      "headings": [
        {{
          "level": 2,
          "text": "3. Create a skill",
          "rerank_sim": 0.85,
          "bm25_sim": null
        }},
        {{
          "level": 2,
          "text": "4. Configure skills",
          "rerank_sim": 0.72,
          "bm25_sim": null
        }}
      ],
      "bm25_sim": 4.79,
      "rerank_sim": null
    }}
  ]
}}
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
- Modify any fields other than `rerank_sim`
- Change the overall JSON structure

---

## Edge Cases

### No Matching Results

If all headings are filtered out:

```json
{{
  "success": false,
  "reason": "No relevant results found after LLM reranking",
  "query": [...],
  "doc_sets_found": [...],
  "results": []
}}
```

### Scene Inference When Not Provided

When `retrieval_scene` is missing, infer from query patterns:

**Concept Learning indicators:**
- Query contains: "what is", "define", "explain", "understand", "concept"
- Example: "What is Model Context Protocol?"

**How-To indicators:**
- Query contains: "how to", "steps", "guide", "tutorial", "install", "configure"
- Example: "How to install Claude Code"

**Comparison indicators:**
- Query contains: "difference", "compare", "vs", "versus", "better"
- Example: "Claude Code vs Cursor"

**Fact Lookup indicators:**
- Query asks for: specific value, number, date, version, name
- Example: "What version is Claude Code 3.5"

**Faithful Reference indicators:**
- Query mentions: "original text", "quote", "documentation says"
- Example: "What does the documentation say about MCP?"

**Faithful How-To indicators:**
- Query asks for implementation with specific steps
- Example: "How to configure MCP servers step by step"

**Exploration indicators:**
- Query is open-ended, broad topic
- Example: "What can Claude Code do?"

### Single Query vs Multiple Queries

When scoring with multiple queries:
- Find **common intent** across all queries
- Score based on how well heading serves the **shared intent**
- If queries have **different intents**, score based on **best match**

**Scene-aware scoring for multiple queries:**
- If queries suggest different scenes, use the **stricter scene** (higher threshold)
- Example: "Claude Code features" (exploration) + "Claude Code installation" (how_to) → use how_to threshold (0.50)

### Mixed Language Queries

Score headings based on **semantic relevance** regardless of language.

---

## Quality Checklist

Before returning output, verify:

- [ ] All `rerank_sim` values are filled (no `null`)
- [ ] No headings with `rerank_sim < threshold` remain
- [ ] No results with empty `headings` arrays remain
- [ ] Original JSON structure is preserved
- [ ] Only `rerank_sim` values have been modified
- [ ] Scene-specific threshold was applied correctly


# User Input
## Retrieval Scenario
{RETRIEVAL_SCENE}

## The Raw Results for Rerank & Filt:
```json
{SEARCHER_RETRIVAL_RESULTS}
```

# Your Task
Please rerank and filter the results.