# F98 Migration: Books & Knowledge Routing

**Status**: Migration file created
**Date**: 2026-02-11
**Tasks**: BT324 (Book Reference System) + BT326 (Knowledge Routing)

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/sql/f98_schema.sql` | Full migration with 3 tables, 7 indexes, column registry, 10 seed routes |
| `docs/F98_MIGRATION_SUMMARY.md` | Quick overview (this directory) |
| `knowledge-vault/.../F98_Schema_Details.md` | Technical reference (vault) |

---

## What's in the Migration

**3 Tables**:
1. `claude.books` - Book metadata (title, author, ISBN, topics)
2. `claude.book_references` - Concept references with VECTOR(1024) embeddings
3. `claude.knowledge_routes` - Task pattern → knowledge source routing (10 seed routes)

**7 Indexes**: GIN on arrays, B-tree on text, ivfflat on vectors

**4 Column Registry Entries**: Validate knowledge_type, priority, tags, topics

**Prerequisites**: pgvector extension (already in use)

---

## To Run

```bash
psql -U postgres -d ai_company_foundation -f scripts/sql/f98_schema.sql
```

Includes verification queries and ON CONFLICT logic for safe re-runs.

---

**For details see**: `knowledge-vault/10-Projects/claude-family/F98_Schema_Details.md`
