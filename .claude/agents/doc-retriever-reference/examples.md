# doc-retriever Agent Workflow Examples

This document provides detailed workflow examples for the doc-retriever agent.

## Example 1: Default Query (Small Document) - Phase 3 SKIPPED

**User:** "use contextZ find content about Agent Skills"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "Agent Skills"]
Optimized queries:
1. "Agent Skills" - direct match
2. "skills reference" - expansion
3. "using skills" - action variation

[Phase 1: Invoke md-doc-searcher with optimized queries]
Found: "Agent Skills - Claude Code Docs"

[Phase 2: Invoke md-doc-reader to extract content]
Extracted: 450 lines of complete content

[Phase 2.5: Conditional Check]
Total line count (450) <= 2000 AND no compression requested
SKIP Phase 3
Return full content directly WITH source citations

[Full 450-line content displayed]

---

**Source:** https://code.claude.com/docs/en/skills
**Path:** md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md
```

---

## Example 2: Default Query (Large Document) - Phase 3 INVOKED

**User:** "use contextZ find content about Hooks configuration"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "Hooks configuration"]
Optimized queries:
1. "hooks configuration" - direct translation
2. "setup hooks" - action variation
3. "hooks settings" - synonym expansion

[Phase 1: Invoke md-doc-searcher with optimized queries]
Found: "Hooks reference"

[Phase 2: Invoke md-doc-reader to extract content]
Extracted: 2850 lines of complete content

[Phase 2.5: Conditional Check]
Total line count (2850) > 2000
 INVOKE Phase 3

[Phase 3: Invoke md-doc-processor - RETURNS FINAL OUTPUT]
[md-doc-processor output displayed directly to user - DO NOT modify]
```

---

## Example 3: Explicit Full Content Request - Phase 3 INVOKED

**User:** "use contextZ find about Hooks，返回完整内容，不要压缩"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "Hooks"]
Optimized queries:
1. "Hooks" - direct match
2. "hooks reference" - expansion
3. "Claude hooks" - context addition

[Phase 1: Invoke md-doc-searcher with optimized queries]
Found: "Hooks reference"

[Phase 2: Invoke md-doc-reader to extract content]
Extracted: 2850 lines of complete content

[Phase 2.5: Conditional Check]
Total line count (2850) > 2000
 INVOKE Phase 3

[Phase 3: Invoke md-doc-processor - RETURNS FINAL OUTPUT]
[md-doc-processor output displayed directly to user - DO NOT modify]
```

---

## Example 4: User Requests Compression (Small Document) - Phase 3 INVOKED

**User:** "use contextZ find about Agent Skills，请压缩总结"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "Agent Skills，请压缩总结"]
Optimized queries:
1. "Agent Skills" - core topic
2. "skills reference" - expansion
3. "using skills" - action variation
Note: Compression request detected for later phase handling

[Phase 1: Invoke md-doc-searcher with optimized queries]
Found: "Agent Skills - Claude Code Docs"

[Phase 2: Invoke md-doc-reader to extract content]
Extracted: 450 lines of complete content

[Phase 2.5: Conditional Check]
Total line count (450) <= 2000 BUT user requested compression ("压缩", "总结")
 INVOKE Phase 3

[Phase 3: Invoke md-doc-processor - RETURNS FINAL OUTPUT]
[md-doc-processor output displayed directly to user - DO NOT modify]
```

---

## Example 5: Multi-Document Fusion with Threshold Check (CRITICAL EXAMPLE)

**User:** "use contextZ find about hooks 配置以及部署注意事项"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "hooks 配置以及部署注意事项"]
Query Analysis:
- Original: "hooks 配置以及部署注意事项"
- Language: Chinese
- Complexity: high (contains "以及" conjunction)
- Ambiguity: low
- Applied Strategies: decomposition, translation, expansion

Optimized Queries (Ranked):
1. "hooks configuration" - translation: Direct English translation
2. "deployment hooks" - decomposition: Focus on deployment aspect
3. "hooks setup guide" - expansion: Documentation type variation
4. "deployment best practices" - expansion: Related to deployment considerations

[Phase 1: Invoke md-doc-searcher with optimized queries]
Searching with multiple optimized queries...
Found: "Hooks reference", "Get started with Claude Code hooks"

[Phase 2: Invoke md-doc-reader with extract_by_titles_with_metadata()]
```python
from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor, ExtractionResult

extractor = MarkdownDocExtractor()

# CRITICAL: Use extract_by_titles_with_metadata for multi-document
result = extractor.extract_by_titles_with_metadata([
    "Hooks reference",
    "Get started with Claude Code hooks"
], threshold=2100)

# Print summary for debugging
print(result.to_summary())
```

Output:
```
📊 Extraction Result Summary:
   Documents extracted: 2
   Total line count: 3200
   Threshold: 2100
   ⚠️  THRESHOLD EXCEEDED by 1100 lines
   → md-doc-processor SHOULD be invoked

 Individual document breakdown:
   - Hooks reference: 1200 lines
   - Get started with Claude Code hooks: 1100 lines
```

[Phase 2.5: Conditional Check]
```python
# CRITICAL: Check the requires_processing flag
if result.requires_processing:
    # Threshold exceeded (3200 > 2100)
    # → MUST invoke md-doc-processor
    INVOKE Phase 3
else:
    # Would return directly (not in this case)
    RETURN directly
```

Decision: result.requires_processing = True
 INVOKE Phase 3

[Phase 3: Invoke md-doc-processor with result.contents and result.total_line_count]
[md-doc-processor output displayed directly to user - DO NOT modify]
```

**Key Learning:** This example demonstrates why `extract_by_titles_with_metadata()` is critical:
- Without it: agent might "forget" to sum (1200 + 1100 = 3200) lines
- With it: `result.requires_processing` flag is automatically calculated
- Result: Threshold check is **guaranteed** to be correct

---

## Example 6: AOP-FINAL Output Format (Direct Return from Phase 2.5)

When skipping Phase 3, you must wrap the output with AOP-FINAL markers:

```markdown
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=450 | source=Claude_Code_Docs:latest ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

# Agent Skills

[Full 450-line content here...]

---

**Source:** https://code.claude.com/docs/en/skills
**Path:** md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md
**Document Set:** Claude_Code_Docs:latest

=== END-AOP-FINAL ===
```

---

## Example 7: Error Handling - No Results Found

**User:** "use contextZ find about non-existent topic xyz123"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "non-existent topic xyz123"]
Optimized queries:
1. "xyz123" - direct match
2. "topic xyz123" - expansion

[Phase 1: Invoke md-doc-searcher with optimized queries]
Searching with progressive fallback...
- Level 1: No semantic matches found
- Level 2: No TOC matches found
- Level 3.1: No cross-set matches found
- Level 3.2: No content matches found

[Response to user]
No documents found matching "non-existent topic xyz123".

**Suggestions:**
1. Check spelling: Did you mean "xyz123"?
2. Try broader search terms: "xyz", "topic"
3. Verify the topic exists in the available documentation sets

Available documentation sets:
- Claude_Code_Docs:latest
- Python_Docs:3.11
- React_Docs:v18
```

---

## Example 8: Progressive Fallback in Action

**User:** "use contextZ find about advanced debugging techniques"

**Your Response:**
```
Let me search for relevant documents...

[Phase 0: Invoke md-doc-query-optimizer with "advanced debugging techniques"]
Optimized queries:
1. "advanced debugging" - direct match
2. "debugging techniques" - expansion
3. "troubleshooting" - synonym
4. "debug tools" - related concept

[Phase 1: Invoke md-doc-searcher with optimized queries]
Searching...
- Level 1: No semantic title matches found (max_similarity < 0.7)
  → Triggering Level 2...
- Level 2: Found 2 documents via TOC grep
  - Debugging guide (contains "debugging" in TOC)
  - Troubleshooting (contains "troubleshooting" in TOC)

[Phase 2: Invoke md-doc-reader to extract content]
Extracted: 850 lines of complete content

[Phase 2.5: Conditional Check]
Total line count (850) <= 2000
SKIP Phase 3

[Return full content with source citations]
```

---

## Key Workflow Patterns

### Pattern 1: Always Start with Query Optimization
```python
# Phase 0 is mandatory for all queries
optimized_queries = md_doc_query_optimizer(user_query)
```

### Pattern 2: Check Threshold Before Phase 3
```python
# Always check the flag before invoking Phase 3
result = extractor.extract_by_titles_with_metadata(titles, threshold=2100)
if result.requires_processing or user_requested_compression():
    md_doc_processor(result.contents, result.total_line_count)
else:
    return_with_citations(result.contents)
```

### Pattern 3: AOP-FINAL Wrapping
```python
# Always wrap output with AOP-FINAL markers
output = format_with_citations(content)
wrapped = f"""=== AOP-FINAL | agent=doc-retriever | format=markdown | lines={line_count} | source={doc_set} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

{output}

=== END-AOP-FINAL ==="""
```

---

## User Compression Request Indicators

| Language | Keywords |
|----------|----------|
| Chinese | "压缩", "总结", "摘要", "精简" |
| English | "compress", "summarize", "summary", "condense" |

**Note:** If user explicitly requests full content ("不压缩", "完整内容", "full content", "don't compress"), that's handled by md-doc-processor, not in Phase 2.5. This check is only for detecting when user **wants** compression on small documents.
