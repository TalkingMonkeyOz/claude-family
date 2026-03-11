---
projects:
- trading-intelligence
tags:
- trading
- strategies
- scanners
- regime
- position-sizing
synced: false
---

# Trading Intelligence - Strategy & Scanner Pipeline

**Purpose**: How stock signals flow from scanners through strategies to trade execution.

---

## Pipeline Overview

```
Universe (~200 stocks)
  ASX 101 + S&P500 100
  defined in universe.py
        |
        v
6 Scanners (daily)             Correction Gauge (4-hourly)
  Tier 1: Momentum, Value,       0-100 score
          Mean Reversion          -> exposure_factor (0.3 - 1.0)
  Tier 2: AI Picks,              -> regime classification
          Dividends,
          Risk Monitor
        |                              |
        v                              v
stock_signals table             RegimeService
        |                        - gauge -> exposure factor
        v                        - momentum/MR favorable checks
6 Strategies (market hours)      - Hurst exponent classification
  read signals, apply rules,
  regime-adjust, size positions
        |
        v
trade_signals table
  status: pending | approved
        |
        v
Order Executor (x86, 10s poll)
  claims -> executes via IBKR
        |
        v
trade_executions table
```

---

## Scanners (6 Types)

All inherit from `BaseScanner` ABC with `scan() -> list[dict]` and `run() -> persist`.

| Scanner | Tier | What It Finds |
|---------|------|---------------|
| **Momentum** | 1 | Stocks with strong relative strength, trend alignment |
| **Value** | 1 | Undervalued stocks (P/E, P/B, dividend yield) |
| **Mean Reversion** | 1 | Oversold stocks with reversion potential (RSI, Bollinger) |
| **AI Picks** | 2 | Claude Haiku analysis of fundamentals + technicals |
| **Dividends** | 2 | High-yield, sustainable dividend stocks |
| **Risk Monitor** | 2 | Existing holdings at risk (stop loss, momentum loss) |

**Technical Patterns Scanner** (F103): 6 additional pattern types:
- Support/resistance levels
- Moving average crossovers
- Bollinger Band squeezes
- Gap detection
- Volume divergence
- Trendline breaks

Output stored in `stock_signals` table with `signal_type`, `confidence`, `metadata` JSONB.

---

## Strategies (6 Active)

All inherit from `BaseStrategy` ABC or `ScannerStrategyBase`.

| Strategy | Alloc | Base Class | Signal Source |
|----------|-------|------------|---------------|
| **Dual Momentum** | 25% | BaseStrategy | ETF rotation: SPY vs VEU vs BND |
| **Cross-Sectional Momentum** | 15% | ScannerStrategyBase | Top-N from universe by 12-month momentum |
| **Pairs Trading** | 15% | BaseStrategy | Cointegrated pairs, mean-reversion on spread |
| **Momentum Picker** | 10% | ScannerStrategyBase | Best momentum scanner signals |
| **Mean Reversion Picker** | 10% | ScannerStrategyBase | Best MR scanner signals |
| **Cash Reserve** | 10% | BaseStrategy | Conservative VAS + cash buffer |

**Total allocation**: 85% (15% buffer unallocated).
All set to `full_auto` execution mode.

### StrategyRegistry

```python
@StrategyRegistry.register
class MyStrategy(BaseStrategy):
    name = "my_strategy"
    ...
```

Auto-registration decorator. Access via `.get(name)`, `.get_all()`, `.get_names()`.

### ScannerStrategyBase

For scanner-driven strategies. Flow:
1. Read `stock_signals` from DB
2. Filter by scanner type and recency
3. Apply regime check (RegimeService)
4. Apply strategy-specific rules (`_apply_strategy_rules()`)
5. Size positions (PositionSizer)
6. Return `list[Signal]`

---

## Regime Service

Converts the Correction Gauge (0-100) into trading constraints.

| Gauge Range | Regime | Exposure Factor |
|-------------|--------|-----------------|
| 0-20 | Extreme Fear | 0.3 |
| 20-40 | Fear | 0.5 |
| 40-60 | Neutral | 0.7 |
| 60-80 | Greed | 1.0 |
| 80-100 | Extreme Greed | 0.8 (pullback risk) |

**Checks**:
- `is_momentum_favorable()`: gauge >= 40
- `is_mean_reversion_favorable()`: gauge <= 60
- `calculate_hurst_exponent()`: trend vs mean-reversion classification per ticker

---

## Position Sizer

Graduated Kelly criterion with multiple safety layers.

### Kelly Graduation (by trade count)

| Trades Completed | Kelly Fraction |
|-----------------|----------------|
| < 10 | Quarter Kelly (0.25x) |
| 10-29 | Third Kelly (0.33x) |
| 30+ | Half Kelly (0.50x) |

### Safety Caps

| Rule | Limit |
|------|-------|
| Max single position | 25% of capital |
| Regime adjustment | Multiply by exposure_factor |
| CPPI floor (loans) | Preserve loan principal - never risk below floor |
| Min position | $500 (skip if smaller) |

### CPPI Floor (Loan-Funded Capital)

For loan-funded trading, CPPI (Constant Proportion Portfolio Insurance) ensures the portfolio never drops below the loan principal:
- `cushion = portfolio_value - loan_principal`
- `max_risk = cushion * multiplier`
- Position sizes capped to protect the floor

---

## SMSF Recommender

Cross-references scanner signals with SMSF compliance rules to generate **manual** trading recommendations (SMSF accounts never have automated trading).

- Reads scanner signals from all 6 scanners
- Filters for SMSF-appropriate stocks (no speculative, adequate liquidity)
- Generates recommendations stored in `smsf_recommendations` table
- Displayed in Trading UI > SMSF Recs tab

---

## Signal Lifecycle

```
Scanner detects opportunity     -> stock_signals (raw)
Strategy filters + sizes        -> trade_signals (status='approved' for full_auto)
                                              (status='pending' for semi_auto)
User approves (if semi_auto)    -> status='approved'
Executor claims (atomic)        -> status='executing'
IBKR fills                      -> status='executed' + trade_executions record
  OR conditions change          -> status='cancelled'
  OR expires                    -> status='expired'
  OR IBKR rejects               -> status='failed'
```

See [[Order Executor Design]] for detailed executor behavior.

---

## Strategy Configuration (DB)

Stored in `strategy_config` table:

| Column | Purpose |
|--------|---------|
| `strategy_name` | Unique identifier |
| `execution_mode` | full_auto, semi_auto, signal_only, disabled |
| `allocation_pct` | % of capital allocated |
| `parameters` | JSONB: tickers, exchange, currency, strategy-specific settings |
| `rebalance_frequency` | daily, weekly, monthly, quarterly |
| `account_id` | Linked trading account (nullable) |

ASX vs US configured per strategy via `parameters` JSONB:
- US: `{"tickers": ["SPY", "VEU", "BND"], "exchange": "SMART", "currency": "USD"}`
- ASX: `{"tickers": ["VAS.AX", "IOZ.AX"], "exchange": "ASX", "currency": "AUD"}`

---

## Related Docs

- [[Architecture Overview]] - System design
- [[Order Executor Design]] - Executor v6 signal processing
- [[Operations Runbook]] - Deployment and monitoring

---

**Version**: 1.0
**Created**: 2026-02-20
**Updated**: 2026-02-20
**Location**: 10-Projects/trading-intelligence/Strategy & Scanner Pipeline.md
