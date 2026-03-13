---
projects:
- claude-family
tags:
- audit
- bpmn
- memory
synced: false
---

# BPMN Memory Audit — Overlap Analysis

**Parent**: [audit-bpmn-memory-analysis.md](audit-bpmn-memory-analysis.md)

Five overlaps were identified where two or more BPMN models cover the same operations.

---

## Overlap 1: `rag_pipeline` vs `knowledge_full_cycle` (retrieval path)

Both models cover: scan vault for changes, generate Voyage AI embeddings, store in pgvector, classify prompt, query embeddings, inject context. `knowledge_full_cycle` models the vault embedding path (Path 2) and the RAG auto-retrieval sub-path (Path 5a) using the same sequence of tasks as `rag_pipeline`'s two branches.

The code implementation (`scripts/rag_query_hook.py`, `scripts/embed_vault_documents.py`) maps equally to both models. Any change to vault RAG logic requires updating two BPMN files.

**Type**: Intentional overlap (different abstraction levels), but fragile.
**Recommendation**: Either retire `rag_pipeline` or have `knowledge_full_cycle` reference it as a subprocess rather than inlining the tasks.

---

## Overlap 2: `cognitive_memory_capture` vs `working_memory` (store path)

`working_memory` Path 1 models `store_session_fact`. `cognitive_memory_capture` SHORT path also delegates to `store_session_fact` when `memory_type` is credential/config/endpoint. Calling `remember(memory_type="credential")` traverses the `cognitive_memory_capture` source gateway, exits via SHORT path, and calls the same operation `working_memory` Path 1 models.

**Type**: Delegation overlap — `cognitive_memory_capture` SHORT path is a routing pointer, not a duplicate lifecycle.
**Recommendation**: Add a cross-reference note to `working_memory` acknowledging the SHORT-path delegation from `cognitive_memory_capture`. No structural change required.

---

## Overlap 3: `working_memory` (compaction path) vs `precompact` — True Duplication

`working_memory` Path 3 models: PreCompact fires → query facts → build system message → post-compaction recovery. `precompact` models the same sequence in greater detail: get project name, connect DB, query active work items, query session facts, read session notes, query pinned workfiles, apply budget cap, build refresh message.

`precompact` is the authoritative, current model. `working_memory` compaction path is a condensed duplicate that adds no information.

**Type**: True duplication.
**Recommendation**: Remove Path 3 from `working_memory`. Replace with a note: "Compaction handling is fully modeled in `precompact`."

---

## Overlap 4: `cognitive_memory_contradiction` vs `cognitive_memory_capture` (inline vs subprocess)

`cognitive_memory_capture` task `link_relations` includes the comment: "Also trigger contradiction check subprocess." This implies `cognitive_memory_contradiction` is a called subprocess. In code (`server.py:tool_remember()`), the contradiction check is inline — a second pgvector search at lines ~1937–1960 that sets `contradiction_flag`.

The BPMN implies an invocation boundary; the code has none. This is a structural mismatch: the model suggests a process call, the implementation is a code block.

**Type**: Structural mismatch — subprocess boundary implied in model, not present in code.
**Recommendation**: Update `cognitive_memory_capture` to label the contradiction step as "inline logic" rather than a subprocess call, or refactor code to call a discrete function matching the BPMN boundary.

---

## Overlap 5: `knowledge_graph_lifecycle` vs `cognitive_memory_consolidation` (decay)

`cognitive_memory_consolidation` Phase 3 calls `decay_knowledge_graph()` scoped to project_id (BPMN script: "Call decay_knowledge_graph() scoped to project_id"). `knowledge_graph_lifecycle` Sub-process 3 models the same decay operation using Apache AGE Cypher queries.

In code, `consolidate_memories` Phase 3 calls a decay function on `claude.knowledge_relations` (not AGE). The `knowledge_graph_lifecycle` decay path is entirely aspirational — AGE is not installed.

**Type**: One process models the implemented behaviour, the other models an aspirational future state.
**Recommendation**: `cognitive_memory_consolidation` is authoritative for decay. `knowledge_graph_lifecycle` should be marked aspirational status. Do not treat them as equivalent.

---

## Overlap Summary Table

| Overlap | Processes | Type | Priority |
|---|---|---|---|
| Vault RAG path duplicated | `rag_pipeline` + `knowledge_full_cycle` | Intentional (different levels) | Medium |
| Store-fact delegation | `cognitive_memory_capture` + `working_memory` | Intentional delegation | Low |
| Compaction path duplicated | `working_memory` + `precompact` | True duplication | High |
| Contradiction as subprocess vs inline | `cognitive_memory_capture` + `cognitive_memory_contradiction` | Structural mismatch | Medium |
| Decay — implemented vs aspirational | `cognitive_memory_consolidation` + `knowledge_graph_lifecycle` | Future state confusion | High |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\audit-bpmn-memory-overlaps.md
