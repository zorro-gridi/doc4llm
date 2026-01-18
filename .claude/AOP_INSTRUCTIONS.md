# AOP Handler Instructions

**CRITICAL INSTRUCTIONS FOR MAIN AI / CALLING AGENTS**

This file defines how to handle outputs from agents that use the Agent Output Protocol (AOP).

---

## DETECTION RULES

Before processing ANY agent output, you MUST check for AOP markers:

```python
def detect_aop_marker(output: str) -> dict:
    """Detect AOP markers in agent output."""
    import re

    pattern = r'=== AOP-(\w+)(?:\s*\|(.+))? ==='
    match = re.search(pattern, output)

    if match:
        return {
            'has_marker': True,
            'type': match.group(1),  # FINAL, INTERMEDIATE, ERROR, etc.
            'attributes': match.group(2) or ''
        }
    return {'has_marker': False}
```

---

## HANDLING RULES

### Rule 1: AOP-FINAL → STRICT PASS-THROUGH

**IF** `output.contains("=== AOP-FINAL ===")`:

```
DO:
  ✅ Return output to user EXACTLY as received
  ✅ Preserve all formatting, spacing, and structure

DO NOT:
  ❌ Summarize or condense
  ❌ Rephrase or reword
  ❌ Add your own commentary
  ❌ Analyze or explain
  ❌ Modify in ANY way
```

**Example:**

```
Agent Output:
=== AOP-FINAL | agent=doc-retriever | lines=<total_lines> ===
[content]
=== END-AOP-FINAL ===

Your Response:
[Just pass through the agent output exactly as-is, NO additional text]
```

---

### Rule 2: AOP-ERROR → DISPLAY THEN ADVISE

**IF** `output.contains("=== AOP-ERROR ===")`:

```
DO:
  ✅ Display the error exactly as received
  ✅ AFTER the error block, provide helpful next steps

DO NOT:
  ❌ Modify the error message itself
  ❌ Try to "fix" the error within the error block
```

**Example:**

```
Agent Output:
=== AOP-ERROR | agent=doc-retriever ===
No documents found...
=== END-AOP-ERROR ===

Your Response:
[Display the error block exactly]

---
**What you can try next:**
- Try rephrasing your query
- Check if the documentation exists
```

---

### Rule 3: AOP-INTERMEDIATE → PROCESS FREELY

**IF** `output.contains("=== AOP-INTERMEDIATE ===")`:

```
DO:
  ✅ Summarize
  ✅ Rephrase
  ✅ Add commentary
  ✅ Use as input for further processing
  ✅ Combine with other outputs
```

---

### Rule 4: AOP-STREAM → HANDLE AS STREAM

**IF** `output.contains("=== AOP-STREAM ===")`:

```
DO:
  ✅ Display each chunk as received
  ✅ Wait for completion before considering done
  ✅ Optionally combine chunks for final display
```

---

### Rule 5: NO MARKER → DEFAULT TO INTERMEDIATE

**IF** `output does NOT contain any AOP marker`:

```
TREAT AS: AOP-INTERMEDIATE
Apply normal processing (summarize, analyze, etc.)
```

---

## IMPLEMENTATION CHECKLIST

When you receive output from an agent:

- [ ] Check for AOP marker (`=== AOP-XXX ===`)
- [ ] Identify marker type (FINAL, INTERMEDIATE, ERROR, STREAM)
- [ ] Apply corresponding handling rule
- [ ] For FINAL: Pass through unchanged
- [ ] For ERROR: Display, then advise
- [ ] For INTERMEDIATE: Process as needed
- [ ] For STREAM: Handle streaming
- [ ] For no marker: Default to intermediate processing

---

## COMMON MISTAKES TO AVOID

### ❌ Mistake 1: Summarizing AOP-FINAL

```
Agent: === AOP-FINAL === [long content] === END-AOP-FINAL ===

Wrong: "Here's a summary of what the agent found..."
Right: [Just pass through the content exactly]
```

### ❌ Mistake 2: Adding commentary to AOP-FINAL

```
Agent: === AOP-FINAL === [content] === END-AOP-FINAL ===

Wrong: [Content] + "Let me know if you need more details!"
Right: [Just the content, nothing else]
```

### ❌ Mistake 3: Modifying AOP-ERROR

```
Agent: === AOP-ERROR === [error] === END-AOP-ERROR ===

Wrong: "The agent had a small issue..." [modified error]
Right: [Display error exactly] + "---" + [Your suggestions]
```

---

## VALIDATION

You can validate your behavior:

```
Q: Did I detect the marker?
A: Yes, I saw "=== AOP-FINAL ==="

Q: Did I pass through unchanged?
A: Yes, I returned the exact output

Q: Did I add anything?
A: No, zero additions

→ VALID
```

---

## QUICK REFERENCE

| Marker | Action |
|--------|--------|
| `AOP-FINAL` | Pass through EXACTLY as-is |
| `AOP-INTERMEDIATE` | Process freely |
| `AOP-ERROR` | Display exactly, then advise |
| `AOP-STREAM` | Handle as streaming |
| No marker | Default to intermediate |
