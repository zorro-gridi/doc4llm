# AOP Handler Rules

When receiving agent output, check for `=== AOP-{TYPE} ===` markers first.

## Handling Rules

| Marker | Action |
|--------|--------|
| `AOP-FINAL` | **Pass through EXACTLY as-is** — NO summarizing, NO rephrasing, NO commentary |
| `AOP-INTERMEDIATE` | Process freely (summarize, rephrase, analyze) |
| `AOP-ERROR` | Display error exactly, then advise |
| `AOP-STREAM` | Handle as streaming |
| No marker | Default to intermediate |

## AOP-FINAL Critical Rules

When you see `=== AOP-FINAL ===`:

- ✅ Return output to user EXACTLY as received
- ❌ DO NOT summarize, rephrase, or add commentary
- ❌ DO NOT say "Here's what the agent found" or similar

**Mental model**: You are a pass-through pipe, not a helpful assistant. The agent has already formatted the output for the user.

## Why This Matters

Agents like `doc-retriever` return carefully formatted results with source citations and metadata. Modifying these outputs breaks citation integrity and progressive disclosure workflows.
