---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - domain/work-context-container
  - domain/agentic-routing
  - type/design
created: 2026-03-11
updated: 2026-03-12
status: active
---

# WCC Agentic Routing & Budget Challenge

Parent: [[wcc-ranking-design]]

Two topics that overflow the ranking overview: Option C's agentic routing (the distinguishing feature vs Option B), and the argument against CF's per-source budget allocation.

---

## Agentic Routing (Option C's Distinguishing Feature)

Option B assembles context when an activity changes. Option C additionally routes queries proactively — the assembler decides to fetch specific information before being asked.

The distinction: Option B is reactive (you changed activity, let me assemble context). Option C is proactive (you're about to need this, let me pre-fetch it).

### Routing Triggers

| Signal in Prompt | Routing Action |
|-----------------|---------------|
| OData entity name not in current context | Pre-fetch that entity's schema chunk |
| "How do I..." with no process_procedural chunks in context | Pre-fetch top procedural matches for domain |
| Feature transitions to `in_progress` | Pre-load feature's explicitly linked knowledge |
| Client name mentioned, not yet scoped | Pre-fetch that client's config chunks |
| Chunk in current context has `freshness_score < 0.4` | Emit staleness warning, offer re-verification |
| Code error message pattern detected | Route to `learned_cognitive` for known-gotchas first |

### Routing Architecture

A lightweight classifier runs after activity detection, before retrieval. It reads the prompt and emits routing hints that augment the retrieval query:

```
classify_prompt(prompt, current_context_chunks) → routing_hints[]

routing_hints examples:
  {type: 'entity_lookup',   entity: 'EmployeeSchedule'}
  {type: 'procedure_fetch', domain: 'odata_configuration'}
  {type: 'client_scope',    client_id: 'uuid'}
  {type: 'gotcha_check',    error_pattern: 'NullReferenceException in PayrollEngine'}
```

The retrieval query is augmented per hint:
- `entity_lookup` → add keyword filter for entity name to api_reference query
- `procedure_fetch` → shift `linked_knowledge_types` to prioritise process_procedural
- `client_scope` → add `client_id` filter to client_config query
- `gotcha_check` → run learned_cognitive query first, before similarity search

### Implementation Path

> **DECISION (2026-03-12):** No keyword/rule-based classifier at any phase. John's experience across 6+ months of Claude Family work: keyword matching has been consistently poor, RAG/embeddings far better by a large margin. This applies to activity detection AND agentic routing. The entire retrieval system is embedding-first.

**Phase 1 — Embedding-based classifier** (launch):
- Embed the prompt; compare against stored **routing exemplars** per hint type
- Routing exemplar = a short description embedded at ingestion time (e.g. "OData entity schema lookup", "known error workaround", "client-specific configuration")
- Cosine similarity ≥ 0.55 against a routing exemplar emits the corresponding hint
- Exemplars are seeded per knowledge type at onboarding; refined through retrieval feedback
- Entity detection: embed entity names/descriptions at ingestion — prompt similarity to those embeddings surfaces entity-scoped hints
- Error pattern detection: embed known-gotcha summaries — prompt similarity surfaces gotcha-check hints
- Client scoping: activity's scope fields provide client context directly (no dictionary lookup needed)

**Phase 2 — Learned classifier** (after retrieval quality metrics establish gaps):
- Analyse retrieval feedback data to identify systematic routing misses
- Generate new routing exemplars from successful retrievals where hints were absent
- Retire underperforming exemplars with low hit rates
- The classifier improves through the same feedback loop as the ranking system

Phase 1 is sufficient to distinguish Option C from Option B. Phase 2 adds precision through data, not through keyword rules.

### What This Looks Like in Practice

User prompt: "Getting NullReferenceException when the parallel pay run tries to load the Monash roster config."

Without agentic routing (Option B): Similarity search against full knowledge store with activity scoping. Returns most similar chunks.

With agentic routing (Option C):
1. Prompt embedding compared against routing exemplars → `gotcha_check` hint fires (similarity to "known error workaround" exemplar)
2. Activity scope already carries Monash client context → `client_scope` hint implicit
3. Prompt embedding similar to RosterConfig entity description → `entity_lookup` hint fires
4. Retrieval executes with these three augmentations
5. Result includes: known-gotchas for parallel pay run (learned_cognitive), Monash roster config schema, RosterConfig OData entity definition

The embedding classifier adds ~10ms (one vector comparison against exemplar set, cacheable). The retrieval augmentation adds no latency (hints modify the query parameters, not the query count). The quality difference is significant: learned gotchas surface first, client config is scoped correctly.

---

## Challenge: Per-Source Budget vs Unified Ranking

**What the CF prototype does**: `SOURCE_BUDGETS = {workfiles: 0.25, knowledge: 0.25, features: 0.15, session_facts: 0.10, vault_rag: 0.15, skills_bpmn: 0.10}`.

**The problem**: These percentages are fixed guesses. They don't adapt to the actual quality distribution of candidates in a given retrieval.

### The Concrete Failure Case

A user is working on a complex OData configuration task. The retrieval pool contains:
- 12 api_reference chunks scoring 0.78-0.85 similarity
- 4 workfile chunks scoring 0.55-0.62 similarity

With per-source budgets (assuming 2000-token budget):
- workfiles gets 500 tokens: includes all 4 workfile chunks (low-value)
- api_reference gets 300 tokens: includes 2-3 api_reference chunks (budget exhausted)
- 9 high-value api_reference chunks excluded because their bucket is capped

With unified ranking:
- Top 12 items by composite score fill the budget
- 10-11 api_reference chunks included (high-value)
- 1-2 workfile chunks included if they make the top-N cut
- Diversity constraint adds 1 chunk from each of top-3 sources if not already represented

The unified approach includes more relevant content. The per-source approach includes more diverse-but-less-relevant content.

### The Steelmanned Counter-Argument

Per-source budgets ensure diversity without a constraint mechanism. They are simpler to implement, predictable for developers, and prevent any single source from monopolising context.

### Why We Reject It

Predictability is not the right optimiser for context assembly. Relevance is. Developers can reason about diversity through the explicit diversity constraint — which is transparent and auditable. The per-source approach encodes an unstated assumption: "all sources are equally likely to have relevant content." That assumption is false for any specific activity.

The diversity constraint in unified ranking addresses the legitimate concern (avoid monopoly from one source) without the quality cost (force-include lower-scored content to maintain quotas).

**The deeper issue**: Per-source budgets are a symptom of not having a single ranking function. When you have three retrieval paths with different scoring, the only way to merge them is to allocate budgets by source. With one retrieval path and one scoring function, source-level allocation is unnecessary.

---

## Feedback Loop: Closing the Loop CF Left Open

CF implemented `rag_feedback` and `rag_doc_quality` tables but neither affects retrieval. The loop is write-only. METIS must close it from day one.

### The Closed Loop

```
Retrieval → Context injection → Claude uses it → Task outcome
     ↑                                                ↓
     ←──────── feedback_factor update ←──────────────
```

### Implementation

Feedback events are written to `retrieval_feedback` (schema in [[wcc-ranking-design]]). The `feedback_factor` on each chunk is recomputed nightly by a background job:

```
update_feedback_factors():
  for each chunk with feedback events since last run:
      positive_count = count(feedback_type IN ('marked_useful', 'task_completed'))
      negative_count = count(feedback_type IN ('rephrased', 'contradicted'))
      total = positive_count + negative_count
      if total > 0:
          raw_factor = positive_count / total
          # Smooth with prior (neutral = 0.5)
          smoothed = (raw_factor * total + 0.5 * 10) / (total + 10)
          UPDATE knowledge_chunks SET feedback_factor = smoothed WHERE chunk_id = ...
```

The Bayesian smoothing (`+ 0.5 * 10` in numerator and denominator) prevents 1 positive event from pushing a chunk to `feedback_factor = 1.0`. The effective prior is 10 neutral observations. After 10 real positive events, the factor reaches ~0.75.

### What This Enables Over Time

After 3+ months of production use per tenant, the feedback_factor becomes a learned quality signal that encodes what the organisation's staff actually found useful. Two organisations using the same product domain knowledge will develop different feedback patterns based on which knowledge actually helped their consultants. The retrieval system personalises at tenant granularity without any explicit configuration.

---

*Parent: [[wcc-ranking-design]]*
*Related: [[wcc-activity-space-design]], [[work-context-container-design]]*

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/wcc-ranking-agentic-routing.md
