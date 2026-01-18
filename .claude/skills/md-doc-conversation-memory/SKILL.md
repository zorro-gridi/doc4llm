---
name: md-doc-conversation-memory
description: "Persistent conversation memory for document retrieval sessions. Tracks query history, enables context-aware query rewriting, detects continuation queries, and avoids redundant searches. Use when maintaining conversation context across multiple document queries."
allowed-tools:
  - Read
  - Bash
---

# Markdown Document Conversation Memory

Persistent memory system for tracking conversation history during document retrieval sessions.

## Purpose

Enable context-aware document retrieval by:
- **Storing** conversation history with queries and results
- **Detecting** continuation queries (e.g., "那X呢？", "And Y?")
- **Suggesting** contextually optimized queries
- **Avoiding** redundant document retrieval
- **Inferring** domain from conversation patterns

## Quick Start

```python
from doc4llm.tool.md_doc_extractor import ConversationMemory

# Initialize memory
memory = ConversationMemory(storage_dir=".claude/memory")
memory.create_session(domain="claude")

# Add conversation turn
memory.add_turn(
    query="如何配置 hooks",
    optimized_query="hooks configuration",
    results=search_results,
    satisfaction_score=0.9
)

# Get context for new query
context = memory.get_context_for_query("那部署呢？")
# Returns: {
#     "previous_queries": ["如何配置 hooks"],
#     "domain": "claude",
#     "suggested_rewrites": "deployment",  # Detected continuation
#     "documents_to_skip": ["Hooks reference"]
# }
```

---

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Conversation Memory                                         │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Sessions    │ │    Turns      │ │   Context     │
│ - session_id  │ │ - query       │ │ - history     │
│ - domain      │ │ - results     │ │ - suggested   │
│ - created_at  │ │ - timestamp   │ │ - to_skip     │
└───────────────┘ └───────────────┘ └───────────────┘
```

---

## Session Management

### Creating a Session

```python
# Auto-generated session ID
session = memory.create_session()

# With specific domain
session = memory.create_session(domain="claude")

# With custom session ID
session = memory.create_session(session_id="my_session")
```

### Loading an Existing Session

```python
# Load by session ID
session = memory.load_session("session_20250118_123456_abc123")

# List available sessions
sessions = memory.list_sessions(limit=10)
for s in sessions:
    print(f"{s['session_id']}: {s['num_turns']} turns, domain={s['domain']}")
```

### Session Data Structure

```python
{
    "session_id": "session_20250118_123456_abc123",
    "created_at": "2025-01-18T12:34:56",
    "last_updated": "2025-01-18T12:36:30",
    "turns": [
        {
            "timestamp": "2025-01-18T12:34:56",
            "query": "如何配置 hooks",
            "optimized_query": "hooks configuration",
            "results": [...],
            "documents_accessed": ["Hooks reference"],
            "satisfaction_score": 0.9
        }
    ],
    "context_summary": "Session with 2 turns. Topics: hooks, configuration. Domain: claude.",
    "domain": "claude"
}
```

---

## Conversation Tracking

### Adding a Turn

```python
memory.add_turn(
    query="那部署呢？",  # User's query
    optimized_query="deployment",  # Suggested rewrite
    results=search_results,  # From AgenticDocMatcher
    satisfaction_score=0.85  # Optional: how satisfied user was
)
```

### Getting Context for Query

```python
context = memory.get_context_for_query("那X呢？")

print(context["suggested_rewrites"])  # "X" (detected continuation)
print(context["documents_to_skip"])   # Docs already seen
print(context["domain"])              # Inferred domain
```

---

## Continuation Detection

The memory system automatically detects continuation queries:

| Pattern | Example | Detected As |
|---------|---------|-------------|
| Chinese: "那X呢？" | "那部署呢？" | "deployment" |
| Chinese: "那呢？" | "那呢？" | "{domain} information" |
| Chinese: "另外X" | "另外hooks" | "hooks" |
| English: "and X" | "and deployment" | "deployment" |
| English: "what about X" | "what about hooks" | "hooks" |

### Continuation Examples

```
Turn 1: User: "如何配置 hooks"
→ Stored as-is

Turn 2: User: "那部署呢？"
→ Detected as continuation
→ Suggested rewrite: "deployment"
→ Context: domain="claude" (inferred from Turn 1)

Turn 3: User: "还有测试相关的吗？"
→ Detected as continuation
→ Suggested rewrite: "testing"
```

---

## Domain Inference

The system automatically infers the domain from conversation history:

| Domain | Keywords |
|--------|----------|
| `claude` | claude, claude code, anthropic |
| `python` | python, pip, pypi |
| `react` | react, reactjs, jsx |
| `javascript` | javascript, js, node |

**Example:**
```python
# After several "Claude Code" queries
print(memory.current_session.domain)
# Output: "claude"
```

---

## Storage

### Storage Location

Sessions are stored as JSON files in:
```
.claude/memory/
├── session_20250118_123456_abc123.json
├── session_20250118_124500_def456.json
└── ...
```

### Cleanup

```python
# Remove old sessions, keeping last 50
deleted = memory.cleanup_old_sessions(keep_last_n=50)
print(f"Deleted {deleted} old sessions")
```

---

## Usage Patterns

### Pattern 1: Context-Aware Search

```python
# User asks follow-up question
query = "那部署呢？"

# Get context
context = memory.get_context_for_query(query)

# Use suggested rewrite if available
if context["suggested_rewrites"]:
    search_query = context["suggested_rewrites"]
else:
    search_query = query

# Skip already-seen documents
results = [
    r for r in matcher.match(search_query)
    if r["title"] not in context["documents_to_skip"]
]

# Add turn to memory
memory.add_turn(query, search_query, results)
```

### Pattern 2: Cross-Session Memory

```python
# Load previous session
memory.load_session("session_from_yesterday")

# Continue conversation
context = memory.get_context_for_query("关于X的更多信息")
print(f"Previous context: {context['previous_queries']}")
```

### Pattern 3: Session Summary

```python
# Get session summary
session = memory.current_session
print(session.context_summary)
# Output: "Session with 5 turns. Topics: hooks, configuration, deployment.
#          Domain: claude."
```

---

## Best Practices

1. **Always add turns** after search to maintain context
2. **Check continuation suggestions** before using original query
3. **Skip already-accessed documents** to avoid redundant retrieval
4. **Clean up old sessions** periodically to manage storage
5. **Use domain inference** to improve query optimization

---

## Integration with doc-qa-agentic

When used with the `doc-qa-agentic` agent:

```python
# In doc-qa-agentic agent:
from doc4llm.tool.md_doc_extractor import ConversationMemory

# Initialize memory
memory = ConversationMemory()
memory.create_session()

# For each user question:
def answer_question(question: str):
    # Get context
    context = memory.get_context_for_query(question)

    # Use suggested rewrite if available
    query = context["suggested_rewrites"] or question

    # Skip already-seen documents
    seen_docs = set(context["documents_to_skip"])

    # Perform search...
    results = matcher.match(query)
    results = [r for r in results if r["title"] not in seen_docs]

    # Add to memory
    memory.add_turn(question, query, results)

    # Return answer...
```

---

## API Reference

### ConversationMemory

| Method | Description |
|--------|-------------|
| `create_session(session_id, domain)` | Create new session |
| `load_session(session_id)` | Load existing session |
| `add_turn(query, optimized_query, results, satisfaction)` | Add conversation turn |
| `get_context_for_query(query)` | Get context for new query |
| `list_sessions(limit)` | List available sessions |
| `cleanup_old_sessions(keep_last_n)` | Remove old sessions |
| `current_session` | Get current session object |

### ConversationSession

| Attribute | Description |
|-----------|-------------|
| `session_id` | Unique session identifier |
| `created_at` | Session creation timestamp |
| `last_updated` | Last update timestamp |
| `turns` | List of ConversationTurn objects |
| `context_summary` | Generated summary of session |
| `domain` | Inferred domain/topic |

### ConversationTurn

| Attribute | Description |
|-----------|-------------|
| `timestamp` | Turn timestamp |
| `query` | Original user query |
| `optimized_query` | Optimized query used |
| `results` | Search results |
| `documents_accessed` | List of document titles |
| `satisfaction_score` | Optional satisfaction (0-1) |
