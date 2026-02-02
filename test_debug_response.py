#!/usr/bin/env python3
"""测试实际运行时的原始响应"""

import json
from doc4llm.doc_rag.llm_reranker.llm_reranker import LLMReranker

# 测试用例
reranker = LLMReranker()

with open('phase1_5_input.json', 'r') as f:
    input_data = json.load(f)

# 修改 rerank 方法来捕获原始响应
original_rerank = reranker.rerank

def debug_rerank(data):
    from doc4llm.llm.anthropic import invoke

    reranker._validate_input(data)
    if not reranker._prompt_template:
        reranker._load_prompt_template()

    prompt = reranker._build_prompt(data)

    print("=" * 60)
    print("INVOKING LLM...")
    print("=" * 60)

    message = invoke(
        model=reranker.config.model,
        max_tokens=reranker.config.max_tokens,
        temperature=reranker.config.temperature,
        system=reranker._prompt_template,
        messages=[{"role": "user", "content": prompt}],
    )

    # 打印原始响应
    print("\n" + "=" * 60)
    print("RAW RESPONSE FROM LLM:")
    print("=" * 60)
    for block in message.content:
        if block.type == "text":
            raw = block.text
            print(f"Response length: {len(raw)} chars")
            print(f"First 1000 chars:\n{raw[:1000]}")
            print(f"\n... middle ...\n")
            print(f"Last 500 chars:\n{raw[-500:]}")

            # 检查 JSON 代码块
            from doc4llm.doc_rag.params_parser.output_parser import JSON_BLOCK_PATTERN
            match = JSON_BLOCK_PATTERN.search(raw)
            if match:
                print(f"\nJSON code block found! Length: {len(match.group(1))} chars")
                print(f"JSON starts with: {match.group(1)[:100]}")
            else:
                print("\nNO JSON CODE BLOCK FOUND!")

    result = reranker._parse_response(message, data)
    return result

# 运行测试
result = debug_rerank(input_data)
print("\n" + "=" * 60)
print("RESULT:")
print("=" * 60)
print(f"Success: {result.success}")
print(f"Headings before: {result.total_headings_before}")
print(f"Headings after: {result.total_headings_after}")
