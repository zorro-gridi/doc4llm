#!/usr/bin/env python3
"""
Unified skill dispatcher for Claude Code skills.

DEPRECATED: This script is deprecated. Use skill-specific CLIs directly:
- md-doc-searcher: python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py
- md-doc-reader: python .claude/skills/md-doc-reader/scripts/extract_md_doc.py

For pure prompt-based skills (md-doc-query-optimizer, md-doc-processor), use them through agent prompting, not script execution.
"""
import sys
from pathlib import Path

def main():
    print("DEPRECATED: skill-dispatcher.py is deprecated.", file=sys.stderr)
    print("Use skill-specific CLIs directly:", file=sys.stderr)
    print("", file=sys.stderr)
    print("  md-doc-searcher: python .claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py [args]", file=sys.stderr)
    print("  md-doc-reader: python .claude/skills/md-doc-reader/scripts/extract_md_doc.py [args]", file=sys.stderr)
    print("", file=sys.stderr)
    print("For prompt-based skills (md-doc-query-optimizer, md-doc-processor), use through agent prompting.", file=sys.stderr)
    sys.exit(1)

if __name__ == '__main__':
    main()
