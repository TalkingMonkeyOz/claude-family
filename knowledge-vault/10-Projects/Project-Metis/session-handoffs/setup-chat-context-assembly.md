---
tags:
  - project/Project-Metis
  - session-handoff
  - area/orchestration-infra
  - area/knowledge-engine
  - topic/context-assembly
  - topic/prompt-engineering
created: 2026-02-24
session: pending-chat-context-assembly
---

# Session Setup: Context Assembly & Prompt Engineering

**Chat Topic:** How the platform composes prompts at runtime — what goes in, in what order, from what sources, and how the layers interact.

**Area(s):** Knowledge Engine (Area 1) + Orchestration (Area 7) + Constrained Deployment — cross-cutting

**Level:** Brainstorm — capture ideas, flag gaps, don't spec implementation

## Read These First

1. Doc 6 in project files (`nimbus_doc6_constrained_deployment.docx`) — the four-layer constraint architecture. This is the starting point. Especially §3.1 (system prompt), §3.2 (cached knowledge), §3.3 (input classification), §3.4 (tool restriction).
2. `knowledge-engine/brainstorm-knowledge-engine-deep-dive.md` — knowledge categories A-F, four-level scope hierarchy, retrieval design, 10+ API endpoints
3. `orchestration-infra/agent-compliance-drift-management.md` — five-layer enforcement, core protocol injection, CLAUDE.md reinjection frequency
4. `orchestration-infra/agent-conventions.md` — the 8 rules that need to be in every prompt
5. `system-product-definition.md` — generic platform framing

## What's Already Decided

- **Four-layer constraint:** System prompt + cached knowledge (200K) + Haiku classifier + tool restriction. ✓ DECIDED.
- **Cached knowledge capacity:** Up to 200K tokens. Cache read at 10% of input price. 5-min TTL (refreshes on hit). ✓ DECIDED.
- **Core protocol injection:** Rules injected at END of every assembled prompt (recency bias). ✓ DECIDED.
- **CLAUDE.md reinjection:** Every ~15 interactions. ✓ DECIDED (tunable).
- **Knowledge retrieval:** Voyage AI embeddings + pgvector cosine similarity. ✓ DECIDED.
- **Intelligence layer:** Claude API (Sonnet 80%, Opus 20%). ✓ DECIDED.

## What's NOT Designed (The Gaps)

### 1. Prompt Assembly Sequence
When a query comes in to the /ask endpoint, what's the full assembly?

Rough sketch from existing docs:
```
[System prompt: identity, role, scope, boundaries, behaviour]
[Cached knowledge: 200K tokens of core domain knowledge]
[Session context: current session state, recent decisions]
[Retrieved knowledge: RAG results relevant to this specific query]
[Agent rules: 8 conventions injected at end]
[User query]
```

But the detail is missing:
- What's the exact token budget for each layer?
- What happens when the total exceeds the context window?
- What's the priority order for dropping content when space is tight?
- How do session context and retrieved knowledge interact — can they conflict?

### 2. Cached Knowledge Curation
Doc 6 §3.2 estimates 95K-170K tokens for core knowledge:
- Product API documentation: 30-50K tokens
- Domain rule type definitions: 20-40K tokens
- Delivery methodology and patterns: 15-25K tokens
- Common support resolutions: 10-20K tokens
- Standard operating procedures: 10-15K tokens
- Configuration templates by vertical: 10-20K tokens

Questions:
- Who curates this? How often is it updated?
- What's the process for adding/removing knowledge from the cache?
- How do we handle cache invalidation when knowledge changes?
- Is the cached knowledge the same for all users, or does it vary by role/deployment?

### 3. RAG + Cache Interaction
Two sources of knowledge at query time:
- Cached (always present, core knowledge, no retrieval step)
- Retrieved (RAG, relevant to specific query, may or may not overlap with cache)

How do they interact?
- Does retrieved knowledge ever contradict cached knowledge? How is that handled?
- Should retrieved knowledge be deduplicated against the cache?
- Does the retrieval layer know what's in the cache (to avoid fetching redundant context)?

### 4. Per-Deployment Configuration
Doc 6 §5 describes three deployment scenarios with different constraint configurations:
- Internal support assistant (Layers 1-3, staff tools)
- Implementation accelerator / Monash POC (Layers 1-3 + customer knowledge in MCP)
- Client-facing support (All 4 layers, maximum constraint)

Each has different knowledge in the cache, different tools, different system prompts. How is this configured?
- Per-deployment config file?
- Per-organisation settings in the database?
- Hardcoded per deployment? (simplest but doesn't scale)

### 5. The Overflow Strategy
When knowledge exceeds 200K cache limit:
- What moves to MCP/KMS for dynamic retrieval?
- How do we decide what stays in cache vs what moves out?
- Is there a priority framework? (e.g., API docs stay cached, support resolutions move to retrieval)

## Claude Family Lessons to Discuss

- **rag_query_hook.py fires on every prompt.** Injects context silently. This is the existing mechanism for automatic context injection. Works well but is hook-based (Claude Desktop specific), not API-based.
- **200K cache shares context window space.** The cached knowledge and the conversation share the same window. Long conversations eat into available space for knowledge. Need a strategy for this.
- **Recency bias is exploitable.** Rules at end of prompt work better than at start. Core protocol injection leverages this.
- **"Lost in the middle" is real.** In long contexts, middle content gets less attention. Design around this — put critical knowledge at start AND end, less critical in middle.

## Outcome Expected

A brainstorm vault file covering context assembly and prompt engineering design. Should answer: what goes into a prompt, from where, in what order, how the layers interact, how overflow is handled, and how deployment-specific configurations work. Gaps and open questions flagged.

---
*Setup doc for next chat session — created 2026-02-24*
