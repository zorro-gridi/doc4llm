# AOP (Agent Output Protocol) - Implementation Summary

## Overview

A unified marker system for agent outputs that prevents unwanted modifications, reformatting, or reprocessing by calling agents or the main AI.

---

## Problem Solved

**Before:** Agents like `doc-retriever` would return final output, but the main AI would incorrectly treat it as intermediate data and add summaries, commentary, or reformatting.

**After:** Agents wrap output with `AOP-FINAL` markers, explicitly signaling that the content must be passed through unchanged.

---

## Files Created

| File | Purpose |
|------|---------|
| `.claude/AGENT_OUTPUT_PROTOCOL.md` | AOP specification and implementation guide |
| `.claude/AOP_INSTRUCTIONS.md` | Handling rules for main AI / calling agents |
| `.claude/AOP_VALIDATION.py` | Python validation tool |
| `.claude/AOP_TESTS.py` | Test suite (10 tests, all passing) |

---

## Files Modified

| File | Changes |
|------|---------|
| `.claude/agents/doc-retriever.md` | Added AOP protocol, updated all output formats |
| `.claude/agents/doc-qa-agentic.md` | Added AOP protocol, updated all output formats |

---

## AOP Marker Types

| Type | Purpose | Receiver Behavior |
|------|---------|-------------------|
| `AOP-FINAL` | Immutable output | Pass through exactly as-is |
| `AOP-INTERMEDIATE` | Processable output | Summarize, reformat, analyze |
| `AOP-ERROR` | Error information | Display exactly, then advise |
| `AOP-STREAM` | Streaming output | Handle as streaming content |
| `AOP-CONTEXT` | Metadata | Use for decision-making |

---

## Marker Syntax

### Basic
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

### Example
```
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines={total_lines} | source={doc_dir} ===

[Document content here...]

---
**Source:** https://example.com
**Path:** md_docs/...

=== END-AOP-FINAL ===
```

---

## Agent Implementation

### Step 1: Add Protocol to Frontmatter

```yaml
---
protocol: AOP
protocol_version: "1.0"
---
```

### Step 2: Update Output Sections

```markdown
## Your Output Requirements

You MUST wrap all final outputs with AOP markers:

```markdown
=== AOP-FINAL | agent=your-agent-name ===
[your output]
=== END-AOP-FINAL ===
```
```

### Step 3: Update STRICT OUTPUT Sections

```markdown
## STRICT OUTPUT PROHIBITION

**CRITICAL:** This agent returns AOP-FINAL output. Any receiver MUST:
- Return content EXACTLY as received
- NO modifications, summaries, or reformatting
- NO additional commentary or analysis
```

---

## Main AI / Caller Behavior

### Detection Rules

```
IF output contains "=== AOP-FINAL ===":
    PASS THROUGH UNCHANGED
ELIF output contains "=== AOP-ERROR ===":
    DISPLAY ERROR, THEN PROVIDE NEXT STEPS
ELIF output contains "=== AOP-INTERMEDIATE ===":
    PROCESS AS NEEDED
ELIF output contains "=== AOP-STREAM ===":
    HANDLE AS STREAMING
ELSE:
    DEFAULT TO INTERMEDIATE PROCESSING
```

### Strict Mode (Recommended)

In strict mode, if a marker is detected, behavior is MANDATORY (not optional).

---

## Validation

### Using Python Tool

```python
from AOP_VALIDATION import validate_agent_output

output = """=== AOP-FINAL | agent=test ===
content
=== END-AOP-FINAL ==="""

result = validate_agent_output(output)
# {'valid': True, 'errors': [], 'marker_type': 'FINAL', 'attributes': {...}}
```

### Running Tests

```bash
python .claude/AOP_TESTS.py
```

All 10 tests should pass.

---

## Examples

### Document Retrieval (doc-retriever)

```
=== AOP-FINAL | agent=doc-retriever | format=markdown | lines={total_lines} | source=<doc_dir> ===

# Agent Skills

[450 lines of content]

---
**Source:** https://code.claude.com/docs/en/skills
**Path:** md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md
**Document Set:** Claude_Code_Docs:latest

=== END-AOP-FINAL ===
```

### QA Result (doc-qa-agentic)

```
=== AOP-FINAL | agent=doc-qa-agentic | confidence=0.92 | sources=3 ===

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

### Error Output

```
=== AOP-ERROR | agent=doc-qa-agentic | code=NO_RESULTS ===

No documents found matching your query: "nonexistent topic"

**Search Parameters:**
- Query: "nonexistent topic"
- Max results: 5

**Suggestions:**
- Try rephrasing your query
- Check for typos

=== END-AOP-ERROR ===
```

---

## Quick Reference for Main AI

| Marker | Action |
|--------|--------|
| `AOP-FINAL` | **Pass through EXACTLY as-is** |
| `AOP-INTERMEDIATE` | Process freely |
| `AOP-ERROR` | Display exactly, then advise |
| `AOP-STREAM` | Handle as streaming |
| No marker | Default to intermediate |

---

## Next Steps

### For Other Agents

To migrate other agents to AOP:

1. Add `protocol: AOP` to frontmatter
2. Update output format sections with AOP markers
3. Add STRICT OUTPUT section
4. Update examples with AOP markers

### For Skills

Skills can also use AOP markers if they return data that should not be modified.

---

## Support

For questions or issues:
- See `.claude/AGENT_OUTPUT_PROTOCOL.md` for full specification
- See `.claude/AOP_INSTRUCTIONS.md` for handling rules
- Run `.claude/AOP_TESTS.py` to verify implementation
