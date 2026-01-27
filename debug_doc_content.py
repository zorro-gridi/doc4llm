#!/usr/bin/env python3
"""Debug script to check docContent.md content."""

import os
import re

# Expand the home directory path
md_docs_base = os.path.expanduser("~/project/md_docs_base")
tools_path = os.path.join(md_docs_base, "OpenCode_Docs@latest", "Tools", "docContent.md")

print(f"Path: {tools_path}")
print(f"Exists: {os.path.exists(tools_path)}")

if os.path.exists(tools_path):
    with open(tools_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Show first 200 lines
    lines = content.split('\n')
    print(f"\nTotal lines: {len(lines)}")

    # Find lines containing "###" (heading level 3)
    print("\n--- All H3 headings (###) ---")
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('###'):
            print(f"{i}: {line.strip()}")

    # Find lines containing "skill"
    print("\n--- Lines containing 'skill' ---")
    for i, line in enumerate(lines, 1):
        if 'skill' in line.lower():
            print(f"{i}: {line[:120]}")
