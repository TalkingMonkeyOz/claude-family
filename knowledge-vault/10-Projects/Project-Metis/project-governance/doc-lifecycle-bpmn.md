---
projects:
  - Project-Metis
  - claude-family
tags:
  - bpmn
  - documentation
  - lifecycle
  - enforcement
---

# BPMN Process: P4 Documentation Lifecycle

Extends [[build-tracking-bpmn]] with mandatory documentation. Linked to build tracking status gates — features cannot advance without required docs.

## Hierarchy Position

```
L2_build_tracking
  ├── P1: Build Planning
  ├── P2: Build Execution
  ├── P3: Build Compliance
  └── P4: Documentation Lifecycle  ← THIS
```

---

## Lanes

| Lane | Actor | Role |
|------|-------|------|
| Author Claude | Claude instance doing the work | Drafts docs from context |
| Reviewer | Human (John) or designated Claude | Reviews, approves, requests changes |
| System | MCP tools + advance_status() | Enforces gates, validates structure, logs events |

---

## Doc States (per document)

```
draft → reviewed → approved → [superseded]
```

Tracked in `plan_data.docs` per document:
```json
{
  "docs": {
    "problem": {"path": "vault/.../problem.md", "status": "approved"},
    "solution": {"path": "vault/.../solution.md", "status": "draft"},
    "implementation": null
  }
}
```

---

## Required Docs by Feature Level

| Level | Doc Type | Required Before | Template |
|-------|----------|----------------|----------|
| **Stream** | Vision & Scope | `draft → planned` | [[doc-templates#vision]] |
| **Stream** | Architecture Overview | `draft → planned` | [[doc-templates#architecture]] |
| **Feature** | Problem Statement | `planned → in_progress` | [[doc-templates#problem]] |
| **Feature** | Proposed Solution | `planned → in_progress` | [[doc-templates#solution]] |
| **Feature** | Implementation Notes | `in_progress → completed` | [[doc-templates#implementation]] |

Small one-task features: combined problem+solution in single file accepted.

---

## Main Flow: Doc Creation & Approval

```
[Trigger: Feature created or status advance requires doc]
  │
  ▼
[Author: create_feature_doc(feature_id, doc_type)]
  │ System: creates vault file from template
  │ System: links in plan_data.docs with status='draft'
  │ Event: work_event(doc_updated, {doc_type, status: 'draft'})
  ▼
[Author: Draft content]
  │ Sources: recall_memories(), unstash(), existing vault docs
  │ Claude drafts from existing context — low manual effort
  ▼
[Author: Submit for review]
  │ Tool: update_doc_status(feature_id, doc_type, 'reviewed')
  │ If human review required: send_message(human, "Doc ready for review")
  ▼
[Reviewer: Review doc]
  │
  ▼
◆ Approved?
  ├── YES → [System: update_doc_status → 'approved']
  │         Event: work_event(doc_updated, {status: 'approved'})
  │
  ├── CHANGES NEEDED → [Reviewer: Add feedback via note]
  │         → [Author: Revise] → resubmit (loop)
  │
  └── REJECTED → [System: status stays 'draft', reason logged]
                  Event: work_event(doc_updated, {status: 'draft', reason})
```

## Status Gate Enforcement

```
[Trigger: advance_status(feature, new_status) called]
  │
  ▼
[System: Check required docs for this transition]
  │ Look up: feature_type + target_status → required doc types
  ▼
[System: For each required doc:]
  │ ✓ Does plan_data.docs.{type} exist?
  │ ✓ Is doc status ≥ 'approved'? (or 'reviewed' for fast-track)
  │ ✓ Does vault file exist at the path?
  │ ✓ Does file contain required sections? (template validation)
  ▼
◆ All checks pass?
  ├── YES → [Advance status] → continue
  └── NO  → [BLOCK with specific message]
            "Cannot advance F42 to in_progress. Missing/unapproved docs:
             - solution: not found (create via create_feature_doc)
             - problem: status='draft' (needs approval)"
```

## Doc Update Flow (Plan Changes Mid-Build)

```
[Trigger: work_event(plan_updated) on a feature]
  │
  ▼
[System: Flag linked docs for review]
  │ Set affected doc statuses → 'draft' (needs re-review)
  │ Event: work_event(doc_updated, {reason: 'plan changed, needs re-review'})
  ▼
[Author: Update docs to reflect changes]
  │ Vault file updated, version incremented
  ▼
[Re-enter approval flow]
```

## Doc Versioning Strategy

| Layer | What It Tracks | How |
|-------|---------------|-----|
| **Content** | Actual text changes | Git (vault is in git repo) |
| **Metadata** | Status, linked feature, doc type | plan_data.docs JSONB |
| **Audit** | When changed, by whom, why | work_events (type='doc_updated') |
| **Self-tracking** | Version number | Vault file footer (Version: X.Y) |

---

## Gap Analysis

| # | Gap | Resolution |
|---|-----|-----------|
| G11 | Doc exists but has no substance | Template validation: check required sections present. Minimum content length per section. |
| G12 | Feature too small for full docs | One-task features accept combined problem+solution file. advance_status checks for either separate OR combined. |
| G13 | Docs drift after plan changes | plan_updated event auto-resets affected doc statuses to 'draft'. Forces re-review. |
| G14 | Retroactive docs for existing work | Migration task: Claude auto-generates from vault content when features created for existing streams. |
| G15 | Multiple Claudes editing same doc | Docs linked to features; one Claude per feature at a time (via start_work lock). |
| G16 | Doc approval bottleneck | Fast-track: 'reviewed' status sufficient for non-critical features. 'approved' required for streams. |

---
**Version**: 1.0
**Created**: 2026-03-16
**Updated**: 2026-03-16
**Location**: knowledge-vault/10-Projects/Project-Metis/project-governance/doc-lifecycle-bpmn.md
