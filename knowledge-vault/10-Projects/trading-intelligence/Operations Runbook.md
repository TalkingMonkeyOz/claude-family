---
projects:
- trading-intelligence
tags:
- operations
- deployment
- infrastructure
- monitoring
synced: false
---

# Trading Intelligence - Operations Runbook

**Purpose**: How to deploy, monitor, and troubleshoot the split-architecture trading system.

---

## Infrastructure

| Server | IP | Role | OS | SSH Alias |
|--------|-----|------|-----|-----------|
| Oracle ARM | 161.33.64.78 | DB + scheduler + watchdog | Ubuntu 24.04 ARM64 | `oracle` |
| Oracle x86 | 152.69.179.53 | IB Gateway + executor | Ubuntu 24.04 x86_64 | `oracle-x86` |
| Windows | Local | Tauri desktop app | Windows 11 | N/A |

SSH keys: `~/.ssh/oci_arm_key` (both servers use same key).
ARM to x86 SSH: `/home/ubuntu/.ssh/oci_x86_key` (copy of oci_arm_key).

---

## ARM Server (Brain)

### Services

| Service | Type | Command |
|---------|------|---------|
| PostgreSQL | systemd | `sudo systemctl {status|restart} postgresql` |
| Scheduler | systemd | `sudo systemctl {status|restart|stop} trading-intelligence` |
| Watchdog | systemd timer | `sudo systemctl {status} watchdog.timer` |

### Key Paths

| Path | Purpose |
|------|---------|
| `/opt/trading-intelligence/` | Code deployment |
| `/opt/trading-intelligence/.env` | DB credentials (TI_DB_* vars) |
| `/opt/trading-intelligence/run_scheduler.py` | Scheduler entry point |
| `/opt/venvs/trading-intelligence/` | Python 3.12 venv |
| `/var/log/trading-intelligence/scheduler.log` | Scheduler log file |

### Deploy to ARM

```bash
# From Windows Git Bash
bash scripts/deploy-server.sh
# Tars services/intelligence/, SCPs to ARM, restarts service
```

### Logs

```bash
ssh oracle
journalctl -u trading-intelligence -f           # Live scheduler logs
journalctl -u trading-intelligence --since today # Today's logs
sudo tail -f /var/log/trading-intelligence/scheduler.log
```

### DB Access

```bash
ssh oracle
sudo -u postgres psql -d trading_intelligence
# Password has special chars - use sudo -u postgres, not password auth
```

---

## x86 Server (Hands)

### Services

| Service | Type | Purpose |
|---------|------|---------|
| `xvfb.service` | systemd | Virtual framebuffer for headless IB Gateway |
| `ibgateway.service` | systemd | IB Gateway via IBC (paper trading) |
| `order-executor.service` | systemd | Order executor v6 (ib_async) |

### Key Paths

| Path | Purpose |
|------|---------|
| `/opt/trading-intelligence/services/order_executor.py` | Executor v6 source |
| `/opt/trading-intelligence/services/.env.executor` | DB DSN + IB config |
| `/opt/ibc/config.ini` | IBC credentials + settings |
| `/opt/venvs/executor/` | Python venv |

### Deploy to x86 (and ARM)

```bash
# From Windows Git Bash - deploys BOTH ARM scheduler + x86 executor
bash scripts/deploy-x86.sh
# 1. Tars services/intelligence/ -> SCPs to ARM -> restarts scheduler
# 2. SCPs order_executor.py -> x86 -> restarts order-executor service
```

### Logs

```bash
ssh oracle-x86
journalctl -u ibgateway -f       # IB Gateway logs
journalctl -u order-executor -f  # Executor logs
journalctl -u xvfb -f            # Virtual display
```

### IBC Configuration

- Config: `/opt/ibc/config.ini`
- Credentials embedded (jdv26121972)
- Paper mode, `ExistingSessionDetectedAction=primaryoverride`
- Auto-restart at 5AM via IBC `ClosedownAt` setting

---

## Windows Desktop App

### Launch (connects to Oracle DB)

```batch
scripts\launch-app.bat
:: 1. Opens SSH tunnel (localhost:5433 -> ARM:5432)
:: 2. Sets TRADING_DB_URL with URL-encoded password
:: 3. Runs npm run tauri dev
```

### Local Dev (uses local PostgreSQL)

```batch
npm run tauri dev
:: Uses PGPASSWORD env var, connects to localhost PostgreSQL 18
```

### SSH Tunnel Only

```batch
scripts\start-tunnel.bat
:: Maps localhost:5433 -> Oracle ARM PostgreSQL
:: Idempotent - checks if already running
```

---

## Watchdog (3-Tier Monitoring)

Runs every 5 minutes on ARM via systemd timer.

| Tier | Action | Example |
|------|--------|---------|
| 1. Check | Detect issues | Service down, DB unreachable, stale data |
| 2. Playbook | Auto-remediate | Restart service, clear stale locks |
| 3. AI (Claude Haiku) | Analyze + recommend | Complex failures, multi-service issues |

Script: `services/intelligence/watchdog.py`
Env: `/opt/trading-intelligence/.env.watchdog`
Log table: `watchdog_log`

---

## Common Operations

### Check System Health

```bash
# ARM: scheduler + DB
ssh oracle "sudo systemctl status trading-intelligence && sudo -u postgres psql -d trading_intelligence -c \"SELECT key, value FROM system_config WHERE key LIKE 'executor%' OR key LIKE 'ibgateway%';\""

# x86: IB Gateway + executor
ssh oracle-x86 "sudo systemctl status ibgateway order-executor"
```

### View Active Signals

```sql
SELECT ticker, action, status, quantity, strategy,
       risk_checks->>'ibkr_order_id' as ibkr_id
FROM trade_signals
WHERE executed = FALSE
ORDER BY created_at DESC;
```

### Emergency: Activate Kill Switch

```sql
-- Via DB (immediate)
UPDATE risk_state SET kill_switch_active = TRUE, updated_at = NOW();
```

Or use the Kill Switch button in the Trading UI.

### Restart All Services

```bash
# ARM
ssh oracle "sudo systemctl restart trading-intelligence"

# x86
ssh oracle-x86 "sudo systemctl restart ibgateway order-executor"
```

---

## Executor v6 Bookkeeping (Feb 2026)

The `record_execution()` function now handles full post-trade bookkeeping:

| Step | What | Detail |
|------|------|--------|
| Signal dedup | `ON CONFLICT` on `trade_executions` | Prevents duplicate execution records on retry |
| Holdings upsert | BUY: insert/increment, SELL: decrement | Automatic portfolio tracking |
| Risk state update | Updates `risk_state` table | Daily P&L, open positions count |
| Trade funding | Creates `trade_funding` record | Links execution to loan capital |
| Telegram alert | Sends on execution failures | Bot notification via `alerts/telegram.py` |
| ASX margin buffer | 15% extra for ASX stocks | Accounts for currency conversion spread |

**Migration 020**: Added `ON CONFLICT` support and CAPE scraper data source.

---

## Known Gotchas

| Issue | Solution |
|-------|----------|
| DB password has `%` chars | systemd: use `EnvironmentFile=`, not `Environment=` |
| `StartLimitIntervalSec` in wrong section | Must be in `[Unit]`, not `[Service]` |
| x86 executor DB connection | Uses VCN internal IP (10.0.0.72:5432), not SSH tunnel |
| IBKR `qualifyContractsAsync` changes exchange | Reset `contract.exchange = "SMART"` after qualifying |
| yfinance MultiIndex columns | `data.columns.droplevel(1)` after multi-ticker download |
| ARM needs `lxml` for yfinance | `pip install lxml` in venv |

---

## Related Docs

- [[Architecture Overview]] - System design and component diagram
- [[Order Executor Design]] - Executor v6 detailed design
- [[Strategy & Scanner Pipeline]] - Signal generation flow

---

**Version**: 1.1
**Created**: 2026-02-20
**Updated**: 2026-02-23
**Location**: 10-Projects/trading-intelligence/Operations Runbook.md
