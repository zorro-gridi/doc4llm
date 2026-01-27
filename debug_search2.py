#!/usr/bin/env python3
"""
Debug search with correct query extraction.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI
from doc4llm.doc_rag.query_optimizer.query_optimizer import QueryOptimizer

query = "如何创建 opencode skills?"

print("=" * 60)
print("Optimizer Check")
print("=" * 60)

optimizer = QueryOptimizer()
opt_result = optimizer.optimize(query)

print(f"\nopt_result.optimized_queries: {opt_result.optimized_queries}")
print(f"\nopt_result.query_analysis.get('doc_set'): {opt_result.query_analysis.get('doc_set', [])}")

# Extract queries correctly
optimized_queries = opt_result.optimized_queries
queries = [q.get("query", "") for q in optimized_queries]
doc_sets = opt_result.query_analysis.get("doc_set", [])

print(f"\nExtracted queries: {queries}")
print(f"Extracted doc_sets: {doc_sets}")

print("\n" + "=" * 60)
print("DocSearcherAPI.search()")
print("=" * 60)

searcher = DocSearcherAPI(
    knowledge_base_path=".opencode/knowledge_base.json",
    debug=True
)

search_result = searcher.search(
    query=queries,  # Pass the list of queries
    target_doc_sets=doc_sets if doc_sets else None
)

print("\n" + "=" * 60)
print("Result Analysis")
print("=" * 60)

print(f"\nSuccess: {search_result.get('success')}")
print(f"Results count: {len(search_result.get('results', []))}")
print(f"Fallback used: {search_result.get('fallback_used')}")
print(f"Doc sets found: {search_result.get('doc_sets_found')}")

for i, page in enumerate(search_result.get('results', [])[:5]):
    print(f"\nPage {i+1}: {page.get('page_title')}")
    print(f"  score: {page.get('score')}")
    print(f"  heading_count: {page.get('heading_count')}")
    print(f"  headings count: {len(page.get('headings', []))}")
