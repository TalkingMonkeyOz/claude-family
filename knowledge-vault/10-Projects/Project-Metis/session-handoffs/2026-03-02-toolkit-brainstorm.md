---
tags:
  - project/Project-Metis
  - type/session-handoff
  - phase/brainstorm-2
created: 2026-03-02
session: toolkit-expansion-and-brainstorm
status: in-progress
---

# Session Handoff: Toolkit & Infrastructure Brainstorm

## Session Summary

Two-part session. First part (with Claude Code) completed Design Coherence check — all 5 phases done, 76 design concepts extracted, 23 relations mapped, 7 findings resolved (FB165-FB171), commit 6668082.

Second part (Claude Desktop) expanded into toolkit brainstorming. Started with design methodology expansion, then moved into "what tools do we need to build, run, and maintain METIS at scale." Session ended mid-brainstorm — Category 1 (Design & Modelling Tools) partially presented, Categories 2-4 not yet discussed with John.

## Status: BRAINSTORM MODE

John clarified this is second-pass brainstorming. Goal is capture ideas and features at high level, THEN flesh out to lower level, THEN review. Not designing yet.

## DECISIONS MADE THIS SESSION

### 1. User-Centric Design Techniques
Five techniques adopted to bridge personas → BPMN gap:
- **User Journey Mapping** — PRIORITY. Per-persona task-focused maps that feed into BPMN
- **Task Analysis** — already doing implicitly in brainstorms
- **C4 Model** — PRIORITY. Four-level architecture (Context/Container/Component/Code)
- **Event Storming** — deferred to detailed design phase
- **Wireflows** — lightweight wireframes with flow arrows

John rejected outdated UCD fluff (feedback buttons, emotional journey mapping). Focus on design techniques that feed into process flows.

### 2. Full Design Notation Stack
Seven complementary views now defined:
| Perspective | Notation | Status |
|---|---|---|
| Process flow | BPMN | ✅ Existing |
| Decision logic | DMN | ✅ Existing |
| Domain boundaries | DDD | ✅ Existing |
| System structure | C4 Model | NEW |
| User perspective | Journey Maps + Wireflows | NEW |
| Lifecycle history | Event Sourcing | ✅ Existing |
| Dependency completeness | Ontology/Knowledge Graph | ✅ Existing |
| Efficiency/waste | Value Stream Mapping | PARKED |

### 3. Value Stream Mapping
Added to toolkit but PARKED. Lean methodology. Revisit after core techniques established.

### 4. MCP Server Building
Confirmed: we already build custom MCP servers (project-tools is one). Not difficult — Python FastMCP or Node SDK, define tools as functions, expose over stdio or HTTP. A code indexer or schema-BPMN validator MCP is within our capability.

## IDEAS CAPTURED (not yet validated with John)

### Large Codebase Handling (CRITICAL)
Real-world trigger: nimbus developer struggling with 10,000-line file in Cursor.

Two dimensions:
1. **Break down existing large codebases for AI consumption** — code chunking, AST parsing, dependency graphs, semantic indexing
2. **Prevent/enforce modularity going forward** — code quality enforcement via Quality & Compliance

This is BOTH a METIS capability (for clients) AND tooling needed while building METIS.

### Research: Code Comprehension Tooling
Core technique: AST parsing + semantic embeddings + dependency graphs.
Best practice: AST for indexing, Tree-sitter for retrieval (both together).

Available MCP-ready tools:
- **Probe** — zero-indexing, AST+ripgrep, works with Claude Code natively
- **Code Context (Zilliz)** — AST chunking + VoyageAI/OpenAI embeddings + Milvus vector DB
- **Context+** — Tree-sitter AST + spectral clustering + Obsidian-style linking
- **Sourcegraph/Cody** — enterprise, symbol graph, semantic search

We already have Voyage AI + pgvector. Suggested approach: use Probe now, build own as METIS feature later.

### Research: Schema-to-BPMN Validation
No off-the-shelf tool does this. But the approach exists:
- BPMN data objects should map to DB entities
- bpmnlint allows custom validation rules
- DF-BPMN (academic) adds data flow annotations to standard BPMN
- Camunda Modeler has simulation/validation

Claude Family message confirmed they already built schema validation tools (schema_docs.py, embed_schema.py, validate_process_schema) — proven on 100 tables. Need to sync to vault.

### Builder's Toolkit Categories (brainstorm framework)

**Category 1: Design & Modelling Tools** (partially discussed)
- C4 architecture diagrams (Mermaid-based)
- User Journey Maps (per-persona templates)
- DB schema diagramming (generate ERDs from DDL)
- Schema-to-BPMN validation (custom skill)
- BPMN quality validation (bpmnlint)
- Design coherence checking (existing skill)
- Build readiness checking (new skill needed)

**Category 2: Code Comprehension & Development Tools** (not yet discussed)
- Code indexer (AST + embeddings into Knowledge Engine)
- Codebase dependency mapping
- Modularity enforcement
- Test generation from config/schema

**Category 3: Reusable Skills** (not yet discussed)
- Sequential thinking ✅ working
- Design coherence ✅ working
- Schema-BPMN validator (to build)
- Code indexer (to build)
- Build readiness checker (to build)
- Journey map template (to build)

**Category 4: Scale & Operations** (not yet discussed)
- Agent orchestration at scale (many concurrent agents)
- Monitoring & observability (agent health, knowledge freshness)
- Knowledge consistency (concurrent read/write conflict resolution)
- Load management and queue prioritisation
- Failure recovery

## ACTIONS PENDING

1. **Message sent to Claude Family** (msg 67d8af18): requesting vault sync of DB analysis tool and documentation process improvements. Awaiting response.
2. **Toolkit brainstorm incomplete**: Categories 2-4 not yet discussed with John. Resume next session.
3. **Claude Family confirmed** schema validation tools exist (schema_docs.py, embed_schema.py, validate_process_schema) — need vault sync.

## NEXT SESSION PLAN

Continue toolkit brainstorm:
- Walk through Categories 2, 3, 4 with John
- Capture his ideas on scale/operations requirements
- Identify any missing categories
- Then: lower-level fleshing out of priority items
- Then: review pass

## KEY FILES
- Feature catalogue: `feature-catalogue.md` (10 user-facing features)
- Design lifecycle: `design-lifecycle.md` (11-phase master checklist)
- Design coherence skill: `skills/design-coherence/SKILL.md`
- This handoff: `session-handoffs/2026-03-02-toolkit-brainstorm.md`

---
*Session: 2026-03-02 | Status: Brainstorm in progress*
