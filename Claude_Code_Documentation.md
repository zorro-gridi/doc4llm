# Claude Code Complete Documentation

**Extracted on:** 2025-01-18

**Topics covered:** Agent Skills, Hooks, Slash Commands, MCP Servers, Settings, IDE Integrations, Keyboard Shortcuts, CLI Reference

---


================================================================================
# Agent Skills

# Agent Skills

> **原文链接**: https://code.claude.com/docs/en/skills

---

This guide shows you how to create, use, and manage Agent Skills in Claude Code. For background on how Skills work across Claude products, see [What are Skills?](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview). A Skill is a markdown file that teaches Claude how to do something specific: reviewing PRs using your team’s standards, generating commit messages in your preferred format, or querying your company’s database schema. When you ask Claude something that matches a Skill’s purpose, Claude automatically applies it.

## Create your first Skill

This example creates a personal Skill that teaches Claude to explain code using visual diagrams and analogies. Unlike Claude’s default explanations, this Skill ensures every explanation includes an ASCII diagram and a real-world analogy.

1

Check available Skills

Before creating a Skill, see what Skills Claude already has access to:
    
    
    What Skills are available?
    

Claude will list any Skills currently loaded. You may see none, or you may see Skills from plugins or your organization.

2

Create the Skill directory

Create a directory for the Skill in your personal Skills folder. Personal Skills are available across all your projects. (You can also create project Skills in `.claude/skills/` to share with your team.)
    
    
    mkdir -p ~/.claude/skills/explaining-code
    

3

Write SKILL.md

Every Skill needs a `SKILL.md` file. The file starts with YAML metadata between `---` markers and must include a `name` and `description`, followed by Markdown instructions that Claude follows when the Skill is active.The `description` is especially important, because Claude uses it to decide when to apply the Skill.Create `~/.claude/skills/explaining-code/SKILL.md`:


    
    
    ---
    name: explaining-code
    description: Explains code with visual diagrams and analogies. Use when explaining how code works, teaching about a codebase, or when the user asks "how does this work?"
    ---
    
    When explaining code, always include:
    
    1. **Start with an analogy**: Compare the code to something from everyday life
    2. **Draw a diagram**: Use ASCII art to show the flow, structure, or relationships
    3. **Walk through the code**: Explain step-by-step what happens
    4. **Highlight a gotcha**: What's a common mistake or misconception?
    
    Keep explanations conversational. For complex concepts, use multiple analogies.
    

4

Load and verify the Skill

Skills are automatically loaded when created or modified. Verify the Skill appears in the list:


    
    
    What Skills are available?
    

You should see `explaining-code` in the list with its description.

5

Test the Skill

Open any file in your project and ask Claude a question that matches the Skill’s description:


    
    
    How does this code work?
    

Claude should ask to use the `explaining-code` Skill, then include an analogy and ASCII diagram in its explanation. If the Skill doesn’t trigger, try rephrasing to include more keywords from the description, like “explain how this works.”

The rest of this guide covers how Skills work, configuration options, and troubleshooting.

## How Skills work

Skills are **model-invoked** : Claude decides which Skills to use based on your request. You don’t need to explicitly call a Skill. Claude automatically applies relevant Skills when your request matches their description. When you send a request, Claude follows these steps to find and use relevant Skills:

1

Discovery

At startup, Claude loads only the name and description of each available Skill. This keeps startup fast while giving Claude enough context to know when each Skill might be relevant.

2

Activation

When your request matches a Skill’s description, Claude asks to use the Skill. You’ll see a confirmation prompt before the full `SKILL.md` is loaded into context. Since Claude reads these descriptions to find relevant Skills, write descriptions that include keywords users would naturally say.

3

Execution

Claude follows the Skill’s instructions, loading referenced files or running bundled scripts as needed.

### Where Skills live

Where you store a Skill determines who can use it:

Location| Path| Applies to  
---|---|---  
Enterprise| See [managed settings](https://code.claude.com/docs/en/iam#managed-settings)| All users in your organization  
Personal| `~/.claude/skills/`| You, across all projects  
Project| `.claude/skills/`| Anyone working in this repository  
Plugin| Bundled with [plugins](https://code.claude.com/docs/en/plugins)| Anyone with the plugin installed  
  
If two Skills have the same name, the higher row wins: managed overrides personal, personal overrides project, and project overrides plugin.

#### Automatic discovery from nested directories

When you work with files in subdirectories, Claude Code automatically discovers Skills from nested `.claude/skills/` directories. For example, if you’re editing a file in `packages/frontend/`, Claude Code also looks for Skills in `packages/frontend/.claude/skills/`. This supports monorepo setups where packages have their own Skills.

### When to use Skills versus other options

Claude Code offers several ways to customize behavior. The key difference: **Skills are triggered automatically by Claude** based on your request, while slash commands require you to type `/command` explicitly.

Use this| When you want to…| When it runs  
---|---|---  
**Skills**|  Give Claude specialized knowledge (e.g., “review PRs using our standards”)| Claude chooses when relevant  
**[Slash commands](https://code.claude.com/docs/en/slash-commands)**|  Create reusable prompts (e.g., `/deploy staging`)| You type `/command` to run it  
**[CLAUDE.md](https://code.claude.com/docs/en/memory)**|  Set project-wide instructions (e.g., “use TypeScript strict mode”)| Loaded into every conversation  
**[Subagents](https://code.claude.com/docs/en/sub-agents)**|  Delegate tasks to a separate context with its own tools| Claude delegates, or you invoke explicitly  
**[Hooks](https://code.claude.com/docs/en/hooks)**|  Run scripts on events (e.g., lint on file save)| Fires on specific tool events  
**[MCP servers](https://code.claude.com/docs/en/mcp)**|  Connect Claude to external tools and data sources| Claude calls MCP tools as needed  
  
**Skills vs. subagents** : Skills add knowledge to the current conversation. Subagents run in a separate context with their own tools. Use Skills for guidance and standards; use subagents when you need isolation or different tool access. **Skills vs. MCP** : Skills tell Claude _how_ to use tools; MCP _provides_ the tools. For example, an MCP server connects Claude to your database, while a Skill teaches Claude your data model and query patterns.

For a deep dive into the architecture and real-world applications of Agent Skills, read [Equipping agents for the real world with Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills).

## Configure Skills

This section covers Skill file structure, supporting files, tool restrictions, and distribution options.

### Write SKILL.md

The `SKILL.md` file is the only required file in a Skill. It has two parts: YAML metadata (the section between `---` markers) at the top, and Markdown instructions that tell Claude how to use the Skill:


    
    
    ---
    name: your-skill-name
    description: Brief description of what this Skill does and when to use it
    ---
    
    # Your Skill Name
    
    ## Instructions
    Provide clear, step-by-step guidance for Claude.
    
    ## Examples
    Show concrete examples of using this Skill.
    

#### Available metadata fields

You can use the following fields in the YAML frontmatter:

Field| Required| Description  
---|---|---  
`name`| Yes| Skill name. Must use lowercase letters, numbers, and hyphens only (max 64 characters). Should match the directory name.  
`description`| Yes| What the Skill does and when to use it (max 1024 characters). Claude uses this to decide when to apply the Skill.  
`allowed-tools`| No| Tools Claude can use without asking permission when this Skill is active. Supports comma-separated values or YAML-style lists. See Restrict tool access.  
`model`| No| [Model](https://docs.claude.com/en/docs/about-claude/models/overview) to use when this Skill is active (e.g., `claude-sonnet-4-20250514`). Defaults to the conversation’s model.  
`context`| No| Set to `fork` to run the Skill in a forked sub-agent context with its own conversation history.  
`agent`| No| Specify which [agent type](https://code.claude.com/docs/en/sub-agents#built-in-subagents) to use when `context: fork` is set (e.g., `Explore`, `Plan`, `general-purpose`, or a custom agent name from `.claude/agents/`). Defaults to `general-purpose` if not specified. Only applicable when combined with `context: fork`.  
`hooks`| No| Define hooks scoped to this Skill’s lifecycle. Supports `PreToolUse`, `PostToolUse`, and `Stop` events.  
`user-invocable`| No| Controls whether the Skill appears in the slash command menu. Does not affect the [`Skill` tool](https://code.claude.com/docs/en/slash-commands#skill-tool) or automatic discovery. Defaults to `true`. See Control Skill visibility.  
  
#### Available string substitutions

Skills support string substitution for dynamic values in the Skill content:

Variable| Description  
---|---  
`$ARGUMENTS`| All arguments passed when invoking the Skill. If `$ARGUMENTS` is not present in the content, arguments are appended as `ARGUMENTS: <value>`.  
`${CLAUDE_SESSION_ID}`| The current session ID. Useful for logging, creating session-specific files, or correlating Skill output with sessions.  
  
**Example using substitutions:**


    
    
    ---
    name: session-logger
    description: Log activity for this session
    ---
    
    Log the following to logs/${CLAUDE_SESSION_ID}.log:
    
    $ARGUMENTS
    

See the [best practices guide](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices) for complete authoring guidance including validation rules.

### Update or delete a Skill

To update a Skill, edit its `SKILL.md` file directly. To remove a Skill, delete its directory. Changes take effect immediately.

### Add supporting files with progressive disclosure

Skills share Claude’s context window with conversation history, other Skills, and your request. To keep context focused, use **progressive disclosure** : put essential information in `SKILL.md` and detailed reference material in separate files that Claude reads only when needed. This approach lets you bundle comprehensive documentation, examples, and scripts without consuming context upfront. Claude loads additional files only when the task requires them.

Keep `SKILL.md` under 500 lines for optimal performance. If your content exceeds this, split detailed reference material into separate files.

#### Example: multi-file Skill structure

Claude discovers supporting files through links in your `SKILL.md`. The following example shows a Skill with detailed documentation in separate files and utility scripts that Claude can execute without reading:


    
    
    my-skill/
    ├── SKILL.md (required - overview and navigation)
    ├── reference.md (detailed API docs - loaded when needed)
    ├── examples.md (usage examples - loaded when needed)
    └── scripts/
        └── helper.py (utility script - executed, not loaded)
    

The `SKILL.md` file references these supporting files so Claude knows they exist:


    
    
    ## Overview
    
    [Essential instructions here]
    
    ## Additional resources
    
    - For complete API details, see [reference.md](reference.md)
    - For usage examples, see [examples.md](examples.md)
    
    ## Utility scripts
    
    To validate input files, run the helper script. It checks for required fields and returns any validation errors:
    ```bash
    python scripts/helper.py input.txt
    ```
    

Keep references one level deep. Link directly from `SKILL.md` to reference files. Deeply nested references (file A links to file B which links to file C) may result in Claude partially reading files.

**Bundle utility scripts for zero-context execution.** Scripts in your Skill directory can be executed without loading their contents into context. Claude runs the script and only the output consumes tokens. This is useful for:

  * Complex validation logic that would be verbose to describe in prose
  * Data processing that’s more reliable as tested code than generated code
  * Operations that benefit from consistency across uses

In `SKILL.md`, tell Claude to run the script rather than read it:


    
    
    Run the validation script to check the form:
    python scripts/validate_form.py input.pdf
    

For complete guidance on structuring Skills, see the [best practices guide](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/best-practices#progressive-disclosure-patterns).

### Restrict tool access with allowed-tools

Use the `allowed-tools` frontmatter field to limit which tools Claude can use when a Skill is active. You can specify tools as a comma-separated string or a YAML list:


    
    
    ---
    name: reading-files-safely
    description: Read files without making changes. Use when you need read-only file access.
    allowed-tools: Read, Grep, Glob
    ---
    

Or use YAML-style lists for better readability:


    
    
    ---
    name: reading-files-safely
    description: Read files without making changes. Use when you need read-only file access.
    allowed-tools:
      - Read
      - Grep
      - Glob
    ---
    

When this Skill is active, Claude can only use the specified tools (Read, Grep, Glob) without needing to ask for permission. This is useful for:

  * Read-only Skills that shouldn’t modify files
  * Skills with limited scope: for example, only data analysis, no file writing
  * Security-sensitive workflows where you want to restrict capabilities

If `allowed-tools` is omitted, the Skill doesn’t restrict tools. Claude uses its standard permission model and may ask you to approve tool usage.

`allowed-tools` is only supported for Skills in Claude Code.

### Run Skills in a forked context

Use `context: fork` to run a Skill in an isolated sub-agent context with its own conversation history. This is useful for Skills that perform complex multi-step operations without cluttering the main conversation:


    
    
    ---
    name: code-analysis
    description: Analyze code quality and generate detailed reports
    context: fork
    ---
    

### Define hooks for Skills

Skills can define hooks that run during the Skill’s lifecycle. Use the `hooks` field to specify `PreToolUse`, `PostToolUse`, or `Stop` handlers:


    
    
    ---
    name: secure-operations
    description: Perform operations with additional security checks
    hooks:
      PreToolUse:
        - matcher: "Bash"
          hooks:
            - type: command
              command: "./scripts/security-check.sh $TOOL_INPUT"
              once: true
    ---
    

The `once: true` option runs the hook only once per session. After the first successful execution, the hook is removed. Hooks defined in a Skill are scoped to that Skill’s execution and are automatically cleaned up when the Skill finishes. See [Hooks](https://code.claude.com/docs/en/hooks) for the complete hook configuration format.

### Control Skill visibility

Skills can be invoked in three ways:

  1. **Manual invocation** : You type `/skill-name` in the prompt
  2. **Programmatic invocation** : Claude calls it via the [`Skill` tool](https://code.claude.com/docs/en/slash-commands#skill-tool)
  3. **Automatic discovery** : Claude reads the Skill’s description and loads it when relevant to the conversation

The `user-invocable` field controls only manual invocation. When set to `false`, the Skill is hidden from the slash command menu but Claude can still invoke it programmatically or discover it automatically. To block programmatic invocation via the `Skill` tool, use `disable-model-invocation: true` instead.

#### When to use each setting

Setting| Slash menu| `Skill` tool| Auto-discovery| Use case  
---|---|---|---|---  
`user-invocable: true` (default)| Visible| Allowed| Yes| Skills you want users to invoke directly  
`user-invocable: false`| Hidden| Allowed| Yes| Skills that Claude can use but users shouldn’t invoke manually  
`disable-model-invocation: true`| Visible| Blocked| Yes| Skills you want users to invoke but not Claude programmatically  
  
#### Example: model-only Skill

Set `user-invocable: false` to hide a Skill from the slash menu while still allowing Claude to invoke it programmatically:


    
    
    ---
    name: internal-review-standards
    description: Apply internal code review standards when reviewing pull requests
    user-invocable: false
    ---
    

With this setting, users won’t see the Skill in the `/` menu, but Claude can still invoke it via the `Skill` tool or discover it automatically based on context.

### Skills and subagents

There are two ways Skills and subagents can work together:

#### Give a subagent access to Skills

[Subagents](https://code.claude.com/docs/en/sub-agents) do not automatically inherit Skills from the main conversation. To give a custom subagent access to specific Skills, list them in the subagent’s `skills` field:


    
    
    # .claude/agents/code-reviewer.md
    ---
    name: code-reviewer
    description: Review code for quality and best practices
    skills: pr-review, security-check
    ---
    

The full content of each listed Skill is injected into the subagent’s context at startup, not just made available for invocation. If the `skills` field is omitted, no Skills are loaded for that subagent.

Built-in agents (Explore, Plan, general-purpose) do not have access to your Skills. Only custom subagents you define in `.claude/agents/` with an explicit `skills` field can use Skills.

#### Run a Skill in a subagent context

Use `context: fork` and `agent` to run a Skill in a forked subagent with its own separate context. See Run Skills in a forked context for details.

### Distribute Skills

You can share Skills in several ways:

  * **Project Skills** : Commit `.claude/skills/` to version control. Anyone who clones the repository gets the Skills.
  * **Plugins** : To share Skills across multiple repositories, create a `skills/` directory in your [plugin](https://code.claude.com/docs/en/plugins) with Skill folders containing `SKILL.md` files. Distribute through a [plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces).
  * **Managed** : Administrators can deploy Skills organization-wide through [managed settings](https://code.claude.com/docs/en/iam#managed-settings). See Where Skills live for managed Skill paths.

## Examples

These examples show common Skill patterns, from minimal single-file Skills to multi-file Skills with supporting documentation and scripts.

### Simple Skill (single file)

A minimal Skill needs only a `SKILL.md` file with frontmatter and instructions. This example helps Claude generate commit messages by examining staged changes:


    
    
    commit-helper/
    └── SKILL.md
    


    
    
    ---
    name: generating-commit-messages
    description: Generates clear commit messages from git diffs. Use when writing commit messages or reviewing staged changes.
    ---
    
    # Generating Commit Messages
    
    ## Instructions
    
    1. Run `git diff --staged` to see changes
    2. I'll suggest a commit message with:
       - Summary under 50 characters
       - Detailed description
       - Affected components
    
    ## Best practices
    
    - Use present tense
    - Explain what and why, not how
    

### Use multiple files

For complex Skills, use progressive disclosure to keep the main `SKILL.md` focused while providing detailed documentation in supporting files. This PDF processing Skill includes reference docs, utility scripts, and uses `allowed-tools` to restrict Claude to specific tools:


    
    
    pdf-processing/
    ├── SKILL.md              # Overview and quick start
    ├── FORMS.md              # Form field mappings and filling instructions
    ├── REFERENCE.md          # API details for pypdf and pdfplumber
    └── scripts/
        ├── fill_form.py      # Utility to populate form fields
        └── validate.py       # Checks PDFs for required fields
    

**`SKILL.md`** :


    
    
    ---
    name: pdf-processing
    description: Extract text, fill forms, merge PDFs. Use when working with PDF files, forms, or document extraction. Requires pypdf and pdfplumber packages.
    allowed-tools: Read, Bash(python:*)
    ---
    
    # PDF Processing
    
    ## Quick start
    
    Extract text:
    ```python
    import pdfplumber
    with pdfplumber.open("doc.pdf") as pdf:
        text = pdf.pages[0].extract_text()
    ```
    
    For form filling, see [FORMS.md](FORMS.md).
    For detailed API reference, see [REFERENCE.md](REFERENCE.md).
    
    ## Requirements
    
    Packages must be installed in your environment:
    ```bash
    pip install pypdf pdfplumber
    ```
    

If your Skill requires external packages, list them in the description. Packages must be installed in your environment before Claude can use them.

## Troubleshooting

### View and test Skills

To see which Skills Claude has access to, ask Claude a question like “What Skills are available?” Claude loads all available Skill names and descriptions into the context window when a conversation starts, so it can list the Skills it currently has access to. To test a specific Skill, ask Claude to do a task that matches the Skill’s description. For example, if your Skill has the description “Reviews pull requests for code quality”, ask Claude to “Review the changes in my current branch.” Claude automatically uses the Skill when the request matches its description.

### Skill not triggering

The description field is how Claude decides whether to use your Skill. Vague descriptions like “Helps with documents” don’t give Claude enough information to match your Skill to relevant requests. A good description answers two questions:

  1. **What does this Skill do?** List the specific capabilities.
  2. **When should Claude use it?** Include trigger terms users would mention.


    
    
    description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
    

This description works because it names specific actions (extract, fill, merge) and includes keywords users would say (PDF, forms, document extraction).

### Skill doesn’t load

**Check the file path.** Skills must be in the correct directory with the exact filename `SKILL.md` (case-sensitive):

Type| Path  
---|---  
Personal| `~/.claude/skills/my-skill/SKILL.md`  
Project| `.claude/skills/my-skill/SKILL.md`  
Enterprise| See Where Skills live for platform-specific paths  
Plugin| `skills/my-skill/SKILL.md` inside the plugin directory  
  
**Check the YAML syntax.** Invalid YAML in the frontmatter prevents the Skill from loading. The frontmatter must start with `---` on line 1 (no blank lines before it), end with `---` before the Markdown content, and use spaces for indentation (not tabs). **Run debug mode.** Use `claude --debug` to see Skill loading errors.

### Skill has errors

**Check dependencies are installed.** If your Skill uses external packages, they must be installed in your environment before Claude can use them. **Check script permissions.** Scripts need execute permissions: `chmod +x scripts/*.py` **Check file paths.** Use forward slashes (Unix style) in all paths. Use `scripts/helper.py`, not `scripts\helper.py`.

### Multiple Skills conflict

If Claude uses the wrong Skill or seems confused between similar Skills, the descriptions are probably too similar. Make each description distinct by using specific trigger terms. For example, instead of two Skills with “data analysis” in both descriptions, differentiate them: one for “sales data in Excel files and CRM exports” and another for “log files and system metrics”. The more specific your trigger terms, the easier it is for Claude to match the right Skill to your request.

### Plugin Skills not appearing

**Symptom** : You installed a plugin from a marketplace, but its Skills don’t appear when you ask Claude “What Skills are available?” **Solution** : Clear the plugin cache and reinstall:


    
    
    rm -rf ~/.claude/plugins/cache
    

Then restart Claude Code and reinstall the plugin:


    
    
    /plugin install plugin-name@marketplace-name
    

This forces Claude Code to re-download and re-register the plugin’s Skills. **If Skills still don’t appear** , verify the plugin’s directory structure is correct. Skills must be in a `skills/` directory at the plugin root:


    
    
    my-plugin/
    ├── .claude-plugin/
    │   └── plugin.json
    └── skills/
        └── my-skill/
            └── SKILL.md
    



================================================================================
# Hooks reference

# Hooks reference

> **原文链接**: https://code.claude.com/docs/en/hooks

---

For a quickstart guide with examples, see [Get started with Claude Code hooks](https://code.claude.com/docs/en/hooks-guide).

## Configuration

Claude Code hooks are configured in your [settings files](https://code.claude.com/docs/en/settings):

  * `~/.claude/settings.json` \- User settings
  * `.claude/settings.json` \- Project settings
  * `.claude/settings.local.json` \- Local project settings (not committed)
  * Managed policy settings

Enterprise administrators can use `allowManagedHooksOnly` to block user, project, and plugin hooks. See [Hook configuration](https://code.claude.com/docs/en/settings#hook-configuration).

### Structure

Hooks are organized by matchers, where each matcher can have multiple hooks:
    
    
    {
      "hooks": {
        "EventName": [
          {
            "matcher": "ToolPattern",
            "hooks": [
              {
                "type": "command",
                "command": "your-command-here"
              }
            ]
          }
        ]
      }
    }
    

  * **matcher** : Pattern to match tool names, case-sensitive (only applicable for `PreToolUse`, `PermissionRequest`, and `PostToolUse`)
    * Simple strings match exactly: `Write` matches only the Write tool
    * Supports regex: `Edit|Write` or `Notebook.*`
    * Use `*` to match all tools. You can also use empty string (`""`) or leave `matcher` blank.
  * **hooks** : Array of hooks to execute when the pattern matches
    * `type`: Hook execution type - `"command"` for bash commands or `"prompt"` for LLM-based evaluation
    * `command`: (For `type: "command"`) The bash command to execute (can use `$CLAUDE_PROJECT_DIR` environment variable)
    * `prompt`: (For `type: "prompt"`) The prompt to send to the LLM for evaluation
    * `timeout`: (Optional) How long a hook should run, in seconds, before canceling that specific hook

For events like `UserPromptSubmit`, `Stop`, and `SubagentStop` that don’t use matchers, you can omit the matcher field:
    
    
    {
      "hooks": {
        "UserPromptSubmit": [
          {
            "hooks": [
              {
                "type": "command",
                "command": "/path/to/prompt-validator.py"
              }
            ]
          }
        ]
      }
    }
    

### Project-Specific Hook Scripts

You can use the environment variable `CLAUDE_PROJECT_DIR` (only available when Claude Code spawns the hook command) to reference scripts stored in your project, ensuring they work regardless of Claude’s current directory:


    
    
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Write|Edit",
            "hooks": [
              {
                "type": "command",
                "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/check-style.sh"
              }
            ]
          }
        ]
      }
    }
    

### Plugin hooks

[Plugins](https://code.claude.com/docs/en/plugins) can provide hooks that integrate seamlessly with your user and project hooks. Plugin hooks are automatically merged with your configuration when plugins are enabled. **How plugin hooks work** :

  * Plugin hooks are defined in the plugin’s `hooks/hooks.json` file or in a file given by a custom path to the `hooks` field.
  * When a plugin is enabled, its hooks are merged with user and project hooks
  * Multiple hooks from different sources can respond to the same event
  * Plugin hooks use the `${CLAUDE_PLUGIN_ROOT}` environment variable to reference plugin files

**Example plugin hook configuration** :


    
    
    {
      "description": "Automatic code formatting",
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Write|Edit",
            "hooks": [
              {
                "type": "command",
                "command": "${CLAUDE_PLUGIN_ROOT}/scripts/format.sh",
                "timeout": 30
              }
            ]
          }
        ]
      }
    }
    

Plugin hooks use the same format as regular hooks with an optional `description` field to explain the hook’s purpose.

Plugin hooks run alongside your custom hooks. If multiple hooks match an event, they all execute in parallel.

**Environment variables for plugins** :

  * `${CLAUDE_PLUGIN_ROOT}`: Absolute path to the plugin directory
  * `${CLAUDE_PROJECT_DIR}`: Project root directory (same as for project hooks)
  * All standard environment variables are available

See the [plugin components reference](https://code.claude.com/docs/en/plugins-reference#hooks) for details on creating plugin hooks.

### Hooks in Skills, Agents, and Slash Commands

In addition to settings files and plugins, hooks can be defined directly in [Skills](https://code.claude.com/docs/en/skills), [subagents](https://code.claude.com/docs/en/sub-agents), and [slash commands](https://code.claude.com/docs/en/slash-commands) using frontmatter. These hooks are scoped to the component’s lifecycle and only run when that component is active. **Supported events** : `PreToolUse`, `PostToolUse`, and `Stop` **Example in a Skill** :


    
    
    ---
    name: secure-operations
    description: Perform operations with security checks
    hooks:
      PreToolUse:
        - matcher: "Bash"
          hooks:
            - type: command
              command: "./scripts/security-check.sh"
    ---
    

**Example in an agent** :


    
    
    ---
    name: code-reviewer
    description: Review code changes
    hooks:
      PostToolUse:
        - matcher: "Edit|Write"
          hooks:
            - type: command
              command: "./scripts/run-linter.sh"
    ---
    

Component-scoped hooks follow the same configuration format as settings-based hooks but are automatically cleaned up when the component finishes executing. **Additional option for skills and slash commands:**

  * `once`: Set to `true` to run the hook only once per session. After the first successful execution, the hook is removed. Note: This option is currently only supported for skills and slash commands, not for agents.

## Prompt-Based Hooks

In addition to bash command hooks (`type: "command"`), Claude Code supports prompt-based hooks (`type: "prompt"`) that use an LLM to evaluate whether to allow or block an action. Prompt-based hooks are currently only supported for `Stop` and `SubagentStop` hooks, where they enable intelligent, context-aware decisions.

### How prompt-based hooks work

Instead of executing a bash command, prompt-based hooks:

  1. Send the hook input and your prompt to a fast LLM (Haiku)
  2. The LLM responds with structured JSON containing a decision
  3. Claude Code processes the decision automatically

### Configuration


    
    
    {
      "hooks": {
        "Stop": [
          {
            "hooks": [
              {
                "type": "prompt",
                "prompt": "Evaluate if Claude should stop: $ARGUMENTS. Check if all tasks are complete."
              }
            ]
          }
        ]
      }
    }
    

**Fields:**

  * `type`: Must be `"prompt"`
  * `prompt`: The prompt text to send to the LLM
    * Use `$ARGUMENTS` as a placeholder for the hook input JSON
    * If `$ARGUMENTS` is not present, input JSON is appended to the prompt
  * `timeout`: (Optional) Timeout in seconds (default: 30 seconds)

### Response schema

The LLM must respond with JSON containing:


    
    
    {
      "ok": true | false,
      "reason": "Explanation for the decision"
    }
    

**Response fields:**

  * `ok`: `true` allows the action, `false` prevents it
  * `reason`: Required when `ok` is `false`. Explanation shown to Claude

### Supported hook events

Prompt-based hooks work with any hook event, but are most useful for:

  * **Stop** : Intelligently decide if Claude should continue working
  * **SubagentStop** : Evaluate if a subagent has completed its task
  * **UserPromptSubmit** : Validate user prompts with LLM assistance
  * **PreToolUse** : Make context-aware permission decisions
  * **PermissionRequest** : Intelligently allow or deny permission dialogs

### Example: Intelligent Stop hook


    
    
    {
      "hooks": {
        "Stop": [
          {
            "hooks": [
              {
                "type": "prompt",
                "prompt": "You are evaluating whether Claude should stop working. Context: $ARGUMENTS\n\nAnalyze the conversation and determine if:\n1. All user-requested tasks are complete\n2. Any errors need to be addressed\n3. Follow-up work is needed\n\nRespond with JSON: {\"ok\": true} to allow stopping, or {\"ok\": false, \"reason\": \"your explanation\"} to continue working.",
                "timeout": 30
              }
            ]
          }
        ]
      }
    }
    

### Example: SubagentStop with custom logic


    
    
    {
      "hooks": {
        "SubagentStop": [
          {
            "hooks": [
              {
                "type": "prompt",
                "prompt": "Evaluate if this subagent should stop. Input: $ARGUMENTS\n\nCheck if:\n- The subagent completed its assigned task\n- Any errors occurred that need fixing\n- Additional context gathering is needed\n\nReturn: {\"ok\": true} to allow stopping, or {\"ok\": false, \"reason\": \"explanation\"} to continue."
              }
            ]
          }
        ]
      }
    }
    

### Comparison with bash command hooks

Feature| Bash Command Hooks| Prompt-Based Hooks  
---|---|---  
**Execution**|  Runs bash script| Queries LLM  
**Decision logic**|  You implement in code| LLM evaluates context  
**Setup complexity**|  Requires script file| Configure prompt  
**Context awareness**|  Limited to script logic| Natural language understanding  
**Performance**|  Fast (local execution)| Slower (API call)  
**Use case**|  Deterministic rules| Context-aware decisions  
  
### Best practices

  * **Be specific in prompts** : Clearly state what you want the LLM to evaluate
  * **Include decision criteria** : List the factors the LLM should consider
  * **Test your prompts** : Verify the LLM makes correct decisions for your use cases
  * **Set appropriate timeouts** : Default is 30 seconds, adjust if needed
  * **Use for complex decisions** : Bash hooks are better for simple, deterministic rules

See the [plugin components reference](https://code.claude.com/docs/en/plugins-reference#hooks) for details on creating plugin hooks.

## Hook Events

### PreToolUse

Runs after Claude creates tool parameters and before processing the tool call. **Common matchers:**

  * `Task` \- Subagent tasks (see [subagents documentation](https://code.claude.com/docs/en/sub-agents))
  * `Bash` \- Shell commands
  * `Glob` \- File pattern matching
  * `Grep` \- Content search
  * `Read` \- File reading
  * `Edit` \- File editing
  * `Write` \- File writing
  * `WebFetch`, `WebSearch` \- Web operations

Use PreToolUse decision control to allow, deny, or ask for permission to use the tool.

### PermissionRequest

Runs when the user is shown a permission dialog. Use PermissionRequest decision control to allow or deny on behalf of the user. Recognizes the same matcher values as PreToolUse.

### PostToolUse

Runs immediately after a tool completes successfully. Recognizes the same matcher values as PreToolUse. Runs when Claude Code sends notifications. Supports matchers to filter by notification type. **Common matchers:**

  * `permission_prompt` \- Permission requests from Claude Code
  * `idle_prompt` \- When Claude is waiting for user input (after 60+ seconds of idle time)
  * `auth_success` \- Authentication success notifications
  * `elicitation_dialog` \- When Claude Code needs input for MCP tool elicitation

You can use matchers to run different hooks for different notification types, or omit the matcher to run hooks for all notifications. **Example: Different notifications for different types**


    
    
    {
      "hooks": {
        "Notification": [
          {
            "matcher": "permission_prompt",
            "hooks": [
              {
                "type": "command",
                "command": "/path/to/permission-alert.sh"
              }
            ]
          },
          {
            "matcher": "idle_prompt",
            "hooks": [
              {
                "type": "command",
                "command": "/path/to/idle-notification.sh"
              }
            ]
          }
        ]
      }
    }
    

### UserPromptSubmit

Runs when the user submits a prompt, before Claude processes it. This allows you to add additional context based on the prompt/conversation, validate prompts, or block certain types of prompts.

### Stop

Runs when the main Claude Code agent has finished responding. Does not run if the stoppage occurred due to a user interrupt.

### SubagentStop

Runs when a Claude Code subagent (Task tool call) has finished responding.

### PreCompact

Runs before Claude Code is about to run a compact operation. **Matchers:**

  * `manual` \- Invoked from `/compact`
  * `auto` \- Invoked from auto-compact (due to full context window)

### SessionStart

Runs when Claude Code starts a new session or resumes an existing session (which currently does start a new session under the hood). Useful for loading in development context like existing issues or recent changes to your codebase, installing dependencies, or setting up environment variables. **Matchers:**

  * `startup` \- Invoked from startup
  * `resume` \- Invoked from `--resume`, `--continue`, or `/resume`
  * `clear` \- Invoked from `/clear`
  * `compact` \- Invoked from auto or manual compact.

#### Persisting environment variables

SessionStart hooks have access to the `CLAUDE_ENV_FILE` environment variable, which provides a file path where you can persist environment variables for subsequent bash commands. **Example: Setting individual environment variables**


    
    
    #!/bin/bash
    
    if [ -n "$CLAUDE_ENV_FILE" ]; then
      echo 'export NODE_ENV=production' >> "$CLAUDE_ENV_FILE"
      echo 'export API_KEY=your-api-key' >> "$CLAUDE_ENV_FILE"
      echo 'export PATH="$PATH:./node_modules/.bin"' >> "$CLAUDE_ENV_FILE"
    fi
    
    exit 0
    

**Example: Persisting all environment changes from the hook** When your setup modifies the environment (for example, `nvm use`), capture and persist all changes by diffing the environment:


    
    
    #!/bin/bash
    
    ENV_BEFORE=$(export -p | sort)
    
    # Run your setup commands that modify the environment
    source ~/.nvm/nvm.sh
    nvm use 20
    
    if [ -n "$CLAUDE_ENV_FILE" ]; then
      ENV_AFTER=$(export -p | sort)
      comm -13 <(echo "$ENV_BEFORE") <(echo "$ENV_AFTER") >> "$CLAUDE_ENV_FILE"
    fi
    
    exit 0
    

Any variables written to this file will be available in all subsequent bash commands that Claude Code executes during the session.

`CLAUDE_ENV_FILE` is only available for SessionStart hooks. Other hook types do not have access to this variable.

### SessionEnd

Runs when a Claude Code session ends. Useful for cleanup tasks, logging session statistics, or saving session state. The `reason` field in the hook input will be one of:

  * `clear` \- Session cleared with /clear command
  * `logout` \- User logged out
  * `prompt_input_exit` \- User exited while prompt input was visible
  * `other` \- Other exit reasons

## Hook Input

Hooks receive JSON data via stdin containing session information and event-specific data:


    
    
    {
      // Common fields
      session_id: string
      transcript_path: string  // Path to conversation JSON
      cwd: string              // The current working directory when the hook is invoked
      permission_mode: string  // Current permission mode: "default", "plan", "acceptEdits", "dontAsk", or "bypassPermissions"
    
      // Event-specific fields
      hook_event_name: string
      ...
    }
    

### PreToolUse Input

The exact schema for `tool_input` depends on the tool. Here are examples for commonly hooked tools.

#### Bash tool

The Bash tool is the most commonly hooked tool for command validation:


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "PreToolUse",
      "tool_name": "Bash",
      "tool_input": {
        "command": "psql -c 'SELECT * FROM users'",
        "description": "Query the users table",
        "timeout": 120000
      },
      "tool_use_id": "toolu_01ABC123..."
    }
    

Field| Type| Description  
---|---|---  
`command`| string| The shell command to execute  
`description`| string| Optional description of what the command does  
`timeout`| number| Optional timeout in milliseconds  
`run_in_background`| boolean| Whether to run the command in background  
  
#### Write tool


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "PreToolUse",
      "tool_name": "Write",
      "tool_input": {
        "file_path": "/path/to/file.txt",
        "content": "file content"
      },
      "tool_use_id": "toolu_01ABC123..."
    }
    

Field| Type| Description  
---|---|---  
`file_path`| string| Absolute path to the file to write  
`content`| string| Content to write to the file  
  
#### Edit tool


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "PreToolUse",
      "tool_name": "Edit",
      "tool_input": {
        "file_path": "/path/to/file.txt",
        "old_string": "original text",
        "new_string": "replacement text"
      },
      "tool_use_id": "toolu_01ABC123..."
    }
    

Field| Type| Description  
---|---|---  
`file_path`| string| Absolute path to the file to edit  
`old_string`| string| Text to find and replace  
`new_string`| string| Replacement text  
`replace_all`| boolean| Whether to replace all occurrences (default: false)  
  
#### Read tool


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "PreToolUse",
      "tool_name": "Read",
      "tool_input": {
        "file_path": "/path/to/file.txt"
      },
      "tool_use_id": "toolu_01ABC123..."
    }
    

Field| Type| Description  
---|---|---  
`file_path`| string| Absolute path to the file to read  
`offset`| number| Optional line number to start reading from  
`limit`| number| Optional number of lines to read  
  
### PostToolUse Input

The exact schema for `tool_input` and `tool_response` depends on the tool.


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "PostToolUse",
      "tool_name": "Write",
      "tool_input": {
        "file_path": "/path/to/file.txt",
        "content": "file content"
      },
      "tool_response": {
        "filePath": "/path/to/file.txt",
        "success": true
      },
      "tool_use_id": "toolu_01ABC123..."
    }
    


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "Notification",
      "message": "Claude needs your permission to use Bash",
      "notification_type": "permission_prompt"
    }
    

### UserPromptSubmit Input


    
    
    {
      "session_id": "abc123",
      "transcript_path": "/Users/.../.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "UserPromptSubmit",
      "prompt": "Write a function to calculate the factorial of a number"
    }
    

### Stop and SubagentStop Input

`stop_hook_active` is true when Claude Code is already continuing as a result of a stop hook. Check this value or process the transcript to prevent Claude Code from running indefinitely.


    
    
    {
      "session_id": "abc123",
      "transcript_path": "~/.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "permission_mode": "default",
      "hook_event_name": "Stop",
      "stop_hook_active": true
    }
    

### PreCompact Input

For `manual`, `custom_instructions` comes from what the user passes into `/compact`. For `auto`, `custom_instructions` is empty.


    
    
    {
      "session_id": "abc123",
      "transcript_path": "~/.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "permission_mode": "default",
      "hook_event_name": "PreCompact",
      "trigger": "manual",
      "custom_instructions": ""
    }
    

### SessionStart Input


    
    
    {
      "session_id": "abc123",
      "transcript_path": "~/.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "permission_mode": "default",
      "hook_event_name": "SessionStart",
      "source": "startup"
    }
    

### SessionEnd Input


    
    
    {
      "session_id": "abc123",
      "transcript_path": "~/.claude/projects/.../00893aaf-19fa-41d2-8238-13269b9b3ca0.jsonl",
      "cwd": "/Users/...",
      "permission_mode": "default",
      "hook_event_name": "SessionEnd",
      "reason": "exit"
    }
    

## Hook Output

There are two mutually exclusive ways for hooks to return output back to Claude Code. The output communicates whether to block and any feedback that should be shown to Claude and the user.

### Simple: Exit Code

Hooks communicate status through exit codes, stdout, and stderr:

  * **Exit code 0** : Success. `stdout` is shown to the user in verbose mode (ctrl+o), except for `UserPromptSubmit` and `SessionStart`, where stdout is added to the context. JSON output in `stdout` is parsed for structured control (see Advanced: JSON Output).
  * **Exit code 2** : Blocking error. Only `stderr` is used as the error message and fed back to Claude. The format is `[command]: {stderr}`. JSON in `stdout` is **not** processed for exit code 2. See per-hook-event behavior below.
  * **Other exit codes** : Non-blocking error. `stderr` is shown to the user in verbose mode (ctrl+o) with format `Failed with non-blocking status code: {stderr}`. If `stderr` is empty, it shows `No stderr output`. Execution continues.

Reminder: Claude Code does not see stdout if the exit code is 0, except for the `UserPromptSubmit` hook where stdout is injected as context.

#### Exit Code 2 Behavior

Hook Event| Behavior  
---|---  
`PreToolUse`| Blocks the tool call, shows stderr to Claude  
`PermissionRequest`| Denies the permission, shows stderr to Claude  
`PostToolUse`| Shows stderr to Claude (tool already ran)  
`Notification`| N/A, shows stderr to user only  
`UserPromptSubmit`| Blocks prompt processing, erases prompt, shows stderr to user only  
`Stop`| Blocks stoppage, shows stderr to Claude  
`SubagentStop`| Blocks stoppage, shows stderr to Claude subagent  
`PreCompact`| N/A, shows stderr to user only  
`SessionStart`| N/A, shows stderr to user only  
`SessionEnd`| N/A, shows stderr to user only  
  
### Advanced: JSON Output

Hooks can return structured JSON in `stdout` for more sophisticated control.

JSON output is only processed when the hook exits with code 0. If your hook exits with code 2 (blocking error), `stderr` text is used directly—any JSON in `stdout` is ignored. For other non-zero exit codes, only `stderr` is shown to the user in verbose mode (ctrl+o).

#### Common JSON Fields

All hook types can include these optional fields:


    
    
    {
      "continue": true, // Whether Claude should continue after hook execution (default: true)
      "stopReason": "string", // Message shown when continue is false
    
      "suppressOutput": true, // Hide stdout from transcript mode (default: false)
      "systemMessage": "string" // Optional warning message shown to the user
    }
    

If `continue` is false, Claude stops processing after the hooks run.

  * For `PreToolUse`, this is different from `"permissionDecision": "deny"`, which only blocks a specific tool call and provides automatic feedback to Claude.
  * For `PostToolUse`, this is different from `"decision": "block"`, which provides automated feedback to Claude.
  * For `UserPromptSubmit`, this prevents the prompt from being processed.
  * For `Stop` and `SubagentStop`, this takes precedence over any `"decision": "block"` output.
  * In all cases, `"continue" = false` takes precedence over any `"decision": "block"` output.

`stopReason` accompanies `continue` with a reason shown to the user, not shown to Claude.

#### `PreToolUse` Decision Control

`PreToolUse` hooks can control whether a tool call proceeds.

  * `"allow"` bypasses the permission system. `permissionDecisionReason` is shown to the user but not to Claude.
  * `"deny"` prevents the tool call from executing. `permissionDecisionReason` is shown to Claude.
  * `"ask"` asks the user to confirm the tool call in the UI. `permissionDecisionReason` is shown to the user but not to Claude.

Additionally, hooks can modify tool inputs before execution using `updatedInput`:

  * `updatedInput` modifies the tool’s input parameters before the tool executes
  * Combine with `"permissionDecision": "allow"` to modify the input and auto-approve the tool call
  * Combine with `"permissionDecision": "ask"` to modify the input and show it to the user for confirmation

Hooks can also provide context to Claude using `additionalContext`:

  * `"hookSpecificOutput.additionalContext"` adds a string to Claude’s context before the tool executes.


    
    
    {
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": "My reason here",
        "updatedInput": {
          "field_to_modify": "new value"
        },
        "additionalContext": "Current environment: production. Proceed with caution."
      }
    }
    

The `decision` and `reason` fields are deprecated for PreToolUse hooks. Use `hookSpecificOutput.permissionDecision` and `hookSpecificOutput.permissionDecisionReason` instead. The deprecated fields `"approve"` and `"block"` map to `"allow"` and `"deny"` respectively.

#### `PermissionRequest` Decision Control

`PermissionRequest` hooks can allow or deny permission requests shown to the user.

  * For `"behavior": "allow"` you can also optionally pass in an `"updatedInput"` that modifies the tool’s input parameters before the tool executes.
  * For `"behavior": "deny"` you can also optionally pass in a `"message"` string that tells the model why the permission was denied, and a boolean `"interrupt"` which will stop Claude.


    
    
    {
      "hookSpecificOutput": {
        "hookEventName": "PermissionRequest",
        "decision": {
          "behavior": "allow",
          "updatedInput": {
            "command": "npm run lint"
          }
        }
      }
    }
    

#### `PostToolUse` Decision Control

`PostToolUse` hooks can provide feedback to Claude after tool execution.

  * `"block"` automatically prompts Claude with `reason`.
  * `undefined` does nothing. `reason` is ignored.
  * `"hookSpecificOutput.additionalContext"` adds context for Claude to consider.


    
    
    {
      "decision": "block" | undefined,
      "reason": "Explanation for decision",
      "hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": "Additional information for Claude"
      }
    }
    

#### `UserPromptSubmit` Decision Control

`UserPromptSubmit` hooks can control whether a user prompt is processed and add context. **Adding context (exit code 0):** There are two ways to add context to the conversation:

  1. **Plain text stdout** (simpler): Any non-JSON text written to stdout is added as context. This is the easiest way to inject information.
  2. **JSON with`additionalContext`** (structured): Use the JSON format below for more control. The `additionalContext` field is added as context.

Both methods work with exit code 0. Plain stdout is shown as hook output in the transcript; `additionalContext` is added more discretely. **Blocking prompts:**

  * `"decision": "block"` prevents the prompt from being processed. The submitted prompt is erased from context. `"reason"` is shown to the user but not added to context.
  * `"decision": undefined` (or omitted) allows the prompt to proceed normally.


    
    
    {
      "decision": "block" | undefined,
      "reason": "Explanation for decision",
      "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": "My additional context here"
      }
    }
    

The JSON format isn’t required for simple use cases. To add context, you can print plain text to stdout with exit code 0. Use JSON when you need to block prompts or want more structured control.

#### `Stop`/`SubagentStop` Decision Control

`Stop` and `SubagentStop` hooks can control whether Claude must continue.

  * `"block"` prevents Claude from stopping. You must populate `reason` for Claude to know how to proceed.
  * `undefined` allows Claude to stop. `reason` is ignored.


    
    
    {
      "decision": "block" | undefined,
      "reason": "Must be provided when Claude is blocked from stopping"
    }
    

#### `SessionStart` Decision Control

`SessionStart` hooks allow you to load in context at the start of a session.

  * `"hookSpecificOutput.additionalContext"` adds the string to the context.
  * Multiple hooks’ `additionalContext` values are concatenated.


    
    
    {
      "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": "My additional context here"
      }
    }
    

#### `SessionEnd` Decision Control

`SessionEnd` hooks run when a session ends. They cannot block session termination but can perform cleanup tasks.

#### Exit Code Example: Bash Command Validation



#### JSON Output Example: UserPromptSubmit to Add Context and Validation

For `UserPromptSubmit` hooks, you can inject context using either method:

  * **Plain text stdout** with exit code 0: Simplest approach, prints text
  * **JSON output** with exit code 0: Use `"decision": "block"` to reject prompts, or `additionalContext` for structured context injection

Remember: Exit code 2 only uses `stderr` for the error message. To block using JSON (with a custom reason), use `"decision": "block"` with exit code 0.



#### JSON Output Example: PreToolUse with Approval



## Working with MCP Tools

Claude Code hooks work seamlessly with [Model Context Protocol (MCP) tools](https://code.claude.com/docs/en/mcp). When MCP servers provide tools, they appear with a special naming pattern that you can match in your hooks.

### MCP Tool Naming

MCP tools follow the pattern `mcp__<server>__<tool>`, for example:

  * `mcp__memory__create_entities` \- Memory server’s create entities tool
  * `mcp__filesystem__read_file` \- Filesystem server’s read file tool
  * `mcp__github__search_repositories` \- GitHub server’s search tool

### Configuring Hooks for MCP Tools

You can target specific MCP tools or entire MCP servers:


    
    
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "mcp__memory__.*",
            "hooks": [
              {
                "type": "command",
                "command": "echo 'Memory operation initiated' >> ~/mcp-operations.log"
              }
            ]
          },
          {
            "matcher": "mcp__.*__write.*",
            "hooks": [
              {
                "type": "command",
                "command": "/home/user/scripts/validate-mcp-write.py"
              }
            ]
          }
        ]
      }
    }
    

## Examples

For practical examples including code formatting, notifications, and file protection, see [More Examples](https://code.claude.com/docs/en/hooks-guide#more-examples) in the get started guide.

## Security Considerations

### Disclaimer

**USE AT YOUR OWN RISK** : Claude Code hooks execute arbitrary shell commands on your system automatically. By using hooks, you acknowledge that:

  * You are solely responsible for the commands you configure
  * Hooks can modify, delete, or access any files your user account can access
  * Malicious or poorly written hooks can cause data loss or system damage
  * Anthropic provides no warranty and assumes no liability for any damages resulting from hook usage
  * You should thoroughly test hooks in a safe environment before production use

Always review and understand any hook commands before adding them to your configuration.

### Security Best Practices

Here are some key practices for writing more secure hooks:

  1. **Validate and sanitize inputs** \- Never trust input data blindly
  2. **Always quote shell variables** \- Use `"$VAR"` not `$VAR`
  3. **Block path traversal** \- Check for `..` in file paths
  4. **Use absolute paths** \- Specify full paths for scripts (use “$CLAUDE_PROJECT_DIR” for the project path)
  5. **Skip sensitive files** \- Avoid `.env`, `.git/`, keys, etc.

### Configuration Safety

Direct edits to hooks in settings files don’t take effect immediately. Claude Code:

  1. Captures a snapshot of hooks at startup
  2. Uses this snapshot throughout the session
  3. Warns if hooks are modified externally
  4. Requires review in `/hooks` menu for changes to apply

This prevents malicious hook modifications from affecting your current session.

## Hook Execution Details

  * **Timeout** : 60-second execution limit by default, configurable per command.
    * A timeout for an individual command does not affect the other commands.
  * **Parallelization** : All matching hooks run in parallel
  * **Deduplication** : Multiple identical hook commands are deduplicated automatically
  * **Environment** : Runs in current directory with Claude Code’s environment
    * The `CLAUDE_PROJECT_DIR` environment variable is available and contains the absolute path to the project root directory (where Claude Code was started)
    * The `CLAUDE_CODE_REMOTE` environment variable indicates whether the hook is running in a remote (web) environment (`"true"`) or local CLI environment (not set or empty). Use this to run different logic based on execution context.
  * **Input** : JSON via stdin
  * **Output** :
    * PreToolUse/PermissionRequest/PostToolUse/Stop/SubagentStop: Progress shown in verbose mode (ctrl+o)
    * Notification/SessionEnd: Logged to debug only (`--debug`)
    * UserPromptSubmit/SessionStart: stdout added as context for Claude

## Debugging

### Basic Troubleshooting

If your hooks aren’t working:

  1. **Check configuration** \- Run `/hooks` to see if your hook is registered
  2. **Verify syntax** \- Ensure your JSON settings are valid
  3. **Test commands** \- Run hook commands manually first
  4. **Check permissions** \- Make sure scripts are executable
  5. **Review logs** \- Use `claude --debug` to see hook execution details

Common issues:

  * **Quotes not escaped** \- Use `\"` inside JSON strings
  * **Wrong matcher** \- Check tool names match exactly (case-sensitive)
  * **Command not found** \- Use full paths for scripts

### Advanced Debugging

For complex hook issues:

  1. **Inspect hook execution** \- Use `claude --debug` to see detailed hook execution
  2. **Validate JSON schemas** \- Test hook input/output with external tools
  3. **Check environment variables** \- Verify Claude Code’s environment is correct
  4. **Test edge cases** \- Try hooks with unusual file paths or inputs
  5. **Monitor system resources** \- Check for resource exhaustion during hook execution
  6. **Use structured logging** \- Implement logging in your hook scripts

### Debug Output Example

Use `claude --debug` to see hook execution details:


    
    
    [DEBUG] Executing hooks for PostToolUse:Write
    [DEBUG] Getting matching hook commands for PostToolUse with query: Write
    [DEBUG] Found 1 hook matchers in settings
    [DEBUG] Matched 1 hooks for query "Write"
    [DEBUG] Found 1 hook commands to execute
    [DEBUG] Executing hook command: <Your command> with timeout 60000ms
    [DEBUG] Hook command completed with status 0: <Your stdout>
    

Progress messages appear in verbose mode (ctrl+o) showing:

  * Which hook is running
  * Command being executed
  * Success/failure status
  * Output or error messages




================================================================================
# Get started with Claude Code hooks

# Get started with Claude Code hooks

> **原文链接**: https://code.claude.com/docs/en/hooks-guide

---

Claude Code hooks are user-defined shell commands that execute at various points in Claude Code’s lifecycle. Hooks provide deterministic control over Claude Code’s behavior, ensuring certain actions always happen rather than relying on the LLM to choose to run them.

For reference documentation on hooks, see [Hooks reference](https://code.claude.com/docs/en/hooks).

Example use cases for hooks include:

  * **Notifications** : Customize how you get notified when Claude Code is awaiting your input or permission to run something.
  * **Automatic formatting** : Run `prettier` on .ts files, `gofmt` on .go files, etc. after every file edit.
  * **Logging** : Track and count all executed commands for compliance or debugging.
  * **Feedback** : Provide automated feedback when Claude Code produces code that does not follow your codebase conventions.
  * **Custom permissions** : Block modifications to production files or sensitive directories.

By encoding these rules as hooks rather than prompting instructions, you turn suggestions into app-level code that executes every time it is expected to run.

You must consider the security implication of hooks as you add them, because hooks run automatically during the agent loop with your current environment’s credentials. For example, malicious hooks code can exfiltrate your data. Always review your hooks implementation before registering them.For full security best practices, see [Security Considerations](https://code.claude.com/docs/en/hooks#security-considerations) in the hooks reference documentation.

## Hook Events Overview

Claude Code provides several hook events that run at different points in the workflow:

  * **PreToolUse** : Runs before tool calls (can block them)
  * **PermissionRequest** : Runs when a permission dialog is shown (can allow or deny)
  * **PostToolUse** : Runs after tool calls complete
  * **UserPromptSubmit** : Runs when the user submits a prompt, before Claude processes it
  * **Notification** : Runs when Claude Code sends notifications
  * **Stop** : Runs when Claude Code finishes responding
  * **SubagentStop** : Runs when subagent tasks complete
  * **PreCompact** : Runs before Claude Code is about to run a compact operation
  * **SessionStart** : Runs when Claude Code starts a new session or resumes an existing session
  * **SessionEnd** : Runs when Claude Code session ends

Each event receives different data and can control Claude’s behavior in different ways.

## Quickstart

In this quickstart, you’ll add a hook that logs the shell commands that Claude Code runs.

### Prerequisites

Install `jq` for JSON processing in the command line.

### Step 1: Open hooks configuration

Run the `/hooks` [slash command](https://code.claude.com/docs/en/slash-commands) and select the `PreToolUse` hook event. `PreToolUse` hooks run before tool calls and can block them while providing Claude feedback on what to do differently.

### Step 2: Add a matcher

Select `+ Add new matcher…` to run your hook only on Bash tool calls. Type `Bash` for the matcher.

You can use `*` to match all tools.

### Step 3: Add the hook

Select `+ Add new hook…` and enter this command:
    
    
    jq -r '"\(.tool_input.command) - \(.tool_input.description // "No description")"' >> ~/.claude/bash-command-log.txt
    

### Step 4: Save your configuration

For storage location, select `User settings` since you’re logging to your home directory. This hook will then apply to all projects, not just your current project. Then press `Esc` until you return to the REPL. Your hook is now registered.

### Step 5: Verify your hook

Run `/hooks` again or check `~/.claude/settings.json` to see your configuration:
    
    
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "Bash",
            "hooks": [
              {
                "type": "command",
                "command": "jq -r '\"\\(.tool_input.command) - \\(.tool_input.description // \"No description\")\"' >> ~/.claude/bash-command-log.txt"
              }
            ]
          }
        ]
      }
    }
    

### Step 6: Test your hook

Ask Claude to run a simple command like `ls` and check your log file:


    
    
    cat ~/.claude/bash-command-log.txt
    

You should see entries like:


    
    
    ls - Lists files and directories
    

## More Examples

For a complete example implementation, see the [bash command validator example](https://github.com/anthropics/claude-code/blob/main/examples/hooks/bash_command_validator_example.py) in our public codebase.

### Code Formatting Hook

Automatically format TypeScript files after editing:


    
    
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write",
            "hooks": [
              {
                "type": "command",
                "command": "jq -r '.tool_input.file_path' | { read file_path; if echo \"$file_path\" | grep -q '\\.ts$'; then npx prettier --write \"$file_path\"; fi; }"
              }
            ]
          }
        ]
      }
    }
    

### Markdown Formatting Hook

Automatically fix missing language tags and formatting issues in markdown files:


    
    
    {
      "hooks": {
        "PostToolUse": [
          {
            "matcher": "Edit|Write",
            "hooks": [
              {
                "type": "command",
                "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/markdown_formatter.py"
              }
            ]
          }
        ]
      }
    }
    

Create `.claude/hooks/markdown_formatter.py` with this content:


    
    
    #!/usr/bin/env python3
    """
    Markdown formatter for Claude Code output.
    Fixes missing language tags and spacing issues while preserving code content.
    """
    import json
    import sys
    import re
    import os
    
    def detect_language(code):
        """Best-effort language detection from code content."""
        s = code.strip()
        
        # JSON detection
        if re.search(r'^\s*[{\[]', s):
            try:
                json.loads(s)
                return 'json'
            except:
                pass
        
        # Python detection
        if re.search(r'^\s*def\s+\w+\s*\(', s, re.M) or \
           re.search(r'^\s*(import|from)\s+\w+', s, re.M):
            return 'python'
        
        # JavaScript detection  
        if re.search(r'\b(function\s+\w+\s*\(|const\s+\w+\s*=)', s) or \
           re.search(r'=>|console\.(log|error)', s):
            return 'javascript'
        
        # Bash detection
        if re.search(r'^#!.*\b(bash|sh)\b', s, re.M) or \
           re.search(r'\b(if|then|fi|for|in|do|done)\b', s):
            return 'bash'
        
        # SQL detection
        if re.search(r'\b(SELECT|INSERT|UPDATE|DELETE|CREATE)\s+', s, re.I):
            return 'sql'
            
        return 'text'
    
    def format_markdown(content):
        """Format markdown content with language detection."""
        # Fix unlabeled code fences
        def add_lang_to_fence(match):
            indent, info, body, closing = match.groups()
            if not info.strip():
                lang = detect_language(body)
                return f"{indent}```{lang}\n{body}{closing}\n"
            return match.group(0)
        
        fence_pattern = r'(?ms)^([ \t]{0,3})```([^\n]*)\n(.*?)(\n\1```)\s*$'
        content = re.sub(fence_pattern, add_lang_to_fence, content)
        
        # Fix excessive blank lines (only outside code fences)
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.rstrip() + '\n'
    
    # Main execution
    try:
        input_data = json.load(sys.stdin)
        file_path = input_data.get('tool_input', {}).get('file_path', '')
        
        if not file_path.endswith(('.md', '.mdx')):
            sys.exit(0)  # Not a markdown file
        
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            formatted = format_markdown(content)
            
            if formatted != content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(formatted)
                print(f"✓ Fixed markdown formatting in {file_path}")
        
    except Exception as e:
        print(f"Error formatting markdown: {e}", file=sys.stderr)
        sys.exit(1)
    

Make the script executable:


    
    
    chmod +x .claude/hooks/markdown_formatter.py
    

This hook automatically:

  * Detects programming languages in unlabeled code blocks
  * Adds appropriate language tags for syntax highlighting
  * Fixes excessive blank lines while preserving code content
  * Only processes markdown files (`.md`, `.mdx`)

Get desktop notifications when Claude needs input:


    
    
    {
      "hooks": {
        "Notification": [
          {
            "matcher": "",
            "hooks": [
              {
                "type": "command",
                "command": "notify-send 'Claude Code' 'Awaiting your input'"
              }
            ]
          }
        ]
      }
    }
    

### File Protection Hook

Block edits to sensitive files:


    
    
    {
      "hooks": {
        "PreToolUse": [
          {
            "matcher": "Edit|Write",
            "hooks": [
              {
                "type": "command",
                "command": "python3 -c \"import json, sys; data=json.load(sys.stdin); path=data.get('tool_input',{}).get('file_path',''); sys.exit(2 if any(p in path for p in ['.env', 'package-lock.json', '.git/']) else 0)\""
              }
            ]
          }
        ]
      }
    }
    

## Learn more

  * For reference documentation on hooks, see [Hooks reference](https://code.claude.com/docs/en/hooks).
  * For comprehensive security best practices and safety guidelines, see [Security Considerations](https://code.claude.com/docs/en/hooks#security-considerations) in the hooks reference documentation.
  * For troubleshooting steps and debugging techniques, see [Debugging](https://code.claude.com/docs/en/hooks#debugging) in the hooks reference documentation.




================================================================================
# Slash commands

# Slash commands

> **原文链接**: https://code.claude.com/docs/en/slash-commands

---

## Built-in slash commands

Command| Purpose  
---|---  
`/add-dir`| Add additional working directories  
`/agents`| Manage custom AI subagents for specialized tasks  
`/bashes`| List and manage background tasks  
`/bug`| Report bugs (sends conversation to Anthropic)  
`/clear`| Clear conversation history  
`/compact [instructions]`| Compact conversation with optional focus instructions  
`/config`| Open the Settings interface (Config tab). Type to search and filter settings  
`/context`| Visualize current context usage as a colored grid  
`/cost`| Show token usage statistics. See [cost tracking guide](https://code.claude.com/docs/en/costs#using-the-cost-command) for subscription-specific details.  
`/doctor`| Checks installation health. Shows Updates section with auto-update channel and available npm versions  
`/exit`| Exit the REPL  
`/export [filename]`| Export the current conversation to a file or clipboard  
`/help`| Get usage help  
`/hooks`| Manage hook configurations for tool events  
`/ide`| Manage IDE integrations and show status  
`/init`| Initialize project with `CLAUDE.md` guide  
`/install-github-app`| Set up Claude GitHub Actions for a repository  
`/login`| Switch Anthropic accounts  
`/logout`| Sign out from your Anthropic account  
`/mcp`| Manage MCP server connections and OAuth authentication  
`/memory`| Edit `CLAUDE.md` memory files  
`/model`| Select or change the AI model  
`/output-style [style]`| Set the output style directly or from a selection menu  
`/permissions`| View or update [permissions](https://code.claude.com/docs/en/iam#configuring-permissions)  
`/plan`| Enter plan mode directly from the prompt  
`/plugin`| Manage Claude Code plugins  
`/pr-comments`| View pull request comments  
`/privacy-settings`| View and update your privacy settings  
`/release-notes`| View release notes  
`/rename <name>`| Rename the current session for easier identification  
`/remote-env`| Configure remote session environment (claude.ai subscribers)  
`/resume [session]`| Resume a conversation by ID or name, or open the session picker  
`/review`| Request code review  
`/rewind`| Rewind the conversation and/or code  
`/sandbox`| Enable sandboxed bash tool with filesystem and network isolation for safer, more autonomous execution  
`/security-review`| Complete a security review of pending changes on the current branch  
`/stats`| Visualize daily usage, session history, streaks, and model preferences. Press `r` to cycle date ranges (Last 7 days, Last 30 days, All time)  
`/status`| Open the Settings interface (Status tab) showing version, model, account, and connectivity  
`/statusline`| Set up Claude Code’s status line UI  
`/teleport`| Resume a remote session from claude.ai by session ID, or open a picker (claude.ai subscribers)  
`/terminal-setup`| Install Shift+Enter key binding for newlines (VS Code, Alacritty, Zed, Warp)  
`/theme`| Change the color theme  
`/todos`| List current TODO items  
`/usage`| For subscription plans only: show plan usage limits and rate limit status  
`/vim`| Enter vim mode for alternating insert and command modes  
  
## Custom slash commands

Custom slash commands allow you to define frequently used prompts as Markdown files that Claude Code can execute. Commands are organized by scope (project-specific or personal) and support namespacing through directory structures.

Slash command autocomplete works anywhere in your input, not just at the beginning. Type `/` at any position to see available commands.

### Syntax
    
    
    /<command-name> [arguments]
    

#### Parameters

Parameter| Description  
---|---  
`<command-name>`| Name derived from the Markdown filename (without `.md` extension)  
`[arguments]`| Optional arguments passed to the command  
  
### Command types

#### Project commands

Commands stored in your repository and shared with your team. When listed in `/help`, these commands show “(project)” after their description. **Location** : `.claude/commands/` The following example creates the `/optimize` command:
    
    
    # Create a project command
    mkdir -p .claude/commands
    echo "Analyze this code for performance issues and suggest optimizations:" > .claude/commands/optimize.md
    

#### Personal commands

Commands available across all your projects. When listed in `/help`, these commands show “(user)” after their description. **Location** : `~/.claude/commands/` The following example creates the `/security-review` command:


    
    
    # Create a personal command
    mkdir -p ~/.claude/commands
    echo "Review this code for security vulnerabilities:" > ~/.claude/commands/security-review.md
    

### Features

#### Namespacing

Use subdirectories to group related commands. Subdirectories appear in the command description but don’t affect the command name. For example:

  * `.claude/commands/frontend/component.md` creates `/component` with description “(project:frontend)”
  * `~/.claude/commands/component.md` creates `/component` with description “(user)”

If a project command and user command share the same name, the project command takes precedence and the user command is silently ignored. For example, if both `.claude/commands/deploy.md` and `~/.claude/commands/deploy.md` exist, `/deploy` runs the project version. Commands in different subdirectories can share names since the subdirectory appears in the description to distinguish them. For example, `.claude/commands/frontend/test.md` and `.claude/commands/backend/test.md` both create `/test`, but show as “(project:frontend)” and “(project:backend)” respectively.

#### Arguments

Pass dynamic values to commands using argument placeholders:

##### All arguments with `$ARGUMENTS`

The `$ARGUMENTS` placeholder captures all arguments passed to the command:


    
    
    # Command definition
    echo 'Fix issue #$ARGUMENTS following our coding standards' > .claude/commands/fix-issue.md
    
    # Usage
    > /fix-issue 123 high-priority
    # $ARGUMENTS becomes: "123 high-priority"
    

##### Individual arguments with `$1`, `$2`, etc.

Access specific arguments individually using positional parameters (similar to shell scripts):


    
    
    # Command definition  
    echo 'Review PR #$1 with priority $2 and assign to $3' > .claude/commands/review-pr.md
    
    # Usage
    > /review-pr 456 high alice
    # $1 becomes "456", $2 becomes "high", $3 becomes "alice"
    

Use positional arguments when you need to:

  * Access arguments individually in different parts of your command
  * Provide defaults for missing arguments
  * Build more structured commands with specific parameter roles

#### Bash command execution

Execute bash commands before the slash command runs using the `!` prefix. The output is included in the command context. You _must_ include `allowed-tools` with the `Bash` tool, but you can choose the specific bash commands to allow. For example:


    
    
    ---
    allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
    description: Create a git commit
    ---
    
    ## Context
    
    - Current git status: !`git status`
    - Current git diff (staged and unstaged changes): !`git diff HEAD`
    - Current branch: !`git branch --show-current`
    - Recent commits: !`git log --oneline -10`
    
    ## Your task
    
    Based on the above changes, create a single git commit.
    

#### File references

Include file contents in commands using the `@` prefix to [reference files](https://code.claude.com/docs/en/common-workflows#reference-files-and-directories). For example:


    
    
    # Reference a specific file
    
    Review the implementation in @src/utils/helpers.js
    
    # Reference multiple files
    
    Compare @src/old-version.js with @src/new-version.js
    

#### Thinking mode

Slash commands can trigger extended thinking by including [extended thinking keywords](https://code.claude.com/docs/en/common-workflows#use-extended-thinking).

### Frontmatter

Command files support frontmatter, useful for specifying metadata about the command:

Frontmatter| Purpose| Default  
---|---|---  
`allowed-tools`| List of tools the command can use| Inherits from the conversation  
`argument-hint`| The arguments expected for the slash command. Example: `argument-hint: add [tagId] | remove [tagId] | list`. This hint is shown to the user when auto-completing the slash command.| None  
`context`| Set to `fork` to run the command in a forked sub-agent context with its own conversation history.| Inline (no fork)  
`agent`| Specify which [agent type](https://code.claude.com/docs/en/sub-agents#built-in-subagents) to use when `context: fork` is set. Only applicable when combined with `context: fork`.| `general-purpose`  
`description`| Brief description of the command| Uses the first line from the prompt  
`model`| Specific model string (see [Models overview](https://docs.claude.com/en/docs/about-claude/models/overview))| Inherits from the conversation  
`disable-model-invocation`| Whether to prevent the `Skill` tool from calling this command| false  
`hooks`| Define hooks scoped to this command’s execution. See Define hooks for commands.| None  
  
For example:


    
    
    ---
    allowed-tools: Bash(git add:*), Bash(git status:*), Bash(git commit:*)
    argument-hint: [message]
    description: Create a git commit
    model: claude-3-5-haiku-20241022
    ---
    
    Create a git commit with message: $ARGUMENTS
    

Example using positional arguments:


    
    
    ---
    argument-hint: [pr-number] [priority] [assignee]
    description: Review pull request
    ---
    
    Review PR #$1 with priority $2 and assign to $3.
    Focus on security, performance, and code style.
    

#### Define hooks for commands

Slash commands can define hooks that run during the command’s execution. Use the `hooks` field to specify `PreToolUse`, `PostToolUse`, or `Stop` handlers:


    
    
    ---
    description: Deploy to staging with validation
    hooks:
      PreToolUse:
        - matcher: "Bash"
          hooks:
            - type: command
              command: "./scripts/validate-deploy.sh"
              once: true
    ---
    
    Deploy the current branch to staging environment.
    

The `once: true` option runs the hook only once per session. After the first successful execution, the hook is removed. Hooks defined in a command are scoped to that command’s execution and are automatically cleaned up when the command finishes. See [Hooks](https://code.claude.com/docs/en/hooks) for the complete hook configuration format.

## Plugin commands

[Plugins](https://code.claude.com/docs/en/plugins) can provide custom slash commands that integrate seamlessly with Claude Code. Plugin commands work exactly like user-defined commands but are distributed through [plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).

### How plugin commands work

Plugin commands are:

  * **Namespaced** : Commands can use the format `/plugin-name:command-name` to avoid conflicts (plugin prefix is optional unless there are name collisions)
  * **Automatically available** : Once a plugin is installed and enabled, its commands appear in `/help`
  * **Fully integrated** : Support all command features (arguments, frontmatter, bash execution, file references)

### Plugin command structure

**Location** : `commands/` directory in plugin root **File format** : Markdown files with frontmatter **Basic command structure** :


    
    
    ---
    description: Brief description of what the command does
    ---
    
    # Command Name
    
    Detailed instructions for Claude on how to execute this command.
    Include specific guidance on parameters, expected outcomes, and any special considerations.
    

**Advanced command features** :

  * **Arguments** : Use placeholders like `{arg1}` in command descriptions
  * **Subdirectories** : Organize commands in subdirectories for namespacing
  * **Bash integration** : Commands can execute shell scripts and programs
  * **File references** : Commands can reference and modify project files

### Invocation patterns

Direct command (when no conflicts)


    
    
    /command-name
    

Plugin-prefixed (when needed for disambiguation)


    
    
    /plugin-name:command-name
    

With arguments (if command supports them)


    
    
    /command-name arg1 arg2
    

## MCP slash commands

MCP servers can expose prompts as slash commands that become available in Claude Code. These commands are dynamically discovered from connected MCP servers.

### Command format

MCP commands follow the pattern:


    
    
    /mcp__<server-name>__<prompt-name> [arguments]
    

### Features

#### Dynamic discovery

MCP commands are automatically available when:

  * An MCP server is connected and active
  * The server exposes prompts through the MCP protocol
  * The prompts are successfully retrieved during connection

#### Arguments

MCP prompts can accept arguments defined by the server:


    
    
    # Without arguments
    > /mcp__github__list_prs
    
    # With arguments
    > /mcp__github__pr_review 456
    > /mcp__jira__create_issue "Bug title" high
    

#### Naming conventions

Server and prompt names are normalized:

  * Spaces and special characters become underscores
  * Names are lowercase for consistency

### Managing MCP connections

Use the `/mcp` command to:

  * View all configured MCP servers
  * Check connection status
  * Authenticate with OAuth-enabled servers
  * Clear authentication tokens
  * View available tools and prompts from each server

### MCP permissions and wildcards

To approve all tools from an MCP server, use either the server name alone or wildcard syntax:

  * `mcp__github` (approves all GitHub tools)
  * `mcp__github__*` (wildcard syntax, also approves all GitHub tools)

To approve specific tools, list each one explicitly:

  * `mcp__github__get_issue`
  * `mcp__github__list_issues`

See [MCP permission rules](https://code.claude.com/docs/en/iam#tool-specific-permission-rules) for more details.

## `Skill` tool

In earlier versions of Claude Code, slash command invocation was provided by a separate `SlashCommand` tool. This has been merged into the `Skill` tool.

The `Skill` tool allows Claude to programmatically invoke both [custom slash commands](https://code.claude.com/docs/en/slash-commands#custom-slash-commands) and [Agent Skills](https://code.claude.com/docs/en/skills) during a conversation. This gives Claude the ability to use these capabilities on your behalf when appropriate.

### What the `Skill` tool can invoke

The `Skill` tool provides access to:

Type| Location| Requirements  
---|---|---  
Custom slash commands| `.claude/commands/` or `~/.claude/commands/`| Must have `description` frontmatter  
Agent Skills| `.claude/skills/` or `~/.claude/skills/`| Must not have `disable-model-invocation: true`  
  
Built-in commands like `/compact` and `/init` are _not_ available through this tool.

### Encourage Claude to use specific commands

To encourage Claude to use the `Skill` tool, reference the command by name, including the slash, in your prompts or `CLAUDE.md` file:


    
    
    > Run /write-unit-test when you are about to start writing tests.
    

This tool puts each available command’s metadata into context up to the character budget limit. Use `/context` to monitor token usage. To see which commands and Skills are available to the `Skill` tool, run `claude --debug` and trigger a query.

### Disable the `Skill` tool

To prevent Claude from programmatically invoking any commands or Skills:


    
    
    /permissions
    # Add to deny rules: Skill
    

This removes the `Skill` tool and all command/Skill descriptions from context.

### Disable specific commands or Skills

To prevent a specific command or Skill from being invoked programmatically via the `Skill` tool, add `disable-model-invocation: true` to its frontmatter. This also removes the item’s metadata from context.

The `user-invocable` field in Skills only controls menu visibility, not `Skill` tool access. Use `disable-model-invocation: true` to block programmatic invocation. See [Control Skill visibility](https://code.claude.com/docs/en/skills#control-skill-visibility) for details.

### `Skill` permission rules

The permission rules support:

  * **Exact match** : `Skill(commit)` (allows only `commit` with no arguments)
  * **Prefix match** : `Skill(review-pr:*)` (allows `review-pr` with any arguments)

### Character budget limit

The `Skill` tool includes a character budget to limit context usage. This prevents token overflow when many commands and Skills are available. The budget includes each item’s name, arguments, and description.

  * **Default limit** : 15,000 characters
  * **Custom limit** : Set via `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable. The name is retained for backwards compatibility.

When the budget is exceeded, Claude sees only a subset of available items. In `/context`, a warning shows how many are included.

## Skills vs slash commands

**Slash commands** and **Agent Skills** serve different purposes in Claude Code:

### Use slash commands for

**Quick, frequently used prompts** :

  * Simple prompt snippets you use often
  * Quick reminders or templates
  * Frequently used instructions that fit in one file

**Examples** :

  * `/review` → “Review this code for bugs and suggest improvements”
  * `/explain` → “Explain this code in simple terms”
  * `/optimize` → “Analyze this code for performance issues”

### Use Skills for

**Comprehensive capabilities with structure** :

  * Complex workflows with multiple steps
  * Capabilities requiring scripts or utilities
  * Knowledge organized across multiple files
  * Team workflows you want to standardize

**Examples** :

  * PDF processing Skill with form-filling scripts and validation
  * Data analysis Skill with reference docs for different data types
  * Documentation Skill with style guides and templates

### Key differences

Aspect| Slash Commands| Agent Skills  
---|---|---  
**Complexity**|  Simple prompts| Complex capabilities  
**Structure**|  Single .md file| Directory with SKILL.md + resources  
**Discovery**|  Explicit invocation (`/command`)| Automatic (based on context)  
**Files**|  One file only| Multiple files, scripts, templates  
**Scope**|  Project or personal| Project or personal  
**Sharing**|  Via git| Via git  
  
### Example comparison

**As a slash command** :


    
    
    # .claude/commands/review.md
    Review this code for:
    - Security vulnerabilities
    - Performance issues
    - Code style violations
    

Usage: `/review` (manual invocation) **As a Skill** :


    
    
    .claude/skills/code-review/
    ├── SKILL.md (overview and workflows)
    ├── SECURITY.md (security checklist)
    ├── PERFORMANCE.md (performance patterns)
    ├── STYLE.md (style guide reference)
    └── scripts/
        └── run-linters.sh
    

Usage: “Can you review this code?” (automatic discovery) The Skill provides richer context, validation scripts, and organized reference material.

### When to use each

**Use slash commands** :

  * You invoke the same prompt repeatedly
  * The prompt fits in a single file
  * You want explicit control over when it runs

**Use Skills** :

  * Claude should discover the capability automatically
  * Multiple files or scripts are needed
  * Complex workflows with validation steps
  * Team needs standardized, detailed guidance

Both slash commands and Skills can coexist. Use the approach that fits your needs. Learn more about [Agent Skills](https://code.claude.com/docs/en/skills).

## See also

  * [Plugins](https://code.claude.com/docs/en/plugins) \- Extend Claude Code with custom commands through plugins
  * [Identity and Access Management](https://code.claude.com/docs/en/iam) \- Complete guide to permissions, including MCP tool permissions
  * [Interactive mode](https://code.claude.com/docs/en/interactive-mode) \- Shortcuts, input modes, and interactive features
  * [CLI reference](https://code.claude.com/docs/en/cli-reference) \- Command-line flags and options
  * [Settings](https://code.claude.com/docs/en/settings) \- Configuration options
  * [Memory management](https://code.claude.com/docs/en/memory) \- Managing Claude’s memory across sessions




================================================================================
# Connect Claude Code to tools via MCP

# Connect Claude Code to tools via MCP

> **原文链接**: https://code.claude.com/docs/en/mcp

---

Claude Code can connect to hundreds of external tools and data sources through the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction), an open source standard for AI-tool integrations. MCP servers give Claude Code access to your tools, databases, and APIs.

## What you can do with MCP

With MCP servers connected, you can ask Claude Code to:

  * **Implement features from issue trackers** : “Add the feature described in JIRA issue ENG-4521 and create a PR on GitHub.”
  * **Analyze monitoring data** : “Check Sentry and Statsig to check the usage of the feature described in ENG-4521.”
  * **Query databases** : “Find emails of 10 random users who used feature ENG-4521, based on our PostgreSQL database.”
  * **Integrate designs** : “Update our standard email template based on the new Figma designs that were posted in Slack”
  * **Automate workflows** : “Create Gmail drafts inviting these 10 users to a feedback session about the new feature.”

## Popular MCP servers

Here are some commonly used MCP servers you can connect to Claude Code:

Use third party MCP servers at your own risk - Anthropic has not verified the correctness or security of all these servers. Make sure you trust MCP servers you are installing. Be especially careful when using MCP servers that could fetch untrusted content, as these can expose you to prompt injection risk.

**Need a specific integration?** [Find hundreds more MCP servers on GitHub](https://github.com/modelcontextprotocol/servers), or build your own using the [MCP SDK](https://modelcontextprotocol.io/quickstart/server).

## Installing MCP servers

MCP servers can be configured in three different ways depending on your needs:

### Option 1: Add a remote HTTP server

HTTP servers are the recommended option for connecting to remote MCP servers. This is the most widely supported transport for cloud-based services.
    
    
    # Basic syntax
    claude mcp add --transport http <name> <url>
    
    # Real example: Connect to Notion
    claude mcp add --transport http notion https://mcp.notion.com/mcp
    
    # Example with Bearer token
    claude mcp add --transport http secure-api https://api.example.com/mcp \
      --header "Authorization: Bearer your-token"
    

### Option 2: Add a remote SSE server

The SSE (Server-Sent Events) transport is deprecated. Use HTTP servers instead, where available.
    
    
    # Basic syntax
    claude mcp add --transport sse <name> <url>
    
    # Real example: Connect to Asana
    claude mcp add --transport sse asana https://mcp.asana.com/sse
    
    # Example with authentication header
    claude mcp add --transport sse private-api https://api.company.com/sse \
      --header "X-API-Key: your-key-here"
    

### Option 3: Add a local stdio server

Stdio servers run as local processes on your machine. They’re ideal for tools that need direct system access or custom scripts.


    
    
    # Basic syntax
    claude mcp add [options] <name> -- <command> [args...]
    
    # Real example: Add Airtable server
    claude mcp add --transport stdio --env AIRTABLE_API_KEY=YOUR_KEY airtable \
      -- npx -y airtable-mcp-server
    

**Important: Option ordering** All options (`--transport`, `--env`, `--scope`, `--header`) must come **before** the server name. The `--` (double dash) then separates the server name from the command and arguments that get passed to the MCP server.For example:

  * `claude mcp add --transport stdio myserver -- npx server` → runs `npx server`
  * `claude mcp add --transport stdio --env KEY=value myserver -- python server.py --port 8080` → runs `python server.py --port 8080` with `KEY=value` in environment

This prevents conflicts between Claude’s flags and the server’s flags.

### Managing your servers

Once configured, you can manage your MCP servers with these commands:


    
    
    # List all configured servers
    claude mcp list
    
    # Get details for a specific server
    claude mcp get github
    
    # Remove a server
    claude mcp remove github
    
    # (within Claude Code) Check server status
    /mcp
    

### Dynamic tool updates

Claude Code supports MCP `list_changed` notifications, allowing MCP servers to dynamically update their available tools, prompts, and resources without requiring you to disconnect and reconnect. When an MCP server sends a `list_changed` notification, Claude Code automatically refreshes the available capabilities from that server.

Tips:

  * Use the `--scope` flag to specify where the configuration is stored:
    * `local` (default): Available only to you in the current project (was called `project` in older versions)
    * `project`: Shared with everyone in the project via `.mcp.json` file
    * `user`: Available to you across all projects (was called `global` in older versions)
  * Set environment variables with `--env` flags (for example, `--env KEY=value`)
  * Configure MCP server startup timeout using the MCP_TIMEOUT environment variable (for example, `MCP_TIMEOUT=10000 claude` sets a 10-second timeout)
  * Claude Code will display a warning when MCP tool output exceeds 10,000 tokens. To increase this limit, set the `MAX_MCP_OUTPUT_TOKENS` environment variable (for example, `MAX_MCP_OUTPUT_TOKENS=50000`)
  * Use `/mcp` to authenticate with remote servers that require OAuth 2.0 authentication

**Windows Users** : On native Windows (not WSL), local MCP servers that use `npx` require the `cmd /c` wrapper to ensure proper execution.


    
    
    # This creates command="cmd" which Windows can execute
    claude mcp add --transport stdio my-server -- cmd /c npx -y @some/package
    

Without the `cmd /c` wrapper, you’ll encounter “Connection closed” errors because Windows cannot directly execute `npx`. (See the note above for an explanation of the `--` parameter.)

### Plugin-provided MCP servers

[Plugins](https://code.claude.com/docs/en/plugins) can bundle MCP servers, automatically providing tools and integrations when the plugin is enabled. Plugin MCP servers work identically to user-configured servers. **How plugin MCP servers work** :

  * Plugins define MCP servers in `.mcp.json` at the plugin root or inline in `plugin.json`
  * When a plugin is enabled, its MCP servers start automatically
  * Plugin MCP tools appear alongside manually configured MCP tools
  * Plugin servers are managed through plugin installation (not `/mcp` commands)

**Example plugin MCP configuration** : In `.mcp.json` at plugin root:


    
    
    {
      "database-tools": {
        "command": "${CLAUDE_PLUGIN_ROOT}/servers/db-server",
        "args": ["--config", "${CLAUDE_PLUGIN_ROOT}/config.json"],
        "env": {
          "DB_URL": "${DB_URL}"
        }
      }
    }
    

Or inline in `plugin.json`:


    
    
    {
      "name": "my-plugin",
      "mcpServers": {
        "plugin-api": {
          "command": "${CLAUDE_PLUGIN_ROOT}/servers/api-server",
          "args": ["--port", "8080"]
        }
      }
    }
    

**Plugin MCP features** :

  * **Automatic lifecycle** : Servers start when plugin enables, but you must restart Claude Code to apply MCP server changes (enabling or disabling)
  * **Environment variables** : Use `${CLAUDE_PLUGIN_ROOT}` for plugin-relative paths
  * **User environment access** : Access to same environment variables as manually configured servers
  * **Multiple transport types** : Support stdio, SSE, and HTTP transports (transport support may vary by server)

**Viewing plugin MCP servers** :


    
    
    # Within Claude Code, see all MCP servers including plugin ones
    /mcp
    

Plugin servers appear in the list with indicators showing they come from plugins. **Benefits of plugin MCP servers** :

  * **Bundled distribution** : Tools and servers packaged together
  * **Automatic setup** : No manual MCP configuration needed
  * **Team consistency** : Everyone gets the same tools when plugin is installed

See the [plugin components reference](https://code.claude.com/docs/en/plugins-reference#mcp-servers) for details on bundling MCP servers with plugins.

## MCP installation scopes

MCP servers can be configured at three different scope levels, each serving distinct purposes for managing server accessibility and sharing. Understanding these scopes helps you determine the best way to configure servers for your specific needs.

### Local scope

Local-scoped servers represent the default configuration level and are stored in `~/.claude.json` under your project’s path. These servers remain private to you and are only accessible when working within the current project directory. This scope is ideal for personal development servers, experimental configurations, or servers containing sensitive credentials that shouldn’t be shared.


    
    
    # Add a local-scoped server (default)
    claude mcp add --transport http stripe https://mcp.stripe.com
    
    # Explicitly specify local scope
    claude mcp add --transport http stripe --scope local https://mcp.stripe.com
    

### Project scope

Project-scoped servers enable team collaboration by storing configurations in a `.mcp.json` file at your project’s root directory. This file is designed to be checked into version control, ensuring all team members have access to the same MCP tools and services. When you add a project-scoped server, Claude Code automatically creates or updates this file with the appropriate configuration structure.


    
    
    # Add a project-scoped server
    claude mcp add --transport http paypal --scope project https://mcp.paypal.com/mcp
    

The resulting `.mcp.json` file follows a standardized format:


    
    
    {
      "mcpServers": {
        "shared-server": {
          "command": "/path/to/server",
          "args": [],
          "env": {}
        }
      }
    }
    

For security reasons, Claude Code prompts for approval before using project-scoped servers from `.mcp.json` files. If you need to reset these approval choices, use the `claude mcp reset-project-choices` command.

### User scope

User-scoped servers are stored in `~/.claude.json` and provide cross-project accessibility, making them available across all projects on your machine while remaining private to your user account. This scope works well for personal utility servers, development tools, or services you frequently use across different projects.


    
    
    # Add a user server
    claude mcp add --transport http hubspot --scope user https://mcp.hubspot.com/anthropic
    

### Choosing the right scope

Select your scope based on:

  * **Local scope** : Personal servers, experimental configurations, or sensitive credentials specific to one project
  * **Project scope** : Team-shared servers, project-specific tools, or services required for collaboration
  * **User scope** : Personal utilities needed across multiple projects, development tools, or frequently used services

**Where are MCP servers stored?**

  * **User and local scope** : `~/.claude.json` (in the `mcpServers` field or under project paths)
  * **Project scope** : `.mcp.json` in your project root (checked into source control)
  * **Managed** : `managed-mcp.json` in system directories (see Managed MCP configuration)

### Scope hierarchy and precedence

MCP server configurations follow a clear precedence hierarchy. When servers with the same name exist at multiple scopes, the system resolves conflicts by prioritizing local-scoped servers first, followed by project-scoped servers, and finally user-scoped servers. This design ensures that personal configurations can override shared ones when needed.

### Environment variable expansion in `.mcp.json`

Claude Code supports environment variable expansion in `.mcp.json` files, allowing teams to share configurations while maintaining flexibility for machine-specific paths and sensitive values like API keys. **Supported syntax:**

  * `${VAR}` \- Expands to the value of environment variable `VAR`
  * `${VAR:-default}` \- Expands to `VAR` if set, otherwise uses `default`

**Expansion locations:** Environment variables can be expanded in:

  * `command` \- The server executable path
  * `args` \- Command-line arguments
  * `env` \- Environment variables passed to the server
  * `url` \- For HTTP server types
  * `headers` \- For HTTP server authentication

**Example with variable expansion:**


    
    
    {
      "mcpServers": {
        "api-server": {
          "type": "http",
          "url": "${API_BASE_URL:-https://api.example.com}/mcp",
          "headers": {
            "Authorization": "Bearer ${API_KEY}"
          }
        }
      }
    }
    

If a required environment variable is not set and has no default value, Claude Code will fail to parse the config.

## Practical examples

### Example: Monitor errors with Sentry


    
    
    # 1. Add the Sentry MCP server
    claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
    
    # 2. Use /mcp to authenticate with your Sentry account
    > /mcp
    
    # 3. Debug production issues
    > "What are the most common errors in the last 24 hours?"
    > "Show me the stack trace for error ID abc123"
    > "Which deployment introduced these new errors?"
    

### Example: Connect to GitHub for code reviews


    
    
    # 1. Add the GitHub MCP server
    claude mcp add --transport http github https://api.githubcopilot.com/mcp/
    
    # 2. In Claude Code, authenticate if needed
    > /mcp
    # Select "Authenticate" for GitHub
    
    # 3. Now you can ask Claude to work with GitHub
    > "Review PR #456 and suggest improvements"
    > "Create a new issue for the bug we just found"
    > "Show me all open PRs assigned to me"
    

### Example: Query your PostgreSQL database


    
    
    # 1. Add the database server with your connection string
    claude mcp add --transport stdio db -- npx -y @bytebase/dbhub \
      --dsn "postgresql://readonly:[[email protected]](https://code.claude.com/cdn-cgi/l/email-protection):5432/analytics"
    
    # 2. Query your database naturally
    > "What's our total revenue this month?"
    > "Show me the schema for the orders table"
    > "Find customers who haven't made a purchase in 90 days"
    

## Authenticate with remote MCP servers

Many cloud-based MCP servers require authentication. Claude Code supports OAuth 2.0 for secure connections.

1

Add the server that requires authentication

For example:


    
    
    claude mcp add --transport http sentry https://mcp.sentry.dev/mcp
    

2

Use the /mcp command within Claude Code

In Claude code, use the command:


    
    
    > /mcp
    

Then follow the steps in your browser to login.

Tips:

  * Authentication tokens are stored securely and refreshed automatically
  * Use “Clear authentication” in the `/mcp` menu to revoke access
  * If your browser doesn’t open automatically, copy the provided URL
  * OAuth authentication works with HTTP servers

## Add MCP servers from JSON configuration

If you have a JSON configuration for an MCP server, you can add it directly:

1

Add an MCP server from JSON


    
    
    # Basic syntax
    claude mcp add-json <name> '<json>'
    
    # Example: Adding an HTTP server with JSON configuration
    claude mcp add-json weather-api '{"type":"http","url":"https://api.weather.com/mcp","headers":{"Authorization":"Bearer token"}}'
    
    # Example: Adding a stdio server with JSON configuration
    claude mcp add-json local-weather '{"type":"stdio","command":"/path/to/weather-cli","args":["--api-key","abc123"],"env":{"CACHE_DIR":"/tmp"}}'
    

2

Verify the server was added


    
    
    claude mcp get weather-api
    

Tips:

  * Make sure the JSON is properly escaped in your shell
  * The JSON must conform to the MCP server configuration schema
  * You can use `--scope user` to add the server to your user configuration instead of the project-specific one

## Import MCP servers from Claude Desktop

If you’ve already configured MCP servers in Claude Desktop, you can import them:

1

Import servers from Claude Desktop


    
    
    # Basic syntax 
    claude mcp add-from-claude-desktop 
    

2

Select which servers to import

After running the command, you’ll see an interactive dialog that allows you to select which servers you want to import.

3

Verify the servers were imported


    
    
    claude mcp list 
    

Tips:

  * This feature only works on macOS and Windows Subsystem for Linux (WSL)
  * It reads the Claude Desktop configuration file from its standard location on those platforms
  * Use the `--scope user` flag to add servers to your user configuration
  * Imported servers will have the same names as in Claude Desktop
  * If servers with the same names already exist, they will get a numerical suffix (for example, `server_1`)

## Use Claude Code as an MCP server

You can use Claude Code itself as an MCP server that other applications can connect to:


    
    
    # Start Claude as a stdio MCP server
    claude mcp serve
    

You can use this in Claude Desktop by adding this configuration to claude_desktop_config.json:


    
    
    {
      "mcpServers": {
        "claude-code": {
          "type": "stdio",
          "command": "claude",
          "args": ["mcp", "serve"],
          "env": {}
        }
      }
    }
    

**Configuring the executable path** : The `command` field must reference the Claude Code executable. If the `claude` command is not in your system’s PATH, you’ll need to specify the full path to the executable.To find the full path:


    
    
    which claude
    

Then use the full path in your configuration:


    
    
    {
      "mcpServers": {
        "claude-code": {
          "type": "stdio",
          "command": "/full/path/to/claude",
          "args": ["mcp", "serve"],
          "env": {}
        }
      }
    }
    

Without the correct executable path, you’ll encounter errors like `spawn claude ENOENT`.

Tips:

  * The server provides access to Claude’s tools like View, Edit, LS, etc.
  * In Claude Desktop, try asking Claude to read files in a directory, make edits, and more.
  * Note that this MCP server is only exposing Claude Code’s tools to your MCP client, so your own client is responsible for implementing user confirmation for individual tool calls.

## MCP output limits and warnings

When MCP tools produce large outputs, Claude Code helps manage the token usage to prevent overwhelming your conversation context:

  * **Output warning threshold** : Claude Code displays a warning when any MCP tool output exceeds 10,000 tokens
  * **Configurable limit** : You can adjust the maximum allowed MCP output tokens using the `MAX_MCP_OUTPUT_TOKENS` environment variable
  * **Default limit** : The default maximum is 25,000 tokens

To increase the limit for tools that produce large outputs:


    
    
    # Set a higher limit for MCP tool outputs
    export MAX_MCP_OUTPUT_TOKENS=50000
    claude
    

This is particularly useful when working with MCP servers that:

  * Query large datasets or databases
  * Generate detailed reports or documentation
  * Process extensive log files or debugging information

If you frequently encounter output warnings with specific MCP servers, consider increasing the limit or configuring the server to paginate or filter its responses.

## Use MCP resources

MCP servers can expose resources that you can reference using @ mentions, similar to how you reference files.

### Reference MCP resources

1

List available resources

Type `@` in your prompt to see available resources from all connected MCP servers. Resources appear alongside files in the autocomplete menu.

2

Reference a specific resource

Use the format `@server:protocol://resource/path` to reference a resource:


    
    
    > Can you analyze @github:issue://123 and suggest a fix?
    


    
    
    > Please review the API documentation at @docs:file://api/authentication
    

3

Multiple resource references

You can reference multiple resources in a single prompt:


    
    
    > Compare @postgres:schema://users with @docs:file://database/user-model
    

Tips:

  * Resources are automatically fetched and included as attachments when referenced
  * Resource paths are fuzzy-searchable in the @ mention autocomplete
  * Claude Code automatically provides tools to list and read MCP resources when servers support them
  * Resources can contain any type of content that the MCP server provides (text, JSON, structured data, etc.)

## Scale with MCP Tool Search

When you have many MCP servers configured, tool definitions can consume a significant portion of your context window. MCP Tool Search solves this by dynamically loading tools on-demand instead of preloading all of them.

### How it works

Claude Code automatically enables Tool Search when your MCP tool descriptions would consume more than 10% of the context window. You can adjust this threshold or disable tool search entirely. When triggered:

  1. MCP tools are deferred rather than loaded into context upfront
  2. Claude uses a search tool to discover relevant MCP tools when needed
  3. Only the tools Claude actually needs are loaded into context
  4. MCP tools continue to work exactly as before from your perspective

### For MCP server authors

If you’re building an MCP server, the server instructions field becomes more useful with Tool Search enabled. Server instructions help Claude understand when to search for your tools, similar to how [skills](https://code.claude.com/docs/en/skills) work. Add clear, descriptive server instructions that explain:

  * What category of tasks your tools handle
  * When Claude should search for your tools
  * Key capabilities your server provides

### Configure tool search

Tool search runs in auto mode by default, meaning it activates only when your MCP tool definitions exceed the context threshold. If you have few tools, they load normally without tool search. This feature requires models that support `tool_reference` blocks: Sonnet 4 and later, or Opus 4 and later. Haiku models do not support tool search. Control tool search behavior with the `ENABLE_TOOL_SEARCH` environment variable:

Value| Behavior  
---|---  
`auto`| Activates when MCP tools exceed 10% of context (default)  
`auto:<N>`| Activates at custom threshold, where `<N>` is a percentage (e.g., `auto:5` for 5%)  
`true`| Always enabled  
`false`| Disabled, all MCP tools loaded upfront  
  

    
    
    # Use a custom 5% threshold
    ENABLE_TOOL_SEARCH=auto:5 claude
    
    # Disable tool search entirely
    ENABLE_TOOL_SEARCH=false claude
    

Or set the value in your [settings.json `env` field](https://code.claude.com/docs/en/settings#available-settings). You can also disable the MCPSearch tool specifically using the `disallowedTools` setting:


    
    
    {
      "permissions": {
        "deny": ["MCPSearch"]
      }
    }
    

## Use MCP prompts as slash commands

MCP servers can expose prompts that become available as slash commands in Claude Code.

### Execute MCP prompts

1

Discover available prompts

Type `/` to see all available commands, including those from MCP servers. MCP prompts appear with the format `/mcp__servername__promptname`.

2

Execute a prompt without arguments


    
    
    > /mcp__github__list_prs
    

3

Execute a prompt with arguments

Many prompts accept arguments. Pass them space-separated after the command:


    
    
    > /mcp__github__pr_review 456
    


    
    
    > /mcp__jira__create_issue "Bug in login flow" high
    

Tips:

  * MCP prompts are dynamically discovered from connected servers
  * Arguments are parsed based on the prompt’s defined parameters
  * Prompt results are injected directly into the conversation
  * Server and prompt names are normalized (spaces become underscores)

## Managed MCP configuration

For organizations that need centralized control over MCP servers, Claude Code supports two configuration options:

  1. **Exclusive control with`managed-mcp.json`**: Deploy a fixed set of MCP servers that users cannot modify or extend
  2. **Policy-based control with allowlists/denylists** : Allow users to add their own servers, but restrict which ones are permitted

These options allow IT administrators to:

  * **Control which MCP servers employees can access** : Deploy a standardized set of approved MCP servers across the organization
  * **Prevent unauthorized MCP servers** : Restrict users from adding unapproved MCP servers
  * **Disable MCP entirely** : Remove MCP functionality completely if needed

### Option 1: Exclusive control with managed-mcp.json

When you deploy a `managed-mcp.json` file, it takes **exclusive control** over all MCP servers. Users cannot add, modify, or use any MCP servers other than those defined in this file. This is the simplest approach for organizations that want complete control. System administrators deploy the configuration file to a system-wide directory:

  * macOS: `/Library/Application Support/ClaudeCode/managed-mcp.json`
  * Linux and WSL: `/etc/claude-code/managed-mcp.json`
  * Windows: `C:\Program Files\ClaudeCode\managed-mcp.json`

These are system-wide paths (not user home directories like `~/Library/...`) that require administrator privileges. They are designed to be deployed by IT administrators.

The `managed-mcp.json` file uses the same format as a standard `.mcp.json` file:


    
    
    {
      "mcpServers": {
        "github": {
          "type": "http",
          "url": "https://api.githubcopilot.com/mcp/"
        },
        "sentry": {
          "type": "http",
          "url": "https://mcp.sentry.dev/mcp"
        },
        "company-internal": {
          "type": "stdio",
          "command": "/usr/local/bin/company-mcp-server",
          "args": ["--config", "/etc/company/mcp-config.json"],
          "env": {
            "COMPANY_API_URL": "https://internal.company.com"
          }
        }
      }
    }
    

### Option 2: Policy-based control with allowlists and denylists

Instead of taking exclusive control, administrators can allow users to configure their own MCP servers while enforcing restrictions on which servers are permitted. This approach uses `allowedMcpServers` and `deniedMcpServers` in the [managed settings file](https://code.claude.com/docs/en/settings#settings-files).

**Choosing between options** : Use Option 1 (`managed-mcp.json`) when you want to deploy a fixed set of servers with no user customization. Use Option 2 (allowlists/denylists) when you want to allow users to add their own servers within policy constraints.

#### Restriction options

Each entry in the allowlist or denylist can restrict servers in three ways:

  1. **By server name** (`serverName`): Matches the configured name of the server
  2. **By command** (`serverCommand`): Matches the exact command and arguments used to start stdio servers
  3. **By URL pattern** (`serverUrl`): Matches remote server URLs with wildcard support

**Important** : Each entry must have exactly one of `serverName`, `serverCommand`, or `serverUrl`.

#### Example configuration


    
    
    {
      "allowedMcpServers": [
        // Allow by server name
        { "serverName": "github" },
        { "serverName": "sentry" },
    
        // Allow by exact command (for stdio servers)
        { "serverCommand": ["npx", "-y", "@modelcontextprotocol/server-filesystem"] },
        { "serverCommand": ["python", "/usr/local/bin/approved-server.py"] },
    
        // Allow by URL pattern (for remote servers)
        { "serverUrl": "https://mcp.company.com/*" },
        { "serverUrl": "https://*.internal.corp/*" }
      ],
      "deniedMcpServers": [
        // Block by server name
        { "serverName": "dangerous-server" },
    
        // Block by exact command (for stdio servers)
        { "serverCommand": ["npx", "-y", "unapproved-package"] },
    
        // Block by URL pattern (for remote servers)
        { "serverUrl": "https://*.untrusted.com/*" }
      ]
    }
    

#### How command-based restrictions work

**Exact matching** :

  * Command arrays must match **exactly** \- both the command and all arguments in the correct order
  * Example: `["npx", "-y", "server"]` will NOT match `["npx", "server"]` or `["npx", "-y", "server", "--flag"]`

**Stdio server behavior** :

  * When the allowlist contains **any** `serverCommand` entries, stdio servers **must** match one of those commands
  * Stdio servers cannot pass by name alone when command restrictions are present
  * This ensures administrators can enforce which commands are allowed to run

**Non-stdio server behavior** :

  * Remote servers (HTTP, SSE, WebSocket) use URL-based matching when `serverUrl` entries exist in the allowlist
  * If no URL entries exist, remote servers fall back to name-based matching
  * Command restrictions do not apply to remote servers

#### How URL-based restrictions work

URL patterns support wildcards using `*` to match any sequence of characters. This is useful for allowing entire domains or subdomains. **Wildcard examples** :

  * `https://mcp.company.com/*` \- Allow all paths on a specific domain
  * `https://*.example.com/*` \- Allow any subdomain of example.com
  * `http://localhost:*/*` \- Allow any port on localhost

**Remote server behavior** :

  * When the allowlist contains **any** `serverUrl` entries, remote servers **must** match one of those URL patterns
  * Remote servers cannot pass by name alone when URL restrictions are present
  * This ensures administrators can enforce which remote endpoints are allowed

Example: URL-only allowlist


    
    
    {
      "allowedMcpServers": [
        { "serverUrl": "https://mcp.company.com/*" },
        { "serverUrl": "https://*.internal.corp/*" }
      ]
    }
    

**Result** :

  * HTTP server at `https://mcp.company.com/api`: ✅ Allowed (matches URL pattern)
  * HTTP server at `https://api.internal.corp/mcp`: ✅ Allowed (matches wildcard subdomain)
  * HTTP server at `https://external.com/mcp`: ❌ Blocked (doesn’t match any URL pattern)
  * Stdio server with any command: ❌ Blocked (no name or command entries to match)

Example: Command-only allowlist


    
    
    {
      "allowedMcpServers": [
        { "serverCommand": ["npx", "-y", "approved-package"] }
      ]
    }
    

**Result** :

  * Stdio server with `["npx", "-y", "approved-package"]`: ✅ Allowed (matches command)
  * Stdio server with `["node", "server.js"]`: ❌ Blocked (doesn’t match command)
  * HTTP server named “my-api”: ❌ Blocked (no name entries to match)

Example: Mixed name and command allowlist


    
    
    {
      "allowedMcpServers": [
        { "serverName": "github" },
        { "serverCommand": ["npx", "-y", "approved-package"] }
      ]
    }
    

**Result** :

  * Stdio server named “local-tool” with `["npx", "-y", "approved-package"]`: ✅ Allowed (matches command)
  * Stdio server named “local-tool” with `["node", "server.js"]`: ❌ Blocked (command entries exist but doesn’t match)
  * Stdio server named “github” with `["node", "server.js"]`: ❌ Blocked (stdio servers must match commands when command entries exist)
  * HTTP server named “github”: ✅ Allowed (matches name)
  * HTTP server named “other-api”: ❌ Blocked (name doesn’t match)

Example: Name-only allowlist


    
    
    {
      "allowedMcpServers": [
        { "serverName": "github" },
        { "serverName": "internal-tool" }
      ]
    }
    

**Result** :

  * Stdio server named “github” with any command: ✅ Allowed (no command restrictions)
  * Stdio server named “internal-tool” with any command: ✅ Allowed (no command restrictions)
  * HTTP server named “github”: ✅ Allowed (matches name)
  * Any server named “other”: ❌ Blocked (name doesn’t match)

#### Allowlist behavior (`allowedMcpServers`)

  * `undefined` (default): No restrictions - users can configure any MCP server
  * Empty array `[]`: Complete lockdown - users cannot configure any MCP servers
  * List of entries: Users can only configure servers that match by name, command, or URL pattern

#### Denylist behavior (`deniedMcpServers`)

  * `undefined` (default): No servers are blocked
  * Empty array `[]`: No servers are blocked
  * List of entries: Specified servers are explicitly blocked across all scopes

#### Important notes

  * **Option 1 and Option 2 can be combined** : If `managed-mcp.json` exists, it has exclusive control and users cannot add servers. Allowlists/denylists still apply to the managed servers themselves.
  * **Denylist takes absolute precedence** : If a server matches a denylist entry (by name, command, or URL), it will be blocked even if it’s on the allowlist
  * Name-based, command-based, and URL-based restrictions work together: a server passes if it matches **either** a name entry, a command entry, or a URL pattern (unless blocked by denylist)

**When using`managed-mcp.json`**: Users cannot add MCP servers through `claude mcp add` or configuration files. The `allowedMcpServers` and `deniedMcpServers` settings still apply to filter which managed servers are actually loaded.



================================================================================
# Claude Code settings

# Claude Code settings

> **原文链接**: https://code.claude.com/docs/en/settings

---

Claude Code offers a variety of settings to configure its behavior to meet your needs. You can configure Claude Code by running the `/config` command when using the interactive REPL, which opens a tabbed Settings interface where you can view status information and modify configuration options.

## Configuration scopes

Claude Code uses a **scope system** to determine where configurations apply and who they’re shared with. Understanding scopes helps you decide how to configure Claude Code for personal use, team collaboration, or enterprise deployment.

### Available scopes

Scope| Location| Who it affects| Shared with team?
---|---|---|---
**Managed**|  System-level `managed-settings.json`| All users on the machine| Yes (deployed by IT)
**User**| `~/.claude/` directory| You, across all projects| No
**Project**| `.claude/` in repository| All collaborators on this repository| Yes (committed to git)
**Local**| `.claude/*.local.*` files| You, in this repository only| No (gitignored)

### When to use each scope

**Managed scope** is for:

  * Security policies that must be enforced organization-wide
  * Compliance requirements that can’t be overridden
  * Standardized configurations deployed by IT/DevOps

**User scope** is best for:

  * Personal preferences you want everywhere (themes, editor settings)
  * Tools and plugins you use across all projects
  * API keys and authentication (stored securely)

**Project scope** is best for:

  * Team-shared settings (permissions, hooks, MCP servers)
  * Plugins the whole team should have
  * Standardizing tooling across collaborators

**Local scope** is best for:

  * Personal overrides for a specific project
  * Testing configurations before sharing with the team
  * Machine-specific settings that won’t work for others

### How scopes interact

When the same setting is configured in multiple scopes, more specific scopes take precedence:

  1. **Managed** (highest) - can’t be overridden by anything
  2. **Command line arguments** \- temporary session overrides
  3. **Local** \- overrides project and user settings
  4. **Project** \- overrides user settings
  5. **User** (lowest) - applies when nothing else specifies the setting

For example, if a permission is allowed in user settings but denied in project settings, the project setting takes precedence and the permission is blocked.

### What uses scopes

Scopes apply to many Claude Code features:

Feature| User location| Project location| Local location
---|---|---|---
**Settings**| `~/.claude/settings.json`| `.claude/settings.json`| `.claude/settings.local.json`
**Subagents**| `~/.claude/agents/`| `.claude/agents/`| —
**MCP servers**| `~/.claude.json`| `.mcp.json`| `~/.claude.json` (per-project)
**Plugins**| `~/.claude/settings.json`| `.claude/settings.json`| `.claude/settings.local.json`
**CLAUDE.md**| `~/.claude/CLAUDE.md`| `CLAUDE.md` or `.claude/CLAUDE.md`| `CLAUDE.local.md`

* * *

## Settings files

The `settings.json` file is our official mechanism for configuring Claude Code through hierarchical settings:

  * **User settings** are defined in `~/.claude/settings.json` and apply to all projects.
  * **Project settings** are saved in your project directory:
    * `.claude/settings.json` for settings that are checked into source control and shared with your team
    * `.claude/settings.local.json` for settings that are not checked in, useful for personal preferences and experimentation. Claude Code will configure git to ignore `.claude/settings.local.json` when it is created.
  * **Managed settings** : For organizations that need centralized control, Claude Code supports `managed-settings.json` and `managed-mcp.json` files that can be deployed to system directories:
    * macOS: `/Library/Application Support/ClaudeCode/`
    * Linux and WSL: `/etc/claude-code/`
    * Windows: `C:\Program Files\ClaudeCode\`

These are system-wide paths (not user home directories like `~/Library/...`) that require administrator privileges. They are designed to be deployed by IT administrators.

See [Managed settings](https://code.claude.com/docs/en/iam#managed-settings) and [Managed MCP configuration](https://code.claude.com/docs/en/mcp#managed-mcp-configuration) for details.

Managed deployments can also restrict **plugin marketplace additions** using `strictKnownMarketplaces`. For more information, see [Managed marketplace restrictions](https://code.claude.com/docs/en/plugin-marketplaces#managed-marketplace-restrictions).

  * **Other configuration** is stored in `~/.claude.json`. This file contains your preferences (theme, notification settings, editor mode), OAuth session, [MCP server](https://code.claude.com/docs/en/mcp) configurations for user and local scopes, per-project state (allowed tools, trust settings), and various caches. Project-scoped MCP servers are stored separately in `.mcp.json`.

Example settings.json


    {
      "permissions": {
        "allow": [
          "Bash(npm run lint)",
          "Bash(npm run test:*)",
          "Read(~/.zshrc)"
        ],
        "deny": [
          "Bash(curl:*)",
          "Read(./.env)",
          "Read(./.env.*)",
          "Read(./secrets/**)"
        ]
      },
      "env": {
        "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
        "OTEL_METRICS_EXPORTER": "otlp"
      },
      "companyAnnouncements": [
        "Welcome to Acme Corp! Review our code guidelines at docs.acme.com",
        "Reminder: Code reviews required for all PRs",
        "New security policy in effect"
      ]
    }


### Available settings

`settings.json` supports a number of options:

Key| Description| Example
---|---|---
`apiKeyHelper`| Custom script, to be executed in `/bin/sh`, to generate an auth value. This value will be sent as `X-Api-Key` and `Authorization: Bearer` headers for model requests| `/bin/generate_temp_api_key.sh`
`cleanupPeriodDays`| Sessions inactive for longer than this period are deleted at startup. Setting to `0` immediately deletes all sessions. (default: 30 days)| `20`
`companyAnnouncements`| Announcement to display to users at startup. If multiple announcements are provided, they will be cycled through at random.| `["Welcome to Acme Corp! Review our code guidelines at docs.acme.com"]`
`env`| Environment variables that will be applied to every session| `{"FOO": "bar"}`
`attribution`| Customize attribution for git commits and pull requests. See Attribution settings| `{"commit": "🤖 Generated with Claude Code", "pr": ""}`
`includeCoAuthoredBy`| **Deprecated** : Use `attribution` instead. Whether to include the `co-authored-by Claude` byline in git commits and pull requests (default: `true`)| `false`
`permissions`| See table below for structure of permissions.|
`hooks`| Configure custom commands to run before or after tool executions. See [hooks documentation](https://code.claude.com/docs/en/hooks)| `{"PreToolUse": {"Bash": "echo 'Running command...'"}}`
`disableAllHooks`| Disable all [hooks](https://code.claude.com/docs/en/hooks)| `true`
`allowManagedHooksOnly`| (Managed settings only) Prevent loading of user, project, and plugin hooks. Only allows managed hooks and SDK hooks. See Hook configuration| `true`
`model`| Override the default model to use for Claude Code| `"claude-sonnet-4-5-20250929"`
`otelHeadersHelper`| Script to generate dynamic OpenTelemetry headers. Runs at startup and periodically (see [Dynamic headers](https://code.claude.com/docs/en/monitoring-usage#dynamic-headers))| `/bin/generate_otel_headers.sh`
`statusLine`| Configure a custom status line to display context. See [`statusLine` documentation](https://code.claude.com/docs/en/statusline)| `{"type": "command", "command": "~/.claude/statusline.sh"}`
`fileSuggestion`| Configure a custom script for `@` file autocomplete. See File suggestion settings| `{"type": "command", "command": "~/.claude/file-suggestion.sh"}`
`respectGitignore`| Control whether the `@` file picker respects `.gitignore` patterns. When `true` (default), files matching `.gitignore` patterns are excluded from suggestions| `false`
`outputStyle`| Configure an output style to adjust the system prompt. See [output styles documentation](https://code.claude.com/docs/en/output-styles)| `"Explanatory"`
`forceLoginMethod`| Use `claudeai` to restrict login to Claude.ai accounts, `console` to restrict login to Claude Console (API usage billing) accounts| `claudeai`
`forceLoginOrgUUID`| Specify the UUID of an organization to automatically select it during login, bypassing the organization selection step. Requires `forceLoginMethod` to be set| `"xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"`
`enableAllProjectMcpServers`| Automatically approve all MCP servers defined in project `.mcp.json` files| `true`
`enabledMcpjsonServers`| List of specific MCP servers from `.mcp.json` files to approve| `["memory", "github"]`
`disabledMcpjsonServers`| List of specific MCP servers from `.mcp.json` files to reject| `["filesystem"]`
`allowedMcpServers`| When set in managed-settings.json, allowlist of MCP servers users can configure. Undefined = no restrictions, empty array = lockdown. Applies to all scopes. Denylist takes precedence. See [Managed MCP configuration](https://code.claude.com/docs/en/mcp#managed-mcp-configuration)| `[{ "serverName": "github" }]`
`deniedMcpServers`| When set in managed-settings.json, denylist of MCP servers that are explicitly blocked. Applies to all scopes including managed servers. Denylist takes precedence over allowlist. See [Managed MCP configuration](https://code.claude.com/docs/en/mcp#managed-mcp-configuration)| `[{ "serverName": "filesystem" }]`
`strictKnownMarketplaces`| When set in managed-settings.json, allowlist of plugin marketplaces users can add. Undefined = no restrictions, empty array = lockdown. Applies to marketplace additions only. See [Managed marketplace restrictions](https://code.claude.com/docs/en/plugin-marketplaces#managed-marketplace-restrictions)| `[{ "source": "github", "repo": "acme-corp/plugins" }]`
`awsAuthRefresh`| Custom script that modifies the `.aws` directory (see [advanced credential configuration](https://code.claude.com/docs/en/amazon-bedrock#advanced-credential-configuration))| `aws sso login --profile myprofile`
`awsCredentialExport`| Custom script that outputs JSON with AWS credentials (see [advanced credential configuration](https://code.claude.com/docs/en/amazon-bedrock#advanced-credential-configuration))| `/bin/generate_aws_grant.sh`
`alwaysThinkingEnabled`| Enable [extended thinking](https://code.claude.com/docs/en/common-workflows#use-extended-thinking) by default for all sessions. Typically configured via the `/config` command rather than editing directly| `true`
`plansDirectory`| Customize where plan files are stored. Path is relative to project root. Default: `~/.claude/plans`| `"./plans"`
`showTurnDuration`| Show turn duration messages after responses (e.g., “Cooked for 1m 6s”). Set to `false` to hide these messages| `true`
`language`| Configure Claude’s preferred response language (e.g., `"japanese"`, `"spanish"`, `"french"`). Claude will respond in this language by default| `"japanese"`
`autoUpdatesChannel`| Release channel to follow for updates. Use `"stable"` for a version that is typically about one week old and skips versions with major regressions, or `"latest"` (default) for the most recent release| `"stable"`
`spinnerTipsEnabled`| Show tips in the spinner while Claude is working. Set to `false` to disable tips (default: `true`)| `false`
`terminalProgressBarEnabled`| Enable the terminal progress bar that shows progress in supported terminals like Windows Terminal and iTerm2 (default: `true`)| `false`

### Permission settings

Keys| Description| Example
---|---|---
`allow`| Array of [permission rules](https://code.claude.com/docs/en/iam#configuring-permissions) to allow tool use. **Note:** Bash rules use prefix matching, not regex| `[ "Bash(git diff:*)" ]`
`ask`| Array of [permission rules](https://code.claude.com/docs/en/iam#configuring-permissions) to ask for confirmation upon tool use.| `[ "Bash(git push:*)" ]`
`deny`| Array of [permission rules](https://code.claude.com/docs/en/iam#configuring-permissions) to deny tool use. Use this to also exclude sensitive files from Claude Code access. **Note:** Bash patterns are prefix matches and can be bypassed (see [Bash permission limitations](https://code.claude.com/docs/en/iam#tool-specific-permission-rules))| `[ "WebFetch", "Bash(curl:*)", "Read(./.env)", "Read(./secrets/**)" ]`
`additionalDirectories`| Additional [working directories](https://code.claude.com/docs/en/iam#working-directories) that Claude has access to| `[ "../docs/" ]`
`defaultMode`| Default [permission mode](https://code.claude.com/docs/en/iam#permission-modes) when opening Claude Code| `"acceptEdits"`
`disableBypassPermissionsMode`| Set to `"disable"` to prevent `bypassPermissions` mode from being activated. This disables the `--dangerously-skip-permissions` command-line flag. See [managed settings](https://code.claude.com/docs/en/iam#managed-settings)| `"disable"`

### Sandbox settings

Configure advanced sandboxing behavior. Sandboxing isolates bash commands from your filesystem and network. See [Sandboxing](https://code.claude.com/docs/en/sandboxing) for details. **Filesystem and network restrictions** are configured via Read, Edit, and WebFetch permission rules, not via these sandbox settings.

Keys| Description| Example
---|---|---
`enabled`| Enable bash sandboxing (macOS/Linux only). Default: false| `true`
`autoAllowBashIfSandboxed`| Auto-approve bash commands when sandboxed. Default: true| `true`
`excludedCommands`| Commands that should run outside of the sandbox| `["git", "docker"]`
`allowUnsandboxedCommands`| Allow commands to run outside the sandbox via the `dangerouslyDisableSandbox` parameter. When set to `false`, the `dangerouslyDisableSandbox` escape hatch is completely disabled and all commands must run sandboxed (or be in `excludedCommands`). Useful for enterprise policies that require strict sandboxing. Default: true| `false`
`network.allowUnixSockets`| Unix socket paths accessible in sandbox (for SSH agents, etc.)| `["~/.ssh/agent-socket"]`
`network.allowLocalBinding`| Allow binding to localhost ports (macOS only). Default: false| `true`
`network.httpProxyPort`| HTTP proxy port used if you wish to bring your own proxy. If not specified, Claude will run its own proxy.| `8080`
`network.socksProxyPort`| SOCKS5 proxy port used if you wish to bring your own proxy. If not specified, Claude will run its own proxy.| `8081`
`enableWeakerNestedSandbox`| Enable weaker sandbox for unprivileged Docker environments (Linux only). **Reduces security.** Default: false| `true`

**Configuration example:**


    {
      "sandbox": {
        "enabled": true,
        "autoAllowBashIfSandboxed": true,
        "excludedCommands": ["docker"],
        "network": {
          "allowUnixSockets": [
            "/var/run/docker.sock"
          ],
          "allowLocalBinding": true
        }
      },
      "permissions": {
        "deny": [
          "Read(.envrc)",
          "Read(~/.aws/**)"
        ]
      }
    }


**Filesystem and network restrictions** use standard permission rules:

  * Use `Read` deny rules to block Claude from reading specific files or directories
  * Use `Edit` allow rules to let Claude write to directories beyond the current working directory
  * Use `Edit` deny rules to block writes to specific paths
  * Use `WebFetch` allow/deny rules to control which network domains Claude can access

### Attribution settings

Claude Code adds attribution to git commits and pull requests. These are configured separately:

  * Commits use [git trailers](https://git-scm.com/docs/git-interpret-trailers) (like `Co-Authored-By`) by default, which can be customized or disabled
  * Pull request descriptions are plain text

Keys| Description
---|---
`commit`| Attribution for git commits, including any trailers. Empty string hides commit attribution
`pr`| Attribution for pull request descriptions. Empty string hides pull request attribution

**Default commit attribution:**




    🤖 Generated with [Claude Code](https://claude.com/claude-code)

       Co-Authored-By: Claude Sonnet 4.5 <[[email protected]](https://code.claude.com/cdn-cgi/l/email-protection)>


**Default pull request attribution:**




    🤖 Generated with [Claude Code](https://claude.com/claude-code)


**Example:**




    {
      "attribution": {
        "commit": "Generated with AI\n\nCo-Authored-By: AI <[[email protected]](https://code.claude.com/cdn-cgi/l/email-protection)>",
        "pr": ""
      }
    }


The `attribution` setting takes precedence over the deprecated `includeCoAuthoredBy` setting. To hide all attribution, set `commit` and `pr` to empty strings.

### File suggestion settings

Configure a custom command for `@` file path autocomplete. The built-in file suggestion uses fast filesystem traversal, but large monorepos may benefit from project-specific indexing such as a pre-built file index or custom tooling.




    {
      "fileSuggestion": {
        "type": "command",
        "command": "~/.claude/file-suggestion.sh"
      }
    }


The command runs with the same environment variables as [hooks](https://code.claude.com/docs/en/hooks), including `CLAUDE_PROJECT_DIR`. It receives JSON via stdin with a `query` field:




    {"query": "src/comp"}


Output newline-separated file paths to stdout (currently limited to 15):




    src/components/Button.tsx
    src/components/Modal.tsx
    src/components/Form.tsx


**Example:**




    #!/bin/bash
    query=$(cat | jq -r '.query')
    your-repo-file-index --query "$query" | head -20


### Hook configuration

**Managed settings only** : Controls which hooks are allowed to run. This setting can only be configured in managed settings and provides administrators with strict control over hook execution. **Behavior when`allowManagedHooksOnly` is `true`:**

  * Managed hooks and SDK hooks are loaded
  * User hooks, project hooks, and plugin hooks are blocked

**Configuration:**




    {
      "allowManagedHooksOnly": true
    }


### Settings precedence

Settings apply in order of precedence. From highest to lowest:

  1. **Managed settings** (`managed-settings.json`)
     * Policies deployed by IT/DevOps to system directories
     * Cannot be overridden by user or project settings
  2. **Command line arguments**
     * Temporary overrides for a specific session
  3. **Local project settings** (`.claude/settings.local.json`)
     * Personal project-specific settings
  4. **Shared project settings** (`.claude/settings.json`)
     * Team-shared project settings in source control
  5. **User settings** (`~/.claude/settings.json`)
     * Personal global settings

This hierarchy ensures that organizational policies are always enforced while still allowing teams and individuals to customize their experience. For example, if your user settings allow `Bash(npm run:*)` but a project’s shared settings deny it, the project setting takes precedence and the command is blocked.

### Key points about the configuration system

  * **Memory files (`CLAUDE.md`)**: Contain instructions and context that Claude loads at startup
  * **Settings files (JSON)** : Configure permissions, environment variables, and tool behavior
  * **Slash commands** : Custom commands that can be invoked during a session with `/command-name`
  * **MCP servers** : Extend Claude Code with additional tools and integrations
  * **Precedence** : Higher-level configurations (Managed) override lower-level ones (User/Project)
  * **Inheritance** : Settings are merged, with more specific settings adding to or overriding broader ones

### System prompt

Claude Code’s internal system prompt is not published. To add custom instructions, use `CLAUDE.md` files or the `--append-system-prompt` flag.

### Excluding sensitive files

To prevent Claude Code from accessing files containing sensitive information like API keys, secrets, and environment files, use the `permissions.deny` setting in your `.claude/settings.json` file:




    {
      "permissions": {
        "deny": [
          "Read(./.env)",
          "Read(./.env.*)",
          "Read(./secrets/**)",
          "Read(./config/credentials.json)",
          "Read(./build)"
        ]
      }
    }


This replaces the deprecated `ignorePatterns` configuration. Files matching these patterns will be completely invisible to Claude Code, preventing any accidental exposure of sensitive data.

## Subagent configuration

Claude Code supports custom AI subagents that can be configured at both user and project levels. These subagents are stored as Markdown files with YAML frontmatter:

  * **User subagents** : `~/.claude/agents/` \- Available across all your projects
  * **Project subagents** : `.claude/agents/` \- Specific to your project and can be shared with your team

Subagent files define specialized AI assistants with custom prompts and tool permissions. Learn more about creating and using subagents in the [subagents documentation](https://code.claude.com/docs/en/sub-agents).

## Plugin configuration

Claude Code supports a plugin system that lets you extend functionality with custom commands, agents, hooks, and MCP servers. Plugins are distributed through marketplaces and can be configured at both user and repository levels.

### Plugin settings

Plugin-related settings in `settings.json`:




    {
      "enabledPlugins": {
        "formatter@acme-tools": true,
        "deployer@acme-tools": true,
        "analyzer@security-plugins": false
      },
      "extraKnownMarketplaces": {
        "acme-tools": {
          "source": "github",
          "repo": "acme-corp/claude-plugins"
        }
      }
    }


#### `enabledPlugins`

Controls which plugins are enabled. Format: `"plugin-name@marketplace-name": true/false` **Scopes** :

  * **User settings** (`~/.claude/settings.json`): Personal plugin preferences
  * **Project settings** (`.claude/settings.json`): Project-specific plugins shared with team
  * **Local settings** (`.claude/settings.local.json`): Per-machine overrides (not committed)

**Example** :




    {
      "enabledPlugins": {
        "code-formatter@team-tools": true,
        "deployment-tools@team-tools": true,
        "experimental-features@personal": false
      }
    }


#### `extraKnownMarketplaces`

Defines additional marketplaces that should be made available for the repository. Typically used in repository-level settings to ensure team members have access to required plugin sources. **When a repository includes`extraKnownMarketplaces`**:

  1. Team members are prompted to install the marketplace when they trust the folder
  2. Team members are then prompted to install plugins from that marketplace
  3. Users can skip unwanted marketplaces or plugins (stored in user settings)
  4. Installation respects trust boundaries and requires explicit consent

**Example** :




    {
      "extraKnownMarketplaces": {
        "acme-tools": {
          "source": {
            "source": "github",
            "repo": "acme-corp/claude-plugins"
          }
        },
        "security-plugins": {
          "source": {
            "source": "git",
            "url": "https://git.example.com/security/plugins.git"
          }
        }
      }
    }


**Marketplace source types** :

  * `github`: GitHub repository (uses `repo`)
  * `git`: Any git URL (uses `url`)
  * `directory`: Local filesystem path (uses `path`, for development only)

#### `strictKnownMarketplaces`

**Managed settings only** : Controls which plugin marketplaces users are allowed to add. This setting can only be configured in [`managed-settings.json`](https://code.claude.com/docs/en/iam#managed-settings) and provides administrators with strict control over marketplace sources. **Managed settings file locations** :

  * **macOS** : `/Library/Application Support/ClaudeCode/managed-settings.json`
  * **Linux and WSL** : `/etc/claude-code/managed-settings.json`
  * **Windows** : `C:\Program Files\ClaudeCode\managed-settings.json`

**Key characteristics** :

  * Only available in managed settings (`managed-settings.json`)
  * Cannot be overridden by user or project settings (highest precedence)
  * Enforced BEFORE network/filesystem operations (blocked sources never execute)
  * Uses exact matching for source specifications (including `ref`, `path` for git sources)

**Allowlist behavior** :

  * `undefined` (default): No restrictions - users can add any marketplace
  * Empty array `[]`: Complete lockdown - users cannot add any new marketplaces
  * List of sources: Users can only add marketplaces that match exactly

**All supported source types** : The allowlist supports six marketplace source types. Each source must match exactly for a user’s marketplace addition to be allowed.

  1. **GitHub repositories** :




    { "source": "github", "repo": "acme-corp/approved-plugins" }
    { "source": "github", "repo": "acme-corp/security-tools", "ref": "v2.0" }
    { "source": "github", "repo": "acme-corp/plugins", "ref": "main", "path": "marketplace" }


Fields: `repo` (required), `ref` (optional: branch/tag/SHA), `path` (optional: subdirectory)

  2. **Git repositories** :




    { "source": "git", "url": "https://gitlab.example.com/tools/plugins.git" }
    { "source": "git", "url": "https://bitbucket.org/acme-corp/plugins.git", "ref": "production" }
    { "source": "git", "url": "ssh://[[email protected]](https://code.claude.com/cdn-cgi/l/email-protection)/plugins.git", "ref": "v3.1", "path": "approved" }


Fields: `url` (required), `ref` (optional: branch/tag/SHA), `path` (optional: subdirectory)

  3. **URL-based marketplaces** :




    { "source": "url", "url": "https://plugins.example.com/marketplace.json" }
    { "source": "url", "url": "https://cdn.example.com/marketplace.json", "headers": { "Authorization": "Bearer ${TOKEN}" } }


Fields: `url` (required), `headers` (optional: HTTP headers for authenticated access)

URL-based marketplaces only download the `marketplace.json` file. They do not download plugin files from the server. Plugins in URL-based marketplaces must use external sources (GitHub, npm, or git URLs) rather than relative paths. For plugins with relative paths, use a Git-based marketplace instead. See [Troubleshooting](https://code.claude.com/docs/en/plugin-marketplaces#plugins-with-relative-paths-fail-in-url-based-marketplaces) for details.

  4. **NPM packages** :




    { "source": "npm", "package": "@acme-corp/claude-plugins" }
    { "source": "npm", "package": "@acme-corp/approved-marketplace" }


Fields: `package` (required, supports scoped packages)

  5. **File paths** :




    { "source": "file", "path": "/usr/local/share/claude/acme-marketplace.json" }
    { "source": "file", "path": "/opt/acme-corp/plugins/marketplace.json" }


Fields: `path` (required: absolute path to marketplace.json file)

  6. **Directory paths** :




    { "source": "directory", "path": "/usr/local/share/claude/acme-plugins" }
    { "source": "directory", "path": "/opt/acme-corp/approved-marketplaces" }


Fields: `path` (required: absolute path to directory containing `.claude-plugin/marketplace.json`) **Configuration examples** : Example - Allow specific marketplaces only:




    {
      "strictKnownMarketplaces": [
        {
          "source": "github",
          "repo": "acme-corp/approved-plugins"
        },
        {
          "source": "github",
          "repo": "acme-corp/security-tools",
          "ref": "v2.0"
        },
        {
          "source": "url",
          "url": "https://plugins.example.com/marketplace.json"
        },
        {
          "source": "npm",
          "package": "@acme-corp/compliance-plugins"
        }
      ]
    }


Example - Disable all marketplace additions:




    {
      "strictKnownMarketplaces": []
    }


**Exact matching requirements** : Marketplace sources must match **exactly** for a user’s addition to be allowed. For git-based sources (`github` and `git`), this includes all optional fields:

  * The `repo` or `url` must match exactly
  * The `ref` field must match exactly (or both be undefined)
  * The `path` field must match exactly (or both be undefined)

Examples of sources that **do NOT match** :




    // These are DIFFERENT sources:
    { "source": "github", "repo": "acme-corp/plugins" }
    { "source": "github", "repo": "acme-corp/plugins", "ref": "main" }

    // These are also DIFFERENT:
    { "source": "github", "repo": "acme-corp/plugins", "path": "marketplace" }
    { "source": "github", "repo": "acme-corp/plugins" }


**Comparison with`extraKnownMarketplaces`**:

Aspect| `strictKnownMarketplaces`| `extraKnownMarketplaces`
---|---|---
**Purpose**|  Organizational policy enforcement| Team convenience
**Settings file**| `managed-settings.json` only| Any settings file
**Behavior**|  Blocks non-allowlisted additions| Auto-installs missing marketplaces
**When enforced**|  Before network/filesystem operations| After user trust prompt
**Can be overridden**|  No (highest precedence)| Yes (by higher precedence settings)
**Source format**|  Direct source object| Named marketplace with nested source
**Use case**|  Compliance, security restrictions| Onboarding, standardization

**Format difference** : `strictKnownMarketplaces` uses direct source objects:




    {
      "strictKnownMarketplaces": [
        { "source": "github", "repo": "acme-corp/plugins" }
      ]
    }


`extraKnownMarketplaces` requires named marketplaces:




    {
      "extraKnownMarketplaces": {
        "acme-tools": {
          "source": { "source": "github", "repo": "acme-corp/plugins" }
        }
      }
    }


**Important notes** :

  * Restrictions are checked BEFORE any network requests or filesystem operations
  * When blocked, users see clear error messages indicating the source is blocked by managed policy
  * The restriction applies only to adding NEW marketplaces; previously installed marketplaces remain accessible
  * Managed settings have the highest precedence and cannot be overridden

See [Managed marketplace restrictions](https://code.claude.com/docs/en/plugin-marketplaces#managed-marketplace-restrictions) for user-facing documentation.

### Managing plugins

Use the `/plugin` command to manage plugins interactively:

  * Browse available plugins from marketplaces
  * Install/uninstall plugins
  * Enable/disable plugins
  * View plugin details (commands, agents, hooks provided)
  * Add/remove marketplaces

Learn more about the plugin system in the [plugins documentation](https://code.claude.com/docs/en/plugins).

## Environment variables

Claude Code supports the following environment variables to control its behavior:

All environment variables can also be configured in `settings.json`. This is useful as a way to automatically set environment variables for each session, or to roll out a set of environment variables for your whole team or organization.

Variable| Purpose
---|---
`ANTHROPIC_AUTH_TOKEN`| API key sent as `X-Api-Key` header, typically for the Claude SDK (for interactive usage, run `/login`)
`ANTHROPIC_AUTH_TOKEN`| Custom value for the `Authorization` header (the value you set here will be prefixed with `Bearer `)
`ANTHROPIC_CUSTOM_HEADERS`| Custom headers you want to add to the request (in `Name: Value` format)
`ANTHROPIC_DEFAULT_HAIKU_MODEL`| See [Model configuration](https://code.claude.com/docs/en/model-config#environment-variables)
`ANTHROPIC_DEFAULT_OPUS_MODEL`| See [Model configuration](https://code.claude.com/docs/en/model-config#environment-variables)
`ANTHROPIC_DEFAULT_SONNET_MODEL`| See [Model configuration](https://code.claude.com/docs/en/model-config#environment-variables)
`ANTHROPIC_FOUNDRY_API_KEY`| API key for Microsoft Foundry authentication (see [Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry))
`ANTHROPIC_MODEL`| Name of the model setting to use (see [Model Configuration](https://code.claude.com/docs/en/model-config#environment-variables))
`ANTHROPIC_SMALL_FAST_MODEL`| [DEPRECATED] Name of [Haiku-class model for background tasks](https://code.claude.com/docs/en/costs)
`ANTHROPIC_SMALL_FAST_MODEL_AWS_REGION`| Override AWS region for the Haiku-class model when using Bedrock
`AWS_BEARER_TOKEN_BEDROCK`| Bedrock API key for authentication (see [Bedrock API keys](https://aws.amazon.com/blogs/machine-learning/accelerate-ai-development-with-amazon-bedrock-api-keys/))
`BASH_DEFAULT_TIMEOUT_MS`| Default timeout for long-running bash commands
`BASH_MAX_OUTPUT_LENGTH`| Maximum number of characters in bash outputs before they are middle-truncated
`BASH_MAX_TIMEOUT_MS`| Maximum timeout the model can set for long-running bash commands
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`| Set the percentage of context capacity (1-100) at which auto-compaction triggers. By default, auto-compaction triggers at approximately 95% capacity. Use lower values like `50` to compact earlier. Values above the default threshold have no effect. Applies to both main conversations and subagents. This percentage aligns with the `context_window.used_percentage` field available in [status line](https://code.claude.com/docs/en/statusline)
`CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR`| Return to the original working directory after each Bash command
`CLAUDE_CODE_API_KEY_HELPER_TTL_MS`| Interval in milliseconds at which credentials should be refreshed (when using `apiKeyHelper`)
`CLAUDE_CODE_CLIENT_CERT`| Path to client certificate file for mTLS authentication
`CLAUDE_CODE_CLIENT_KEY_PASSPHRASE`| Passphrase for encrypted CLAUDE_CODE_CLIENT_KEY (optional)
`CLAUDE_CODE_CLIENT_KEY`| Path to client private key file for mTLS authentication
`CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS`| Set to `1` to disable Anthropic API-specific `anthropic-beta` headers. Use this if experiencing issues like “Unexpected value(s) for the `anthropic-beta` header” when using an LLM gateway with third-party providers
`CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`| Set to `1` to disable all background task functionality, including the `run_in_background` parameter on Bash and subagent tools, auto-backgrounding, and the Ctrl+B shortcut
`CLAUDE_CODE_EXIT_AFTER_STOP_DELAY`| Time in milliseconds to wait after the query loop becomes idle before automatically exiting. Useful for automated workflows and scripts using SDK mode
`CLAUDE_CODE_PROXY_RESOLVES_HOSTS`| Set to `true` to allow the proxy to perform DNS resolution instead of the caller. Opt-in for environments where the proxy should handle hostname resolution
`CLAUDE_CODE_TMPDIR`| Override the temp directory used for internal temp files. Claude Code appends `/claude/` to this path. Default: `/tmp` on Unix/macOS, `os.tmpdir()` on Windows
`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC`| Equivalent of setting `DISABLE_AUTOUPDATER`, `DISABLE_BUG_COMMAND`, `DISABLE_ERROR_REPORTING`, and `DISABLE_TELEMETRY`
`CLAUDE_CODE_DISABLE_TERMINAL_TITLE`| Set to `1` to disable automatic terminal title updates based on conversation context
`CLAUDE_CODE_FILE_READ_MAX_OUTPUT_TOKENS`| Override the default token limit for file reads. Useful when you need to read larger files in full
`CLAUDE_CODE_HIDE_ACCOUNT_INFO`| Set to `1` to hide your email address and organization name from the Claude Code UI. Useful when streaming or recording
`CLAUDE_CODE_IDE_SKIP_AUTO_INSTALL`| Skip auto-installation of IDE extensions
`CLAUDE_CODE_MAX_OUTPUT_TOKENS`| Set the maximum number of output tokens for most requests. Default: 32,000. Maximum: 64,000. Increasing this value reduces the effective context window available before [auto-compaction](https://code.claude.com/docs/en/costs#reduce-token-usage) triggers.
`CLAUDE_CODE_OTEL_HEADERS_HELPER_DEBOUNCE_MS`| Interval for refreshing dynamic OpenTelemetry headers in milliseconds (default: 1740000 / 29 minutes). See [Dynamic headers](https://code.claude.com/docs/en/monitoring-usage#dynamic-headers)
`CLAUDE_CODE_SHELL`| Override automatic shell detection. Useful when your login shell differs from your preferred working shell (for example, `bash` vs `zsh`)
`CLAUDE_CODE_SHELL_PREFIX`| Command prefix to wrap all bash commands (for example, for logging or auditing). Example: `/path/to/logger.sh` will execute `/path/to/logger.sh <command>`
`CLAUDE_CODE_SKIP_BEDROCK_AUTH`| Skip AWS authentication for Bedrock (for example, when using an LLM gateway)
`CLAUDE_CODE_SKIP_FOUNDRY_AUTH`| Skip Azure authentication for Microsoft Foundry (for example, when using an LLM gateway)
`CLAUDE_CODE_SKIP_VERTEX_AUTH`| Skip Google authentication for Vertex (for example, when using an LLM gateway)
`CLAUDE_CODE_SUBAGENT_MODEL`| See [Model configuration](https://code.claude.com/docs/en/model-config)
`CLAUDE_CODE_USE_BEDROCK`| Use [Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
`CLAUDE_CODE_USE_FOUNDRY`| Use [Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry)
`CLAUDE_CODE_USE_VERTEX`| Use [Vertex](https://code.claude.com/docs/en/google-vertex-ai)
`CLAUDE_CONFIG_DIR`| Customize where Claude Code stores its configuration and data files
`DISABLE_AUTOUPDATER`| Set to `1` to disable automatic updates.
`DISABLE_BUG_COMMAND`| Set to `1` to disable the `/bug` command
`DISABLE_COST_WARNINGS`| Set to `1` to disable cost warning messages
`DISABLE_ERROR_REPORTING`| Set to `1` to opt out of Sentry error reporting
`DISABLE_NON_ESSENTIAL_MODEL_CALLS`| Set to `1` to disable model calls for non-critical paths like flavor text
`DISABLE_PROMPT_CACHING`| Set to `1` to disable prompt caching for all models (takes precedence over per-model settings)
`DISABLE_PROMPT_CACHING_HAIKU`| Set to `1` to disable prompt caching for Haiku models
`DISABLE_PROMPT_CACHING_OPUS`| Set to `1` to disable prompt caching for Opus models
`DISABLE_PROMPT_CACHING_SONNET`| Set to `1` to disable prompt caching for Sonnet models
`DISABLE_TELEMETRY`| Set to `1` to opt out of Statsig telemetry (note that Statsig events do not include user data like code, file paths, or bash commands)
`ENABLE_TOOL_SEARCH`| Controls [MCP tool search](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search). Values: `auto` (default, enables at 10% context), `auto:N` (custom threshold, e.g., `auto:5` for 5%), `true` (always on), `false` (disabled)
`FORCE_AUTOUPDATE_PLUGINS`| Set to `true` to force plugin auto-updates even when the main auto-updater is disabled via `DISABLE_AUTOUPDATER`
`HTTP_PROXY`| Specify HTTP proxy server for network connections
`HTTPS_PROXY`| Specify HTTPS proxy server for network connections
`IS_DEMO`| Set to `true` to enable demo mode: hides email and organization from the UI, skips onboarding, and hides internal commands. Useful for streaming or recording sessions
`MAX_MCP_OUTPUT_TOKENS`| Maximum number of tokens allowed in MCP tool responses. Claude Code displays a warning when output exceeds 10,000 tokens (default: 25000)
`MAX_THINKING_TOKENS`| Override the [extended thinking](https://docs.claude.com/en/docs/build-with-claude/extended-thinking) token budget. Thinking is enabled at max budget (31,999 tokens) by default. Use this to limit the budget (for example, `MAX_THINKING_TOKENS=10000`) or disable thinking entirely (`MAX_THINKING_TOKENS=0`). Extended thinking improves performance on complex reasoning and coding tasks but impacts [prompt caching efficiency](https://docs.claude.com/en/docs/build-with-claude/prompt-caching#caching-with-thinking-blocks).
`MCP_TIMEOUT`| Timeout in milliseconds for MCP server startup
`MCP_TOOL_TIMEOUT`| Timeout in milliseconds for MCP tool execution
`NO_PROXY`| List of domains and IPs to which requests will be directly issued, bypassing proxy
`SLASH_COMMAND_TOOL_CHAR_BUDGET`| Maximum number of characters for slash command metadata shown to the [Skill tool](https://code.claude.com/docs/en/slash-commands#skill-tool) (default: 15000)
`USE_BUILTIN_RIPGREP`| Set to `0` to use system-installed `rg` instead of `rg` included with Claude Code
`VERTEX_REGION_CLAUDE_3_5_HAIKU`| Override region for Claude 3.5 Haiku when using Vertex AI
`VERTEX_REGION_CLAUDE_3_7_SONNET`| Override region for Claude 3.7 Sonnet when using Vertex AI
`VERTEX_REGION_CLAUDE_4_0_OPUS`| Override region for Claude 4.0 Opus when using Vertex AI
`VERTEX_REGION_CLAUDE_4_0_SONNET`| Override region for Claude 4.0 Sonnet when using Vertex AI
`VERTEX_REGION_CLAUDE_4_1_OPUS`| Override region for Claude 4.1 Opus when using Vertex AI

## Tools available to Claude

Claude Code has access to a set of powerful tools that help it understand and modify your codebase:

Tool| Description| Permission Required
---|---|---
**AskUserQuestion**|  Asks multiple-choice questions to gather requirements or clarify ambiguity| No
**Bash**|  Executes shell commands in your environment (see Bash tool behavior below)| Yes
**TaskOutput**|  Retrieves output from a background task (bash shell or subagent)| No
**Edit**|  Makes targeted edits to specific files| Yes
**ExitPlanMode**|  Prompts the user to exit plan mode and start coding| Yes
**Glob**|  Finds files based on pattern matching| No
**Grep**|  Searches for patterns in file contents| No
**KillShell**|  Kills a running background bash shell by its ID| No
**MCPSearch**|  Searches for and loads MCP tools when [tool search](https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search) is enabled| No
**NotebookEdit**|  Modifies Jupyter notebook cells| Yes
**Read**|  Reads the contents of files| No
**Skill**|  Executes a [skill or slash command](https://code.claude.com/docs/en/slash-commands#skill-tool) within the main conversation| Yes
**Task**|  Runs a sub-agent to handle complex, multi-step tasks| No
**TodoWrite**|  Creates and manages structured task lists| No
**WebFetch**|  Fetches content from a specified URL| Yes
**WebSearch**|  Performs web searches with domain filtering| Yes
**Write**|  Creates or overwrites files| Yes

Permission rules can be configured using `/allowed-tools` or in [permission settings](https://code.claude.com/docs/en/settings#available-settings). Also see [Tool-specific permission rules](https://code.claude.com/docs/en/iam#tool-specific-permission-rules).

### Bash tool behavior

The Bash tool executes shell commands with the following persistence behavior:

  * **Working directory persists** : When Claude changes the working directory (for example, `cd /path/to/dir`), subsequent Bash commands will execute in that directory. You can use `CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR=1` to reset to the project directory after each command.
  * **Environment variables do NOT persist** : Environment variables set in one Bash command (for example, `export MY_VAR=value`) are **not** available in subsequent Bash commands. Each Bash command runs in a fresh shell environment.

To make environment variables available in Bash commands, you have **three options** : **Option 1: Activate environment before starting Claude Code** (simplest approach) Activate your virtual environment in your terminal before launching Claude Code:




    conda activate myenv
    # or: source /path/to/venv/bin/activate
    claude


This works for shell environments but environment variables set within Claude’s Bash commands will not persist between commands. **Option 2: Set CLAUDE_ENV_FILE before starting Claude Code** (persistent environment setup) Export the path to a shell script containing your environment setup:




    export CLAUDE_ENV_FILE=/path/to/env-setup.sh
    claude


Where `/path/to/env-setup.sh` contains:




    conda activate myenv
    # or: source /path/to/venv/bin/activate
    # or: export MY_VAR=value


Claude Code will source this file before each Bash command, making the environment persistent across all commands. **Option 3: Use a SessionStart hook** (project-specific configuration) Configure in `.claude/settings.json`:




    {
      "hooks": {
        "SessionStart": [{
          "matcher": "startup",
          "hooks": [{
            "type": "command",
            "command": "echo 'conda activate myenv' >> \"$CLAUDE_ENV_FILE\""
          }]
        }]
      }
    }


The hook writes to `$CLAUDE_ENV_FILE`, which is then sourced before each Bash command. This is ideal for team-shared project configurations. See [SessionStart hooks](https://code.claude.com/docs/en/hooks#persisting-environment-variables) for more details on Option 3.

### Extending tools with hooks

You can run custom commands before or after any tool executes using [Claude Code hooks](https://code.claude.com/docs/en/hooks-guide). For example, you could automatically run a Python formatter after Claude modifies Python files, or prevent modifications to production configuration files by blocking Write operations to certain paths.

## See also

  * [Identity and Access Management](https://code.claude.com/docs/en/iam#configuring-permissions) \- Learn about Claude Code’s permission system
  * [IAM and access control](https://code.claude.com/docs/en/iam#managed-settings) \- Managed policy configuration
  * [Troubleshooting](https://code.claude.com/docs/en/troubleshooting#auto-updater-issues) \- Solutions for common configuration issues



================================================================================
# Use Claude Code in VS Code

# Use Claude Code in VS Code

> **原文链接**: https://code.claude.com/docs/en/vs-code

---

![VS Code editor with the Claude Code extension panel open on the right side, showing a conversation with Claude](https://mintcdn.com/claude-code/-YhHHmtSxwr7W8gy/images/vs-code-extension-interface.jpg?fit=max&auto=format&n=-YhHHmtSxwr7W8gy&q=85&s=300652d5678c63905e6b0ea9e50835f8) The VS Code extension provides a native graphical interface for Claude Code, integrated directly into your IDE. This is the recommended way to use Claude Code in VS Code. With the extension, you can review and edit Claude’s plans before accepting them, auto-accept edits as they’re made, @-mention files with specific line ranges from your selection, access conversation history, and open multiple conversations in separate tabs or windows.

## Prerequisites

  * VS Code 1.98.0 or higher
  * An Anthropic account (you’ll sign in when you first open the extension). If you’re using a third-party provider like Amazon Bedrock or Google Vertex AI, see Use third-party providers instead.

You don’t need to install the Claude Code CLI first. However, some features like MCP server configuration require the CLI. See VS Code extension vs. Claude Code CLI for details.

## Install the extension

Click the link for your IDE to install directly:

  * [Install for VS Code](vscode:extension/anthropic.claude-code)
  * [Install for Cursor](cursor:extension/anthropic.claude-code)

Or in VS Code, press `Cmd+Shift+X` (Mac) or `Ctrl+Shift+X` (Windows/Linux) to open the Extensions view, search for “Claude Code”, and click **Install**.

You may need to restart VS Code or run “Developer: Reload Window” from the Command Palette after installation.

## Get started

Once installed, you can start using Claude Code through the VS Code interface:

1

Open the Claude Code panel

Throughout VS Code, the Spark icon indicates Claude Code: ![Spark icon](https://mintcdn.com/claude-code/mfM-EyoZGnQv8JTc/images/vs-code-spark-icon.svg?fit=max&auto=format&n=mfM-EyoZGnQv8JTc&q=85&s=a734d84e785140016672f08e0abb236c)The quickest way to open Claude is to click the Spark icon in the **Editor Toolbar** (top-right corner of the editor). The icon only appears when you have a file open.![VS Code editor showing the Spark icon in the Editor Toolbar](https://mintcdn.com/claude-code/mfM-EyoZGnQv8JTc/images/vs-code-editor-icon.png?fit=max&auto=format&n=mfM-EyoZGnQv8JTc&q=85&s=eb4540325d94664c51776dbbfec4cf02)Other ways to open Claude Code:

  * **Command Palette** : `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux), type “Claude Code”, and select an option like “Open in New Tab”
  * **Status Bar** : Click **✱ Claude Code** in the bottom-right corner of the window. This works even when no file is open.

You can drag the Claude panel to reposition it anywhere in VS Code. See Customize your workflow for details.

2

Send a prompt

Ask Claude to help with your code or files, whether that’s explaining how something works, debugging an issue, or making changes.

Select text in the editor and press `Alt+K` to insert an @-mention with the file path and line numbers directly into your prompt.

Here’s an example of asking about a particular line in a file:![VS Code editor with lines 2-3 selected in a Python file, and the Claude Code panel showing a question about those lines with an @-mention reference](https://mintcdn.com/claude-code/FVYz38sRY-VuoGHA/images/vs-code-send-prompt.png?fit=max&auto=format&n=FVYz38sRY-VuoGHA&q=85&s=ede3ed8d8d5f940e01c5de636d009cfd)

3

Review changes

When Claude wants to edit a file, it shows you a diff and asks for permission. You can accept, reject, or tell Claude what to do instead.![VS Code showing a diff of Claude's proposed changes with a permission prompt asking whether to make the edit](https://mintcdn.com/claude-code/FVYz38sRY-VuoGHA/images/vs-code-edits.png?fit=max&auto=format&n=FVYz38sRY-VuoGHA&q=85&s=e005f9b41c541c5c7c59c082f7c4841c)

For more ideas on what you can do with Claude Code, see [Common workflows](https://code.claude.com/docs/en/common-workflows).

## Customize your workflow

Once you’re up and running, you can reposition the Claude panel or switch to terminal mode.

### Change the layout

You can drag the Claude panel to reposition it anywhere in VS Code. Grab the panel’s tab or title bar and drag it to:

  * **Secondary sidebar** (default): The right side of the window
  * **Primary sidebar** : The left sidebar with icons for Explorer, Search, etc.
  * **Editor area** : Opens Claude as a tab alongside your files

The Spark icon only appears in the Activity Bar (left sidebar icons) when the Claude panel is docked to the left. Since Claude defaults to the right side, use the Editor Toolbar icon to open Claude.

### Switch to terminal mode

By default, the extension opens a graphical chat panel. If you prefer the CLI-style interface, open the [Use Terminal setting](vscode://settings/claudeCode.useTerminal) and check the box. You can also open VS Code settings (`Cmd+,` on Mac or `Ctrl+,` on Windows/Linux), go to Extensions → Claude Code, and check **Use Terminal**.

## VS Code commands and shortcuts

Open the Command Palette (`Cmd+Shift+P` on Mac or `Ctrl+Shift+P` on Windows/Linux) and type “Claude Code” to see all available VS Code commands for the Claude Code extension:

These are VS Code commands for controlling the extension. For Claude Code slash commands (like `/help` or `/compact`), not all CLI commands are available in the extension yet. See VS Code extension vs. Claude Code CLI for details.

Command| Shortcut| Description  
---|---|---  
Focus Input| `Cmd+Esc` (Mac) / `Ctrl+Esc` (Windows/Linux)| Toggle focus between editor and Claude  
Open in Side Bar| —| Open Claude in the left sidebar  
Open in Terminal| —| Open Claude in terminal mode  
Open in New Tab| `Cmd+Shift+Esc` (Mac) / `Ctrl+Shift+Esc` (Windows/Linux)| Open a new conversation as an editor tab  
Open in New Window| —| Open a new conversation in a separate window  
New Conversation| `Cmd+N` (Mac) / `Ctrl+N` (Windows/Linux)| Start a new conversation (when Claude is focused)  
Insert @-Mention Reference| `Alt+K`| Insert a reference to the current file (includes line numbers if text is selected)  
Show Logs| —| View extension debug logs  
Logout| —| Sign out of your Anthropic account  
  
Use **Open in New Tab** or **Open in New Window** to run multiple conversations simultaneously. Each tab or window maintains its own conversation history and context.

## Configure settings

The extension has two types of settings:

  * **Extension settings** : Open with `Cmd+,` (Mac) or `Ctrl+,` (Windows/Linux), then go to Extensions → Claude Code.

Setting| Description  
---|---  
Selected Model| Default model for new conversations. Change per-session with `/model`.  
Use Terminal| Launch Claude in terminal mode instead of graphical panel  
Initial Permission Mode| Controls approval prompts for file edits and commands. Defaults to `default` (ask before each action).  
Preferred Location| Default location: sidebar (right) or panel (new tab)  
Autosave| Auto-save files before Claude reads or writes them  
Use Ctrl+Enter to Send| Use Ctrl/Cmd+Enter instead of Enter to send prompts  
Enable New Conversation Shortcut| Enable Cmd/Ctrl+N to start a new conversation  
Respect Git Ignore| Exclude .gitignore patterns from file searches  
Environment Variables| Set environment variables for the Claude process. **Not recommended** —use [Claude Code settings](https://code.claude.com/docs/en/settings) instead so configuration is shared between extension and CLI.  
Disable Login Prompt| Skip authentication prompts (for third-party provider setups)  
Allow Dangerously Skip Permissions| Bypass all permission prompts. **Use with extreme caution** —recommended only for isolated sandboxes with no internet access.  
Claude Process Wrapper| Executable path used to launch the Claude process  
  
  * **Claude Code settings** (`~/.claude/settings.json`): These settings are shared between the VS Code extension and the CLI. Use this file for allowed commands and directories, environment variables, hooks, and MCP servers. See the [settings documentation](https://code.claude.com/docs/en/settings) for details.

## Use third-party providers

By default, Claude Code connects directly to Anthropic’s API. If your organization uses Amazon Bedrock, Google Vertex AI, or Microsoft Foundry to access Claude, configure the extension to use your provider instead:

1

Disable login prompt

Open the [Disable Login Prompt setting](vscode://settings/claudeCode.disableLoginPrompt) and check the box.You can also open VS Code settings (`Cmd+,` on Mac or `Ctrl+,` on Windows/Linux), search for “Claude Code login”, and check **Disable Login Prompt**.

2

Configure your provider

Follow the setup guide for your provider:

  * [Claude Code on Amazon Bedrock](https://code.claude.com/docs/en/amazon-bedrock)
  * [Claude Code on Google Vertex AI](https://code.claude.com/docs/en/google-vertex-ai)
  * [Claude Code on Microsoft Foundry](https://code.claude.com/docs/en/microsoft-foundry)

These guides cover configuring your provider in `~/.claude/settings.json`, which ensures your settings are shared between the VS Code extension and the CLI.

## VS Code extension vs. Claude Code CLI

The extension doesn’t yet have full feature parity with the CLI. If you need CLI-only features, you can run `claude` directly in VS Code’s integrated terminal.

Feature| CLI| VS Code Extension  
---|---|---  
Slash commands| [Full set](https://code.claude.com/docs/en/slash-commands)| Subset (type `/` to see available)  
MCP server config| Yes| No (configure via CLI, use in extension)  
Checkpoints| Yes| Coming soon  
`!` bash shortcut| Yes| No  
Tab completion| Yes| No  
  
### Run CLI in VS Code

To use the CLI while staying in VS Code, open the integrated terminal (`Ctrl+`` on Windows/Linux or `Cmd+`` on Mac) and run `claude`. The CLI automatically integrates with your IDE for features like diff viewing and diagnostic sharing. If using an external terminal, run `/ide` inside Claude Code to connect it to VS Code.

### Switch between extension and CLI

The extension and CLI share the same conversation history. To continue an extension conversation in the CLI, run `claude --resume` in the terminal. This opens an interactive picker where you can search for and select your conversation.

## Security considerations

With auto-edit permissions enabled, Claude Code can modify VS Code configuration files (like `settings.json` or `tasks.json`) that VS Code may execute automatically. This could potentially bypass Claude Code’s normal permission prompts. To reduce risk when working with untrusted code:

  * Enable [VS Code Restricted Mode](https://code.visualstudio.com/docs/editor/workspace-trust#_restricted-mode) for untrusted workspaces
  * Use manual approval mode instead of auto-accept for edits
  * Review changes carefully before accepting them

## Fix common issues

### Extension won’t install

  * Ensure you have a compatible version of VS Code (1.98.0 or later)
  * Check that VS Code has permission to install extensions
  * Try installing directly from the Marketplace website

### Spark icon not visible

The Spark icon appears in the **Editor Toolbar** (top-right of editor) when you have a file open. If you don’t see it:

  1. **Open a file** : The icon requires a file to be open—having just a folder open isn’t enough
  2. **Check VS Code version** : Requires 1.98.0 or higher (Help → About)
  3. **Restart VS Code** : Run “Developer: Reload Window” from the Command Palette
  4. **Disable conflicting extensions** : Temporarily disable other AI extensions (Cline, Continue, etc.)
  5. **Check workspace trust** : The extension doesn’t work in Restricted Mode

Alternatively, click ”✱ Claude Code” in the **Status Bar** (bottom-right corner)—this works even without a file open. You can also use the **Command Palette** (`Cmd+Shift+P` / `Ctrl+Shift+P`) and type “Claude Code”.

### Claude Code never responds

If Claude Code isn’t responding to your prompts:

  1. **Check your internet connection** : Ensure you have a stable internet connection
  2. **Start a new conversation** : Try starting a fresh conversation to see if the issue persists
  3. **Try the CLI** : Run `claude` from the terminal to see if you get more detailed error messages
  4. **File a bug report** : If the problem continues, [file an issue on GitHub](https://github.com/anthropics/claude-code/issues) with details about the error

### Standalone CLI not connecting to IDE

  * Ensure you’re running Claude Code from VS Code’s integrated terminal (not an external terminal)
  * Ensure the CLI for your IDE variant is installed:
    * VS Code: `code` command should be available
    * Cursor: `cursor` command should be available
    * Windsurf: `windsurf` command should be available
    * VSCodium: `codium` command should be available
  * If the command isn’t available, install it from the Command Palette → “Shell Command: Install ‘code’ command in PATH”

## Uninstall the extension

To uninstall the Claude Code extension:

  1. Open the Extensions view (`Cmd+Shift+X` on Mac or `Ctrl+Shift+X` on Windows/Linux)
  2. Search for “Claude Code”
  3. Click **Uninstall**

To also remove extension data and reset all settings:
    
    
    rm -rf ~/.vscode/globalStorage/anthropic.claude-code
    

For additional help, see the [troubleshooting guide](https://code.claude.com/docs/en/troubleshooting).



================================================================================
# JetBrains IDEs

# JetBrains IDEs

> **原文链接**: https://code.claude.com/docs/en/jetbrains

---

Claude Code integrates with JetBrains IDEs through a dedicated plugin, providing features like interactive diff viewing, selection context sharing, and more.

## Supported IDEs

The Claude Code plugin works with most JetBrains IDEs, including:

  * IntelliJ IDEA
  * PyCharm
  * Android Studio
  * WebStorm
  * PhpStorm
  * GoLand

## Features

  * **Quick launch** : Use `Cmd+Esc` (Mac) or `Ctrl+Esc` (Windows/Linux) to open Claude Code directly from your editor, or click the Claude Code button in the UI
  * **Diff viewing** : Code changes can be displayed directly in the IDE diff viewer instead of the terminal
  * **Selection context** : The current selection/tab in the IDE is automatically shared with Claude Code
  * **File reference shortcuts** : Use `Cmd+Option+K` (Mac) or `Alt+Ctrl+K` (Linux/Windows) to insert file references (for example, @File#L1-99)
  * **Diagnostic sharing** : Diagnostic errors (lint, syntax, etc.) from the IDE are automatically shared with Claude as you work

## Installation

### Marketplace Installation

Find and install the [Claude Code plugin](https://plugins.jetbrains.com/plugin/27310-claude-code-beta-) from the JetBrains marketplace and restart your IDE. If you haven’t installed Claude Code yet, see [our quickstart guide](https://code.claude.com/docs/en/quickstart) for installation instructions.

After installing the plugin, you may need to restart your IDE completely for it to take effect.

## Usage

### From Your IDE

Run `claude` from your IDE’s integrated terminal, and all integration features will be active.

### From External Terminals

Use the `/ide` command in any external terminal to connect Claude Code to your JetBrains IDE and activate all features:
    
    
    claude
    > /ide
    

If you want Claude to have access to the same files as your IDE, start Claude Code from the same directory as your IDE project root.

## Configuration

### Claude Code Settings

Configure IDE integration through Claude Code’s settings:

  1. Run `claude`
  2. Enter the `/config` command
  3. Set the diff tool to `auto` for automatic IDE detection

### Plugin Settings

Configure the Claude Code plugin by going to **Settings → Tools → Claude Code [Beta]** :

#### General Settings

  * **Claude command** : Specify a custom command to run Claude (for example, `claude`, `/usr/local/bin/claude`, or `npx @anthropic/claude`)
  * **Suppress notification for Claude command not found** : Skip notifications about not finding the Claude command
  * **Enable using Option+Enter for multi-line prompts** (macOS only): When enabled, Option+Enter inserts new lines in Claude Code prompts. Disable if experiencing issues with the Option key being captured unexpectedly (requires terminal restart)
  * **Enable automatic updates** : Automatically check for and install plugin updates (applied on restart)

For WSL users: Set `wsl -d Ubuntu -- bash -lic "claude"` as your Claude command (replace `Ubuntu` with your WSL distribution name)

#### ESC Key Configuration

If the ESC key doesn’t interrupt Claude Code operations in JetBrains terminals:

  1. Go to **Settings → Tools → Terminal**
  2. Either:
     * Uncheck “Move focus to the editor with Escape”, or
     * Click “Configure terminal keybindings” and delete the “Switch focus to Editor” shortcut
  3. Apply the changes

This allows the ESC key to properly interrupt Claude Code operations.

## Special Configurations

### Remote Development

When using JetBrains Remote Development, you must install the plugin in the remote host via **Settings → Plugin (Host)**.

The plugin must be installed on the remote host, not on your local client machine.

### WSL Configuration

WSL users may need additional configuration for IDE detection to work properly. See our [WSL troubleshooting guide](https://code.claude.com/docs/en/troubleshooting#jetbrains-ide-not-detected-on-wsl2) for detailed setup instructions.

WSL configuration may require:

  * Proper terminal configuration
  * Networking mode adjustments
  * Firewall settings updates

## Troubleshooting

### Plugin Not Working

  * Ensure you’re running Claude Code from the project root directory
  * Check that the JetBrains plugin is enabled in the IDE settings
  * Completely restart the IDE (you may need to do this multiple times)
  * For Remote Development, ensure the plugin is installed in the remote host

### IDE Not Detected

  * Verify the plugin is installed and enabled
  * Restart the IDE completely
  * Check that you’re running Claude Code from the integrated terminal
  * For WSL users, see the [WSL troubleshooting guide](https://code.claude.com/docs/en/troubleshooting#jetbrains-ide-not-detected-on-wsl2)

### Command Not Found

If clicking the Claude icon shows “command not found”:

  1. Verify Claude Code is installed: `npm list -g @anthropic-ai/claude-code`
  2. Configure the Claude command path in plugin settings
  3. For WSL users, use the WSL command format mentioned in the configuration section

## Security Considerations

When Claude Code runs in a JetBrains IDE with auto-edit permissions enabled, it may be able to modify IDE configuration files that can be automatically executed by your IDE. This may increase the risk of running Claude Code in auto-edit mode and allow bypassing Claude Code’s permission prompts for bash execution. When running in JetBrains IDEs, consider:

  * Using manual approval mode for edits
  * Taking extra care to ensure Claude is only used with trusted prompts
  * Being aware of which files Claude Code has access to modify

For additional help, see our [troubleshooting guide](https://code.claude.com/docs/en/troubleshooting).



================================================================================
# Quickstart

# Quickstart

> **原文链接**: https://code.claude.com/docs/en/quickstart

---

This quickstart guide will have you using AI-powered coding assistance in just a few minutes. By the end, you’ll understand how to use Claude Code for common development tasks.

## Before you begin

Make sure you have:

  * A terminal or command prompt open
  * A code project to work with
  * A [Claude subscription](https://claude.com/pricing) (Pro, Max, Teams, or Enterprise) or [Claude Console](https://console.anthropic.com/) account

## Step 1: Install Claude Code

To install Claude Code, use one of the following methods:

  * Native Install (Recommended)

  * Homebrew

  * WinGet

**macOS, Linux, WSL:**
    
    
     curl -fsSL https://claude.ai/install.sh | bash
    

**Windows PowerShell:**
    
    
     irm https://claude.ai/install.ps1 | iex
    

**Windows CMD:**


    
    
    curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
    

Native installations automatically update in the background to keep you on the latest version.


    
    
    brew install --cask claude-code
    

Homebrew installations do not auto-update. Run `brew upgrade claude-code` periodically to get the latest features and security fixes.


    
    
    winget install Anthropic.ClaudeCode
    

WinGet installations do not auto-update. Run `winget upgrade Anthropic.ClaudeCode` periodically to get the latest features and security fixes.

## Step 2: Log in to your account

Claude Code requires an account to use. When you start an interactive session with the `claude` command, you’ll need to log in:


    
    
    claude
    # You'll be prompted to log in on first use
    


    
    
    /login
    # Follow the prompts to log in with your account
    

You can log in using any of these account types:

  * [Claude Pro, Max, Teams, or Enterprise](https://claude.com/pricing) (recommended)
  * [Claude Console](https://console.anthropic.com/) (API access with pre-paid credits)

Once logged in, your credentials are stored and you won’t need to log in again.

When you first authenticate Claude Code with your Claude Console account, a workspace called “Claude Code” is automatically created for you. This workspace provides centralized cost tracking and management for all Claude Code usage in your organization.

You can have both account types under the same email address. If you need to log in again or switch accounts, use the `/login` command within Claude Code.

## Step 3: Start your first session

Open your terminal in any project directory and start Claude Code:


    
    
    cd /path/to/your/project
    claude
    

You’ll see the Claude Code welcome screen with your session information, recent conversations, and latest updates. Type `/help` for available commands or `/resume` to continue a previous conversation.

After logging in (Step 2), your credentials are stored on your system. Learn more in [Credential Management](https://code.claude.com/docs/en/iam#credential-management).

## Step 4: Ask your first question

Let’s start with understanding your codebase. Try one of these commands:


    
    
    > what does this project do?
    

Claude will analyze your files and provide a summary. You can also ask more specific questions:


    
    
    > what technologies does this project use?
    


    
    
    > where is the main entry point?
    


    
    
    > explain the folder structure
    

You can also ask Claude about its own capabilities:


    
    
    > what can Claude Code do?
    


    
    
    > how do I use slash commands in Claude Code?
    


    
    
    > can Claude Code work with Docker?
    

Claude Code reads your files as needed - you don’t have to manually add context. Claude also has access to its own documentation and can answer questions about its features and capabilities.

## Step 5: Make your first code change

Now let’s make Claude Code do some actual coding. Try a simple task:


    
    
    > add a hello world function to the main file
    

Claude Code will:

  1. Find the appropriate file
  2. Show you the proposed changes
  3. Ask for your approval
  4. Make the edit

Claude Code always asks for permission before modifying files. You can approve individual changes or enable “Accept all” mode for a session.

## Step 6: Use Git with Claude Code

Claude Code makes Git operations conversational:


    
    
    > what files have I changed?
    


    
    
    > commit my changes with a descriptive message
    

You can also prompt for more complex Git operations:


    
    
    > create a new branch called feature/quickstart
    


    
    
    > show me the last 5 commits
    


    
    
    > help me resolve merge conflicts
    

## Step 7: Fix a bug or add a feature

Claude is proficient at debugging and feature implementation. Describe what you want in natural language:


    
    
    > add input validation to the user registration form
    

Or fix existing issues:


    
    
    > there's a bug where users can submit empty forms - fix it
    

Claude Code will:

  * Locate the relevant code
  * Understand the context
  * Implement a solution
  * Run tests if available

## Step 8: Test out other common workflows

There are a number of ways to work with Claude: **Refactor code**


    
    
    > refactor the authentication module to use async/await instead of callbacks
    

**Write tests**


    
    
    > write unit tests for the calculator functions
    

**Update documentation**


    
    
    > update the README with installation instructions
    

**Code review**


    
    
    > review my changes and suggest improvements
    

**Remember** : Claude Code is your AI pair programmer. Talk to it like you would a helpful colleague - describe what you want to achieve, and it will help you get there.

## Essential commands

Here are the most important commands for daily use:

Command| What it does| Example  
---|---|---  
`claude`| Start interactive mode| `claude`  
`claude "task"`| Run a one-time task| `claude "fix the build error"`  
`claude -p "query"`| Run one-off query, then exit| `claude -p "explain this function"`  
`claude -c`| Continue most recent conversation in current directory| `claude -c`  
`claude -r`| Resume a previous conversation| `claude -r`  
`claude commit`| Create a Git commit| `claude commit`  
`/clear`| Clear conversation history| `> /clear`  
`/help`| Show available commands| `> /help`  
`exit` or Ctrl+C| Exit Claude Code| `> exit`  
  
See the [CLI reference](https://code.claude.com/docs/en/cli-reference) for a complete list of commands.

## Pro tips for beginners

Be specific with your requests

Instead of: “fix the bug”Try: “fix the login bug where users see a blank screen after entering wrong credentials”

Use step-by-step instructions

Break complex tasks into steps:


    
    
    > 1. create a new database table for user profiles
    


    
    
    > 2. create an API endpoint to get and update user profiles
    


    
    
    > 3. build a webpage that allows users to see and edit their information
    

Let Claude explore first

Before making changes, let Claude understand your code:


    
    
    > analyze the database schema
    


    
    
    > build a dashboard showing products that are most frequently returned by our UK customers
    

Save time with shortcuts

  * Press `?` to see all available keyboard shortcuts
  * Use Tab for command completion
  * Press ↑ for command history
  * Type `/` to see all slash commands

## What’s next?

Now that you’ve learned the basics, explore more advanced features:

## [Common workflowsStep-by-step guides for common tasks](https://code.claude.com/docs/en/common-workflows)## [CLI referenceMaster all commands and options](https://code.claude.com/docs/en/cli-reference)## [ConfigurationCustomize Claude Code for your workflow](https://code.claude.com/docs/en/settings)## [Claude Code on the webRun tasks asynchronously in the cloud](https://code.claude.com/docs/en/claude-code-on-the-web)## [About Claude CodeLearn more on claude.com](https://claude.com/product/claude-code)

## Getting help

  * **In Claude Code** : Type `/help` or ask “how do I…”
  * **Documentation** : You’re here! Browse other guides
  * **Community** : Join our [Discord](https://www.anthropic.com/discord) for tips and support




================================================================================
# CLI reference

# CLI reference

> **原文链接**: https://code.claude.com/docs/en/cli-reference

---

## CLI commands

Command| Description| Example  
---|---|---  
`claude`| Start interactive REPL| `claude`  
`claude "query"`| Start REPL with initial prompt| `claude "explain this project"`  
`claude -p "query"`| Query via SDK, then exit| `claude -p "explain this function"`  
`cat file | claude -p "query"`| Process piped content| `cat logs.txt | claude -p "explain"`  
`claude -c`| Continue most recent conversation in current directory| `claude -c`  
`claude -c -p "query"`| Continue via SDK| `claude -c -p "Check for type errors"`  
`claude -r "<session>" "query"`| Resume session by ID or name| `claude -r "auth-refactor" "Finish this PR"`  
`claude update`| Update to latest version| `claude update`  
`claude mcp`| Configure Model Context Protocol (MCP) servers| See the [Claude Code MCP documentation](https://code.claude.com/docs/en/mcp).  
  
## CLI flags

Customize Claude Code’s behavior with these command-line flags:

Flag| Description| Example  
---|---|---  
`--add-dir`| Add additional working directories for Claude to access (validates each path exists as a directory)| `claude --add-dir ../apps ../lib`  
`--agent`| Specify an agent for the current session (overrides the `agent` setting)| `claude --agent my-custom-agent`  
`--agents`| Define custom [subagents](https://code.claude.com/docs/en/sub-agents) dynamically via JSON (see below for format)| `claude --agents '{"reviewer":{"description":"Reviews code","prompt":"You are a code reviewer"}}'`  
`--allow-dangerously-skip-permissions`| Enable permission bypassing as an option without immediately activating it. Allows composing with `--permission-mode` (use with caution)| `claude --permission-mode plan --allow-dangerously-skip-permissions`  
`--allowedTools`| Tools that execute without prompting for permission. To restrict which tools are available, use `--tools` instead| `"Bash(git log:*)" "Bash(git diff:*)" "Read"`  
`--append-system-prompt`| Append custom text to the end of the default system prompt (works in both interactive and print modes)| `claude --append-system-prompt "Always use TypeScript"`  
`--append-system-prompt-file`| Load additional system prompt text from a file and append to the default prompt (print mode only)| `claude -p --append-system-prompt-file ./extra-rules.txt "query"`  
`--betas`| Beta headers to include in API requests (API key users only)| `claude --betas interleaved-thinking`  
`--chrome`| Enable [Chrome browser integration](https://code.claude.com/docs/en/chrome) for web automation and testing| `claude --chrome`  
`--continue`, `-c`| Load the most recent conversation in the current directory| `claude --continue`  
`--dangerously-skip-permissions`| Skip all permission prompts (use with caution)| `claude --dangerously-skip-permissions`  
`--debug`| Enable debug mode with optional category filtering (for example, `"api,hooks"` or `"!statsig,!file"`)| `claude --debug "api,mcp"`  
`--disable-slash-commands`| Disable all skills and slash commands for this session| `claude --disable-slash-commands`  
`--disallowedTools`| Tools that are removed from the model’s context and cannot be used| `"Bash(git log:*)" "Bash(git diff:*)" "Edit"`  
`--fallback-model`| Enable automatic fallback to specified model when default model is overloaded (print mode only)| `claude -p --fallback-model sonnet "query"`  
`--fork-session`| When resuming, create a new session ID instead of reusing the original (use with `--resume` or `--continue`)| `claude --resume abc123 --fork-session`  
`--ide`| Automatically connect to IDE on startup if exactly one valid IDE is available| `claude --ide`  
`--include-partial-messages`| Include partial streaming events in output (requires `--print` and `--output-format=stream-json`)| `claude -p --output-format stream-json --include-partial-messages "query"`  
`--input-format`| Specify input format for print mode (options: `text`, `stream-json`)| `claude -p --output-format json --input-format stream-json`  
`--json-schema`| Get validated JSON output matching a JSON Schema after agent completes its workflow (print mode only, see [Agent SDK Structured Outputs](https://docs.claude.com/en/docs/agent-sdk/structured-outputs))| `claude -p --json-schema '{"type":"object","properties":{...}}' "query"`  
`--max-budget-usd`| Maximum dollar amount to spend on API calls before stopping (print mode only)| `claude -p --max-budget-usd 5.00 "query"`  
`--max-turns`| Limit the number of agentic turns (print mode only). Exits with an error when the limit is reached. No limit by default| `claude -p --max-turns 3 "query"`  
`--mcp-config`| Load MCP servers from JSON files or strings (space-separated)| `claude --mcp-config ./mcp.json`  
`--model`| Sets the model for the current session with an alias for the latest model (`sonnet` or `opus`) or a model’s full name| `claude --model claude-sonnet-4-5-20250929`  
`--no-chrome`| Disable [Chrome browser integration](https://code.claude.com/docs/en/chrome) for this session| `claude --no-chrome`  
`--no-session-persistence`| Disable session persistence so sessions are not saved to disk and cannot be resumed (print mode only)| `claude -p --no-session-persistence "query"`  
`--output-format`| Specify output format for print mode (options: `text`, `json`, `stream-json`)| `claude -p "query" --output-format json`  
`--permission-mode`| Begin in a specified [permission mode](https://code.claude.com/docs/en/iam#permission-modes)| `claude --permission-mode plan`  
`--permission-prompt-tool`| Specify an MCP tool to handle permission prompts in non-interactive mode| `claude -p --permission-prompt-tool mcp_auth_tool "query"`  
`--plugin-dir`| Load plugins from directories for this session only (repeatable)| `claude --plugin-dir ./my-plugins`  
`--print`, `-p`| Print response without interactive mode (see [SDK documentation](https://docs.claude.com/en/docs/agent-sdk) for programmatic usage details)| `claude -p "query"`  
`--remote`| Create a new [web session](https://code.claude.com/docs/en/claude-code-on-the-web) on claude.ai with the provided task description| `claude --remote "Fix the login bug"`  
`--resume`, `-r`| Resume a specific session by ID or name, or show an interactive picker to choose a session| `claude --resume auth-refactor`  
`--session-id`| Use a specific session ID for the conversation (must be a valid UUID)| `claude --session-id "550e8400-e29b-41d4-a716-446655440000"`  
`--setting-sources`| Comma-separated list of setting sources to load (`user`, `project`, `local`)| `claude --setting-sources user,project`  
`--settings`| Path to a settings JSON file or a JSON string to load additional settings from| `claude --settings ./settings.json`  
`--strict-mcp-config`| Only use MCP servers from `--mcp-config`, ignoring all other MCP configurations| `claude --strict-mcp-config --mcp-config ./mcp.json`  
`--system-prompt`| Replace the entire system prompt with custom text (works in both interactive and print modes)| `claude --system-prompt "You are a Python expert"`  
`--system-prompt-file`| Load system prompt from a file, replacing the default prompt (print mode only)| `claude -p --system-prompt-file ./custom-prompt.txt "query"`  
`--teleport`| Resume a [web session](https://code.claude.com/docs/en/claude-code-on-the-web) in your local terminal| `claude --teleport`  
`--tools`| Restrict which built-in tools Claude can use (works in both interactive and print modes). Use `""` to disable all, `"default"` for all, or tool names like `"Bash,Edit,Read"`| `claude --tools "Bash,Edit,Read"`  
`--verbose`| Enable verbose logging, shows full turn-by-turn output (helpful for debugging in both print and interactive modes)| `claude --verbose`  
`--version`, `-v`| Output the version number| `claude -v`  
  
The `--output-format json` flag is particularly useful for scripting and automation, allowing you to parse Claude’s responses programmatically.

### Agents flag format

The `--agents` flag accepts a JSON object that defines one or more custom subagents. Each subagent requires a unique name (as the key) and a definition object with the following fields:

Field| Required| Description  
---|---|---  
`description`| Yes| Natural language description of when the subagent should be invoked  
`prompt`| Yes| The system prompt that guides the subagent’s behavior  
`tools`| No| Array of specific tools the subagent can use (for example, `["Read", "Edit", "Bash"]`). If omitted, inherits all tools  
`model`| No| Model alias to use: `sonnet`, `opus`, or `haiku`. If omitted, uses the default subagent model  
  
Example:
    
    
    claude --agents '{
      "code-reviewer": {
        "description": "Expert code reviewer. Use proactively after code changes.",
        "prompt": "You are a senior code reviewer. Focus on code quality, security, and best practices.",
        "tools": ["Read", "Grep", "Glob", "Bash"],
        "model": "sonnet"
      },
      "debugger": {
        "description": "Debugging specialist for errors and test failures.",
        "prompt": "You are an expert debugger. Analyze errors, identify root causes, and provide fixes."
      }
    }'
    

For more details on creating and using subagents, see the [subagents documentation](https://code.claude.com/docs/en/sub-agents).

### System prompt flags

Claude Code provides four flags for customizing the system prompt, each serving a different purpose:

Flag| Behavior| Modes| Use Case  
---|---|---|---  
`--system-prompt`| **Replaces** entire default prompt| Interactive + Print| Complete control over Claude’s behavior and instructions  
`--system-prompt-file`| **Replaces** with file contents| Print only| Load prompts from files for reproducibility and version control  
`--append-system-prompt`| **Appends** to default prompt| Interactive + Print| Add specific instructions while keeping default Claude Code behavior  
`--append-system-prompt-file`| **Appends** file contents to default prompt| Print only| Load additional instructions from files while keeping defaults  
  
**When to use each:**

  * **`--system-prompt`** : Use when you need complete control over Claude’s system prompt. This removes all default Claude Code instructions, giving you a blank slate.
        
        claude --system-prompt "You are a Python expert who only writes type-annotated code"
        

  * **`--system-prompt-file`** : Use when you want to load a custom prompt from a file, useful for team consistency or version-controlled prompt templates.


        
        claude -p --system-prompt-file ./prompts/code-review.txt "Review this PR"
        

  * **`--append-system-prompt`** : Use when you want to add specific instructions while keeping Claude Code’s default capabilities intact. This is the safest option for most use cases.


        
        claude --append-system-prompt "Always use TypeScript and include JSDoc comments"
        

  * **`--append-system-prompt-file`** : Use when you want to append instructions from a file while keeping Claude Code’s defaults. Useful for version-controlled additions.


        
        claude -p --append-system-prompt-file ./prompts/style-rules.txt "Review this PR"
        

`--system-prompt` and `--system-prompt-file` are mutually exclusive. The append flags can be used together with either replacement flag. For most use cases, `--append-system-prompt` or `--append-system-prompt-file` is recommended as they preserve Claude Code’s built-in capabilities while adding your custom requirements. Use `--system-prompt` or `--system-prompt-file` only when you need complete control over the system prompt.

## See also

  * [Chrome extension](https://code.claude.com/docs/en/chrome) \- Browser automation and web testing
  * [Interactive mode](https://code.claude.com/docs/en/interactive-mode) \- Shortcuts, input modes, and interactive features
  * [Slash commands](https://code.claude.com/docs/en/slash-commands) \- Interactive session commands
  * [Quickstart guide](https://code.claude.com/docs/en/quickstart) \- Getting started with Claude Code
  * [Common workflows](https://code.claude.com/docs/en/common-workflows) \- Advanced workflows and patterns
  * [Settings](https://code.claude.com/docs/en/settings) \- Configuration options
  * [SDK documentation](https://docs.claude.com/en/docs/agent-sdk) \- Programmatic usage and integrations




---

## 文档来源 (Sources)

1. **Agent Skills**
   - 原文链接: https://code.claude.com/docs/en/skills
   - 路径: `md_docs/Claude_Code_Docs:latest/Agent Skills/docContent.md`

2. **Hooks reference**
   - 原文链接: https://code.claude.com/docs/en/hooks
   - 路径: `md_docs/Claude_Code_Docs:latest/Hooks reference/docContent.md`

3. **Get started with Claude Code hooks**
   - 原文链接: https://code.claude.com/docs/en/hooks-guide
   - 路径: `md_docs/Claude_Code_Docs:latest/Get started with Claude Code hooks/docContent.md`

4. **Slash commands**
   - 原文链接: https://code.claude.com/docs/en/slash-commands
   - 路径: `md_docs/Claude_Code_Docs:latest/Slash commands/docContent.md`

5. **Connect Claude Code to tools via MCP**
   - 原文链接: https://code.claude.com/docs/en/mcp
   - 路径: `md_docs/Claude_Code_Docs:latest/Connect Claude Code to tools via MCP/docContent.md`

6. **Claude Code settings**
   - 原文链接: https://code.claude.com/docs/en/settings
   - 路径: `md_docs/Claude_Code_Docs:latest/Claude Code settings/docContent.md`

7. **Use Claude Code in VS Code**
   - 原文链接: https://code.claude.com/docs/en/vs-code
   - 路径: `md_docs/Claude_Code_Docs:latest/Use Claude Code in VS Code/docContent.md`

8. **JetBrains IDEs**
   - 原文链接: https://code.claude.com/docs/en/jetbrains
   - 路径: `md_docs/Claude_Code_Docs:latest/JetBrains IDEs/docContent.md`

9. **Quickstart**
   - 原文链接: https://code.claude.com/docs/en/quickstart
   - 路径: `md_docs/Claude_Code_Docs:latest/Quickstart/docContent.md`

10. **CLI reference**
   - 原文链接: https://code.claude.com/docs/en/cli-reference
   - 路径: `md_docs/Claude_Code_Docs:latest/CLI reference/docContent.md`
