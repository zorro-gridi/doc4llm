#!/usr/bin/env python3
"""测试 json_repair 库"""

from json_repair import repair_json
import json
from doc4llm.doc_rag.params_parser.output_parser import extract_json_from_codeblock

print("=" * 60)
print("Test 1: Basic unescaped quotes in string")
print("=" * 60)

bad_json = '{"text": "He said "Hello" world"}'
print(f"Input: {bad_json}")

result = repair_json(bad_json)
print(f"Repaired: {result}")
print(f"Type: {type(result)}")

print("\n" + "=" * 60)
print("Test 2: Multiple unescaped quotes")
print("=" * 60)

bad_json2 = '{"related_context": "Click "View Session" to see the full transcript"}'
print(f"Input: {bad_json2}")

result2 = repair_json(bad_json2)
print(f"Repaired: {result2}")

print("\n" + "=" * 60)
print("Test 3: Compare with current fix function")
print("=" * 60)

bad_json3 = '{"related_context": "Click "View Session" to see the full transcript"}'
print(f"Input: {bad_json3}")

# json_repair
fixed_repair = repair_json(bad_json3)
print(f"json_repair: {fixed_repair}")

print("\n" + "=" * 60)
print("Test 4: Complex nested JSON")
print("=" * 60)

bad_json4 = '{"query": ["transcript concept"], "results": [{"page_title": "Test", "headings": [{"text": "## Test "quote" here", "rerank_sim": 0.5, "related_context": "Some "content" with "quotes""}]}]}'
print(f"Input: {bad_json4}")

result4 = repair_json(bad_json4)
print(f"Result type: {type(result4)}")
if isinstance(result4, dict):
    print(f"Parsed successfully!")
    print(f"related_context: {result4['results'][0]['headings'][0]['related_context']}")
else:
    print(f"Repaired result (string): {result4}")

print("\n" + "=" * 60)
print("Test 5: Full code block format")
print("=" * 60)

llm_response = '''```json
{
  "query": ["test query"],
  "results": [
    {
      "page_title": "Test Page",
      "rerank_sim": 0.6,
      "headings": [
        {
          "text": "## Test Section",
          "rerank_sim": 0.7,
          "related_context": "Click "View Details" for more info"
        }
      ]
    }
  ]
}
```'''

# Extract JSON from codeblock
parsed = extract_json_from_codeblock(llm_response)
print(f"extract_json_from_codeblock result: {parsed}")

print("\n" + "=" * 60)
print("Test 6: Edge cases")
print("=" * 60)

# Test with valid JSON
valid_json = '{"name": "test", "value": 123}'
print(f"Valid JSON result type: {type(repair_json(valid_json))}")

# Test with completely broken JSON
broken_json = '{name: "test"'
print(f"Broken JSON result: {repair_json(broken_json)}")

print("\n" + "=" * 60)
print("Test 7: Real LLM response with quotes")
print("=" * 60)

real_response = '''```json
{
  "related_context": "Click "View Session" to see the full transcript"
}
```'''

parsed_real = extract_json_from_codeblock(real_response)
print(f"Parser result: {parsed_real}")

print("\n" + "=" * 60)
print("Summary: json_repair is powerful!")
print("=" * 60)
