---
name: md-doc-query-optimizer
description: "Pure LLM prompt-based skill. Optimize and rewrite user queries for better document retrieval. Supports query decomposition, expansion, synonym replacement, and multi-query generation. Returns optimized queries for document search."
disable-model-invocation: true
---

# Markdown Document Query Optimizer

Optimize user queries to improve document retrieval quality in the doc4llm system through pure prompt-based analysis and transformation.

---

## Purpose

Improve search relevance by:

- Detecting target documentation sets from local knowledge base
- Decomposing complex queries into simpler sub-queries
- Expanding queries with synonyms and related terms
- Generating multiple query variations for broader coverage
- Translating non-English queries to documentation language

---

## When to Use

Use this skill when:

1. User query uses **"use contextZ"** or **"use contextz"** keywords
2. `doc-retriever` subagent is invoked

---

## Five-Phase Optimization Protocol

---

### Phase 0: Doc-Set Detection

Before query analysis, identify target documentation sets.

**Knowledge Base Configuration**

- Read `.claude/knowledge_base.json` → get `base_dir`
- List all first-level subdirectories under `<base_dir>/`
- Subdirectory naming pattern: `<doc_name>@<doc_version>`

Example:
```

code_claude_com@latest
anthropic_api@v1

````

**Matching Strategy**

1. **Direct Match**: Query contains doc-set identifier
2. **Keyword Match**: Query keywords match doc-set naming conventions
3. **Domain Inference**: Technical terms suggest documentation domain
4. **No Match**: Return empty list `[]` → Suggest online search

**Output**

```json
"doc_set": ["code_claude_com@latest"]
````

or

```json
"doc_set": []
```

---

### Phase 1: Strategy Selection

| Analysis Result      | Primary Strategy       | Secondary Actions            |
| -------------------- | ---------------------- | ---------------------------- |
| Has conjunctions     | Decomposition          | Expand each sub-query        |
| Generic / ambiguous  | Expansion              | Generate multiple variations |
| Chinese query        | Translation            | Expand translated terms      |
| Mixed language       | Translation + preserve | Keep technical terms         |
| Well-formed specific | None                   | Minor expansion only         |

---

## Strategy Rules

### Decomposition Rules

When detecting conjunctions:

* Create a focused query for each concept
* Generate variations for each
* Include combined queries
* Rank by specificity

---

### Expansion Rules

**Chinese**

* 配置 + noun → `{noun} configuration`, `{noun} setup`, `{noun} settings`
* 部署 → deployment, deploy, production setup
* 安全 → security, authentication, authorization

**English**

* how to {verb} → `{verb} guide`, `{verb} tutorial`, `{verb} configuration`
* {noun} related → `{noun}`, `{noun} reference`, `{noun} guide`

---

### Translation Rules

* Translate non-technical words
* Preserve technical terms (API, hooks, middleware)
* Handle mixed language carefully

---

### Phase 2: Query Generation

Generate optimized queries following:

1. Prioritize **direct translations** for Chinese queries
2. Add **domain-specific variations**
3. Include documentation modifiers:
   * reference, guide, tutorial, setup
4. Preserve **core technical terms exactly**
5. Rank by expected relevance (most direct first)

### Phase 3: Intent Recognition

For each user query, analyze:

1. **Complexity Check**

   * Look for conjunctions: 和、以及、与、还有 / and, also, along with

2. **Ambiguity Check**

   * Detect generic terms: skills, hooks, features, setup

3. **Language Detection**

   * Chinese / English / Mixed

4. **Technical Term Extraction**

5. **Semantic Extraction**

### Phase 4: Domain Nouns (实体名词 ONLY)

**Core Extraction Rule**

> *Return ONLY the noun that represents the true entity being **created**, **configured**, **built**, or **operated on** in the query. This is the **target object** of the action, NOT the tool/platform used to perform the action.*

**Decision Tree**

```
┌─────────────────────────────────────────────────────────────────┐
│ Q1: Is this noun the TARGET of the action (created, configured, built)? ──→ YES → INCLUDE
│ Q2: Is this noun the TOOL/PLATFORM used to perform the action?          ──→ YES → EXCLUDE
│ Q3: Is this noun the THEME/TOPIC being discussed/analyzed?              ──→ YES → INCLUDE
└─────────────────────────────────────────────────────────────────┘
```

Examples:
- "opencode **如何创建 skills**" → skills is TARGET → `["skills"]`
- "opencode **的设计理念**" → opencode is THEME → `["opencode"]`
- "用 Python **处理** CSV 文件" → CSV is TARGET → `["CSV"]`

**Include:**

* **Target Objects**: hooks, skills, middleware, API, components being created/configured
* **Product Names**: Claude Code, OpenCode (when they are the topic/theme)
* **Technical Entities**: authentication, database, configuration files

**Exclude:**

* **Implementation Tools/Platforms**: opencode, python, docker, git (how it's done)
* **Abstract Process Nouns**: creation, deployment, configuration (as a process)

Demo Extraction
| query input | returned entities | Rationale |
| :--- | :--- | :--- |
| opencode 如何创建 skills | skills | skills is the TARGET being created |
| opencode 的设计理念 | opencode | opencode is the THEME being discussed |
| opencode 和 Claude code 的 skills 对比分析 | skills | skills is the TARGET being compared |
| opencode 和 claude code 对比分析 | opencode, Claude code | both are THEMEs being compared |

### Phase 5: Predicate Verbs

> **⚠️ CRITICAL: This phase extracts from OPTIMIZED queries, NOT original query.**

| Aspect | Phase 4 (Domain Nouns) | Phase 5 (Predicate Verbs) |
|--------|------------------------|---------------------------|
| **Source** | Original query | Optimized queries |
| **Extraction** | Direct extraction | Derive from query variations |
| **Purpose** | Identify target entities | Capture action diversity |

**Core Extraction Rule**

> *Derive ALL action verbs from the optimized query set generated in Phase 2. Each optimized query contains a different action variant (e.g., "create", "setup", "configure"). Collect these verbs to capture the full range of possible actions.*

**Common Mistakes Table**

| ❌ Wrong | ✅ Correct | Reason |
|----------|------------|--------|
| Extract from "如何**创建**" → `["create"]` | Derive from optimized queries → `["create", "setup", "configure"]` | Phase 5 rule violation |
| Extract single verb | Extract multiple verbs | Must capture action diversity |
| From original query | From optimized queries | Protocol requirement |

**Complete Workflow Example**

**Original Query:** `"opencode 如何创建 skills"`

**Phase 2 Output (Optimized Queries):**

| Rank | Query | Key Verb |
|------|-------|----------|
| 1 | "opencode **skills creation**" | creation → create |
| 2 | "opencode skills **setup** guide" | setup |
| 3 | "opencode how to **create** skills tutorial" | create |
| 4 | "opencode skills **configuration**" | configure |

**Phase 5 Output:**
```json
"predicate_verbs": ["create", "setup", "configure", "creation", "creating", "configuration", "configuring", "setting up"]
```

> **Note:** `predicate_verbs` should include multiple forms:
> - **Verb base forms**: `create`, `setup`, `configure`
> - **Gerund forms**: `creating`, `setting up`, `configuring`
> - **Noun forms**: `creation`, `configuration`, `setup`
---

### Optimized Query Count Logic

The number of optimized queries returned is dynamically determined based on the number of extracted **Domain Nouns**.

Use the following branching logic:

```text
IF domain_nouns_count == 1:
    return 3–5 optimized queries
ELSE IF domain_nouns_count == 2:
    return 6–10 optimized queries
ELSE IF domain_nouns_count >= 3:
    base = 6
    extra_nouns = domain_nouns_count - 2
    return base + (extra_nouns * 3~5)
```

**Explanation**

* 1 Domain Noun → return **3–5** optimized queries
* 2 Domain Nouns → return **6–10** optimized queries
* Each additional Domain Noun beyond 2 increases the result count by **3–5**

This ensures:

* Lightweight output for simple queries
* Broad coverage for complex, multi-entity queries
* Query volume scales with semantic complexity

---

## Integration Protocol
* If `doc_set` empty → Suggest online search
* If not empty → Call `md-doc-searcher`

---

## Output Format (JSON)

```json
{
  "query_analysis": {
    "original": "{original_query}",
    "language": "{detected_language}",
    "complexity": "{low|medium|high}",
    "ambiguity": "{low|medium|high}",
    "strategies": ["translation","expansion"],
    "doc_set": ["code_claude_com@latest"],
    "domain_nouns": ["skills"],
    "predicate_verbs": ["create", "setup", "configure", "creation", "creating", "configuration", "configuring", "setting up"]
  },
  "optimized_queries": [
    {
      "rank": 1,
      "query": "opencode skills creation guide",
      "strategy": "expansion",
      "rationale": "Direct translation with documentation modifier"
    },
    {
      "rank": 2,
      "query": "opencode skills setup tutorial",
      "strategy": "expansion",
      "rationale": "Alternative action verb for broader coverage"
    },
    {
      "rank": 3,
      "query": "how to create skills in opencode",
      "strategy": "translation",
      "rationale": "Question format with explicit action"
    }
  ],
  "search_recommendation": {
    "online_suggested": false,
    "reason": ""
  }
}
```