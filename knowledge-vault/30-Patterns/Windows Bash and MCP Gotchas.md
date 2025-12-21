---
synced: true
synced_at: '2025-12-21T13:55:56.214237'
---

# Windows Bash and MCP Gotchas

**Category**: troubleshooting
**Tags**: #windows #bash #mcp #gotchas #errors

---

## Overview

Common issues when running Claude Code on Windows with Git Bash and MCP servers.

---

## Issue 1: `dir /b` Fails in Git Bash

**Symptom**: `dir: cannot access '/b': No such file or directory`

**Cause**: Claude Code runs in Git Bash on Windows, which uses Unix commands, not Windows `dir`.

**Solution**: Use Unix commands instead:
```bash
# WRONG (Windows)
dir /b "C:\Projects\myproject"

# CORRECT (Unix/Git Bash)
ls "C:/Projects/myproject"
```

**For Claude**: Always use `ls` instead of `dir` when listing directories.

---

## Issue 2: SessionStart Hook Error

**Symptom**: `SessionStart:startup hook error` on Claude startup

**Common Causes**:
1. Hook script uses deprecated database schema
2. Hook script path doesn't exist
3. Python dependencies not installed in venv

**Check Hook Config**:
```
~/.claude/settings.json → hooks.SessionStart
```

**Fix**: Verify script exists and uses correct schema (`claude.*` not `claude_family.*`)

---

## Issue 3: Duplicate Slash Commands

**Symptom**: Same command appears twice in menu (user) and (project)

**Cause**: Command exists in both:
- `~/.claude/commands/` (user level)
- `.claude-plugins/*/commands/` or `.claude/commands/` (project level)

**Solution**: Remove duplicates from user level if project provides them:
```bash
rm ~/.claude/commands/session-start.md
rm ~/.claude/commands/session-end.md
```

---

## Issue 4: MCP Errors on Session End

**Symptom**: Errors when closing Claude Code session

**Common Causes**:
1. MCP server process cleanup issues (Claude Code bug #1935)
2. Hook scripts with database errors
3. Session logging to non-existent tables

**Workaround**: These are often cosmetic - session still ends correctly.

---

## Issue 5: Deprecated Schema References

**Symptom**: Database queries fail with "relation does not exist"

**Old Schema** → **New Schema**:
| Old | New |
|-----|-----|
| `claude_family.instance_messages` | `claude.messages` |
| `claude_family.identities` | `claude.identities` |
| `claude_family.session_history` | `claude.sessions` |
| `claude_family.shared_knowledge` | `claude.knowledge` |
| `claude_pm.*` | `claude.*` |

**Find deprecated refs**:
```bash
grep -r "claude_family\." C:/claude/shared/scripts/
```

---

## Prevention Checklist

Before deploying hooks/scripts:
- [ ] Use Unix paths in Git Bash (`/` not `\`)
- [ ] Use `ls` not `dir`
- [ ] Use `claude.*` schema (not deprecated)
- [ ] Test script standalone before adding to hooks
- [ ] Check command doesn't duplicate existing

---

**Version**: 1.0
**Created**: 2025-12-21
**Updated**: 2025-12-21