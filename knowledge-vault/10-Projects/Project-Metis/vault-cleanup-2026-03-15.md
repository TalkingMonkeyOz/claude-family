---
projects:
  - Project-Metis
tags:
  - type/audit
  - type/quality
  - project/metis
created: 2026-03-15
updated: 2026-03-15
---

# METIS Vault Quality Audit — 2026-03-15

**Scope**: 119 active `.md` files (excluding `_archive/`)
**Audited by**: Claude Sonnet 4.6 (automated scan)

---

## Quality Scores

| Dimension | Score | Detail |
|-----------|-------|--------|
| YAML Frontmatter (projects/tags) | **good** | All 119 files have `projects:` and `tags:` fields |
| Version Footers | **poor** | 44 of 119 files (37%) missing `**Version**:` footer |
| Cross-references (wiki-links) | **good** | Links use `[[...]]` syntax correctly; no obviously broken targets found |
| File Naming | **needs-work** | 4 misplaced root-level files; 1 file missing `---` frontmatter entirely |
| Folder Structure | **needs-work** | `orchestration-infra/` (15 files), `research/` (23 files) exceed 10-file subfolder threshold |
| Duplicate Content | **needs-work** | `plan-of-attack.md` and `plan-of-attack-rewrite-brief.md` coexist — brief says plan is unvalidated but plan is dated 2026-03-15 |
| Stale Content | **needs-work** | `azure-infrastructure-recommendation.md` contradicts Decision 6 (platform-agnostic); several `orchestration-infra/` files pre-date Gate Zero |

---

## Files Requiring Attention (Top 20)

### Critical — Stale / Contradicts Validated Decisions

1. `orchestration-infra/azure-infrastructure-recommendation.md`
   - **Issue**: Recommends Azure-specific infrastructure (VMs, pricing, resource groups). Decision 6 is "platform-agnostic infrastructure — no Azure specifics."
   - **Action**: Move to `_archive/superseded/` or rewrite as generic cloud sizing guide.

2. `plan-of-attack.md` vs `plan-of-attack-rewrite-brief.md`
   - **Issue**: The rewrite-brief supersedes the original plan but both live side-by-side. The current `plan-of-attack.md` was updated 2026-03-15 — unclear if the rewrite has been applied.
   - **Action**: Confirm if rewrite is done. If yes, archive the brief. If not, add a WARNING banner to `plan-of-attack.md`.

3. `orchestration-infra/phase-0-task-list.md`
   - **Issue**: Written 2026-02-24 (pre-Gate Zero). Phase 0 tasks may not reflect current gate framework.
   - **Action**: Review against `gates/design-lifecycle.md` and update or archive.

### High — Missing Version Footers (44 files total, representative list)

4. `ethos.md` — Core document, no standard footer (has non-standard `*Gate Zero Doc 5 | Created: 2026-03-06*`)
5. `feature-catalogue.md` — Key reference, no footer
6. `security-architecture.md` — Critical document, no standard footer
7. `system-product-definition.md` — Core v0.3 doc, no footer
8. `plan-of-attack-rewrite-brief.md` — Has `created:/updated:` in FM but no footer block
9. All 15 `orchestration-infra/*.md` files — none have version footers
10. All 3 `knowledge-engine/*.md` files — none have version footers
11. All 2 `integration-hub/*.md` files — none have version footers
12. All 3 `bpmn-sop-enforcement/*.md` files — none have version footers
13. `session-handoffs/2026-03-14-context-hygiene-handoff.md` — no footer

### Medium — Misplaced Files (wrong folder)

14. `bpmn-coverage-audit-2026-03-14-detail.md` — Audit file at vault root; should be in `audits/` (folder exists but is empty)
15. `project-tools-functional-test-2026-03-14.md` — Test/functional file at vault root; should be in `audits/`
16. `project-tools-functional-test-detail-2026-03-14.md` — Same issue
17. `CATALOG_EXPORT.md` — Generated export file at vault root; should be in `audits/` or deleted if transient
18. `skills/session-manager-update-patch.md` — A patch instruction file, not a skill; should go to `_archive/` or be applied and deleted

### Medium — Folder Structure (exceeds 10-file threshold)

19. `research/` — 23 files. Suggested subfolders: `schema/` (12 schema-* files), `impl-audit/` (6 impl-audit-* files), `background/` (5 research docs)
20. `orchestration-infra/` — 15 files. Suggested subfolders: `decisions/` (infra-decisions-*, dev-decisions-*), `specs/` (cicd-*, monitoring-*, agent-*)

---

## Recommended Actions (Prioritised)

### P1 — Do First (Correctness)
- [ ] Archive or rewrite `azure-infrastructure-recommendation.md` — violates Decision 6
- [ ] Clarify `plan-of-attack.md` status — add WARNING or confirm rewrite complete
- [ ] Move 4 root-level misplaced files to `audits/`

### P2 — Do Next (Standards Compliance)
- [ ] Add version footers to `ethos.md`, `feature-catalogue.md`, `security-architecture.md`, `system-product-definition.md` (4 core docs)
- [ ] Add version footers to all 15 `orchestration-infra/` files
- [ ] Add version footers to `knowledge-engine/`, `integration-hub/`, `bpmn-sop-enforcement/` (8 files)

### P3 — Do When Convenient (Structure)
- [ ] Split `research/` into `schema/`, `impl-audit/`, `background/` subfolders
- [ ] Split `orchestration-infra/` into `decisions/` and `specs/` subfolders
- [ ] Review `phase-0-task-list.md` for currency; archive if superseded
- [ ] Apply or delete `skills/session-manager-update-patch.md`

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total active files | 119 |
| Files with YAML frontmatter | 119 (100%) |
| Files with version footer | 75 (63%) |
| Files missing version footer | 44 (37%) |
| Files misplaced (wrong folder) | 4 |
| Folders exceeding 10-file threshold | 2 |
| Files with stale/contradicted content | 2-3 |

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: knowledge-vault/10-Projects/Project-Metis/vault-cleanup-2026-03-15.md
