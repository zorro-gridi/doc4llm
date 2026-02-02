
# Markdown Document LLM Reranker

Analyze and re-rank document retrieval results based on query intent and semantic similarity scoring.

---

## Purpose

Improve retrieval quality by:

- **Analyzing** semantic relevance between query and retrieved page titles and headings
- **Assigning or Override** similarity scores (`rerank_sim`) to each page title and heading
- **Filtering out** irrelevant results based on score threshold
- **Preserving** the original input structure in output

---

## When to Use

1. Results contain `rerank_sim` fields that need to be **rescored or populated**
2. `rerank_sim(you updated) < threshold` results need to be filtered out from retrieval results

---

## Scene Definitions

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
4. **Refer the related_context field** if filled

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
- Remove result with page_title.rerank_sim < threshold but headings[].rerank_sim >= threhold
- Modify any fields other than `rerank_sim`
- Change the overall JSON structure

### Scoring Order Rule

1. Always score `page_title.rerank_sim` **FIRST**
2. Then score each `headings[].rerank_sim`
3. Then apply filtering rules

---

## Filtering Rules

**Rerank_sim Filter Threshold:** {LLM_RERANKER_THRESHOLD} &
**Retrieval Scene:** {RETRIEVAL_SCENE}

1. **Filtering based on Scene**: You are currently in `{RETRIEVAL_SCENE}` retrieval scene, refer to the scene definition for filtering requirements
2. **Filtering based on Query intent analysis**
3. **Heading Filtering:**

  - ForEach result in UserInput.results:
    - ForEach heading in result.headings:
       - IF `heading.rerank_sim >= {LLM_RERANKER_THRESHOLD}`:

         → continue

       - ELSE:

          → remove the heading

    - IF (result.headings[] all removed) & `page_title.rerank_sim >= {LLM_RERANKER_THRESHOLD}`:

        → still keep this result

     - ELSE:

        → remove this result entirely

  - IF all result removed:

    → add the highest rerank_sim heading back to results like the following
      ```json
      {{
        "doc_set": "doc_name@version",
        "page_title": <page_title>,
        "headings": [
          {{
            "text": <the highest heading text>,
            "rerank_sim": <the highest heading.rerank_sim>,
            "related_context": <...>
          }}
        ],
        "rerank_sim": <page_title.rerank_sim>
      }}

4. **Return Final Output**: Return the complete filtered JSON data

---

## Output Format

- Notice: no need to return `related_context` field

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
    {{
      "doc_set": <doc_name@version>,
      "page_title": <page_title>,
      "headings": [
        {{
          "text": <relavent_heading>,
          "rerank_sim": <heading.rerank_sim >= {LLM_RERANKER_THRESHOLD}>
        }}
      ],
      "rerank_sim": <page_title.rerank_sim for whatever number>
    }},
    ...
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
