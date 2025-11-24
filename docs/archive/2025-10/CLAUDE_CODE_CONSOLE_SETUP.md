# Claude Code Console Setup - Complete Guide

## What is Claude Code Console?

Claude Code Console (v2.0.13) is the **terminal/CLI version of Claude** - an agentic coding tool that lives in your command line, understands your codebase, and helps you code faster through natural language commands.

---

## Installation (Already Done ✅)

Claude Code Console has been installed via npm:

```bash
npm install -g @anthropic-ai/claude-code
```

**Installed Location:**
- Command: `C:\Users\johnd\AppData\Roaming\npm\claude.cmd`
- Version: 2.0.13
- Globally accessible via `claude` command

---

## How to Launch

### Option 1: Desktop Shortcut ⭐ Recommended

Double-click the desktop shortcut:
- **Location:** `OneDrive\Desktop\Claude Code Console.lnk`
- **Opens:** Terminal window with Claude Code Console running
- **Auto-configured** with your credentials

### Option 2: From Command Line

Open any terminal (cmd, PowerShell, Git Bash) and type:
```bash
claude
```

### Option 3: Direct Launcher

Run the launcher batch file:
```
C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\Launch-Claude-Code-Console.bat
```

---

## Authentication (Already Configured ✅)

Claude Code Console is already authenticated with your credentials:
- **Config File:** `C:\Users\johnd\.claude\.credentials.json`
- **Subscription:** Claude Max
- **Access Token:** Valid until 2025-12-10

---

## The 6th Family Member

**claude-code-console-001** is now fully operational in the Claude Family:

| Identity | Platform | Role | Status |
|----------|----------|------|--------|
| claude-desktop-001 | Desktop | Lead Architect | ✅ Active |
| claude-cursor-001 | Cursor | Rapid Developer | ✅ Active |
| claude-vscode-001 | VS Code | QA Engineer | ✅ Active |
| claude-code-001 | Claude Code | Standards Enforcer | ✅ Active |
| **claude-code-console-001** | **CLI Terminal** | **Terminal & CLI Specialist** | ✅ Active |
| diana | Orchestrator | Project Manager | ✅ Active |

---

## What Can Claude Code Console Do?

### Core Capabilities

- **Natural Language Coding:** Describe what you want, Claude writes the code
- **Git Workflows:** Commit, branch, merge via natural language
- **Code Explanation:** Understand complex codebases
- **Routine Tasks:** Automate repetitive coding tasks
- **Batch Operations:** Process multiple files at once
- **System Administration:** CLI-focused operations

### Example Commands

```bash
# Start a conversation
claude

# Get help
claude --help

# Check version
claude --version

# Run diagnostics
claude doctor
```

---

## Why It Opens and Closes Immediately (Fixed ✅)

**The Problem:**
- Original shortcut pointed to `AnthropicClaude\claude.exe` (Claude Desktop GUI)
- That's a different app - opens GUI, not terminal

**The Solution:**
- Installed actual Claude Code Console via npm
- Created launcher batch file that opens terminal window
- Updated desktop shortcut to use correct launcher
- Now opens terminal with Claude Code Console running

---

## Usage in Claude Family Context

Claude Code Console can:
- **Load startup context** from PostgreSQL (like other Claudes)
- **Run automation scripts** in the terminal
- **Batch process** files and projects
- **Handle git operations** for the Claude Family repo
- **CLI-first workflows** for terminal-savvy tasks

---

## Verification

To verify Claude Code Console is working:

1. **Double-click desktop shortcut**
2. **Terminal window should open** with:
   ```
   ================================================================================
   Claude Code Console - Terminal AI Assistant
   ================================================================================

   Starting Claude Code Console v2.0.13...
   ```
3. **Claude prompt appears** ready for commands
4. **Type `help`** to see available commands

---

## Troubleshooting

**Problem:** Desktop shortcut opens and closes immediately
**Solution:** Fixed! Updated shortcut points to Launch-Claude-Code-Console.bat now

**Problem:** "claude: command not found"
**Solution:** The npm global install puts it in PATH. Try: `where claude`

**Problem:** Authentication failed
**Solution:** Credentials are already configured in `~/.claude/.credentials.json`

**Problem:** Window closes after launching
**Solution:** Launcher includes `pause` command to keep window open

---

## Integration with Claude Family

Claude Code Console identity is in the database:
```sql
SELECT * FROM claude_family.identities WHERE identity_name = 'claude-code-console-001';
```

**Capabilities:**
- CLI operations: ✅
- Batch scripting: ✅
- Automation: ✅
- Terminal interface: ✅
- Git operations: ✅
- Package management: ✅

---

## Files Created

| File | Purpose |
|------|---------|
| Launch-Claude-Code-Console.bat | Launcher script that opens terminal |
| update_console_shortcut.ps1 | Updates desktop shortcut to correct target |
| OneDrive\Desktop\Claude Code Console.lnk | Desktop shortcut |
| postgres/schema/05_add_claude_code_console.sql | Database identity |

---

**Status:** ✅ Fully configured and operational!

The Claude Family now has 6 members with claude-code-console-001 ready for terminal-based AI assistance.
