#!/usr/bin/env python3
"""
Check skill type and provide execution guidance.
"""
import sys
from pathlib import Path

def check_skill_type(skill_name: str) -> None:
    """Check skill type and provide execution guidance."""
    skill_path = Path(f".claude/skills/{skill_name}/SKILL.md")

    if not skill_path.exists():
        print(f"❌ Skill '{skill_name}' not found")
        print(f"   Expected: {skill_path}")
        sys.exit(1)

    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract frontmatter
    config = {}
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip().strip('"')

    skill_type = config.get('context', 'unknown')
    description = config.get('description', 'No description')

    print(f"✅ Skill: {skill_name}")
    print(f"   Type: {skill_type}")
    print(f"   Description: {description}")

    if skill_type == 'fork':
        print(f"   🔄 Execution: Prompt-based (use as template)")
        print(f"   ❌ Do NOT execute as script")
    elif skill_type == 'exec':
        print(f"   ⚡ Execution: Script-based")
        # Map skill names to their CLI paths
        cli_paths = {
            'md-doc-searcher': '.claude/skills/md-doc-searcher/scripts/doc_searcher_cli.py',
            'md-doc-reader': '.claude/skills/md-doc-reader/scripts/extract_md_doc.py',
        }
        if skill_name in cli_paths:
            print(f"   ✅ Use: python {cli_paths[skill_name]} [args]")
        else:
            print(f"   ⚠️  No CLI configured. Check skill documentation.")
    else:
        print(f"   ❓ Execution: Unknown type '{skill_type}'")

    # Check for common mistakes
    if skill_name == 'md-doc-query-optimizer' and skill_type == 'fork':
        print(f"   ⚠️  WARNING: This is a PROMPT-BASED skill")
        print(f"   ⚠️  Do NOT try to execute scripts/optimize_query.py")
        print(f"   ⚠️  Use the skill instructions as a prompt template")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: check-skill-type.py <skill_name>")
        sys.exit(1)

    skill_name = sys.argv[1]
    check_skill_type(skill_name)