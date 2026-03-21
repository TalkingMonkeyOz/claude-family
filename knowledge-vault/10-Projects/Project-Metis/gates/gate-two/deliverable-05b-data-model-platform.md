---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - deliverable/5b
  - type/data-model
  - domain/sessions
  - domain/agents
  - domain/llm
  - domain/tokens
created: 2026-03-17
updated: 2026-03-17
status: draft
---

# Gate 2 Deliverable 5b: Data Model — Platform Core

Extension of [[deliverable-05-data-model|Deliverable 5]]. Covers 11 tables for Phase 1 core platform: session management, agent orchestration, LLM tracking, token budgets, cognitive memory, and code intelligence.

**Key decisions informing this model:**
- Augmentation Layer is core Phase 1 (D3) — sessions, context assembly, memory
- Agent orchestration with sub-agent cap (P7)
- Single ranking pipeline with 6 signals (D10) — context snapshots track which signals were used
- Event-driven freshness (D11) — cognitive memory promotion feeds knowledge freshness
- Content-aware chunking (D8) — cognitive memory and code_symbols use same embedding dimension as knowledge_chunks
- Extensible parser pipeline (coding intelligence decision #4) — code is a content type alongside documents
- Flat tables + recursive CTEs over Apache AGE (coding intelligence decision #2) — backup-safe, faster, cloud-compatible

**References:** [[deliverable-05a-data-model-rbac|Deliverable 5a]] for users/audit FKs.

---

## 8. Session Management

### `sessions`

Core interaction unit — a user or agent working with METIS.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| user_id | uuid FK → users | Who started this session |
| scope_org_id | uuid FK → organisations | |
| scope_product_id | uuid FK → products | Nullable |
| scope_client_id | uuid FK → clients | Nullable |
| scope_engagement_id | uuid FK → engagements | Most sessions are engagement-scoped |
| session_type | text NOT NULL | interactive, api, agent, background |
| status | text NOT NULL | active, ended, abandoned, error |
| context_config | jsonb | Token budget, model prefs, tool permissions |
| started_at | timestamptz DEFAULT now() | |
| ended_at | timestamptz | |
| last_activity_at | timestamptz | For timeout detection |
| metadata | jsonb | Client info, entry point, etc. |
| created_at | timestamptz DEFAULT now() | |

### `session_messages`

Conversation history. Ordered by message_index.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| session_id | uuid FK → sessions | |
| message_index | int NOT NULL | Order within session |
| role | text NOT NULL | user, assistant, system, tool_call, tool_result |
| content | text | Message text (nullable for tool_call) |
| tool_name | text | For tool_call/tool_result messages |
| tool_input | jsonb | |
| tool_output | jsonb | |
| token_count | int | Estimated tokens for this message |
| model_id | text | Which model generated (assistant messages) |
| created_at | timestamptz DEFAULT now() | |

**Index:** (session_id, message_index) UNIQUE

### `session_context_snapshots`

Point-in-time context assembly snapshots. For eval and debugging.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| session_id | uuid FK → sessions | |
| snapshot_type | text NOT NULL | initial, mid_session, compaction |
| assembled_context | jsonb | Full context sent to model |
| knowledge_items_used | uuid[] | Which knowledge items included |
| total_tokens | int | Token count of assembled context |
| budget_limit | int | Budget cap for this assembly |
| budget_used_pct | float | % of budget consumed |
| strategy_used | text | relevance, recency, hybrid |
| created_at | timestamptz DEFAULT now() | |

**Purpose:** Measurable context assembly quality. Compare snapshots to eval retrieval effectiveness.

---

## 9. Agent Orchestration

### `agents`

Agent definitions — types, capabilities, configuration.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| name | text UNIQUE NOT NULL | e.g. supervisor, knowledge_specialist |
| agent_type | text NOT NULL | supervisor, specialist, tool_agent |
| description | text | |
| model_id | text NOT NULL | Which LLM this agent uses |
| capabilities | jsonb | Tool access, knowledge domains |
| system_prompt | text | System prompt template |
| config | jsonb | temperature, max_tokens, tool_choice |
| max_sub_agents | int DEFAULT 0 | Sub-agent cap (P7 orchestration) |
| status | text NOT NULL | active, disabled, deprecated |
| version | text | Semver for prompt/config tracking |
| created_at / updated_at | timestamptz | |

### `agent_instances`

Runtime instances — each spawned agent during a session.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| agent_id | uuid FK → agents | Definition used |
| session_id | uuid FK → sessions | Parent session |
| parent_instance_id | uuid FK → agent_instances | Null = top-level; set = sub-agent |
| spawned_by | uuid FK → users | Human whose access ceiling applies |
| status | text NOT NULL | pending, running, completed, failed, cancelled, timeout |
| input_context | jsonb | What the agent was given |
| output_result | jsonb | What the agent produced |
| error_info | text | |
| token_count_total | int | Aggregated from llm_calls |
| started_at | timestamptz DEFAULT now() | |
| completed_at | timestamptz | |
| metadata | jsonb | tool_calls_count, knowledge_items_accessed |

**Agent tree:** `parent_instance_id` enables supervisor → specialist hierarchy. Query depth via recursive CTE or Apache AGE graph.

**Access ceiling:** `spawned_by` → user_roles determines agent permissions. Runtime check, not schema-enforced.

---

## 10. LLM Call Log

### `llm_calls`

Every LLM provider call. Critical for eval, cost tracking, debugging.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| session_id | uuid FK → sessions | |
| agent_instance_id | uuid FK → agent_instances | Nullable (direct session calls) |
| model_id | text NOT NULL | e.g. claude-sonnet-4-6 |
| provider | text NOT NULL | anthropic, openai, etc. |
| request_type | text NOT NULL | chat, completion, embedding, tool_use |
| prompt_tokens | int NOT NULL | |
| completion_tokens | int NOT NULL | |
| total_tokens | int NOT NULL | |
| latency_ms | int | End-to-end call time |
| status | text NOT NULL | success, error, timeout, rate_limited |
| error_code | text | |
| error_message | text | |
| temperature | float | |
| max_tokens_requested | int | |
| tool_use | boolean DEFAULT false | |
| cache_hit | boolean DEFAULT false | Prompt caching |
| cost_usd | numeric(10,6) | Estimated, calculated post-hoc |
| metadata | jsonb | request_id, stop_reason, model_version |
| created_at | timestamptz DEFAULT now() | |

**Indexes:**
- `(session_id, created_at)` — session replay
- `(model_id, created_at)` — cost analysis by model
- `(status, created_at)` — error monitoring

---

## 11. Token Budgets

### `token_budgets`

Budget limits at various scopes and periods.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| scope_org_id | uuid FK → organisations | |
| scope_product_id | uuid FK → products | Nullable |
| scope_client_id | uuid FK → clients | Nullable |
| scope_engagement_id | uuid FK → engagements | Nullable |
| budget_type | text NOT NULL | session, daily, monthly, total |
| limit_tokens | bigint NOT NULL | Max tokens for period |
| used_tokens | bigint DEFAULT 0 | Running counter |
| period_start | timestamptz | Null for 'total' type |
| period_end | timestamptz | Null for 'total' type |
| is_hard_limit | boolean DEFAULT false | Hard = reject, soft = warn |
| created_at / updated_at | timestamptz | |

**Flow:** llm_calls INSERT → increment used_tokens → check thresholds → alert if crossed.

### `token_budget_alerts`

Threshold notifications.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| budget_id | uuid FK → token_budgets | |
| threshold_pct | int NOT NULL | e.g. 80, 90, 100 |
| triggered_at | timestamptz DEFAULT now() | |
| acknowledged_by | uuid FK → users | Nullable |
| acknowledged_at | timestamptz | |
| notification_sent | boolean DEFAULT false | |

---

## 12. Cognitive Memory

### `cognitive_memory`

METIS's working memory — facts, decisions, observations from sessions. Promotion path to permanent knowledge.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| session_id | uuid FK → sessions | Which session captured this |
| scope_org_id | uuid FK → organisations | |
| scope_product_id | uuid FK → products | Nullable |
| scope_client_id | uuid FK → clients | Nullable |
| scope_engagement_id | uuid FK → engagements | Nullable |
| memory_type | text NOT NULL | fact, decision, observation, preference, pattern |
| content | text NOT NULL | |
| confidence | float DEFAULT 1.0 | 0-1, decays if contradicted |
| source_type | text | user_stated, inferred, promoted_from_session |
| source_ref | text | message_id or knowledge_item_id |
| embedding | vector(1024) | For semantic recall (same dim as knowledge_chunks) |
| is_promoted | boolean DEFAULT false | Promoted to knowledge_items? |
| promoted_to_id | uuid FK → knowledge_items | Set on promotion |
| expires_at | timestamptz | Nullable (temporary memories) |
| is_superseded | boolean DEFAULT false | Replaced by newer memory |
| superseded_by_id | uuid FK → cognitive_memory | Self-referencing |
| created_at / updated_at | timestamptz | |

**Indexes:**
- HNSW on `embedding` — semantic recall (same pattern as knowledge_chunks)
- `(scope_engagement_id, memory_type, created_at)` — scoped recall
- `(session_id)` — session replay

**Promotion pattern:** cognitive_memory → knowledge_items via suggest-and-confirm. AI suggests, human approves, sets `is_promoted = true` + `promoted_to_id`.

---

## 13. Code Intelligence

### `code_symbols`

Parsed code symbols from tree-sitter AST analysis. Same scope chain as all METIS tables. Embeddings in shared Voyage AI vector space for cross-content-type semantic search.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| org_id | uuid FK → organisations | Scope chain |
| product_id | uuid FK → products | Nullable |
| client_id | uuid FK → clients | Nullable |
| engagement_id | uuid FK → engagements | Nullable |
| project_name | text NOT NULL | Repository/project identifier |
| name | text NOT NULL | Symbol name (function, class, variable) |
| kind | text NOT NULL | function, class, method, interface, variable, type, enum, module |
| file_path | text NOT NULL | Relative path within project |
| line_number | int NOT NULL | Start line |
| end_line | int | End line (nullable for single-line symbols) |
| scope | text | Enclosing scope (e.g. module path) |
| visibility | text | public, private, protected, internal |
| signature | text | Full signature (params, return type) |
| parent_symbol_id | uuid FK → code_symbols | Self-referencing: method→class, nested→parent |
| language | text NOT NULL | python, typescript, javascript, csharp, rust |
| file_hash | text | SHA-256 of source file at index time — skip re-parse if unchanged |
| embedding | vector(1024) | Voyage AI, same dimension as knowledge_chunks |
| last_indexed_at | timestamptz | When this symbol was last parsed |
| created_at | timestamptz DEFAULT now() | |
| updated_at | timestamptz DEFAULT now() | |

**Indexes:**
- `(project_name, name)` BTREE — symbol lookup by name within project
- `(file_path)` BTREE — all symbols in a file
- `(parent_symbol_id)` BTREE — children of a class/module
- HNSW on `embedding` — semantic similarity search (same pattern as knowledge_chunks)

**Design rationale:** Dedicated table rather than reusing `knowledge_items` because code has structural relationships (calls, imports, extends, parent symbols) that document chunks don't model. Validated in Claude Family CKG prototype (3,759 symbols, 19,517 references). Apache AGE rejected for graph storage — flat tables + recursive CTEs are faster (0.8ms vs 1.5-3.7ms), pg_dump-safe, and cloud-compatible (D6).

### `code_references`

Directional edges between symbols — calls, imports, extends, implements.

| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | |
| from_symbol_id | uuid FK → code_symbols | Source of the reference |
| to_symbol_id | uuid FK → code_symbols | Target (nullable if unresolved) |
| to_symbol_name | text NOT NULL | Name of target — kept for unresolved refs |
| ref_type | text NOT NULL | calls, imports, extends, implements, uses, instantiates |
| created_at | timestamptz DEFAULT now() | |

**Indexes:**
- `(from_symbol_id)` BTREE — "what does this symbol reference?"
- `(to_symbol_id)` BTREE — "what references this symbol?"

**Graph traversal:** Use recursive CTEs for call chain / dependency analysis (depth-limited, typically 3-5 hops). No Apache AGE dependency.

---

## Cross-References (All 11 Tables)

| This table | References | Via |
|------------|------------|-----|
| sessions | → users (05a) | user_id FK |
| sessions | → scope chain (05) | org/product/client/engagement FKs |
| session_messages | → sessions | session_id FK |
| session_context_snapshots | → sessions, knowledge_items (05) | FKs + uuid array |
| agents | (standalone definitions) | — |
| agent_instances | → agents, sessions, users (05a) | FKs |
| agent_instances | → agent_instances (self) | parent_instance_id |
| llm_calls | → sessions, agent_instances | FKs |
| token_budgets | → scope chain (05) | org/product/client/engagement FKs |
| token_budget_alerts | → token_budgets, users (05a) | FKs |
| cognitive_memory | → sessions, knowledge_items (05) | FKs |
| cognitive_memory | → cognitive_memory (self) | superseded_by_id |
| code_symbols | → scope chain (05) | org/product/client/engagement FKs |
| code_symbols | → code_symbols (self) | parent_symbol_id |
| code_references | → code_symbols (×2) | from_symbol_id, to_symbol_id FKs |

---

**Version**: 1.1
**Created**: 2026-03-17
**Updated**: 2026-03-22
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/deliverable-05b-data-model-platform.md
