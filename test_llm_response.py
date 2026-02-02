#!/usr/bin/env python3
"""诊断 LLM 响应解析问题"""

import re
import json
from doc4llm.doc_rag.params_parser.output_parser import extract_json_from_codeblock, JSON_BLOCK_PATTERN

# 模拟 LLM 实际响应（包含 thinking）
actual_response = """Let me analyze the user input:

**Retrieval Scene:** faithful_reference
**Filter Threshold:** 0.55

**Queries:**
- "transcript concept definition"
- "transcript how it works mechanism"
- "what is transcript in"
- "transcript usage explanation guide"
- "understanding transcript functionality"

The queries are all about understanding what a "transcript" is...

I'll rate each result by relevance:

1. **"Get started with Claude Code hooks"**
   - Page title: Not relevant to transcript concept
   - Heading: "# Get started with Claude Code hooks" - Not about transcript
   - Score: Low (0.1-0.2) - Completely unrelated topic

2. **"Manage costs effectively"**
   - Page title: Not relevant to transcript concept
   - Headings: "## 3. Reduce token usage" and "## 4. Background token usage"
   - Score: Low (0.1-0.3) - Only tangential connection

```json
{
  "query": [
    "transcript concept definition",
    "transcript how it works mechanism",
    "what is transcript in",
    "transcript usage explanation guide",
    "understanding transcript functionality"
  ],
  "doc_sets_found": [
    "Claude_Code_Docs@latest"
  ],
  "results": [
    {
      "doc_set": "Claude_Code_Docs@latest",
      "page_title": "Manage costs effectively",
      "rerank_sim": 0.55,
      "headings": [
        {
          "text": "## 4. Background token usage",
          "rerank_sim": 0.55,
          "related_context": ""
        }
      ]
    },
    {
      "doc_set": "Claude_Code_Docs@latest",
      "page_title": "Claude Code in Slack",
      "rerank_sim": 0.55,
      "headings": [
        {
          "text": "## What's accessible where",
          "rerank_sim": 0.75,
          "related_context": "**In Slack** : You'll see status updates, completion summaries, and action buttons. The full transcript is preserved and always accessible. **On the web** : The complete Claude Code session with full conversation history."
        }
      ]
    },
    {
      "doc_set": "Claude_Code_Docs@latest",
      "page_title": "Data usage",
      "rerank_sim": 0.55,
      "headings": [
        {
          "text": "### Data retention",
          "rerank_sim": 0.6,
          "related_context": "Anthropic retains Claude Code data based on your account type and preferences. Consumer users: 5-year retention period. Commercial users: 30-day retention period. Zero data retention: Claude Code will not retain chat transcripts on servers."
        }
      ]
    },
    {
      "doc_set": "Claude_Code_Docs@latest",
      "page_title": "Create custom subagents",
      "rerank_sim": 0.55,
      "headings": [
        {
          "text": "#### Resume subagents",
          "rerank_sim": 0.6,
          "related_context": "Subagent transcripts persist independently of the main conversation. They're stored in separate files at ~/.claude/projects/{project}/{sessionId}/subagents/. Subagent transcripts are unaffected by main conversation compaction."
        }
      ]
    }
  ]
}
```"""

print("=" * 60)
print("Test: Parse actual LLM response format")
print("=" * 60)

# 检查代码块匹配
print("\n1. Checking JSON_BLOCK_PATTERN...")
match = JSON_BLOCK_PATTERN.search(actual_response)
if match:
    print(f"   Found code block, length: {len(match.group(1))} chars")
    json_str = match.group(1).strip()
    print(f"   First 200 chars of JSON:\n   {json_str[:200]}")
else:
    print("   NO CODE BLOCK FOUND!")
    # 尝试其他模式
    print("\n   Trying alternative patterns...")
    alt_patterns = [
        r'\{[^{}]*"results"[^{}]*\}',
        r'```[^{}]*```',
    ]
    for pattern in alt_patterns:
        matches = re.findall(pattern, actual_response, re.DOTALL)
        print(f"   Pattern '{pattern}': {len(matches)} matches")

print("\n2. Attempting direct parse...")
result = extract_json_from_codeblock(actual_response)
print(f"   Result: {result}")
if result:
    print(f"   Success! Found {len(result.get('results', []))} results")
else:
    print("   Failed to parse!")

print("\n3. Checking for common issues...")
# 检查是否有未闭合的引号
lines = actual_response.split('\n')
in_string = False
for i, line in enumerate(lines):
    for char in line:
        if char == '"' and (i == 0 or line[i-1] != '\\'):
            in_string = not in_string
    if 'related_context' in line and '"' in line:
        # 简单检查 related_context 行
        print(f"   Line {i+1}: related_context field found")
