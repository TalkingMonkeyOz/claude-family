---
projects:
- claude-family
- Project-Metis
tags:
- audit
- knowledge
- rag
- memory
synced: false
---

# Audit: Knowledge & RAG System (AI Memory Layer)

**Parent**: [[claude-family-systems-audit]]
**Raw data**: `docs/audit/knowledge_rag_audit.md` (20K chars)

---

## What It Is

Multi-layered system giving Claude persistent memory: vault documents (Obsidian markdown), Voyage AI embeddings (pgvector), 3-tier cognitive memory, and automatic context injection per prompt.

## Architecture

```
Knowledge Vault (290 md files)  →  Voyage AI embed  →  vault_embeddings (9,655 vectors)
                                                           ↓
User Prompt  →  rag_query_hook.py  →  classify prompt  →  query embeddings
                                                           ↓
                                  ←  inject context  ←  top 3 vault + top 3 knowledge
                                                           ↑
Cognitive Memory (717 entries)  →  Voyage AI embed  →  knowledge.embedding
  SHORT: session_facts (394)
  MID:   knowledge tier='mid'
  LONG:  knowledge tier='long'
```

## RAG Pipeline (rag_query_hook.py, 2,120 lines)

Fires every `UserPromptSubmit`. Sequence:
1. **Command detection** — Short imperatives (<30 chars) skip RAG
2. **Session facts** — Always injected (credentials, decisions, findings)
3. **Config keyword detection** — Warns about DB-is-source-of-truth if settings mentioned
4. **Skill suggestions** — Top 2 skills by embedding similarity (threshold 0.50)
5. **RAG gate** — Questions and long prompts get full RAG; action verbs skip
6. **Knowledge graph query** — pgvector seeds + 2-hop relation walk (min sim 0.35)
7. **Vault RAG query** — Top 3 unique vault docs (min sim 0.45)
8. **Schema context** — If schema keywords detected (min sim 0.40)
9. **Context health** — Graduated warnings at 30%/20%/10% remaining
10. **Failure surfacing** — Pending auto-filed bugs from last 48h
11. **Assembly** — All context blocks combined into `additionalContext`

**Token injection**: 2,000-6,000 tokens per prompt depending on how many blocks fire.

## Cognitive Memory (F130)

3-tier system replacing unbounded knowledge dumps:

| Tier | Storage | Example | Lifecycle |
|------|---------|---------|-----------|
| SHORT | session_facts table | API keys, endpoints, decisions | Session-scoped; promoted on session end |
| MID | knowledge (tier='mid') | Learned facts, decisions | Default for `remember()`; promoted after repeated use |
| LONG | knowledge (tier='long') | Patterns, procedures, gotchas | Proven knowledge; auto-promoted or explicit |
| ARCHIVED | knowledge (tier='archived') | Stale/low-confidence | Decayed after 90+ days without access |

**Tools**: `remember()` (auto-routes, dedup/merge, auto-link), `recall_memories()` (3-tier retrieval, budget-capped ~1000 tokens), `consolidate_memories()` (promote/decay/archive lifecycle).

## Vault Health

| Folder | Files | Notes |
|--------|-------|-------|
| 00-Inbox | 0 | Empty (good — nothing uncategorized) |
| 10-Projects | ~105 | Heavy: Metis (90+), claude-family (20+) |
| 20-Domains | ~85 | 75 are awesome-copilot-reference; 12 native |
| 30-Patterns | ~30 | Well-organized |
| 40-Procedures | ~27 | Core SOPs |
| Claude Family | ~33 | Core system docs |

**43 documents reference deprecated concepts**: orchestrator MCP, `claude_family.*` schema, retired MCPs. Key stale docs:
- Claude Tools Reference (lists orchestrator as active)
- Family Rules (lists orchestrator in MCP table)
- Session User Story docs (use `mcp__orchestrator__*` calls)
- Orchestrator MCP doc (extensively documents retired system, no retirement note)

## Issues

1. **No aggregate token cap** — All 7 context blocks can fire simultaneously. No ceiling.
2. **`needs_rag()` too aggressive on action verbs** — "Implement X but first explain" skips RAG.
3. **Knowledge graph uses min_similarity=0.35** vs vault's 0.45 — graph path more permissive.
4. **Consolidation ordering bug** — Current-session facts never promoted (see hooks audit).
5. **Legacy knowledge entries** (pre-F130) have no `tier` field, ignored by consolidation.
6. **No RAG quality metrics** — Can't measure hit/miss rates or usefulness.
7. **43 stale vault docs** — Will pollute RAG results with wrong information.

## Effectiveness

The RAG system is **the most valuable subsystem**. It provides continuity across sessions, making Claude feel like it remembers previous work. The cognitive memory 3-tier design is genuinely innovative — most AI memory systems are flat stores.

**For Metis**: Keep the RAG + cognitive memory architecture. Enterprise needs: dedicated vector DB at scale, retrieval evaluation metrics, hard token budget, user feedback loop, vault doc freshness scoring to deprioritize stale content.

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-knowledge.md
