---
projects:
- claude-family
- nimbus-mui
- nimbus-odata-configurator
- monash-nimbus-reports
tags:
- mcp
- nimbus
- shutdown-review
synced: false
---

# nimbus-knowledge MCP: Shutdown Review

**Recommendation**: Migrate small tables now; keep entity server running until tooling replacement ships. See details below.

---

## Quick Reference

| Item | Value |
|------|-------|
| Server location | `C:\Projects\nimbus-mui\mcp-server\server.py` |
| DB schema | `nimbus_context` (separate from `claude.*`) |
| Tools exposed | 10 (7 read, 3 write) |
| Active dependents | 3 projects (odata-configurator, monash-nimbus-reports, nimbus-mui) |
| Configured but inactive | 2 projects (nimbus-import, nimbus-user-loader) |

---

## Documents

| Document | Contents |
|----------|----------|
| [Part 1 - Data and Dependents](nimbus-knowledge-part1.md) | Schema tables, row counts, project dependency matrix, tool inventory |
| [Part 2 - Migration and Recommendation](nimbus-knowledge-part2.md) | Migration mapping, effort estimate, risks, shutdown steps, final recommendation |

---

## Recommendation Summary

**Migrate the 34 small-table rows now** (learnings, facts, patterns) to `claude.knowledge` LONG tier via `remember()`. These benefit immediately from RAG and auto-surfacing.

**Keep the entity server running** until `get_entity_schema` / `search_entities` equivalents are added to project-tools targeting `claude.entities`. The 366-entity / 7,357-property dataset needs purpose-built query tooling before the server can be retired.

**Full shutdown trigger**: When entity lookup tools land in project-tools, migrate `api_entities` / `api_properties` and remove the server from all 5 project configs.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: C:\Projects\claude-family\docs\nimbus-knowledge-shutdown-review.md
