---
projects:
  - Project-Metis
tags:
  - type/audit
created: 2026-03-15
updated: 2026-03-15
---

# METIS Vault Audit — 2026-03-15

**Scope**: All files under `knowledge-vault/10-Projects/Project-Metis/`
**Total files**: ~160 (120 .md active, 40+ archived)
**Audit goal**: Catalogue, identify superseded files, surface gaps, recommend cleanup.

---

## Summary Counts

| Location | Files | Notes |
|----------|-------|-------|
| `gates/gate-two/` | 20 | All 12 deliverables + 4 decision docs + README (today, 2026-03-15) |
| `_archive/session-handoffs/` | 55 | All pre-2026-03-14; correctly archived |
| `_archive/audits/` | 16 | Correctly archived |
| `_archive/superseded/` | 5 | Correctly archived |
| `_archive/handoffs/` | 4 | Correctly archived |
| `session-handoffs/` (active) | 2 | Correct — only current handoffs |
| `research/` | 23 | Mix: 10 schema audits + 6 impl audits + 7 domain research |
| `orchestration-infra/` | 15 | Pre-Gate-2; mostly superseded by deliverables |
| `wcc/` | 5 | Superseded by Gate 2 deliverables 3 and 5 |
| `data-model/` | 2 | Superseded by Gate 2 deliverable 5 |
| `knowledge-engine/` | 3 | Partially superseded by Gate 2 deliverables 1, 3 |
| Root-level | ~20 | Mix: active (system-product-definition, ethos, feature-catalogue) and candidates |

---

## File Inventory — Active Area (Non-Archive)

### Root Level

| File | Lines | Last Modified | YAML | Status |
|------|-------|---------------|------|--------|
| `README.md` | 143 | 2026-03-14 | Yes | Active |
| `CATALOG_EXPORT.md` | 77 | 2026-03-14 | Yes | Active (generated) |
| `system-product-definition.md` | 300 | 2026-03-12 | Yes | Active — core reference |
| `feature-catalogue.md` | 218 | 2026-03-07 | Yes | Active — core reference |
| `security-architecture.md` | 276 | 2026-03-08 | Yes | Partial overlap with deliverable-08 |
| `ethos.md` | 34 | 2026-03-14 | Yes | Active — core reference |
| `plan-of-attack.md` | 229 | 2026-03-15 | Yes | Active — rewritten today |
| `plan-of-attack-phase0.md` | 125 | 2026-03-15 | Yes | Active |
| `plan-of-attack-phase1.md` | 210 | 2026-03-15 | Yes | Active |
| `plan-of-attack-phase2.md` | 216 | 2026-03-15 | Yes | Active |
| `plan-of-attack-rewrite-brief.md` | 132 | 2026-03-12 | Yes | Archive candidate — brief served its purpose |
| `bpmn-coverage-audit-2026-03-14-detail.md` | 94 | 2026-03-14 | Yes | Archive candidate — temporal audit |
| `project-tools-functional-test-2026-03-14.md` | 71 | 2026-03-14 | Yes | Archive candidate — temporal test |
| `project-tools-functional-test-detail-2026-03-14.md` | 164 | 2026-03-14 | Yes | Archive candidate — temporal test |

### Gates

| File | Lines | Last Modified | YAML | Status |
|------|-------|---------------|------|--------|
| `gates/design-lifecycle.md` | 253 | 2026-03-15 | Yes | Active — master tracker |
| `gates/gate-zero/*.md` (4 files) | 58-234 | 2026-03-11/12 | Yes | Active — validated Gate 0 |
| `gates/gate-one/*.md` (5 files) | 118-206 | 2026-03-11 | Yes | Active — draft Gate 1 (pending human review) |
| `gates/gate-two/README.md` | 88 | 2026-03-15 | Yes | Active |
| `gates/gate-two/deliverable-01 to 12` | 98-291 | 2026-03-15 | Yes | Active — all 12 complete (design) |
| `gates/gate-two/decisions-*.md` (5 files) | 64-120 | 2026-03-15 | Yes | Active |
| `gates/gate-three/README.md` | 71 | 2026-03-11 | Yes | Active — placeholder |

### Research

| File | Lines | Last Modified | YAML | Status |
|------|-------|---------------|------|--------|
| `research/augmentation-layer-research.md` | 200 | 2026-03-08 | Yes | Active — foundational, not yet superseded |
| `research/library-science-research.md` | 831 | 2026-03-10 | Yes | Active — exceeds 300-line limit; split candidate |
| `research/filing-records-management-research.md` | 664 | 2026-03-10 | Yes | Active — exceeds 300-line limit; split candidate |
| `research/work-context-container-options.md` | 183 | 2026-03-10 | Yes | Superseded by Gate 2 D3/D5 |
| `research/work-context-container-synthesis.md` | 136 | 2026-03-10 | Yes | Superseded by Gate 2 D3/D5 |
| `research/schema-*.md` (9 files) | 107-182 | 2026-03-11 | Yes | Superseded by Gate 2 D5 (data model) |
| `research/impl-audit-*.md` (6 files) | 48-179 | 2026-03-11 | Yes | Archive candidate — CF audit work, not METIS design |
| `research/schema-assessment-gaps.md` | 152 | 2026-03-11 | Yes | Superseded by Gate 2 D5 |

### Orchestration-Infra (All dated 2026-02-25)

| File | Lines | Status |
|------|-------|--------|
| `azure-infrastructure-recommendation.md` | 138 | Superseded by deliverable-11 (deployment) |
| `monitoring-alerting-design.md` | 149 | Superseded by deliverable-12 (monitoring) |
| `cicd-pipeline-spec.md` | 87 | Superseded by deliverable-11 |
| `session-memory-context-persistence.md` | 544 | Superseded by deliverable-05 + D3; exceeds limit |
| `dev-decisions-agents-workflow-handoff.md` | 273 | Superseded by deliverable-04 (DMN) + D6 (tech stack) |
| `infra-decisions-api-git-auth.md` | 194 | Superseded by deliverable-07 (API) + D6 |
| `agent-conventions.md` | 162 | Partially superseded by deliverable-01 (BPMN), D3 |
| `agent-compliance-drift-management.md` | 165 | Partially superseded by deliverable-08 (security) |
| `autonomous-operations.md` | 90 | Superseded by deliverable-01 BPMN processes |
| `phase-0-task-list.md` | 304 | Superseded by plan-of-attack-phase0.md; exceeds limit |
| `day-1-readiness.md` | 83 | Superseded by plan-of-attack |
| `user-experience.md` | 67 | Superseded by deliverable-10 (journey maps) |
| `claude-md-template.md` | 208 | Active — operational template for Gate 3 |
| `claude-data-privacy-reference.md` | 101 | Active — reference doc |
| `README.md` | 202 | Update candidate — index is stale |

### WCC

| File | Lines | Status |
|------|-------|--------|
| `wcc/work-context-container-design.md` | 139 | Superseded by deliverable-03 domain model |
| `wcc/wcc-ranking-design.md` | 168 | Superseded by deliverable-04 DMN + D3 |
| `wcc/wcc-ranking-agentic-routing.md` | 181 | Superseded by deliverable-01 BPMN |
| `wcc/wcc-activity-space-design.md` | 232 | Superseded by deliverable-03 + D5 |
| `wcc/wcc-mechanics-feedback-design.md` | 214 | Superseded by deliverable-03 + D9 (test strategy) |

### Data Model

| File | Lines | Status |
|------|-------|--------|
| `data-model/data-model-prototype-and-gaps.md` | 108 | Superseded by deliverable-05 |
| `data-model/data-model-table-assessments.md` | 110 | Superseded by deliverable-05 |

### Knowledge Engine

| File | Lines | Status |
|------|-------|--------|
| `knowledge-engine/brainstorm-knowledge-engine-deep-dive.md` | 560 | Partially superseded by D1/D3; source brainstorm — keep for traceability |
| `knowledge-engine/knowledge-graph-relationships.md` | 179 | Partially superseded by D3 domain model |
| `knowledge-engine/README.md` | 140 | Stale — predates Gate 2 design |

### Other Folders

| Folder | Files | Status |
|--------|-------|--------|
| `bpmn-maps/` | 3 | Active — process maps; D1 is the formal deliverable |
| `bpmn-sop-enforcement/` | 3 | Partially superseded by D1 BPMN; brainstorm file still useful |
| `decisions/README.md` | 155 | Stale — predates gate-two/decisions-* cluster docs |
| `integration-hub/` | 2 | Partially superseded by D7 (API) |
| `commercial/README.md` | 126 | Active — not in Gate 2 deliverables |
| `project-governance/` | 3 | Active — PM lifecycle, not superseded |
| `ps-accelerator/` | 2 | Active — area brainstorm |
| `quality-compliance/` | 2 | Active — area brainstorm |
| `support-defect-intel/README.md` | 137 | Active — area brainstorm |
| `skills/` | 4 | Active — operational skills |
| `session-handoffs/` | 2 | Active — current session handoffs only |

---

## Superseded Files (Recommend Move to `_archive/superseded/`)

| File | Superseded By |
|------|--------------|
| `research/work-context-container-options.md` | Gate 2 D3 + D5 |
| `research/work-context-container-synthesis.md` | Gate 2 D3 + D5 |
| `research/schema-*.md` (9 files) | Gate 2 D5 (data model) |
| `data-model/data-model-prototype-and-gaps.md` | Gate 2 D5 |
| `data-model/data-model-table-assessments.md` | Gate 2 D5 |
| `wcc/*.md` (5 files) | Gate 2 D3, D4, D5 |
| `orchestration-infra/azure-infrastructure-recommendation.md` | Gate 2 D11 |
| `orchestration-infra/monitoring-alerting-design.md` | Gate 2 D12 |
| `orchestration-infra/cicd-pipeline-spec.md` | Gate 2 D11 |
| `orchestration-infra/session-memory-context-persistence.md` | Gate 2 D3, D5 |
| `orchestration-infra/dev-decisions-agents-workflow-handoff.md` | Gate 2 D4, D6 |
| `orchestration-infra/infra-decisions-api-git-auth.md` | Gate 2 D7, D6 |
| `orchestration-infra/autonomous-operations.md` | Gate 2 D1 |
| `orchestration-infra/user-experience.md` | Gate 2 D10 |
| `orchestration-infra/phase-0-task-list.md` | plan-of-attack-phase0.md |
| `orchestration-infra/day-1-readiness.md` | plan-of-attack |
| `decisions/README.md` | gate-two/decisions-*.md |

## Archive Candidates (Temporal / One-Off Docs)

| File | Reason |
|------|--------|
| `plan-of-attack-rewrite-brief.md` | Brief executed; superseded by plan-of-attack.md |
| `bpmn-coverage-audit-2026-03-14-detail.md` | Temporal audit; outcome absorbed |
| `project-tools-functional-test-2026-03-14.md` | Test run, not design knowledge |
| `project-tools-functional-test-detail-2026-03-14.md` | Test run, not design knowledge |
| `research/impl-audit-*.md` (6 files) | CF audit of Claude Family, not METIS design |

---

## Files Exceeding 300-Line Limit

| File | Lines | Action |
|------|-------|--------|
| `research/library-science-research.md` | 831 | Split into 3 linked docs |
| `research/filing-records-management-research.md` | 664 | Split into 2 linked docs |
| `knowledge-engine/brainstorm-knowledge-engine-deep-dive.md` | 560 | Archive (superseded) or split |
| `orchestration-infra/session-memory-context-persistence.md` | 544 | Archive (superseded) |
| `orchestration-infra/phase-0-task-list.md` | 304 | Archive (superseded) |
| `gates/gate-two/deliverable-01-bpmn-processes.md` | 291 | At limit — monitor |

---

## Knowledge Gaps (Gate 2 Topics Without Standalone Vault Docs)

| Gap | Where Covered | Gap Level |
|-----|--------------|-----------|
| Augmentation Layer architecture | Only in research/augmentation-layer-research.md + archived handoffs | High — needs a formal doc |
| Agent architecture (supervisor pattern) | Only in actor-map.md §2 and archived handoffs | High — referenced but not documented |
| Interaction Model (L1/L2/L3 constraints) | Only in archived handoff 2026-03-09 | High — no active vault doc |
| Knowledge Engine design (post-Gate-2) | knowledge-engine/README.md is stale | Medium — README needs update |
| WCC Option C (Smart Context Assembly) | wcc/ files superseded, replacement not fully in D3/D5 | Medium — transition doc needed |
| BPMN XML files | Only markdown descriptions exist | High — Gate 3 dependency but gap now |

---

## Session Handoffs Assessment

**Active** (`session-handoffs/`): 2 files, both dated 2026-03-14. The most recent (`2026-03-14-gate2-decisions-progress.md`) supersedes the earlier context hygiene handoff. Both are appropriate to keep. No redundancy issue.

**Archived** (`_archive/session-handoffs/`): 55 files spanning 2026-02-23 to 2026-03-13. All correctly archived. No active files mistakenly left here.

---

## _archive Assessment

Archive is being used correctly:
- `_archive/session-handoffs/` — historical handoffs, well-organised by date
- `_archive/audits/` — CF system audits; correctly separated
- `_archive/superseded/` — superseded planning docs
- `_archive/handoffs/` — inter-session context files from early work

No active files found in archive. No gaps in archiving practice.

---

## Cleanup Recommendations (Priority Order)

1. **Move 17 superseded files** to `_archive/superseded/` — keeps vault clean and searchable
2. **Move 10 archive candidates** (impl audits, temporal test files) to `_archive/`
3. **Split 2 oversized research files** (`library-science-research.md`, `filing-records-management-research.md`)
4. **Write 3 missing active docs**: Augmentation Layer Architecture, Agent Architecture, Interaction Model — these are Gate 2 design decisions with no active vault home
5. **Update stale READMEs**: `knowledge-engine/README.md`, `decisions/README.md`, `orchestration-infra/README.md`
6. **Consider archiving** `security-architecture.md` root file — deliverable-08 is the formal version; root file adds confusion

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/vault-audit-2026-03-15.md
