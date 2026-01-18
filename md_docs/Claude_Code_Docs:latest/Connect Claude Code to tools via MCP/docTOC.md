# Connect Claude Code to tools via MCP

原文链接: https://code.claude.com/docs/en/mcp

提取的锚点数量: 43

## 1. What you can do with MCP：https://code.claude.com/docs/en/mcp#what-you-can-do-with-mcp

## 2. Popular MCP servers：https://code.claude.com/docs/en/mcp#popular-mcp-servers

## 3. Installing MCP servers：https://code.claude.com/docs/en/mcp#installing-mcp-servers

### 3.1. Option 1: Add a remote HTTP server：https://code.claude.com/docs/en/mcp#option-1%3A-add-a-remote-http-server

### 3.2. Option 2: Add a remote SSE server：https://code.claude.com/docs/en/mcp#option-2%3A-add-a-remote-sse-server

### 3.3. Option 3: Add a local stdio server：https://code.claude.com/docs/en/mcp#option-3%3A-add-a-local-stdio-server

### 3.4. Managing your servers：https://code.claude.com/docs/en/mcp#managing-your-servers

### 3.5. Dynamic tool updates：https://code.claude.com/docs/en/mcp#dynamic-tool-updates

### 3.6. Plugin-provided MCP servers：https://code.claude.com/docs/en/mcp#plugin-provided-mcp-servers

## 4. MCP installation scopes：https://code.claude.com/docs/en/mcp#mcp-installation-scopes

### 4.1. Local scope：https://code.claude.com/docs/en/mcp#local-scope

### 4.2. Project scope：https://code.claude.com/docs/en/mcp#project-scope

### 4.3. User scope：https://code.claude.com/docs/en/mcp#user-scope

### 4.4. Choosing the right scope：https://code.claude.com/docs/en/mcp#choosing-the-right-scope

### 4.5. Scope hierarchy and precedence：https://code.claude.com/docs/en/mcp#scope-hierarchy-and-precedence

### 4.6. Environment variable expansion in .mcp.json：https://code.claude.com/docs/en/mcp#environment-variable-expansion-in-mcp-json

## 5. Practical examples：https://code.claude.com/docs/en/mcp#practical-examples

### 5.1. Example: Monitor errors with Sentry：https://code.claude.com/docs/en/mcp#example%3A-monitor-errors-with-sentry

### 5.2. Example: Connect to GitHub for code reviews：https://code.claude.com/docs/en/mcp#example%3A-connect-to-github-for-code-reviews

### 5.3. Example: Query your PostgreSQL database：https://code.claude.com/docs/en/mcp#example%3A-query-your-postgresql-database

## 6. Authenticate with remote MCP servers：https://code.claude.com/docs/en/mcp#authenticate-with-remote-mcp-servers

## 7. Add MCP servers from JSON configuration：https://code.claude.com/docs/en/mcp#add-mcp-servers-from-json-configuration

## 8. Import MCP servers from Claude Desktop：https://code.claude.com/docs/en/mcp#import-mcp-servers-from-claude-desktop

## 9. Use Claude Code as an MCP server：https://code.claude.com/docs/en/mcp#use-claude-code-as-an-mcp-server

## 10. MCP output limits and warnings：https://code.claude.com/docs/en/mcp#mcp-output-limits-and-warnings

## 11. Use MCP resources：https://code.claude.com/docs/en/mcp#use-mcp-resources

### 11.1. Reference MCP resources：https://code.claude.com/docs/en/mcp#reference-mcp-resources

## 12. Scale with MCP Tool Search：https://code.claude.com/docs/en/mcp#scale-with-mcp-tool-search

### 12.1. How it works：https://code.claude.com/docs/en/mcp#how-it-works

### 12.2. For MCP server authors：https://code.claude.com/docs/en/mcp#for-mcp-server-authors

### 12.3. Configure tool search：https://code.claude.com/docs/en/mcp#configure-tool-search

## 13. Use MCP prompts as slash commands：https://code.claude.com/docs/en/mcp#use-mcp-prompts-as-slash-commands

### 13.1. Execute MCP prompts：https://code.claude.com/docs/en/mcp#execute-mcp-prompts

## 14. Managed MCP configuration：https://code.claude.com/docs/en/mcp#managed-mcp-configuration

### 14.1. Option 1: Exclusive control with managed-mcp.json：https://code.claude.com/docs/en/mcp#option-1%3A-exclusive-control-with-managed-mcp-json

### 14.2. Option 2: Policy-based control with allowlists and denylists：https://code.claude.com/docs/en/mcp#option-2%3A-policy-based-control-with-allowlists-and-denylists

#### 14.2.1. Restriction options：https://code.claude.com/docs/en/mcp#restriction-options

#### 14.2.2. Example configuration：https://code.claude.com/docs/en/mcp#example-configuration

#### 14.2.3. How command-based restrictions work：https://code.claude.com/docs/en/mcp#how-command-based-restrictions-work

#### 14.2.4. How URL-based restrictions work：https://code.claude.com/docs/en/mcp#how-url-based-restrictions-work

#### 14.2.5. Allowlist behavior (allowedMcpServers)：https://code.claude.com/docs/en/mcp#allowlist-behavior-allowedmcpservers

#### 14.2.6. Denylist behavior (deniedMcpServers)：https://code.claude.com/docs/en/mcp#denylist-behavior-deniedmcpservers

#### 14.2.7. Important notes：https://code.claude.com/docs/en/mcp#important-notes

