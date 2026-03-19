---
projects:
  - Project-Metis
tags:
  - project/metis
  - gate/two
  - scope/architecture
created: 2026-03-15
updated: 2026-03-15
---

# Cluster 3: Architecture Decisions (Detail)

Parent: [[gate-two/decisions-summary|Gate 2 Decisions Summary]]

## C3-1: Context Assembly Orchestrator

**Decision:** Declarative recipe pattern.

Each agent type/task has a **context recipe** — a config specifying which sources to include, token budget per source, and priority order. The orchestrator is a simple executor; intelligence is in recipe design.

### Recipe Tiers

| Recipe | Knowledge | Workflow | Session | Enforcement |
|--------|-----------|----------|---------|-------------|
| system_agent | none | basic | none | minimal |
| workflow_agent | task_relevant | full | light | standard |
| conversational | full_rag | aware | full | heavy |

Recipes are composable configs, not code. Fits ethos: readable, expandable, maintainable.

---

## C3-Bonus: Scope Guardrails

**Decision:** Per-engagement policy + per-user permission, enforced by lightweight topic classifier.

- **Engagement-level** defines domain boundary via domain tags from knowledge base
- **User-level** RBAC permission `scope.general_access` controls who can go off-topic
- **Classifier** checks against engagement domain tags, not a global blocklist
- Domain-appropriate content always allowed (adult retailer can discuss adult products)
- Off-topic requests logged for customer admin transparency
- Policy options: "strict domain only" or "domain-first, general allowed"

---

## C3-2: Multi-Product Pipeline

**Decision:** Hybrid — separate ingestion, unified retrieval.

- **Ingestion** is separate per product (different connectors, chunking strategies)
- **Retrieval** is unified with scope filtering via product tags
- Default search scoped to current product
- Cross-product search available with appropriate permissions
- Leverages scope tag inheritance chain (C2-2) and embeddings-only retrieval (Decision #9)

---

## C3-3: Products Without APIs

**Decision:** Unified connector adapter pattern (Option D).

All ingestion modes flow through the same connector interface:
1. **API pull** — real connectors for products with APIs (OData, REST, etc.)
2. **File watch/drop** — scheduled polling of watched folders (expected heaviest use)
3. **Manual upload** — user drags files in

All connector types produce the same output: chunks ready for embedding. The pipeline doesn't care how data arrived.

---
**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/gates/gate-two/decisions-cluster3.md
