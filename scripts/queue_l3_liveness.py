#!/usr/bin/env python3
"""
L3 Liveness Check — Monitor-the-monitor for queue_health_check.

Runs during SessionStart to verify that the L2 queue_health_check job template
has executed recently (within CF_L3_LIVENESS_MAX_AGE_MINS). If stale, surfaces
a severity_critical finding.

This module is called from session_startup_hook_enhanced.py to ensure the queue
monitoring system itself is not broken.

Returns dict:
    {
        'healthy': bool,
        'finding': None | {'severity': 'critical', 'title': '...', 'body': '...', ...}
    }
"""

import logging
import sys
import os
from datetime import datetime, timedelta

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg
from cf_constants import CF_L3_LIVENESS_MAX_AGE_MINS

logger = logging.getLogger(__name__)

psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None


def check_queue_health_liveness():
    """Check if queue_health_check template has run recently.

    Queries job_run_history for the most recent run of the 'queue_health_check'
    template. If not found or too stale, returns a critical finding.

    Returns:
        {
            'healthy': bool,
            'finding': None | {severity, title, body, suggested_action}
        }
    """
    if not DB_AVAILABLE:
        # DB not available — log and continue (don't fail SessionStart)
        logger.warning("L3 liveness check: DB unavailable, skipping")
        return {
            'healthy': True,  # Optimistic — continue SessionStart
            'finding': None,
        }

    try:
        conn = get_db_connection(strict=False)
        if not conn:
            logger.warning("L3 liveness check: DB connection failed, continuing")
            return {
                'healthy': True,
                'finding': None,
            }

        cur = conn.cursor()

        # Query last run of queue_health_check template
        cur.execute("""
            SELECT j.template_id, j.template_name, j.status, j.completed_at
            FROM claude.job_run_history j
            WHERE j.template_name = 'queue_health_check'
            ORDER BY j.started_at DESC
            LIMIT 1
        """)
        row = cur.fetchone()
        cur.close()
        conn.close()

        if not row:
            # Never run
            return {
                'healthy': False,
                'finding': {
                    'severity': 'critical',
                    'title': 'Queue Health Check Never Run',
                    'body': 'The L2 queue_health_check job template has never executed. '
                           'It should be scheduled to run every 15 minutes.',
                    'suggested_action': 'Register queue_health_check as a scheduled_job and restart the worker daemon.',
                }
            }

        completed_at = row['completed_at']
        if completed_at is None:
            # Still running?
            return {
                'healthy': True,  # Optimistic
                'finding': None,
            }

        # Check staleness
        age = datetime.utcnow() - completed_at
        threshold = timedelta(minutes=CF_L3_LIVENESS_MAX_AGE_MINS)

        if age > threshold:
            return {
                'healthy': False,
                'finding': {
                    'severity': 'critical',
                    'title': 'Queue Health Check Stale',
                    'body': f'Last run of queue_health_check: {age.total_seconds() / 60:.0f} minutes ago. '
                           f'Expected within {CF_L3_LIVENESS_MAX_AGE_MINS} minutes.',
                    'suggested_action': 'Check job_runner.py logs for errors. Verify scheduled_jobs table. '
                                      'Restart worker daemon and verify it picks up the queue_health_check job.',
                }
            }

        # Healthy
        return {
            'healthy': True,
            'finding': None,
        }

    except Exception as e:
        # Log and continue (don't fail SessionStart on transient errors)
        logger.error(f"L3 liveness check error: {e}")
        return {
            'healthy': True,  # Optimistic — continue SessionStart
            'finding': None,
        }
