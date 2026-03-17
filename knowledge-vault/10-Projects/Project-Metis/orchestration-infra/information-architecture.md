---
projects:
  - Project-Metis
tags:
  - project/metis
  - pattern/information-architecture
  - type/design-document
created: 2026-03-16
updated: 2026-03-16
status: validated
---

# Information Architecture: Two-Layer Model

## Problem

AI agents consume project documentation to make decisions. When the same information exists in multiple locations (design docs, trackers, databases), it drifts — and AI agents build on false premises. Research confirms: "documentation lag creates AI assumptions that diverge from reality" (Digital Streams, 2026).

METIS has 5 storage systems (notepad, memory, filing cabinet, entity catalog, vault) plus a build board. Without crisp boundaries, Claude instances will be confused about which to query.

## Solution: Two Layers

### Layer 1 — Structured Systems (Current State)

Owns: what exists NOW, what's next, what's done, current decisions.

| System | Owns | Tool |
|--------|------|------|
| Build board | Execution state (tasks, status, deps, progress) | `get_build_board()` |
| Entity catalog | Validated decisions, deliverables, API specs | `recall_entities()` |
| Session notepad | Credentials, endpoints, session findings | `store_session_fact()` |
| Filing cabinet | Component working notes | `stash()`/`unstash()` |
| Memory | Patterns, gotchas, cross-session lessons | `remember()` |

### Layer 2 — Vault Documents (Historical Rationale)

Owns: WHY decisions were made, design thinking, risk assessments, stable reference material.

Vault docs **freeze after acceptance**. They are design artifacts — the "RFC." When implementation diverges, capture the divergence as a new decision in the entity catalog with a `supersedes` reference. Do NOT edit the frozen vault doc.

## The Authoritative Source Rule

> If data exists in both a structured system AND a vault doc, the structured system is authoritative for CURRENT STATE and the vault doc is authoritative for HISTORICAL RATIONALE.

This means:
- "What features are in Phase 1?" → Build board (not plan-of-attack.md)
- "Why did we choose separate DB per customer?" → Vault (plan-of-attack-rewrite-brief.md)
- "What's the current schema?" → DB / information_schema (not deliverable-05-data-model.md)
- "Why was the schema designed this way?" → Vault (deliverable-05-data-model.md)

## Routing Table

Deployed in CLAUDE.md. The routing table maps every data type to its authoritative system. Claude instances consult this BEFORE querying any system.

### Routing Rule: No Hardcoded Paths

CLAUDE.md must never contain hardcoded vault file paths — they break when files are reorganized. Instead:

| I need... | Route via |
|-----------|----------|
| Current execution state | Tool: `get_build_board()`, `get_work_context()` |
| A design document | Tool: `recall_entities("topic", entity_type="design_document")` |
| A gate deliverable | Tool: `recall_entities("topic", entity_type="gate_deliverable")` |
| A validated decision | Tool: `recall_entities("topic", entity_type="decision")` |
| An SOP or procedure | Wiki-link: `[[SOP Name]]` (RAG-discoverable) |
| A pattern or gotcha | Tool: `recall_memories("topic")` |

The entity catalog is the indirection layer. When a file moves, update the catalog entry — CLAUDE.md stays stable.

### Discoverability
- Loaded every session via CLAUDE.md (auto-loaded)
- Embedded in metis-build skill (loaded during build work)
- Stored as memory (recalled contextually via RAG)

### Versioning
- CLAUDE.md is DB-managed with version snapshots
- Updated via `update_claude_md()` when new data types emerge
- Each update logged in `audit_log`

### Security & Segmentation
- Tools enforce scope at query time (project, org, product, client, engagement params)
- Routing table is metadata about WHERE to look, not the data itself
- No security concern — it contains no sensitive data

## Errata Pattern (ADR-Inspired)

When implementation diverges from a design doc:

1. **Do NOT edit the vault doc** — it's frozen
2. **Catalog a new decision** via `catalog(type="decision")` with:
   - `supersedes_id` referencing the original decision
   - `rationale` explaining why the change was needed
3. **Update the build board** if tasks/deps changed
4. The entity catalog becomes the authoritative decision log

This follows the Apache Geode RFC pattern: "the existing body should remain immutable; changes are captured in Errata."

## Gate Documentation Requirement

Before any gate review:
1. All new decisions cataloged in entity catalog
2. All build tasks reflect current plan in build board
3. Vault design docs have frozen-reference headers if execution state has moved
4. Routing table in CLAUDE.md is current

This is a mandatory step in the gate lifecycle — not optional cleanup.

## References

- ADR (Architecture Decision Records): https://adr.github.io/
- Pragmatic Engineer on RFCs: https://newsletter.pragmaticengineer.com/p/rfcs-and-design-docs
- SYSTEM-STATE.md for AI: https://www.digital-streams.com/system-state-md-why-every-ai-assisted-project-needs-a-source-of-truth/
- Apache Geode RFC Process: https://cwiki.apache.org/confluence/display/GEODE/Lightweight+RFC+Process

---

**Version**: 1.1 (Added routing rule: no hardcoded vault paths in CLAUDE.md)
**Created**: 2026-03-16
**Updated**: 2026-03-17
**Location**: knowledge-vault/10-Projects/Project-Metis/orchestration-infra/information-architecture.md
