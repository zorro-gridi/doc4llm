# Claude Code overview - Claude Code Docs

> **原文链接**: https://code.claude.com/docs/en/

---

## Get started in 30 seconds

Prerequisites:

  * A [Claude subscription](https://claude.com/pricing) (Pro, Max, Teams, or Enterprise) or [Claude Console](https://console.anthropic.com/) account

**Install Claude Code:** To install Claude Code, use one of the following methods:

  * Native Install (Recommended)

  * Homebrew

  * WinGet

**macOS, Linux, WSL:**
    
    
     curl -fsSL https://claude.ai/install.sh | bash
    

**Windows PowerShell:**
    
    
     irm https://claude.ai/install.ps1 | iex
    

**Windows CMD:**


    
    
    curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
    


    
    
    brew install --cask claude-code
    


    
    
    winget install Anthropic.ClaudeCode
    

**Start using Claude Code:**


    
    
    cd your-project
    claude
    

You’ll be prompted to log in on first use. That’s it! [Continue with Quickstart (5 minutes) →](https://code.claude.com/docs/en/quickstart)

Claude Code automatically keeps itself up to date. See [advanced setup](https://code.claude.com/docs/en/setup) for installation options, manual updates, or uninstallation instructions. Visit [troubleshooting](https://code.claude.com/docs/en/troubleshooting) if you hit issues.

## What Claude Code does for you

  * **Build features from descriptions** : Tell Claude what you want to build in plain English. It will make a plan, write the code, and ensure it works.
  * **Debug and fix issues** : Describe a bug or paste an error message. Claude Code will analyze your codebase, identify the problem, and implement a fix.
  * **Navigate any codebase** : Ask anything about your team’s codebase, and get a thoughtful answer back. Claude Code maintains awareness of your entire project structure, can find up-to-date information from the web, and with [MCP](https://code.claude.com/docs/en/mcp) can pull from external data sources like Google Drive, Figma, and Slack.
  * **Automate tedious tasks** : Fix fiddly lint issues, resolve merge conflicts, and write release notes. Do all this in a single command from your developer machines, or automatically in CI.

## Why developers love Claude Code

  * **Works in your terminal** : Not another chat window. Not another IDE. Claude Code meets you where you already work, with the tools you already love.
  * **Takes action** : Claude Code can directly edit files, run commands, and create commits. Need more? [MCP](https://code.claude.com/docs/en/mcp) lets Claude read your design docs in Google Drive, update your tickets in Jira, or use _your_ custom developer tooling.
  * **Unix philosophy** : Claude Code is composable and scriptable. `tail -f app.log | claude -p "Slack me if you see any anomalies appear in this log stream"` _works_. Your CI can run `claude -p "If there are new text strings, translate them into French and raise a PR for @lang-fr-team to review"`.
  * **Enterprise-ready** : Use the Claude API, or host on AWS or GCP. Enterprise-grade [security](https://code.claude.com/docs/en/security), [privacy](https://code.claude.com/docs/en/data-usage), and [compliance](https://trust.anthropic.com/) is built-in.
