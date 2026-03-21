---
projects:
- trading-intelligence
tags:
- sop
- infrastructure
- server
- health-check
- oracle
---

# Trading Server Health Check SOP

**Purpose**: Standard procedure for verifying the trading infrastructure (ARM scheduler + x86 executor) is operational.

---

## When to Run

- At the start of every trading-intelligence session
- After server reboots or maintenance windows
- When investigating missing signals or failed orders
- Weekly as a routine check

---

## Quick Check (Single Command Per Server)

### ARM Server (161.33.64.78) - DB + Scheduler

```bash
ssh oracle "systemctl is-active trading-intelligence postgresql && journalctl -u trading-intelligence --no-pager -n 10 --since '1 hour ago' && sudo -u postgres psql -d trading_intelligence -c \"SELECT NOW(), count(*) as signals_24h FROM trade_signals WHERE created_at > NOW() - INTERVAL '24 hours';\""
```

**Expect**: Both services `active`, recent heartbeat/gauge logs, signal count > 0 on trading days.

### x86 Server (152.69.179.53) - Executor + IB Gateway

```bash
ssh oracle-x86 "systemctl is-active ssh-tunnel-arm xvfb ibgateway order-executor && journalctl -u order-executor --no-pager -n 10 && journalctl -u ibgateway --no-pager -n 5"
```

**Expect**: All 4 services `active`, executor cycling every 10s with `ib_connected=True`.

---

## What to Check

| Check | ARM | x86 | How |
|-------|-----|-----|-----|
| Services running | trading-intelligence, postgresql | ssh-tunnel-arm, xvfb, ibgateway, order-executor | `systemctl is-active` |
| Recent activity | Heartbeat every 60s, gauge every 15m | Executor cycle every 10s | `journalctl -n 10` |
| DB connectivity | PostgreSQL accepting connections | Tunnel to ARM DB working | psql query / executor logs |
| IB Gateway | N/A | Connected, paper account DUM054196 | `ib_connected=True` in logs |
| Signals flowing | Signal count in last 24h | Signals being processed | DB query / executor logs |
| Errors | No `[error]` in logs | No `[error]` in logs | `journalctl -p err -n 5` |

---

## Deeper Diagnostics

### Check for Errors (Last Hour)

```bash
# ARM
ssh oracle "journalctl -u trading-intelligence -p err --since '1 hour ago' --no-pager"

# x86
ssh oracle-x86 "journalctl -u order-executor -p err --since '1 hour ago' --no-pager"
ssh oracle-x86 "journalctl -u ibgateway -p err --since '1 hour ago' --no-pager"
```

### Check Scheduler Jobs

```bash
ssh oracle "journalctl -u trading-intelligence --no-pager -n 50 | grep -E 'executed successfully|ERROR'"
```

### Check Capital and Positions

Look for `available_capital` lines in executor logs — shows AUD and USD balances.

### Check ASX Market Hours

ASX signals are held outside hours (Mon-Fri 10:00-16:00 AEST). The executor logs `asx_order_held_outside_hours` — this is normal behaviour, not an error.

---

## Common Issues and Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Service `inactive` | Crashed or server rebooted | `sudo systemctl restart <service>` |
| `ib_connected=False` | IB Gateway disconnected | Check ibgateway service, may need IBC restart |
| No signals in 24h | Scheduler job failed or market holiday | Check scheduler logs for errors |
| Executor not processing | SSH tunnel down (x86 can't reach ARM DB) | `sudo systemctl restart ssh-tunnel-arm` |
| High cycle count, no orders | All signals already processed or held | Normal — check signal statuses in DB |

---

## Service Management

```bash
# ARM
sudo systemctl {start|stop|restart|status} trading-intelligence
sudo systemctl {start|stop|restart|status} postgresql

# x86
sudo systemctl {start|stop|restart|status} order-executor
sudo systemctl {start|stop|restart|status} ibgateway
sudo systemctl {start|stop|restart|status} ssh-tunnel-arm
sudo systemctl {start|stop|restart|status} xvfb
```

---

## Key File Locations

| What | ARM | x86 |
|------|-----|-----|
| Code | `/opt/trading-intelligence/services/intelligence/` | `/opt/trading-intelligence/services/order_executor.py` |
| Venv | `/opt/venvs/trading-intelligence` | `/opt/venvs/executor` |
| Env file | `/opt/trading-intelligence/.env` | `/opt/trading-intelligence/services/.env.executor` |
| Logs | `journalctl -u trading-intelligence` | `journalctl -u order-executor` |
| IBC config | N/A | `/opt/ibc/config.ini` |
| Deploy script | `scripts/deploy-server.sh` | `scripts/deploy-x86.sh` |

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: knowledge-vault/40-Procedures/infrastructure/Trading Server Health Check SOP.md
