#!/usr/bin/env python3
"""
Unified skill dispatcher for Claude Code skills.
Routes skill calls to appropriate handlers based on skill type.
"""
import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

def load_skill_config(skill_name: str) -> Optional[Dict[str, Any]]:
    """Load skill configuration from SKILL.md file."""
    skill_path = Path(f".claude/skills/{skill_name}/SKILL.md")
    if not skill_path.exists():
        return None
    
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1].strip()
            config = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    config[key.strip()] = value.strip().strip('"')
            return config
    
    return None

def dispatch_skill(skill_name: str, *args) -> None:
    """Dispatch skill call to appropriate handler."""
    config = load_skill_config(skill_name)
    if not config:
        print(f"Error: Skill '{skill_name}' not found", file=sys.stderr)
        sys.exit(1)
    
    skill_type = config.get('context', 'unknown')
    
    if skill_name == 'md-doc-query-optimizer':
        # This is a pure prompt-based skill, should not be called as script
        print("Error: md-doc-query-optimizer is a prompt-based skill", file=sys.stderr)
        print("Use the skill through agent prompting, not script execution", file=sys.stderr)
        sys.exit(2)
    
    elif skill_name == 'md-doc-searcher':
        # Call the actual Python implementation
        from doc4llm.tool.md_doc_retrieval import optimize_query
        query = ' '.join(args)
        results = optimize_query(query, debug_mode=True)
        for result in results:
            print(result)
    
    else:
        print(f"Error: Unknown skill type for '{skill_name}'", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: skill-dispatcher.py <skill_name> [args...]", file=sys.stderr)
        sys.exit(1)
    
    skill_name = sys.argv[1]
    args = sys.argv[2:]
    
    dispatch_skill(skill_name, *args)