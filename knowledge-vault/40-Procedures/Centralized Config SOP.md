---
projects:
  - claude-family
  - claude-manager-mui
tags:
  - sop
  - configuration
  - database
  - profiles
synced: false
---

# Centralized Config SOP

**Purpose**: Define the centralized configuration management process for Claude Family projects.

---

## Core Principle: Database is Source of Truth

All Claude configurations are stored in the PostgreSQL database (`claude.profiles` table). Files are generated from the database and should NOT be edited directly.

```
┌──────────────────────────┐
│   DATABASE (Source)      │
│   claude.profiles        │
│   - config.behavior      │  ← CLAUDE.md content
│   - config.mcps          │  ← MCP servers
│   - config.skills        │  ← Enabled skills
└──────────────────────────┘
            │
            ▼ ONE-WAY PUSH
┌──────────────────────────┐
│   FILES (Generated)      │
│   {project}/CLAUDE.md    │
│   {project}/.claude/     │
│     settings.local.json  │
└──────────────────────────┘
```

---

## Workflows

### Import: File → Database

**When**: Initial migration, or accepting local file changes

1. Read `{project_path}/CLAUDE.md` content
2. Read `{project_path}/.claude/settings.local.json` for MCPs, skills
3. Update `claude.profiles` with:
   - `config.behavior` = CLAUDE.md content
   - `config.mcps` = from settings
   - `config.skills` = from settings
4. Create version snapshot in `claude.profile_versions`

**UI**: Configuration → Select Profile → "Import from Project"

**Script**: `python scripts/import_profiles_from_projects.py`

---

### Export: Database → File (ONE-WAY PUSH)

**When**: User explicitly deploys profile changes to project files

1. Create backup: `CLAUDE.md.bak`
2. Write `config.behavior` → `{project_path}/CLAUDE.md`
3. Regenerate `{project_path}/.claude/settings.local.json`
4. Log deployment to database

**UI**: Configuration → Select Profile → "Apply to Project"

**Script**: Called via Tauri backend command

---

## Change Detection

On startup (via BAT launcher or Claude Manager):

1. Compare hash of `{project_path}/CLAUDE.md` vs `profiles.config.behavior`
2. If different, prompt user:
   - **[1] Accept Changes** → Import file to database
   - **[2] Discard Changes** → Restore file from database
   - **[3] Continue Anyway** → No sync, use as-is

---

## ONE-WAY PUSH Principle

**Files are NEVER auto-synced back to database.**

If a Claude instance needs to modify configuration:
1. It must REQUEST the change (not auto-modify)
2. Human approves via Claude Manager UI
3. Human clicks "Apply to Project" to deploy

This prevents:
- Accidental overwrites
- Configuration drift
- Conflicting changes from multiple sessions

---

## For Claudes: How to Request Config Changes

If you need to modify CLAUDE.md or configuration:

```markdown
## Config Change Request

**Project**: claude-family
**Requested Change**: Add new skill 'documentation-management'
**Reason**: Need to track documentation updates

**Suggested Edit**:
Add to config.skills:
- documentation-management
```

Then tell the user:
> "I've identified a configuration change that would help. Please review and apply via Claude Manager if you approve."

**DO NOT**:
- ❌ Edit CLAUDE.md files directly
- ❌ Modify settings.local.json
- ❌ Auto-update database profiles

---

## Key Tables

| Table | Purpose |
|-------|---------|
| `claude.profiles` | Current profile config (JSONB) |
| `claude.profile_versions` | Immutable version history |
| `claude.workspaces` | Project registry with paths |

---

## Key Scripts

| Script | Purpose |
|--------|---------|
| `generate_project_settings.py` | Startup sync + change detection |
| `backup_claude_configs.py` | Backup all project configs |
| `import_profiles_from_projects.py` | Bulk import to database |

---

## Key UI Elements

| Location | Action |
|----------|--------|
| Configuration → Profile → "Import from Project" | Pull file content to database |
| Configuration → Profile → "Apply to Project" | Push database to files |
| Launch → Pre-launch check | Detect local changes |

---

## Related Documents

- [[Config Rollback SOP]] - How to recover from bad changes
- [[Config Management SOP]] - Legacy config generation
- [[Profile Manager Feature]] - UI implementation details

---

**Version**: 1.0
**Created**: 2026-01-11
**Updated**: 2026-01-11
**Location**: knowledge-vault/40-Procedures/Centralized Config SOP.md
