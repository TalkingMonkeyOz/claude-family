"""
cf_constants.py — Shared constants and helpers for Claude Family infrastructure.

Single-source for values that cross multiple consumers (worker daemons,
MCP tools, schedulers). Override defaults via environment variables.
F224 — Local Task Queue + Worker Daemon.

Module exports:
- Worker pool size constants (CF_SCRIPT_WORKER_COUNT, CF_AGENT_WORKER_COUNT)
- Lease + heartbeat defaults (CF_DEFAULT_LEASE_SECS, CF_DEFAULT_HEARTBEAT_DIVISOR, ...)
- Retry policy defaults (CF_DEFAULT_MAX_ATTEMPTS, CF_DEFAULT_RETRY_BACKOFF_*, ...)
- Circuit breaker defaults (CF_DEFAULT_PAUSE_THRESHOLD_*)
- Queue health monitoring thresholds (CF_BACKLOG_ALERT_THRESHOLD, CF_DEAD_LETTER_RATE_*, ...)
- Helper functions: cf_backoff_seconds, cf_heartbeat_interval, cf_idempotency_key
"""

import hashlib
import json
import os
import random
from typing import Any

# ---------------------------------------------------------------------------
# Worker pool sizes (override via env var; daemon restart applies)
# ---------------------------------------------------------------------------
CF_SCRIPT_WORKER_COUNT = int(os.environ.get("CF_SCRIPT_WORKER_COUNT", "2"))
CF_AGENT_WORKER_COUNT = int(os.environ.get("CF_AGENT_WORKER_COUNT", "4"))

# ---------------------------------------------------------------------------
# Lease + heartbeat (per-template overrides come from job_templates row)
# ---------------------------------------------------------------------------
CF_DEFAULT_LEASE_SECS = int(os.environ.get("CF_DEFAULT_LEASE_SECS", "300"))
CF_DEFAULT_HEARTBEAT_DIVISOR = int(
    os.environ.get("CF_DEFAULT_HEARTBEAT_DIVISOR", "3")
)
CF_DEFAULT_DRAIN_DEADLINE_SECS = int(
    os.environ.get("CF_DEFAULT_DRAIN_DEADLINE_SECS", "60")
)

# ---------------------------------------------------------------------------
# Retry policy defaults (per-template overrides come from job_templates row)
# ---------------------------------------------------------------------------
CF_DEFAULT_MAX_ATTEMPTS = int(os.environ.get("CF_DEFAULT_MAX_ATTEMPTS", "3"))
CF_DEFAULT_RETRY_BACKOFF_BASE = int(
    os.environ.get("CF_DEFAULT_RETRY_BACKOFF_BASE", "30")
)
CF_DEFAULT_RETRY_BACKOFF_MAX = int(
    os.environ.get("CF_DEFAULT_RETRY_BACKOFF_MAX", "3600")
)
CF_DEFAULT_RETRY_JITTER_PCT = int(os.environ.get("CF_DEFAULT_RETRY_JITTER_PCT", "25"))

# ---------------------------------------------------------------------------
# Circuit breaker defaults
# ---------------------------------------------------------------------------
CF_DEFAULT_PAUSE_THRESHOLD_FAILS = int(
    os.environ.get("CF_DEFAULT_PAUSE_THRESHOLD_FAILS", "5")
)
CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS = int(
    os.environ.get("CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS", "600")
)

# ---------------------------------------------------------------------------
# Queue health monitoring thresholds (L2)
# ---------------------------------------------------------------------------
CF_BACKLOG_ALERT_THRESHOLD = int(
    os.environ.get("CF_BACKLOG_ALERT_THRESHOLD", "100")
)
CF_DEAD_LETTER_RATE_THRESHOLD = int(
    os.environ.get("CF_DEAD_LETTER_RATE_THRESHOLD", "5")
)
CF_LEAKED_LEASE_THRESHOLD = int(os.environ.get("CF_LEAKED_LEASE_THRESHOLD", "0"))
CF_DRAIN_STALL_SECS = int(os.environ.get("CF_DRAIN_STALL_SECS", "1800"))
CF_HEALTH_CHECK_INTERVAL_MINS = int(
    os.environ.get("CF_HEALTH_CHECK_INTERVAL_MINS", "15")
)
CF_L3_LIVENESS_MAX_AGE_MINS = int(
    os.environ.get("CF_L3_LIVENESS_MAX_AGE_MINS", "30")
)

# ---------------------------------------------------------------------------
# Default transient error classes (per-template overrides on job_templates)
# ---------------------------------------------------------------------------
CF_DEFAULT_TRANSIENT_ERROR_CLASSES = [
    "ConnectionError",
    "TimeoutError",
    "OSError",
    "psycopg.OperationalError",
]

# Agent-kind templates extend this with LLM-specific transient errors
CF_AGENT_TRANSIENT_ERROR_CLASSES = CF_DEFAULT_TRANSIENT_ERROR_CLASSES + [
    "RateLimitError",
    "APIConnectionError",
    "APITimeoutError",
]


def cf_backoff_seconds(
    attempt: int, base: int = None, cap: int = None, jitter_pct: int = None
) -> int:
    """
    Exponential backoff with bounded jitter.

    Args:
        attempt (int): 1-indexed attempt number. If < 1, treated as 1.
        base (int): Base backoff in seconds. Default: CF_DEFAULT_RETRY_BACKOFF_BASE.
        cap (int): Maximum backoff in seconds. Default: CF_DEFAULT_RETRY_BACKOFF_MAX.
        jitter_pct (int): Jitter as percentage of raw backoff (±N%). Default: CF_DEFAULT_RETRY_JITTER_PCT.

    Returns:
        int: Backoff in seconds (always >= 1).

    Formula:
        raw = min(base * (2 ** (attempt - 1)), cap)
        jitter = (random ± jitter_pct% of raw)
        result = raw + jitter
    """
    base = base or CF_DEFAULT_RETRY_BACKOFF_BASE
    cap = cap or CF_DEFAULT_RETRY_BACKOFF_MAX
    jitter_pct = jitter_pct if jitter_pct is not None else CF_DEFAULT_RETRY_JITTER_PCT

    if attempt < 1:
        attempt = 1

    # Exponential with cap
    raw = min(base * (2 ** (attempt - 1)), cap)

    # Bounded jitter: ±jitter_pct% of raw
    jitter_range = raw * (jitter_pct / 100.0)
    jitter = (random.random() * 2 - 1) * jitter_range  # ±jitter_range

    return max(1, int(raw + jitter))


def cf_heartbeat_interval(lease_secs: int = None, divisor: int = None) -> int:
    """
    Heartbeat cadence derived from lease.

    Typically lease/3 so two heartbeats keep a lease alive (one at 1/3, one at 2/3).

    Args:
        lease_secs (int): Lease duration in seconds. Default: CF_DEFAULT_LEASE_SECS.
        divisor (int): Divisor for lease. Default: CF_DEFAULT_HEARTBEAT_DIVISOR.

    Returns:
        int: Heartbeat interval in seconds (always >= 1).
    """
    lease = lease_secs or CF_DEFAULT_LEASE_SECS
    div = divisor or CF_DEFAULT_HEARTBEAT_DIVISOR
    return max(1, lease // div)


def cf_idempotency_key(template_id: str, version: int, payload: Any) -> str:
    """
    Deterministic idempotency key for enqueue dedup.

    Hashes template_id, version, and canonical JSON of payload.
    Dict/list payloads are JSON-dumped with sorted keys for determinism.

    Args:
        template_id (str): Template UUID or name.
        version (int): Template version number.
        payload (Any): Payload dict, list, str, None, or any JSON-serializable.

    Returns:
        str: SHA256 hex digest (64 chars).
    """
    # Canonicalize payload to JSON with sorted keys for determinism
    if payload is not None:
        payload_canonical = json.dumps(payload, sort_keys=True, default=str)
    else:
        payload_canonical = "null"

    # Construct raw string
    raw = f"{template_id}|{version}|{payload_canonical}"

    # Return SHA256 hash
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
