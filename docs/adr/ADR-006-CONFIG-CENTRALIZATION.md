# ADR-006: Configuration Centralization

**Status**: Approved
**Date**: 2026-01-11
**Context**: Claude Manager UI Restructure & Multi-Session Support

---

## Problem

Configuration is scattered across database and files with no single source of truth:
- Skills, instructions, rules: File-only (not in database)
- `shared_commands` table: Exists but empty
- Multi-session conflicts possible when parallel Claudes edit files

---

## Decision

**Database is the single source of truth. Files are generated from database.**

### ONE-WAY PUSH Model

```
Database (Source) ──> Generated Files (Deployed)
```

Files regenerate on session start or manual trigger. Manual file edits are overwritten.

---

## New Tables

| Table | Purpose | Scope Levels |
|-------|---------|--------------|
| `global_config` | Key-value settings | global |
| `skills` | Skill definitions | global, project_type, project |
| `instructions` | Auto-apply .instructions.md | global, project_type, project |
| `rules` | Enforcement rules | global, project_type, project |

Each has a `_versions` table for history.

**Scope inheritance**: Project > Project Type > Global

**Schema details**: See `docs/schemas/config-centralization-schema.sql`

---

## Multi-Session Strategy

**Optimistic locking** via `updated_at` column. Before update, check if another session modified the row. On conflict: refresh, show diff, user decides.

---

## Migration Phases

1. **Create tables** - 4 core + 4 version tables
2. **Import data** - Migrate existing files to database
3. **UI changes** - Separate Global/Project config menus
4. **Backend** - CRUD commands, file regeneration

---

## Consequences

| Positive | Negative |
|----------|----------|
| Single source of truth | Migration effort |
| All config editable via UI | Manual file edits lost |
| Version history | More complex |
| Multi-session safe | |

---

**Version**: 1.0
**Author**: Claude (claude-family session)
