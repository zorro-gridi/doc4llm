#!/usr/bin/env python3
"""
Markdown Document Extractor Script for md-doc-reader skill.

This script extracts content from markdown documents by title using the
MarkdownDocExtractor from doc4llm.tool.md_doc_extractor.

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

    args = parser.parse_args()

    # Validate arguments
    if not args.list and not args.title:
        parser.error("--title is required unless using --list")

    try:
        # Import the extractor
        from doc4llm.tool.md_doc_extractor import MarkdownDocExtractor

        # Create extractor from config or with parameters
        if args.config:
            extractor = MarkdownDocExtractor.from_config(args.config)
        elif args.file:
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
            if args.json:
                print(json.dumps({"documents": docs}, indent=2))
            else:
                print("Available documents:")
                for doc in docs:
                    print(f"  - {doc}")
            return 0

        # Search for documents
        if args.search:
            results = extractor.search_documents(args.title)
            if args.json:
                print(json.dumps({"results": results}, indent=2))
            else:
                print(f"Search results for '{args.title}':")
                for result in results:
                    print(f"  - {result['title']}")
                    print(f"    Similarity: {result['similarity']:.2f}")
                    print(f"    Source: {result['doc_name_version']}")
            return 0

        # Extract content by title
        content = extractor.extract_by_title(args.title)

        if content is None:
            print(f"No document found with title: '{args.title}'", file=sys.stderr)
            return 1
        elif content == "":
            print(f"Title does not match in single-file mode: '{args.title}'", file=sys.stderr)
            return 1
        else:
            if args.json:
                print(json.dumps({
                    "title": args.title,
                    "content": content,
                    "length": len(content),
                }, indent=2))
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


if __name__ == "__main__":
    sys.exit(main())
