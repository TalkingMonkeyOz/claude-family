---
projects:
- project-hal
- claude-family
tags:
- research
- value-analysis
- coding-intelligence
- CKG
- patterns
---

# SCE Value Analysis — What's the Return If It Works?

This document answers: **regardless of build effort, what improvement does each approach deliver?** And: **how do we measure whether it actually worked?**

## The CKG Reality Check (2026-03-25 Audit)

Before projecting value, here's what the current CKG system actually does:

| Area | Status | Detail |
|---|---|---|
| Session-start re-index | WORKS | Fires on every session for indexed projects |
| Post-commit re-index | BROKEN | Only installed on claude-family, missing from other projects |
| Mid-session re-index | MISSING | No hook triggers indexing after Write/Edit during a session |
| Collision warnings | WORKS (advisory) | Warns about name collisions but never blocks |
| CKG usage enforcement | MISSING | Nothing forces Claude to query CKG before coding |
| Coding-intelligence skill | WORKS (opt-in) | Claude must manually invoke; nothing requires it |

**8,077 symbols indexed across 7 projects.** Data freshness varies: nimbus-mui (today), claude-family (yesterday), trading-intelligence (4 days stale).

**The fundamental gap**: CKG data exists but Claude doesn't use it during coding. The collision hook is advisory-only. The coding-intelligence skill is opt-in. There is zero enforcement.

## What We're Measuring Against: The 7 Failure Modes

These cause multi-day debugging sessions (observed in nimbus-mui parallel run, trading-intelligence, claude-manager-mui):

| # | Failure Mode | Pain Weight | Real Example |
|---|---|---|---|
| 1 | Pattern Inconsistency | ×3 (CRITICAL) | `execute_rest_get` vs `execute_odata_query` — 2-4 day parallel run nightmare |
| 2 | Error Cascade | ×3 (CRITICAL) | Fix A breaks B, fix B breaks C. One wrong assumption snowballs. |
| 3 | Context Loss | ×2 (HIGH) | Change file A, discover it broke file D after compilation |
| 4 | Accumulated Drift | ×2 (HIGH) | Each session adds "close but not quite" code. Slow poison. |
| 5 | Missing Constraints | ×2 (HIGH) | Valid TypeScript that compiles but uses wrong approach |
| 6 | Discovery Overhead | ×1.5 (MEDIUM) | 60% of AI time reading/understanding, 40% writing |
| 7 | Cross-File Coordination | ×1.5 (MEDIUM) | 5+ files need atomic changes done sequentially |

## The Value Table — Improvement Per Approach

Scored 0-3 per failure mode (0=no help, 3=eliminates problem), weighted by pain:

| Approach | Pattern (×3) | Cascade (×3) | Context (×2) | Drift (×2) | Constraints (×2) | Discovery (×1.5) | Cross-file (×1.5) | **Total /46.5** | **% Improvement** |
|---|---|---|---|---|---|---|---|---|---|
| **Current (no CKG use)** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **0** | baseline |
| **1. Enhanced CKG** | 2 | 1 | 2 | 1 | 0 | 3 | 1 | **21** | **45%** |
| **6. Patterns** | 3 | 2 | 1 | 3 | 3 | 2 | 2 | **35** | **75%** |
| **1+6 Combined** | 3 | 2 | 2 | 3 | 3 | 3 | 2 | **39** | **84%** |
| **2. Semantic Layer** | 2 | 2 | 3 | 2 | 2 | 3 | 3 | **35** | **75%** |
| **4. Components** | 3 | 2 | 2 | 2 | 2 | 2 | 3 | **34.5** | **74%** |
| **3. Intent-Based** | 3 | 3 | 3 | 3 | 3 | 3 | 3 | **45** | **97%** |

**Key finding**: Approaches 1+6 combined deliver 84% of theoretical maximum. Approach 3 (Intent-Based) delivers 97% but at 10x the build effort.

## Realistic Scenario Projections

Based on observed session times from nimbus-mui, trading-intelligence, and claude-manager-mui:

### Scenario 1: "Add a new OData entity fetcher"
*Frequency: ~2x per week on nimbus-mui*

| Method | Time | Risk | Tokens Used |
|---|---|---|---|
| Current (no tools) | 5-60 min | 50% chance wrong pattern | 5-10 file reads |
| + Enhanced CKG | 2-3 min | Sees majority pattern | 1 tool call |
| + Patterns | **30 seconds** | Template instantiation | 1 tool call |
| **Improvement** | **90-99%** | **Risk → 0** | **80% fewer tokens** |

### Scenario 2: "Refactor all OData calls to new paginated API"
*Frequency: ~1x per month, but costs days when it happens*

| Method | Time | Missed Instances | Rework |
|---|---|---|---|
| Current | 1-3 hours | 2-3 missed | 30-60 min rework |
| + Enhanced CKG | 30-60 min | 0 missed (complete list) | None |
| + Patterns | **5-10 min** | 0 missed | None |
| **Improvement** | **90-95%** | **100%** | **100%** |

### Scenario 3: "Parallel run breaks — inconsistent response handling"
*Frequency: rare but catastrophic (~1x per project lifecycle)*

| Method | Time | Root Cause Discovery | Resolution |
|---|---|---|---|
| Current | **2-4 DAYS** | Trial and error across files | Iterative fix-break-fix |
| + Enhanced CKG | 30-60 min | Inconsistency visible upfront | Single targeted fix |
| + Patterns | **Problem doesn't exist** | Pattern enforces consistency | N/A |
| **Improvement** | **95-100%** | **Instant vs days** | **Structural prevention** |

### Scenario 4: "New developer (Claude) starts on existing project"
*Frequency: every new session*

| Method | Ramp-up Time | Context Quality | First-change Accuracy |
|---|---|---|---|
| Current | 5-15 min reading files | Incomplete, biased by which files read | ~70% |
| + Enhanced CKG | 1-2 min (one get_context call) | Complete graph | ~90% |
| + Patterns | **30 sec** (patterns + context) | Complete + constrained | **~98%** |

## How to Measure If It Worked

**Proposed metrics (measurable from existing data):**

| Metric | Current Baseline | Target | How to Measure |
|---|---|---|---|
| Tasks per feature | 50-277 (nimbus-mui) | <30 | Count from `claude.todos` per feature |
| Session time per feature | Hours-days | <2 hours | Session duration from `claude.sessions` |
| Files read before first edit | 5-10 | 1-2 | MCP usage logs (file reads vs CKG calls) |
| Pattern violations detected | 0 (no detection) | Track all | Collision hook + pattern violation logs |
| Rework iterations | 3-5 fix cycles | <2 | Todo reopen count, error cascade length |
| Cross-session consistency | Unmeasured | >90% pattern adherence | CKG audit tool |

**The 2% vs 20% question**: If Approach 1+6 reduces average tasks-per-feature from 100 to 30, that's a **70% improvement** in iteration overhead. If it only reduces from 100 to 90, that's 10% — still worth it but different priority. We won't know until we measure with a real project.

**Proposed test**: Run nimbus-mui's next feature with Approach 1 active (Enhanced CKG + get_context). Compare tasks created, session time, and rework cycles against the parallel run baseline.

## The Enforcement Question

The user's core concern: "I say this isn't working, you go okay, and change it. But do you actually update the CKG?"

**Current answer: No.** The process should be:

```
1. User requests change
2. Claude queries CKG (get_context) → understands full impact
3. Claude makes the change (Write/Edit)
4. CKG automatically re-indexes the changed files
5. Pattern system validates the change against constraints
```

**What actually happens:**
```
1. User requests change
2. Claude reads files directly (skips CKG entirely)
3. Claude makes the change
4. CKG stays stale until next session start
5. No validation occurs
```

**What HAL Phase A would fix:**
- Step 2: Enforcement hook forces CKG query before Write/Edit (not advisory)
- Step 4: PostToolUse hook on Write/Edit triggers immediate re-index
- Step 5: Pattern constraints checked at write time

This is the difference between a **tool that exists** and a **process that's enforced**.

---
**Version**: 1.0
**Created**: 2026-03-25
**Updated**: 2026-03-25
**Location**: knowledge-vault/20-Domains/coding-intelligence/sce-value-analysis.md
