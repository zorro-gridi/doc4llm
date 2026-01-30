
# Markdown Document LLM Reranker

Analyze and re-rank document retrieval results based on query intent and semantic similarity scoring.

---

## Purpose

Improve retrieval quality by:

- Analyzing semantic relevance between query and retrieved page titles and headings
- Assigning or reassigning similarity scores (`rerank_sim`) to each page title and heading
- Filtering out irrelevant results based on score threshold
- Preserving the original input structure in output

---

## When to Use

Use this skill when:

1. Results contain `rerank_sim` fields that need to be rescored or populated
2. `rerank_sim < threshold` results element need to be filtered out from retrieval results

---

## Scene Definitions

Refer to `query_router_template.md` for detailed scene descriptions:

| Scene | Description |
|-------|-------------|
| `fact_lookup` | Precise fact retrieval - single specific facts (version, value, boolean) |
| `faithful_reference` | High-fidelity original text - official documentation explanations |
| `faithful_how_to` | Original text + comprehensive procedures - project implementation |
| `concept_learning` | Systematic concept understanding - definitions, principles, relationships |
| `how_to` | Step-by-step procedures - learning task execution |
| `comparison` | Multi-option comparison - evaluating alternatives |
| `exploration` | Deep research with broad context - multi-angle analysis |

---

## Scoring Criteria

Base on **Page title or Headings match**

| Score Range | Meaning | Criteria |
|-------------|---------|----------|
| 0.9 - 1.0 | Perfect match | Directly answers the query, contains exact key terms |
| 0.7 - 0.89 | Strong match | highly relevant, contains most key terms |
| 0.5 - 0.69 | Moderate match | Somewhat relevant, partial term overlap |
| 0.3 - 0.49 | Weak match | Minor relevance, tangential connection |
| 0.1 - 0.29 | Poor match | Barely relates to query |
| 0.0 | No match | Page title or heading is completely unrelated |

### High or Strong Score Indicators

- Page title or heading contains exact one or many query keywords
- Page title or heading is exactly talking about the query topic

### Moderate Score Indicators

- Page title or heading not cover the keyword of query, but matches query intent

### Low Score Indicators

- Page title or heading covers unrelated topics
- Page title or heading  is too specific to a different use case
- No semantic connection to query concepts

---

## Scoring Guidelines

### Intent-Aware & Scene-Aware Scoring Rule

When filtering results, you MUST combine:

1. **Retrieval Scene requirements**
2. **User Query Intent analysis**
3. **Document coverage balance**

❗ **Do NOT rely only on literal semantic similarity scores.**
You must ensure the final document list:

* Matches the **core intent** of the query
* Fits the **retrieval scene expectations**
* Provides **sufficient but not redundant coverage**

#### Practical Interpretation

Before filtering, always answer internally:

* What does the user *really want* in this scene?
* Is this result helps for specific retieval scene. For example:

  * Explain a concept?
  * Provide exact reference?
  * Teach how to implement?
  * Compare options?
  * Explore a topic broadly?

Then apply filtering with these principles:

| Principle            | Requirement                                                           |
| -------------------- | --------------------------------------------------------------------- |
| **Scene Fit**        | Results must satisfy the purpose of the current `{RETRIEVAL_SCENE}`   |
| **Intent Match**     | Results must serve the user’s *task intent*, not just keyword overlap |
| **Coverage Balance** | Final list must be:                                                   |

* ❌ Not redundant (avoid multiple near-duplicate sections)
* ❌ Not fragmented (avoid missing core concepts/steps)
* ✅ Sufficiently complete for the scene |


### Single Query vs Multiple Queries

When scoring with multiple queries:
- Find **common intent** across all queries
- Score based on how well heading serves the **shared intent**
- If queries have **different intents**, score based on **best match**

### Mixed Language Queries

Score headings based on **semantic relevance** regardless of language.

### Do:

- Consider **all queries** in the array when scoring (query variations indicate intent)
- Use **related context** as additional message for scoring
- Assign **aggressive scores** when uncertain (prefer 0.65-0.70 over 0.60)
- **Filter conservative** to prevent info missing (better to keep the borderline cases)

### Don't:

- Score based solely on keyword presence
- Remove results of page_title with a empty headings
- Modify any fields other than `rerank_sim`
- Change the overall JSON structure

### Scoring Order Rule

1. Always score `page_title.rerank_sim` **FIRST**
2. Then score each `headings[].rerank_sim`
3. Then apply filtering rules

---

## Pre Definition
To avoid misunderstanding, we make the commom ground definition below:

- page title with headings = [], means keep whole page headings
- page title with headings != [], means keep page with specific headings

You can't remove the page title with headings = [] result.

---

## Filtering Rules

**Rerank_sim Filter Threshold:** {LLM_RERANKER_THRESHOLD} &
**Retrieval Scene:** {RETRIEVAL_SCENE}

1. **Filtering based on Scene**: You are currently in `{RETRIEVAL_SCENE}` retrieval scene, refer to the scene definition for filtering requirements
2. **Filtering based on Query intent analysis**
3. **What is Preserved / Filtered:**

  - If `page_title.rerank_sim >= 0.7`, which means **OVER strong match level**

    → page_title preserved **AND** set corresponding headings = []

  - ELSE

    → filter headings where `heading.rerank_sim >= {LLM_RERANKER_THRESHOLD}`

    → if no headings remain

    → remove this result entirely

4. **Return Final Output**: Return the complete filtered JSON data

---

## Output Format

Return the **exact same JSON structure** with:

1. `rerank_sim` populated: Fill in `null` values with calculated scores (0.0 - 1.0)
2. `page_title`preserved: Keep page_title with `rerank_sim >= {LLM_RERANKER_THRESHOLD}`
3. `headings` filtered: Remove headings with `rerank_sim < {LLM_RERANKER_THRESHOLD}`
4. `results` preserved: Keep results even if headings array is empty

```json
{{
  "query": [
    query_1,
    query_2
  ],
  "doc_sets_found": [
    doc_name@version
  ],
  "results": [
    // case 1.  When `page_title.rerank_sim >= {LLM_RERANKER_THRESHOLD}`, headings MUST set be [].
    {{
      "doc_set": doc_name@version,
      "page_title": relavent_page_title,
      "headings": [],
      "rerank_sim": page_title.rerank_sim >= {LLM_RERANKER_THRESHOLD}
    }},
    // case 2. When `heading.rerank_sim >= {LLM_RERANKER_THRESHOLD}`, remained
    {{
      "doc_set": doc_name@version,
      "page_title": other_page_title,
      "headings": [
        {{
          "text": relavent_heading,
          "rerank_sim": heading.rerank_sim >= {LLM_RERANKER_THRESHOLD}
        }}
      ],
      "rerank_sim": page_title.rerank_sim for whatever number
    }}
  ]
}}
```
---

## Edge Cases

### No Matching Page Title or Headings in Results

If all page_title **and** headings are filtered out, keep the result with empty headings:

```json
{{
  "query": [...],
  "doc_sets_found": [...],
  "results": [
    {{
      "page_title": "",
      "headings": []
    }}
  ]
}}
```
---

# User Input

## Retrieval Scene
{RETRIEVAL_SCENE}

## Filter Threshold
{LLM_RERANKER_THRESHOLD}

## The Raw Results for Rerank & Filter:
```json
{SEARCHER_RETRIVAL_RESULTS}
```

# Your Task

Please rerank and filter the results.
