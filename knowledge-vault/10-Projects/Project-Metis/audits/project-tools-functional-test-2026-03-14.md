---
projects:
- claude-family
tags:
- testing
- project-tools
- mcp
synced: false
---

# Project-Tools MCP — Functional Test Report

**Date**: 2026-03-14
**Server**: `mcp-servers/project-tools/server_v2.py`
**Method**: Static code analysis + environment verification

> Note: MCP tools are not callable from spawned agents (`disableAllHooks: true`).
> All 15 tools evaluated via implementation review, SQL tracing, and env config audit.

---

## Result: 11/15 passed, 4 issues found

| # | Tool | Status | Notes |
|---|------|--------|-------|
| 1 | `start_session` | PASS | 3-CTE query, correct return shape, startup demotion logic OK |
| 2 | `get_work_context` | PASS | All 3 scopes (current/feature/project) implemented correctly |
| 3 | `list_session_facts` | PASS | Delegates to `tool_list_session_facts`, sensitive values redacted |
| 4 | `recall_memories` | PASS | 3-tier retrieval (short/mid/long) with budget profiles correct |
| 5 | `recall_entities` | PASS* | RRF fusion correct; silent empty result if entity_type unknown |
| 6 | `recall_knowledge` | PASS | Legacy path functional; excludes archived tier |
| 7 | `list_workfiles` | PASS | Component grouping or file listing depending on params |
| 8 | `unstash` | PASS | Retrieves by component, updates access stats |
| 9 | `get_ready_tasks` | PASS | Correct blocker resolution (completed OR NULL) |
| 10 | `get_incomplete_todos` | PASS | Correct status filter, LEFT JOIN sessions for timestamp |
| 11 | `check_inbox` | PASS | Broadcast + project-targeted logic correct |
| 12 | `list_recipients` | PASS | Returns active workspaces with last_session |
| 13 | `get_active_protocol` | ISSUE | Version discrepancy: MEMORY.md says v11, CLAUDE.md says v12 |
| 14 | `search_bpmn_processes` | PASS* | Falls back to ILIKE if Voyage unavailable |
| 15 | `recall_book_reference` | ISSUE | Books migrated to Entity Catalog; sparse data expected |

---

## Issues Found

| # | Severity | Issue | Action |
|---|----------|-------|--------|
| 1 | Low | `get_active_protocol`: MEMORY.md says v11, CLAUDE.md says v12 — DB version unknown | Verify: `SELECT version FROM claude.protocol_versions WHERE is_active = true` |
| 2 | Low | `recall_book_reference`: books migrated to Entity Catalog (49 entities, 2026-03-13); `claude.book_references` likely sparse | Update docstring to recommend `recall_entities(entity_type='book')` instead |
| 3 | Low | `recall_entities`: unknown `entity_type` silently returns empty results | Add validation against `claude.entity_types` with helpful error message |
| 4 | Low | `VOYAGE_API_KEY` in `mcp.json` is `${VOYAGE_API_KEY}` (unexpanded placeholder); server self-heals via .env fallback but path is fragile | Replace with literal key in mcp.json |

---

## Environment

| Item | Status |
|------|--------|
| `DATABASE_URI` | Set correctly in `~/.claude/mcp.json` env block |
| `VOYAGE_API_KEY` | Unexpanded in mcp.json; loaded from `~/OneDrive/.../ai-workspace/.env` at server startup |
| `server.py` import | All async tool functions imported correctly (lines 3240-3267) |
| `_run_async` bridge | Handles both async and sync contexts correctly |

**Full detail**: See [project-tools-functional-test-detail-2026-03-14.md](project-tools-functional-test-detail-2026-03-14.md)

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: knowledge-vault/10-Projects/Project-Metis/project-tools-functional-test-2026-03-14.md
