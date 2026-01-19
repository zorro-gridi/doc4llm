# Progressive Fallback Strategy (Detailed Reference)

This document provides detailed information about the progressive fallback levels used in md-doc-searcher.

## Overview

The progressive fallback strategy ensures comprehensive document discovery by automatically escalating search sophistication when simpler methods fail.

## Level 1: Semantic Title Matching (Default)

**Purpose:** Fast semantic matching using LLM understanding

**How it works:**
- Uses LLM semantic understanding to match query concepts to document titles
- Leverages synonym recognition, domain knowledge, and context understanding
- Fast operation: O(k) where k = number of matches

**Quality threshold:** `max_similarity >= 0.7` to return results

**When triggered:** Always (starting point)

**Example:**
```
Query: "how to configure"
Matches: "Settings", "Configuration", "Setup", "Preferences"
```

## Level 2: TOC Content Grep (Fallback)

**Purpose:** Search within TOC file contents when title matching fails

**Trigger:** Level 1 returns 0 results OR `max_similarity < 0.7` (low quality)

**How to use:**

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

# First extract keywords
keywords = SearchHelpers.extract_keywords("how to configure hooks for deployment")
# → ['configure', 'hooks', 'deployment']

# Then build grep command
SearchHelpers.build_level2_grep_command(
    keywords=["configure", "hooks", "deployment"],
    doc_set="Claude_Code_Docs:latest"
)
# → "grep -r -iE '(configure|hooks|deployment)' md_docs/Claude_Code_Docs:latest/*/docTOC.md"
```

**Execute via Bash tool:**
```bash
grep -r -iE '(configure|hooks|deployment)' md_docs/Claude_Code_Docs:latest/*/docTOC.md
```

**Benefits:**
- Finds content within sections that don't match title exactly
- Captures documents where relevant content is in subsections
- Balanced performance: O(1) operation

## Level 3: Cross-Set + Content Search (Last Resort)

Level 3 has two sub-levels:

### Level 3.1: Cross-Set TOC Search (with Relevance Constraints)

**Purpose:** Search across multiple documentation sets when single-set search fails

**Trigger:** Level 2 returns 0 results

**Step 1: Extract domain keywords from user query** (LLM semantic analysis)
```python
# Example: User queries "Claude Code skills design philosophy"
# Domain keywords: Claude, Code
# Topic keywords: skills, design, philosophy
```

**Step 2: Filter documentation sets by domain relevance**
```python
# Use helper to build filter pattern
SearchHelpers.build_doc_set_filter_pattern(["Claude", "Code"])
# → "md_docs/*Claude* md_docs/*Code*"

# For "Claude Code skills", only search:
# - Claude_Code_Docs:latest
# NOT: Python_Docs, React_Docs, etc.
```

**Step 3: Search TOC files in filtered sets**
```bash
# Cross-set TOC search WITH domain filter
grep -r -i "keyword" md_docs/*Claude*/*/docTOC.md md_docs/*Code*/*/docTOC.md
```

**Why domain filtering matters:**
Searching "best practices" across ALL doc sets could return Python, React, or other framework-specific practices that are irrelevant to the user's actual query context.

### Level 3.2: docContent.md Context Search (with Traceback)

**Purpose:** Search within document contents when TOC search fails

**Trigger:** Level 3.1 returns 0 results

**CRITICAL CONSTRAINTS:**
- ❌ **NEVER** use `Read` tool to load entire docContent.md files
- ✅ Only use `grep` with context to extract minimal information
- ✅ Return docTOC.md paths for subsequent use by md-doc-reader

**Search with context traceback:**
```python
# Use helper to build command
SearchHelpers.build_level3_content_grep_command(
    keywords=["design philosophy"],
    doc_sets=["Claude_Code_Docs:latest"],
    context_lines=10
)
# → "grep -r -i -B 10 'design philosophy' md_docs/Claude_Code_Docs:latest/*/docContent.md"
```

**Execute via Bash tool:**
```bash
grep -r -i -B 10 "design philosophy" md_docs/*Claude*/*/docContent.md
```

**Parse results to extract:**
1. **Documentation set name** - Extract from file path
2. **Document title** - Extract from docContent.md (first 5 lines, look for `#` headings)
3. **Match context** - The 10 lines before the match showing relevant section

**Helper for title extraction:**
```python
SearchHelpers.build_title_extraction_command(
    "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md",
    max_lines=5
)
# → "head -5 md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"
```

**Return format for Level 3.2:**
```markdown
Found N relevant document(s) via Level 3.2 content search:

1. **Document Title** (Doc_Set:Version)
   - Relevance: Content contains "keyword" in section context
   - Context: [Brief excerpt from grep -B 10 output]
   - TOC Path: `md_docs/<doc_set>/<PageTitle>/docTOC.md`

**Note:** Use `/md-doc-reader "Document Title"` to view full TOC and structure.
```

## Progressive Fallback Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    SEARCH REQUEST                            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  Level 1: Title Semantic Match │
              │  - LLM semantic understanding  │
              │  - Fast: O(k) where k = matches│
              │  - Threshold: max_sim >= 0.7   │
              └───────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
        [Results > 0 AND                 [Results = 0 OR
         max_sim >= 0.7]                  max_sim < 0.7]
              │                               │
              ▼                               ▼
        To Coverage Check            ┌───────────────────────────────┐
                                    │  Level 2: TOC Grep Fallback   │
                                    │  - grep -r across TOC files   │
                                    │  - Balanced: O(1) operation   │
                                    └───────────────────────────────┘
                                              │
                                    ┌─────────┴─────────┐
                                    │                   │
                              [Results > 0]      [Results = 0]
                                    │                   │
                                    ▼                   ▼
                          To Coverage Check    ┌───────────────────────────────┐
                                                  │  Level 3.1: Cross-Set TOC   │
                                                  │  - Filter by domain        │
                                                  │  - grep -r across filtered │
                                                  │    doc sets                │
                                                  └───────────────────────────────┘
                                                            │
                                                  ┌─────────┴─────────┐
                                                  │                   │
                                            [Results > 0]      [Results = 0]
                                                  │                   │
                                                  ▼                   ▼
                                        To Coverage Check    ┌───────────────────────────────┐
                                                                      │  Level 3.2: Content Search │
                                                                      │  - grep -B 10 for context │
                                                                      │  - Extract title from 5   │
                                                                      │    lines (retry: 20)      │
                                                                      │  - Return TOC paths only  │
                                                                      └───────────────────────────────┘
                                                                                │
                                                                                ▼
                                                                      ┌─────────────────────────┐
                                                                      │   Coverage Completeness │
                                                                      │   Verification Check    │
                                                                      │   - Assess query type   │
                                                                      │   - Check result diversity
                                                                      │   - Identify gaps      │
                                                                      └─────────────────────────┘
                                                                                │
                                                              ┌─────────────┴─────────────┐
                                                              │                           │
                                                        [Coverage Complete]          [Gaps Found]
                                                        - Generic queries handled   - Expand scope
                                                        - All aspects covered      - Search other sets
                                                              │                           │
                                                              └─────────────┬─────────────┘
                                                                            ▼
                                                              ┌─────────────────────────┐
                                                              │  Intent-Based Filtering  │
                                                              │  (Step 6 - NEW)         │
                                                              │  - Analyze query intent  │
                                                              │  - Score document relevance
                                                              │  - Filter by thresholds  │
                                                              │  - Improve precision     │
                                                              └─────────────────────────┘
                                                                            │
                                                              ┌─────────────┴─────────────┐
                                                              │                           │
                                                        [High Precision Results]    [Medium + Context]
                                                        - Score ≥ 0.8              - Score 0.5-0.79
                                                        - Direct intent match      - Related content
                                                              │                           │
                                                              └─────────────┬─────────────┘
                                                                            ▼
                                                              ┌─────────────────────────┐
                                                              │    Return Filtered       │
                                                              │    Results with          │
                                                              │    - Relevance scores    │
                                                              │    - Filtering rationale │
                                                              │    - Coverage notes      │
                                                              │    - TOC Paths           │
                                                              └─────────────────────────┘
```

## Decision Criteria Summary

| Level | Trigger | Search Scope | Output |
|-------|---------|--------------|--------|
| **1** | Always (start) | Single set, titles only | Document titles with TOC paths |
| **2** | Level 1 fails OR low quality | Single set, TOC contents | Document titles with TOC paths |
| **3.1** | Level 2 fails | Multiple filtered sets, TOC | Document titles with TOC paths |
| **3.2** | Level 3.1 fails | Multiple filtered sets, content | Document titles with context + TOC paths |
