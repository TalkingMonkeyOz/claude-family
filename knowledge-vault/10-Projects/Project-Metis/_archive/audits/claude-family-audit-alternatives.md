---
projects:
- claude-family
- Project-Metis
tags:
- audit
- alternatives
- enterprise
synced: false
---

# Audit: Enterprise Alternative Analysis

**Parent**: [[claude-family-systems-audit]]

---

## Comparison Matrix

| System | Claude Family Approach | Enterprise Alternative | Our Advantage | Their Advantage |
|--------|----------------------|----------------------|---------------|-----------------|
| **Event System** | Python stdin/stdout hooks | Redis Streams, NATS, Kafka | Tight Claude Code integration | Cross-platform, scalable, observable |
| **RAG** | Voyage AI + pgvector | Qdrant, Pinecone + LangChain | Integrated with hook system; no external deps | Purpose-built for scale; better tooling |
| **BPMN Engine** | SpiffWorkflow 3.1.2 | Camunda 8, Temporal.io, Flowable | Python-native, embedded, fast tests | Production-grade, multi-language, visual designer |
| **Knowledge Graph** | PG relations + pgvector | Neo4j, Apache AGE, MemGraph | Same DB as everything else | Native graph queries, visualization |
| **Session Mgmt** | Custom hooks + DB | LangGraph, CrewAI, AutoGen | Full control over lifecycle | Framework support, community |
| **Work Tracking** | Custom PG tables + WorkflowEngine | Linear API, Jira, GitHub Projects | Integrated state machines | Ecosystem, UI, collaboration |
| **Messaging** | PG message table | Redis pub/sub, RabbitMQ, NATS | Simple, no extra infra | Real-time, scalable |
| **Config Mgmt** | DB-driven + script gen | Consul, etcd, Vault | Self-healing, project-aware | Distributed, encrypted, production-grade |
| **AI Memory** | 3-tier cognitive (F130) | Mem0, Zep, LangMem | More sophisticated tier model | Simpler API, hosted options |
| **Process Modeling** | BPMN (SpiffWorkflow) | Camunda, Flowable, Zeebe | Embedded, fast, testable | Enterprise features, monitoring |

---

## Analysis by System

### 1. Event/Hook System

**Current**: Python scripts on stdin/stdout, platform-specific (Windows msvcrt locking).

**Best enterprise options (2026)**:
- **Temporal.io** — Durable execution, handles retries/timeouts natively. Growing fast.
- **NATS** — Lightweight pub/sub with JetStream for persistence. Cloud-native.
- **Custom webhook framework** — REST/gRPC endpoints triggered by LLM lifecycle.

**Recommendation**: The hook concept is sound. Replace stdin/stdout transport with HTTP/webhook or message queue. Keep the per-event-type pattern. Add health monitoring.

### 2. RAG Pipeline

**Current**: Voyage AI embeddings, pgvector, custom retrieval in Python hook.

**Best enterprise options (2026)**:
- **Qdrant** — Purpose-built vector DB, excellent filtering, scales well.
- **LlamaIndex** — RAG framework with built-in evaluation and optimization.
- **Pinecone** — Managed vector DB, zero ops.

**Recommendation**: pgvector is fine at our scale (~10K vectors). At 100K+, consider Qdrant. Our custom retrieval logic (multi-source, budget-capped) is more sophisticated than off-the-shelf — preserve the logic, swap the vector store.

### 3. BPMN Process Engine

**Current**: SpiffWorkflow 3.1.2 (Python), pytest validation, 76 processes.

**Best enterprise options (2026)**:
- **Camunda Platform 8** — Industry standard. BPMN + DMN. Zeebe for execution.
- **Temporal.io** — Not BPMN but durable workflow execution. Growing fast.
- **Flowable** — Open-source BPMN engine, Java-based.

**Recommendation**: SpiffWorkflow is surprisingly effective for our use case (process validation + GPS navigation). For Metis enterprise, consider Camunda for client-facing workflows but keep SpiffWorkflow as internal sidecar for Claude-side process governance.

### 4. AI Memory (Cognitive Memory)

**Current**: 3-tier (short/mid/long) with auto-consolidation, dedup, relation linking.

**Best enterprise options (2026)**:
- **Mem0** — AI memory layer with auto-extraction. Simpler but less control.
- **Zep** — Long-term memory for AI assistants. Session-aware.
- **LangMem** — LangChain's memory framework. Modular.

**Recommendation**: Our 3-tier system is more sophisticated than any off-the-shelf option. The consolidation lifecycle (promote/decay/archive) and budget-capped retrieval are genuine innovations. Keep the architecture, potentially open-source it.

### 5. Work Tracking + State Machines

**Current**: Custom tables + WorkflowEngine with 28 transitions + audit log.

**Best enterprise options**: Linear, Jira, GitHub Projects for the UI/collaboration layer.

**Recommendation**: The WorkflowEngine pattern is excellent for AI governance. Enterprise should expose work items through a standard API (Linear/Jira integration) but keep the state machine enforcement server-side.

---

## Key Insight

**No single product combines all of these**. The integration between hook-based behavior modification, RAG retrieval, BPMN governance, cognitive memory, and work tracking is unique. Each piece has mature alternatives, but the combined system — where RAG injection is governed by BPMN models, enforced by hooks, tracked in a state machine, and remembered across sessions — is our competitive advantage.

**For Metis**: Don't replace the architecture. Replace the transports and storage backends with enterprise-grade components while preserving the integration patterns.

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-audit-alternatives.md
