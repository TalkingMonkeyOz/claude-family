# Inter-Claude Messaging Audit — Detail

**Parent**: [messaging-audit-2026-03-15.md](messaging-audit-2026-03-15.md)
**Date**: 2026-03-15

---

## Recipient Routing Analysis (Query 4)

| to_project | Exists? | Count | Issue |
|-----------|---------|-------|-------|
| claude-family | Yes | 77 | OK |
| *(broadcasts)* | N/A | 49 | OK |
| mission-control-web | Yes | 17 | OK |
| claude-family-manager-v2 | Yes | 8 | OK |
| claude-desktop-config | Yes | 7 | OK |
| nimbus-mui | Yes | 6 | OK |
| nimbus-user-loader | Yes | 6 | OK |
| **ato-tax-agent** | **No** | **5** | Dead — lowercase variant |
| claude-family-manager | Yes | 4 | OK |
| monash-nimbus-reports | Yes | 4 | OK |
| metis | Yes | 4 | OK |
| **ATO-tax-agent** | **No** | **3** | Dead — mixed case |
| nimbus-import | Yes | 3 | OK |
| **mcw** | **No** | **2** | Dead — abbreviation for mission-control-web |
| **nimbus-manager-mui** | **No** | **2** | Dead — old project name |
| claude-mission-control | Yes | 2 | OK |
| **Claude Family Manager v2** | **No** | **2** | Dead — display name used instead of slug |
| claude-manager-mui | Yes | 2 | OK |
| **mission-control** | **No** | **1** | Dead — old project name |
| **DRY_RUN_playwright** | **No** | **1** | Dead — test artifact |
| trading-intelligence | Yes | 1 | OK |
| **claude-code-unified** | **No** | **1** | Dead — retired project name |
| personal-finance-system | Yes | 1 | OK |

9 dead `to_project` values, 19 messages total undeliverable.

---

## Active Workspaces — Valid Recipients (Query 5)

| project_name | type | domain | Last Session |
|-------------|------|--------|--------------|
| project-metis | infrastructure | metis | 2026-03-15 |
| claude-family | infrastructure | infrastructure | 2026-03-15 |
| trading-intelligence | tauri-react | finance | 2026-03-15 |
| finance-mui | web | finance | 2026-03-14 |
| nimbus-mui | application | nimbus | 2026-03-13 |
| monash-nimbus-reports | tauri-react | nimbus | 2026-03-11 |
| nimbus-odata-configurator | application | nimbus | 2026-02-27 |
| nimbus-user-loader | csharp-winforms | nimbus | 2026-02-06 |
| nimbus-import | tauri-react | nimbus | 2026-01-25 |
| bee-game | unity-game | personal | 2026-01-18 |
| claude-manager-mui | tauri-react | claude-tools | 2026-01-15 |
| **claude-desktop-config** | infrastructure | infrastructure | **2026-01-12** |
| ATO-tax-agent | work-research | ato | 2026-01-04 |
| ATO-Tax-Agent | nextjs-typescript | ato | 2026-01-04 |
| ATO-Infrastructure | azure-infrastructure | ato | 2026-01-03 |
| claude-family-manager-v2 | csharp-winforms | claude-tools | 2025-12-27 |
| mcp-search-test | infrastructure | NULL | NULL |

17 active workspaces. `ATO-tax-agent` and `ATO-Tax-Agent` are duplicate workspaces (same last session date). `mcp-search-test` has never had a session.

---

## Messages to Non-Existent Projects (Query 7)

| to_project | Subject | Date |
|-----------|---------|------|
| DRY_RUN_playwright | Reprocess 860 Schedules for Part Number + Activity Fixes | 2026-01-24 |
| nimbus-manager-mui | Monash Costing Investigation Complete - Root Cause Analysis | 2026-01-24 |
| nimbus-manager-mui | Nimbus Costing Investigation - Award Rules Migration Knowledge | 2026-01-24 |
| Claude Family Manager v2 | Update: Batch File Updated + C# Integration Code | 2025-12-22 |
| Claude Family Manager v2 | Feature Request: Centralized Config Deployment | 2025-12-21 |
| mcw | Data Gateway System Implemented - MCW Integration Required | 2025-12-04 |
| mcw | Schema Update - Document-Project Linking System | 2025-12-03 |
| claude-code-unified | MCW Schema Usage Analysis Complete | 2025-12-01 |
| mission-control | Architecture Change: Migrate from Python Flet to Next.js + shadcn/ui | 2025-11-29 |

All 9 are historical (pre-2026). Content may be relevant — the `mcw` messages about Data Gateway and schema updates may have been superseded; verify before archiving.

---

## Notable Unactioned Messages (Selected from Query 3)

High-priority items still in non-terminal states:

| Date | From → To | Type | Priority | Subject |
|------|-----------|------|----------|---------|
| 2026-03-10 | nimbus-mui → monash-nimbus-reports | task_request | **urgent** | BREAKING: Shared keyring service name changed to "nimbus-time2work" |
| 2026-03-10 | metis → claude-family | task_request | **urgent** | UPDATED: Full Gate Consolidation — All Gates, Not Just Gate 1 |
| 2026-03-10 | metis → claude-family | task_request | **urgent** | Gate 1 Consolidation — 4 Docs From Existing Material + Gap List |
| 2026-03-14 | claude-family → claude-family | task_request | normal | METIS: Plan-of-Attack Rewrite Brief Ready (13 validated decisions) |
| 2026-02-25 | NULL → claude-desktop-config | handoff | **urgent** | Cognitive Memory System - Full Design Handoff (BPMN + Tests + Architecture) |

The cognitive memory handoff to `claude-desktop-config` (2026-02-25, urgent) is orphaned — that workspace has been inactive since 2026-01-12.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: C:\Projects\claude-family\docs\messaging-audit-2026-03-15-detail.md
