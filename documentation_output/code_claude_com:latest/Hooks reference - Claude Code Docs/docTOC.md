# Hooks reference - Claude Code Docs

原文链接: https://code.claude.com/docs/en/hooks

提取的锚点数量: 78

- 0.0.0.1. Skip to main content：https://code.claude.com/docs/en/hooks#content-area
## 1. Configuration：https://code.claude.com/docs/en/hooks#configuration

### 1.1. Structure：https://code.claude.com/docs/en/hooks#structure

### 1.2. Project-Specific Hook Scripts：https://code.claude.com/docs/en/hooks#project-specific-hook-scripts

### 1.3. Plugin hooks：https://code.claude.com/docs/en/hooks#plugin-hooks

### 1.4. Hooks in Skills, Agents, and Slash Commands：https://code.claude.com/docs/en/hooks#hooks-in-skills%2C-agents%2C-and-slash-commands

## 2. Prompt-Based Hooks：https://code.claude.com/docs/en/hooks#prompt-based-hooks

### 2.1. How prompt-based hooks work：https://code.claude.com/docs/en/hooks#how-prompt-based-hooks-work

### 2.2. Configuration：https://code.claude.com/docs/en/hooks#configuration-2

### 2.3. Response schema：https://code.claude.com/docs/en/hooks#response-schema

### 2.4. Supported hook events：https://code.claude.com/docs/en/hooks#supported-hook-events

### 2.5. Example: Intelligent Stop hook：https://code.claude.com/docs/en/hooks#example%3A-intelligent-stop-hook

### 2.6. Example: SubagentStop with custom logic：https://code.claude.com/docs/en/hooks#example%3A-subagentstop-with-custom-logic

### 2.7. Comparison with bash command hooks：https://code.claude.com/docs/en/hooks#comparison-with-bash-command-hooks

### 2.8. Best practices：https://code.claude.com/docs/en/hooks#best-practices

## 3. Hook Events：https://code.claude.com/docs/en/hooks#hook-events

### 3.1. PreToolUse：https://code.claude.com/docs/en/hooks#pretooluse

### 3.2. PermissionRequest：https://code.claude.com/docs/en/hooks#permissionrequest

### 3.3. PostToolUse：https://code.claude.com/docs/en/hooks#posttooluse

### 3.4. Notification：https://code.claude.com/docs/en/hooks#notification

### 3.5. UserPromptSubmit：https://code.claude.com/docs/en/hooks#userpromptsubmit

### 3.6. Stop：https://code.claude.com/docs/en/hooks#stop

### 3.7. SubagentStop：https://code.claude.com/docs/en/hooks#subagentstop

### 3.8. PreCompact：https://code.claude.com/docs/en/hooks#precompact

### 3.9. SessionStart：https://code.claude.com/docs/en/hooks#sessionstart

#### 3.9.1. Persisting environment variables：https://code.claude.com/docs/en/hooks#persisting-environment-variables

### 3.10. SessionEnd：https://code.claude.com/docs/en/hooks#sessionend

## 4. Hook Input：https://code.claude.com/docs/en/hooks#hook-input

### 4.1. PreToolUse Input：https://code.claude.com/docs/en/hooks#pretooluse-input

#### 4.1.1. Bash tool：https://code.claude.com/docs/en/hooks#bash-tool

#### 4.1.2. Write tool：https://code.claude.com/docs/en/hooks#write-tool

#### 4.1.3. Edit tool：https://code.claude.com/docs/en/hooks#edit-tool

#### 4.1.4. Read tool：https://code.claude.com/docs/en/hooks#read-tool

### 4.2. PostToolUse Input：https://code.claude.com/docs/en/hooks#posttooluse-input

### 4.3. Notification Input：https://code.claude.com/docs/en/hooks#notification-input

### 4.4. UserPromptSubmit Input：https://code.claude.com/docs/en/hooks#userpromptsubmit-input

### 4.5. Stop and SubagentStop Input：https://code.claude.com/docs/en/hooks#stop-and-subagentstop-input

### 4.6. PreCompact Input：https://code.claude.com/docs/en/hooks#precompact-input

### 4.7. SessionStart Input：https://code.claude.com/docs/en/hooks#sessionstart-input

### 4.8. SessionEnd Input：https://code.claude.com/docs/en/hooks#sessionend-input

## 5. Hook Output：https://code.claude.com/docs/en/hooks#hook-output

### 5.1. Simple: Exit Code：https://code.claude.com/docs/en/hooks#simple%3A-exit-code

#### 5.1.1. Exit Code 2 Behavior：https://code.claude.com/docs/en/hooks#exit-code-2-behavior

### 5.2. Advanced: JSON Output：https://code.claude.com/docs/en/hooks#advanced%3A-json-output

#### 5.2.1. Common JSON Fields：https://code.claude.com/docs/en/hooks#common-json-fields

#### 5.2.2. PreToolUse Decision Control：https://code.claude.com/docs/en/hooks#pretooluse-decision-control

#### 5.2.3. PermissionRequest Decision Control：https://code.claude.com/docs/en/hooks#permissionrequest-decision-control

#### 5.2.4. PostToolUse Decision Control：https://code.claude.com/docs/en/hooks#posttooluse-decision-control

#### 5.2.5. UserPromptSubmit Decision Control：https://code.claude.com/docs/en/hooks#userpromptsubmit-decision-control

#### 5.2.6. Stop/SubagentStop Decision Control：https://code.claude.com/docs/en/hooks#stop%2Fsubagentstop-decision-control

#### 5.2.7. SessionStart Decision Control：https://code.claude.com/docs/en/hooks#sessionstart-decision-control

#### 5.2.8. SessionEnd Decision Control：https://code.claude.com/docs/en/hooks#sessionend-decision-control

#### 5.2.9. Exit Code Example: Bash Command Validation：https://code.claude.com/docs/en/hooks#exit-code-example%3A-bash-command-validation

#### 5.2.10. JSON Output Example: UserPromptSubmit to Add Context and Validation：https://code.claude.com/docs/en/hooks#json-output-example%3A-userpromptsubmit-to-add-context-and-validation

#### 5.2.11. JSON Output Example: PreToolUse with Approval：https://code.claude.com/docs/en/hooks#json-output-example%3A-pretooluse-with-approval

## 6. Working with MCP Tools：https://code.claude.com/docs/en/hooks#working-with-mcp-tools

### 6.1. MCP Tool Naming：https://code.claude.com/docs/en/hooks#mcp-tool-naming

### 6.2. Configuring Hooks for MCP Tools：https://code.claude.com/docs/en/hooks#configuring-hooks-for-mcp-tools

## 7. Examples：https://code.claude.com/docs/en/hooks#examples

## 8. Security Considerations：https://code.claude.com/docs/en/hooks#security-considerations

### 8.1. Disclaimer：https://code.claude.com/docs/en/hooks#disclaimer

### 8.2. Security Best Practices：https://code.claude.com/docs/en/hooks#security-best-practices

### 8.3. Configuration Safety：https://code.claude.com/docs/en/hooks#configuration-safety

## 9. Hook Execution Details：https://code.claude.com/docs/en/hooks#hook-execution-details

## 10. Debugging：https://code.claude.com/docs/en/hooks#debugging

### 10.1. Basic Troubleshooting：https://code.claude.com/docs/en/hooks#basic-troubleshooting

### 10.2. Advanced Debugging：https://code.claude.com/docs/en/hooks#advanced-debugging

### 10.3. Debug Output Example：https://code.claude.com/docs/en/hooks#debug-output-example

### 10.4. ​：https://code.claude.com/docs/en/hooks#hooks-in-skills,-agents,-and-slash-commands

### 10.5. ​：https://code.claude.com/docs/en/hooks#example:-intelligent-stop-hook

### 10.6. ​：https://code.claude.com/docs/en/hooks#example:-subagentstop-with-custom-logic

### 10.7. ​：https://code.claude.com/docs/en/hooks#simple:-exit-code

- 10.7.0.1. Advanced: JSON Output：https://code.claude.com/docs/en/hooks#advanced-json-output
### 10.8. ​：https://code.claude.com/docs/en/hooks#advanced:-json-output

#### 10.8.1. ​：https://code.claude.com/docs/en/hooks#stop/subagentstop-decision-control

#### 10.8.2. ​：https://code.claude.com/docs/en/hooks#exit-code-example:-bash-command-validation

#### 10.8.3. ​：https://code.claude.com/docs/en/hooks#json-output-example:-userpromptsubmit-to-add-context-and-validation

#### 10.8.4. ​：https://code.claude.com/docs/en/hooks#json-output-example:-pretooluse-with-approval

