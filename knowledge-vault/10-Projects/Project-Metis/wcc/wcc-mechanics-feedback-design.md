---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - domain/work-context-container
  - domain/feedback-loops
  - type/design
created: 2026-03-11
updated: 2026-03-12
status: active
---

# WCC Session Mechanics, Feedback Loops & Co-Access Tracking

Parent: [[work-context-container-design]]

This document covers how the WCC's four layers interact in a real session, the feedback mechanisms that close the retrieval loop, and the co-access tracking that builds behavioural evidence of knowledge relatedness. The scoring formula and assembler algorithm are defined in [[wcc-ranking-design]]. This document shows them operating over time.

---

## Section 1: Four-Layer Interaction During a Real Session

### The Scenario

A consultant resumes work on a Monash payroll integration — resolving a batch processing timeout. She worked on this activity last session. Her prior session ended with an unresolved question about roster config caching.

### Layer Responsibilities

| Layer | What | Owner | Survives compaction? |
|-------|------|-------|----------------------|
| **1. Core Protocols** | Task decomposition rules, boundaries | System prompt (Core Protocol hook) | Always — static |
| **2. Session Notebook** | Decisions, configs, credentials this session | `session_facts` table | Yes — DB-backed + PreCompact re-injection |
| **3. Knowledge Retrieval** | Chunked knowledge assembled per-prompt | WCC assembler | No — reassembled fresh each prompt |
| **4. Persistent Knowledge** | Cross-session patterns, gotchas | `persistent_knowledge` table | Always — long-lived storage |

**Layer 1** is not managed by the WCC. It assumes L1 is present. The benefit: L1 instructs Claude to decompose requests into structured task descriptions, which improves activity detection quality — better-formed prompts produce cleaner embeddings.

**Layer 2** informs L3 in two ways: (a) `current_activity` key overrides embedding-based detection (step 1 of the detection algorithm in [[wcc-activity-space-design]]); (b) `client_scope` key narrows `client_config` queries without prompt pattern matching. The consultant has `current_activity = "monash-payroll-integration"` stored — the WCC uses it immediately.

**Layer 3** is the WCC's primary domain. It queries 4 source types in parallel, scores all candidates with the composite formula, and fills the budget greedily. It is ephemeral: assembled context is not carried forward between prompts. Relevance shifts as conversation progresses.

**Layer 4** is retrieved as part of L3's pipeline (retrieval levels 3-4: cognitive/learned + knowledge graph). The distinction is lifecycle: L4 content was promoted through retrieval success and survives across sessions. The consultant's prior session encountered a Monash timeout gotcha. That chunk was in context when she marked a task `completed` — it auto-promoted to L4. This session, it surfaces at the top of ranking before she asks about timeouts.

**Layer interaction chain:**
```
L1 governs all reasoning → structured prompts → better activity detection
L2 informs L3 → activity override + client scope filter
L3 draws from L4 → persistent knowledge is one retrieval source
L4 survives sessions → promoted from L3 on task completion or 3+ retrievals
```

---

## Section 2: Session Lifecycle Mechanics

### Phase 1: Session Start

**Fresh session**: Detect activity from first prompt via embedding. Load activity's `linked_knowledge` UUIDs. First retrieval is a cache miss — full parallel query (~180ms).

**Resuming**: Read `session_facts` for `current_activity` override (skips embedding detection). Pre-warm cache using last activity's context bundle — costs one retrieval at session start but the first prompt hits cache. Load prior `session_notes` into Layer 2.

### Phase 2: Active Work

Per-prompt cycle:
```
detect_activity() → if changed: invalidate cache
→ cache hit (< 5 min, same activity): serve cached bundle
→ cache miss: retrieve_and_rank() → assemble() → cache result
→ inject bundle into prompt at priority 2
→ log co_access_log entry (chunk_ids[] in this assembly)
```

`remember()` call → write to `persistent_knowledge` or `session_facts` → invalidate WCC cache.
`stash()` call → write to `activity_workfiles` → invalidate WCC cache.
Activity change → invalidate cache; old activity's chunks leave context immediately.

### Phase 3: Pre-Compaction

The PreCompact hook injects (state preservation, not retrieval):
- Active todos + active features
- All `session_facts` for the current session
- `session_notes` content
- Pinned workfiles (`is_pinned = True`)

The WCC cache state file is persisted to `~/.claude/wcc_cache/{session_id}.json` before compaction. After compaction, context is compressed but the DB is unchanged — the WCC can reassemble from scratch if the cache expired.

### Phase 4: Post-Compaction Resume

1. `session_facts` re-read from DB — `current_activity` key re-establishes scope
2. Cache checked: hit if < 5 min, miss triggers full retrieval
3. `co_access_log` is unaffected (DB-persisted) — rankings compute correctly
4. Session notebook reconstructed from DB facts, not from compressed context

---

## Section 3: Feedback Loops

Three mechanisms feed `feedback_factor` on chunks. Together they close the loop CF left open (write-only `rag_feedback` table, never read). The Bayesian smoothing formula and nightly update job are defined in [[wcc-ranking-agentic-routing]].

All feedback writes to:
```sql
retrieval_feedback (
    feedback_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chunk_id        UUID NOT NULL REFERENCES knowledge_chunks(chunk_id),
    session_id      UUID NOT NULL,
    activity_id     UUID REFERENCES activities(activity_id),
    -- No tenant_id: separate DB per customer; scope is implicit
    feedback_type   TEXT NOT NULL,   -- marked_useful | task_completed | rephrased |
                                     -- contradicted | outdated | not_relevant | ab_useful | ab_not_useful
    feedback_source TEXT NOT NULL,   -- implicit_rephrase | implicit_completion | explicit_user | ab_test
    prompt_hash     TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

### Mechanism 1: Implicit Feedback (Automatic)

**Rephrasing detection** — weak negative. On each prompt, compute cosine similarity between current and previous prompt embeddings. If >= 0.85 (near-duplicate phrasing, not just related topic), the prior assembly likely did not fully answer the question. Log all prior assembly's chunks as `feedback_type = 'rephrased'`. Threshold is 0.85, not the activity-detection threshold of 0.6, because consecutive prompts are naturally more similar.

**Task completion** — positive. When `complete_work()` fires, read `co_access_log` for the session, filter entries to the task's active window (`task.started_at` to now), union `chunk_ids[]`, deduplicate. Write one `retrieval_feedback` row per unique chunk with `feedback_type = 'task_completed'`. This replaces CF's never-called `mark_knowledge_applied()` — fires automatically on task close.

**Activity abandonment** — neutral. If the activity changes without task completion, no feedback is written. Penalising abandonment would suppress chunks for legitimate interrupted-work patterns.

### Mechanism 2: Explicit Feedback (User-Triggered)

| User Action | `feedback_type` | Additional effect |
|-------------|----------------|-------------------|
| "Remember this" / `remember()` | `marked_useful` | Triggers persistent tier promotion if not already persistent |
| "That's wrong" / "That's outdated" | `contradicted` / `outdated` | Sets `freshness_score = 0.3`, flags `needs_review = TRUE` immediately |
| "Not relevant" / explicit dismissal | `not_relevant` | Scoped to current `activity_id` — does not globally penalise the chunk |

`not_relevant` feedback includes `activity_id` in the row. The nightly Bayesian update job respects this scope: a chunk useful for one activity is not penalised for being irrelevant to a different activity.

### Mechanism 3: Retrieval A/B Testing (Phase 2)

On 10% of retrievals, include one additional chunk from just below the budget cutoff. Track whether the chunk's `key_terms[]` (stored at embedding time) appear in Claude's next response. If yes → `ab_useful`; if no → `ab_not_useful`. Over time, A/B results identify chunks the composite score systematically undervalues — input for Phase 2 weight recalibration. Not required at launch.

---

## Section 4: Co-Access Tracking

Co-access captures relationships embeddings miss. "OData batch error handling" and "Monash timeout configuration" may have low cosine similarity but are always retrieved together when fixing batch errors. Co-access sees this pattern; vector search cannot.

Defined as Signal 2 in [[wcc-ranking-design]] (weight 0.30). This section defines schema and scoring algorithm.

### Schema

```sql
co_access_log (
    log_id       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   UUID NOT NULL,
    prompt_hash  TEXT NOT NULL,
    chunk_ids    UUID[] NOT NULL,   -- all chunks in this assembly
    activity_id  UUID REFERENCES activities(activity_id),
    -- No tenant_id: separate DB per customer; scope is implicit
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
CREATE INDEX idx_co_access_chunk_ids ON co_access_log USING GIN (chunk_ids);
CREATE INDEX idx_co_access_activity  ON co_access_log (activity_id, retrieved_at DESC);
```

One row per cache-miss assembly. Cache hits do not generate co-access events — no new retrieval decision was made.

### Scoring Algorithm

```
co_access_score(C, current_candidates, activity_id):
  co_retrieval_count = COUNT(log entries WHERE C IN chunk_ids
                             AND any current_candidate IN chunk_ids
                             AND activity_id = current_activity
                             AND retrieved_at > NOW() - INTERVAL '90 days')
  total_retrieval_count = COUNT(log entries WHERE C IN chunk_ids
                                AND activity_id = current_activity
                                AND retrieved_at > NOW() - INTERVAL '90 days')
  # No tenant filter needed — separate DB per customer
  return co_retrieval_count / NULLIF(total_retrieval_count, 0)
  -- NULL → treated as 0 in composite formula
```

The 90-day window prevents stale project-phase patterns from dominating current work. Bootstrap: all scores are 0 at launch; meaningful signal emerges after ~100 retrievals per activity. Strong signal after ~500 (3-4 months of active use). The 0.30 weight is effectively dormant at launch and activates as evidence accumulates.

---

## Section 5: Freshness Scoring

Every chunk has `freshness_score FLOAT NOT NULL DEFAULT 1.0`. It is a multiplier in the composite score. A chunk with similarity 0.85 and freshness 0.3 scores `0.255` effective (before recency and feedback multipliers). A chunk with similarity 0.65 and freshness 1.0 scores `0.65`. Stale content is penalised, not excluded.

### Freshness Events

| Event | Result | Notes |
|-------|--------|-------|
| Chunk first embedded | 1.0 | Default — no event needed |
| Source doc re-embedded (hash changed) | 0.5 for all chunks from that doc | System does not know which sentences changed; conservative partial staleness |
| Human re-verification | 1.0 | Explicit trust restoration |
| Explicitly superseded | 0.2 | Written when a new chunk is created with `explicit_relations` link type 'supersedes' |
| Product release event (tagged to knowledge type) | `max(0.3, current - 0.3)` | Registered API version bumps trigger type-scoped decay |
| Feedback: "wrong" / "outdated" | 0.3 + `needs_review = TRUE` | Immediate — does not wait for nightly job |

**Staleness propagation**: When a source document changes, all derived chunks become `freshness_score = 0.5`. Re-embedding produces new chunks starting at 1.0. As new chunks accumulate retrieval history and positive feedback, they self-displace old chunks through the composite score. Old chunks do not need deletion — they deprecate through scoring.

**Freshness is not time decay**: CF used `created_at` as a staleness proxy, which decays new content faster than old. METIS decouples freshness from time. An old chunk re-verified last week has `freshness_score = 1.0`. A new chunk contradicted yesterday has `freshness_score = 0.3`. Time is a proxy for staleness. Events are evidence of staleness. METIS uses evidence.

---

*Parent: [[work-context-container-design]]*
*Related: [[wcc-ranking-design]], [[wcc-activity-space-design]], [[wcc-ranking-agentic-routing]]*

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/wcc-mechanics-feedback-design.md
