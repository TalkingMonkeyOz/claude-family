---
projects:
- trading-intelligence
tags:
- architecture
- overview
synced: false
---

# Trading Intelligence - Architecture Overview

**Purpose**: Desktop trading system with SMSF compliance, market intelligence, ML forecasting, and semi-automated IBKR trading. Loan-funded capital ($624k SMSF + paper trading).

---

## Split Architecture (Deployed Feb 2026)

```
Windows Desktop                Oracle ARM (161.33.64.78)         Oracle x86 (152.69.179.53)
┌──────────────────┐           ┌──────────────────────┐          ┌──────────────────────┐
│  Tauri App       │           │  PostgreSQL 16        │          │  IB Gateway + IBC    │
│  (Rust + React)  │──SSH───>  │  trading_intelligence │  <──VCN──│  (Java, paper mode)  │
│                  │  tunnel   │  42 tables, 19 mig.   │          │                      │
│  - UI (React/MUI)│  :5433   │                       │          │  Order Executor v6   │
│  - DB (sqlx)     │           │  Python Scheduler     │          │  (ib_async, 10s poll)│
│  - State (Zustand│           │  31 jobs, APScheduler │          │                      │
│    + TanStack Q) │           │                       │          │  Watchdog (5 min)    │
└──────────────────┘           │  Watchdog (5 min)     │          └──────────────────────┘
                               └──────────────────────┘
```

**Communication bus**: PostgreSQL on ARM. All processes read/write the same DB.

| Server | Role | Services |
|--------|------|----------|
| **ARM** (161.33.64.78) | Brain | PostgreSQL, scheduler (signal generation), watchdog |
| **x86** (152.69.179.53) | Hands | IB Gateway, IBC, order executor, watchdog |
| **Windows** | Eyes | Tauri desktop app (connects via SSH tunnel to ARM DB) |

---

## Database Schema (19 Migrations, 42 Tables)

| Migration | Key Tables | Purpose |
|-----------|------------|---------|
| 001 | accounts, holdings, transactions, member_profile, contribution_tracking | Core portfolio |
| 002 | correction_gauge, market_indicators, stock_signals, news_articles, portfolio_snapshots, system_config | Market intelligence |
| 003 | watchlist, alert_config, alerts, strategy_config, trade_signals, trade_executions, risk_state | Scanners + trading |
| 004 | SMSF trade-blocking trigger | Compliance |
| 005 | trading_mode on accounts | Paper/live mode |
| 006 | backtest_*, tax_*, monthly_reports, investment_loans, loan_interest_log, go_live_checklist | Phase 4 |
| 007 | Seed 6 strategies | Strategy config |
| 008 | trade_funding | Loan deployment tracking |
| 009 | smsf_recommendations, trade_signal columns | Trading flow redesign |
| 010-012 | Strategy account fixes, new strategies, allocation fixes | Iterative fixes |
| 013-015 | dividend_dates, seasonal_overlay, ml_classifier | Feature tables |
| 016 | stock_events, event_patterns, stock_fundamentals, ml_forecasts, deep_analysis, morningstar_reports | F109 event-driven ML |
| 017 | Partial unique index on trade_signals | Signal deduplication |
| 018 | watchdog_log | Monitoring audit |
| 019 | Daily signal dedup constraint | Signal integrity |

**Live data** (Oracle ARM): 217k+ price bars, 198 tickers, 25 signals, 13 executions, 19k+ events, 603 fundamentals.

---

## UI Structure

| Page | Tabs / Features |
|------|-----------------|
| **Dashboard** | Portfolio summary, service status panel (scheduler + IB Gateway), setup checklist |
| **Markets** | Gauge, Scanners (7 sub-tabs), News, Watchlist |
| **Trading** | Strategies, Pending, Positions, History, Performance, Backtest, SMSF Recs + Kill Switch + Go Live + Regime chip |
| **Analysis** | Overview (Deep Think), Events, Fundamentals, Forecasts |
| **Reports** | Income & Expenses, By Category, Trends, CGT Report, Monthly |
| **Settings** | Profile, API Keys, Alerts, IBKR Config, Loan Manager, Database, System Info |

---

## Python Services (ARM Scheduler - 31 Jobs)

| Service | Location | Schedule | Description |
|---------|----------|----------|-------------|
| Correction Gauge | `market_gauge/` | Every 4 hours | Multi-indicator market regime (0-100) |
| Price Collector | `market_gauge/price_collector.py` | Daily 5:30 PM AEST | yfinance for ~200 tickers + 6 ETFs |
| 6 Scanners | `scanner/` | Daily (staggered) | 3 Tier 1 + 3 Tier 2 AI scanners |
| News/Sentiment | `sentiment/` | Every 2 hours | RSS + Claude Haiku analysis |
| 6 Strategies | `trading/strategies/` | Market hours | See [[Strategy & Scanner Pipeline]] |
| SMSF Recommender | `recommendations/` | Daily | Cross-references scanners for manual recs |
| Event Collector | `events/collector.py` | Daily | Earnings, dividends, splits, macro events |
| Pattern Engine | `events/pattern_engine.py` | Daily | Historical event impact patterns |
| ML Forecaster | `ml/forecaster.py` | Daily | LightGBM 5/10/20-day return predictions |
| Deep Think | `analysis/deep_think.py` | Weekly | Claude Sonnet structured research |
| Backtest Engine | `backtest/` | On-demand | yfinance data, walk-forward validation |
| CGT Calculator | `tax/` | On-demand | FIFO matching, SMSF/Personal rates |
| Monthly Reports | `reports/` | 2nd of month | Portfolio snapshots, strategy breakdown |
| Loan Service | `loan/` | 1st of month | Interest accrual, profitability check |

---

## Trading Strategies (6 Active, 85% Allocation)

| Strategy | Allocation | Type | Rebalance |
|----------|-----------|------|-----------|
| Dual Momentum | 25% | Trend-following (SPY vs VEU vs BND) | Monthly |
| Cross-Sectional Momentum | 15% | Top-N from universe by momentum | Monthly |
| Pairs Trading | 15% | Cointegrated pair mean-reversion | Daily |
| Momentum Picker | 10% | Scanner-driven momentum signals | Daily |
| Mean Reversion Picker | 10% | Scanner-driven MR signals | Daily |
| Cash Reserve | 10% | Conservative (VAS + cash buffer) | Quarterly |

15% buffer unallocated. All set to `full_auto` execution mode.

---

## Key Technical Patterns

- Rust `Decimal` serializes as `string` in JSON - TS types use `string | null`
- `parseDecimal()` helper converts string decimals to numbers in React
- Python services use `get_connection()` context manager from `db.py`
- TanStack Query for data fetching, Zustand for UI state
- SMSF/Personal separation enforced at DB level (trigger + constraints)
- `StrategyRegistry`: `@StrategyRegistry.register` decorator, auto-registration
- Kill switch: dual mechanism (file `kill_switch.txt` + DB `risk_state.kill_switch_active`)
- Go Live: triple gate (60 days paper + positive return + typed "CONFIRM LIVE TRADING")

---

## BPMN Process Models (10 Files)

All workflows modeled in `processes/` directory. Synced to `claude.bpmn_processes` registry.

| File | Level | Scope |
|------|-------|-------|
| `L0_trading_intelligence.bpmn` | L0 | System cascade - full architecture with swim lanes |
| `L1_data_collection.bpmn` | L1 | Price collection, events, news ingestion |
| `L1_signal_generation.bpmn` | L1 | 6 strategies, regime filtering, position sizing |
| `L1_order_execution.bpmn` | L1 | Executor v6, 10s monitoring cycle |
| `L1_risk_monitoring.bpmn` | L1 | Daily risk checks, watchdog, heartbeat |
| `L1_market_gauge.bpmn` | L1 | 8 indicators, regime classification (fear→greed) |
| `L1_stock_scanners.bpmn` | L1 | 7 scanners, Tier 1 (algorithmic) / Tier 2 (AI) |
| `L1_monthly_reporting.bpmn` | L1 | CGT calculation, portfolio snapshots, loan tracking |
| `L1_event_analysis.bpmn` | L1 | Event collection, ML forecaster, Deep Think |
| `L2_signal_lifecycle.bpmn` | L2 | Full-auto vs semi-auto signal flow detail |

---

## Related Docs

- [[Order Executor Design]] - Executor v6 signal lifecycle and monitoring
- [[Strategy & Scanner Pipeline]] - Scanner→strategy→signal flow, regime, position sizing
- [[Operations Runbook]] - Deployment, monitoring, troubleshooting
- [[Build History]] - Phase-by-phase construction record

---

**Version**: 2.1
**Created**: 2026-02-09
**Updated**: 2026-02-23
**Location**: 10-Projects/trading-intelligence/Architecture Overview.md
