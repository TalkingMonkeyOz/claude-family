---
tags:
  - procedure
  - design
  - conventions
projects:
  - claude-family
  - metis
---

# Design Capture Conventions

Behavioral guidance for capturing design concepts during brainstorm sessions. Applies to Claude Desktop (primary brainstorm environment) but any Claude instance can follow these conventions.

## 1. When to Capture

**CAPTURE** these during brainstorms:

| Type | Prefix | Example |
|------|--------|---------|
| Decisions | `DECIDED:` | "Auth uses JWT + RBAC" |
| Assumptions | `ASSUMED:` | "Jira is not required long-term" |
| Dependencies | `DEPENDS:` | "Delivery Accelerator needs Knowledge Engine API" |
| Constraints | `CONSTRAINT:` | "Australian data residency required" |
| Principles | `PRINCIPLE:` | "Build for nimbus first, generalise second" |
| Requirements | `REQUIRED:` | "Every alert must provide information for action" |

**SKIP** these:

- Background context and motivation paragraphs
- Examples and illustrations (unless they contain implicit decisions)
- Future/aspirational features marked Phase 3+ or "later"
- Meeting logistics and session management notes
- Restating what the user just said without adding a decision

## 2. How to Capture

Use `remember()` with structured content and area tag:

```
remember(
    "DECIDED: Auth uses JWT + RBAC for all API endpoints. Area: Orchestration. Type: decision.",
    memory_type="decision"
)
```

**Format**: `PREFIX: Description. Area: AreaName. Type: concept_type.`

Valid concept types: `decision`, `assumption`, `requirement`, `dependency`, `principle`, `constraint`

The `Area:` and `Type:` tags are parsed by `generate_design_map.py` and the Design Coherence skill for cross-referencing. Always include them.

## 3. Pacing

- **Target**: 3-8 concepts per brainstorm session
- **Too few** (< 3 from a substantive session): You're skipping important decisions
- **Too many** (> 15): You're too granular — consolidate related items
- **Don't interrupt flow**: Batch captures at natural pauses, not after every sentence

## 4. Quality Check

At the end of each brainstorm session, review what was captured:

```
recall_memories("design concept", query_type="task_specific")
```

Ask yourself:
- Did I capture the key decisions that were made?
- Are there dependencies between areas that I missed?
- Would another Claude session understand the design state from these entries?

## 5. Session Tracking

Track capture progress with a session fact:

```
store_session_fact(
    "design_capture_count",
    "5 concepts captured: 3 decisions, 1 assumption, 1 dependency. Area: Knowledge Engine.",
    "data"
)
```

This helps the next session know what was covered and what might be missing.

## 6. Area Names (Project Metis)

Use these canonical area names for consistency:

| Area | Scope |
|------|-------|
| Knowledge Engine | Semantic search, embeddings, knowledge graph |
| Orchestration | Agent coordination, Azure infra, Claude API |
| Integration Hub | Connectors (Jira, SF, Git), data ingestion |
| BPMN & SOP Enforcement | Process modeling, validation, compliance |
| Quality & Compliance | Testing, audit trails, release gates |
| Project Governance | PM lifecycle, client tracking, timelines |
| Delivery Accelerator | Config generation, deployment automation |
| Support & Defect Intel | Ticket analysis, pattern detection |
| Commercial | Pricing, packaging, Monash model |

Other projects should define their own area names in a similar table.

## Reference

- **Design Coherence Skill**: [[Design Coherence SKILL|SKILL.md]] — the 5-phase cross-referencing process
- **Design Map Generator**: `scripts/generate_design_map.py` — renders captured concepts into a compressed map
- **Vault Validator**: `scripts/validate_vault.py` — structural checks on vault files

---

**Version**: 1.0
**Created**: 2026-03-01
**Updated**: 2026-03-01
**Location**: knowledge-vault/40-Procedures/Design Capture Conventions.md
