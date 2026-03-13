---
projects:
- claude-family
- project-metis
tags:
- research
- data-model
- postgresql
- jsonb
synced: false
---

# Data Structure Research: Modern Database Approaches

Part of [data-structure-research.md](data-structure-research.md) — EAV, JSONB, STI, property graphs.

---

## EAV (Entity-Attribute-Value) — DON'T

PostgreSQL community consensus: "don't do it" (Cybertec, Art of PostgreSQL).

**Performance vs JSONB** (benchmarks):
- **Storage**: EAV 6.43GB vs JSONB 2.08GB (3x less)
- **Updates without indexes**: JSONB 50,000x faster
- **Selects with GIN + @>**: JSONB 15,000x faster
- **Selects with B-tree**: EAV 1.3x faster for single-property lookups

**Row-level locking**: EAV locks multiple rows per entity update. JSONB locks one row. Critical difference for concurrent access.

**Verdict**: JSONB does everything EAV does, faster, with less storage. EAV is a documented anti-pattern.

## JSONB + GIN Indexing

Two GIN operator classes:
- **`jsonb_ops`** (default): indexes every key and value. Supports `?`, `?|`, `?&`, `@>`.
- **`jsonb_path_ops`**: indexes only value paths as hashes. Smaller index, faster `@>`. No key-existence (`?`).

**Best practices for heterogeneous data**:
```sql
-- General containment (find books by author)
CREATE INDEX idx_props ON entities USING GIN(properties jsonb_path_ops);
-- Supports: WHERE properties @> '{"author": "Fowler"}'

-- Hot-key expression index (frequent filter on entity_set)
CREATE INDEX idx_entity_set ON entities ((properties->>'entity_set'))
WHERE entity_type = 'odata_entity';
```

**Write overhead**: GIN adds overhead. Mitigated by `fastupdate=on` (default) and `REINDEX CONCURRENTLY`. Our system is read-heavy (recall >> remember), so acceptable.

**Rule**: Use `@>` containment (GIN-friendly), not `->>` path extraction (needs expression index or seq scan).

## Single Table Inheritance (STI)

One table with discriminator column + all possible columns from all types. NULL for inapplicable fields.

Works for 3-5 types. Degrades for open-ended type systems because:
- Dozens of NULL columns per row
- Table becomes incomprehensible
- Every new type = ALTER TABLE

**JSONB hybrid is superior**: No NULL waste, no ALTER TABLE for new types, GIN gives fast querying.

## Table-per-Type

Each type gets its own table. Our current approach: `books`, `book_references`, `knowledge`, `project_workfiles`.

**Pros**: Strong types, clear queries, targeted indexes.
**Cons**: No unified search, tool explosion (N tools for N types), adding a type costs 2-4 hours (table + MCP tools + BPMN + tests + docs + column_registry).

## Apache AGE (Property Graphs)

Adds Cypher graph traversal to PostgreSQL. Stores vertices + edges with `agtype` (JSONB superset).

**Pros**: Native graph traversal, ACID-compliant.
**Cons**: Cypher alongside SQL (complexity), limited maturity, doesn't integrate with pgvector, our relationship needs are simple.

**Verdict**: Entity_relationships table gives us the edges we need. AGE is overkill. Revisit if we need multi-hop graph reasoning.

---

## Sources

- Cybertec: EAV in PostgreSQL — Don't Do It
- coussej.github.io: Replacing EAV with JSONB in PostgreSQL
- Evolveum: JSON vs EAV (MidScale comparison)
- Crunchy Data: Indexing JSONB
- pganalyze: GIN Index Guide
- Martin Fowler: Single Table Inheritance
- Apache AGE documentation

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/research/data-structure-modern-db.md
