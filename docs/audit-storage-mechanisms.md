---
projects:
- claude-family
tags:
- audit
- storage
synced: false
---

# Storage Mechanisms Audit — Index

**Audit date**: 2026-03-12
**Analyst**: Claude (analyst-sonnet)
**Basis**: Schema research (2026-02-28 snapshot) + session notes (2026-03-12 updated counts)

Full detail in knowledge-vault:

| Section | File | Lines |
|---------|------|-------|
| Mechanisms 1-5: Facts, Knowledge, Workfiles | [storage-audit-part1](../knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-part1.md) | 280 |
| Mechanisms 6-14: Vault, Todos, WCC, Notes, Misc | [storage-audit-part2](../knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-part2.md) | 250 |
| Overlap, Dead Weight, Volume Analysis | [storage-audit-part3](../knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-part3.md) | 200 |
| Key Findings (12 numbered) | [storage-audit-findings](../knowledge-vault/10-Projects/Project-Metis/audits/storage-audit-findings.md) | 150 |

## Summary Table

| Mechanism | Rows | Status | Primary Overlap |
|-----------|------|--------|-----------------|
| `session_facts` (SHORT) | ~676 | Active, healthy | knowledge MID, session notes |
| `knowledge` MID | ~930 | Active, polluted (96% stuck) | vault_embeddings, session_facts |
| `knowledge` LONG | ~127 | Promotion broken | vault 30-Patterns/, MEMORY.md |
| `knowledge_relations` | ~67 | Sparse, marginal value | — |
| `project_workfiles` | ~3 | Built, not adopted | session notes, session_facts |
| `vault_embeddings` | ~12,345 | Healthy, growing | knowledge, WCC vault_rag source |
| `todos` | 2,711 | Active, high-churn | `build_tasks` |
| `activities` (WCC) | ~0 explicit | Framework only | workfiles |
| `messages` | 187 | Active, low-volume | — |
| `audit_log` | 254 | Active | — |
| `sessions` | 906 | Active | — |
| `mcp_usage` | 6,965 | Dead (all synthetic) | — |
| `enforcement_log` | 1,333 | Dead (zombie writes) | — |
| Session notes files | 7 files | Active, inconsistent | workfiles, session_facts |
| `MEMORY.md` | 1 file | Active (1 project only) | LONG knowledge, vault docs |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\audit-storage-mechanisms.md
