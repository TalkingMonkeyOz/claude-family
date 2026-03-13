---
projects:
- claude-family
tags:
- schema-audit
- data-model
- metis
synced: false
---

# Claude Family - Full Schema Audit (Index)

**Database**: ai_company_foundation, schema: claude
**Basis**: Static codebase analysis. Row counts from 2026-02-28 post-ANALYZE snapshot.
**Live data script**: `scripts/run_schema_audit.py` — run to get current counts.

---

## Detail Documents

| Section | File | Coverage |
|---------|------|----------|
| Table inventory, dead weight | [[schema-audit-tables]] | 60 tables, row counts, empty/zero tables, scan stats |
| Column registry, BPMN, state machines | [[schema-audit-registry]] | column_registry, BPMN process list, workflow transitions |
| Indexes, sizes, spot checks, recommendations | [[schema-audit-indexes]] | index analysis, table sizes, data quality issues, Metis design notes |

Vault path: `knowledge-vault/10-Projects/Project-Metis/research/`

---

## Summary

- **60 tables** (58 post-cleanup + `project_workfiles` + `activities`, both added 2026-03-09/10)
- **6 empty tables**: workflow_state, process_data_map, rag_query_patterns, instructions_versions, rules_versions, skills_versions
- **3 degraded tables**: schema_registry (101 rows, 43 stale), mcp_usage (6,965 rows all synthetic), enforcement_log (zombie writes)
- **28 workflow transitions** across 3 entity types (feedback, features, build_tasks)
- **60+ BPMN processes** — sync script broken (ImportError), registry stale
- **Critical gotcha**: `build_tasks.status` valid value is `todo` NOT `pending` — stale vault doc says otherwise

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: C:\Projects\claude-family\docs\metis-data-model-research-full-schema.md
