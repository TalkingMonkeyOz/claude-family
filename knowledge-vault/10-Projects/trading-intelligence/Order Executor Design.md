---
projects:
- trading-intelligence
tags:
- trading
- ibkr
- order-execution
- infrastructure
synced: false
---

# Order Executor v6 - Design Document

## Overview

The Order Executor is a standalone Python asyncio service that continuously monitors and manages trade signal execution via Interactive Brokers. It runs on the **x86 Oracle Cloud instance** alongside IB Gateway and connects to the **ARM server's PostgreSQL** for signal data.

**Purpose**: Bridge the gap between strategy signal generation (ARM brain) and order execution (IBKR hands).

**Current version**: v6 (Feb 2026) - adds full post-trade bookkeeping, Telegram alerts, ASX margin handling.

## Deployment

| Property | Value |
|----------|-------|
| **Server** | x86 Oracle Cloud (152.69.179.53) |
| **Path** | `/opt/order-executor/run.py` |
| **Service** | `systemd order-executor.service` |
| **Python** | 3.12, venv at `/opt/venvs/order-executor` |
| **DB Connection** | ARM PostgreSQL at `10.0.0.72:5432/trading_intelligence` |
| **IB Gateway** | `127.0.0.1:4002`, paper trading, client_id=2 |
| **Deploy** | `scp services/order_executor.py oracle-x86:/tmp/run.py && ssh oracle-x86 "sudo cp /tmp/run.py /opt/order-executor/run.py && sudo systemctl restart order-executor"` |

## 10-Second Monitoring Cycle

Every 10 seconds, the executor runs a complete cycle:

### Step 1: Expire Stale Signals
- Marks signals past `expires_at` as `expired` (approved, pending, or executing)
- Runs even without IBKR connection (DB-only operation)

### Step 2: Kill Switch Check
- Reads `risk_state.kill_switch_active` from DB
- **Fail-closed**: If DB unreachable, assumes kill switch ON (stops trading)

### Step 3: Process New Approved Signals
- Queries `trade_signals WHERE status='approved' AND executed=FALSE`
- **Claim-before-execute**: Atomically sets `status='executing'` (optimistic locking prevents duplicate orders on restart)
- Submits to IBKR via `ib_async`
- Handles outcomes: FILLED → record execution, QUEUED → store ibkr_order_id, ERROR → mark failed

### Step 4: Reconcile Queued Orders
For all `status='executing'` signals:
- **Has ibkr_order_id**: Check IBKR open trades for match
  - Filled → record execution
  - Cancelled/Inactive → mark failed
  - Gone from IBKR + recent (<2h) → re-submit
  - Gone from IBKR + old (>2h) → expire
- **No ibkr_order_id** (lost order):
  - Recent (<2h) → re-submit to IBKR
  - Old (>2h) → expire (strategy will generate fresh signal)

### Step 5: Re-evaluate Active Orders
Checks whether pending/queued orders still make sense:
- **Regime check**: Gauge dropped to fear/extreme_fear → cancel BUY orders
- **Stop loss breach**: Latest DB price below stop loss → cancel
- **Price drift**: Price moved >8% from entry → cancel (stale signal)
- Cancels both at IBKR and in DB (status → 'cancelled')

## Signal Lifecycle

```
Strategy generates signal → trade_signals.status = 'approved' (full_auto)
                                                  = 'pending' (semi_auto)
        ↓
Executor claims (atomic) → status = 'executing'
        ↓
IBKR accepts             → status = 'executing' + ibkr_order_id in risk_checks
        ↓
Market fills             → status = 'executed' + trade_executions record
                    OR
Conditions change        → status = 'cancelled' (re-evaluation)
Expired                  → status = 'expired' (past expires_at)
IBKR rejects             → status = 'failed'
```

## Key Design Decisions

### Claim-Before-Execute
Before placing any IBKR order, the signal is atomically moved to `executing` status. This prevents duplicate orders if the executor restarts mid-cycle. Only signals with `status='approved'` can be claimed.

### Lost Order Recovery
If IB Gateway crashes and restarts, queued IBKR orders are lost. The executor detects this (executing signal with no ibkr_order_id or ibkr_order_id not found in IBKR open trades) and re-submits within 2 hours. After 2 hours, the signal is expired so strategies can generate a fresh one with current prices.

### ASX Ticker Handling
IBKR does **not** use the `.AX` suffix (Yahoo Finance convention). The executor strips `.AX` before creating the IBKR contract:
- Signal: `RRL.AX` → IBKR: `Stock('RRL', 'ASX', 'AUD')`
- Signal: `SPY` → IBKR: `Stock('SPY', 'SMART', 'USD')`

### ValidationError (Warning 399)
IBKR returns `ValidationError` with warning 399 for orders placed outside market hours (e.g., ASX stocks after 4PM AEDT). This is **not an error** - the order is accepted and will be placed at the next market open. Treated as QUEUED.

### Reconnect Backoff
On IBKR connection failure, backoff starts at 10s and doubles to max 60s. Resets to 10s on successful connection. Executor never exits on IBKR unavailability - keeps retrying.

## Configuration

| Constant | Default | Description |
|----------|---------|-------------|
| `POLL_INTERVAL` | 10s | Main loop cycle time |
| `ORDER_FILL_TIMEOUT` | 60s | Wait for immediate fill before treating as QUEUED |
| `STALE_ORDER_HOURS` | 2h | Expire executing signals stuck without IBKR match |
| `RECONNECT_BACKOFF_MAX` | 60s | Maximum backoff between reconnect attempts |

## Monitoring & Observability

### Logs
```bash
# Live logs
journalctl -u order-executor -f

# Filter for errors
journalctl -u order-executor --since today | grep -E 'error|fail|cancel'

# Cycle summaries (only logged when activity occurs)
journalctl -u order-executor | grep cycle_complete
```

### Heartbeat (DB)
```sql
SELECT key, value, updated_at
FROM system_config
WHERE key IN ('executor.last_heartbeat', 'ibgateway.connected', 'executor.cycle_stats');
```

### Signal Status
```sql
-- Active signals
SELECT ticker, action, status, quantity, strategy,
       risk_checks->>'ibkr_order_id' as ibkr_id
FROM trade_signals
WHERE executed = FALSE
ORDER BY created_at DESC;

-- Execution history
SELECT ticker, action, quantity, price, commission, executed_at
FROM trade_executions
ORDER BY executed_at DESC LIMIT 20;
```

## v6 Bookkeeping (record_execution)

When an order fills, `record_execution()` performs a complete post-trade update:

```
IBKR fill received
  ├── INSERT trade_executions (ON CONFLICT DO NOTHING → dedup on retry)
  ├── Holdings upsert:
  │     BUY  → INSERT ON CONFLICT UPDATE (add quantity, recalc avg_price)
  │     SELL → UPDATE (subtract quantity, remove if zero)
  ├── UPDATE risk_state (daily_pnl, open_positions_count, updated_at)
  ├── INSERT trade_funding (links execution to loan capital source)
  └── On failure → Telegram alert via alerts/telegram.py
```

### ASX Margin Buffer

ASX stocks require a 15% margin buffer on capital checks to account for AUD/USD currency conversion spread and settlement timing. Applied in `check_capital_available()` before order submission.

### Telegram Failure Alerts

On execution failure (IBKR rejection, capital insufficient, contract qualification error), the executor sends a Telegram notification via the bot API. Configured in `.env.executor` with `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.

---

## Related Components

| Component | Server | Role |
|-----------|--------|------|
| [[Architecture Overview]] | Both | System architecture |
| Strategy Service | ARM (161.33.64.78) | Generates signals in `trade_signals` |
| Scheduler | ARM | Runs strategies on cron schedules |
| IB Gateway + IBC | x86 | Java IBKR gateway, paper trading |
| Correction Gauge | ARM | Regime indicator for re-evaluation |
| `trade_signals` table | ARM DB | Signal queue (source of truth) |
| `trade_executions` table | ARM DB | Execution records |
| `system_config` table | ARM DB | Heartbeats and status |

---
**Version**: 1.1
**Created**: 2026-02-17
**Updated**: 2026-02-23
**Location**: 10-Projects/trading-intelligence/Order Executor Design.md
