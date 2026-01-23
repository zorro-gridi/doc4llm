#!/usr/bin/env python3
"""
Markdown Document Searcher CLI.

Command-line interface for searching markdown documents in the doc4llm
knowledge base using BM25-based retrieval.

Usage:
    python doc_searcher_cli.py --query "search query" --doc-sets "doc1@v1,doc2@v2"
    python doc_searcher_cli.py --query "query1" --query "query2" --doc-sets "doc@v1"
    python doc_searcher_cli.py --query "query" --doc-sets "doc@v1" --bm25-k1 1.5
    python doc_searcher_cli.py --query "query" --doc-sets "doc@v1" --no-fallback

Examples:
    Search single doc-set:
        python doc_searcher_cli.py --query "hooks configuration" --doc-sets "code_claude_com@latest"

    Search multiple doc-sets:
        python doc_searcher_cli.py --query "authentication" --doc-sets "api_doc@v1,auth_service@v2"

    Search with custom BM25 parameters:
        python doc_searcher_cli.py --query "api reference" --doc-sets "docs@latest" --bm25-k1 1.5 --bm25-b 0.8

    Disable fallback strategies:
        python doc_searcher_cli.py --query "skills" --doc-sets "code_claude_com@latest" --no-fallback

    Save output to file:
        python doc_searcher_cli.py --query "configuration" --doc-sets "docs@latest" --output results.txt

    Enable debug mode:
        python doc_searcher_cli.py --query "hooks" --doc-sets "code_claude_com@latest" --debug

Note:
    --doc-sets is REQUIRED. Use md-doc-query-optimizer skill to detect target doc-sets
    from the local knowledge base before calling this CLI.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from doc_searcher_api import DocSearcherAPI


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Markdown Document Searcher - BM25 based retrieval for doc4llm knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--query",
        required=True,
        action="append",
        help="Search query string (can be specified multiple times for multiple queries)",
    )

    parser.add_argument(
        "--base-dir",
        default=None,
        help="Knowledge base base directory (loaded from knowledge_base.json by default)",
    )

    # BM25 parameters
    parser.add_argument(
        "--bm25-k1", type=float, default=1.2, help="BM25 k1 parameter (default: 1.2)"
    )
    parser.add_argument(
        "--bm25-b", type=float, default=0.75, help="BM25 b parameter (default: 0.75)"
    )

    # Threshold parameters
    parser.add_argument(
        "--threshold-page-title",
        type=float,
        default=0.6,
        help="Page title matching threshold (default: 0.6)",
    )
    parser.add_argument(
        "--threshold-headings",
        type=float,
        default=0.25,
        help="Headings matching threshold (default: 0.25)",
    )
    parser.add_argument(
        "--threshold-precision",
        type=float,
        default=0.7,
        help="Precision matching threshold for headings (default: 0.7)",
    )

    # Minimum count parameters
    parser.add_argument(
        "--min-page-titles",
        type=int,
        default=1,
        help="Minimum page titles per doc-set (default: 1)",
    )
    parser.add_argument(
        "--min-headings",
        type=int,
        default=2,
        help="Minimum headings per doc-set (default: 2)",
    )

    # Required doc-sets filter
    parser.add_argument(
        "--doc-sets",
        required=True,
        help="Comma-separated list of doc-sets to search (required, from md-doc-query-optimizer)",
    )

    # Behavior control
    parser.add_argument(
        "--no-fallback", action="store_true", help="Disable fallback strategies"
    )

    # Output control
    parser.add_argument("--output", help="Output file path (default: stdout)")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    # JSON output mode
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON result instead of AOP format",
    )

    # Reranker parameters
    parser.add_argument(
        "--reranker",
        action="store_true",
        default=True,
        help="Enable transformer-based semantic re-ranking for headings",
    )
    parser.add_argument(
        "--reranker-model-zh",
        type=str,
        default="BAAI/bge-large-zh-v1.5",
        help="Chinese model ID for reranker (default: BAAI/bge-large-zh-v1.5)",
    )
    parser.add_argument(
        "--reranker-model-en",
        type=str,
        default="BAAI/bge-large-en-v1.5",
        help="English model ID for reranker (default: BAAI/bge-large-en-v1.5)",
    )
    parser.add_argument(
        "--reranker-threshold",
        type=float,
        default=0.68,
        help="Similarity threshold for filtering headings (default: 0.68). Headings with score < threshold are filtered out.",
    )
    parser.add_argument(
        "--reranker-top-k",
        type=int,
        default=None,
        help="Keep top K headings after re-ranking (default: None = keep all above threshold)",
    )
    parser.add_argument(
        "--reranker-lang-threshold",
        type=float,
        default=0.6,
        help="Language detection threshold (default: 0.6). Ratio of Chinese characters >= this value uses Chinese model, otherwise English model.",
    )

    return parser


def parse_doc_sets(doc_sets_str: Optional[str]) -> Optional[List[str]]:
    """Parse comma-separated doc-sets string."""
    if not doc_sets_str:
        return None
    return [ds.strip() for ds in doc_sets_str.split(",") if ds.strip()]


def validate_args(args: argparse.Namespace) -> bool:
    """Validate CLI arguments."""
    if args.base_dir:
        base_path = Path(args.base_dir).expanduser().resolve()
        if not base_path.exists():
            print(f"Error: base-dir path does not exist: {args.base_dir}")
            return False
        if not base_path.is_dir():
            print(f"Error: base-dir is not a directory: {args.base_dir}")
            return False

    # Validate BM25 parameters
    if not 0.0 <= args.bm25_k1 <= 5.0:
        print("Error: bm25-k1 must be between 0.0 and 5.0")
        return False

    if not 0.0 <= args.bm25_b <= 1.0:
        print("Error: bm25-b must be between 0.0 and 1.0")
        return False

    # Validate thresholds
    if not 0.0 <= args.threshold_page_title <= 1.0:
        print("Error: threshold-page-title must be between 0.0 and 1.0")
        return False

    if not 0.0 <= args.threshold_headings <= 1.0:
        print("Error: threshold-headings must be between 0.0 and 1.0")
        return False

    if not 0.0 <= args.threshold_precision <= 1.0:
        print("Error: threshold-precision must be between 0.0 and 1.0")
        return False

    # Validate minimum counts
    if args.min_page_titles < 1:
        print("Error: min-page-titles must be at least 1")
        return False

    if args.min_headings < 1:
        print("Error: min-headings must be at least 1")
        return False

    # Validate reranker threshold
    if not 0.0 <= args.reranker_threshold <= 1.0:
        print("Error: reranker-threshold must be between 0.0 and 1.0")
        return False

    # Validate reranker lang threshold
    if not 0.0 <= args.reranker_lang_threshold <= 1.0:
        print("Error: reranker-lang-threshold must be between 0.0 and 1.0")
        return False

    # Validate reranker top-k
    if args.reranker_top_k is not None and args.reranker_top_k < 1:
        print("Error: reranker-top-k must be at least 1")
        return False

    return True


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Validate arguments
    if not validate_args(args):
        return 1

    # Parse doc-sets
    doc_sets = parse_doc_sets(args.doc_sets)

    # Build API kwargs - only pass base_dir if provided
    api_kwargs = dict(
        bm25_k1=args.bm25_k1,
        bm25_b=args.bm25_b,
        threshold_page_title=args.threshold_page_title,
        threshold_headings=args.threshold_headings,
        threshold_precision=args.threshold_precision,
        min_page_titles=args.min_page_titles,
        min_headings=args.min_headings,
        debug=args.debug,
        reranker_enabled=args.reranker,
        reranker_model_zh=args.reranker_model_zh,
        reranker_model_en=args.reranker_model_en,
        reranker_threshold=args.reranker_threshold,
        reranker_top_k=args.reranker_top_k,
        reranker_lang_threshold=args.reranker_lang_threshold,
    )
    if args.base_dir:
        api_kwargs["base_dir"] = args.base_dir

    # Create API instance
    api = DocSearcherAPI(**api_kwargs)

    # Execute search - pass target_doc_sets to skip internal Jaccard matching
    result = api.search(query=args.query, target_doc_sets=doc_sets)

    # Format output (JSON is default since --json flag is required for AOP format)
    if args.json:
        output = api.format_structured_output(result)
    else:
        output = api.format_aop_output(result)

    # Write output
    if args.output:
        try:
            Path(args.output).write_text(output, encoding="utf-8")
            if args.debug:
                print(f"[DEBUG] Output written to: {args.output}")
        except Exception as e:
            print(f"Error writing output file: {e}")
            return 1
    else:
        print(output)

    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())
