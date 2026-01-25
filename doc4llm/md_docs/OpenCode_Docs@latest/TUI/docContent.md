# TUI

> **原文链接**: https://opencode.ai/docs/tui

---

# TUI

Using the OpenCode terminal user interface.

OpenCode provides an interactive terminal interface or TUI for working on your projects with an LLM.

Running OpenCode starts the TUI for the current directory.

Terminal window
    
    opencode

Or you can start it for a specific working directory.

Terminal window
    
    opencode /path/to/project

Once you’re in the TUI, you can prompt it with a message.
    
    Give me a quick summary of the codebase.

* * *

## File references

You can reference files in your messages using `@`. This does a fuzzy file search in the current working directory.
    
    How is auth handled in @packages/functions/src/api/index.ts?

The content of the file is added to the conversation automatically.

* * *

## Bash commands

Start a message with `!` to run a shell command.
    
    !ls -la

The output of the command is added to the conversation as a tool result.

* * *

## Commands

When using the OpenCode TUI, you can type `/` followed by a command name to quickly execute actions. For example:
    
    /help

Most commands also have keybind using `ctrl+x` as the leader key, where `ctrl+x` is the default leader key. [Learn more](https://opencode.ai/docs/keybinds).

Here are all available slash commands:

* * *

### connect

Add a provider to OpenCode. Allows you to select from available providers and add their API keys.
    
    /connect

* * *

### compact

Compact the current session. _Alias_ : `/summarize`
    
    /compact

**Keybind:** `ctrl+x c`

* * *

### details

Toggle tool execution details.
    
    /details

**Keybind:** `ctrl+x d`

* * *

### editor

Open external editor for composing messages. Uses the editor set in your `EDITOR` environment variable. Learn more.
    
    /editor

**Keybind:** `ctrl+x e`

* * *

### exit

Exit OpenCode. _Aliases_ : `/quit`, `/q`
    
    /exit

**Keybind:** `ctrl+x q`

* * *

### export

Export current conversation to Markdown and open in your default editor. Uses the editor set in your `EDITOR` environment variable. Learn more.
    
    /export

**Keybind:** `ctrl+x x`

* * *

### help

Show the help dialog.
    
    /help

**Keybind:** `ctrl+x h`

* * *

### init

Create or update `AGENTS.md` file. [Learn more](https://opencode.ai/docs/rules).
    
    /init

**Keybind:** `ctrl+x i`

* * *

### models

List available models.
    
    /models

**Keybind:** `ctrl+x m`

* * *

### new

Start a new session. _Alias_ : `/clear`
    
    /new

**Keybind:** `ctrl+x n`

* * *

### redo

Redo a previously undone message. Only available after using `/undo`.

Internally, this uses Git to manage the file changes. So your project **needs to be a Git repository**.
    
    /redo

**Keybind:** `ctrl+x r`

* * *

### sessions

List and switch between sessions. _Aliases_ : `/resume`, `/continue`
    
    /sessions

**Keybind:** `ctrl+x l`

* * *

### share

Share current session. [Learn more](https://opencode.ai/docs/share).
    
    /share

**Keybind:** `ctrl+x s`

* * *

### themes

List available themes.
    
    /theme

**Keybind:** `ctrl+x t`

* * *

### thinking

Toggle the visibility of thinking/reasoning blocks in the conversation. When enabled, you can see the model’s reasoning process for models that support extended thinking.
    
    /thinking

* * *

### undo

Undo last message in the conversation. Removes the most recent user message, all subsequent responses, and any file changes.

Internally, this uses Git to manage the file changes. So your project **needs to be a Git repository**.
    
    /undo

**Keybind:** `ctrl+x u`

* * *

### unshare

Unshare current session. [Learn more](https://opencode.ai/docs/share#un-sharing).
    
    /unshare

* * *

## Editor setup

Both the `/editor` and `/export` commands use the editor specified in your `EDITOR` environment variable.

     * Linux/macOS 
     * Windows (CMD) 
     * Windows (PowerShell) 

Terminal window
    
    # Example for nano or vim
    
    export EDITOR=nano
    
    export EDITOR=vim
    
    
    
    
    # For GUI editors, VS Code, Cursor, VSCodium, Windsurf, Zed, etc.
    
    # include --wait
    
    export EDITOR="code --wait"

To make it permanent, add this to your shell profile; `~/.bashrc`, `~/.zshrc`, etc.

Terminal window
    
    set EDITOR=notepad
    
    
    
    
    # For GUI editors, VS Code, Cursor, VSCodium, Windsurf, Zed, etc.
    
    # include --wait
    
    set EDITOR=code --wait

To make it permanent, use **System Properties** > **Environment Variables**.

Terminal window
    
    $env:EDITOR = "notepad"
    
    
    
    
    # For GUI editors, VS Code, Cursor, VSCodium, Windsurf, Zed, etc.
    
    # include --wait
    
    $env:EDITOR = "code --wait"

To make it permanent, add this to your PowerShell profile.

Popular editor options include:

     * `code` - Visual Studio Code
     * `cursor` - Cursor
     * `windsurf` - Windsurf
     * `nvim` - Neovim editor
     * `vim` - Vim editor
     * `nano` - Nano editor
     * `notepad` - Windows Notepad
     * `subl` - Sublime Text

Some editors need command-line arguments to run in blocking mode. The `\--wait` flag makes the editor process block until closed.

* * *

## Configure

You can customize TUI behavior through your OpenCode config file.

opencode.json
    
    {
    
      "$schema": "https://opencode.ai/config.json",
    
      "tui": {
    
        "scroll_speed": 3,
    
        "scroll_acceleration": {
    
          "enabled": true
    
        }
    
      }
    
    }

### Options

     * `scroll_acceleration` - Enable macOS-style scroll acceleration for smooth, natural scrolling. When enabled, scroll speed increases with rapid scrolling gestures and stays precise for slower movements. **This setting takes precedence over`scroll_speed` and overrides it when enabled.**
     * `scroll_speed` - Controls how fast the TUI scrolls when using scroll commands (minimum: `1`). Defaults to `3`. **Note: This is ignored if`scroll_acceleration.enabled` is set to `true`.**

* * *

## Customization

You can customize various aspects of the TUI view using the command palette (`ctrl+x h` or `/help`). These settings persist across restarts.

* * *

#### Username display

Toggle whether your username appears in chat messages. Access this through:

     * Command palette: Search for “username” or “hide username”
     * The setting persists automatically and will be remembered across TUI sessions
