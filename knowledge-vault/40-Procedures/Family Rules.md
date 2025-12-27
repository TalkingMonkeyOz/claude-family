---
synced: true
synced_at: '2025-12-20T23:29:45.920629'
tags:
- sop
- procedure
projects: []
---

# Claude Family Rules

**Category**: governance
**Tags**: #rules #coordination #mandatory

---

## Identity

We are the **Claude Family** - multiple Claude instances coordinating across projects via:
- Shared PostgreSQL database (`ai_company_foundation`, schema `claude`)
- Inter-instance messaging (`claude.messages`)
- Session logging (`claude.sessions`)
- Knowledge persistence (`claude.knowledge`, `knowledge-vault/`)

---

## Session Rules (MANDATORY)

| When | Action | Why |
|------|--------|-----|
| Session Start | Run `/session-start` | Logs session, checks inbox, loads context |
| Session End | Run `/session-end` | Saves summary, captures learnings |
| Before Major Work | Check inbox | May have messages from other instances |

**Consequence of skipping**: Future sessions waste time rediscovering work.

**Detailed Documentation**: See [[Session Lifecycle]] for complete session flow and [[Session Quick Reference]] for quick commands.

---

## Database Rules

1. **Schema**: Use `claude.*` only
   - Deprecated: `claude_family.*`, `claude_pm.*` (removed Dec 8, 2025)

2. **Data Gateway**: Before writing to constrained columns:
   ```sql
   SELECT valid_values FROM claude.column_registry
   WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
   ```

3. **Session Logging**: Mandatory for all sessions

---

## Coordination Rules

1. **One task at a time** - Don't step on other instances' work
2. **Log decisions** - Add to `claude.shared_knowledge` if it helps others
3. **Check before creating** - Search vault/database before creating duplicate content
4. **Update docs** - If you change behavior, update relevant CLAUDE.md

---

## Knowledge Capture

1. **Vault location**: `C:\Projects\claude-family\knowledge-vault\`
2. **Quick capture**: Add to `00-Inbox/` with basic frontmatter
3. **Organized storage**: Move to appropriate folder (10-Projects, 20-Domains, etc.)
4. **Sync to DB**: Run `python scripts/sync_obsidian_to_db.py`
5. **Link related notes**: Use `[[wiki-links]]` for connections

---

## MCP Servers

Always available across all projects:

| Server | Purpose |
|--------|---------|
| postgres | Database access, session logging |
| memory | Persistent memory graph |
| filesystem | File operations |
| orchestrator | Agent spawning, messaging |
| sequential-thinking | Complex problem solving |

---

## Related Documents

- [[Session Lifecycle]] - Complete session flow documentation (NEW)
- [[Session Quick Reference]] - Quick reference for session operations (NEW)
- [[Database Schema - Core Tables]] - Core database tables reference (NEW)
- [[Purpose]] - Vault overview
- [[Session Workflow]] - Detailed session procedures
- [[Claude Hooks]] - Enforcement layer
- [[MCP Configuration]] - Server setup

---

**Version**: 1.1
**Created**: 2025-12-20
**Updated**: 2025-12-26
**Location**: knowledge-vault/40-Procedures/Family Rules.md