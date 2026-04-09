---
projects:
- claude-family
tags:
- knowledge-management
- rag
- architecture
- audit
---

# Knowledge System Audit — April 2026

## Core Finding

We built 5 excellent storage systems but only wired 2 of them into automatic retrieval. ~60% of our knowledge is "dark" — it exists but is only found if Claude manually calls the right tool.

## Current System Size

| Store | Items | DB Size | Auto-Searched? |
|-------|-------|---------|----------------|
| Knowledge memories | 2,171 (1,725 mid, 443 long) | 30 MB | Yes |
| Vault (890 files, 36K lines) | 14,869 chunks | 207 MB | Yes |
| Entity catalog | 526 entries | 15 MB | **NO** |
| Workfiles | 154 active | — | **NO** |
| Session facts | ~347/month | — | Current session only |

Total: ~264MB across filesystem + PostgreSQL. 99.9% embedding coverage.

## The UserSDK Case Study (2026-04-09)

UserSDK knowledge existed abundantly (20 knowledge entries + 13 entities + 1 workfile), all tagged to nimbus-mui. But a nimbus-mui session couldn't find it because:

1. Entity catalog (13 entries) — NEVER auto-searched by RAG hook
2. Workfiles (1 entry) — NEVER auto-searched by RAG hook
3. nimbus-mui missing from NIMBUS_PROJECTS list in rag_queries.py
4. Vault has ZERO UserSDK content
5. 3,000 token budget cap drops lower-priority results
6. WCC pre-emption replaces all RAG queries when active

## Three Structural Problems

### Problem 1: Fragmented Retrieval
RAG hook (`rag_query_hook.py`) searches knowledge table + vault chunks. Entity catalog, workfiles, and nimbus_context are invisible to automatic retrieval. This is like having a library where 3 of 5 rooms are locked.

### Problem 2: No Consolidation Pipeline
Knowledge enters from many directions but nothing synthesizes fragments into reference articles. 34 UserSDK fragments across 3 stores — no "UserSDK Reference Guide." Knowledge Curator (F188) was built but failed on first run due to a SQL type cast bug (`text[] @> uuid[]`).

### Problem 3: Flat Chunking
890 files chunked into 14,869 flat pieces. Retrieval returns decontextualized fragments. Industry best practice: hierarchical chunking (parent-child) with 87% accuracy vs 13% for fixed-size.

## What's Working Well

- 5-store architecture design is sound for different use cases
- `remember()` with 75% dedup + contradiction detection is ahead of industry
- 3-tier lifecycle (short/mid/long) with decay aligns with best practices
- pgvector + Voyage AI confirmed as right tech stack at our scale
- Storage routing rules are clear and well-documented

## Scheduled Jobs Status

### Windows Task Scheduler (4 tasks)

| Task | Schedule | Status | Notes |
|------|----------|--------|-------|
| Job Runner | Hourly | Working | Triggers all DB-registered cron jobs |
| PostgreSQL Backup | Weekly Sun 1AM | Last failed (-196608) | Needs investigation |
| Documentation Audit | Daily 8AM | Exit code 1 | Needs investigation |
| Startup | At logon | Disabled | Legacy |

### DB-Registered Jobs (24 total, 14 active)

Knowledge-related active jobs: knowledge-curator (FAILED), knowledge-decay, memory-consolidation, vault-embeddings-update, vault-librarian, document-scanner, system-maintenance.

Knowledge Curator failure: `psycopg.errors.UndefinedFunction: operator does not exist: text[] @> uuid[]` — type mismatch in `_get_next_due_project()`.

---
**Version**: 1.0
**Created**: 2026-04-09
**Updated**: 2026-04-09
**Location**: knowledge-vault/30-Patterns/knowledge-system-audit-2026-04-09.md
