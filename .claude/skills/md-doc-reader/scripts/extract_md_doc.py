#!/usr/bin/env python3
"""
Markdown Document Extractor Script for md-doc-reader skill.

This script extracts content from markdown documents by title using the
MarkdownDocExtractor from doc4llm.tool.md_doc_retrieval.

Usage:
    python extract_md_doc.py --title "Agent Skills - Claude Code Docs"
    python extract_md_doc.py --title "Getting Started" --base-dir custom_docs
    python extract_md_doc.py --title "Guide" --file /path/to/file.md --search-mode fuzzy
"""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Extract markdown document content by title"
    )
    parser.add_argument(
        "--title",
        "-t",
        help="Document title to extract (required unless using --list)",
    )
    parser.add_argument(
        "--base-dir",
        "-b",
        default="md_docs",
        help="Base documentation directory (default: md_docs)",
    )
    parser.add_argument(
        "--file",
        "-f",
        help="Single .md file path for single-file mode",
    )
    parser.add_argument(
        "--search-mode",
        "-s",
        choices=["exact", "case_insensitive", "fuzzy", "partial"],
        default="exact",
        help="Search mode (default: exact)",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        "-T",
        type=float,
        default=0.6,
        help="Fuzzy threshold 0.0-1.0 (default: 0.6)",
    )
    parser.add_argument(
        "--max-results",
        "-m",
        type=int,
        help="Maximum results for fuzzy/partial search",
    )
    parser.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available documents instead of extracting",
    )
    parser.add_argument(
        "--search",
        "-S",
        action="store_true",
        help="Search for documents matching the title",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--config",
        "-c",
        help="Path to config.json file",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument(
        "--titles-csv",
        help="Comma-separated titles for multi-document extraction",
    )
    parser.add_argument(
        "--titles-file",
        help="File containing titles (one per line)",
    )
    parser.add_argument(
        "--with-metadata",
        action="store_true",
        help="Return ExtractionResult with line counts",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=2100,
        help="Threshold for requires_processing (default: 2100)",
    )
    parser.add_argument(
        "--compress",
        action="store_true",
        help="Enable compression mode",
    )
    parser.add_argument(
        "--compress-query",
        help="Query for relevance-based compression",
    )
    parser.add_argument(
        "--candidates",
        action="store_true",
        help="Extract candidate matches",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=5,
        help="Max candidates (default: 5)",
    )
    parser.add_argument(
        "--min-threshold",
        type=float,
        default=0.5,
        help="Min similarity threshold (default: 0.5)",
    )
    parser.add_argument(
        "--semantic-search",
        action="store_true",
        help="Use semantic search",
    )
    parser.add_argument(
        "--doc-set",
        help="Filter by document set",
    )
    parser.add_argument(
        "--doc-info",
        action="store_true",
        help="Get document metadata",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "summary"],
        default="text",
        help="Output format (default: text)",
    )

    args = parser.parse_args()

    # Validate arguments
    # Allow --list, --titles-csv, --titles-file, --semantic-search without --title
    requires_title = not (
        args.list or args.titles_csv or args.titles_file or args.semantic_search
    )
    if requires_title and not args.title:
        parser.error(
            "--title is required unless using --list, --titles-csv, --titles-file, or --semantic-search"
        )

    try:
        # Import the extractor
        from doc4llm.tool.md_doc_retrieval import MarkdownDocExtractor

        # Create extractor from config or with parameters
        if args.config:
            extractor = MarkdownDocExtractor.from_config(args.config)
        else:
            # Try to load knowledge base config first (shared config for all skills)
            project_root = Path(
                __file__
            ).parent.parent.parent  # scripts/ -> skill/ -> .claude/
            knowledge_base_config_path = (
                project_root / ".claude" / "knowledge_base.json"
            )
            skill_config_path = None

            if knowledge_base_config_path.exists():
                try:
                    with open(knowledge_base_config_path, "r", encoding="utf-8") as f:
                        kb_config = json.load(f)
                    kb_base_dir = kb_config.get("knowledge_base", {}).get(
                        "base_dir", "md_docs"
                    )
                    extractor = MarkdownDocExtractor(
                        base_dir=args.base_dir or kb_base_dir,
                        search_mode=args.search_mode
                        or kb_config.get("default_search_mode", "exact"),
                        fuzzy_threshold=args.fuzzy_threshold
                        or kb_config.get("fuzzy_threshold", 0.6),
                        max_results=args.max_results
                        or kb_config.get("max_results", 10),
                        debug_mode=args.debug,
                        enable_fallback=kb_config.get("enable_fallback", False),
                        fallback_modes=kb_config.get("fallback_modes", None),
                        compress_threshold=kb_config.get("compress_threshold", 2000),
                        enable_compression=kb_config.get("enable_compression", False),
                    )
                except (json.JSONDecodeError, IOError, KeyError):
                    # Fall back to skill's own config
                    knowledge_base_config_path = None
            # Fall back to skill's own config if knowledge_base.json not available
            if (
                knowledge_base_config_path is None
                or not knowledge_base_config_path.exists()
            ):
                script_dir = Path(__file__).parent  # scripts/ directory
                skill_config_path = script_dir / "config.json"

                # Add deprecation fallback for old location
                old_config_path = script_dir.parent / "config.json"
                if not skill_config_path.exists() and old_config_path.exists():
                    import warnings

                    warnings.warn(
                        "Config location deprecated: Move config.json from skill root to scripts/ directory.",
                        DeprecationWarning,
                        stacklevel=2,
                    )
                    skill_config_path = old_config_path

                if skill_config_path and skill_config_path.exists():
                    try:
                        with open(skill_config_path, "r", encoding="utf-8") as f:
                            skill_config = json.load(f)

                        if args.file:
                            extractor = MarkdownDocExtractor(
                                single_file_path=args.file,
                                search_mode=args.search_mode
                                or skill_config.get("default_search_mode", "exact"),
                                fuzzy_threshold=args.fuzzy_threshold
                                or skill_config.get("fuzzy_threshold", 0.6),
                                max_results=args.max_results
                                or skill_config.get("max_results", 10),
                                debug_mode=args.debug,
                                enable_fallback=skill_config.get(
                                    "enable_fallback", False
                                ),
                                fallback_modes=skill_config.get("fallback_modes", None),
                                compress_threshold=skill_config.get(
                                    "compress_threshold", 2000
                                ),
                                enable_compression=skill_config.get(
                                    "enable_compression", False
                                ),
                            )
                        else:
                            extractor = MarkdownDocExtractor(
                                base_dir=args.base_dir
                                or skill_config.get("base_dir", "md_docs"),
                                search_mode=args.search_mode
                                or skill_config.get("default_search_mode", "exact"),
                                fuzzy_threshold=args.fuzzy_threshold
                                or skill_config.get("fuzzy_threshold", 0.6),
                                max_results=args.max_results
                                or skill_config.get("max_results", 10),
                                debug_mode=args.debug,
                                enable_fallback=skill_config.get(
                                    "enable_fallback", False
                                ),
                                fallback_modes=skill_config.get("fallback_modes", None),
                                compress_threshold=skill_config.get(
                                    "compress_threshold", 2000
                                ),
                                enable_compression=skill_config.get(
                                    "enable_compression", False
                                ),
                            )
                    except (json.JSONDecodeError, IOError):
                        pass

            # If no config file worked, use CLI args only
            if "extractor" not in locals():
                if args.file:
                    extractor = MarkdownDocExtractor(
                        single_file_path=args.file,
                        search_mode=args.search_mode,
                        fuzzy_threshold=args.fuzzy_threshold,
                        max_results=args.max_results,
                        debug_mode=args.debug,
                    )
                else:
                    extractor = MarkdownDocExtractor(
                        base_dir=args.base_dir,
                        search_mode=args.search_mode,
                        fuzzy_threshold=args.fuzzy_threshold,
                        max_results=args.max_results,
                        debug_mode=args.debug,
                    )

        # List available documents
        if args.list:
            docs = extractor.list_available_documents()
            if args.format == "json":
                print(json.dumps({"documents": docs}, indent=2))
            else:
                print("Available documents:")
                for doc in docs:
                    print(f"  - {doc}")
            return 0

        # Search for documents
        if args.search:
            results = extractor.search_documents(args.title)
            if args.format == "json":
                print(json.dumps({"results": results}, indent=2))
            else:
                print(f"Search results for '{args.title}':")
                for result in results:
                    print(f"  - {result['title']}")
                    print(f"    Similarity: {result['similarity']:.2f}")
                    print(f"    Source: {result['doc_name_version']}")
            return 0

        # Multi-document extraction
        if args.titles_csv or args.titles_file:
            titles = []
            if args.titles_csv:
                titles.extend([t.strip() for t in args.titles_csv.split(",")])
            if args.titles_file:
                with open(args.titles_file, "r") as f:
                    titles.extend([line.strip() for line in f if line.strip()])

            if args.with_metadata:
                # Use extract_by_titles_with_metadata()
                from doc4llm.tool.md_doc_retrieval import ExtractionResult

                result: ExtractionResult = extractor.extract_by_titles_with_metadata(
                    titles=titles, threshold=args.threshold
                )
                output_metadata_result(result, args.format)
            else:
                # Use extract_by_titles()
                contents = extractor.extract_by_titles(titles)
                output_multi_contents(contents, args.format)
            return 0

        # Compression mode
        if args.compress:
            result = extractor.extract_with_compression(
                title=args.title, query=args.compress_query
            )
            output_compression_result(result, args.format)
            return 0

        # Candidate extraction
        if args.candidates:
            candidates = extractor.extract_by_title_with_candidates(
                title=args.title,
                max_candidates=args.max_candidates,
                min_threshold=args.min_threshold,
            )
            output_candidates(candidates, args.format)
            return 0

        # Semantic search
        if args.semantic_search:
            results = extractor.semantic_search_titles(
                query=args.title,
                doc_set=args.doc_set,
                max_results=args.max_results or 10,
            )
            output_semantic_results(results, args.format)
            return 0

        # Document info
        if args.doc_info:
            info = extractor.get_document_info(args.title)
            output_doc_info(info, args.format)
            return 0

        # Extract content by title
        content = extractor.extract_by_title(args.title)

        if content is None:
            print(f"No document found with title: '{args.title}'", file=sys.stderr)
            return 1
        elif content == "":
            print(
                f"Title does not match in single-file mode: '{args.title}'",
                file=sys.stderr,
            )
            return 1
        else:
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "title": args.title,
                            "content": content,
                            "length": len(content),
                        },
                        indent=2,
                    )
                )
            else:
                print(content)
            return 0

    except ImportError as e:
        print(f"Error: Could not import MarkdownDocExtractor: {e}", file=sys.stderr)
        print("Make sure doc4llm is installed: pip install doc4llm", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


# Output formatting functions


def output_metadata_result(result, format_type: str):
    """Output ExtractionResult with metadata."""
    if format_type == "json":
        print(
            json.dumps(
                {
                    "contents": result.contents,
                    "total_line_count": result.total_line_count,
                    "individual_counts": result.individual_counts,
                    "requires_processing": result.requires_processing,
                    "threshold": result.threshold,
                    "document_count": result.document_count,
                },
                indent=2,
            )
        )
    elif format_type == "summary":
        print(result.to_summary())
    else:  # text
        print(f"=== Extraction Result ===")
        print(f"Documents extracted: {result.document_count}")
        print(f"Total line count: {result.total_line_count}")
        print(f"Requires processing: {'Yes' if result.requires_processing else 'No'}")
        print(f"Threshold: {result.threshold}")
        print("\nIndividual counts:")
        for title, count in result.individual_counts.items():
            print(f"  - {title}: {count} lines")


def output_multi_contents(contents: dict, format_type: str):
    """Output multiple document contents."""
    if format_type == "json":
        print(json.dumps(contents, indent=2))
    elif format_type == "summary":
        print(f"Extracted {len(contents)} documents:")
        for title, content in contents.items():
            line_count = len(content.split("\n"))
            print(f"  - {title}: {line_count} lines")
    else:  # text
        for title, content in contents.items():
            print(f"=== {title} ===")
            print(content)
            print()


def output_compression_result(result: dict, format_type: str):
    """Output compression result."""
    if format_type == "json":
        print(json.dumps(result, indent=2))
    elif format_type == "summary":
        print(f"Title: {result['title']}")
        print(f"Line count: {result['line_count']}")
        print(f"Compressed: {result['compressed']}")
        if result["compressed"]:
            print(f"Compression ratio: {result['compression_ratio']:.0%}")
            print(f"Method: {result['compression_method']}")
    else:  # text
        print(f"=== {result['title']} ===")
        if result["compressed"]:
            print(
                f"[Compressed - {result['compression_ratio']:.0%} reduction via {result['compression_method']}]"
            )
        print(result["content"])


def output_candidates(candidates: list, format_type: str):
    """Output candidate extraction results."""
    if format_type == "json":
        print(json.dumps(candidates, indent=2))
    elif format_type == "summary":
        print(f"Found {len(candidates)} candidates:")
        for c in candidates:
            print(f"  - {c['title']} (similarity: {c['similarity']:.2f})")
    else:  # text
        for i, c in enumerate(candidates, 1):
            print(f"{i}. {c['title']}")
            print(f"   Similarity: {c['similarity']:.2f}")
            print(f"   Source: {c['doc_name_version']}")
            print(f"   Preview: {c['content_preview'][:100]}...")
            print()


def output_semantic_results(results: list, format_type: str):
    """Output semantic search results."""
    if format_type == "json":
        print(json.dumps(results, indent=2))
    elif format_type == "summary":
        print(f"Found {len(results)} results:")
        for r in results:
            print(
                f"  - {r['title']} ({r['match_type']}, similarity: {r['similarity']:.2f})"
            )
    else:  # text
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['title']}")
            print(f"   Match type: {r['match_type']}")
            print(f"   Similarity: {r['similarity']:.2f}")
            print(f"   Source: {r['doc_name_version']}")
            print()


def output_doc_info(info: dict, format_type: str):
    """Output document info."""
    if info is None:
        print("No document found.", file=sys.stderr)
        return
    if format_type == "json":
        print(json.dumps(info, indent=2))
    elif format_type == "summary":
        print(f"Title: {info.get('title', 'N/A')}")
        print(f"File: {info.get('file_path', 'N/A')}")
        print(f"Line count: {info.get('line_count', 'N/A')}")
        print(f"Document set: {info.get('doc_name_version', 'N/A')}")
    else:  # text
        print(f"=== Document Info ===")
        for key, value in info.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    sys.exit(main())
