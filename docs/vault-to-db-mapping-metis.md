# Vault-to-DB Mapping: project-metis

Parent: [vault-to-db-mapping.md](vault-to-db-mapping.md)

## DB Knowledge (15 entries, confidence 85-90)

| Title | Type |
|-------|------|
| METIS Security Architecture -- 12 validated decisions | fact |
| METIS scope reframe -- domain-agnostic platform | learned |
| METIS Gate Framework -- 5 gates, 31 deliverables | procedure |
| Port 3100 is firewalled on Oracle ARM -- use SSH tunnel | learned |
| Oracle ARM server deploy path is /home/ubuntu/metis/ | learned |
| Metis gates and project phases are orthogonal | learned |
| The document-code parallel is a key METIS differentiator | learned |
| METIS has no designed interaction layer yet | learned |
| Build board task completion can diverge from actual state | learned |
| Apache AGE rejected for code symbol graphs | learned |
| Code ingestion should be sub-process of P1 Knowledge Ingestion | learned |
| PM2 ecosystem.config.cjs must use .cjs extension | learned |
| METIS was much further deployed than build board indicated | learned |

## Entities (20+ entries)

**Decisions**: Infrastructure is platform-agnostic, Build from zero, Generic framing with nimbus as lead example, Use area-level features as structure

**Gate deliverables**: Data Model Master Index, Problem Statement, BPMN Process Models, Decision Models (DMN), Data Model, Tech Stack, Security & Access Model, Process Inventory, Integration Points, DMN Decision Tables

**Design documents**: Security Architecture, Gate 2 Decisions Clusters 2/3/4/5-6, Gate 2 Decisions Summary

## Workfiles (10 active)

| Component | Title |
|-----------|-------|
| metis-active | build-board-navigator |
| gate-1-review | review progress |
| session-handoff | handoff-2026-03-29 (and 7 more handoffs) |

## Vault Topics with NO DB Equivalent (140+ files total)

**Design/architecture** (vault-only):
- ethos.md, feature-catalogue.md, system-product-definition.md
- plan-of-attack.md + phase0/1/2
- executive-proposal-brief.md
- coding-intelligence-design.md + competitive analysis
- knowledge-engine/ (3 files) -- knowledge graph design
- integration-hub/ (2 files) -- connector design
- orchestration-infra/ (6 files) -- agent conventions/architecture
- project-governance/ (8 files) -- build tracking BPMN
- bpmn-maps/ (3 files), bpmn-sop-enforcement/ (3 files)
- ps-accelerator/ (2 files), quality-compliance/ (2 files)
- support-defect-intel/, commercial/
- research/ (6 files) -- augmentation layer, code analysis, filing research
- project-history.md, gates/design-lifecycle.md

**With DB equivalents**:
- gates/gate-zero/ (4 files) -- matched by gate_deliverable entities
- gates/gate-one/ (5 files) -- matched by gate_deliverable entities
- gates/gate-two/ (20+ files) -- matched by gate_deliverable + design_document entities
- security-architecture.md -- matched in both knowledge and entities
- _archive/ (90+ files) -- historical, not expected in DB

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/vault-to-db-mapping-metis.md
