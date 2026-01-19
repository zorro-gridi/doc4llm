# Agent Output Protocol (AOP)

A unified system for marking agent outputs to control how they are processed by calling agents or the main AI.

---

## Overview

When agents return results, they wrap their output with special markers that tell the receiver how to handle the content. This prevents unwanted modifications, reformatting, or reprocessing.

---

## Marker Types

### 1. `FINAL` - Immutable Output

**Purpose:** Output that MUST NOT be modified in any way.

**Use Cases:**
- Document retrieval results (doc-retriever)
- Final QA answers (doc-qa-agentic)
- Any output that has already been formatted for the user

**Format:**
```
=== AOP-FINAL ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary
[content that must not be modified]
=== END-AOP-FINAL ===
```

**Receiver Behavior:**
- ✅ Return to user exactly as received
- ❌ NO summarization
- ❌ NO reformatting
- ❌ NO additional commentary
- ❌ NO analysis or explanation

---

### 2. `INTERMEDIATE` - Processable Output

**Purpose:** Output that can be processed, summarized, or transformed by the receiver.

**Use Cases:**
- Raw data extraction
- Partial results
- Intermediate computation outputs

**Format:**
```
=== AOP-INTERMEDIATE ===
[content that can be processed]
=== END-AOP-INTERMEDIATE ===
```

**Receiver Behavior:**
- ✅ Can summarize
- ✅ Can reformat
- ✅ Can add commentary
- ✅ Can use as input for further processing

---

### 3. `STREAM` - Streaming Output

**Purpose:** Output that is being streamed and may continue.

**Use Cases:**
- Long-running operations
- Real-time data processing
- Multi-stage workflows

**Format:**
```
=== AOP-STREAM ===
[chunk 1 of content]
=== END-AOP-STREAM ===

=== AOP-STREAM ===
[chunk 2 of content]
=== END-AOP-STREAM ===
```

**Receiver Behavior:**
- ✅ Display each chunk as received
- ✅ Wait for final chunk before considering complete
- ✅ Can buffer and combine

---

### 4. `ERROR` - Error Output

**Purpose:** Error information that should be preserved exactly.

**Format:**
```
=== AOP-ERROR ===
[error message, stack trace, diagnostic info]
=== END-AOP-ERROR ===
```

**Receiver Behavior:**
- ✅ Display error to user
- ❌ NO attempt to "fix" or rephrase the error
- ✅ Can suggest next steps AFTER the error block

---

### 5. `CONTEXT` - Contextual Information

**Purpose:** Metadata or context that accompanies the main output.

**Format:**
```
=== AOP-CONTEXT ===
{"metadata": "values", "stats": {...}}
=== END-AOP-CONTEXT ===

=== AOP-FINAL ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary
[main content]
=== END-AOP-FINAL ===
```

**Receiver Behavior:**
- Context can be used for decision-making
- Main output follows standard marker rules

---

## Marker Syntax

### Basic Syntax

```
=== AOP-{TYPE} ===
[content]
=== END-AOP-{TYPE} ===
```

### With Attributes

```
=== AOP-{TYPE} | {key1}={value1} | {key2}={value2} ===
[content]
=== END-AOP-{TYPE} ===
```

**Example:**
```
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=<total_lines> ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary
[content]
=== END-AOP-FINAL ===
```

**Supported Attributes:**
| Attribute | Description | Example |
|-----------|-------------|---------|
| `agent` | Agent name | `doc-retriever` |
| `format` | Content format | `markdown`, `json`, `code` |
| `lines` | Line count | `450` |
| `source` | Source URL or path | `https://example.com` |
| `version` | Document or API version | `v1.2.3` |
| `confidence` | Confidence score | `0.85` |

---

## Agent Implementation Guide

### Step 1: Import Protocol Constants

```yaml
# In agent frontmatter
protocol: AOP
protocol_version: "1.0"
```

### Step 2: Define Your Output Type

Choose the appropriate marker type based on your agent's purpose:

| Agent Purpose | Recommended Marker |
|---------------|-------------------|
| Final answer/result | `AOP-FINAL` |
| Raw data extraction | `AOP-INTERMEDIATE` |
| Real-time processing | `AOP-STREAM` |
| Error conditions | `AOP-ERROR` |

### Step 3: Wrap Output

```markdown
=== AOP-FINAL | agent=your-agent-name | source={doc_dir} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

[Your formatted output here]

**Sources:**
- [Document 1](url)
- [Document 2](url)

=== END-AOP-FINAL ===
```

---

## Main AI / Caller Behavior

### Detection Rules

The calling AI MUST check for AOP markers before processing any agent output:

```
IF output contains "=== AOP-FINAL ===":
    PASS THROUGH UNCHANGED
ELIF output contains "=== AOP-ERROR ===":
    DISPLAY ERROR, THEN PROVIDE NEXT STEPS
ELIF output contains "=== AOP-INTERMEDIATE ===":
    PROCESS AS NEEDED (summarize, reformat, analyze)
ELIF output contains "=== AOP-STREAM ===":
    HANDLE AS STREAMING CONTENT
ELSE:
    DEFAULT INTERMEDIATE PROCESSING
```

### Strict Mode

In **strict mode** (recommended for production):
- If marker is detected, behavior is MANDATORY (not optional)
- Violations should be logged as errors
- System should warn if unmarked output is received

---

## Migration Guide

### For Existing Agents

1. **Add protocol to frontmatter:**
   ```yaml
   ---
   protocol: AOP
   protocol_version: "1.0"
   ---
   ```

2. **Update output sections:**
   ```markdown
   ## Your Output Requirements

   You MUST wrap all final outputs with AOP markers:

   ```markdown
   === AOP-FINAL | agent=your-agent-name ===
   **Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary
   [your output]
   === END-AOP-FINAL ===
   ```

3. **Update STRICT OUTPUT sections:**
   ```markdown
   ## STRICT OUTPUT PROHIBITION

   **CRITICAL:** This agent returns AOP-FINAL output. Any receiver MUST:
   - Return content EXACTLY as received
   - NO modifications, summaries, or reformatting
   - NO additional commentary or analysis
   ```

### Before/After Example

**Before:**
```
Based on my search, here are the results:

[content]
```

**After:**
```
=== AOP-FINAL | agent=doc-retriever | source={doc_dir} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

[content]

**Sources:** ...
=== END-AOP-FINAL ===
```

---

## Validation

### Automated Testing

```python
import re

AOP_PATTERN = r'=== AOP-(\w+)(?:\s*\|([^=]+=[^=|\s]+(?:\s*\|\s*[^=]+=[^=|\s]+)*))? ==='

def validate_aop_output(output: str) -> bool:
    """Check if output has valid AOP markers."""
    matches = re.findall(AOP_PATTERN, output)

    if not matches:
        return False  # No markers found

    # Check for matching end markers
    for marker_type, _ in matches:
        if f'=== END-AOP-{marker_type} ===' not in output:
            return False

    return True
```

### Manual Testing Checklist

- [ ] Output has proper opening marker
- [ ] Output has proper closing marker (matching type)
- [ ] Marker type is appropriate for content
- [ ] Attributes (if any) are correctly formatted
- [ ] Content is properly enclosed

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-18 | Initial AOP specification |

---

## Examples

### Example 1: Document Retrieval (doc-retriever)

```
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines=<total_lines> | source={doc_dir} ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

# Agent Skills

[450 lines of content]

---
**Source:** https://code.claude.com/docs/en/skills
**Path:** md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md
**Document Set:** Claude_Code_Docs:latest

=== END-AOP-FINAL ===
```

### Example 2: QA Result (doc-qa-agentic)

```
=== AOP-FINAL | agent=doc-qa-agentic | confidence=0.92 | sources=3 ===
**Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary

## Hooks Configuration and Deployment

I searched through 2 topics to answer your question.

### Configuration
[content]

### Deployment Considerations
[content]

**Confidence:** 92%

**Sources:**
1. Hooks reference (relevance: 0.92)
2. Get started with hooks (relevance: 0.85)

=== END-AOP-FINAL ===
```

### Example 3: Error Output

```
=== AOP-ERROR | agent=doc-retriever | code=DOC_NOT_FOUND ===

No documents found matching query: "nonexistent topic"

**Search Parameters:**
- Query: "nonexistent topic"
- Max results: 5
- Similarity threshold: 0.5

**Suggestions:**
- Try rephrasing your query
- Check for typos
- Use more general terms

=== END-AOP-ERROR ===
```
