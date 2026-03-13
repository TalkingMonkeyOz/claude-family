---
projects:
- claude-family
tags:
- audit
- bpmn
- memory
synced: false
---

# BPMN Memory Audit — Recommendations and Key Findings

**Parent**: [audit-bpmn-memory-analysis.md](audit-bpmn-memory-analysis.md)

---

## Simplification Recommendations

### R1 — Retire `L1_knowledge_management` (effort: low)
Contains 6 tasks at pre-F130 level, fully superseded by `knowledge_full_cycle`. Its only remaining value is as an L0 architecture entry point. Replace content with a call-reference comment pointing to `knowledge_full_cycle` and add a deprecation notice.

### R2 — Resolve `rag_pipeline` vs `knowledge_full_cycle` duplication (effort: low)
Both model vault embed and RAG retrieval. Two options: (a) retire `rag_pipeline` and add a cross-reference comment in `knowledge_full_cycle`, or (b) keep `rag_pipeline` as the authoritative model and remove the duplicated sub-paths from `knowledge_full_cycle`, replacing them with a subprocess reference. Option (b) is cleaner.

### R3 — Remove compaction path from `working_memory` (effort: low)
`working_memory` Path 3 (action == "compaction") duplicates `precompact` at lower fidelity. Remove the path and replace with a note: "Compaction handling is modeled in `precompact`." Retains all other paths unchanged.

### R4 — Fix stale MID→LONG promotion criteria in consolidation model (effort: trivial)
`cognitive_memory_consolidation` `evaluate_mid` script comment still reads `times_applied >= 3`. Correct value is `access_count >= 5 AND age >= 7d`. Update the BPMN comment only — no structural change.

### R5 — Fix dedup threshold in capture model (effort: trivial)
`cognitive_memory_capture` `dedup_check` task script says "similarity > 0.85". Code uses 0.75. Update both the `dedup_check` and `link_relations` task comments to reflect 0.75.

### R6 — Implement `wcc_assembly.py` or mark WCC model aspirational (effort: high for impl, trivial for doc)
`work_context_assembly` BPMN is fully specified but `wcc_assembly` module is absent. WCC is currently disabled at runtime. Either implement the module, or add `[STATUS: NOT IMPLEMENTED — wcc_assembly.py absent]` to the BPMN header and to the process name.

### R7 — Mark `knowledge_graph_lifecycle` aspirational (effort: trivial)
Add to BPMN header: "STATUS: ASPIRATIONAL — requires Apache AGE extension. Not installed. Current graph implementation uses pgvector + CTE in claude.knowledge_relations. See cognitive_memory_retrieval search_long path for implemented behaviour." Prevents the model from being mistaken for active documentation.

---

## Key Findings

1. **F130 cognitive memory tools are well-modeled and well-implemented.** `cognitive_memory_capture`, `cognitive_memory_retrieval`, and `cognitive_memory_consolidation` accurately reflect the three MCP tools. Minor threshold and criteria discrepancies exist (R4, R5) but do not affect runtime correctness.

2. **Workfile system has the highest model-to-code fidelity.** `workfile_management` and `precompact` are both at 95%+. The filing-cabinet metaphor in the model maps directly to the UPSERT implementation.

3. **WCC is modeled but not executing.** The `wcc_assembly` module referenced by `rag_query_hook.py` does not exist on disk. The `work_context_assembly` BPMN is the largest single gap between model and running code in the memory subsystem. Activity-based context assembly is silently disabled every session.

4. **Knowledge graph (AGE) is entirely aspirational.** The `knowledge_graph_lifecycle` model describes a sophisticated Apache AGE graph layer. None of this is implemented. The actual graph capability — `claude.knowledge_relations` with pgvector + recursive CTE — is correctly modeled in `cognitive_memory_retrieval` (search_long path).

5. **Two threshold values disagree between model and code.** Dedup similarity threshold: model=0.85, code=0.75. A lower threshold means more items are merged rather than created, affecting knowledge density over time.

6. **MID→LONG promotion criteria are stale in the BPMN.** The `evaluate_mid` comment references the pre-fix `times_applied >= 3` rule. The fix (using `access_count >= 5`) is documented in MEMORY.md but the BPMN was not updated.

7. **Session-end lightweight consolidation is not fully modeled.** `session_end_hook.py:consolidate_session_facts()` promotes session facts to mid-tier knowledge WITHOUT Voyage AI embeddings as a lightweight pass. This is a distinct operation from the full `consolidate_memories()` MCP call. Only briefly referenced in `cognitive_memory_consolidation` commentary.

8. **`L1_knowledge_management` is an obsolete stub.** It represents a pre-F130 knowledge model and has been fully superseded by `knowledge_full_cycle`. Its continued presence as an active model creates confusion.

9. **`working_memory` is structurally sound except for one redundant path.** All five paths are correctly aligned to code; Path 3 (compaction) duplicates `precompact`.

10. **No BPMN covers the full contradiction-feedback loop.** `cognitive_memory_contradiction` `flag_review` task creates a feedback item, but no model traces how that item surfaces back to Claude in a future session or how resolution is confirmed.

---

## Priority Order for Action

| Priority | Recommendation | Effort |
|---|---|---|
| 1 | R6 — WCC: implement or mark aspirational | High / Trivial |
| 2 | R7 — AGE graph: mark aspirational | Trivial |
| 3 | R3 — Remove compaction path from working_memory | Low |
| 4 | R4 — Fix consolidation MID→LONG criteria | Trivial |
| 5 | R5 — Fix dedup threshold | Trivial |
| 6 | R2 — Resolve rag_pipeline overlap | Low |
| 7 | R1 — Retire L1_knowledge_management | Low |

---

**Version**: 1.0
**Created**: 2026-03-12
**Updated**: 2026-03-12
**Location**: C:\Projects\claude-family\docs\audit-bpmn-memory-recommendations.md
