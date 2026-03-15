# CLAUDE.md Audit — 2026-03-15

## Summary

| File | Current Lines | Target | Over By |
|------|--------------|--------|---------|
| Global `~/.claude/CLAUDE.md` | 281 | 200 | 81 lines |
| Project `claude-family/CLAUDE.md` | 342 | 250 | 92 lines |

Primary causes: duplicated content between files, verbose tool tables already covered by `storage-rules.md`, and a 14-row changelog that should be trimmed to 3 entries.

**Detailed section analysis**: See [claude-md-audit-details-2026-03-15.md](claude-md-audit-details-2026-03-15.md)

---

## Priority Edit Order

Apply in this order to avoid inconsistent state:

1. **Global**: Remove storage tools table — covered by `storage-rules.md` (-13 lines)
2. **Global**: Trim BPMN section from 50 lines to 6 lines (-44 lines)
3. **Global**: Condense Delegation + Structured Autonomy to pointers (-20 lines)
4. **Global**: Condense Skills to 2 lines + instructions table to 1 line (-25 lines)
5. **Project**: Remove Skills + Auto-Apply sections — duplicate of global (-30 lines)
6. **Project**: Trim Knowledge System to 4 lines (-42 lines)
7. **Project**: Trim WCC section to 2 lines, remove state machines table (-20 lines)
8. **Project**: Condense Memory/Knowledge/Filing Cabinet tables to pointers (-26 lines)
9. **Project**: Update `generate_project_settings.py` → `sync_project.py` in config section
10. **Project**: Trim changelog to last 3 entries (-11 lines)
11. **Both**: Update footers

**Estimated lines after changes**: Global ~185, Project ~230

---

## Cross-File Duplication

Content appearing in both files — should exist in only one:

| Content | Global | Project | Resolution |
|---------|--------|---------|------------|
| Storage tools routing table | L80–92 | Memory/Knowledge/Filing sections | Remove from global; `storage-rules.md` covers it |
| Skills list (8 rows) | L130–143 | L236–250 | Remove from project; keep 2-line pointer in global |
| Auto-apply instructions table | L257–273 | L256–263 | Remove from project entirely |
| "Database is source of truth" | L244 | L23, L205 | Keep only in project config section |

---

## Quick-Reference: What to Do With Each Section

### Global `~/.claude/CLAUDE.md`

| Section | Action | Notes |
|---------|--------|-------|
| Identity, Environment, Vault | KEEP | Essential orientation |
| Database Connection | KEEP | 4-line rule |
| Work Tracking | KEEP | Hierarchy + git codes |
| Session Workflow | KEEP | Auto-behavior summary |
| Code Style | KEEP | Universal standards |
| MCP Storage Tools table | REMOVE | Duplicated in `storage-rules.md` |
| MCP Full Tool Index | TRIM | Keep 6-7 rows; remove legacy footnote |
| Skills section | TRIM | 2 lines only; remove 8-row table |
| Delegation Rules table | TRIM | Keep principle + pointer; remove 7-row table |
| Structured Autonomy | TRIM | 3 lines; remove step detail |
| BPMN section | TRIM | Keep 2-line principle + sync command; remove multi-tenancy list + tool table |
| SOPs table | KEEP | Remove "Key Principle" footer (duplicate) |
| Global Instructions table | TRIM | Condense 17 lines to 2 |
| Footer date | UPDATE | Change from 2026-02-22 to 2026-03-15 |

### Project `claude-family/CLAUDE.md`

| Section | Action | Notes |
|---------|--------|-------|
| Header, Problem, Phase, Architecture, Structure | KEEP | Project identity |
| Coding Standards | KEEP | |
| Work Tracking + Workflow Tools | KEEP | Core daily interface |
| Config Management (CRITICAL) | UPDATE | Remove SQL block; update script name to `sync_project.py` |
| Config Tools table | TRIM | 1 line pointer only |
| Memory Tools table | TRIM | 1 line; `storage-rules.md` covers it |
| Knowledge Tools table | TRIM | 1 line pointer |
| Filing Cabinet table | TRIM | Remove table; keep UPSERT/mode/is_pinned gotcha |
| WCC section | TRIM | 2 lines; remove tool table + state machines |
| Configuration (DB-Driven) | KEEP | Already references `sync_project.py` |
| SOPs + Key Procedures | KEEP | |
| Skills System | REMOVE | Duplicate of global |
| Auto-Apply Instructions | REMOVE | Exact duplicate of global |
| Knowledge System | TRIM | 4 lines only |
| Recent Changes | TRIM | Keep last 3 entries only |
| Table count "58 tables" | UPDATE | Verify current count |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: C:\Projects\claude-family\docs\claude-md-audit-2026-03-15.md
