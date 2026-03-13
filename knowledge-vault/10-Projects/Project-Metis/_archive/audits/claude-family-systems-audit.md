---
projects:
- claude-family
- Project-Metis
tags:
- audit
- baseline
- systems-inventory
- enterprise
synced: false
---

# Claude Family Systems Audit - Project Metis Baseline

**Purpose**: Complete inventory and assessment of every Claude Family subsystem. Baseline for Project Metis enterprise solution design.

**Audit Date**: 2026-03-09 | **Scope**: All hooks, MCP tools, BPMN models, DB tables, knowledge systems, logging, skills, config, vault docs.

---

## Executive Summary

Claude Family is a custom infrastructure layer on Claude Code adding: session persistence, knowledge management (RAG), work tracking with state machines, BPMN process governance, inter-agent coordination, self-healing config, and enforcement hooks.

Built over ~5 months (Oct 2025 - Mar 2026): **58 DB tables, ~72 MCP tools, 76 BPMN processes, 11 hook scripts, 16 skills, 24 slash commands**.

### Health Dashboard

| Area | Health | Working | Broken/Stale | Critical Issue |
|------|--------|---------|-------------|----------------|
| Hook System | Good | 8/11 | 3 plugin validators dead | session_end fact promotion bug |
| MCP Tools | Good | ~68/72 | 4 unused | server.py/v2 split; BPMN sync broken |
| Knowledge/RAG | Good | Core working | 43 stale vault docs | No aggregate token cap |
| Database | Good | 55/58 tables | 3 empty, 43 stale registry | 52 orphaned sessions |
| BPMN Models | Good | 76 processes | sync script broken | alignment covers only 8 processes |
| Skills | Mixed | 10/16 | 6 stale | orchestrator refs; invalid status values |
| Commands | Poor | 16/24 | 6 severely broken | session-start/end use retired schemas |
| Logging | Mixed | 5/7 | subagent broken | no fallback replay; no log rotation |
| Vault Docs | Mixed | ~247/290 | ~43 deprecated refs | Family Rules lists retired orchestrator |

### What Works Well (Preserve for Metis)

1. Hook-based context injection — proven LLM behavior shaping
2. WorkflowEngine state machines — prevents invalid transitions
3. 3-tier cognitive memory — innovative AI memory design
4. BPMN-first governance — executable, testable process models
5. Encapsulated MCP tools — high-level ops, not raw SQL
6. Core Protocol injection — 8 rules on every prompt
7. Session fact persistence — survives context compaction
8. Self-healing config — DB source of truth, auto-regeneration
9. Failure capture loop — errors auto-filed as bugs
10. Task discipline enforcement — prevents code without planning

---

## Subsystem Index

| # | System | Detail Doc | Lines |
|---|--------|-----------|-------|
| 1 | Hook System | [[claude-family-audit-hooks]] | Event-driven behavior layer |
| 2 | MCP Tools & Servers | [[claude-family-audit-mcp]] | Model Context Protocol |
| 3 | Knowledge & RAG | [[claude-family-audit-knowledge]] | AI memory and retrieval |
| 4 | Database Schema | [[claude-family-audit-database]] | Persistence and state machines |
| 5 | BPMN Process Governance | [[claude-family-audit-bpmn]] | Process modeling and testing |
| 6 | Operations (Skills/Config/Logging) | [[claude-family-audit-operations]] | Skills, config, logging, vault |
| 7 | Enterprise Alternatives | [[claude-family-audit-alternatives]] | Comparison with off-the-shelf |

---

## Gaps for Enterprise (Metis)

| Gap | Impact | Recommendation |
|-----|--------|---------------|
| No proper event bus | Hooks fragile, platform-specific | Event-driven architecture |
| No token budget management | RAG can flood context | Hard caps with priority ordering |
| 43 stale vault docs | Misleads Claude instances | Systematic cleanup pass |
| 6 broken slash commands | Errors on use | Delete or rewrite |
| 72 MCP tools, no grouping | Tool selection overwhelm | Namespacing or dynamic loading |
| BPMN alignment covers 8/76 | Can't verify model=code | Expand _ARTIFACT_REGISTRY |
| server.py/v2 split | Maintenance burden | Consolidate |
| Windows-only file locking | Platform lock-in | Cross-platform abstraction |
| No cross-project monitoring | Blind to health | Monitoring dashboard |
| No RAG quality metrics | Can't optimize retrieval | Add feedback loop |

**Key Insight**: No single product combines hook-based behavior modification + RAG + BPMN governance + cognitive memory + work tracking. The integration is the innovation. Each piece has off-the-shelf alternatives, but the combined system is unique.

**Raw audit reports**: `docs/audit/` (7 files, ~145K chars total)

---

**Version**: 1.0
**Created**: 2026-03-09
**Updated**: 2026-03-09
**Location**: knowledge-vault/10-Projects/Project-Metis/claude-family-systems-audit.md
