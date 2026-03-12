---
projects:
- claude-family
tags:
- design
- storage
- entities
- integration
synced: false
---

# Entities System — Integration & Boundaries

**Parent**: [entities-system.md](entities-system.md)

---

## Claude Code Boundaries

### What Claude Code Provides Natively

| Feature | Claude Code Built-in | How It Works |
|---------|---------------------|-------------|
| Auto-memory | `MEMORY.md` in `~/.claude/projects/<hash>/memory/` | Claude writes files with frontmatter (type: user/feedback/project/reference) |
| `/memory` command | Lists/manages memory files | User can review and delete |
| Context compaction | Automatic when context fills | Compresses older messages |
| Task system | `TaskCreate`/`TaskUpdate`/`TaskList` | Session-scoped, deleted on completion |
| Session resume | None built-in | Each session starts fresh |

### What Our System Adds

| Feature | Our Custom System | Why Needed |
|---------|-------------------|-----------|
| DB-backed session facts | `store_session_fact()` | Survives compaction (MEMORY.md does not) |
| 3-tier memory | `remember()` / `recall_memories()` | Cross-session knowledge with confidence |
| Semantic search | Voyage AI + pgvector | CC memory is file-based, no semantic retrieval |
| Entities catalog | `catalog()` / `recall()` CTE | Structured reference data with type validation |
| Work tracking | features / build_tasks / feedback | Persistent project management (CC tasks ephemeral) |
| Multi-instance | Messaging, shared DB | CC is single-instance only |
| RAG | Vault embeddings + hook injection | CC has no equivalent |
| Pre-compaction | Hook injects active state | CC compaction loses context; ours preserves |

### Complementary Boundaries

- **MEMORY.md** — Always-loaded tier. Small, curated, project-scoped. Equivalent to a pinned index.
- **Session facts** — Within-session persistence that survives compaction.
- **Entities** — Typed, validated, structured data that outlives any session (books, APIs, schemas).
- **Knowledge** (remember/recall) — Unstructured learnings, patterns, gotchas.
- **Dossiers** (workfiles) — Multi-session research notes on specific topics.

The entities system fills the gap for **typed, validated, structured data** none of the other mechanisms address.

---

## Filing Alignment

Entity types map to Metis 8 knowledge types:

| Entity Type | Metis Knowledge Type | Filing Category |
|-------------|---------------------|-----------------|
| book | reference | 20-Domains/Books/ |
| book_concept | reference | 20-Domains/Books/ |
| odata_entity | domain | 20-Domains/APIs/ |
| api_endpoint | domain | 20-Domains/APIs/ |
| knowledge_pattern | pattern | 30-Patterns/ |
| process_model | procedure | 40-Procedures/ |

The `project_id` field provides multi-tenancy — entities are scoped to projects but searchable across the whole catalog when `project_id` is NULL.

---

## Cross-Referencing Queries

### All API endpoints for a specific project

```sql
SELECT e.display_name, e.properties->>'method', e.properties->>'path'
FROM claude.entities e
JOIN claude.entity_types et ON e.entity_type_id = et.type_id
WHERE et.type_name = 'api_endpoint'
  AND e.project_id = (SELECT project_id FROM claude.projects
                      WHERE project_name = 'nimbus-odata-configurator');
```

### Books and their concepts (via relationships)

```sql
SELECT book.display_name AS book,
       concept.properties->>'concept' AS concept
FROM claude.entities book
JOIN claude.entity_relationships rel ON rel.from_entity_id = book.entity_id
JOIN claude.entities concept ON concept.entity_id = rel.to_entity_id
JOIN claude.entity_types bt ON book.entity_type_id = bt.type_id
    AND bt.type_name = 'book'
JOIN claude.entity_types ct ON concept.entity_type_id = ct.type_id
    AND ct.type_name = 'book_concept';
```

### Cross-type property search

```sql
SELECT e.display_name, et.type_name, e.properties
FROM claude.entities e
JOIN claude.entity_types et ON e.entity_type_id = et.type_id
WHERE e.properties::text ILIKE '%time2work%'
  AND NOT e.is_archived;
```

---

## Dossier-to-Entity Linking

Workfiles reference entities through `entity_relationships`:

```sql
INSERT INTO claude.entity_relationships
    (from_entity_id, to_entity_id, relationship_type, metadata)
VALUES (
    '<workfile_entity_id>', '<odata_entity_id>', 'references',
    '{"context": "Research notes on this entity"}'
);
```

---

## Task/Feature Retrieval Integration

When `recall()` runs during active work:

1. **During feature work**: Entities linked to the current feature get a relevance boost in RRF scoring.
2. **During session resume**: `start_session()` surfaces recently accessed entities.
3. **WCC integration**: Entities matching an activity name/aliases are included as a source.

### Session Resume

```python
# In start_session(), surface recent entities
cur.execute("""
    SELECT e.display_name, et.type_name, e.last_accessed_at
    FROM claude.entities e
    JOIN claude.entity_types et ON e.entity_type_id = et.type_id
    WHERE e.project_id = %s AND NOT e.is_archived
      AND e.last_accessed_at > NOW() - INTERVAL '7 days'
    ORDER BY e.last_accessed_at DESC LIMIT 5
""", (project_id,))
```

### BPMN Integration

`cognitive_memory_retrieval.bpmn` updated with 5th parallel search branch:

```
parallel_search → search_short
                → search_mid
                → search_long
                → search_workfiles
                → search_entities  ← NEW
```

All branches merge at `parallel_join`, then rank → trim → format → update access.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/design/entities-integration.md
