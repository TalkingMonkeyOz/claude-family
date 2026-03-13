---
projects:
- claude-family
tags:
- audit
- structured-data
synced: false
---

# Audit: Structured Data Storage and Retrieval (Index)

**Date**: 2026-03-12
**Scope**: Schemas, APIs, OData definitions across Claude Family.

## Detail Documents

| Section | File |
|---------|------|
| Inventory, nimbus-knowledge, vault content | [[audit-structured-data-part1]] |
| knowledge table, column registry, gaps, recommendations, findings | [[audit-structured-data-part2]] |

Vault path: `knowledge-vault/10-Projects/audit/`

## One-Line Summary

Structured reference data lives in three places: `nimbus_context` schema (366 OData entities,
accessible via nimbus-knowledge MCP at `C:\Projects\nimbus-mui\mcp-server\server.py`),
four vault gotcha docs in `20-Domains/APIs/`, and `claude.knowledge` (717 narrative entries).
Non-Nimbus API schemas have no home. `column_registry` covers 20% of claude tables by design.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\audit-structured-data.md
