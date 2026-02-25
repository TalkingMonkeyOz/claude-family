---
tags:
  - project/Project-Metis
  - area/orchestration-infra
  - area/knowledge-engine
  - scope/system
  - type/brainstorm
  - topic/context-assembly
  - topic/session-memory
  - topic/compaction-survival
  - phase/1
projects:
  - Project-Metis
created: 2026-02-24
synced: false
---

# Session Memory & Context Persistence — Brainstorm Capture

> **Scope:** system (core platform concern — how any agent maintains state, survives context limits, and persists knowledge)
>
> **Design Principles:**
> - State that only exists in the context window will be lost. Write it down or lose it.
> - Explicit checkpointing beats automatic capture — noise kills signal.
> - The agent's scratchpad is the desk notepad, not the filing cabinet. Keep it focused.
> - Different deployments cache different knowledge — one size does not fit all.
> - Don't fight transformer architecture — design around context window limits and compaction behaviour.

**Parent:** [[orchestration-infra/README|Orchestration & Infrastructure]]
**Cross-cuts:** [[knowledge-engine/README|Knowledge Engine]] (two-tier model, retrieval interaction)
**Depends on:** Constrained Deployment pattern (Doc 6), Five-Layer Enforcement Architecture

---

## 1. Three Kinds of Memory

The System has three distinct memory concerns operating simultaneously. They serve different purposes, have different lifespans, and need different mechanisms.

| Memory Type | What It Is | Lifespan | Analogy |
|-------------|-----------|----------|---------|
| **Working Memory** | What the agent needs RIGHT NOW for the current task | Current task / current prompt | Notepad on the desk |
| **Session Memory** | What happened so far this session — decisions, discoveries, state | Current session | Whiteboard in the room |
| **Persistent Memory** | What carries across sessions and agents — the institutional knowledge | Indefinite | Filing cabinet / knowledge base |

These are NOT the same as:
- **Audit log** = what happened (immutable record of actions, for traceability)
- **Scratchpad** = what matters right now (curated by the agent, for working context)
- **Knowledge base** = what the organisation knows (validated, versioned, searchable)

The audit log is comprehensive and append-only. The scratchpad is selective and mutable. The knowledge base is validated and permanent. All three coexist.

---

## 2. Session Scratchpad Design

The scratchpad is how an agent checkpoints important information so it survives context compaction and session boundaries. It is the primary defence against "I discovered X earlier but my context window no longer contains it."

> Lesson from Claude Family: Custom session facts/notepad outperforms native memory graph (MCP). The native graph added noise. Custom scratchpad was more reliable because the agent had explicit control over what went in.

### 2.1 What Gets Stored

The agent writes entries when it discovers, decides, or encounters something that would be lost if the context window reset. Not everything — just the things that matter.

**Entry categories:**

| Category | What It Captures | Example |
|----------|-----------------|---------|
| `decision` | A choice made during the session | "Using JWT with refresh tokens. SSO deferred to Phase 3." |
| `discovery` | Something learned that wasn't previously known | "time2work API returns 404 for deleted users, not 410. Handle accordingly." |
| `blocker` | Something preventing progress | "Cannot access Monash UAT — credentials expired. Waiting on IT." |
| `context` | Background that helps interpret later work | "Client confirmed they use casual academic employment under EA clause 14.3." |
| `handoff` | Information for the next agent or session | "Config generation complete for pay rules. Testing agent should validate scenarios 1-15 next." |

### 2.2 Entry Structure

```
scratchpad_entries
├── id (UUID, PK)
├── session_id (FK → sessions)
├── agent_id (varchar — which agent wrote this)
├── category (enum: decision, discovery, blocker, context, handoff)
├── key (varchar — descriptive, searchable label)
├── value (text — the content)
├── scope (enum: current_task, session, carry_forward)
├── related_work_item_id (FK → work_items, nullable)
├── created_at (timestamp)
├── superseded_by_id (FK → self, nullable) — for updates within a session
```

### 2.3 Scope Levels

| Scope | Meaning | Retention |
|-------|---------|-----------|
| `current_task` | Only relevant to the task in progress | Cleared when task completes or agent moves on |
| `session` | Relevant for the rest of this session | Retained until session ends, available on context reload |
| `carry_forward` | Relevant beyond this session | Included in session handoff package for next session/agent |

### 2.4 Who Writes and When

**The agent writes explicitly, via a tool.** Not automatic. Automatic capture creates noise that drowns signal.

> Lesson from Claude Family: Automatic memory writing added noise. The agent is better at knowing what's important than any heuristic we could build. But it needs to be TOLD to checkpoint — this is an enforceable rule.

**Proposed Rule (candidate for agent conventions):**
"When you discover something, make a decision, or hit a blocker that would be lost if your context window reset, write it to the scratchpad immediately. Do not batch scratchpad writes — write as you go."

**Checkpoint triggers (when the agent SHOULD write):**
- After every decision that affects later work
- After discovering unexpected API behaviour or system state
- When encountering a blocker
- Before spawning a sub-agent (checkpoint current state)
- When receiving new context from a human that changes the task
- At natural breakpoints in multi-step work

### 2.5 Reading Back After Compaction

When an agent's context window has been compacted (messages dropped to make room), the scratchpad serves as the reconstruction source.

**Read mechanism:**
```
GET /api/v1/session/{id}/scratchpad
  ?scope=session,carry_forward    (exclude current_task items from completed tasks)
  &category=decision,discovery    (optional category filter)
  &since=2026-02-24T10:00:00Z   (optional time filter)
```

Returns entries ordered by created_at. The agent reads these into its current context to reconstruct working state.

**When to read:**
- On session resume (after restart or crash)
- After context compaction (if the system can detect this — open question)
- When switching to a new task within the same session (read carry_forward items)
- When receiving a handoff from another agent

### 2.6 Difference from Audit Log

| | Scratchpad | Audit Log |
|-|-----------|-----------|
| **Purpose** | What matters right now | What happened (complete record) |
| **Written by** | Agent, selectively | System, automatically |
| **Mutable** | Yes (superseded_by_id for updates) | No (append-only) |
| **Granularity** | Key facts and decisions | Every action and state change |
| **Read by** | The agent, during work | Humans and compliance systems, after the fact |
| **Volume** | Low (curated) | High (comprehensive) |

---

## 3. Context Assembly — How the Prompt Gets Built

When a query or task comes in, the system assembles the complete prompt from multiple sources. The assembly order determines what the agent "knows" and what gets priority.

### 3.1 Assembly Order

```
┌──────────────────────────────────────────────────────────┐
│ 1. System Prompt (identity, role, boundaries)      ~2K   │  ← static, always first
│ 2. Cached Knowledge — Tier 1 (domain knowledge)   ~120K  │  ← cached, 10% read cost
│ 3. Session Context (scratchpad + session state)    ~5-10K │  ← from DB, per session
│ 4. Retrieved Knowledge — Tier 2 (RAG results)     ~10-20K│  ← dynamic, per query
│ 5. Task Context (current task spec, if applicable) ~2-5K  │  ← from work_items
│ 6. Conversation History (recent messages)          ~10-50K│  ← managed by LLM API
│ 7. User Query / Agent Instruction                  varies │  ← the actual request
│ 8. Core Protocol Rules (8 rules, injected at END)  ~1K   │  ← recency bias exploit
└──────────────────────────────────────────────────────────┘
```

**Why this order:**
- System prompt and cached knowledge are the "always on" foundation
- Session and task context personalise to the current work
- Retrieved knowledge supplements with specific details
- Conversation provides interaction continuity
- Core protocol rules go LAST to exploit recency bias (most recently read = most influential)

> Lesson from Claude Family: Rules at END of prompts work better than at START. The "lost in the middle" effect is real — content in the middle of long prompts gets less attention. Critical rules go at the end.

### 3.2 Token Budget Allocation

Context window sizes vary by model. The allocation must be proportional:

**Sonnet 4.5 (200K context window):**

| Component | Budget | % | Notes |
|-----------|--------|---|-------|
| System prompt + core protocol | ~3K | 1.5% | Static, always present |
| Cached knowledge (Tier 1) | ~120-150K | 60-75% | The bulk. Cached at 10% cost. |
| Session context (scratchpad) | ~5-10K | 2.5-5% | From DB. Curated, not raw. |
| Retrieved knowledge (Tier 2) | ~10-20K | 5-10% | RAG results, dynamic per query |
| Task context | ~2-5K | 1-2.5% | Current task spec |
| Conversation history | ~10-50K | 5-25% | Shrinks as session grows |
| Headroom / overflow | ~5-10K | 2.5-5% | Buffer for response generation |

**Opus 4.6 (1M context window):**
Same proportions but much more room. Cached knowledge could expand to 500K+. Conversation history has more room. Used for complex reasoning tasks where full context matters.

**Critical constraint:** The 200K cached prompt and conversation share the same context window. As conversation grows, it squeezes out room for retrieved knowledge and task context. This is why session memory (scratchpad in DB) matters — it's outside the context window.

### 3.3 Token Budget Manager

The system needs an active component that manages the token budget:

**Responsibilities:**
- Track current usage across all prompt components
- Decide what to include vs exclude when budget is tight
- Signal to the agent when context is getting full
- Manage the transition from "everything fits" to "something must be dropped"

**Shedding priority (what gets dropped first):**
1. Older conversation messages (standard compaction behaviour)
2. Lower-similarity RAG results (reduce from top-N to top-5)
3. Stale scratchpad items (completed current_task items)
4. Redundant session context (things now in scratchpad that are also in conversation)

**Never drop:**
- System prompt
- Core protocol rules
- Current task spec
- carry_forward scratchpad items

### 3.4 RAG vs Cached Knowledge Interaction

They complement, not overlap.

| | Tier 1 (Cached) | Tier 2 (RAG Retrieved) |
|-|-----------------|----------------------|
| **Contains** | Core knowledge always needed | Full knowledge base |
| **Availability** | Always in context | Retrieved per query |
| **Cost** | 10% of input cost (cached) | Full embedding + retrieval cost |
| **Latency** | Zero (already loaded) | ~50-100ms per retrieval |
| **Coverage** | Top ~150K tokens of knowledge | Everything in the knowledge base |
| **Analogy** | Textbook always open on the desk | Library you go to for specific lookups |

**At query time:**
1. Question comes in
2. Cached knowledge (Tier 1) is already in context — the LLM can reason over it immediately
3. RAG searches Tier 2 for additional relevant knowledge not in the cache
4. Retrieved results injected into prompt alongside cached knowledge
5. LLM generates answer using both sources
6. Source citations distinguish "core knowledge" vs "retrieved knowledge"

**Overlap handling:** Some knowledge will exist in both tiers (cached AND in the knowledge base). This is fine — the cached version provides instant access, the retrieval confirms/supplements. Not a problem unless it creates conflicting versions (addressed by versioning in knowledge_items).

---

## 4. Cross-Session Persistence

### 4.1 What Survives Session End

When a session ends (cleanly or via crash recovery), the following persists:

| Data | Storage | Retrieval Method |
|------|---------|-----------------|
| Session record (metadata, times, summary) | `sessions` table | Query by session_id |
| Session context JSONB (structured state snapshot) | `sessions.context` column | Load with session record |
| Scratchpad entries (all scopes) | `scratchpad_entries` table | Filter by session_id + scope |
| Work items created during session | `work_items` table | Filter by session_id or status |
| Full audit log | `audit_log` table | Filter by session_id |
| Files written (vault, filesystem) | Filesystem / git | Path references in session context |
| Session summary (human-readable handoff) | `sessions.summary` column or separate field | Load with session record |

### 4.2 Session Resume Mechanism

When a new session needs to pick up where a previous one left off:

```
resume_session(previous_session_id) → HandoffPackage
```

**HandoffPackage contains:**
1. Previous session summary (human-readable narrative)
2. All `carry_forward` scratchpad items from previous session
3. All open work items (status = assigned | in_progress | blocked)
4. Last N significant audit entries (decisions, state changes — not every log line)
5. Key metrics (session duration, tasks completed, tasks remaining)

**This is a tool call, not automatic injection.** The agent (or orchestrator) explicitly requests the handoff package and decides what to load into context. This keeps it controllable and prevents loading irrelevant state.

**Why not automatic:** Different resume scenarios need different context:
- Same agent continuing same work → load everything
- Different agent taking over → load only work items and carry_forward facts
- Human reviewing session output → load summary and decisions only
- Crash recovery → load full state for reconstruction

### 4.3 Cross-Agent Context Transfer

When one agent type hands off to another (e.g., KnowledgeAgent → ConfigAgent within the same engagement):

```
Orchestrator creates handoff package:
  ├── Relevant carry_forward scratchpad items (not all — filtered by relevance)
  ├── Work items being handed over (with status and context)
  ├── Key decisions from previous agent's work
  └── Engagement context (client, product, scope)

Receiving agent gets:
  ├── Its own system prompt (role-specific)
  ├── Cached knowledge (same Tier 1 cache, possibly role-specific variant)
  ├── Handoff package (injected as session context)
  └── Its task spec

Receiving agent does NOT get:
  ├── Full session history of previous agent (noise)
  ├── Previous agent's current_task scratchpad items (irrelevant)
  └── Previous agent's conversation history
```

**Key principle:** Each agent starts with clean context + targeted handoff. Not a brain dump of everything the previous agent knew.

> Lesson from Claude Family: Sub-agent isolation is the strongest defence against context rot. Fresh context per task beats long sessions. The handoff package is how you get isolation WITHOUT losing continuity.

---

## 5. Compaction Survival

### 5.1 The Problem

Context compaction (dropping older messages to make room for new ones) happens silently in the LLM API. The agent doesn't know what was dropped. Information that was "known" earlier in the conversation may simply vanish.

> Lesson from Claude Family: Context compaction loses information. You don't know what got dropped. Session facts/notepad was built specifically as insurance against this. The key insight: if it's only in the context window, it's ephemeral. If it's in the database, it's persistent.

### 5.2 The Defence: Write-Through Scratchpad

The scratchpad is the primary compaction survival mechanism. When the agent writes to the scratchpad, the data goes to the database immediately — not buffered in context.

```
Agent discovers something important
    ↓
Writes to scratchpad (DB write, immediate)
    ↓
Context compaction drops the original conversation
    ↓
Agent reads scratchpad to recover the fact
    ↓
Continues work with the fact restored
```

This is a **write-through** pattern. The scratchpad entry exists in BOTH the context window AND the database. If the context loses it, the database still has it.

### 5.3 Compaction Detection

**Open question:** Can the system detect when compaction has occurred?

Possible approaches:
- **Token counting:** Track approximate token usage. When it approaches the limit, proactively save state before compaction hits.
- **Canary tokens:** Include a known marker early in the conversation. If the agent can't see it, compaction has occurred. (Fragile — depends on model behaviour.)
- **Periodic refresh:** Every N interactions, the agent re-reads its scratchpad regardless of whether compaction occurred. Belt-and-suspenders approach.
- **Model signals:** Some API responses may indicate truncation. Provider-specific.

**Recommended approach:** Periodic refresh (simplest, most reliable). Every ~20 interactions, the agent re-reads its session scratchpad and task context. This aligns with the CLAUDE.md reinjection cycle (every ~15 interactions) — could be combined into a single "context refresh" mechanism.

### 5.4 Checkpoint Frequency

Rule-based, not timer-based:

| Trigger | What Gets Checkpointed |
|---------|----------------------|
| Decision made | Decision entry to scratchpad (scope: session or carry_forward) |
| Unexpected discovery | Discovery entry to scratchpad |
| Blocker encountered | Blocker entry to scratchpad |
| Before sub-agent spawn | Full state checkpoint (all in-flight context → scratchpad) |
| New human context received | Context entry to scratchpad |
| Natural breakpoint in multi-step work | Progress checkpoint |
| Every ~20 interactions | Periodic context refresh (re-read scratchpad) |
| Session end | Automatic session summary generation |

---

## 6. Two-Tier Knowledge Model

### 6.1 Tier 1: Cached System Prompt

Core knowledge that should always be in context. Feels "baked in" to the AI — no retrieval step, no latency, no relevance ranking. Always available.

**What goes in Tier 1:**

| Knowledge Type | Why It's Always Needed | Estimated Tokens |
|---------------|----------------------|-----------------|
| Product API reference | Every task touches APIs | 30-50K |
| Core compliance/rule definitions | Safety-critical, always relevant | 20-40K |
| Top implementation patterns | The "80%" patterns used constantly | 15-25K |
| Standard procedures | How-to for common operations | 10-15K |
| Organisation conventions and terminology | Shared language | 5-10K |
| **TOTAL** | | **80-140K** |

This leaves headroom within the 200K cache limit for growth.

**What does NOT go in Tier 1:**
- Client-specific configurations (isolation — always Tier 2)
- Historical support resolutions (volume — Tier 2 with retrieval)
- Engagement-specific decisions (scope — Tier 2)
- Edge case patterns (low frequency — Tier 2 with retrieval on demand)
- Meeting notes and decision records (volume — Tier 2)

### 6.2 Tier 2: MCP/KMS Retrieval

Everything in the knowledge base that isn't cached. Retrieved on demand via semantic search when the cached knowledge isn't sufficient to answer.

**Retrieval trigger:** The /ask endpoint always does both — uses cached knowledge AND retrieves from Tier 2. The RAG results supplement what's already in context.

**Retrieval pipeline:**
```
Query → Embed (Voyage AI) → Vector search (pgvector) → Scope filter → Rerank → Top-N → Inject into prompt
```

### 6.3 Decision Rule: Tier 1 vs Tier 2

| Criteria | → Tier 1 | → Tier 2 |
|----------|----------|----------|
| Used in >20% of queries | ✓ | |
| Compliance/safety critical | ✓ | |
| Core to product understanding | ✓ | |
| Changes rarely | ✓ | |
| Client-specific | | ✓ |
| Historical/archival | | ✓ |
| High volume (many items) | | ✓ |
| Edge case / low frequency | | ✓ |

### 6.4 Overflow Strategy

When Tier 1 knowledge exceeds the cache limit:

1. **Priority-score each item** based on query frequency, compliance criticality, and recency
2. **Lowest-priority items move to Tier 2** — still available via retrieval, just not cached
3. **Periodically re-evaluate** based on query logs (what gets asked about most?)
4. **Alert when cache is >80% full** — human decides what to prioritise

### 6.5 Deployment-Specific Caching

Different constrained deployments for different roles should cache different knowledge. One size does not fit all.

| Deployment | Tier 1 Focus | Why |
|-----------|-------------|-----|
| **Support Assistant** | Product API + common resolutions + compliance rules | Support needs immediate, accurate answers |
| **Delivery Accelerator** | Implementation patterns + config templates + procedures | Delivery needs how-to knowledge |
| **Client Portal** | Product basics + client-specific config (scoped) | Client needs their own context |
| **Testing Agent** | Test scenarios + expected outcomes + regression patterns | Testing needs validation reference data |
| **Compliance Reviewer** | Full compliance/rule knowledge + audit patterns | Compliance needs comprehensive rule coverage |

Each deployment gets its own cached prompt payload, assembled from the same knowledge base but with different priority scoring.

### 6.6 Cache Assembly Script

A build-time (or scheduled) process that assembles the Tier 1 cached prompt:

```
assemble_cache(deployment_type, organisation_id, product_id, optional client_id)
  → Fetch knowledge items matching Tier 1 criteria
  → Sort by priority score
  → Pack into prompt until token budget reached
  → Store assembled prompt for caching
  → Log what was included/excluded
  → Alert if priority items were excluded due to space
```

This runs whenever knowledge changes significantly (new product release, compliance update) or on a schedule (daily/weekly).

---

## 7. Interaction Patterns — Putting It All Together

### 7.1 Simple Query (Support)

```
User asks: "How do I configure penalty rates for casual employees?"

1. System prompt + cached knowledge already in context (Tier 1)
2. Input classifier (Haiku): "Is this on-topic?" → YES
3. RAG retrieves from Tier 2: specific penalty rate patterns, client-specific EA details
4. LLM generates answer using Tier 1 context + Tier 2 retrieval
5. Response includes source citations from both tiers
6. Query logged to audit trail
```

No scratchpad involvement — single query, no session state needed.

### 7.2 Multi-Step Task (Delivery)

```
Agent task: "Generate pay rule configuration for Monash casual academics"

1. System prompt + cached knowledge (Tier 1) loaded
2. Agent reads task spec from work_items table
3. Agent reads scratchpad for any carry_forward items from previous sessions
4. Agent calls /search to retrieve Monash-specific EA knowledge (Tier 2)
5. Agent discovers EA clause 14.3 has unusual overtime interaction
   → Writes to scratchpad: category=discovery, key="monash_ea_14.3_overtime"
6. Agent generates partial configuration
7. Agent hits blocker: API doesn't support bulk rule creation
   → Writes to scratchpad: category=blocker, key="bulk_rule_api_gap"
8. Context compaction occurs (long session)
9. Agent re-reads scratchpad on next interaction — recovers discoveries and blocker
10. Agent completes configuration, writes handoff entry for Testing Agent
11. Session ends — summary generated, carry_forward items tagged
```

### 7.3 Cross-Agent Handoff

```
Knowledge Agent finishes client context gathering
    ↓
Orchestrator creates handoff package:
  - carry_forward scratchpad items (3 entries)
  - work items (2 open: "config generation", "test scenario creation")
  - key decisions (EA interpretation confirmed with client)
    ↓
Config Agent starts new session:
  - Own system prompt + cached knowledge (Tier 1)
  - Handoff package injected as session context
  - Reads task spec for "config generation"
  - Does NOT have Knowledge Agent's full conversation history
    ↓
Config Agent works with clean context + targeted handoff
```

---

## 8. Open Questions

- [ ] **Compaction detection:** Can we reliably detect when context compaction has occurred? Or is periodic refresh sufficient?
- [ ] **Scratchpad size limits:** Should there be a max number of entries per session? Per scope? What prevents scratchpad bloat?
- [ ] **Automatic summarisation:** Should the system auto-summarise old scratchpad entries to compress them? Or is manual curation better?
- [ ] **Tier 1 cache refresh frequency:** How often should the cached prompt be rebuilt? On every knowledge change? Daily? On-demand?
- [ ] **Token counting accuracy:** Can we accurately count tokens across all prompt components before sending to the API? Or do we estimate and handle overflow?
- [ ] **Scratchpad vs work_items overlap:** Some information belongs in both (e.g., a blocker is relevant to the task AND to the session). How do we avoid duplication?
- [ ] **Multi-model support:** Different models have different context windows (200K vs 1M). Does the context assembly logic adapt per model?
- [ ] **Encryption:** Should scratchpad entries be encrypted at rest? They may contain client-sensitive discoveries.
- [ ] **Retention:** How long do session scratchpad entries persist? Forever? Purged after N days? After session review?

---

## 9. Relationship to Other Areas

| Area | Relationship |
|------|-------------|
| **Knowledge Engine** | Tier 2 retrieval comes from the Knowledge Engine. Cache assembly pulls from Knowledge Engine. |
| **Constrained Deployment** | Defines the 200K cached prompt pattern that Tier 1 implements. |
| **Agent Compliance** | Scratchpad checkpointing becomes an enforceable agent rule. Context refresh aligns with CLAUDE.md reinjection cycle. |
| **BPMN/SOP Enforcement** | BPMN gates may require reading scratchpad state to verify prerequisites are met. |
| **Orchestration** | Session management, handoff packages, and cross-agent transfers are orchestration concerns that use this memory infrastructure. |

---

*Source: Focused session on Session Memory & Context Persistence, 2026-02-24*
*Setup doc: session-handoffs/setup-chat-session-memory-context.md*
*Next: Write session handoff, update README and decisions tracker*
