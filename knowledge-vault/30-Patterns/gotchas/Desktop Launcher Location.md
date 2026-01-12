# Desktop Launcher Location

The desktop shortcut "Claude Code Console" points to a bat file that handles project selection and terminal launching.

---

## Location

**Desktop Shortcut**: `C:\Users\johnd\OneDrive\Desktop\Claude Code Console.lnk`

**Target**: `C:\claude\start-claude.bat`

**Working Directory**: `C:\claude`

---

## What It Does

1. Runs project selector (`C:\claude\shared\scripts\select_project.py`)
2. Syncs shared resources (commands, MCP approvals, configs)
3. Offers terminal selection (WezTerm or current console)
4. Launches Claude Code in selected terminal

---

## Terminal Options

| Option | Command |
|--------|---------|
| WezTerm | `wezterm-gui.exe start --cwd PATH -- cmd /k claude` |
| Current console | `claude --dangerously-skip-permissions` |

---

## Related Files

- `C:\claude\shared\scripts\select_project.py` - Project selector
- `C:\claude\shared\scripts\sync_workspaces.py` - Workspace sync
- `C:\claude\shared\scripts\sync_mcp_approvals.py` - MCP approval sync

---

## Keywords

launcher, desktop, shortcut, start-claude.bat, wezterm, terminal, project-selector

---

**Version**: 1.0
**Created**: 2026-01-10
**Updated**: 2026-01-10
**Location**: knowledge-vault/30-Patterns/gotchas/Desktop Launcher Location.md
