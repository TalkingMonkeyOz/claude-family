#!/usr/bin/env python3
"""
task_worker.py — Background worker daemon for the Claude Family local task queue.

Polls claude.task_queue, claims tasks with SKIP LOCKED + per-template
max_concurrent_runs guard, dispatches to script or agent thread pool,
runs a heartbeat per claim, routes findings on completion, and trips
per-template CircuitBreakers on repeated failure.

Architecture (F224 Concurrency — locked):
  - Single process
  - Two ThreadPoolExecutor pools: script (CF_SCRIPT_WORKER_COUNT) + agent (CF_AGENT_WORKER_COUNT)
  - Main thread: claim loop (polls DB every second while idle)
  - Worker threads: execute tasks, write back results
  - Heartbeat thread per running task: extends claimed_until at lease/3 cadence
  - Cancel-check thread per running task: polls cancel_requested

Launch:
  python scripts/task_worker.py <project_name>

Lifecycle:
  - Spawned by SessionStart watchdog (daemon_helper.watchdog_respawn)
  - SIGTERM -> graceful drain (60s hard cap, CF_DEFAULT_DRAIN_DEADLINE_SECS)
  - PID file: ~/.claude/task-worker-<project>.pid
  - Log file: ~/.claude/logs/task-worker-<project>.log
  - Port 9900-9999 range (vs ckg_daemon's 9800-9899)

F224 BT697 -- 2026-05-02
"""

import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path setup -- allow both `python scripts/task_worker.py` and module import
# ---------------------------------------------------------------------------
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from cf_circuit_breaker import CircuitBreaker
from cf_constants import (
    CF_AGENT_WORKER_COUNT,
    CF_DEFAULT_DRAIN_DEADLINE_SECS,
    CF_DEFAULT_MAX_ATTEMPTS,
    CF_DEFAULT_PAUSE_THRESHOLD_FAILS,
    CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS,
    CF_DEFAULT_TRANSIENT_ERROR_CLASSES,
    CF_SCRIPT_WORKER_COUNT,
    cf_backoff_seconds,
    cf_heartbeat_interval,
)
from config import get_db_connection
from daemon_helper import DaemonContext

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IDLE_TIMEOUT_SECS = 4 * 60 * 60   # 4h -- stays alive between scheduled tasks
CLAIM_POLL_INTERVAL = 1.0          # seconds between empty-queue polls
CANCEL_CHECK_INTERVAL = 5.0        # seconds between cancel_requested polls
WORKER_ID_PREFIX = "task-worker"

# ---------------------------------------------------------------------------
# Global state (set in main, accessed by worker threads)
# ---------------------------------------------------------------------------
_shutting_down = threading.Event()
_active_futures: List[Future] = []
_futures_lock = threading.Lock()

# Logger is set up in main() via DaemonContext; module-level placeholder
logger: logging.Logger = logging.getLogger("task-worker")


# ---------------------------------------------------------------------------
# DB connection helper
# ---------------------------------------------------------------------------
def _get_conn():
    """Return a fresh DB connection. Raises on failure."""
    return get_db_connection(strict=True)


# ---------------------------------------------------------------------------
# claim_next_task
# ---------------------------------------------------------------------------
def claim_next_task(worker_id: str) -> Optional[Dict[str, Any]]:
    """
    Claim one pending task from the queue.

    Uses FOR UPDATE SKIP LOCKED so concurrent workers never block each other.
    A correlated subquery enforces per-template max_concurrent_runs by counting
    currently in_progress tasks for the same template before allowing the claim.

    Returns a dict of the claimed row (task_queue.* plus key job_templates fields),
    or None if no claimable task exists right now.

    OVERRIDE: worker_daemon
    """
    conn = _get_conn()
    description = None
    try:
        cur = conn.cursor()
        sql = """
            -- OVERRIDE: worker_daemon
            WITH claimed AS (
                SELECT t.task_id
                FROM claude.task_queue t
                JOIN claude.job_templates jt ON t.template_id = jt.template_id
                WHERE t.status = 'pending'
                  AND (t.next_attempt_at IS NULL OR t.next_attempt_at <= now())
                  AND NOT jt.is_paused
                  AND (
                      SELECT COUNT(*) FROM claude.task_queue sq
                      WHERE sq.template_id = t.template_id
                        AND sq.status = 'in_progress'
                  ) < jt.max_concurrent_runs
                ORDER BY t.priority ASC, t.enqueued_at ASC
                FOR UPDATE OF t SKIP LOCKED
                LIMIT 1
            )
            UPDATE claude.task_queue tq
            SET status        = 'in_progress',
                claimed_by    = %s,
                claimed_at    = now(),
                claimed_until = now() + (jt.lease_duration_secs * interval '1 second'),
                attempts      = attempts + 1,
                started_at    = COALESCE(tq.started_at, now())
            FROM claude.job_templates jt
            WHERE tq.task_id = (SELECT task_id FROM claimed)
              AND jt.template_id = tq.template_id
            RETURNING
                tq.task_id,
                tq.template_id,
                tq.template_version,
                tq.payload_override,
                tq.status,
                tq.priority,
                tq.project_id,
                tq.attempts,
                tq.started_at,
                tq.claimed_until,
                tq.cancel_requested,
                jt.name                       AS template_name,
                jt.kind,
                jt.lease_duration_secs,
                jt.max_attempts,
                jt.transient_error_classes,
                jt.retry_backoff_base,
                jt.retry_backoff_max,
                jt.retry_jitter_pct,
                jt.is_idempotent,
                jt.pause_threshold_fails,
                jt.pause_threshold_window_secs
        """
        cur.execute(sql, (worker_id,))
        description = cur.description
        row = cur.fetchone()
        conn.commit()
        cur.close()

        if row is None:
            return None

        # Normalise to dict (psycopg2 may return tuple or RealDictRow)
        if isinstance(row, dict):
            task = dict(row)
        else:
            cols = [d[0] for d in description] if description else []
            task = dict(zip(cols, row))

        # Ensure task_id is a plain string
        task["task_id"] = str(task["task_id"])
        return task

    except Exception as exc:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.error(f"claim_next_task error: {exc}")
        return None
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Heartbeat thread
# ---------------------------------------------------------------------------
def _heartbeat_thread(task_id: str, lease_secs: int, stop_event: threading.Event) -> None:
    """Extend claimed_until every heartbeat_interval seconds until stop_event fires."""
    interval = cf_heartbeat_interval(lease_secs)
    while not stop_event.wait(timeout=interval):
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                -- OVERRIDE: worker_daemon
                UPDATE claude.task_queue
                SET claimed_until = now() + (%s * interval '1 second')
                WHERE task_id = %s AND status = 'in_progress'
                """,
                (lease_secs, task_id),
            )
            conn.commit()
            cur.close()
            conn.close()
            logger.debug(f"[{task_id}] heartbeat extended +{lease_secs}s")
        except Exception as exc:
            logger.warning(f"[{task_id}] heartbeat failed: {exc}")


# ---------------------------------------------------------------------------
# Cancel-check thread
# ---------------------------------------------------------------------------
def _cancel_check_thread(
    task_id: str, cancel_flag: threading.Event, stop_event: threading.Event
) -> None:
    """Poll cancel_requested in DB; set cancel_flag when found True."""
    while not stop_event.wait(timeout=CANCEL_CHECK_INTERVAL):
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT cancel_requested FROM claude.task_queue WHERE task_id = %s",
                (task_id,),
            )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                val = row[0] if not isinstance(row, dict) else row.get("cancel_requested")
                if val:
                    logger.info(f"[{task_id}] cancel_requested detected")
                    cancel_flag.set()
                    return
        except Exception as exc:
            logger.warning(f"[{task_id}] cancel check error: {exc}")


# ---------------------------------------------------------------------------
# Lease-revocation helper
# ---------------------------------------------------------------------------
def _is_lease_revoked(task_id: str) -> bool:
    """Return True if claimed_until has been set to the past (force-cancel)."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT claimed_until FROM claude.task_queue WHERE task_id = %s",
            (task_id,),
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row:
            val = row[0] if not isinstance(row, dict) else row.get("claimed_until")
            if isinstance(val, datetime):
                now = datetime.now(timezone.utc)
                if val.tzinfo is None:
                    val = val.replace(tzinfo=timezone.utc)
                return val < now
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Template payload resolver
# ---------------------------------------------------------------------------
def _resolve_payload(task: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch the current template version payload and merge payload_override on top.

    Script kind keys: command, args, cwd, env, timeout
    Agent kind keys:  model, prompt, mcp_servers, max_tokens, on_finding_route
    """
    template_id = task.get("template_id")
    template_version = task.get("template_version")
    base_payload: Dict[str, Any] = {}

    if template_id:
        try:
            conn = _get_conn()
            cur = conn.cursor()
            if template_version:
                cur.execute(
                    """
                    SELECT payload FROM claude.job_template_versions
                    WHERE template_id = %s AND version = %s
                    """,
                    (str(template_id), template_version),
                )
            else:
                cur.execute(
                    """
                    SELECT payload FROM claude.job_template_versions
                    WHERE template_id = %s
                    ORDER BY version DESC LIMIT 1
                    """,
                    (str(template_id),),
                )
            row = cur.fetchone()
            cur.close()
            conn.close()
            if row:
                pv = row[0] if not isinstance(row, dict) else row.get("payload")
                if isinstance(pv, dict):
                    base_payload = pv
                elif isinstance(pv, str):
                    base_payload = json.loads(pv)
        except Exception as exc:
            logger.warning(f"[{task['task_id']}] payload fetch error: {exc}")

    override = task.get("payload_override") or {}
    if isinstance(override, str):
        try:
            override = json.loads(override)
        except Exception:
            override = {}

    return {**base_payload, **override}


# ---------------------------------------------------------------------------
# Script execution
# ---------------------------------------------------------------------------
def _run_script(
    task: Dict[str, Any],
    payload: Dict[str, Any],
    cancel_flag: threading.Event,
) -> Dict[str, Any]:
    """
    Execute a script-kind task as a subprocess.

    Payload keys:
      command (str | list): executable + args
      args    (list):       extra args appended after command
      cwd     (str):        working directory (default: project root two levels up)
      env     (dict):       extra env vars merged onto os.environ
      timeout (int):        subprocess timeout in seconds (default: 300)

    Returns: {output, findings, return_code, duration_secs}

    Findings are parsed from the last JSON line of stdout that is a list or
    a dict with a 'findings' key.
    """
    command = payload.get("command") or []
    if isinstance(command, str):
        command = command.split()
    else:
        command = list(command)

    extra_args = payload.get("args") or []
    if extra_args:
        command = command + list(extra_args)

    cwd = payload.get("cwd") or str(Path(__file__).parents[1])
    timeout = int(payload.get("timeout") or 300)

    env = os.environ.copy()
    extra_env = payload.get("env") or {}
    env.update({str(k): str(v) for k, v in extra_env.items()})

    task_id = task["task_id"]
    logger.info(f"[{task_id}] script start: {command}")
    start = time.monotonic()

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stdout_lines: List[str] = []
    while True:
        line = proc.stdout.readline()
        if line:
            stdout_lines.append(line)
            logger.debug(f"[{task_id}] stdout: {line.rstrip()}")
        elif proc.poll() is not None:
            break

        if cancel_flag.is_set():
            proc.terminate()
            raise RuntimeError("Task cancelled via cancel_requested flag")

        if time.monotonic() - start > timeout:
            proc.terminate()
            raise TimeoutError(f"Script exceeded timeout of {timeout}s")

    # Drain remaining
    tail = proc.stdout.read()
    if tail:
        stdout_lines.append(tail)

    output_text = "".join(stdout_lines)
    return_code = proc.returncode
    duration_secs = time.monotonic() - start

    if return_code != 0:
        raise RuntimeError(
            f"Script exited with code {return_code}. Tail: {output_text[-1000:]}"
        )

    # Parse findings from last JSON line
    findings: List[Any] = []
    for line in reversed(output_text.splitlines()):
        line = line.strip()
        if line.startswith("[") or line.startswith("{"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, list):
                    findings = parsed
                elif isinstance(parsed, dict) and "findings" in parsed:
                    findings = parsed["findings"]
                break
            except json.JSONDecodeError:
                continue

    logger.info(
        f"[{task_id}] script complete rc={return_code} duration={duration_secs:.1f}s"
    )
    return {
        "output": output_text[-5000:],
        "findings": findings,
        "return_code": return_code,
        "duration_secs": duration_secs,
    }


# ---------------------------------------------------------------------------
# Agent execution (stubbed)
# ---------------------------------------------------------------------------
def _run_agent(
    task: Dict[str, Any],
    payload: Dict[str, Any],
    cancel_flag: threading.Event,
) -> Dict[str, Any]:
    """
    Execute an agent-kind task via the `claude` CLI in non-interactive (-p) mode.

    Routes through the user's logged-in OAuth/subscription so token usage is
    covered by the Max subscription (no per-call API billing). `--bare` is
    intentionally NOT passed because it forces API-key auth and bypasses OAuth.

    Payload keys:
      prompt              (str, required)  the user message
      model               (str)            'sonnet' (default) | 'opus' | 'haiku' | full name
      cwd                 (str)            project root passed via --add-dir; default: claude-family
      allowed_tools       (list[str])      passed to --allowed-tools
      disallowed_tools    (list[str])      passed to --disallowed-tools
      append_system       (str)            text passed to --append-system-prompt
      mcp_config          (str)            path to MCP JSON file
      timeout             (int)            wall-clock seconds (default 600)
      max_findings_lines  (int)            scan last N output lines for findings JSON

    Returns: {output, findings, return_code, duration_secs, agent_meta}
      agent_meta is the parsed JSON metadata from claude -p --output-format json
      (cost_usd, duration_ms, num_turns, etc.) when available.

    Findings parsed identically to _run_script: last JSON line that is a list
    or a dict with 'findings' key.
    """
    task_id = task["task_id"]
    prompt = payload.get("prompt")
    if not prompt:
        raise ValueError("agent-kind payload requires 'prompt'")

    cwd = payload.get("cwd") or str(Path(__file__).parents[1])
    timeout = int(payload.get("timeout") or 600)
    model = payload.get("model") or "sonnet"

    cmd: List[str] = ["claude", "-p", str(prompt),
                      "--output-format", "json",
                      "--model", str(model),
                      "--add-dir", str(cwd)]

    allowed = payload.get("allowed_tools")
    if allowed:
        cmd += ["--allowed-tools", ",".join(str(t) for t in allowed)]

    disallowed = payload.get("disallowed_tools")
    if disallowed:
        cmd += ["--disallowed-tools", ",".join(str(t) for t in disallowed)]

    append_system = payload.get("append_system")
    if append_system:
        cmd += ["--append-system-prompt", str(append_system)]

    mcp_config = payload.get("mcp_config")
    if mcp_config:
        cmd += ["--mcp-config", str(mcp_config)]

    logger.info(f"[{task_id}] agent start: model={model} cwd={cwd}")
    start = time.monotonic()

    proc = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    stdout_lines: List[str] = []
    while True:
        line = proc.stdout.readline()
        if line:
            stdout_lines.append(line)
        elif proc.poll() is not None:
            break
        if cancel_flag.is_set():
            proc.terminate()
            raise RuntimeError("Agent task cancelled via cancel_requested flag")
        if time.monotonic() - start > timeout:
            proc.terminate()
            raise TimeoutError(f"Agent exceeded timeout of {timeout}s")

    tail = proc.stdout.read()
    if tail:
        stdout_lines.append(tail)

    output_text = "".join(stdout_lines)
    return_code = proc.returncode
    duration_secs = time.monotonic() - start

    if return_code != 0:
        raise RuntimeError(
            f"claude CLI exited with code {return_code}. Tail: {output_text[-1000:]}"
        )

    # claude -p --output-format json emits a single JSON object as the last
    # non-empty line. Extract the assistant 'result' text + meta separately.
    agent_meta: Dict[str, Any] = {}
    result_text = output_text
    for line in reversed(output_text.splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, dict) and ("result" in parsed or "type" in parsed):
                    agent_meta = {k: v for k, v in parsed.items() if k != "result"}
                    if "result" in parsed:
                        result_text = str(parsed["result"])
                    break
            except json.JSONDecodeError:
                continue

    # Findings: scan last N lines of result_text for embedded JSON
    findings: List[Any] = []
    max_lines = int(payload.get("max_findings_lines") or 50)
    for line in reversed(result_text.splitlines()[-max_lines:]):
        line = line.strip()
        if line.startswith("[") or line.startswith("{"):
            try:
                parsed = json.loads(line)
                if isinstance(parsed, list):
                    findings = parsed
                    break
                if isinstance(parsed, dict) and "findings" in parsed:
                    findings = parsed["findings"]
                    break
            except json.JSONDecodeError:
                continue

    logger.info(
        f"[{task_id}] agent complete rc={return_code} duration={duration_secs:.1f}s "
        f"turns={agent_meta.get('num_turns', '?')}"
    )
    return {
        "output": result_text[-5000:],
        "findings": findings,
        "return_code": return_code,
        "duration_secs": duration_secs,
        "agent_meta": agent_meta,
    }


# ---------------------------------------------------------------------------
# set_template_paused
# ---------------------------------------------------------------------------
def set_template_paused(template_id: str, reason: str) -> None:
    """Pause a job_template when the circuit breaker trips. OVERRIDE: worker_daemon"""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(
            """
            -- OVERRIDE: worker_daemon
            UPDATE claude.job_templates
            SET is_paused     = true,
                paused_at     = now(),
                paused_reason = %s,
                updated_at    = now()
            WHERE template_id = %s
              AND NOT is_paused
            """,
            (reason[:500], str(template_id)),
        )
        conn.commit()
        cur.close()
        conn.close()
        logger.warning(f"[template:{template_id}] paused by circuit breaker: {reason}")
    except Exception as exc:
        logger.error(f"set_template_paused failed for {template_id}: {exc}")


# ---------------------------------------------------------------------------
# route_findings -- Q4 D2 finding routing
# ---------------------------------------------------------------------------
def route_findings(task: Dict[str, Any], result: Dict[str, Any]) -> None:
    """
    Route task findings to messages and/or feedback based on severity.

    Finding shape (from result['findings']):
        [{severity: 'low'|'medium'|'high'|'critical',
          title: str, body: str, suggested_action: str}]

    Routing config from payload on_finding_route (default: {"default": "message"}):
        {
          "critical": "both",      -- message + feedback
          "high":     "feedback",
          "medium":   "message",
          "low":      "message",
          "default":  "message"
        }

    For feedback rows: INSERT into claude.feedback.
    For message rows: INSERT into claude.messages.
    Sets task_queue.surfaced_as_feedback_id to the highest-severity finding's feedback_id.
    """
    findings = result.get("findings") or []
    if not findings:
        return

    try:
        payload = _resolve_payload(task)
        routing: Dict[str, str] = payload.get("on_finding_route") or {}
    except Exception:
        routing = {}

    if not routing:
        routing = {"default": "message"}

    def _route_for(severity: str) -> str:
        return routing.get(severity) or routing.get("default") or "message"

    SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

    sorted_findings = sorted(
        findings,
        key=lambda f: SEVERITY_ORDER.get(str(f.get("severity", "low")), 99),
    )

    project_id = task.get("project_id")
    task_id = str(task["task_id"])
    template_name = str(task.get("template_name") or task.get("template_id", "unknown"))
    top_feedback_id: Optional[str] = None

    for finding in sorted_findings:
        severity = str(finding.get("severity") or "low")
        title = str(finding.get("title") or "Task finding")
        body = str(finding.get("body") or "")
        suggested_action = str(finding.get("suggested_action") or "")
        route = _route_for(severity)

        feedback_id: Optional[str] = None

        if route in ("feedback", "both"):
            priority_map = {"critical": "1", "high": "2", "medium": "3", "low": "4"}
            fb_priority = priority_map.get(severity, "3")
            feedback_type = "bug" if severity in ("critical", "high") else "idea"
            description = body
            if suggested_action:
                description += f"\n\nSuggested action: {suggested_action}"

            try:
                conn = _get_conn()
                cur = conn.cursor()
                new_feedback_id = str(uuid.uuid4())
                cur.execute(
                    """
                    -- OVERRIDE: worker_daemon
                    INSERT INTO claude.feedback
                        (feedback_id, project_id, feedback_type, title, description, status, priority)
                    VALUES (%s, %s, %s, %s, %s, 'open', %s)
                    ON CONFLICT DO NOTHING
                    RETURNING feedback_id
                    """,
                    (
                        new_feedback_id,
                        str(project_id) if project_id else None,
                        feedback_type,
                        f"[{template_name}] {title}"[:200],
                        description[:4000],
                        fb_priority,
                    ),
                )
                row = cur.fetchone()
                conn.commit()
                cur.close()
                conn.close()
                if row:
                    feedback_id = str(
                        row[0] if not isinstance(row, dict) else row.get("feedback_id")
                    )
                    if top_feedback_id is None:
                        top_feedback_id = feedback_id
                    logger.info(
                        f"[{task_id}] finding routed to feedback {feedback_id} severity={severity}"
                    )
            except Exception as exc:
                logger.error(f"[{task_id}] route_findings feedback insert failed: {exc}")

        if route in ("message", "both"):
            msg_priority = (
                "critical" if severity == "critical"
                else ("high" if severity == "high" else "normal")
            )
            msg_body = body
            if suggested_action:
                msg_body += f"\n\nSuggested action: {suggested_action}"
            if feedback_id:
                msg_body += f"\n\nFeedback created: {feedback_id[:8]}"

            try:
                conn = _get_conn()
                cur = conn.cursor()
                cur.execute(
                    """
                    -- OVERRIDE: worker_daemon
                    INSERT INTO claude.messages
                        (to_project, from_project, message_type, priority, subject, body, status, metadata)
                    VALUES (%s, 'task-worker', 'notification', %s, %s, %s, 'unread', %s)
                    """,
                    (
                        "claude-family",
                        msg_priority,
                        f"[{severity.upper()}] {template_name}: {title}"[:200],
                        msg_body[:4000],
                        json.dumps({"task_id": task_id, "severity": severity}),
                    ),
                )
                conn.commit()
                cur.close()
                conn.close()
                logger.info(f"[{task_id}] finding routed to message severity={severity}")
            except Exception as exc:
                logger.error(f"[{task_id}] route_findings message insert failed: {exc}")

    # Update surfaced_as_feedback_id on the task row
    if top_feedback_id:
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                -- OVERRIDE: worker_daemon
                UPDATE claude.task_queue
                SET surfaced_as_feedback_id = %s
                WHERE task_id = %s
                """,
                (top_feedback_id, task_id),
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as exc:
            logger.error(f"[{task_id}] surfaced_as_feedback_id update failed: {exc}")


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------
def _is_transient(exc: Exception, transient_classes: Optional[List[str]]) -> bool:
    """Return True if exc matches any of the transient error class names."""
    classes = transient_classes or CF_DEFAULT_TRANSIENT_ERROR_CLASSES
    exc_mro_names = [t.__name__ for t in type(exc).__mro__]
    for cls_name in classes:
        bare = cls_name.split(".")[-1]
        if bare in exc_mro_names or cls_name in exc_mro_names:
            return True
    return False


# ---------------------------------------------------------------------------
# execute_task -- main worker function (runs in thread pool)
# ---------------------------------------------------------------------------
def execute_task(task: Dict[str, Any]) -> None:
    """
    Execute one claimed task end-to-end.

    1. Resolve effective payload (template payload merged with payload_override).
    2. Start heartbeat thread (extends claimed_until at lease/3 interval).
    3. Start cancel-check thread (polls cancel_requested).
    4. Dispatch by kind: script -> subprocess; agent -> stub (NotImplementedError).
    5. On success: UPDATE status='completed', write result, call route_findings.
    6. On failure: classify transient vs permanent:
       - Transient + attempts < max_attempts: status='pending', schedule retry backoff.
       - Permanent or max_attempts exhausted: status='dead_letter', trip CircuitBreaker.
    7. On lease revocation: exit without touching status (next worker reclaims).

    Must not raise -- all exceptions are caught and converted to DB status updates.
    """
    task_id = str(task.get("task_id", "?"))
    template_id = str(task.get("template_id") or "")
    kind = str(task.get("kind") or "script")
    lease_secs = int(task.get("lease_duration_secs") or 300)
    max_attempts = int(task.get("max_attempts") or CF_DEFAULT_MAX_ATTEMPTS)
    attempts = int(task.get("attempts") or 1)
    transient_classes: List[str] = list(
        task.get("transient_error_classes") or CF_DEFAULT_TRANSIENT_ERROR_CLASSES
    )
    backoff_base = int(task.get("retry_backoff_base") or 30)
    backoff_max = int(task.get("retry_backoff_max") or 3600)
    jitter_pct = int(task.get("retry_jitter_pct") or 25)
    pause_threshold_fails = int(
        task.get("pause_threshold_fails") or CF_DEFAULT_PAUSE_THRESHOLD_FAILS
    )
    pause_threshold_window = int(
        task.get("pause_threshold_window_secs") or CF_DEFAULT_PAUSE_THRESHOLD_WINDOW_SECS
    )
    template_name = task.get("template_name") or template_id

    logger.info(
        f"[{task_id}] starting: template={template_name} kind={kind} "
        f"attempt={attempts}/{max_attempts}"
    )

    hb_stop = threading.Event()
    cancel_stop = threading.Event()
    cancel_flag = threading.Event()

    hb_thread = threading.Thread(
        target=_heartbeat_thread,
        args=(task_id, lease_secs, hb_stop),
        name=f"hb-{task_id[:8]}",
        daemon=True,
    )
    hb_thread.start()

    cc_thread = threading.Thread(
        target=_cancel_check_thread,
        args=(task_id, cancel_flag, cancel_stop),
        name=f"cc-{task_id[:8]}",
        daemon=True,
    )
    cc_thread.start()

    result: Optional[Dict[str, Any]] = None
    error: Optional[Exception] = None

    try:
        payload = _resolve_payload(task)

        if kind == "script":
            result = _run_script(task, payload, cancel_flag)
        elif kind == "agent":
            result = _run_agent(task, payload, cancel_flag)
        else:
            raise ValueError(f"Unknown task kind: {kind!r}")

    except Exception as exc:
        error = exc
    finally:
        hb_stop.set()
        cancel_stop.set()

    # Check for lease revocation (force-cancel by another process)
    if _is_lease_revoked(task_id):
        logger.warning(
            f"[{task_id}] lease revoked during execution -- "
            "leaving status unchanged for next worker to reclaim"
        )
        return

    # --- Write-back ---
    if error is None and result is not None:
        # SUCCESS
        try:
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                """
                -- OVERRIDE: worker_daemon
                UPDATE claude.task_queue
                SET status       = 'completed',
                    result       = %s,
                    output_text  = %s,
                    completed_at = now(),
                    last_error   = NULL
                WHERE task_id = %s
                """,
                (
                    json.dumps(result),
                    (result.get("output") or "")[:10000],
                    task_id,
                ),
            )
            conn.commit()
            cur.close()
            conn.close()
            logger.info(f"[{task_id}] completed successfully")
        except Exception as exc:
            logger.error(f"[{task_id}] success write-back failed: {exc}")

        try:
            route_findings(task, result)
        except Exception as exc:
            logger.error(f"[{task_id}] route_findings error: {exc}")

    else:
        # FAILURE
        err_str = str(error)
        err_class = type(error).__name__ if error else "Unknown"
        logger.error(f"[{task_id}] failed: [{err_class}] {err_str[:500]}")

        is_trans = _is_transient(error, transient_classes) if error else False
        can_retry = is_trans and (attempts < max_attempts)

        if can_retry:
            backoff = cf_backoff_seconds(
                attempt=attempts,
                base=backoff_base,
                cap=backoff_max,
                jitter_pct=jitter_pct,
            )
            try:
                conn = _get_conn()
                cur = conn.cursor()
                cur.execute(
                    """
                    -- OVERRIDE: worker_daemon
                    UPDATE claude.task_queue
                    SET status          = 'pending',
                        claimed_by      = NULL,
                        claimed_at      = NULL,
                        claimed_until   = NULL,
                        next_attempt_at = now() + (%s * interval '1 second'),
                        last_error      = %s
                    WHERE task_id = %s
                    """,
                    (backoff, f"[{err_class}] {err_str[:1000]}", task_id),
                )
                conn.commit()
                cur.close()
                conn.close()
                logger.info(
                    f"[{task_id}] transient failure, retry in {backoff}s "
                    f"(attempt {attempts}/{max_attempts})"
                )
            except Exception as exc:
                logger.error(f"[{task_id}] retry write-back failed: {exc}")
        else:
            # Permanent or exhausted
            reason = (
                "max_attempts_exceeded" if attempts >= max_attempts else "permanent_error"
            )
            try:
                conn = _get_conn()
                cur = conn.cursor()
                cur.execute(
                    """
                    -- OVERRIDE: worker_daemon
                    UPDATE claude.task_queue
                    SET status       = 'dead_letter',
                        last_error   = %s,
                        completed_at = now()
                    WHERE task_id = %s
                    """,
                    (f"[{reason}] [{err_class}] {err_str[:1000]}", task_id),
                )
                conn.commit()
                cur.close()
                conn.close()
                logger.warning(f"[{task_id}] dead_letter: {reason} [{err_class}]")
            except Exception as exc:
                logger.error(f"[{task_id}] dead_letter write-back failed: {exc}")

            # Trip per-template circuit breaker
            if template_id:
                try:
                    cb = CircuitBreaker(
                        name=f"job_template:{template_id}",
                        threshold_fails=pause_threshold_fails,
                        window_secs=pause_threshold_window,
                        on_trip=lambda: set_template_paused(
                            template_id,
                            f"CircuitBreaker tripped: {pause_threshold_fails} "
                            f"failures in {pause_threshold_window}s window",
                        ),
                    )
                    cb.record_failure(
                        error_class=err_class,
                        error_message=err_str[:500],
                    )
                except Exception as exc:
                    logger.error(
                        f"[{task_id}] circuit breaker record_failure error: {exc}"
                    )


# ---------------------------------------------------------------------------
# graceful_drain
# ---------------------------------------------------------------------------
def graceful_drain(deadline_secs: int = CF_DEFAULT_DRAIN_DEADLINE_SECS) -> None:
    """
    Initiate graceful shutdown on SIGTERM.

    1. Sets _shutting_down so the claim loop exits without claiming new tasks.
    2. Waits for in-flight futures up to deadline_secs.
    3. Logs a warning and returns (caller does sys.exit) after deadline.
    """
    logger.info(
        f"graceful_drain: waiting up to {deadline_secs}s for in-flight tasks"
    )
    _shutting_down.set()

    with _futures_lock:
        active = list(_active_futures)

    if active:
        remaining = deadline_secs
        wait(active, timeout=remaining)
        still_running = [f for f in active if not f.done()]
        if still_running:
            logger.warning(
                f"graceful_drain: {len(still_running)} tasks still running after "
                f"{deadline_secs}s -- hard exit"
            )

    logger.info("graceful_drain: complete")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global logger

    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <project_name>", file=sys.stderr)
        sys.exit(1)

    project_name = sys.argv[1]
    worker_id = f"{WORKER_ID_PREFIX}-{project_name}-{os.getpid()}"

    ctx = DaemonContext(
        name="task-worker",
        project_name=project_name,
        port_range_start=9900,
        port_range_size=100,
        idle_timeout_secs=IDLE_TIMEOUT_SECS,
    )

    # Guard against double-spawn
    if ctx.is_daemon_alive():
        info = ctx.read_pid_file()
        print(
            f"task-worker already running (PID {info.get('pid') if info else '?'}), exiting",
            file=sys.stderr,
        )
        sys.exit(0)

    port = ctx.find_available_port()
    logger = ctx.setup_logger()
    logger.info(
        f"task-worker starting: project={project_name} pid={os.getpid()} "
        f"worker_id={worker_id} port_slot={port} "
        f"pools: script={CF_SCRIPT_WORKER_COUNT} agent={CF_AGENT_WORKER_COUNT}"
    )

    ctx.write_pid_file(os.getpid(), port)

    # SIGTERM -> graceful_drain in background thread so signal handler returns fast
    def _sigterm(signum, frame):
        logger.info(f"Received signal {signum}, starting graceful drain")
        t = threading.Thread(
            target=_do_drain_and_exit,
            daemon=True,
        )
        t.start()

    def _do_drain_and_exit():
        graceful_drain(deadline_secs=CF_DEFAULT_DRAIN_DEADLINE_SECS)
        ctx.cleanup()
        sys.exit(0)

    ctx.install_sigterm_handler(on_shutdown=_sigterm)

    script_pool = ThreadPoolExecutor(
        max_workers=CF_SCRIPT_WORKER_COUNT,
        thread_name_prefix="task-worker-script",
    )
    agent_pool = ThreadPoolExecutor(
        max_workers=CF_AGENT_WORKER_COUNT,
        thread_name_prefix="task-worker-agent",
    )

    def _on_idle_timeout():
        logger.info(
            f"idle timeout reached ({IDLE_TIMEOUT_SECS}s with empty queue); "
            f"initiating graceful shutdown"
        )
        _sigterm(None, None)

    idle_timer_armed = False

    try:
        consecutive_errors = 0
        while not _shutting_down.is_set():
            try:
                task = claim_next_task(worker_id)
            except Exception as exc:
                consecutive_errors += 1
                backoff = min(2 ** consecutive_errors, 60)
                logger.error(
                    f"claim loop error #{consecutive_errors}: {exc}; sleeping {backoff}s"
                )
                _shutting_down.wait(timeout=float(backoff))
                continue

            if task is None:
                consecutive_errors = 0
                if not idle_timer_armed:
                    ctx.reset_idle_timer(_on_idle_timeout)
                    idle_timer_armed = True
                _shutting_down.wait(timeout=CLAIM_POLL_INTERVAL)
                continue

            consecutive_errors = 0
            if idle_timer_armed:
                ctx.cancel_idle_timer()
                idle_timer_armed = False
            kind = str(task.get("kind") or "script")
            pool = script_pool if kind == "script" else agent_pool

            future = pool.submit(execute_task, task)

            with _futures_lock:
                _active_futures.append(future)

            def _on_done(f: Future) -> None:
                with _futures_lock:
                    try:
                        _active_futures.remove(f)
                    except ValueError:
                        pass
                if f.exception():
                    logger.error(
                        f"Unhandled exception from execute_task: {f.exception()}"
                    )

            future.add_done_callback(_on_done)

    finally:
        logger.info("Shutting down thread pools")
        script_pool.shutdown(wait=False)
        agent_pool.shutdown(wait=False)
        ctx.cleanup()
        logger.info("task-worker exited")


if __name__ == "__main__":
    main()
