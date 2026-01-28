#!/usr/bin/env python3
"""
Markdown Document Extractor CLI for DocReaderAPI.

This script provides CLI interface for extracting content from markdown documents.
It wraps DocReaderAPI with command-line arguments.

Usage:
    python doc_reader_cli.py --list --base-dir <dir>
    python doc_reader_cli.py --search "getting started" --base-dir <dir>
    python doc_reader_cli.py --page-title "Getting Started" --base-dir <dir>
    python doc_reader_cli.py --page-titles ["Guide", "API"] --base-dir <dir>
    python doc_reader_cli.py --sections [{"title": "Guide", "headings": ["Installation"], "doc_set": "docs@latest"}]
    python doc_reader_cli.py --headings "Installation" --page-title "Guide" --doc-set "docs@latest"

DocReaderAPI Parameters Mapping:
    --base-dir        -> base_dir
    --config          -> config (unified config for DocReaderAPI and MarkdownDocExtractor)
    --search-mode     -> search_mode
    --fuzzy-threshold -> fuzzy_threshold
    --max-results     -> max_results
    --debug           -> debug_mode
    --threshold       -> compress_threshold

Config Format for --config:
    Supports JSON file path or inline JSON string.
    Can contain both DocReaderAPI and MarkdownDocExtractor parameters.

    Nested structure (recommended):
        {
            "search_mode": "fuzzy",
            "debug_mode": true,
            "matcher": {
                "case_sensitive": true,
                "fuzzy_threshold": 0.8
            }
        }

    Flat structure (auto-detect field ownership):
        {
            "search_mode": "fuzzy",
            "case_sensitive": true
        }
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def main():
    parser = argparse.ArgumentParser(
        description="Extract markdown document content using DocReaderAPI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
DocReaderAPI Parameters Mapping:
    --base-dir        -> base_dir
    --config          -> config (unified config for DocReaderAPI and MarkdownDocExtractor)
    --search-mode     -> search_mode
    --fuzzy-threshold -> fuzzy_threshold
    --max-results     -> max_results
    --debug           -> debug_mode
    --threshold       -> compress_threshold

Config Format for --config:
    - File path: /path/to/config.json
    - Inline JSON: '{"search_mode": "fuzzy"}'
    - Supports nested structure: {"search_mode": "fuzzy", "matcher": {"case_sensitive": true}}
        """,
    )

    # Core arguments matching DocReaderAPI
    parser.add_argument(
        "--base-dir",
        "-b",
        default=None,
        help="Base directory for documents (required)",
    )
    parser.add_argument(
        "--config",
        "-c",
        default=None,
        help="Unified config: JSON file path or inline JSON string (supports nested 'matcher' key)",
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
        default=None,
        help="Maximum results for fuzzy/partial search",
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug output",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=2100,
        help="Threshold for requires_processing (default: 2100)",
    )

    # Operation mode arguments
    operation_group = parser.add_mutually_exclusive_group(required=True)
    operation_group.add_argument(
        "--list",
        "-l",
        action="store_true",
        help="List available documents",
    )
    operation_group.add_argument(
        "--search",
        "-S",
        action="store_true",
        help="Search for documents matching the title",
    )
    operation_group.add_argument(
        "--page-title",
        "-t",
        help="Single document page title to extract",
    )
    operation_group.add_argument(
        "--page-titles",
        help="JSON array of document titles to extract",
    )
    operation_group.add_argument(
        "--sections",
        help='JSON array of section configs: [{"title": "...", "headings": [...], "doc_set": "..."}]',
    )
    operation_group.add_argument(
        "--headings",
        nargs="+",
        help="Heading names for section extraction (requires --page-title and --doc-set)",
    )

    # Additional arguments
    parser.add_argument(
        "--doc-set",
        help="Document set identifier (e.g., 'code_claude_com@latest') - REQUIRED for --headings",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output in JSON format",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "summary"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--with-metadata",
        action="store_true",
        help="Return ExtractionResult with line counts (for --page-titles)",
    )

    args = parser.parse_args()

    # Handle config file/json (unified config for DocReaderAPI and MarkdownDocExtractor)
    config = None
    if args.config:
        if os.path.isfile(args.config):
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)
        else:
            try:
                config = json.loads(args.config)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON in --config: {e}", file=sys.stderr)
                return 1

    # Apply config values (if provided)
    if config:
        args.base_dir = config.get("base_dir", args.base_dir)
        args.doc_set = config.get("doc_set", args.doc_set)
        args.with_metadata = config.get("with_metadata", args.with_metadata)
        args.threshold = config.get("threshold", args.threshold)
        args.format = config.get("format", args.format)
        args.search_mode = config.get("search_mode", args.search_mode)
        args.fuzzy_threshold = config.get("fuzzy_threshold", args.fuzzy_threshold)
        args.max_results = config.get("max_results", args.max_results)
        args.debug = config.get("debug_mode", args.debug)

        page_titles = config.get("page_titles")
        if page_titles:
            if isinstance(page_titles, list) and page_titles:
                first = page_titles[0]
                if isinstance(first, dict):
                    if any(isinstance(p, dict) and "headings" in p for p in page_titles):
                        args.sections = page_titles
                    else:
                        args.page_titles = [p.get("title") if isinstance(p, dict) else p for p in page_titles]
                else:
                    args.page_titles = page_titles
            else:
                args.page_titles = [page_titles] if not isinstance(page_titles, list) else page_titles
        else:
            args.page_title = config.get("page_title", args.page_title)

        sections = config.get("sections")
        if sections:
            args.sections = sections

        headings = config.get("headings")
        if headings:
            args.headings = headings

    # Validate base_dir
    if not args.base_dir:
        parser.error("--base-dir is required")
    base_path = Path(args.base_dir).expanduser().resolve()
    if not base_path.exists():
        print(f"Error: base-dir path does not exist: {args.base_dir}", file=sys.stderr)
        return 1
    if not base_path.is_dir():
        print(f"Error: base-dir is not a directory: {args.base_dir}", file=sys.stderr)
        return 1

    # Validate --headings requires --doc-set
    if args.headings and not args.doc_set:
        parser.error("--doc-set is required when using --headings for section extraction")

    # Validate --page-titles format
    if args.page_titles and isinstance(args.page_titles, str):
        try:
            args.page_titles = json.loads(args.page_titles)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --page-titles: {e}", file=sys.stderr)
            return 1

    # Validate --sections format
    if args.sections and isinstance(args.sections, str):
        try:
            args.sections = json.loads(args.sections)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --sections: {e}", file=sys.stderr)
            return 1

    try:
        from doc4llm.doc_rag.reader.doc_reader_api import DocReaderAPI

        # Initialize DocReaderAPI
        reader = DocReaderAPI(
            base_dir=str(base_path),
            config=args.config,
            search_mode=args.search_mode,
            fuzzy_threshold=args.fuzzy_threshold,
            max_results=args.max_results,
            debug_mode=args.debug,
            compress_threshold=args.threshold,
        )

        # List available documents
        if args.list:
            docs = reader.list_available_documents()
            if args.format == "json":
                print(json.dumps({"documents": docs}, indent=2))
            else:
                print("Available documents:")
                for doc in docs:
                    print(f"  - {doc}")
            return 0

        # Search for documents
        if args.search:
            results = reader.search_documents(args.page_title)
            if args.format == "json":
                print(json.dumps({"results": results}, indent=2))
            else:
                print(f"Search results for '{args.page_title}':")
                for result in results:
                    print(f"  - {result['title']}")
                    print(f"    Similarity: {result['similarity']:.2f}")
                    if 'doc_name_version' in result:
                        print(f"    Source: {result['doc_name_version']}")
            return 0

        # Multi-document extraction by titles
        if args.page_titles:
            titles = args.page_titles
            doc_set = None
            if isinstance(titles[0], dict):
                doc_set = titles[0].get("doc_set")
            if args.with_metadata:
                from doc4llm.tool.md_doc_retrieval import ExtractionResult
                result: ExtractionResult = reader._extractor.extract_by_titles_with_metadata(
                    titles=titles, threshold=args.threshold, doc_set=doc_set
                )
                output_metadata_result(result, args.format)
            else:
                contents = reader.extract_by_titles(titles)
                output_multi_contents(contents, args.format)
            return 0

        # Multi-section extraction (multiple documents with their associated headings)
        if args.sections:
            from doc4llm.tool.md_doc_retrieval import ExtractionResult
            result: ExtractionResult = reader.extract_multi_by_headings(
                sections=args.sections, threshold=args.threshold
            )
            output_multi_sections_result(result, args.format)
            return 0

        # Section extraction by headings
        if args.headings:
            sections = reader._extractor.extract_by_headings(
                page_title=args.page_title, headings=args.headings, doc_set=args.doc_set
            )
            if args.format == "json":
                print(json.dumps(sections, indent=2, ensure_ascii=False))
            else:
                for heading, content in sections.items():
                    print(f"=== {heading} ===")
                    print(content)
                    print()
            return 0

        # Single document extraction by title
        content = reader.extract_by_title(args.page_title)

        if content is None:
            print(f"No document found with title: '{args.page_title}'", file=sys.stderr)
            return 1
        elif content == "":
            print(
                f"Title does not match: '{args.page_title}'",
                file=sys.stderr,
            )
            return 1
        else:
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "title": args.page_title,
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
        print(f"Error: Could not import DocReaderAPI: {e}", file=sys.stderr)
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


def output_multi_sections_result(result, format_type: str):
    """Output multi-section extraction result with composite keys.

    The composite key format is "{title}::{heading}" for each section.
    """
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
                ensure_ascii=False,
            )
        )
    elif format_type == "summary":
        print(result.to_summary())
        # Also show section breakdown
        print("\nSection breakdown:")
        current_title = None
        for key, count in result.individual_counts.items():
            if "::" in key:
                title, heading = key.split("::", 1)
                if title != current_title:
                    print(f"\n  {title}:")
                    current_title = title
                print(f"     - {heading}: {count} lines")
            else:
                print(f"  - {key}: {count} lines")
    else:  # text
        print(f"=== Multi-Section Extraction Result ===")
        print(f"Total sections extracted: {result.document_count}")
        print(f"Total line count: {result.total_line_count}")
        print(f"Requires processing: {'Yes' if result.requires_processing else 'No'}")
        print(f"Threshold: {result.threshold}")
        print("\n--- Content ---\n")

        current_title = None
        for key, content in result.contents.items():
            if "::" in key:
                title, heading = key.split("::", 1)
                if title != current_title:
                    if current_title is not None:
                        print()  # Blank line between documents
                    print(f"## {title}")
                    print("=" * (len(title) + 3))
                    current_title = title
                print(f"\n### {heading}")
                print("-" * (len(heading) + 4))
                print()
            else:
                print(f"=== {key} ===")
            print(content)
            print()


if __name__ == "__main__":
    sys.exit(main())
