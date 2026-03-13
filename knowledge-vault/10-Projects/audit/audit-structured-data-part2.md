---
projects:
- claude-family
tags:
- audit
- structured-data
- schema
- column-registry
- recommendations
synced: false
---

# Audit: Structured Data — Analysis and Recommendations (Part 2 of 2)

**Index**: `docs/audit-structured-data.md`
**Part 1**: [[audit-structured-data-part1]]
**Date**: 2026-03-12

---

## Knowledge Table as Schema Store

### Current Usage

`claude.knowledge` (717 entries) uses the 3-tier cognitive memory system (short/mid/long).
It stores operational patterns and gotchas for Claude Family infrastructure — session decisions
promoted to mid-tier and proven patterns promoted to long-tier. There is no evidence of systematic
structured data (OData schemas, field definitions, endpoint catalogs) being loaded into this table.

### Suitability for Structured Data

The table is optimized for semantic similarity search via Voyage AI embeddings and budget-capped retrieval. It suits:
- "How do I do X?" queries
- Pattern retrieval (gotchas, procedures)
- Conceptual knowledge

It is poorly suited for:
- Field-level schema lookups ("what type is `ScheduleShift.StartTime`?")
- Exhaustive entity enumeration ("list all 366 Nimbus entities")
- Machine-readable structured data consumption

The `nimbus_context` dedicated tables exist precisely because structured schema data requires a relational model, not a knowledge blob. The two systems are complementary, not competing.

---

## Column Registry Model

### Current Coverage

`claude.column_registry`: 87 entries, ~12 tables covered out of 60 (20% table coverage).
The registry tracks only **constrained columns** (enum values, range limits) — not all columns.
This is the correct design intent.

| Table | Columns Tracked | Key Constraints |
|-------|----------------|-----------------|
| `feedback` | 2 | status, feedback_type |
| `features` | 2 | status, phase |
| `build_tasks` | 2 | status (`todo` NOT `pending`), priority |
| `messages` | 2 | status, message_type |
| `knowledge_routes` | 2 | knowledge_type |
| `knowledge` | 1 | tier |
| `session_facts` | 1 | fact_type |
| `projects` | 1 | priority |

The registry is actively used by the Data Gateway pattern: `validate_db_write.py` hook queries it before INSERT/UPDATE on constrained columns. A critical discrepancy: vault doc `Work Tracking Schema.md` lists `pending` as valid for `build_tasks.status`; the registry and DB CHECK constraint both define `todo`. That vault doc is stale and actively harmful.

### Extension to External Schemas?

The column_registry model could extend to external API documentation by adding a `schema_source` column, but this would be inappropriate for full OData schemas with 366 entities and thousands of properties. The `nimbus_context` relational model handles that scale. Column registry should remain focused on internal DB constraint enforcement — its current purpose.

---

## Gap Analysis

| Gap | Impact | Notes |
|-----|--------|-------|
| No OData/REST schema store for non-Nimbus systems | High | ATO, Finance projects have no schema stores |
| `claude.schema_registry` is 43% stale (43/101 entries) | Medium | Exists to document `claude.*` tables; unreliable |
| No PostgreSQL schema documentation in vault | Medium | `20-Domains/Database/` has only DeepSeek notes |
| Vault API docs not linked to nimbus_context entities | Medium | 4 vault docs reference entities but have no frontmatter linkage |
| `awesome-copilot-reference` repo misplaced in vault | Low | Pollutes embedding glob; not vault knowledge |
| `nimbus_context` RAG fallback uses keyword search only | Low | No vector similarity; misses semantic matches |
| No endpoint → entity → field navigation path | High | Getting from "update a User" to required fields requires manual multi-source lookup |
| `COMMENT ON TABLE` not applied to claude schema tables | Low | `schema_docs.py --apply-comments` exists but not run |

---

## Architecture Recommendations

### 1. Preserve and Extend nimbus_context as the OData Schema Store

The 5-table design (`api_entities`, `api_properties`, `code_patterns`, `project_learnings`, `project_facts`) is the correct architecture for structured API data at this scale. Keep it as the primary store for all Nimbus OData/REST schema knowledge. The nimbus-db MCP (live Azure SQL) complements it for actual schema introspection against production.

### 2. Cross-Reference Vault Docs to nimbus_context Entities

Add YAML frontmatter keys to vault API docs to link them to entity names:

```yaml
entities: [Employee, ScheduleShift, ActivityType]
```

This would enable richer RAG context — returning both the gotcha doc and the relevant entity schema in one query, without duplicating content.

### 3. Create `claude.external_schemas` for Non-Nimbus APIs

For ATO, Finance, and other client-domain projects with structured APIs:

```sql
CREATE TABLE claude.external_schemas (
    id          serial PRIMARY KEY,
    project_id  uuid REFERENCES claude.projects(id),
    system_name text NOT NULL,         -- e.g., 'ato-efiling-api'
    schema_type text NOT NULL,         -- 'odata', 'rest', 'graphql', 'db-table'
    entity_name text NOT NULL,
    field_name  text,
    field_type  text,
    description text,
    notes       text,
    embedding   vector(1024),
    updated_at  timestamptz DEFAULT now()
);
```

Lighter-weight than replicating the full nimbus_context model, but provides the same searchability via Voyage AI embeddings.

### 4. Refresh `schema_registry` Via Automation

The table exists to document `claude.*` tables but is 43% stale. A scheduled job or post-migration hook that refreshes it from `information_schema` on schema changes would keep it current. Until then, `column_registry` is the more reliable self-documenting mechanism.

### 5. Relocate `awesome-copilot-reference`

Move `20-Domains/awesome-copilot-reference/` outside the vault (e.g., `references/external/`) or remove it. Its presence in `20-Domains/` pollutes the glob pattern used to discover vault documents for embedding.

### 6. Write the Missing PostgreSQL Operations Domain Doc

`20-Domains/Database/` is effectively empty of database content. A `postgresql-operations.md` document covering `claude` schema design, column_registry usage, Data Gateway pattern, and common query patterns would be the highest-value addition to the domain library.

---

## Key Findings

1. **nimbus-knowledge MCP is functional** at `C:\Projects\nimbus-mui\mcp-server\server.py` with 10 tools and 366 OData entities. Correctly absent from claude-family context; correctly present in Nimbus project contexts.

2. **`nimbus_context` schema is the right architecture** for external API structured data. The 5-table relational model serves structured queries that a knowledge blob cannot.

3. **Vault API docs are thin but accurate** — 4 documents, all embedded, all covering real gotchas. Coverage is 4 patterns against 366 entities.

4. **`column_registry` covers 20% of claude tables by design** — it is an enforcement tool for constrained columns, not a general schema catalog. Appropriate use; should not be extended to external schemas.

5. **`claude.knowledge` stores narrative knowledge, not structured schemas** — the 3-tier cognitive memory system is the right tool for patterns and procedures; `nimbus_context` is the right tool for field-level schema data. These are complementary stores.

6. **Non-Nimbus API schemas have no home** — ATO, Finance, and other projects with structured APIs have zero schema storage infrastructure.

7. **`schema_registry` is 43% stale and unreliable** — `column_registry` is the more trustworthy source for schema constraints.

8. **A second Nimbus MCP (nimbus-db) exists** at `C:\Projects\nimbus-mui\mcp-server-nimbus-db\server.py` — live read-only Azure SQL access. Separates documented knowledge from live data correctly.

9. **`nimbus_context` RAG fallback uses keyword search only** — `query_nimbus_context()` in rag_query_hook.py has no vector similarity, and claude-family is excluded from the trigger list regardless.

10. **`awesome-copilot-reference` in `20-Domains/` is misplaced** — a cloned external git repo inside the vault; not embedded; should be relocated or removed.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/audit/audit-structured-data-part2.md
