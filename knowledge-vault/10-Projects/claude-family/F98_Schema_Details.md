---
projects:
- claude-family
tags:
- database
- schema
- f98
- books
- knowledge-routing
synced: false
---

# F98 Schema Details - Books & Knowledge Routing

**Feature**: F98 - Knowledge Routing and Book Reference Integration
**Build Tasks**: BT324 (Book Reference System) + BT326 (Knowledge Routing)
**Migration File**: `scripts/sql/f98_schema.sql`
**Created**: 2026-02-11

---

## Table 1: claude.books (BT324)

**Purpose**: Store book metadata and topics for knowledge management

| Column | Type | Constraints |
|--------|------|-----------|
| `book_id` | UUID | PK, auto-generated |
| `title` | VARCHAR(500) | NOT NULL |
| `author` | VARCHAR(300) | NULL |
| `isbn` | VARCHAR(20) | NULL |
| `year` | INTEGER | NULL |
| `topics` | TEXT[] | DEFAULT '{}' |
| `summary` | TEXT | NULL |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() |

**Indexes**:
- `idx_books_topics` - GIN on topics array for fast filtering
- `idx_books_title` - B-tree on title for text search

**Use Case**: Store reusable book references, topics array enables multi-faceted filtering (e.g., books about "Python AND testing").

---

## Table 2: claude.book_references (BT324)

**Purpose**: Store references to specific concepts with vector embeddings for semantic search

| Column | Type | Constraints |
|--------|------|-----------|
| `ref_id` | UUID | PK, auto-generated |
| `book_id` | UUID | FK → books.book_id, CASCADE |
| `chapter` | VARCHAR(200) | NULL |
| `page_range` | VARCHAR(50) | NULL |
| `concept` | VARCHAR(500) | NOT NULL |
| `description` | TEXT | NULL |
| `quote` | TEXT | NULL |
| `tags` | TEXT[] | DEFAULT '{}' |
| `embedding` | VECTOR(1024) | NULL |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() |

**Indexes**:
- `idx_book_refs_book` - B-tree on book_id (FK lookups)
- `idx_book_refs_tags` - GIN on tags (concept filtering)
- `idx_book_refs_concept` - B-tree on concept (exact match)
- `idx_book_refs_embedding` - ivfflat vector index (semantic search, cosine distance, lists=10)

**Vector Details**:
- VECTOR(1024) matches Voyage AI (voyage-3) embedding dimensions
- ivfflat index balances query speed vs. memory usage
- Cosine distance for semantic similarity (typical for text embeddings)

**Use Case**: Find related concepts across books via semantic search. Examples:
- "Show me references about error handling" → ivfflat search on embedding
- "Find quotes on page 42" → indexed by page_range
- "What concepts are tagged 'SOLID'?" → GIN search on tags array

---

## Table 3: claude.knowledge_routes (BT326)

**Purpose**: Route task patterns to knowledge sources with priority ranking

| Column | Type | Constraints |
|--------|------|-----------|
| `route_id` | UUID | PK, auto-generated |
| `task_pattern` | VARCHAR(500) | NOT NULL |
| `knowledge_source` | VARCHAR(500) | NOT NULL |
| `knowledge_type` | VARCHAR(50) | NOT NULL, CHECK IN ('sop', 'pattern', 'book', 'domain', 'tool') |
| `description` | TEXT | NULL |
| `priority` | INTEGER | DEFAULT 3, CHECK BETWEEN 1-5 |
| `active` | BOOLEAN | DEFAULT TRUE |
| `created_at` | TIMESTAMPTZ | DEFAULT NOW() |
| `updated_at` | TIMESTAMPTZ | DEFAULT NOW() |

**Indexes**:
- `idx_knowledge_routes_active` - Partial B-tree on active=TRUE (common filter)
- `idx_knowledge_routes_type` - B-tree on knowledge_type (filtering by source type)

**Valid Values**:
- `knowledge_type`: sop, pattern, book, domain, tool
- `priority`: 1 (critical), 2, 3 (default), 4, 5 (low)

**Use Case**: When task pattern "update CLAUDE.md" is detected, routes point to:
- Priority 1: Config Management SOP (vault doc)
- Priority 1: update_claude_md tool (MCP)

Agent can query routes and prioritize sources by priority number.

---

## Column Registry Entries

Four entries in `claude.column_registry` enforce data validation:

```sql
-- books.topics - free form array
-- book_references.tags - free form array
-- knowledge_routes.knowledge_type - constrained to 5 values
-- knowledge_routes.priority - constrained to 1-5
```

Upserts use `ON CONFLICT DO UPDATE` to safely re-run without duplicates.

---

## Seeded Knowledge Routes (10 total)

Initial routes cover core Claude Family operations:

**Priority 1 (Critical)**:
- "update CLAUDE.md" → Config Management SOP (sop)
- "update CLAUDE.md" → update_claude_md tool (tool)
- "create new project" → New Project SOP (sop)
- "add MCP server" → Add MCP Server SOP (sop)

**Priority 2 (High)**:
- "database schema" → Database Integration Guide (domain)
- "winforms" → WinForms Best Practices (domain)
- "hook" → Claude Hooks doc (domain)
- "agent delegation" → Agent Selection Decision Tree (pattern)
- "session workflow" → Session Lifecycle SOP (sop)
- "RAG knowledge retrieval" → RAG Usage Guide (domain)

Routes are seeded with `ON CONFLICT DO NOTHING` (idempotent).

---

## Architecture Decisions

**Why Separate Tables**:
1. **books** + **book_references** split allows:
   - Many references per book (normalized)
   - Book discovery (search books table) vs. concept discovery (search references)
   - Cascade delete keeps consistency

2. **knowledge_routes** as separate table allows:
   - Routing logic decoupled from actual sources
   - Update routes without touching source documents
   - A/B test new routes via priority/active flag
   - No need to modify CLAUDE.md or vault structure

**Indexing Rationale**:
- GIN on TEXT[] (topics, tags) - optimal for contains/overlap queries
- Partial index on active=TRUE - common filter reduces scan
- ivfflat on VECTOR - balance of speed (lists=10) vs. memory
- B-tree on text fields - exact match and range queries

**Extensibility**:
- knowledge_type enum prevents invalid source types
- Priority system (1-5) allows customization without schema changes
- Active flag enables testing without deletion
- Can add more columns (e.g., `condition`, `tags_required`) without breaking changes

---

## Integration Points

**RAG System**:
- Embeddings in book_references can feed semantic search in vault
- Knowledge routes can determine which vault docs to retrieve

**Agent Tools**:
- Query knowledge_routes to find sources for task pattern
- Fetch book_references by concept or semantic similarity
- Populate context before running agents

**Session Workflow**:
- PreCompact hook can query routes based on current task
- Inject relevant knowledge before context compaction

---

## Prerequisites

**pgvector Extension Required**:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Already in use (vault_embeddings table has VECTOR(1024) columns), so safe to run.

---

## Verification Queries

After migration:

```sql
-- Tables exist
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'claude' AND table_name IN ('books', 'book_references', 'knowledge_routes');

-- Indexes created
SELECT indexname FROM pg_indexes WHERE schemaname = 'claude'
AND (indexname LIKE 'idx_books%' OR indexname LIKE 'idx_book_refs%' OR indexname LIKE 'idx_knowledge%');

-- Column registry
SELECT table_name, column_name, data_type FROM claude.column_registry
WHERE table_name IN ('books', 'book_references', 'knowledge_routes');

-- Routes seeded
SELECT COUNT(*) FROM claude.knowledge_routes;
```

---

**Version**: 1.0
**Created**: 2026-02-11
**Updated**: 2026-02-11
**Location**: C:\Projects\claude-family\knowledge-vault\10-Projects\claude-family\F98_Schema_Details.md
