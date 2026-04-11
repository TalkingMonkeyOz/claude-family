# BT585: BPMN Vault Reference Audit

**Task**: F195 BT585 — Identify vault references in 6 BPMN files needing DB-first updates
**Date**: 2026-04-11
**Scope**: READ-ONLY research. No BPMN files modified.

---

## Summary

| File | Vault References | Type | Action Needed |
|------|-----------------|------|---------------|
| rag_hook_execution.bpmn | 2 | READ | Update priority order comment |
| knowledge_full_cycle.bpmn | 3 | READ + WRITE path | Rename task; add clarifying comments |
| rag_pipeline.bpmn | 2 | READ + WRITE path | Add clarifying comment |
| vault_librarian.bpmn | Many (by design) | READ | Keep as-is (correct scope) |
| L1_knowledge_management.bpmn | 0 | — | No changes needed |
| knowledge_consolidation.bpmn | 0 | — | No changes needed |

---

## File-by-File Findings

### 1. rag_hook_execution.bpmn

**Element: `task_vault_rag` (line 149)**
- Name: "[HOOK] Query Vault RAG"
- Type: READ — queries `vault_embeddings` at prompt time
- Assessment: Legitimate READ source in parallel fan-out. Vault RAG is a valid supplementary retrieval path.
- Concern: It is one of 8 equal parallel branches, visually equal to `task_entity_catalog` and `task_knowledge_graph`.

**Element: `task_apply_budget` (line 295, priority list)**
- Script comment: `priority=["protocol", "session_facts", "todos", "rag", "entity_catalog", "vault", "workfiles", "schema"]`
- Type: READ — determines injection order
- Concern: Vault is ranked ABOVE workfiles (position 6 vs 7). Under DB-first, workfiles (DB) should outrank vault (file system). Vault should drop to last DB-sourced position.
- Recommended change: Reorder to `["protocol", "session_facts", "todos", "rag", "entity_catalog", "workfiles", "vault", "schema"]`

---

### 2. knowledge_full_cycle.bpmn

**Path 2 header comment (line 127): "PATH 2: VAULT EMBEDDING (batch pipeline)"**
- Type: WRITE — `scan_vault` → `chunk_and_embed` → `upsert_vectors`
- Assessment: This path correctly models the batch embedding pipeline for John's vault docs. The vault is the SOURCE for human documentation; embeddings flow INTO the DB.
- Concern: The path is presented as a peer to "Direct Capture" (Claude's knowledge). A reader could infer vault embedding is an equally valid way for Claude to store knowledge.
- Recommended change: Add comment clarifying this path is for John's reference docs only; Claude's knowledge goes via Path 1 (direct capture → `remember()`).

**Element: `rag_query` (line 294)**
- Name: "[HOOK] Query Vault Embeddings (cosine similarity)"
- Type: READ — RAG retrieval path
- Assessment: Correctly models vault as a READ source. No issue with the mechanism. 
- Concern: In the retrieval section (Path 5), vault RAG is the DEFAULT path (`flow_rag_auto`). Direct search against `claude.knowledge` is a non-default branch. This inverts DB-first priority.
- Recommended change: Either make direct search the default, or add a comment that DB knowledge takes priority and vault is a fallback.

**Header comment (line 25): "1. RAG (vault): UserPromptSubmit hook → classify → Voyage AI query → inject context"**
- Type: READ reference in documentation comment
- Concern: Listed first among retrieval paths, giving vault top billing.
- Recommended change: Reorder list to put direct knowledge search first.

---

### 3. rag_pipeline.bpmn

**Element: `scan_vault` (line 40)**
- Name: "Scan Vault for Changes"
- Type: WRITE path — part of the embedding pipeline that writes to `vault_embeddings`
- Assessment: Correct — models the batch job that keeps vault embeddings fresh. Not directing Claude to write knowledge to vault.
- Concern: None. This is the infrastructure pipeline for John's human docs.

**Element: `query_voyage_embeddings` (line 96)**
- Name: "Query Voyage AI Embeddings" (script sets `vault_docs_retrieved = True`)
- Type: READ — retrieves vault docs for prompt injection
- Assessment: The task name is neutral, but the script variable name confirms vault-only retrieval.
- Concern: Minor. The process models vault RAG as THE retrieval mechanism (no parallel DB knowledge search). This is a simplified view that predates the full parallel fan-out in `rag_hook_execution.bpmn`.
- Recommended change: Add comment that this is a simplified model; see `rag_hook_execution.bpmn` for full implementation including DB knowledge graph.

---

### 4. vault_librarian.bpmn

All vault references are by design and correct. This process exists specifically to audit the vault filesystem for:
- Uncataloged files (vault → entity catalog sync)
- Orphaned catalog entries
- Missing frontmatter
- Missing embeddings

No DB-first violations. The process correctly treats vault as John's documentation layer and helps maintain its health. No changes needed.

---

### 5. L1_knowledge_management.bpmn

Zero vault references. This is a high-level L1 model covering capture → embed → store → retrieve → apply. Fully DB-aligned. No changes needed.

---

### 6. knowledge_consolidation.bpmn

Zero vault references. This process consolidates memories into `domain_concept` entities in the entity catalog. Entirely DB-first. No changes needed.

---

## Priority Changes

| Priority | File | Element ID | Change |
|----------|------|-----------|--------|
| High | rag_hook_execution.bpmn | `task_apply_budget` | Reorder priority: move `vault` after `workfiles` |
| Medium | knowledge_full_cycle.bpmn | Path 2 header + `rag_query` | Add comments; make direct search default retrieval |
| Low | knowledge_full_cycle.bpmn | Header comment line 25 | Reorder retrieval path list |
| Low | rag_pipeline.bpmn | `query_voyage_embeddings` | Add comment pointing to fuller model |

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/bt585-vault-audit.md
