---
tags:
  - project/Project-Metis
  - scope/system
  - type/research
  - topic/augmentation-layer
  - topic/cognitive-architecture
created: 2026-03-08
updated: 2026-03-08
status: active
knowledge_id: 267bc450-8866-420e-8511-5cdca5edc597
---

# Augmentation Layer — Research & Design Direction

## Why This Document Exists

During the C4 L2 session (2026-03-08), John asked: "where do the tools that we build for METIS live — like the cognitive memory?" This question revealed a gap in the container diagram. The tools we build — memory, RAG, skills, session management, coherence checking — don't fit neatly into any single container. They are augmentations of the AI itself, sitting between the user and the LLM.

John's assessment: **this is the crux of the system. If the Augmentation Layer doesn't work well with non-technical people in a contained sandbox, nothing else matters.**

This document captures the research and establishes the design direction for further analysis.

---

## The METIS View

Three layers work together:

| Layer | What It Does | Metaphor |
|---|---|---|
| **Knowledge Engine** | What the platform *knows* — stored data, embeddings, knowledge entries | The brain (storage) |
| **Augmentation Layer** | How the platform *gets smarter* — memory management, RAG orchestration, skills, context engineering, session continuity | The bridge (assembly) |
| **Intelligence Layer** | What the platform *thinks with* — LLM interaction, prompt construction, constrained deployment | The mind (reasoning) |

The Augmentation Layer spans Knowledge Engine and Intelligence Layer. It is not a separate service — it is the connective tissue that makes the difference between "generic LLM with a database" and "AI that deeply understands your domain."

### What Lives in the Augmentation Layer

| Tool / Capability | What It Does | Current State in Claude Family |
|---|---|---|
| Cognitive Memory | Multi-tier memory (short/mid/long), promotion, decay, dedup/merge | Working — `remember()` / `recall_memories()` |
| RAG Pipeline | Retrieval-augmented generation — embed, store, retrieve, inject context | Working — Voyage AI + pgvector, auto-injection |
| Skills System | Procedural knowledge — how to do specific tasks | Working — skill files, SKILL.md convention |
| Session Management | Session continuity — handoffs, facts, checkpoints | Working — `store_session_fact()`, handoffs |
| Design Coherence | Cross-cutting quality checking — extract, map, check, report | Working — five-phase skill |
| Knowledge Relations | Typed relationships between knowledge entries, graph walking | Working — `link_knowledge()`, `graph_search()` |
| Context Assembly | Building the right prompt from all available context | Implicit — not yet a named subsystem |

---

## Industry Research (March 2026)

### 1. CoALA — Cognitive Architectures for Language Agents

**Source:** Cognee.ai (explaining the CoALA academic paper)

CoALA proposes that robust AI systems need three core components: memory, decision processes, and actions. Memory is broken into:

- **Working Memory** — short-term scratchpad for immediate context (current session, recent messages)
- **Episodic Memory** — records of past events ("what happened last time I tried X")
- **Semantic Memory** — factual knowledge about the world (domain knowledge, rules)
- **Procedural Memory** — how to perform tasks (skills, embedded in code or LLM parameters)
- **Procedures** — higher-order functions that retrieve, manipulate, and apply stored information

**METIS mapping:** Working memory = session facts + current context. Episodic memory = session handoffs + conversation history. Semantic memory = knowledge store + RAG. Procedural memory = skills. Procedures = the augmentation layer orchestration.

### 2. Context Engineering (Five-Layer Architecture)

**Source:** Fractal Analytics (March 2026)

Treats context as a first-class system artifact. Five layers:

- **Layer A: System Identity** — who the AI is, constraints, reasoning style
- **Layer B: Retrieval** — knowledge retrieval, RAG pipeline
- **Layer C: State** — persistent state across sessions
- **Layer D: Session Memory** — conversation history, working context
- **Layer E: Tool/Action** — available tools and their outputs

Key insight: "When LLMs fail in production, the root cause is almost always contextual: missing constraints, polluted memory, overloaded prompts, or uncontrolled tool outputs."

**METIS mapping:** Layer A = constrained deployment pattern (system prompt, cached knowledge). Layer B = Knowledge Engine + RAG. Layer C = session facts, knowledge store. Layer D = session management, handoffs. Layer E = MCP tools, integration hub.

### 3. Memory-Augmented RAG

**Source:** Medium / AI Engineering (December 2024)

Adds a dynamic memory module as a first-class RAG component. Architecture:

- **Retrieval Module** — static knowledge retrieval (traditional RAG)
- **Memory Module** — dynamic, evolving, tailored to user/session/context
- **Reasoning Module** — merges static retrieval + memory for rich context
- **Generation Module** — uses enriched context for output

**METIS mapping:** This is exactly the dual-source pattern we need. Static knowledge (product APIs, compliance rules) + dynamic memory (session learnings, engagement patterns) → assembled context → LLM.

### 4. Observational Memory (Mastra)

**Source:** VentureBeat (February 2026)

Alternative to traditional RAG for session continuity:

- Two background agents: **Observer** (compresses conversation into dated notes) and **Reflector** (identifies patterns and insights)
- Divides context window into two blocks: observations (compressed history) + current interaction
- Scored 94.87% on LongMemEval (GPT-5-mini), vs 80.05% for Mastra's own RAG implementation
- "Simpler and more powerful — scores better on benchmarks"

**METIS relevance:** The observer/reflector pattern is similar to our session handoff + memory consolidation approach. Worth evaluating whether a similar two-agent compression model could improve our multi-session continuity.

### 5. Agentic RAG

**Sources:** IBM, Weaviate (2024-2025)

Adds AI agents to the RAG pipeline for adaptive retrieval:

- **Routing agents** — determine which knowledge sources to query
- **Validation agents** — evaluate retrieved context, decide whether to re-retrieve
- **Multi-source agents** — one queries databases, another combs emails/web, etc.
- Agents have memory (short and long term), enabling planning and complex task execution

**METIS relevance:** As METIS matures, the Knowledge Engine retrieval could become agentic — routing queries to the right knowledge source (product APIs vs compliance rules vs implementation patterns) rather than searching everything.

### 6. "Is RAG Dead?" — Context Engineering Evolution

**Source:** Towards Data Science (October 2025)

RAG is evolving into "context engineering" — retrieval is just one tool in a broader loop:

- Agents dynamically write, compress, isolate, and select context
- Semantic layers standardise data definitions so agents can understand, retrieve, and reason over all kinds of data, tools, memories, and other agents
- Next era requires metadata management across data structures, tools, memories, and agents themselves
- Evaluation moves beyond accuracy to include relevance, groundedness, provenance, coverage, and recency

**METIS relevance:** This is the direction we're heading. The Augmentation Layer IS context engineering — the discipline of assembling the right context for each interaction.

---

## Design Implications for METIS

### 1. The Augmentation Layer Needs to Be a Named Subsystem

Currently implicit across multiple tools. Should be explicitly designed as the orchestration layer that assembles context from all sources (knowledge store, memory tiers, session facts, skills, integration data) before any LLM interaction.

### 2. Non-Technical User Experience Is the Test

John's framing: "if this doesn't work well with non-tech people in a contained sandbox, it's not going to work." The Augmentation Layer must be invisible to the user — they interact naturally, and the layer silently assembles the right context. No technical knowledge required.

### 3. Competitive Positioning

The industry is moving fast. Key competitors/frameworks to watch:

| Framework | Focus | Status |
|---|---|---|
| CoALA | Academic cognitive architecture | Framework/paper |
| Mastra Observational Memory | Session continuity, cost reduction | Open source, production |
| LangChain / LlamaIndex | RAG orchestration, agentic workflows | Open source, widely adopted |
| Cognee | Knowledge graph memory engine | Open source, $7.5M seed |
| RAGFlow | Enterprise RAG + agent capabilities | Open source, production |
| Fractal Five-Layer | Enterprise context engineering | Methodology |

METIS advantage: we're building domain-specific (enterprise knowledge), not generic. The augmentation is tuned to *understanding what an organisation does*, not general-purpose retrieval.

### 4. What We Have vs What We Need

**Have (working in Claude Family):**
- Multi-tier memory with promotion/decay
- RAG with semantic search (Voyage AI + pgvector)
- Skills system (procedural knowledge)
- Session management and handoffs
- Knowledge relations and graph search

**Need to evaluate/build:**
- Explicit context assembly orchestration (the "reasoning module" from Memory-Augmented RAG)
- Observer/reflector pattern for better session compression (Mastra approach)
- Agentic retrieval routing (query goes to right knowledge source automatically)
- Context quality metrics (relevance, groundedness, recency — not just similarity scores)
- Non-technical user interface that makes all of this invisible

---

## Next Steps

1. **Map current Claude Family augmentation capabilities to the CoALA framework** — identify gaps
2. **Evaluate Mastra's observational memory pattern** — could it improve our multi-session continuity?
3. **Design the context assembly orchestrator** — the explicit subsystem that assembles context from all sources
4. **Define metrics** — how do we measure augmentation quality beyond similarity scores?
5. **Prototype non-technical user experience** — can a PS consultant use this without understanding RAG?

---

## C4 L2 Impact

The System Map (Gate Zero Doc 4) shows Knowledge Engine and Intelligence Layer as separate containers. The Augmentation Layer spans both. At Gate 2 (C4 L3), we need to show how the Augmentation Layer's subsystems (memory, RAG, skills, context assembly) connect the two.

For now, the C4 L2 is correct at its level of abstraction — the Augmentation Layer is an internal concern of how Knowledge Engine and Intelligence Layer interact, which is a Gate 2 design question.

---

*Research document | Created: 2026-03-08 | Author: John de Vere + Claude Desktop*
*Knowledge ID: 267bc450-8866-420e-8511-5cdca5edc597*
