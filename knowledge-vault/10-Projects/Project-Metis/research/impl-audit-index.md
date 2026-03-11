---
projects:
- claude-family
- project-metis
tags:
- research
- implementation-audit
- memory
- retrieval
synced: false
---

# Implementation Audit: Memory and Retrieval Systems

Research findings on what the prototype actually does versus what the docs say.
All findings reference specific files and line numbers.

## Document Index

| File | Covers |
|------|--------|
| [impl-audit-cognitive-memory.md](impl-audit-cognitive-memory.md) | remember(), recall_memories(), consolidate_memories() |
| [impl-audit-wcc.md](impl-audit-wcc.md) | WCC assembly, activity detection, caching |
| [impl-audit-rag-hook.md](impl-audit-rag-hook.md) | RAG hook pipeline, budget, session facts |
| [impl-audit-persistence.md](impl-audit-persistence.md) | Precompact, task sync, session startup |
| [impl-audit-cross-cutting.md](impl-audit-cross-cutting.md) | Systemic findings, what the prototype taught us |

## Quick Summary of Key Gaps

| Gap | Severity | Location |
|-----|----------|----------|
| WCC claims trigram matching, uses word overlap only | Medium | wcc_assembly.py:43 vs 189-256 |
| WCC cache invalidation never called | High | wcc_assembly.py:83-90 |
| Short-tier recall has no relevance signal | Medium | server.py:1583-1628 |
| Duplicate consolidation logic in startup hook | Low | session_startup_hook:283 vs server.py:2098 |
| Edge decay uses created_at not last_accessed_at | Medium | server.py:2116-2125 |
| Feedback loop collects data, never reads it | High | rag_query_hook.py:822-873 |
| Voyage AI client instantiated per call | Low | rag_query_hook.py:413 |
| Task map lives in %TEMP%, lost on reboot | High | task_sync_hook.py:91 |
| Cross-tier dedup does not happen | Medium | server.py:1867-1878 |
| Skill/schema context fire even when WCC active | Low | rag_query_hook.py:2090-2132 |

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/research/impl-audit-index.md
