---
projects:
- trading-intelligence
tags:
- quick-reference
- claude-family
synced: false
---

# Project - Trading Intelligence

**Type**: Tauri Desktop (Rust + React)
**Phase**: All 5 phases complete (F93-F97)
**Path**: `C:\Projects\trading-intelligence`
**Project ID**: `e64b62e0-0b09-4310-92d8-52b5aedd9ed0`
**GitHub**: `TalkingMonkeyOz/trading-intelligence`

---

## Purpose

SMSF portfolio management ($624k), market intelligence (Correction Gauge), opportunity scanning (6 scanners + AI), and semi-automated trading via IBKR. Trading capital is loan-funded - safety is paramount.

Evolved from `finance-mui` (`2ebf5484-59a8-477c-b475-258b2a062d40`).

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Desktop | Tauri 2.0 (Rust backend) |
| Frontend | React 19 + TypeScript 5 + MUI X 7 |
| Backend | Rust (sqlx for PostgreSQL) |
| Intelligence | Python 3.12 (pandas, yfinance, ib_async) |
| Database | PostgreSQL 16 (`trading_intelligence`) |
| AI | Claude Haiku (news sentiment) |
| Alerts | Telegram Bot API |

---

## Phase Summary

| Phase | Feature | Code | Status |
|-------|---------|------|--------|
| 0 | SQLite to PostgreSQL Migration | F93 | Completed |
| 1 | SMSF Portfolio + Correction Gauge + Alerts | F94 | Completed |
| 2 | Stock Scanners + News Sentiment + Watchlist | F95 | Completed |
| 3 | Paper Trading + IBKR Connector + Trading UI | F96 | Completed |
| 3.5 | ASX Support | - | Completed |
| 4 | Go Live + Backtest + CGT Reports + Loans | F97 | Completed |

---

## Key Components

| Component | Location |
|-----------|----------|
| Rust commands (~700 lines) | `src-tauri/src/commands.rs` |
| Rust models (~1400 lines) | `src-tauri/src/models.rs` |
| Rust DB (~1620 lines) | `src-tauri/src/db.rs` |
| React pages | `src/pages/` (Markets, Trading, Reports, Settings) |
| React hooks (25 files) | `src/hooks/` |
| Python trading engine | `services/intelligence/trading/` |
| Python scanners (6 types) | `services/intelligence/scanner/` |
| Python backtest | `services/intelligence/backtest/` |
| Python CGT calculator | `services/intelligence/tax/` |
| Python loan service | `services/intelligence/loan/` |
| DB migrations (6) | `database/migrations/` |

---

## Safety Rules (Trading)

- Paper trading minimum 60 days before live
- Kill switch: file-based + DB + Telegram + UI
- Max drawdown 15%, max daily loss 3%, max position 35%
- Go Live: typed "CONFIRM LIVE TRADING" confirmation
- SMSF accounts NEVER have automated trading (DB constraint)

---

## Config & MCP

| MCP | Purpose |
|-----|---------|
| postgres | `ai_company_foundation` DB (NOT `trading_intelligence`) |
| orchestrator | Agent spawning |
| sequential-thinking | Complex reasoning |
| project-tools | Work tracking |

**Python venv**: `C:\venvs\trading-intelligence`

See also: [[Orchestrator MCP]], [[Claude Family Postgres]]

---

**Version**: 1.0
**Created**: 2026-02-09
**Updated**: 2026-02-09
**Location**: Claude Family/Project - Trading Intelligence.md
