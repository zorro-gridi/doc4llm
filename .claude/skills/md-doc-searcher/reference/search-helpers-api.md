# SearchHelpers API Reference

This document provides complete reference documentation for the `SearchHelpers` class in `doc4llm.tool.md_doc_retrieval`.

## Overview

`SearchHelpers` provides utility functions for common operations in document search, handling repetitive formatting and construction tasks. Core semantic understanding (intent analysis, concept matching, context reasoning) remains with the LLM.

## Import

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers
```

## API Reference

### Path Construction

#### `build_toc_glob_pattern(doc_set)`

Builds a glob pattern for finding all TOC files in a documentation set.

**Parameters:**
- `doc_set` (str): Documentation set name (e.g., "Claude_Code_Docs:latest")

**Returns:**
- `str`: Glob pattern (e.g., "md_docs/Claude_Code_Docs:latest/*/docTOC.md")

**Example:**
```python
pattern = SearchHelpers.build_toc_glob_pattern("Claude_Code_Docs:latest")
# → "md_docs/Claude_Code_Docs:latest/*/docTOC.md"
```

---

#### `build_toc_path(doc_set, title)`

Builds the path to a specific document's TOC file.

**Parameters:**
- `doc_set` (str): Documentation set name
- `title` (str): Document title

**Returns:**
- `str`: Path to TOC file (e.g., "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md")

**Example:**
```python
path = SearchHelpers.build_toc_path("Claude_Code_Docs:latest", "Agent Skills")
# → "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md"
```

---

#### `build_content_path(doc_set, title)`

Builds the path to a specific document's content file.

**Parameters:**
- `doc_set` (str): Documentation set name
- `title` (str): Document title

**Returns:**
- `str`: Path to content file (e.g., "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md")

**Example:**
```python
path = SearchHelpers.build_content_path("Claude_Code_Docs:latest", "Agent Skills")
# → "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"
```

---

### Command Construction

#### `build_level2_grep_command(keywords, doc_set)`

Builds a grep command for Level 2 fallback (TOC content search).

**Parameters:**
- `keywords` (list[str]): List of keywords to search for
- `doc_set` (str): Documentation set name

**Returns:**
- `str`: Grep command string

**Example:**
```python
cmd = SearchHelpers.build_level2_grep_command(
    keywords=["configure", "hooks", "deployment"],
    doc_set="Claude_Code_Docs:latest"
)
# → "grep -r -iE '(configure|hooks|deployment)' md_docs/Claude_Code_Docs:latest/*/docTOC.md"
```

---

#### `build_level3_content_grep_command(keywords, doc_sets, context_lines=10)`

Builds a grep command for Level 3.2 fallback (content search with context).

**Parameters:**
- `keywords` (list[str]): List of keywords to search for
- `doc_sets` (list[str]): List of documentation set names
- `context_lines` (int, optional): Number of context lines before match. Default: 10

**Returns:**
- `str`: Grep command string with context

**Example:**
```python
cmd = SearchHelpers.build_level3_content_grep_command(
    keywords=["design philosophy"],
    doc_sets=["Claude_Code_Docs:latest"],
    context_lines=10
)
# → "grep -r -i -B 10 'design philosophy' md_docs/Claude_Code_Docs:latest/*/docContent.md"
```

---

#### `build_title_extraction_command(path, max_lines=5)`

Builds a command to extract the document title from content file.

**Parameters:**
- `path` (str): Path to docContent.md file
- `max_lines` (int, optional): Maximum number of lines to read. Default: 5

**Returns:**
- `str`: Head command string

**Example:**
```python
cmd = SearchHelpers.build_title_extraction_command(
    "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md",
    max_lines=5
)
# → "head -5 md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"
```

---

### Extraction Helpers

#### `extract_original_url(toc_content)`

Extracts the original URL from TOC content.

**Parameters:**
- `toc_content` (str): Raw TOC markdown content

**Returns:**
- `str`: Original URL or empty string if not found

**Example:**
```python
url = SearchHelpers.extract_original_url(toc_content)
# → "https://code.claude.com/docs/en/agent-skills"
```

---

#### `extract_keywords(query)`

Performs basic keyword extraction from a query.

**Parameters:**
- `query` (str): User query string

**Returns:**
- `list[str]`: List of extracted keywords

**Example:**
```python
keywords = SearchHelpers.extract_keywords("how to configure hooks for deployment")
# → ['configure', 'hooks', 'deployment']
```

---

### Formatting Helpers

#### `format_sources_section(titles_and_urls)`

Formats a sources section for output.

**Parameters:**
- `titles_and_urls` (list[tuple]): List of (title, url, path) tuples

**Returns:**
- `str`: Formatted sources section in markdown

**Example:**
```python
sources = SearchHelpers.format_sources_section([
    ("Agent Skills", "https://code.claude.com/docs/en/agent-skills", "md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md")
])
# Returns:
# """
#
# ---
#
# ### 文档来源
#
# 1. **Agent Skills**
#    - 原文链接: https://code.claude.com/docs/en/agent-skills
#    - TOC 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docTOC.md`
# """
```

---

#### `format_coverage_section(covered, partial, not_covered, suggestion)`

Formats a coverage section for output.

**Parameters:**
- `covered` (list[str]): List of covered aspects
- `partial` (list[str]): List of partially covered aspects
- `not_covered` (list[str]): List of not covered aspects
- `suggestion` (str, optional): Suggestion for further search

**Returns:**
- `str`: Formatted coverage section in markdown

**Example:**
```python
coverage = SearchHelpers.format_coverage_section(
    covered=["Configuration", "Setup"],
    partial=["Advanced patterns"],
    not_covered=["Performance"],
    suggestion="Search 'performance' for optimization tips"
)
# Returns:
# """
# **Coverage:**
# - ✅ Covered: Configuration, Setup
# - ⚠️  Partially covered: Advanced patterns
# - ❌ Not covered: Performance
# - 💡 Suggestion: Search 'performance' for optimization tips
# """
```

---

### Documentation Set Helpers

#### `get_list_command(base_dir="md_docs")`

Gets the command to list all documentation sets.

**Parameters:**
- `base_dir` (str, optional): Base directory path. Default: "md_docs"

**Returns:**
- `str`: Command to list documentation sets

**Example:**
```python
cmd = SearchHelpers.get_list_command()
# → "ls -1 md_docs/"
```

---

#### `build_doc_set_filter_pattern(intent_keywords)`

Builds a filter pattern for documentation sets based on intent keywords.

**Parameters:**
- `intent_keywords` (list[str]): List of keywords for filtering

**Returns:**
- `str`: Filter pattern for glob/find commands

**Example:**
```python
pattern = SearchHelpers.build_doc_set_filter_pattern(["Claude", "Code"])
# → "md_docs/*Claude* md_docs/*Code*"
```

---

### Intent Analysis and Filtering Helpers (Step 6)

#### `analyze_query_intent(original_query)`

Analyzes the original user query to determine intent classification for filtering.

**Parameters:**
- `original_query` (str): The original user query (not optimized queries)

**Returns:**
- `dict`: Intent analysis result with keys:
  - `primary_intent` (str): LEARN, CONFIGURE, TROUBLESHOOT, REFERENCE, COMPARE
  - `scope` (str): SPECIFIC, GENERAL, CONTEXTUAL
  - `depth` (str): OVERVIEW, DETAILED, PRACTICAL
  - `specificity_keywords` (list[str]): Key terms that indicate specific focus

**Example:**
```python
intent = SearchHelpers.analyze_query_intent("如何配置Claude Code的hooks用于自动化测试")
# Returns:
# {
#   "primary_intent": "CONFIGURE",
#   "scope": "SPECIFIC", 
#   "depth": "PRACTICAL",
#   "specificity_keywords": ["hooks", "自动化测试", "配置"]
# }
```

---

#### `calculate_relevance_score(doc_title, doc_context, query_intent)`

Calculates relevance score for a document based on query intent analysis.

**Parameters:**
- `doc_title` (str): Document title
- `doc_context` (str, optional): Additional context from TOC or content
- `query_intent` (dict): Intent analysis result from `analyze_query_intent()`

**Returns:**
- `dict`: Relevance analysis with keys:
  - `score` (float): Overall relevance score (0.0-1.0)
  - `intent_match` (float): How well document serves the intent (0.0-1.0)
  - `scope_alignment` (float): Scope alignment score (0.0-1.0)
  - `depth_appropriateness` (float): Depth appropriateness score (0.0-1.0)
  - `specificity_match` (float): Specificity alignment score (0.0-1.0)
  - `rationale` (str): Brief explanation of the scoring

**Example:**
```python
relevance = SearchHelpers.calculate_relevance_score(
    doc_title="Hooks reference",
    doc_context="Configuration options and setup guide for hooks",
    query_intent={"primary_intent": "CONFIGURE", "scope": "SPECIFIC", "depth": "PRACTICAL"}
)
# Returns:
# {
#   "score": 0.9,
#   "intent_match": 0.95,
#   "scope_alignment": 0.9,
#   "depth_appropriateness": 0.85,
#   "specificity_match": 0.9,
#   "rationale": "Direct configuration guide for hooks with practical setup information"
# }
```

---

#### `format_filtered_results(high_relevance, medium_relevance, filtered_out)`

Formats the filtered results with relevance categories.

**Parameters:**
- `high_relevance` (list[dict]): High relevance documents (≥0.8) with metadata
- `medium_relevance` (list[dict]): Medium relevance documents (0.5-0.79) with metadata  
- `filtered_out` (list[dict]): Filtered out documents (<0.5) with reasons

**Returns:**
- `str`: Formatted filtered results section in markdown

**Example:**
```python
filtered = SearchHelpers.format_filtered_results(
    high_relevance=[
        {"title": "Hooks reference", "score": 0.9, "rationale": "Direct configuration guide", "path": "path/to/toc"}
    ],
    medium_relevance=[
        {"title": "Testing best practices", "score": 0.6, "rationale": "Related context", "path": "path/to/toc"}
    ],
    filtered_out=[
        {"title": "API reference", "score": 0.2, "reason": "Different topic (API vs configuration)"}
    ]
)
```

---

#### `format_filtering_summary(original_count, final_count, precision_improvement)`

Formats a summary of the filtering process.

**Parameters:**
- `original_count` (int): Number of documents before filtering
- `final_count` (int): Number of documents after filtering (high + medium relevance)
- `precision_improvement` (str): Description of precision improvement

**Returns:**
- `str`: Formatted filtering summary in markdown

**Example:**
```python
summary = SearchHelpers.format_filtering_summary(
    original_count=5,
    final_count=3,
    precision_improvement="60% → 100% (high relevance only)"
)
# Returns:
# """
# **Filtering Summary:**
# - Original results: 5 documents
# - Final results: 3 documents
# - Precision improvement: 60% → 100% (high relevance only)
# """
```

---

## Usage Examples

### Complete Level 2 Fallback Example

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

# Step 1: Extract keywords from query
query = "how to configure hooks for deployment"
keywords = SearchHelpers.extract_keywords(query)
# → ['configure', 'hooks', 'deployment']

# Step 2: Build grep command
doc_set = "Claude_Code_Docs:latest"
cmd = SearchHelpers.build_level2_grep_command(keywords, doc_set)
# → "grep -r -iE '(configure|hooks|deployment)' md_docs/Claude_Code_Docs:latest/*/docTOC.md"

# Step 3: Execute via Bash tool
# (Use Bash tool to execute the command)

# Step 4: Format results with sources
url = SearchHelpers.extract_original_url(toc_content)
sources = SearchHelpers.format_sources_section([
    ("Hooks reference", url, "md_docs/Claude_Code_Docs:latest/Hooks reference/docTOC.md")
])
```

### Complete Level 3.2 Fallback Example

```python
from doc4llm.tool.md_doc_retrieval import SearchHelpers

# Step 1: Build content grep command with context
keywords = ["design philosophy"]
doc_sets = ["Claude_Code_Docs:latest"]
cmd = SearchHelpers.build_level3_content_grep_command(keywords, doc_sets, context_lines=10)
# → "grep -r -i -B 10 'design philosophy' md_docs/Claude_Code_Docs:latest/*/docContent.md"

# Step 2: Execute via Bash tool
# (Use Bash tool to execute the command)

# Step 3: Extract title from docContent.md (first 5 lines)
path = "md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"
title_cmd = SearchHelpers.build_title_extraction_command(path, max_lines=5)
# → "head -5 md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md"

# Step 4: Format results with context and sources
```

---

## Key Principle

These helpers handle repetitive formatting and construction tasks. Core semantic understanding (intent analysis, concept matching, context reasoning) remains with the LLM.
