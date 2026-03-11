---
projects:
- trading-intelligence
tags:
- build-history
- delegation
synced: false
---

# Trading Intelligence - Build History

**Purpose**: Record of how each phase was built, agent delegation patterns, and lessons learned.

---

## Phase Summary

| Phase | Feature | Build Tasks | Agents | What |
|-------|---------|-------------|--------|------|
| Phase 0 (F93) | Foundation | BT-1 to BT-7 | Manual | SQLite to PostgreSQL migration |
| Phase 1 (F94) | SMSF + Gauge | BT-1 to BT-12 | 12 agents | Markets screen, gauge, alerts |
| Phase 2 (F95) | Scanners + News | BT-13 to BT-20 | 5 Sonnet | 6-tier scanners, sentiment, watchlist |
| Phase 3 (F96) | Paper Trading | BT-21 to BT-28 | 6 Sonnet | IBKR connector, strategies, risk mgr |
| Phase 4 (F97) | Go Live + Reports | BT-29 to BT-38 | 7 Sonnet + 3 Haiku | Backtest, CGT, loans, Go Live |
| Phase 5 (F98) | Strategy Pipeline | BT-39 to BT-58 | 5 Sonnet | Scanner→strategy, regime, Kelly, 65 tests |
| Phase 6 (F102) | Universe + Strategies | BT-59 to BT-68 | Multiple | Pairs, XS-momentum, 200 stocks, Hurst |
| Phase 7 (F103) | Risk Framework | N/A | Multiple | CPPI floor, graduated Kelly, ATR stops, patterns scanner |
| Phase 8 (F109) | ML + Events | BT-360 to BT-369 | Multiple | Event collector, ML forecaster, Deep Think, fundamentals |
| Deployment | Split Architecture | N/A | Manual | ARM+x86 servers, executor v6, watchdog |

| Operational | Executor Bookkeeping | N/A | Manual | ON CONFLICT dedup, holdings upsert, Telegram alerts, CAPE |
| BPMN | Process Models | N/A | Manual | 10 BPMN files (L0 + 7 L1 + 1 L2 + 4 new) |

**Total**: ~68+ build tasks, 90+ unit tests, 200k+ lines across all languages.

---

## Key Milestones

| Date | Milestone |
|------|-----------|
| 2026-02-08 | F93: SQLite→PostgreSQL migration complete |
| 2026-02-09 | F94-F97: Phases 1-4 built (2 days) |
| 2026-02-10 | F98: Scanner→strategy pipeline, position sizing, regime |
| 2026-02-11 | F102: Universe expansion, pairs/XS-momentum strategies |
| 2026-02-13 | F103: Risk framework, CPPI, graduated Kelly |
| 2026-02-14 | F109: Event-driven ML forecaster, Deep Think |
| 2026-02-15 | Split architecture: ARM (brain) + x86 (hands) deployed |
| 2026-02-16 | Paper trading live: 3 orders queued, $1M paper capital |
| 2026-02-17 | Watchdog deployed, executor v6, operational runbooks |
| 2026-02-20 | Startup shortcut removed, docs updated |
| 2026-02-23 | Executor bookkeeping: holdings upsert, risk_state, dedup, Telegram alerts, CAPE scraper |
| 2026-02-23 | 4 new BPMN models: gauge, scanners, reporting, analysis (10 total) |

---

## Phase 4 Execution Pattern (Most Refined)

```
Phase A (5 parallel, no dependencies):
  BT-29 (DB Migration)           -> Sonnet
  BT-30 (Python Backtest)        -> Sonnet
  BT-31 (Python CGT Calculator)  -> Sonnet
  BT-32 (Python Monthly Reports) -> Haiku
  BT-33 (Python Loan Service)    -> Haiku

Phase B (sequential, depends on BT-29):
  BT-34 (Rust Commands)          -> Sonnet (needs table schema)
  BT-35 (React Types/Hooks)      -> Sonnet (needs command signatures)

Phase C (3 parallel, depends on BT-35):
  BT-36 (Backtest UI)            -> Sonnet
  BT-37 (CGT Report UI)          -> Sonnet
  BT-38 (Go Live + IBKR + Loans) -> Sonnet
```

**Result**: All 10 agents successful, zero Phase 4 TypeScript errors, minimal cleanup.

---

## Delegation Lessons

| Lesson | Detail |
|--------|--------|
| Sonnet agents add unused imports | Always run `tsc` after agent completes |
| `alpha` import from wrong path | Common MUI mistake - quick fix |
| Haiku good for structured tasks | Types, hooks, service wrappers |
| Sonnet needed for UI components | Complex JSX, state management |
| `import *` inside functions fails | Python restriction, caught in F98 |
| Context is key | Provide exact file contents and patterns to agents |
| Parallel execution saves time | Phase A (5 parallel) -> Phase B (sequential) -> Phase C (3 parallel) |

---

## Git History (Key Commits)

```
ae0982e fix: 6 medium-priority operational fixes from BPMN gap analysis
ac55466 fix: 6 high-priority safety fixes from BPMN gap analysis
0e7ec93 fix: 7 critical safety fixes from BPMN gap analysis
b5fa7bc feat: split architecture - executor v6, watchdog, operational scripts
be640b7 fix: prevent duplicate trade signals on same day
12e1bdd feat: F109 Event-Driven ML Forecaster + Deep Think Analysis
973bf04 fix: mean reversion regime boundary - allow at gauge=60
def204a feat: F103 Portfolio Risk Framework - CPPI, Kelly, ATR stops
<earlier> feat: F102 Universe expansion, pairs + cross-sectional momentum
<earlier> feat: F98 Scanner-strategy pipeline, regime, position sizing
7e80933 feat: Implement Phase 4 - Go Live, Backtest, CGT Reports [F97]
a6279c0 feat: Implement Phase 3 - Paper Trading Engine, IBKR [F96]
5bb4365 feat: Implement Phase 2 - Stock Scanners, News Sentiment [F95]
8bb300c feat: Implement Phase 1 - SMSF Portfolio, Correction Gauge [F94]
301b83b feat: Rewrite Rust backend from SQLite to PostgreSQL [F93]
```

---

**Version**: 2.1
**Created**: 2026-02-09
**Updated**: 2026-02-23
**Location**: 10-Projects/trading-intelligence/Build History.md
