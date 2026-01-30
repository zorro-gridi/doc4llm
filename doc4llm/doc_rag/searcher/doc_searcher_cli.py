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
import re
import sys
from pathlib import Path
from typing import List, Optional

from .doc_searcher_api import DocSearcherAPI


def load_skiped_keywords(domain_nouns: List[str] = None) -> List[str]:
    """Load skiped keywords from skiped_keywords.txt file, filtered by domain_nouns.

    Only returns keywords that are also present in domain_nouns (protected keywords).

    Args:
        domain_nouns: List of domain nouns to filter against. Only keywords
                      that are also in this list will be returned.

    Returns:
        List of protected keywords (skiped_keywords that are also in domain_nouns)
    """
    keywords_file = Path(__file__).parent / "skiped_keywords.txt"
    if not keywords_file.exists():
        return []

    all_keywords = [line.strip() for line in keywords_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    # Filter to only return keywords that are also in domain_nouns
    if domain_nouns:
        domain_set = set(n.lower() for n in domain_nouns)
        return [kw for kw in all_keywords if kw.lower() in domain_set]

    return all_keywords


def filter_query_keywords(query: str, skiped_keywords: List[str]) -> str:
    """Filter out skiped keywords from query string (case-insensitive).

    Args:
        query: Original query string
        skiped_keywords: List of keywords to remove

    Returns:
        Filtered query string with keywords removed (case-insensitive match)
    """
    # Strip query for processing
    query_lower = query.strip()
    result = query_lower

    for keyword in skiped_keywords:
        keyword_lower = keyword.strip().lower()
        if not keyword_lower:
            continue
        # Case-insensitive replacement
        pattern = keyword_lower
        # Use regex with re.IGNORECASE flag
        result = re.sub(re.escape(pattern), '', result, flags=re.IGNORECASE)

    # Clean up extra spaces that may result from keyword removal
    result = re.sub(r'\s+', ' ', result).strip()
    return result


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Markdown Document Searcher - BM25 based retrieval for doc4llm knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Config file option (must be added first to allow early override)
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON configuration file OR JSON text directly. "
             "For JSON text, input must start with '{'. "
             "All config parameters use Python naming convention (underscores). "
             "Command-line arguments override config file values.",
    )

    parser.add_argument(
        "--query",
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
        default=3,
        help="Minimum page titles per doc-set (default: 3)",
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
        default=None,
        help="Comma-separated list of doc-sets to search (required if --config not provided)",
    )

    # Behavior control
    parser.add_argument(
        "--no-fallback", action="store_true", help="Disable fallback strategies"
    )
    parser.add_argument(
        "--fallback-mode",
        type=str,
        default="parallel",
        choices=["serial", "parallel"],
        help="Fallback strategy execution mode (default: parallel). "
             "serial   - Execute fallbacks sequentially (FALLBACK_2 only if FALLBACK_1 fails). "
             "parallel - Execute both fallbacks and merge results.",
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
    parser.add_argument(
        "--hierarchical-filter",
        type=int,
        default=1,
        choices=[0, 1],
        help="Enable hierarchical heading filtering (default: 1). "
             "1=enabled (keep only highest-level headings), 0=disabled.",
    )

    # Preprocessing parameters for reranker
    parser.add_argument(
        "--domain-nouns",
        type=str,
        default="",
        help="Comma-separated list of domain nouns for rerank preprocessing (e.g., 'hook,agent,tool')",
    )
    parser.add_argument(
        "--predicate-verbs",
        type=str,
        default="",
        help="Comma-separated list of predicate verbs to filter during rerank preprocessing (e.g., 'create,delete,update')",
    )
    parser.add_argument(
        "--rerank-scopes",
        type=str,
        default="page_title",
        help="Rerank scope: 'page_title' (default), 'headings', or 'page_title,headings'. "
             "page_title: Only rerank page_title, clear headings if threshold met. "
             "headings: Only rerank headings. "
             "page_title,headings: Rerank both.",
    )

    return parser


def parse_doc_sets(doc_sets_input) -> Optional[List[str]]:
    """Parse doc-sets from string (comma-separated) or list."""
    if not doc_sets_input:
        return None
    if isinstance(doc_sets_input, list):
        return [ds.strip() for ds in doc_sets_input if ds.strip()]
    return [ds.strip() for ds in doc_sets_input.split(",") if ds.strip()]


def validate_args(args: argparse.Namespace) -> bool:
    """Validate CLI arguments."""
    # Check required query parameter
    if not args.query or not args.query:
        print("Error: --query is required (either via CLI or --config)")
        return False

    # Check required doc-sets parameter
    if not args.doc_sets:
        print("Error: --doc-sets is required (either via CLI or --config)")
        return False

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

    # Validate domain_nouns and predicate_verbs
    if args.domain_nouns:
        # Handle both list (from config) and string (from CLI) formats
        if isinstance(args.domain_nouns, list):
            nouns = [n.strip() for n in args.domain_nouns if n.strip()]
        else:
            nouns = [n.strip() for n in args.domain_nouns.split(",") if n.strip()]
        if not nouns:
            print("Error: domain-nouns cannot be empty when specified")
            return False

    if args.predicate_verbs:
        # Handle both list (from config) and string (from CLI) formats
        if isinstance(args.predicate_verbs, list):
            verbs = [v.strip() for v in args.predicate_verbs if v.strip()]
        else:
            verbs = [v.strip() for v in args.predicate_verbs.split(",") if v.strip()]
        if not verbs:
            print("Error: predicate-verbs cannot be empty when specified")
            return False

    # Validate rerank_scopes
    if args.rerank_scopes:
        # Parse both list and string formats
        if isinstance(args.rerank_scopes, list):
            scopes = [str(s).strip() for s in args.rerank_scopes if str(s).strip()]
        else:
            scopes = [s.strip() for s in args.rerank_scopes.split(",") if s.strip()]
        valid_scopes = {"page_title", "headings"}
        invalid_scopes = set(scopes) - valid_scopes
        if invalid_scopes:
            print(f"Error: Invalid rerank-scopes: {invalid_scopes}. Valid options: page_title, headings")
            return False

    return True


def load_config_file(config_input: str) -> dict:
    """Load configuration from JSON file or JSON text.

    Args:
        config_input: Either a JSON text string (starts with '{') or a path to JSON file

    Returns:
        Dictionary containing configuration values

    Raises:
        FileNotFoundError: If config file does not exist
        json.JSONDecodeError: If config is not valid JSON
    """
    # Check if input is JSON text (starts with '{' after stripping whitespace)
    if config_input.strip().startswith('{'):
        # Direct JSON text input
        return json.loads(config_input)

    # Treat as file path
    path = Path(config_input).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_input}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def apply_config_to_args(args: argparse.Namespace, config: dict) -> argparse.Namespace:
    """Apply config file values to args, preserving command-line overrides.

    Config file values are applied only if the corresponding CLI argument
    was not explicitly provided by the user.

    Args:
        args: Parsed command-line arguments
        config: Configuration dictionary from JSON file

    Returns:
        Updated args with config values applied where not overridden
    """
    # Map of config keys to args attributes
    config_mapping = {
        "base_dir": "base_dir",
        "bm25_k1": "bm25_k1",
        "bm25_b": "bm25_b",
        "threshold_page_title": "threshold_page_title",
        "threshold_headings": "threshold_headings",
        "threshold_precision": "threshold_precision",
        "min_page_titles": "min_page_titles",
        "min_headings": "min_headings",
        "doc_sets": "doc_sets",
        "no_fallback": "no_fallback",
        "fallback_mode": "fallback_mode",
        "output": "output",
        "debug": "debug",
        "json": "json",
        "reranker": "reranker",
        "reranker_model_zh": "reranker_model_zh",
        "reranker_model_en": "reranker_model_en",
        "reranker_threshold": "reranker_threshold",
        "reranker_top_k": "reranker_top_k",
        "reranker_lang_threshold": "reranker_lang_threshold",
        "hierarchical_filter": "hierarchical_filter",
        "domain_nouns": "domain_nouns",
        "predicate_verbs": "predicate_verbs",
        "rerank_scopes": "rerank_scopes",
    }

    for config_key, args_attr in config_mapping.items():
        if config_key in config:
            # Only apply config value if args attribute is at default value
            current_value = getattr(args, args_attr, None)
            default_value = _get_default_value(args, args_attr)

            # For booleans stored as action="store_true", config can enable or disable them
            if config_key in ("debug", "json", "reranker", "no_fallback"):
                if current_value == default_value:
                    setattr(args, args_attr, config[config_key])
            elif current_value == default_value:
                setattr(args, args_attr, config[config_key])

    # Handle query specially - it's a list and needs to be set from config if not provided
    if "query" in config and (not args.query or not args.query):
        args.query = config["query"] if isinstance(config["query"], list) else [config["query"]]

    return args


def _get_default_value(args: argparse.Namespace, attr: str):
    """Get the default value for an argument attribute."""
    defaults = {
        "query": None,
        "base_dir": None,
        "bm25_k1": 1.2,
        "bm25_b": 0.75,
        "threshold_page_title": 0.6,
        "threshold_headings": 0.25,
        "threshold_precision": 0.7,
        "min_page_titles": 3,
        "min_headings": 2,
        "doc_sets": None,
        "no_fallback": False,
        "fallback_mode": "parallel",
        "output": None,
        "debug": False,
        "json": False,
        "reranker": True,
        "reranker_model_zh": "BAAI/bge-large-zh-v1.5",
        "reranker_model_en": "BAAI/bge-large-en-v1.5",
        "reranker_threshold": 0.68,
        "reranker_top_k": None,
        "reranker_lang_threshold": 0.9,
        "hierarchical_filter": 1,
        "domain_nouns": "",
        "predicate_verbs": "",
        "rerank_scopes": "page_title",
    }
    return defaults.get(attr)


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Load config file if specified
    if args.config:
        try:
            config = load_config_file(args.config)
            if args.debug:
                print(f"[DEBUG] Loaded config from: {args.config}")
            args = apply_config_to_args(args, config)
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            return 1

    # Validate arguments
    if not validate_args(args):
        return 1

    # Parse doc-sets
    doc_sets = parse_doc_sets(args.doc_sets)

    # Filter query keywords - only when reranker is enabled
    if args.reranker:
        # Parse domain_nouns inline (parse_list_param is defined later)
        domain_nouns_value = args.domain_nouns
        if domain_nouns_value:
            if isinstance(domain_nouns_value, list):
                domain_nouns_list = [str(n).strip() for n in domain_nouns_value if str(n).strip()]
            else:
                domain_nouns_list = [n.strip() for n in str(domain_nouns_value).split(",") if n.strip()]
        else:
            domain_nouns_list = []

        protected_keywords = load_skiped_keywords(domain_nouns_list if domain_nouns_list else None)

        # Get all keywords from file
        keywords_file = Path(__file__).parent / "skiped_keywords.txt"
        if keywords_file.exists():
            all_keywords = [line.strip() for line in keywords_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            # Keywords to filter = all_keywords - protected_keywords
            skiped_keywords = [kw for kw in all_keywords if kw.lower() not in set(k.lower() for k in protected_keywords)]

            if skiped_keywords:
                filtered_queries = [filter_query_keywords(q, skiped_keywords) for q in args.query]
                # Remove empty queries after filtering
                args.query = [q for q in filtered_queries if q]
                if not args.query:
                    print("Error: All queries filtered out by skiped_keywords.txt")
                    return 1

    # Build API kwargs - only pass base_dir if provided (None or empty means use config default)
    def parse_list_param(value):
        """Parse a parameter that can be either a list or comma-separated string."""
        if not value:
            return []
        if isinstance(value, list):
            return [str(n).strip() for n in value if str(n).strip()]
        return [n.strip() for n in str(value).split(",") if n.strip()]

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
        hierarchical_filter=args.hierarchical_filter,
        fallback_mode=args.fallback_mode,
        domain_nouns=parse_list_param(args.domain_nouns),
        predicate_verbs=parse_list_param(args.predicate_verbs),
        rerank_scopes=parse_list_param(args.rerank_scopes),
    )
    if args.base_dir:
        api_kwargs["base_dir"] = args.base_dir

    # Create API instance
    api = DocSearcherAPI(**api_kwargs)

    # Execute search - pass target_doc_sets to skip internal Jaccard matching
    result = api.search(query=args.query, target_doc_sets=doc_sets)

    # Format output (JSON is default since --json flag is required for AOP format)
    if args.json:
        output = api.format_structured_output(result, queries=args.query,
                                              reranker_enabled=args.reranker)
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
