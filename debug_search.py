#!/usr/bin/env python3
"""
Debug script to trace the issue between BM25 and fallback results.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import json
from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI
from doc4llm.doc_rag.searcher.bm25_recall import BM25Recall, extract_keywords, BM25Config

kb_path = ".opencode/knowledge_base.json"
query = "如何创建 opencode skills?"

print("=" * 60)
print("Step 1: DocSearcherAPI.search() with debug=True")
print("=" * 60)

# Create searcher with debug mode
searcher = DocSearcherAPI(
    knowledge_base_path=kb_path,
    debug=True
)

# Get optimized queries from optimizer
from doc4llm.doc_rag.query_optimizer.query_optimizer import QueryOptimizer
optimizer = QueryOptimizer()
opt_result = optimizer.optimize(query)
doc_sets = opt_result.query_analysis.get("doc_set", [])
queries = [q.get("query", "") for q in opt_result.optimized_queries]
target_doc_sets = doc_sets if doc_sets else None

print(f"\nTarget doc_sets: {target_doc_sets}")
print(f"Queries: {queries[:3]}...")

# Run search
search_result = searcher.search(
    query=queries,
    target_doc_sets=target_doc_sets
)

print("\n" + "=" * 60)
print("Search Result Analysis")
print("=" * 60)

print(f"\nSuccess: {search_result.get('success')}")
print(f"Total results: {len(search_result.get('results', []))}")
print(f"Fallback used: {search_result.get('fallback_used')}")

# Check results
for i, page in enumerate(search_result.get('results', [])[:5]):
    print(f"\nPage {i+1}: {page.get('page_title')}")
    print(f"  doc_set: {page.get('doc_set')}")
    print(f"  score: {page.get('score')}")
    print(f"  bm25_sim: {page.get('bm25_sim')}")
    print(f"  heading_count: {page.get('heading_count')}")
    print(f"  headings: {len(page.get('headings', []))}")

print("\n" + "=" * 60)
print("Direct BM25 Recall Check")
print("=" * 60)

# Test BM25 recall directly
if target_doc_sets:
    bm25_recall = BM25Recall(
        base_dir=searcher.base_dir,
        threshold_page_title=0.6,
        threshold_headings=0.25,
        debug=False
    )

    scored_pages = bm25_recall.recall_pages(target_doc_sets[0], queries, min_headings=2)
    print(f"\nDirect BM25 recall found {len(scored_pages)} pages:")

    for page in scored_pages[:5]:
        print(f"  {page['page_title']}: score={page['score']:.4f}, headings={page['heading_count']}")
