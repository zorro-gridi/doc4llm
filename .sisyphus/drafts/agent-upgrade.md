# Draft: Upgrade Project-Level Agent to User-Level Agent

## Research Findings

### Claude Code Agent Hierarchy (4 Levels)
| Priority | Level | Location | Visibility |
|----------|-------|----------|------------|
| 1 (Highest) | CLI Temporary | Via `--agents` flag | Single session |
| 2 | Project-level | `.claude/agents/` | Current project, git-shareable |
| 3 | User-level | `~/.claude/agents/` | Cross-project, private |
| 4 (Lowest) | Plugin-level | Via MCP/extensions | Context-dependent |

### Key Differences
- **Project-level**: Stored in `.claude/agents/`, committed to git, shared with team
- **User-level**: Stored in `~/.claude/agents/`, private, available across all projects

### Migration Steps
1. **Locate**: `ls -la .claude/agents/doc-rag.md`
2. **Copy**: `mkdir -p ~/.claude/agents/ && cp .claude/agents/doc-rag.md ~/.claude/agents/`
3. **Verify**: Run `/agents` command to confirm migration
4. **Optional Cleanup**: Remove from project `rm .claude/agents/doc-rag.md && git rm .claude/agents/doc-rag.md`

### Important Notes
- Agent takes effect immediately (no restart needed)
- Uses `.md` extension with YAML frontmatter (name, description, tools, model)
- On name conflicts: Project-level takes precedence over user-level

### Documentation Sources
- Create custom subagents: https://code.claude.com/docs/en/sub-agents
- CLI reference: https://code.claude.com/docs/en/cli-reference
- Agent Skills: https://code.claude.com/docs/en/skills
