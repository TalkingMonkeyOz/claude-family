---
projects:
- project-metis
- claude-family
tags:
- research
- data-model
- schema
synced: false
---

# Schema Detail: `claude.documents`

Back to [[schema-index]]

**Row count (audit 2026-02-28)**: 5,940
**Purpose**: Document registry for all project documentation. Serves two roles: (1) metadata registry for tracked files, (2) source of `document_id` FKs used in `vault_embeddings`. Populated primarily by `embed_vault_documents.py` which creates or updates a document record for every vault/project file it embeds.

---

## Columns

| # | Column | Type | Nullable | Default | Notes |
| --- | --- | --- | --- | --- | --- |
| 1 | `doc_id` | `uuid` | NO | `gen_random_uuid()` | Primary key |
| 2 | `doc_type` | `varchar` | YES | NULL | Document type — UPPERCASE enum (16 values) |
| 3 | `doc_title` | `varchar` | YES | NULL | Human-readable title (min 5 chars) |
| 4 | `project_id` | `uuid` | YES | NULL | DEPRECATED — use `document_projects` junction table |
| 5 | `file_path` | `text` | YES | NULL | Absolute path to source file |
| 6 | `file_hash` | `varchar` | YES | NULL | SHA-256 for change detection |
| 7 | `version` | `varchar` | YES | NULL | Semantic version string (e.g., `1.0`, `2.3`) |
| 8 | `status` | `varchar` | YES | NULL | `ACTIVE` or `ARCHIVED` |
| 9 | `category` | `varchar` | YES | NULL | Lowercase mirror of `doc_type` (REDUNDANT) |
| 10 | `tags` | `text[]` | YES | NULL | Searchable tags |
| 11 | `generated_by_agent` | `varchar` | YES | NULL | Identity that created the document |
| 12 | `is_core` | `boolean` | YES | `false` | Core documentation flag |
| 13 | `core_reason` | `text` | YES | NULL | Required when `is_core=true` |
| 14 | `is_archived` | `boolean` | YES | `false` | Soft-delete flag |
| 15 | `archived_at` | `timestamptz` | YES | NULL | Archive timestamp |
| 16 | `created_at` | `timestamptz` | YES | `NOW()` | Registration timestamp |
| 17 | `updated_at` | `timestamptz` | YES | `NOW()` | Last update |
| 18 | `last_verified_at` | `timestamptz` | YES | NULL | Last file-existence verification |

Source: `docs/DATA_GATEWAY_DOMAIN_ANALYSIS.md` section 2.1 and INSERT in `docs/DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md` lines 385–402.

---

## doc_type Enum (UPPERCASE — 16 values)

| Value | Description |
| --- | --- |
| `ADR` | Architecture Decision Records |
| `API` | API documentation |
| `ARCHITECTURE` | System architecture docs |
| `ARCHIVE` | Archived documents |
| `CLAUDE_CONFIG` | Claude configuration files (CLAUDE.md, etc.) |
| `COMPLETION_REPORT` | Session completion reports |
| `GUIDE` | How-to guides and tutorials |
| `MIGRATION` | Migration guides |
| `OTHER` | Miscellaneous documents |
| `README` | Project README files |
| `REFERENCE` | Reference documentation |
| `SESSION_NOTE` | Session work notes |
| `SOP` | Standard Operating Procedures |
| `SPEC` | Specifications |
| `TEST_DOC` | Test documentation |
| `TROUBLESHOOTING` | Troubleshooting guides |

---

## status Enum

| Value | Description | Consistency Rule |
| --- | --- | --- |
| `ACTIVE` | Currently valid | Default on creation |
| `ARCHIVED` | Not current | Must have `is_archived=true` AND `archived_at` set |

---

## Indexes

| Index | Type | Columns | Purpose |
| --- | --- | --- | --- |
| `documents_pkey` | btree (PK) | `doc_id` | PK |
| `idx_documents_doc_type` | btree | `doc_type` | Type queries |
| `idx_documents_status` | btree | `status` | Active/archived filter |
| `idx_documents_file_path` | btree | `file_path` | Dedup on registration |
| `idx_documents_is_core` | btree | `is_core` | Core doc queries |
| `idx_documents_tags` | GIN | `tags` | Array containment search |
| `idx_documents_project_id` | btree | `project_id` | Legacy direct project link (deprecated column) |

---

## Foreign Keys

| Column | References | On Delete |
| --- | --- | --- |
| `project_id` | `claude.projects.project_id` | SET NULL (deprecated column) |

### Child Relationships

| Child Table | FK Column | Description |
| --- | --- | --- |
| `claude.document_projects` | `doc_id` | Many-to-many project links (6,515 rows) |
| `claude.vault_embeddings` | `document_id` | Embedding chunks |

---

## Data Volume Context (from older audit analysis of ~1,734 sampled docs)

| Metric | Value |
| --- | --- |
| Total documents | 5,940 (as of Feb 2026 audit) |
| Archived (`is_archived=true`) | ~21.8% (~1,295) |
| Core (`is_core=true`) | ~6.5% (~386) |
| With direct `project_id` (deprecated) | 293 |
| `document_projects` rows | 6,515 |

**Core document breakdown by type (from sample)**:
- `CLAUDE_CONFIG`: 71% of all CLAUDE_CONFIG docs are core
- `SESSION_NOTE`: 15% are core
- `REFERENCE`: 9% are core
- `COMPLETION_REPORT`: 2% are core

---

## Known Schema Issues

| Issue | Impact | Recommendation |
| --- | --- | --- |
| `project_id` column deprecated but not removed | 293 rows still use it; creates confusion | Migrate to `document_projects`, then DROP COLUMN |
| `category` column redundant (= lowercase `doc_type`) | Doubles storage, no additional value | Deprecate and DROP |
| `status='ARCHIVED'` without `is_archived=true` | DB inconsistency (no enforcement constraint) | Add CHECK constraint or trigger |
| `is_archived=true` without `archived_at` | Missing timestamp | Add NOT NULL constraint when `is_archived=true` |

---

## METIS Assessment Notes

**Strength**: Large, well-populated registry with file hash tracking for change detection. The `is_core` flag enables important-document prioritization.

**Gap**: No semantic embedding on the `documents` table itself — only on `vault_embeddings` (chunks). Document-level semantic search requires aggregating chunk scores or adding a document-level embedding.

**Gap**: The deprecated `project_id` column and redundant `category` column add maintenance overhead. METIS should clean these before building on this table.

**Gap**: `document_projects` has 6,515 rows for 5,940 documents, suggesting most documents link to multiple projects. METIS needs to account for this many-to-many structure in project-scoped document queries.

---

## Source Code References

- `scripts/embed_vault_documents.py` — primary writer (creates/updates documents)
- `docs/DATA_GATEWAY_DOMAIN_ANALYSIS.md` — full schema documentation with valid values
- `docs/DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md` lines 385–402 — INSERT SQL
- `knowledge-vault/20-Domains/Table Code Reference Map - KEEP.md` line 29 — row count

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/schema-documents.md
