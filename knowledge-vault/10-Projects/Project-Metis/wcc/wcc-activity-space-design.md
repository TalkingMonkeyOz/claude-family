---
projects:
  - Project-Metis
tags:
  - project/Project-Metis
  - domain/work-context-container
  - domain/activity-space
  - type/design
created: 2026-03-11
updated: 2026-03-11
status: active
---

# WCC Activity Space — Design

Parent: [[work-context-container-design]]

The Activity Space is the scoping mechanism that makes the WCC work as a retrieval system rather than a search engine. Without it, every prompt queries the entire knowledge store. With it, retrieval is pre-scoped to the domain of current work before any ranking happens.

---

## What an Activity Space Is

An Activity Space is the system's answer to "what is this user working on right now?" It is not a task, a session, or a feature — it maps to a bounded area of work that persists across multiple sessions and accumulates linked knowledge over time.

| Concept | Example |
|---------|---------|
| Activity name | `monash-payroll-integration` |
| What it scopes | All knowledge relevant to Monash's payroll connector work |
| What it is NOT | A specific ticket, a session, or a user story |
| Lifetime | Created when focused work begins; dormant after 7 days; archived after 30 |

The dossier metaphor from library science applies: the Activity Space is the dossier for a case. Items are placed in it from all knowledge types. The assembler opens the dossier and pulls the most relevant items.

---

## Activity Entity

```
activity
├── activity_id         UUID PK
├── tenant_id           UUID NOT NULL (FK tenants, RLS)
├── name                TEXT NOT NULL          -- canonical name (authority control)
├── description         TEXT                   -- used in embedding
├── aliases             TEXT[]                 -- synonym list, maps → canonical name
├── activity_embedding  VECTOR(1024)           -- embedding of name + description
├── linked_features     UUID[]                 -- work tracking features in scope
├── linked_workfiles    UUID[]                 -- workfiles that belong to this activity
├── linked_knowledge    UUID[]                 -- knowledge_chunk IDs explicitly linked
├── linked_knowledge_types  TEXT[]             -- which of the 6 types are relevant
├── lifecycle_status    TEXT NOT NULL          -- active | dormant | archived
├── created_by          TEXT NOT NULL          -- 'user' | 'system' | 'implicit'
├── created_at          TIMESTAMPTZ NOT NULL
├── last_accessed_at    TIMESTAMPTZ
├── access_count        INT DEFAULT 0
```

`activity_embedding` is computed from `name || ': ' || coalesce(description, '')` using the same Voyage AI model as all other embeddings (voyage-3, 1024 dimensions). This ensures cosine similarity comparisons are valid.

`linked_knowledge_types` drives which of the 6 knowledge sources the assembler queries. An activity scoped to a payroll integration activates `['api_reference', 'client_config', 'process_procedural', 'learned_cognitive']` but not `product_domain` (unless explicitly added). This eliminates irrelevant source queries entirely.

---

## How Activities Are Created

### Explicit Creation (Preferred)

A user or system call explicitly creates the activity with name and description:

```
create_activity(
    name="monash-payroll-integration",
    description="Payroll file generation and SFTP delivery for Monash University",
    linked_features=["F112"],
    linked_knowledge_types=["api_reference", "client_config", "process_procedural"]
)
```

Explicit activities have accurate embeddings because description is provided. They are the authoritative source for semantic detection.

### Implicit Creation (Fallback Path)

When no explicit activity matches but a workfile component name matches word patterns in the prompt, the system auto-creates an activity from the component name with an empty description. This is the CF prototype behaviour (`_ensure_activity_exists`). It degrades detection quality because the embedding is computed from the name alone.

**Design decision**: Keep implicit creation as a fallback, but flag implicitly created activities for enrichment. Surface them to the user ("I'm treating this as the `sftp-delivery` activity — is that right?"). When the user confirms, update the description and re-compute the embedding.

The library science principle of literary warrant supports implicit creation: build the catalogue from what exists, not from theory. But it also requires that those entries be enriched before they become authoritative.

---

## Detection Mechanism: Embedding-Based

**What the prototype does**: Trigram similarity (`pg_trgm`) against activity names and aliases. Threshold 0.6 is declared as `MIN_ACTIVITY_SIMILARITY` but the code uses trigrams, not vectors.

**The problem**: Trigrams match character substrings. "authentication-token-manager" trigram-matches any prompt containing "token", regardless of semantic distance. False positives cause the wrong activity to activate, pulling irrelevant context.

**The fix**: Compare prompt embedding against `activity_embedding` using cosine similarity.

### Detection Algorithm

```
detect_activity(prompt, tenant_id, session_id) → (activity_name, activity_id, confidence)

1. Check session_facts for manual override ("current_activity" key)
   → If found: return that activity regardless of prompt content

2. Embed the current prompt using Voyage AI (voyage-3)
   → embed_prompt = voyage_embed(prompt)

3. Query activities table:
   SELECT activity_id, name,
          1 - (activity_embedding <=> embed_prompt) AS similarity
   FROM activities
   WHERE tenant_id = current_tenant
     AND lifecycle_status = 'active'
     AND activity_embedding IS NOT NULL
   ORDER BY similarity DESC
   LIMIT 5

4. Take top result IF similarity >= 0.6
   → If similarity >= 0.6: return that activity (confidence = similarity)

5. Alias expansion: check if any alias appears verbatim in the prompt
   → If matched: return canonical activity name (confidence = 1.0)
   (Alias expansion is a hard match, not similarity-based)

6. Workfile component fallback:
   SELECT DISTINCT component FROM activity_workfiles
   WHERE project_id = current_project
   → Word-overlap >= 2 words with prompt
   → If matched: auto-create or fetch activity from component name

7. No match: retain previous activity if any, else None
```

### Threshold Rationale

0.6 cosine similarity (Voyage AI voyage-3 space) corresponds roughly to:
- 0.9+: Near-identical text
- 0.75-0.9: Same topic, different phrasing
- 0.6-0.75: Related domain, likely same activity
- 0.45-0.6: Adjacent topics — might be related, might not
- <0.45: Different topic

A threshold of 0.6 means we require "related domain" before activating. This gives a false-positive rate of approximately 5-10% in practice, acceptable for a scoping mechanism (the ranking step corrects for scope errors by scoring items lower if they're irrelevant to the actual prompt).

### Embedding Cache

Activity embeddings are computed once and stored. They re-compute only when `name` or `description` changes. This costs ~2ms per activity update, not per prompt. The prompt embedding costs ~30ms per prompt (single Voyage API call, cached for 5 minutes against WCC state).

---

## Activity Lifecycle

| Status | Trigger | Behaviour |
|--------|---------|-----------|
| `active` | Created | Full retrieval scoping, included in detection queries |
| `dormant` | 7 days without access | Still searchable, excluded from default detection queries, lower weight in ranking |
| `archived` | 30 days without access | Excluded from all queries by default, accessible via explicit lookup only |

Dormancy and archival are reversible. Accessing a dormant activity restores it to active. This follows the records management lifecycle: semi-active records are still accessible, just filed away.

The 7-day and 30-day thresholds correspond to professional service engagement patterns: a 7-day gap typically means a topic has been set aside; a 30-day gap typically means the work is complete or blocked long-term.

---

## Activity-to-Knowledge Linking

Linking is the mechanism that narrows retrieval from "all knowledge" to "knowledge for this activity." There are three linking modes:

### 1. Explicit Links (Highest Authority)

Created when a knowledge chunk is specifically associated with an activity:
- User action: "remember this for the monash-payroll-integration activity"
- System action: chunk retrieved during an active session → auto-linked with co-access tracking

Stored as UUIDs in `linked_knowledge`.

### 2. Feature/Workfile Links

Features and workfiles associated with an activity inherit their knowledge links. When a feature has linked build tasks, those tasks' workfiles are reachable through the activity without explicit chunk-level linking.

### 3. Type Scoping

`linked_knowledge_types` tells the assembler which of the 6 sources to query. The assembler only opens the relevant drawers in the filing cabinet, not all of them. A purely internal process task may activate only `process_procedural` and `learned_cognitive` — never `api_reference`.

---

## How Activity Space Interacts with Each Retrieval Level

| Level | Activity Space Role |
|-------|-------------------|
| 1. Session facts | Read to find manual override; otherwise no interaction |
| 2. Activity scope | Activity IS this level — the filter applied before all other queries |
| 3. Cognitive/Learned | Filter by `linked_knowledge` UUIDs + activity's `tenant_id` |
| 4. Knowledge graph | Start from activity's linked chunks, walk 2 hops |
| 5. Product Domain | Query only if 'product_domain' in `linked_knowledge_types` |
| 6. API Reference | Query only if 'api_reference' in `linked_knowledge_types` |
| 7. Client Config | Query only if 'client_config' in `linked_knowledge_types`, scoped to activity's client |
| 8. Project/Delivery | Filter to `linked_features` UUIDs |

When no activity is detected, the assembler falls back to project-scoped retrieval across all knowledge types — equivalent to a broad search. This is worse but not broken. The Activity Space is an optimisation, not a hard dependency.

---

## Design Challenge: Auto-Create vs Require Explicit Creation

**CF prototype behaviour**: Auto-creates activities from workfile components (`_ensure_activity_exists`). When the user stashes a workfile under component "sftp-delivery", the WCC auto-creates an activity named "sftp-delivery" with no description.

**The problem with auto-create**: Activities created without descriptions have embeddings computed from the name alone. "sftp-delivery" is 2 words — the embedding is low-information. Detection quality degrades. The activity may match prompts it shouldn't (anything mentioning "sftp") and miss ones it should (prompts about "file transfer" that don't say "sftp").

**The argument for auto-create**: Literary warrant — the catalogue should reflect actual usage. If someone stashes workfiles under "sftp-delivery", that work exists and deserves a dossier. Requiring explicit creation adds friction that blocks adoption.

**Recommendation — Keep auto-create, but surface enrichment prompts**:

Auto-creation from workfile components is correct behaviour. The fix is not to require explicit creation but to make the description-gap visible. After auto-creating an activity, the system emits a notification: "Activity `sftp-delivery` auto-created from your workfile. Add a description to improve context detection: `update_activity('sftp-delivery', description='...')`."

This respects the zero-friction creation path while addressing the detection quality gap. Enrichment becomes a natural workflow step, not a gate.

The alternative — requiring explicit creation — would result in activities never being created, because the cognitive overhead of "I should create an activity before I start working" is too high. The catalogue builds itself from work, then gets enriched.

---

*Parent: [[work-context-container-design]]*
*Related: [[wcc-ranking-design]], [[library-science-research]], [[filing-records-management-research]]*

---

**Version**: 1.0
**Created**: 2026-03-11
**Updated**: 2026-03-11
**Location**: knowledge-vault/10-Projects/Project-Metis/wcc-activity-space-design.md
