---
projects:
- claude-family
- Project-Metis
tags:
- schema
- database
- embeddings
- rag
- governance
- design-tooling
synced: false
---

# Schema Governance - 3-Layer Architecture

Self-documenting, searchable, BPMN-validated database schema management. The foundation for **schema-aware design**: overlay DB structure on BPMN flows so you understand the data landscape before writing code.

## Overview

| Layer | Script/Tool | Purpose |
|-------|------------|---------|
| L1 | `scripts/schema_docs.py` | Introspect pg_catalog, generate COMMENT ON, sync registries |
| L2 | `scripts/embed_schema.py` | Embed table metadata via Voyage AI for semantic search |
| L3 | `validate_process_schema()` | BPMN MCP tool validating data refs against live schema |

Each layer depends on the previous. L1 is the foundation.

## Design-Time Usage (Schema + BPMN Overlay)

The core idea: **pull back a BPMN flow, overlay the DB schema, and understand the full data landscape before designing or coding**. This prevents recreating from scratch every time.

### Workflow: Designing a New Feature

```
1. DISCOVER existing flows
   search_bpmn_processes("topic related to your feature")
   → Returns matching processes with similarity scores

2. UNDERSTAND what data those flows touch
   validate_process_schema("related_process_id")
   → Shows every table referenced by [DB] tasks and data objects

3. RECALL the table structures
   get_schema(tier=1)   # core tables
   get_schema(tier=2)   # + infrastructure tables
   → Token-budgeted schema with columns, types, constraints, valid values

4. DESIGN your new schema with full awareness
   → You know what exists, what to reuse, what to extend

5. MODEL your new BPMN with [DB] task references
   → Tag tasks as [DB] Read claude.your_table, [DB] Write claude.your_table

6. VALIDATE your model
   validate_process_schema("your_new_process")
   → Confirms all data references resolve against the live schema

7. TEST with schema awareness
   → pytest tests can use get_current_step() to walk the flow
   → process_data_map tracks which processes touch which tables
```

### Key MCP Tools for Design

| Tool | Server | Purpose |
|------|--------|---------|
| `get_schema(tier)` | project-tools | Token-budgeted schema recall with constraints |
| `validate_process_schema(id)` | bpmn-engine | Validate BPMN data refs against live schema |
| `search_bpmn_processes(query)` | project-tools | Find processes by semantic search |
| `check_alignment(id)` | bpmn-engine | Verify BPMN model matches code artifacts |
| `get_process(id)` | bpmn-engine | Read process structure (elements, flows) |
| `get_current_step(id, completed)` | bpmn-engine | Walk a flow step-by-step for testing |

### Supporting Data

| Table | Purpose |
|-------|---------|
| `claude.schema_registry` | Table metadata + Voyage AI embeddings (58 rows) |
| `claude.column_registry` | Constrained column values from CHECK constraints (88 rows) |
| `claude.process_data_map` | Which BPMN processes read/write which tables |
| `claude.bpmn_processes` | BPMN process registry with embeddings |

### Auto-Injection via RAG

When you ask a schema-related question (mentioning "table", "column", "schema", etc.), the RAG hook automatically queries `schema_registry` embeddings and injects matching table structures into context. No manual lookup needed for conversational questions.

## Layer 1: Schema Self-Documentation

**Script**: `scripts/schema_docs.py`

**CLI Options**:
```bash
python scripts/schema_docs.py --report              # Coverage report
python scripts/schema_docs.py --generate-comments    # Generate SQL file
python scripts/schema_docs.py --apply-comments       # Apply COMMENT ON statements
python scripts/schema_docs.py --sync-registry        # Sync schema_registry table
python scripts/schema_docs.py --sync-column-registry # Sync column_registry from CHECK constraints
python scripts/schema_docs.py --all                  # Run everything
```

**What it does**:
- Introspects `pg_catalog`, `information_schema`, `pg_description`
- Generates intelligent `COMMENT ON TABLE/COLUMN` from column names, types, FK relationships
- Syncs `claude.schema_registry` with table descriptions, column info, FK relationships
- Extracts CHECK constraint values into `claude.column_registry`

**Results (2026-03-04)**: 58 tables (post Pre-Metis cleanup), 762 columns. Table comments: 100%. Column comments: 99.1%. schema_registry: 100%.

## Layer 2: Schema Embeddings + RAG

**Script**: `scripts/embed_schema.py`

**CLI Options**:
```bash
python scripts/embed_schema.py              # Embed all (incremental)
python scripts/embed_schema.py --force      # Re-embed everything
python scripts/embed_schema.py --table X    # Embed single table
python scripts/embed_schema.py --dry-run    # Preview without writing
```

**What it does**:
- Builds rich text per table (name, purpose, columns, FKs, constraints, row count)
- Generates Voyage AI embeddings (voyage-3, 1024 dimensions)
- Stores in `claude.schema_registry.embedding` column
- Hash-based incremental updates (skips unchanged tables)

**RAG Integration** (`scripts/rag_query_hook.py`):
- `needs_schema_search(prompt)` detects schema-related questions via keyword list
- `query_schema_context(prompt)` queries pgvector cosine distance on schema_registry
- Results injected as `SCHEMA CONTEXT` block alongside vault/knowledge context
- Keywords: table, column, schema, database, foreign key, constraint, data model, etc.

**Results**: All 58 tables embedded. Semantic search verified working.

## Layer 3: BPMN-Schema Validation

**MCP Tool**: `validate_process_schema(process_id)` in bpmn-engine

**What it does**:
- Extracts data references from BPMN processes:
  - `<bpmn:dataObjectReference>` elements
  - Tasks prefixed with `[DB]`
  - Documentation containing `claude.*` table references
- Validates each reference against live database schema
- Reports coverage percentage and invalid references

**Supporting Table**: `claude.process_data_map`
- Tracks which BPMN processes read/write which tables
- Columns: process_id, table_name, access_type, element_id, source

## Key Gotchas

- `information_schema.key_column_usage` has NO `constraint_type` column — must JOIN through `table_constraints`
- `column_registry.valid_values` is JSONB — needs `json.dumps()` + `::jsonb` cast
- `column_registry.data_type` is NOT NULL — provide default when syncing from constraints
- psycopg `dict_row` requires explicit `AS alias` for computed columns (e.g., `col_description() AS comment`)
- `claude.schema_registry.embedding` column added by `embed_schema.py` on first run via ALTER TABLE

## Running the Full Pipeline

```bash
# Step 1: Self-document (generates comments, syncs registries)
python scripts/schema_docs.py --all

# Step 2: Embed for RAG (incremental, skips unchanged)
python scripts/embed_schema.py

# Step 3: Validate BPMN data refs (after MCP restart)
# Use via bpmn-engine MCP: validate_process_schema("process_id")
```

## BPMN Model

The schema governance pipeline is fully modeled: `schema_governance` (19 elements, 22 flows).

Three modes via `pipeline_mode` gateway:
- **full** (default): L1 introspect → L2 embed → L3 validate
- **embed_only**: Skip introspection, just re-embed
- **validate_only**: Skip introspection + embedding, just validate BPMN data refs

Run `validate_process("schema_governance")` to test the model.

## Related

- [[Vault Embeddings Management SOP]] — same Voyage AI pipeline for vault docs
- [[RAG Usage Guide]] — how RAG hook works
- [[Config Management SOP]] — database as source of truth pattern
- BPMN model: `processes/infrastructure/schema_governance.bpmn`

---
**Version**: 2.0
**Created**: 2026-02-28
**Updated**: 2026-03-04
**Location**: knowledge-vault/20-Domains/Schema Governance.md
