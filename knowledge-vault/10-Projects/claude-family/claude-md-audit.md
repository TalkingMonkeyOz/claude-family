---
projects:
- claude-family
tags:
- audit
- claude-md
- governance
synced: false
---

# CLAUDE.md Audit — Overview

**Scope**: 15 project CLAUDE.md files across C:\Projects
**Audit Date**: 2026-03-13
**Details**: See [claude-md-audit-details.md](claude-md-audit-details.md)

---

## Summary Table

| Project | Retired Tools | Storage Guidance | Footer Current | project-tools ref | Priority |
|---------|:---:|:---:|:---:|:---:|:---:|
| ATO-Infrastructure | - | No | Stale (2026-01-03) | No | Medium |
| ATO-Tax-Agent | - | No | Stale (2025-12-26) | No | Medium |
| bee-game | - | No | Missing Updated | No | Low |
| claude-family-manager-v2 | orchestrator, memory | No | Stale (2025-12-27) | No | **High** |
| claude-manager-mui | orchestrator, memory | No | Stale (2025-12-29) | No | **High** |
| finance-htmx | - | No | Missing Updated | No | Low |
| finance-mui | - | No | Missing Updated | No | Low |
| monash-nimbus-reports | orchestrator | No | Stale (2026-01-26) | Yes | **High** |
| nimbus-import | - | No | Stale (2025-12-27) | No | Low |
| nimbus-mui | orchestrator | No | 2026-02-22 | Yes | **High** |
| nimbus-odata-configurator | orchestrator | No | Missing Updated | Yes | **High** |
| nimbus-user-loader | - | No | Malformed | No | Medium |
| personal-finance-system | memory (via config) | No | Stale (2025-12-27) | No | **High** |
| trading-intelligence | - | No | Stale (2026-02-08) | Yes | Low |
| mcp-search-test | - | No | Minimal | No | Low |

---

## Cross-Cutting Findings

### 1. Retired MCPs in Active Use — 6 projects (High)

The `orchestrator` MCP was retired 2026-02-24. The `memory` MCP was removed 2026-01. Six files still list one or both as available:

| Project | Retired Tools Listed |
|---------|---------------------|
| claude-family-manager-v2 | orchestrator, memory |
| claude-manager-mui | orchestrator, memory |
| monash-nimbus-reports | orchestrator |
| nimbus-mui | orchestrator |
| nimbus-odata-configurator | orchestrator |
| personal-finance-system | memory (via project_type_configs) |

Three files also carry the stale instruction "message `claude-family` project via orchestrator" — the correct instruction is `project-tools.send_message`.

### 2. No Storage Tool Guidance — All 15 projects (Medium)

Zero project files explain the 3-tier memory system (F130, 2026-02-26). None mention `remember()`, `store_session_fact()`, or `catalog()`. The global CLAUDE.md covers this, but project files should reference it.

### 3. Stale Footers — 13 of 15 projects (Medium)

Only `nimbus-mui` (2026-02-22) post-dates the orchestrator retirement. Three files have structural footer issues (missing fields or non-standard format).

### 4. Missing project-tools Reference — 9 projects (Medium)

ATO-Infrastructure, ATO-Tax-Agent, bee-game, claude-manager-mui, finance-htmx, finance-mui, nimbus-import, nimbus-user-loader, and personal-finance-system have no in-file reminder to use project-tools for work tracking.

### 5. nimbus-knowledge Pending Shutdown Not Documented (Medium)

Listed as active in `monash-nimbus-reports` and `nimbus-mui` without a deprecation note. MEMORY.md marks it "PENDING SHUTDOWN — 34 rows to migrate via remember(), then retire."

---

## Priority Action List

### High — Address Immediately

1. **claude-family-manager-v2**: Remove orchestrator + memory from MCP list; fix messaging instruction.
2. **claude-manager-mui**: Same as above.
3. **monash-nimbus-reports**: Remove orchestrator; fix messaging instruction; add nimbus-knowledge deprecation note.
4. **nimbus-mui**: Remove orchestrator; fix messaging instruction; add nimbus-knowledge deprecation note.
5. **nimbus-odata-configurator**: Remove orchestrator; fix messaging instruction.
6. **personal-finance-system**: Audit `csharp-desktop` project_type_configs in the DB to remove retired `memory` MCP default.

### Medium — Next Maintenance Pass

7. **ATO-Infrastructure**: Add work tracking and project-tools sections; update footer.
8. **ATO-Tax-Agent**: Remove `sync_obsidian_to_db.py` reference; add project-tools ref; update footer.
9. **nimbus-user-loader**: Verify Context7/Roslyn MCP availability; fix footer format; add project-tools ref.
10. **All projects**: Add brief storage tools note (remember() vs store_session_fact() vs catalog()).

### Low — Nice to Have

11. bee-game, finance-htmx, finance-mui, nimbus-import: Fix/add footer fields; add project-tools ref.
12. trading-intelligence: Update footer; add storage guidance.
13. mcp-search-test: No action required (ephemeral test project).

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: C:\Projects\claude-family\knowledge-vault\10-Projects\claude-family\claude-md-audit.md
