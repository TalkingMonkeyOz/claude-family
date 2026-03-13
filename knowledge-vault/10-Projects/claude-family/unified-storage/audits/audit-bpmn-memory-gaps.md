---
projects:
- claude-family
tags:
- audit
- bpmn
- memory
synced: false
---

# BPMN Memory Audit — Data Flow Trace and Gap Analysis

**Parent**: [audit-bpmn-memory-analysis.md](audit-bpmn-memory-analysis.md)

---

## Data Flow Trace

This traces a single knowledge item through the memory subsystem to show which processes handle it at each stage.

**Scenario**: Claude learns "The `build_tasks.status` valid values are `todo`, `in_progress`, `blocked`, `completed`, `cancelled` — never `pending`." (a gotcha)

**Step 1 — Capture** (`cognitive_memory_capture`)
Claude calls `remember(content=..., memory_type="gotcha")`. Source gateway → explicit path. Quality gate passes (>80 chars, no junk patterns). Semantic dedup check queries `claude.knowledge` for similarity > 0.75 in the `long` tier (gotcha maps to long). No duplicate found. Voyage AI embedding generated. Row inserted into `claude.knowledge` (tier='long', confidence=60). Relation linking checks for nearby entries at 0.5–0.75 similarity.
Code: `server.py:tool_remember()` lines 1792–1960.

**Step 2 — Consolidation** (`cognitive_memory_consolidation`)
Not needed for `long`-tier items on first capture — they are inserted directly as long-tier. The consolidation process handles MID→LONG promotion. At session end, `session_end_hook.py:consolidate_session_facts()` runs a lightweight scan of `claude.session_facts` only (not `claude.knowledge`), so this gotcha is unaffected.
Code: `session_end_hook.py` + `server.py:tool_consolidate_memories()`.

**Step 3 — Retrieval** (`cognitive_memory_retrieval`)
Claude calls `recall_memories(query="build task status values")`. Budget allocated: default profile (short=200, mid=400, long=300, workfiles=100). Parallel search: LONG branch queries `claude.knowledge WHERE tier='long'`, pgvector similarity + recursive CTE 2-hop graph walk. Result ranked, formatted as `[LONG-TERM]`, trimmed to budget. `update_access` increments `access_count`.
Code: `server.py:tool_recall_memories()` lines 1549–1790.

**Step 4 — Automatic injection** (`work_context_assembly` / `rag_pipeline`)
Every UserPromptSubmit triggers `rag_query_hook.py`. If WCC is active (requires `wcc_assembly.py` — currently absent), Source 2 queries knowledge mid/long. Without WCC, only vault RAG runs (searches vault document embeddings, not `claude.knowledge`). This item would only surface via explicit `recall_memories()` call or WCC, not via standard vault RAG.

**Step 5 — Compaction preservation** (`precompact`)
`claude.knowledge` rows persist in DB across compaction. The precompact hook preserves `claude.session_facts` only. Long-term memories do not need precompact injection — they are always queryable.

**Full flow**: `remember()` → `claude.knowledge(long)` → `recall_memories()` or WCC Source 2 → context injection

---

## Gap Analysis

Operations that exist in code or system design but lack dedicated BPMN model coverage.

| Gap | Severity | Evidence |
|---|---|---|
| **WCC `wcc_assembly` module absent** | Critical | `rag_query_hook.py:372–375`: import silently fails, WCC disabled |
| **session_end lightweight consolidation** | Medium | `session_end_hook.py:consolidate_session_facts()` promotes session_facts without embeddings — distinct from `consolidate_memories()` MCP tool, not modeled separately |
| **Dedup threshold mismatch** | Medium | `cognitive_memory_capture` model: 0.85. `server.py` code: 0.75. Affects merge frequency |
| **MID→LONG promotion criteria stale** | Medium | `cognitive_memory_consolidation` evaluate_mid comment: `times_applied >= 3`. Code: `access_count >= 5 AND age >= 7d`. MEMORY.md documents the fix but BPMN not updated |
| **AGE graph entirely unimplemented** | High (aspirational risk) | `knowledge_graph_lifecycle` has 18 tasks, no Apache AGE installed. Current graph = pgvector + CTE in `claude.knowledge_relations` |
| **Session startup state loading** | Low | `session_startup_hook_enhanced.py` loads active todos, features, messages at SessionStart. No BPMN covers the knowledge/state loading portion of startup |
| **Book references lifecycle** | Low | `store_book`, `store_book_reference`, `recall_book_reference` implemented in `server_v2.py`. Only appear as sub-paths in `knowledge_full_cycle`, no standalone model |
| **Quality gate default-flow inversion** | Low | `cognitive_memory_capture` quality_gw: `default="flow_quality_fail"` is correct (fails by default), but `flow_quality_pass` has condition `passes_quality == True`. The BPMN script sets `passes_quality = locals().get('passes_quality', True)` — the default is True, so the fail branch never fires unless code explicitly sets it False. Logic is sound but confusing |
| **Contradiction feedback surfacing** | Low | `cognitive_memory_contradiction` `flag_review` task creates feedback items. No BPMN connects this back to Claude's session context or the failure-capture system |

---

## Alignment Summary Table

| Operation | Model | Code | Status |
|---|---|---|---|
| remember() quality gate, tier routing | Yes | Yes | Aligned |
| remember() dedup threshold | 0.85 | 0.75 | **Mismatch** |
| remember() contradiction inline | Subprocess call | Inline code | Structural mismatch |
| recall_memories() 4-branch parallel | Yes | Yes | Aligned |
| recall_memories() budget profiles | Yes | Yes | Aligned |
| consolidate_memories() session_end phase | Yes | Yes | Aligned |
| consolidate_memories() MID→LONG criteria | times_applied>=3 | access_count>=5 | **Model stale** |
| session_end lightweight consolidation | Not modeled | Yes | Gap |
| working_memory store/recall/workfile | Yes | Yes | Aligned |
| workfile_management all 4 paths | Yes | Yes | Aligned |
| precompact all steps + budget cap | Yes | Yes | Aligned |
| context_preservation StatusLine sensor | Yes | Yes | Aligned |
| context_preservation tool blocking | Modeled | Unconfirmed | Uncertain |
| work_context_assembly WCC detect+assemble | Modeled | wcc_assembly.py absent | **Critical gap** |
| knowledge_graph_lifecycle AGE | Fully modeled | Not implemented | **Aspirational** |
| rag_pipeline vault embed + retrieve | Yes | Yes | Aligned |
| L1_knowledge_management | Stub | Superseded | Stale stub |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: knowledge-vault/10-Projects/claude-family/unified-storage/audits/audit-bpmn-memory-gaps.md
