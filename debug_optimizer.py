#!/usr/bin/env python3
"""
Debug optimizer output format.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from doc4llm.doc_rag.query_optimizer.query_optimizer import QueryOptimizer

query = "如何创建 opencode skills?"

print("=" * 60)
print("Optimizer Output Debug")
print("=" * 60)

optimizer = QueryOptimizer()
opt_result = optimizer.optimize(query)

print(f"\nopt_result type: {type(opt_result)}")
print(f"\nopt_result attributes: {dir(opt_result)}")

print(f"\noptimized_queries type: {type(opt_result.optimized_queries)}")
print(f"optimized_queries value: {opt_result.optimized_queries}")

print(f"\nquery_analysis type: {type(opt_result.query_analysis)}")
print(f"query_analysis value: {opt_result.query_analysis}")

# Check what we get when we access
print("\n" + "=" * 60)
print("Extracting values")
print("=" * 60)

# Method 1: Direct attribute access
print(f"\nDirect access:")
print(f"  opt_result.optimized_queries: {opt_result.optimized_queries}")
print(f"  opt_result.query_analysis: {opt_result.query_analysis}")

# Method 2: Get from dict
if hasattr(opt_result, '__dict__'):
    print(f"\nopt_result.__dict__: {opt_result.__dict__}")

# Check if optimized_queries is a list of dicts or something else
if isinstance(opt_result.optimized_queries, list):
    print(f"\noptimized_queries is a list with {len(opt_result.optimized_queries)} items")
    if len(opt_result.optimized_queries) > 0:
        print(f"  First item type: {type(opt_result.optimized_queries[0])}")
        print(f"  First item: {opt_result.optimized_queries[0]}")

# Check query_analysis
if isinstance(opt_result.query_analysis, dict):
    print(f"\nquery_analysis keys: {opt_result.query_analysis.keys()}")
    print(f"  doc_set: {opt_result.query_analysis.get('doc_set', 'NOT FOUND')}")
