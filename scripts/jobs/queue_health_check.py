#!/usr/bin/env python3
"""
Queue Health Check — L2 monitoring script for Claude Family task queue.

Queries 4 metrics every 15 minutes (scheduled via claude.scheduled_jobs):
1. Backlog overflow (pending count > threshold)
2. Leaked leases (in_progress with expired claimed_until)
3. Dead-letter rate spike (dead_letter count in last hour > threshold)
4. Drain stall (no completion in N minutes AND backlog > 0)

Exit codes:
  0 = all healthy
  1 = high severity finding detected
  2 = critical severity finding detected

Output: JSON to stdout (for worker D2 routing) + structured log to
        ~/.claude/logs/queue_health_check.log (FB413-pattern rotating handler).

Findings route via Q4 D2 logic:
  - high → create feedback row (feedback_type='performance', title='...')
  - critical → create feedback + send message to claude-family project

Usage:
  python scripts/jobs/queue_health_check.py
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Shared credential loading from scripts/config.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import get_db_connection, detect_psycopg, setup_hook_logging

# Import thresholds from cf_constants.py (same directory)
from cf_constants import (
    CF_BACKLOG_ALERT_THRESHOLD,
    CF_DEAD_LETTER_RATE_THRESHOLD,
    CF_LEAKED_LEASE_THRESHOLD,
    CF_DRAIN_STALL_SECS,
)

# Setup logging (rotating, per FB413 pattern)
logger = setup_hook_logging(__name__)

psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None


def get_db_connection_safe():
    """Get DB connection, handle gracefully if unavailable."""
    if not DB_AVAILABLE:
        return None
    try:
        return get_db_connection(strict=False)
    except Exception as e:
        logger.error(f"Failed to get DB connection: {e}")
        return None


def query_queue_metrics():
    """Query 4 queue health metrics from the database.

    Returns dict with keys:
        backlog, leaked_leases, dead_letter_rate_1h, drain_stall_secs, backlog_pending
    """
    conn = get_db_connection_safe()
    if not conn:
        return None

    metrics = {
        'backlog': 0,
        'leaked_leases': 0,
        'dead_letter_rate_1h': 0,
        'drain_stall_secs': None,
        'backlog_pending': 0,
    }

    try:
        cur = conn.cursor()

        # 1. Backlog: count of pending tasks
        cur.execute("SELECT COUNT(*) as cnt FROM claude.task_queue WHERE status = 'pending'")
        row = cur.fetchone()
        metrics['backlog'] = row['cnt'] if row else 0
        metrics['backlog_pending'] = metrics['backlog']

        # 2. Leaked leases: in_progress tasks with expired claimed_until
        cur.execute(
            "SELECT COUNT(*) as cnt FROM claude.task_queue "
            "WHERE status = 'in_progress' AND claimed_until < NOW() - INTERVAL '5 minutes'"
        )
        row = cur.fetchone()
        metrics['leaked_leases'] = row['cnt'] if row else 0

        # 3. Dead-letter rate: count in last hour
        cur.execute(
            "SELECT COUNT(*) as cnt FROM claude.task_queue "
            "WHERE status = 'dead_letter' AND created_at > NOW() - INTERVAL '1 hour'"
        )
        row = cur.fetchone()
        metrics['dead_letter_rate_1h'] = row['cnt'] if row else 0

        # 4. Drain stall: time since last completion + backlog count
        cur.execute(
            "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(completed_at)))::int as stall_secs "
            "FROM claude.job_run_history WHERE status = 'completed'"
        )
        row = cur.fetchone()
        if row and row['stall_secs'] is not None:
            metrics['drain_stall_secs'] = row['stall_secs']
        else:
            # No completions yet, or NULL — assume recent
            metrics['drain_stall_secs'] = 0

        cur.close()
        conn.close()
        return metrics
    except Exception as e:
        logger.error(f"Error querying metrics: {e}")
        conn.close()
        return None


def check_queue_health():
    """Main health check logic.

    Returns dict:
        {
            'findings': [
                {'severity': 'high'|'critical', 'title': '...', 'body': '...', 'suggested_action': '...'}
            ],
            'metrics': {...},
            'summary': '...',
            'exit_code': 0|1|2
        }
    """
    metrics = query_queue_metrics()
    if metrics is None:
        return {
            'findings': [
                {
                    'severity': 'critical',
                    'title': 'Queue Health Check — DB Unavailable',
                    'body': 'Failed to connect to PostgreSQL or query metrics. Check DB connectivity.',
                    'suggested_action': 'Verify DATABASE_URL and DB service status.',
                }
            ],
            'metrics': None,
            'summary': 'Critical: DB unavailable',
            'exit_code': 2,
        }

    findings = []
    max_severity = None

    # Check 1: Backlog overflow
    if metrics['backlog'] > CF_BACKLOG_ALERT_THRESHOLD:
        severity = 'critical' if metrics['backlog'] > CF_BACKLOG_ALERT_THRESHOLD * 2 else 'high'
        findings.append({
            'severity': severity,
            'title': 'Queue Backlog Overflow',
            'body': f"Pending task count: {metrics['backlog']}. Threshold: {CF_BACKLOG_ALERT_THRESHOLD}.",
            'suggested_action': 'Check worker daemon health (CF_SCRIPT_WORKER_COUNT, CF_AGENT_WORKER_COUNT). '
                              'Review failed tasks in task_queue (status=dead_letter). Consider scaling workers.',
        })
        max_severity = 'critical' if severity == 'critical' else (max_severity or 'high')

    # Check 2: Leaked leases
    if metrics['leaked_leases'] > CF_LEAKED_LEASE_THRESHOLD:
        severity = 'critical' if metrics['leaked_leases'] > 5 else 'high'
        findings.append({
            'severity': severity,
            'title': 'Leaked Task Leases',
            'body': f"In-progress tasks with expired claimed_until: {metrics['leaked_leases']}. "
                   f"Threshold: {CF_LEAKED_LEASE_THRESHOLD}.",
            'suggested_action': 'Tasks are claimed but not completing or heartbeating. '
                              'Check worker logs for hangs. Consider killing stale workers and restarting daemon.',
        })
        max_severity = severity if (max_severity is None or severity == 'critical') else max_severity

    # Check 3: Dead-letter rate spike
    if metrics['dead_letter_rate_1h'] > CF_DEAD_LETTER_RATE_THRESHOLD:
        severity = 'critical' if metrics['dead_letter_rate_1h'] > CF_DEAD_LETTER_RATE_THRESHOLD * 2 else 'high'
        findings.append({
            'severity': severity,
            'title': 'Dead-Letter Rate Spike',
            'body': f"Dead-letter tasks in last hour: {metrics['dead_letter_rate_1h']}. "
                   f"Threshold: {CF_DEAD_LETTER_RATE_THRESHOLD}.",
            'suggested_action': 'Review task_queue WHERE status=dead_letter for error patterns. '
                              'Check template validation + error class configuration. Investigate root cause.',
        })
        max_severity = severity if (max_severity is None or severity == 'critical') else max_severity

    # Check 4: Drain stall
    if (metrics['drain_stall_secs'] is not None and
            metrics['drain_stall_secs'] > CF_DRAIN_STALL_SECS and
            metrics['backlog_pending'] > 0):
        findings.append({
            'severity': 'critical',
            'title': 'Queue Drain Stalled',
            'body': f"No task completions in {metrics['drain_stall_secs']} seconds. "
                   f"Threshold: {CF_DRAIN_STALL_SECS}s. Pending backlog: {metrics['backlog_pending']}.",
            'suggested_action': 'Daemon may be hung or workers paused (circuit breaker active). '
                              'Restart worker daemon. Check job_run_history for failures.',
        })
        max_severity = 'critical'

    # Build summary
    if findings:
        summary = f"{len(findings)} finding(s): " + ", ".join([f['title'] for f in findings])
    else:
        summary = "All metrics healthy"

    exit_code = 0
    if max_severity == 'critical':
        exit_code = 2
    elif max_severity == 'high':
        exit_code = 1

    return {
        'findings': findings,
        'metrics': metrics,
        'summary': summary,
        'exit_code': exit_code,
    }


def main():
    """Main entry point."""
    logger.info("Queue health check started")

    result = check_queue_health()

    # Output JSON (for worker D2 routing)
    print(json.dumps(result, indent=2))

    # Log the result
    logger.info(f"Health check summary: {result['summary']}")
    if result['findings']:
        for finding in result['findings']:
            logger.log(
                logging.CRITICAL if finding['severity'] == 'critical' else logging.WARNING,
                f"[{finding['severity'].upper()}] {finding['title']}: {finding['body']}"
            )

    sys.exit(result['exit_code'])


if __name__ == '__main__':
    main()
