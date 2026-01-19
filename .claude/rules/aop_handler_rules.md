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

## Skill Execution Rules

### Rule 1: Identify Skill Type
Before executing any skill, check the skill configuration:
- Read `.claude/skills/{skill_name}/SKILL.md` frontmatter
- Check `context` field: `fork` = prompt-based, `exec` = script-based

### Rule 2: Prompt-based Skills (context: fork)
For skills marked as `context: fork`:
```
DO:
  ✅ Use skill content as prompt template
  ✅ Apply skill instructions directly in conversation
  ✅ Follow the skill's internal protocol

DO NOT:
  ❌ Execute as script
  ❌ Call external Python files
  ❌ Use bash commands
```

### Rule 3: Script-based Skills (context: exec)
For skills that have executable implementations:
```bash
python .claude/scripts/skill-dispatcher.py {skill_name} "arguments"
```

### Rule 4: Error Handling
If skill execution fails:
- Check skill type first
- Verify skill exists
- Use appropriate execution method

## Common Skill Execution Mistakes

### ❌ Mistake 1: Executing prompt-based skills as scripts
```
Wrong: cd .claude/skills/md-doc-query-optimizer && python scripts/optimize_query.py
Right: Apply the skill's prompt template directly
```

### ❌ Mistake 2: Not checking skill configuration
```
Wrong: Assume all skills are executable
Right: Read SKILL.md frontmatter to determine type
```

### ❌ Mistake 3: Using hardcoded paths
```
Wrong: cd /specific/path && python specific_script.py
Right: Use skill-dispatcher.py for unified handling
```