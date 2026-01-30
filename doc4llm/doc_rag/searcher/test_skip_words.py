#!/usr/bin/env python3
"""测试 doc_searcher_api.py 接口的 skip words 过滤功能。"""

import sys
import json
from pathlib import Path

# 添加项目路径 - 使用项目根目录
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI

# 测试数据
test_input = {
    "query": [
        "claude code skill result context injection",
        "claude code hook skill output context integration",
        "how to add skill results to conversation context claude code",
        "claude code skill context hook mechanism",
        "inject skill output into context claude code guide"
    ],
    "target_doc_sets": [
        "Claude_Code_Docs@latest"
    ],
    "domain_nouns": [
        "skill",
        "hook",
        "context",
        "rag skill"
    ],
    "predicate_verbs": [
        "inject",
        "integrate",
        "add",
        "insert",
        "pass",
        "return",
        "provide",
        "deliver"
    ],
    "reranker_threshold": 0.58,
    "scene": "faithful_how_to"
}

# 获取知识库路径
knowledge_base_path = project_root / ".claude" / "knowledge_base.json"
if knowledge_base_path.exists():
    with open(knowledge_base_path, "r", encoding="utf-8") as f:
        kb_config = json.load(f)
        base_dir = kb_config.get("knowledge_base", {}).get("base_dir", str(project_root / "knowledge_base"))
        # 处理 ~ 路径
        if base_dir.startswith("~"):
            base_dir = Path(base_dir).expanduser()
else:
    base_dir = str(project_root / "knowledge_base")

# 确保路径是绝对路径
base_dir = str(Path(base_dir).expanduser().resolve())

print(f"Knowledge base path: {base_dir}")
print(f"Target doc-sets: {test_input['target_doc_sets']}")
print()

# 测试 skip words 过滤功能
print("=" * 70)
print("测试 Skip Words 过滤功能")
print("=" * 70)

# 创建搜索器实例，启用 debug 模式
searcher = DocSearcherAPI(
    base_dir=base_dir,
    debug=True,
    domain_nouns=test_input["domain_nouns"],
    predicate_verbs=test_input["predicate_verbs"],
    reranker_enabled=False,  # 禁用 reranker 以简化测试
)

print(f"\nskiped_keywords 配置: {searcher.skiped_keywords}")
print(f"domain_nouns 配置: {searcher.domain_nouns}")
print()

# 测试过滤函数
print("-" * 70)
print("测试 _filter_query_keywords 函数")
print("-" * 70)

skiped_keywords_filter = [
    kw for kw in searcher.skiped_keywords
    if kw.lower() not in {pk.lower() for pk in searcher._get_protected_keywords()}
]

print(f"实际要过滤的 skiped_keywords: {skiped_keywords_filter}")
print()

original_queries = test_input["query"]
filtered_queries = []

for q in original_queries:
    filtered_q = searcher._filter_query_keywords(q, skiped_keywords_filter)
    filtered_queries.append(filtered_q)
    status = "已过滤" if filtered_q != q else "无变化"
    print(f"  原始: '{q}'")
    print(f"  过滤: '{filtered_q}' [{status}]")
    print()

# 执行搜索
print("-" * 70)
print("执行搜索测试")
print("-" * 70)

result = searcher.search(
    query=original_queries,
    target_doc_sets=test_input["target_doc_sets"],
)

print("\n" + "=" * 70)
print("搜索结果分析")
print("=" * 70)

print(f"\nsuccess: {result.get('success')}")
print(f"fallback_used: {result.get('fallback_used')}")
print(f"doc_sets_found: {result.get('doc_sets_found')}")
print(f"\n返回的 query (过滤后):")
for i, q in enumerate(result.get('query', [])):
    print(f"  [{i}] {q}")

print(f"\n结果数量: {len(result.get('results', []))}")

# 检查 skip words 是否在返回的 query 中
print("\n" + "-" * 70)
print("Skip Words 验证")
print("-" * 70)

returned_queries = result.get('query', [])
skip_words_found = []

for sw in skiped_keywords_filter:
    for q in returned_queries:
        if sw.lower() in q.lower():
            skip_words_found.append((sw, q))

if skip_words_found:
    print("⚠️  发现 skip words 仍在返回的 query 中:")
    for sw, q in skip_words_found:
        print(f"  - '{sw}' 出现在: '{q}'")
else:
    print("✓ 所有 skip words 已被正确过滤掉!")

print("\n" + "=" * 70)
print("测试完成")
print("=" * 70)
