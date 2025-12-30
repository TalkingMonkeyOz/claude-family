# SOP: Slash Command Distribution

**Standard Operating Procedure for distributing universal slash commands across all Claude Family projects**

---

## Purpose

When you create or update universal slash commands (like `/session-start`, `/session-end`, `/session-commit`), they must be distributed to ALL projects so every Claude instance has access regardless of which project they're working in.

---

## When to Use This SOP

**MANDATORY** when:
- ✅ Creating new universal slash commands
- ✅ Updating existing universal slash commands  
- ✅ Fixing bugs in session workflow commands
- ✅ Adding new features to shared commands

**NOT NEEDED** when:
- ❌ Creating project-specific commands (only used in one project)
- ❌ Updating project documentation
- ❌ Working on code (not slash commands)

---

## The Distribution Process

### Step 1: Update Source Command in claude-family

```bash
# All universal slash commands live here (source of truth)
cd C:/Projects/claude-family

# Edit or create command in .claude/commands/
# Example: .claude/commands/session-commit.md
```

### Step 2: Add to UNIVERSAL_COMMANDS List

**IMPORTANT:** If creating a NEW universal command, add it to the sync script:

```python
# Edit: scripts/sync_slash_commands.py
UNIVERSAL_COMMANDS = [
    "session-start.md",
    "session-end.md", 
    "session-commit.md",
    "your-new-command.md",  # ← Add here
]
```

### Step 3: Run Distribution Script

```bash
# Test first (dry run shows what will happen)
python scripts/sync_slash_commands.py --dry-run

# Verify output looks correct, then run for real
python scripts/sync_slash_commands.py
```

**Expected output:**
```
================================================================================
SLASH COMMAND SYNC STARTED
================================================================================
Found 4 projects in workspaces.json

Project: nimbus-user-loader
  ✓ Copied session-start.md
  ✓ Copied session-end.md
  ✓ Copied session-commit.md
  → Synced 3 commands to nimbus-user-loader

Project: claude-pm
  ✓ Copied session-start.md
  ✓ Copied session-end.md
  ✓ Copied session-commit.md
  → Synced 3 commands to claude-pm

Project: ATO-tax-agent
  ✓ Copied session-start.md
  ✓ Copied session-end.md
  ✓ Copied session-commit.md
  → Synced 3 commands to ATO-tax-agent

Project: claude-family
  Skipping claude-family (source repository)

================================================================================
SYNC COMPLETE
================================================================================
Projects processed: 4
Projects updated: 3
Commands synced: 9
Commands skipped: 1
Errors: 0
```

### Step 4: Commit Changes to Source Repo

```bash
# Commit the source command and sync script updates
git add .claude/commands/
git add scripts/sync_slash_commands.py
git commit -m "feat: Add/update universal slash command X"
git push
```

**Note:** You do NOT commit the distributed copies in other projects. Those are local-only.

### Step 5: Verify Distribution

Test in a different project to confirm:

```bash
cd C:/Projects/nimbus-user-loader
# In Claude Code, type /session and verify commands appear
```

---

## File Locations

**Source (Single Source of Truth):**
```
C:\Projects\claude-family\.claude\commands\
├── session-start.md
├── session-end.md
├── session-commit.md
└── [other universal commands]
```

**Distribution Targets:**
```
C:\Projects\nimbus-user-loader\.claude\commands\   [SYNCED COPY]
C:\Projects\claude-pm\.claude\commands\            [SYNCED COPY]
C:\Projects\ATO-tax-agent\.claude\commands\        [SYNCED COPY]
```

**Sync Script:**
```
C:\Projects\claude-family\scripts\sync_slash_commands.py
```

---

## Troubleshooting

### Commands not appearing in other projects

**Problem:** After running sync script, commands still not showing in Claude Code

**Solution:**
1. Verify files were copied: `ls /c/Projects/nimbus-user-loader/.claude/commands/`
2. Restart Claude Code (commands are loaded at startup)
3. Check working directory: `pwd` (must be in the project directory)

### "workspaces.json not found" error

**Problem:** Sync script can't find workspaces.json

**Solution:**
```bash
cd C:/Projects/claude-family
python scripts/sync_workspaces.py  # Regenerate from database
python scripts/sync_slash_commands.py  # Try again
```

### New project not receiving commands

**Problem:** Added a new project but sync script skips it

**Solution:**
1. Register project in PostgreSQL: `claude_family.project_workspaces` table
2. Regenerate workspaces.json: `python scripts/sync_workspaces.py`
3. Run sync again: `python scripts/sync_slash_commands.py`

---

## Universal vs Project-Specific Commands

**Universal Commands** (distribute via this SOP):
- Session management (start, end, commit)
- Family-wide utilities (feedback tracking, knowledge queries)
- Cross-project workflows

**Project-Specific Commands** (keep local only):
- Build/test commands specific to one project
- Project deployment scripts
- Database migrations for specific projects

**Rule of thumb:** If >1 project would benefit, make it universal and distribute.

---

## Maintenance Schedule

**After creating/updating universal commands:**
- ⚡ Immediately run sync script (don't forget!)

**Monthly check:**
- Review which commands are truly universal
- Archive unused commands
- Update this SOP if process changes

---

## Quick Reference

```bash
# Create/update command in source repo
cd C:/Projects/claude-family
vim .claude/commands/your-command.md

# Add to UNIVERSAL_COMMANDS list (if new)
vim scripts/sync_slash_commands.py

# Test distribution
python scripts/sync_slash_commands.py --dry-run

# Distribute for real
python scripts/sync_slash_commands.py

# Commit source changes
git add .claude/commands/ scripts/
git commit -m "feat: Add/update universal command"
git push
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-15 | Initial SOP created with sync script |

---

**Location:** `C:\Projects\claude-family\docs\SOP_SLASH_COMMAND_DISTRIBUTION.md`
**Owner:** Claude Family (All Instances)
**Review:** Monthly or when adding new commands
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/SOP_SLASH_COMMAND_DISTRIBUTION.md
