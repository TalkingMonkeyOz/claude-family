---
projects:
- claude-family
tags:
- cognitive-memory
- memory-architecture
- bpmn
- knowledge-management
synced: false
---

# Cognitive Memory - Process Details

Back-link: [[cognitive-memory-handoff]]

## 1. Capture Pipeline (`cognitive_memory_capture`)

**3 input paths**:
- **Explicit**: `remember()` call -> formulate content -> classify tier
- **Auto-detect**: Hook extracts from conversation -> significance gate (>= 0.5)
- **Session harvest**: Session end -> collect facts accessed 2+ times or typed decision/pattern

**Then**: Classify tier -> Dedup (similarity > 0.85) -> If dup: merge. If new: embed -> store -> link relations -> trigger contradiction check.

## 2. Token-Budgeted Retrieval (`cognitive_memory_retrieval`)

The core innovation. Entirely automated (no user tasks).

**Budget allocation by query type**:

| Type | Short | Mid | Long |
|------|-------|-----|------|
| Task-specific | 300 | 400 | 300 |
| Exploration | 100 | 300 | 600 |
| Default recall | 200 | 500 | 300 |

**Flow**: Parse query -> Allocate budget -> **Parallel search 3 tiers** -> Rank (composite score) -> Greedy fill with diversity guarantee (1+ per tier) -> Format with tier labels -> Update access stats.

**Tier search details**:
- SHORT: `session_facts` for current session (recency + access_count scoring)
- MID: `knowledge WHERE tier='mid' AND created > NOW()-30d` (similarity * 0.4 + recency * 0.3 + access * 0.2 + confidence * 0.1)
- LONG: `knowledge WHERE tier='long'` + recursive CTE graph walk 2 hops (similarity * 0.5 + graph_penalty * 0.2 + confidence * 0.2 + applied * 0.1)

## 3. Consolidation (`cognitive_memory_consolidation`)

**Triggers**: session_end (Phase 1 only), periodic (Phase 2+3), manual (all).

**Phase 1 (SHORT->MID)**: Promote if accessed >= 2 times, type is decision/pattern/reference, explicitly important, or matches active task. Generate Voyage AI embedding on promotion. Initial confidence 60-70.

**Phase 2 (MID->LONG)**: Promote if applied 3+ times, confidence >= 80, accessed in multiple sessions, not contradicted. Decay: not accessed 14+ days, confidence < 50, single-session only.

**Phase 3 (DECAY)**: `decay_knowledge_graph()` SQL function (weight * 0.95^days, floor 0.05). Archive: confidence < 30, not accessed 90+ days. Soft delete (preserved for audit).

## 4. Contradiction Resolution (`cognitive_memory_contradiction`)

**Trigger**: Semantic overlap > 0.75 on new memory store.

| Type | Action |
|------|--------|
| Extends | Keep both, link as 'extends' |
| Reinforces | Boost existing confidence, link as 'supports' |
| Contradicts | Score both -> newer wins / older wins / flag for review |
| Supersedes | Archive old, transfer relations to new |

**Contradiction scoring**: recency + confidence + authority (user > auto > inferred) + applied_success. If score delta > 0.3: clear winner. Otherwise: flag as feedback for human review.

## What Already Exists

| Component | Status |
|-----------|--------|
| `claude.knowledge` + pgvector embeddings | Built |
| `claude.session_facts` | Built |
| `claude.knowledge_relations` + graph search | Built (F129) |
| `decay_knowledge` tool | Built (F129) |
| `store_knowledge`, `recall_knowledge` tools | Built |
| `mark_knowledge_applied` feedback loop | Built |
| Voyage AI embedding pipeline | Built |

## What Needs Building

1. **Tier metadata**: Add `tier` column to `claude.knowledge` (short/mid/long)
2. **Capture hook**: Auto-detect memories from conversation (significance scoring)
3. **Token-budgeted retrieval**: Parallel search + rank + trim function
4. **Consolidation scheduler**: Phase 1 in session_end_hook, Phase 2+3 on SessionStart with cooldown
5. **Contradiction detector**: Post-store_knowledge overlap check
6. **Desktop MCP** (Option B): Standalone server with SQLite backend, 3 tools: `remember()`, `recall()`, `consolidate()`

## mcp-server-memory vs. Cognitive Memory

| Aspect | mcp-server-memory | Cognitive Memory |
|--------|-------------------|------------------|
| Storage | JSONL flat file | PostgreSQL/SQLite + embeddings |
| Context cost | Unbounded | Fixed ~1000 tokens |
| Lifecycle | None | 3-tier promotion + decay |
| Contradiction | None | 4-type classification |
| Tools | 9 granular | 3 user-facing |

## Open Questions

1. **Desktop storage**: SQLite (portable) or PostgreSQL (shared graph)?
2. **Desktop embeddings**: Local model or proxy through Voyage AI API?
3. **Cross-device sync**: Should Code and Desktop share memories?
4. **Migration**: How to import existing mcp-server-memory JSONL data?

---

**Version**: 1.0
**Created**: 2026-02-25
**Updated**: 2026-02-25
**Location**: knowledge-vault/10-Projects/claude-family/cognitive-memory-processes.md
