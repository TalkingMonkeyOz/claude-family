---
projects:
- claude-family
tags:
- audit
- structured-data
- schema
- odata
- nimbus-knowledge
synced: false
---

# Audit: Structured Data — Inventory and Storage (Part 1 of 2)

**Index**: `docs/audit-structured-data.md`
**Part 2**: [[audit-structured-data-part2]]
**Date**: 2026-03-12

---

## Executive Summary

Structured reference data splits across three separate stores with no unified access model:

1. **`nimbus_context` schema** — the richest store: 366 OData entity definitions, thousands of API properties, code patterns, learnings, and facts. Accessible via the nimbus-knowledge MCP at `C:\Projects\nimbus-mui\mcp-server\server.py`. Functional, but absent from claude-family's MCP list (by design — scoped to Nimbus projects).
2. **Vault documents** (`knowledge-vault/20-Domains/APIs/`) — four hand-written Nimbus API gotcha notes. Embedded and RAG-searchable. Narrow in scope.
3. **`claude.knowledge`** (717 entries) — general Claude Family operational knowledge. Narrative, not machine-readable schema data.

Key gaps: no OData schema store for non-Nimbus systems, 43% of `schema_registry` is stale, no cross-reference between vault docs and nimbus_context entities.

---

## Inventory Table

| Data Type | Where Stored | Retrievable? | Volume |
|-----------|-------------|--------------|--------|
| Nimbus OData entity schemas | `nimbus_context.api_entities` + `api_properties` | nimbus-knowledge MCP (Nimbus projects only) | 366 entities, thousands of properties |
| Nimbus API code patterns | `nimbus_context.code_patterns` | nimbus-knowledge MCP | Unknown count |
| Nimbus project learnings | `nimbus_context.project_learnings` | nimbus-knowledge MCP | Unknown count |
| Nimbus project facts | `nimbus_context.project_facts` | nimbus-knowledge MCP | Unknown count |
| Nimbus entity dependency order | `nimbus_context.api_entities` (order field) | `get_dependency_order` tool | Critical for imports |
| Nimbus API gotchas (vault) | `knowledge-vault/20-Domains/APIs/*.md` | RAG auto-injected | 4 documents, embedded |
| Claude schema column constraints | `claude.column_registry` | Direct SQL | 87 entries, ~12 tables |
| Claude table descriptions | `claude.schema_registry` | Direct SQL | 101 entries, 43 stale |
| General knowledge/patterns | `claude.knowledge` | `recall_memories()` MCP | 717 entries (3-tier) |
| BPMN process models | `claude.bpmn_processes` + filesystem | bpmn-engine MCP | ~71 DB, 63 BPMN files |
| Book references | `claude.book_references` | `recall_book_reference()` | 46 entries, 3 books |
| Nimbus Azure SQL (live) | Azure SQL (prod-ausespoke3-db-server-001) | nimbus-db MCP (read-only) | 3 database instances |
| Vault document embeddings | `claude.vault_embeddings` | RAG hook (auto) | 9,655 embeddings |

---

## Nimbus-Knowledge MCP Analysis

### Status: Functional, Scoped to Nimbus Projects

The server exists and is complete at `C:\Projects\nimbus-mui\mcp-server\server.py`.
A gotcha note documents the correct location: `knowledge-vault/30-Patterns/gotchas/nimbus-knowledge MCP Location.md`.
The server is correctly absent from claude-family's `settings.local.json` — it loads in Nimbus project contexts only.

### 10 Tools

| Tool | Purpose |
|------|---------|
| `get_entity_schema` | Full OData property definitions for any of 366 entities |
| `search_entities` | Find entities by keyword |
| `get_code_pattern` | Reusable Nimbus API code patterns |
| `get_learnings` | Lessons learned (success/failure/pattern) |
| `get_facts` | Project facts and constraints by category |
| `get_dependency_order` | Entity creation order (critical for imports) |
| `add_learning` | Capture new learnings |
| `add_fact` | Record facts/constraints |
| `add_code_pattern` | Add reusable code patterns |
| `get_stats` | Knowledge base statistics |

### Backing Schema: `nimbus_context`

| Table | Content |
|-------|---------|
| `api_entities` | 366 Nimbus OData entities, EntitySet names, namespaces, descriptions |
| `api_properties` | Per-entity properties: type, nullability, key flags, navigation targets |
| `code_patterns` | Integration code (batch-upload, session-affinity, OData parsing) |
| `project_learnings` | Documented successes, failures, patterns |
| `project_facts` | Constraints, architecture decisions, API quirks |

### RAG Fallback: Incomplete

`rag_query_hook.py` has a `query_nimbus_context()` function that queries these tables directly using keyword search (no vector similarity). It only triggers for projects in `NIMBUS_PROJECTS = ['monash-nimbus-reports', 'nimbus-user-loader', 'nimbus-customer-app', 'ATO-Tax-Agent']`. Claude-family is not in this list. The MCP tool is the correct access path.

### Second Nimbus MCP: nimbus-db

`C:\Projects\nimbus-mui\mcp-server-nimbus-db\server.py` provides live read-only access to Nimbus Azure SQL databases (test, staging, audit instances of Nimbus_Monash) via Microsoft Entra MFA. Tools: `execute_sql`, `list_tables`, `describe_table`, `get_connection_status`, `list_databases`. Separates documented knowledge (nimbus-knowledge MCP) from live data (nimbus-db MCP).

---

## Vault Domain Content (`20-Domains/`)

### What Exists

| Path | Type | Quality |
|------|------|---------|
| `APIs/nimbus-odata-field-naming.md` | gotcha | Good — `Description` not `Name`, confidence 95, synced |
| `APIs/nimbus-rest-crud-pattern.md` | pattern | Good — POST for both create/update, confidence 95, synced |
| `APIs/nimbus-activity-type-prefixes.md` | pattern | Good — `TT:/S:/U:` prefixes, confidence 90, synced |
| `APIs/nimbus-time-fields.md` | api-reference | Good — local times only for ScheduleShift, confidence 95, synced |
| `CSharp/csharp-expert-rules.md` | rules | Present |
| `Database/local-reasoning-deepseek.md` | architecture | DeepSeek-r1 LLM notes; misclassified in Database folder |
| `Database/mui-mcp-installation.md` | setup | MUI MCP install notes; misclassified in Database folder |
| `WinForms/*.md` | patterns | 4 documents; async, databinding, designer rules, layout |
| `Infrastructure Stats and Monitoring.md` | domain | Hook performance metrics, hook coverage stats |
| `awesome-copilot-reference/` | external repo | Cloned git repo; not vault knowledge; not embedded |

### Gaps

The README lists these planned but unwritten documents: PostgreSQL Operations, Git/Version Control, Testing Patterns, Tauri Desktop, HTMX/Alpine.js, React/MUI, Claude API Integration, Agentic Orchestration, Knowledge Management, Security/Secrets. The Database subfolder contains only non-database content.

The `awesome-copilot-reference/` folder is a full git clone living inside the vault. It pollutes glob output used for vault embedding and should be relocated outside the vault or removed.

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/audit/audit-structured-data-part1.md
