#!/usr/bin/env python3
"""诊断 JSON 解析问题"""

import re
import json
from doc4llm.doc_rag.params_parser.output_parser import extract_json_from_codeblock, JSON_BLOCK_PATTERN

# 测试用例1: 正常的 JSON 代码块
test1 = """```json
{
  "related_context": "Click \"View Session\" to see the full transcript"
}
```"""

print("=" * 60)
print("Test 1 - Normal JSON with escaped quotes:")
print(f"Input:\n{test1}")
print()
result = extract_json_from_codeblock(test1)
print(f"Result: {result}")

# 测试用例2: 未转义的引号
test2 = """```json
{
  "related_context": "Click "View Session" to see the full transcript"
}
```"""

print("\n" + "=" * 60)
print("Test 2 - Unescaped quotes:")
print(f"Input:\n{test2}")
print()
result = extract_json_from_codeblock(test2)
print(f"Result: {result}")

# 测试用例3: 测试修复后的解析
print("\n" + "=" * 60)
print("Test 3 - Repair function on test2:")
from json_repair import repair_json
fixed = repair_json(test2)
print(f"Fixed:\n{fixed}")
print()
try:
    if isinstance(fixed, dict):
        result = fixed
        print(f"Already parsed successfully: {result}")
    else:
        result = json.loads(fixed)
        print(f"Parsed successfully: {result}")
except Exception as e:
    print(f"Parse error: {e}")

# 测试用例4: 检查修复后是否包含 related_context
print("\n" + "=" * 60)
print("Test 4 - Check if fixed JSON contains related_context:")
if isinstance(fixed, dict):
    print(f"related_context: {fixed.get('related_context', 'NOT FOUND')}")
else:
    print("Fixed is still a string, checking...")
    if '"related_context"' in fixed:
        print("related_context field found in fixed string")

# 测试用例5: 多行 related_context
test5 = """```json
{
  "related_context": "**In Slack** : You'll see status updates. **On the web** : The full transcript is preserved."
}
```"""

print("\n" + "=" * 60)
print("Test 5 - Multi-line related_context with markdown:")
print(f"Input:\n{test5}")
result = extract_json_from_codeblock(test5)
print(f"Result: {result}")
