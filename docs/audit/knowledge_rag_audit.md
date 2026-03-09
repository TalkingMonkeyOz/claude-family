I now have comprehensive information to produce the full report. Let me compile it.

---

# Claude Family RAG and Knowledge System - Technical Assessment

## 1. RAG Pipeline Assessment

### Architecture Overview

The RAG pipeline is implemented in `/C:/Projects/claude-family/scripts/rag_query_hook.py` (2,120 lines), firing on every `UserPromptSubmit` event. It is the most complex hook in the system.

### End-to-End Flow

Every user prompt passes through this sequence:

1. **Command detection** - Prompts under 30 characters matching imperative patterns (commit, yes, push) skip all injection except the core protocol.
2. **Task map session check** - Validates that the claude_task_map temp file belongs to the current session; clears stale maps.
3. **Implicit feedback processing** - Scans prompt for negative phrases ("that didn't work") or query rephrasing to log feedback against prior RAG results.
4. **Session facts injection** - Always runs; plain SQL, no embedding. Pulls credential/endpoint/decision/config facts for the current project and session.
5. **Config keyword detection** - If prompt mentions settings.local.json or hook editing, injects a database-is-source-of-truth warning.
6. **Skill suggestions** - Queries `claude.skill_content` by embedding similarity (threshold 0.50, top 2 results).
7. **Design map** - Attempts a file read of `10-Projects/{project}/design-map.md` if present.
8. **RAG gate (`needs_rag()`)** - Decides whether to run the expensive embedding path. Returns true for questions (contains `?`, `how do`, `explain`, etc.) or prompts over 100 characters that do not start with action verbs. Blocks on slash commands. Approximately 30% of prompts skip RAG.
9. **When RAG is enabled:**
   - **Knowledge graph query** - `query_knowledge_graph()`: generates Voyage AI embedding, seeds with pgvector, then walks `claude.knowledge_relations` up to 2 hops. Min similarity 0.35, token budget 400, top 3 seed hits.
   - **Vault RAG query** - `query_vault_rag()`: generates embedding, queries `claude.vault_embeddings`, fetches 3x more results than needed and deduplicates by doc_path. Min similarity 0.45, returns top 3 unique documents.
   - **Nimbus context** - Keyword search (no embedding) against `nimbus_context` tables for the four listed Nimbus project names.
   - **Schema context** - If prompt contains schema keywords (table, column, foreign key, etc.), queries `claude.schema_registry` embeddings. Min similarity 0.40.
10. **Context health check** - Reads `~/.claude/state/context_health.json` from the StatusLine sensor. Falls back to prompt count heuristic. Injects yellow/orange/red warnings with progressive urgency.
11. **Failure surfacing** - Calls `get_pending_failures()` to surface auto-filed bug feedback from the last 48 hours.
12. **Assembly and output** - Combines all context parts in priority order and writes `hookSpecificOutput.additionalContext` JSON to stdout.

### Voyage AI Integration

- **Model**: `voyage-3`
- **Dimensions**: 1024
- **Input type for queries**: `query` (distinct from `document` used during indexing)
- **Lazy loading**: The `voyageai` Python module is imported on first use, saving approximately 100ms on prompts that skip RAG.
- **In the hook**: Uses the `voyageai.Client` SDK. In `embed_vault_documents.py`: uses the REST API directly via `requests`.
- **API key**: Read from `VOYAGE_API_KEY` environment variable at runtime.

### Token Budget Behavior

The hook does not enforce a hard token cap on combined output. Instead, each subsystem limits its own results (top 3 vault docs, top 3 knowledge entries, top 3 schema tables, top 2 skills). The cognitive memory `recall_memories` tool has an explicit 1000-token budget, but that is a separate MCP tool path not called directly from the hook. In practice the hook can inject 2,000-6,000 tokens depending on how many subsystems fire.

The context health system provides graduated warnings at 30%/20%/10% remaining context but does not suppress injection to protect the budget.

### Issues Found

- **No aggregate token cap on the hook output**. On a long question touching schema keywords, config keywords, and a Nimbus project, all seven context blocks can fire simultaneously. There is no ceiling.
- **`needs_rag()` action-verb skip is too aggressive**. Prompts starting with "implement X but first explain the pattern" start with the word "implement" and skip RAG entirely, even though they need documentation context.
- **`query_knowledge_graph()` uses min_similarity=0.35** while `query_knowledge()` uses 0.55. This means the graph path is more permissive than the direct path - could surface weaker matches.
- **RAG usage log logs `query_type = "user_prompt"`** but the RAG Usage Guide states the valid values are `manual_search` and `session_preload`. The log will be inconsistent if anyone queries by query_type.

---

## 2. Knowledge Vault Health

### File Counts by Folder

| Folder | File Count (approx) | Notes |
|--------|---------------------|-------|
| `00-Inbox/` | 0 | Empty - no uncategorized captures |
| `10-Projects/` | ~105 | Heavily populated with Project-Metis (90+), claude-family (20+), ATO (5+), trading-intelligence (5+) |
| `20-Domains/` | ~85+ | Dominated by `awesome-copilot-reference/` (~75 agent files). Native domain docs: 12 |
| `30-Patterns/` | ~30 | Well-organized; gotchas, solutions, BPMN diagrams |
| `40-Procedures/` | ~27 | Core SOPs |
| `Claude Family/` | ~33 | Core system docs |
| `John's Notes/` | ~8 | Personal notes, finance docs |
| `_templates/` | 3 | Templates |

### Stale / Outdated Documents

**Documents with December 2025 version dates that reference the current (obsolete) architecture:**

- `/knowledge-vault/Claude Family/Claude Tools Reference.md` - Updated 2025-12-26. Still lists `filesystem` and `memory` MCPs as active. Lists `orchestrator` as a current server. Skills list is the pre-ADR-005 list (feature-workflow, nimbus-api, doc-keeper - not the current 8-skill inventory).

- `/knowledge-vault/Claude Family/Purpose.md` - Updated 2025-12-29. Still lists only three projects (Claude Family, ATO Tax Agent, Mission Control Web). Metis and trading-intelligence are not mentioned.

- `/knowledge-vault/Claude Family/Claude Family Memory Graph.md` - Updated 2025-12-26. Describes a JSONL-based mcp-server-memory at `C:\claude\shared\memory\claude-family-memory.json`. This MCP was retired in January 2026.

- `/knowledge-vault/Claude Family/Claude Family todo Session Start.md` - Updated 2025-12-26. Likely pre-hook-automation era content.

- `/knowledge-vault/40-Procedures/Family Rules.md` - Updated 2026-02-10 but still lists `orchestrator` in the MCP servers table as active for Claude Code (the orchestrator was retired 2026-02-24).

- `/knowledge-vault/40-Procedures/Add MCP Server SOP.md` - References orchestrator as a core infrastructure MCP.

- `/knowledge-vault/40-Procedures/New Project SOP.md` - Instructs new projects to configure postgres, project-tools, and orchestrator.

- `/knowledge-vault/Claude Family/Orchestrator MCP.md` - Updated 2026-02-07. Extensively documents an MCP that was retired 2026-02-24. The document does not note it is retired.

- `/knowledge-vault/10-Projects/claude-family/Session User Story - Spawn Agent.md` and `Session User Story - Cross-Project Message.md` - Both describe `mcp__orchestrator__*` tool calls that no longer exist.

- `/knowledge-vault/Claude Family/Database Schema - Overview.md` (under 10-Projects) - Reports 57 tables, updated 2025-12-26. Current count is 58 tables post-cleanup. Minor but shows the doc predates the 2026-02-28 cleanup.

### Deprecated Concept References

43 markdown files contain references to `orchestrator`, `claude_family.`, `claude_pm.`, or deprecated MCP names. The most significant concentration:
- All Session User Story docs reference `mcp__orchestrator__*`
- Family Rules, Add MCP Server SOP, New Project SOP still prescribe orchestrator
- Orchestrator MCP.md is a detailed description of a retired system with no retirement notice

### YAML Frontmatter Presence

Most vault documents in `00-Inbox/`, `10-Projects/`, `20-Domains/`, `30-Patterns/`, and `40-Procedures/` have YAML frontmatter. The `Claude Family/` folder documents are mixed - some have frontmatter (`synced: true/false`), some do not (e.g., `Purpose.md` has a minimal frontmatter block). The `John's Notes/` folder documents generally lack frontmatter. The `_templates/` files have illustrative frontmatter examples.

The Vault Embeddings Management SOP and Knowledge Capture SOP both require frontmatter. Compliance is roughly 75-80% across the full vault.

---

## 3. Embedding System Status

### How It Works

`/C:/Projects/claude-family/scripts/embed_vault_documents.py`:
- Reads markdown files from `C:/Projects/claude-family/knowledge-vault/`
- Extracts YAML frontmatter (using PyYAML; falls back to line-by-line parsing)
- Chunks text at 1,000 characters with 200-character overlap, breaking at sentence boundaries
- Calls Voyage AI REST API for each chunk with `input_type: "document"`
- Stores in `claude.vault_embeddings` with SHA256 hash for incremental skip logic
- Supports `--folder`, `--project`, `--all-projects`, `--force` flags

### Storage Tables

| Table | Purpose |
|-------|---------|
| `claude.vault_embeddings` | Vault markdown chunks + project docs (CLAUDE.md, ARCHITECTURE.md, etc.) |
| `claude.knowledge` (embedding column) | Learned knowledge entries |
| `claude.schema_registry` (embedding column) | Database table descriptions |
| `claude.skill_content` (description_embedding column) | Skill descriptions |
| `claude.book_references` (embedding VECTOR(1024)) | Book concept references |

### Incremental Sync

The hash-check approach is correct and functional. The script computes SHA256 of the file, compares it to the stored `file_hash`, and skips if identical. On hash change, it deletes the old chunks then re-embeds. This means renamed files create orphan rows since the path changes but the old path remains in the table.

### Known Gap

The Vault Embeddings Management SOP notes the vault had "88 files, ~768 chunks" as of 2025-12-30 but the glob shows the vault has grown substantially (project-metis alone adds 90+ files). The SOP's cost and time estimates are outdated. The `awesome-copilot-reference` subtree (75+ agent files) is explicitly excluded from RAG queries in the hook (`doc_path NOT LIKE '%%awesome-copilot%%'`) but is still embedded - wasted compute and storage.

---

## 4. Cognitive Memory System (F130)

### Implementation Status

The three tools are implemented in `/C:/Projects/claude-family/mcp-servers/project-tools/server_v2.py`:

- `remember()` - Routes credential/config/endpoint memory types to `session_facts` (short tier); learned/fact/decision to `knowledge` table (mid tier); pattern/procedure/gotcha to `knowledge` table (long tier). Performs dedup at 85% similarity, contradiction detection, and auto-relation linking.
- `recall_memories()` - Queries all three tiers in parallel with a configurable budget (default 1,000 tokens). Budget profiles shift allocation between tiers for task_specific, exploration, or default queries.
- `consolidate_memories()` - Three trigger modes: `session_end` promotes qualifying session_facts to mid tier; `periodic` promotes mid to long and runs decay/archive; `manual` runs the full cycle.

### Whether Consolidation Actually Runs

Based on the MEMORY.md documentation: the session_end_hook auto-calls consolidate_memories with trigger=session_end at the end of each session, and the startup_hook runs periodic consolidation with a 24-hour cooldown. This is the documented intent. The actual hooks (`session_end_hook.py`, `session_startup_hook_enhanced.py`) would need to be read to confirm these calls are present, but the MEMORY.md entry is detailed enough to suggest this was implemented as part of F130.

### Design vs. Implementation Gap

The `cognitive-memory-processes.md` document (dated 2026-02-25) contains a "What Needs Building" section that lists tier metadata, capture hook, token-budgeted retrieval, consolidation scheduler, contradiction detector, and desktop MCP as outstanding work. However, based on `server_v2.py`, at least `remember`, `recall_memories`, and `consolidate_memories` are all present and implemented. The document appears to be a design artifact that was not updated after implementation.

### Session Fact Persistence

Session facts are auto-injected on every prompt via `query_critical_session_facts()` - this is the lightweight SQL path that does not require embeddings. The injection covers credential, endpoint, config, and decision types. Notes and data fact types exist in storage but are not auto-injected, requiring a manual `list_session_facts()` call.

---

## 5. Knowledge Graph

### Table Structure

`claude.knowledge_relations` stores typed edges between knowledge entries. Supported relation types: extends, contradicts, supports, supersedes, depends_on, relates_to, part_of, caused_by.

### Graph Search Implementation

`query_knowledge_graph()` in the RAG hook uses a `claude.graph_aware_search()` PostgreSQL function that combines pgvector cosine similarity for seed nodes with a recursive CTE to walk `knowledge_relations` up to N hops. Results are returned with `source_type = direct | graph`, `graph_depth`, and `edge_path` fields. The hook uses max_initial_hits=3, max_hops=2.

The MCP tool `get_related_knowledge()` allows explicit traversal from a known knowledge UUID. `link_knowledge()` creates edges. `mark_knowledge_applied()` feeds back success/failure signals that adjust confidence scores.

### Usage and Value Assessment

**Structural concern**: The knowledge graph value is limited by how many relations are actually created. Relation creation requires explicit `link_knowledge()` calls or the auto-relation detection in `remember()`. If Claude instances rarely call `link_knowledge()` manually and `remember()` is called infrequently (because `store_knowledge` is the legacy path most documentation points to), the graph remains sparse.

The `query_knowledge_graph()` function falls back to the plain pgvector search if the graph query fails, which means the graph walk is an enhancement layer rather than a dependency. However, with a sparse graph, most queries will see zero graph-hop results (`graph_count=0`).

The RAG Usage Guide (version 3.1, updated 2026-02-10) reports "290+ learned knowledge entries" with "100% embedding coverage." That data point is 27 days old relative to today. No current count is observable without a database query.

---

## 6. Gaps and Recommendations

### Critical: Deprecated System Documentation

The orchestrator MCP was retired 2026-02-24. Multiple vault documents describe it as active and prescribe its use. Any new Claude session that reads `Family Rules.md`, `Add MCP Server SOP.md`, `New Project SOP.md`, or the Session User Story files will receive incorrect instructions. These documents should be updated to replace orchestrator references with the native `Task` tool and `project-tools` messaging tools.

Priority files to update:
- `/knowledge-vault/40-Procedures/Family Rules.md`
- `/knowledge-vault/40-Procedures/Add MCP Server SOP.md`
- `/knowledge-vault/40-Procedures/New Project SOP.md`
- `/knowledge-vault/Claude Family/Orchestrator MCP.md` (add retirement notice at top)
- `/knowledge-vault/10-Projects/claude-family/Session User Story - Spawn Agent.md`
- `/knowledge-vault/10-Projects/claude-family/Session User Story - Cross-Project Message.md`
- `/knowledge-vault/Claude Family/Claude Tools Reference.md`
- `/knowledge-vault/Claude Family/Claude Family Memory Graph.md`

### Significant: awesome-copilot-reference Embedding Waste

The `20-Domains/awesome-copilot-reference/` subtree contains 75+ GitHub Copilot agent definition files that are explicitly excluded from RAG results in the hook. Embedding these files costs money and consumes storage with zero retrieval value. The embed script should exclude this path, or the existing embeddings should be deleted.

### Moderate: No Token Budget Cap on Hook Output

The RAG hook can inject from 7 simultaneous context blocks with no aggregate ceiling. On queries that trigger all paths (schema keywords + Nimbus project + question form + session facts + skill suggestions + design map + failures), the combined injection could approach 5,000-8,000 tokens per prompt. This compounds with the 8-rule core protocol. A configurable max_context_tokens guard in `main()` would allow pruning lower-priority blocks when budget is tight.

### Moderate: `needs_rag()` Action Verb Over-Skip

The logic checks only the first word of the prompt against the ACTION_INDICATORS list. Compound prompts like "implement this but first explain how the pattern works" skip RAG because the first word is "implement." A secondary check for embedded question words even when the prompt starts with an action word would improve retrieval coverage for these cases.

### Moderate: Cognitive Memory Docs Inconsistency

`/knowledge-vault/10-Projects/claude-family/cognitive-memory-processes.md` contains a "What Needs Building" section listing items that `server_v2.py` shows are already implemented. The document should be updated to reflect current status so it does not mislead future analysis.

### Minor: RAG Usage Log Query Type Mismatch

The hook inserts `query_type = "user_prompt"` into `claude.rag_usage_log`, but the RAG Usage Guide documents valid types as `manual_search` and `session_preload`. The analytics queries in that guide will not find hook-generated rows. The query type should be standardized to `auto_hook` or the guide's examples should be updated.

### Minor: Vault File Count Drift vs. SOP Estimates

The Vault Embeddings Management SOP states "88 files, ~768 chunks" and "$0.30 total cost." The vault has grown significantly since then, primarily from Project-Metis session handoffs (90+ files). The SOP cost and time estimates should be refreshed based on a current embedding run.

### Minor: Orphan Embeddings on File Rename/Move

When a vault document is moved or renamed, `embed_vault_documents.py` creates new embeddings under the new path but leaves the old embeddings in `claude.vault_embeddings`. There is no cleanup step. Over time this accumulates stale rows that consume storage and may slightly dilute query results. A periodic cleanup job comparing stored paths against actual filesystem state would address this.

---

## File Paths Referenced

- `/C:/Projects/claude-family/scripts/rag_query_hook.py` - RAG hook implementation (2,120 lines)
- `/C:/Projects/claude-family/scripts/embed_vault_documents.py` - Embedding pipeline
- `/C:/Projects/claude-family/mcp-servers/project-tools/server_v2.py` - Cognitive memory tools (remember, recall_memories, consolidate_memories at lines 3551-3697)
- `/C:/Projects/claude-family/knowledge-vault/Claude Family/RAG Usage Guide.md` - RAG documentation (v3.1, updated 2026-02-10)
- `/C:/Projects/claude-family/knowledge-vault/40-Procedures/Vault Embeddings Management SOP.md` - Embedding SOP (updated 2025-12-30, partially stale)
- `/C:/Projects/claude-family/knowledge-vault/40-Procedures/Knowledge Capture SOP.md` - Knowledge capture procedure
- `/C:/Projects/claude-family/knowledge-vault/Claude Family/Orchestrator MCP.md` - Retired system doc (updated 2026-02-07, no retirement notice)
- `/C:/Projects/claude-family/knowledge-vault/Claude Family/Claude Tools Reference.md` - Stale tools reference (updated 2025-12-26)
- `/C:/Projects/claude-family/knowledge-vault/10-Projects/claude-family/cognitive-memory-processes.md` - Design doc with outdated "What Needs Building" section
- `/C:/Projects/claude-family/knowledge-vault/Claude Family/Claude Family Memory Graph.md` - References retired memory MCP