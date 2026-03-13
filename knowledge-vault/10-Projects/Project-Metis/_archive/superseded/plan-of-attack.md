---
tags:
  - project/Project-Metis
  - scope/system
  - type/build-plan
created: 2026-02-26
updated: 2026-02-26
---

# METIS Plan of Attack

Build sequence, dependencies, MVP definition, and timeline.

## Phase 0: Foundation (~1.5 weeks)

Infrastructure — no features work without it.

| Deliverable | Effort | Dependency |
|---|---|---|
| PostgreSQL + pgvector on Azure Australia East | 1-2 days | Azure access (mgmt decision) |
| Core schema: organisations, products, clients, knowledge_items, knowledge_relations, sessions, work_items, audit_log, connector_configs, jobs | 2-3 days | Database running |
| Git repo (Azure DevOps) + CI basics | 1 day | DevOps access |
| Auth layer (JWT + simple RBAC) | 2-3 days | Schema deployed |
| Agent conventions (CLAUDE.md, core protocol) | 1 day | — |
| Project structure + coding conventions | 1 day | Git repo |

**Exit criteria:** Authenticate, query database, push code, agents follow conventions.

## Phase 1: Knowledge Engine + Integration Layer (~4-6 weeks)

The brain and the hands. Features 1, 2, 10 (basic).

| Deliverable | Effort | Dependency | Feature |
|---|---|---|---|
| Embedding provider interface + Voyage AI | 2-3 days | Phase 0 | — |
| Knowledge ingestion pipeline (/ingest, /ingest/batch) | 3-4 days | Embeddings | F2 |
| Knowledge search (/search — vector + graph walk) | 3-4 days | Ingestion, GAP-1 | F1 partial |
| Knowledge ask (/ask — LLM answers) | 3-4 days | Search | F1 |
| time2work REST API connector | 3-5 days | Phase 0, GAP-2 pattern | — |
| time2work OData connector | 2-3 days | REST connector | — |
| First knowledge load (Swagger + OData metadata) | 2-3 days | Ingestion + connectors | F1 useful |
| Evaluation framework (50 questions + scoring) | 3-4 days | /ask working | GAP-4 |
| Constrained deployment v1 (system prompt + cache) | 2-3 days | /ask + knowledge loaded | F10 basic |
| Basic web UI (chat for /ask) | 3-5 days | /ask endpoint | F1 UI |
| Audit logging | 2-3 days | Throughout | — |

**Exit criteria:** Ask time2work question → get correct, cited answer. Eval framework running. First constrained deployment working.

## Phase 2: First Customer + Engagement (~6-8 weeks) — MVP MILESTONE

Prove real value. Features 3-7, Monash POC.

| Deliverable | Effort | Dependency | Feature |
|---|---|---|---|
| Engagement creation + client isolation | 3-4 days | Phase 1 schema | F3 |
| Delivery pipeline (BPMN process #2) | 5-7 days | Phase 1 + SpiffWorkflow | F3 pipeline |
| Monash knowledge ingestion (EAs, configs) | 3-5 days | Phase 1 ingestion | F1 Monash |
| Configuration generation from requirements | 5-7 days | KE + connector + pipeline | F4 |
| Pay scenario test generation + validation | 5-7 days | Config gen + API write access | F5 |
| Defect triage workflow (BPMN process #3) | 3-4 days | Phase 1 + Jira connector | F6 |
| Jira connector (enhanced) | 3-4 days | GAP-2 pattern, Jira MCP | F6 |
| Documentation generation | 4-5 days | Config + test results | F7 |
| Knowledge validation workflow (BPMN process #1) | 3-4 days | Phase 1 ingestion | F2 governed |
| Constrained deployment for Monash | 2-3 days | Phase 1 + Monash knowledge | F10 Monash |

**Exit criteria:** Monash running through delivery pipeline. Config generated, tested, documented automatically. Stakeholders see measurable time savings.

## Phase 3: Hardening + Remaining Features (~4-6 weeks)

| Deliverable | Effort | Feature |
|---|---|---|
| Project health dashboard | 5-7 days | F8 |
| Knowledge promotion workflow | 3-4 days | F9 |
| Multi-client isolation testing | 3-5 days | Hardening |
| Full RBAC | 3-5 days | Hardening |
| Background job scheduler (GAP-9) | 2-3 days | Scheduled analysis |
| Performance + resilience testing | 3-5 days | Hardening |
| Second client onboarding | Varies | Validates reusability |

**Exit criteria:** All 10 features working. Multi-tenant proven. Ready for customer #2.

## MVP Definition

The minimum that proves value to nimbus management and Monash:

1. ✅ Knowledge Engine answering time2work questions correctly (F1)
2. ✅ One constrained deployment working (F10)
3. ✅ Config generation + validation for Monash (F4 + F5)
4. ✅ Documentation generated from system state (F7)

**The demo:** "An AI that knows time2work, generates configs from requirements, tests them automatically, produces audit-ready docs. 2 hours instead of 2 weeks."

## Timeline Summary

| Phase | Duration | Cumulative | Features Working |
|---|---|---|---|
| Phase 0 | 1.5 weeks | 1.5 weeks | Infrastructure only |
| Phase 1 | 4-6 weeks | 5.5-7.5 weeks | F1, F2, F10 basic |
| Phase 2 (MVP) | 6-8 weeks | 11.5-15.5 weeks | F1-F7, F10 — 7 of 10 |
| Phase 3 | 4-6 weeks | 15.5-21.5 weeks | All 10 features |

**Realistic total: ~4-5 months. MVP at ~3 months.**

## Current Blockers (Management Decisions)

| Decision | Impact | From |
|---|---|---|
| Monash POC go-ahead | Gates Phase 2 | Master Tracker |
| Azure access (isolated resource group) | Gates Phase 0 | Master Tracker |
| time2work API access for Monash | Gates Phase 1 connectors | Master Tracker |
| Internal sponsor beyond John | Political, not technical | Master Tracker |

Until resolved: local development (Phase 0 setup, schema, conventions) can proceed but can't connect to anything real.

## 3 BPMN Processes for MVP (GAP-7)

1. **Knowledge ingestion & validation** — new knowledge → tiered validation → searchable
2. **Delivery pipeline stage gate** — requirements → config → test → deploy (human checkpoint per stage)
3. **Defect triage** — new defect → classify → duplicate check → assign

---
*Created: 2026-02-26*
