#!/usr/bin/env python3
"""
Debug script to diagnose BM25 scoring issue.
"""
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

import json
from doc4llm.doc_rag.searcher.doc_searcher_api import DocSearcherAPI
from doc4llm.doc_rag.searcher.bm25_recall import BM25Recall, extract_keywords, BM25Config

# Test configuration
kb_path = ".opencode/knowledge_base.json"
query = "如何创建 opencode skills?"

print("=" * 60)
print("Debug: BM25 Scoring Issue")
print("=" * 60)

# Load knowledge base
with open(kb_path, 'r') as f:
    kb = json.load(f)
base_dir = kb.get("knowledge_base", {}).get("base_dir", "")
print(f"\nKnowledge base dir: {base_dir}")

# Check available doc-sets
searcher = DocSearcherAPI(knowledge_base_path=kb_path)
print(f"Available doc-sets: {searcher._find_doc_sets()}")

# Extract keywords from query
keywords = extract_keywords(query)
print(f"\nExtracted keywords from '{query}': {keywords}")

# Check optimized queries
from doc4llm.doc_rag.query_optimizer.query_optimizer import QueryOptimizer
optimizer = QueryOptimizer()
opt_result = optimizer.optimize(query)
print(f"\nOptimized queries:")
for q in opt_result.optimized_queries:
    q_keywords = extract_keywords(q.get("query", ""))
    print(f"  Query: {q.get('query', '')}")
    print(f"  Keywords: {q_keywords}")

# BM25 recall test
print(f"\n" + "=" * 60)
print("BM25 Recall Test")
print("=" * 60)

doc_sets = opt_result.query_analysis.get("doc_set", [])
print(f"Target doc-sets from optimizer: {doc_sets}")

if doc_sets:
    target_doc_set = doc_sets[0]
    print(f"\nTesting BM25 recall for doc-set: {target_doc_set}")

    # Create BM25 recall instance
    bm25_recall = BM25Recall(
        base_dir=searcher.base_dir,
        threshold_page_title=0.6,
        threshold_headings=0.25,
        debug=True
    )

    # Get optimized queries
    queries = [q.get("query", "") for q in opt_result.optimized_queries[:3]]
    print(f"\nRunning BM25 recall with queries: {queries}")

    # Recall pages
    scored_pages = bm25_recall.recall_pages(target_doc_set, queries, min_headings=2)

    print(f"\nBM25 recall results:")
    print(f"  Total pages found: {len(scored_pages)}")

    for page in scored_pages[:5]:
        print(f"  Page: {page['page_title']}")
        print(f"    Score: {page['score']:.4f}")
        print(f"    Heading count: {page['heading_count']}")
        print(f"    Is basic: {page['is_basic']}")

    # Check if any page has score > 0
    pages_with_score = [p for p in scored_pages if p['score'] > 0]
    print(f"\n  Pages with score > 0: {len(pages_with_score)}")

    # Check page titles
    print(f"\n" + "=" * 60)
    print("Page Titles in Doc-Set")
    print("=" * 60)

    toc_files = bm25_recall._find_toc_files(target_doc_set)
    print(f"Found {len(toc_files)} TOC files")

    for toc_path in toc_files[:10]:
        page_title = toc_path.split("/")[-2]
        content = bm25_recall._read_toc_content(toc_path)
        # Get first few headings
        headings = content.split("\n")[:5]
        print(f"\nPage: {page_title}")
        for h in headings:
            if h.strip().startswith("#"):
                print(f"  {h.strip()[:60]}")
