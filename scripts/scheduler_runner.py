#!/usr/bin/env python3
"""
Scheduler Runner - Execute due scheduled jobs

This script:
1. Checks for jobs that are due (next_run <= now or schedule-based)
2. Executes them via subprocess or orchestrator agents
3. Updates job status and history
4. Calculates next_run times

Can be run:
- Manually: python scheduler_runner.py
- Via Windows Task Scheduler (every 5-15 minutes)
- Via cron on Linux

Author: claude-code-unified
Date: 2025-12-07
"""

import sys
import os
import io
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import POSTGRES_CONFIG

import psycopg2
from psycopg2.extras import RealDictCursor


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)


def parse_schedule(schedule: str) -> Optional[timedelta]:
    """
    Parse schedule string into timedelta for next_run calculation.

    Supports:
    - 'daily' -> 1 day
    - 'weekly' -> 7 days
    - 'hourly' -> 1 hour
    - 'every 5 minutes' -> 5 minutes
    - 'every 2 hours' -> 2 hours
    """
    if not schedule:
        return None

    schedule = schedule.lower().strip()

    if schedule == 'daily':
        return timedelta(days=1)
    elif schedule == 'weekly':
        return timedelta(weeks=1)
    elif schedule == 'hourly':
        return timedelta(hours=1)
    elif schedule.startswith('every '):
        parts = schedule.replace('every ', '').split()
        if len(parts) >= 2:
            try:
                num = int(parts[0])
                unit = parts[1].rstrip('s')  # Remove trailing 's'
                if unit == 'minute':
                    return timedelta(minutes=num)
                elif unit == 'hour':
                    return timedelta(hours=num)
                elif unit == 'day':
                    return timedelta(days=num)
            except ValueError:
                pass

    return None


def calculate_next_run(schedule: str, last_run: Optional[datetime] = None) -> Optional[datetime]:
    """Calculate next run time based on schedule."""
    interval = parse_schedule(schedule)
    if not interval:
        return None

    base_time = last_run or datetime.now()
    next_run = base_time + interval

    # If next_run is in the past, calculate from now
    if next_run < datetime.now():
        next_run = datetime.now() + interval

    return next_run


def get_due_jobs(conn) -> List[Dict[str, Any]]:
    """Get jobs that are due to run."""
    cur = conn.cursor()

    # Get scheduled jobs that are:
    # 1. Active
    # 2. Have a command (for subprocess) OR agent_type (for agent execution)
    # 3. Either: next_run is past, OR trigger_type is 'scheduled' and never run
    cur.execute("""
        SELECT job_id, job_name, command, working_directory, schedule,
               trigger_type, timeout_seconds, last_run, next_run, priority,
               COALESCE(execution_type, 'subprocess') as execution_type,
               agent_type, agent_config
        FROM claude.scheduled_jobs
        WHERE is_active = true
          AND (command IS NOT NULL OR agent_type IS NOT NULL)
          AND trigger_type IN ('scheduled', 'schedule')
          AND (
              next_run <= NOW()
              OR (next_run IS NULL AND last_run IS NULL)
              OR (next_run IS NULL AND last_run < NOW() - INTERVAL '1 day')
          )
        ORDER BY priority ASC, next_run ASC NULLS FIRST
        LIMIT 5
    """)

    return [dict(row) for row in cur.fetchall()]


def run_job_via_agent(job: Dict[str, Any], conn) -> Dict[str, Any]:
    """Execute a job via orchestrator agent."""
    import requests

    job_name = job['job_name']
    agent_type = job['agent_type']
    agent_config = job.get('agent_config') or {}
    working_dir = job['working_directory'] or r'C:\Projects\claude-family'

    # Build task description from command or config
    task = agent_config.get('task') or job['command'] or f"Execute job: {job_name}"

    print(f"\n▶ Running via agent: {job_name}")
    print(f"  Agent: {agent_type}")
    print(f"  Task: {task[:100]}...")

    # For now, we'll use subprocess to call claude CLI with the agent
    # In future, this could use MCP directly
    cmd = f'claude --print "{task}" --allowedTools "Read,Write,Edit,Bash,mcp__postgres,mcp__filesystem"'

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=job['timeout_seconds'] or 300,
            encoding='utf-8',
            errors='replace'
        )
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr if result.returncode != 0 else None
        }
    except Exception as e:
        return {
            'success': False,
            'output': None,
            'error': str(e)
        }


def run_job(job: Dict[str, Any], conn) -> Dict[str, Any]:
    """Execute a single job and return results."""
    job_id = job['job_id']
    job_name = job['job_name']
    execution_type = job.get('execution_type', 'subprocess')
    command = job['command']
    working_dir = job['working_directory'] or r'C:\Projects\claude-family'
    timeout = job['timeout_seconds'] or 300

    print(f"\n▶ Running: {job_name}")
    if execution_type == 'agent':
        print(f"  Agent: {job.get('agent_type')}")
    else:
        print(f"  Command: {command}")

    started_at = datetime.now()

    # Log run start to history
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claude.job_run_history (job_id, started_at, triggered_by, status)
        VALUES (%s, %s, 'scheduler_runner', 'running')
        RETURNING id
    """, (job_id, started_at))
    run_id = cur.fetchone()['id']
    conn.commit()

    try:
        if execution_type == 'agent' and job.get('agent_type'):
            # Execute via orchestrator agent
            agent_result = run_job_via_agent(job, conn)
            completed_at = datetime.now()
            status = 'SUCCESS' if agent_result['success'] else 'FAILED'
            output = agent_result.get('output', '')[:10000] if agent_result.get('output') else None
            error = agent_result.get('error', '')[:5000] if agent_result.get('error') else None
        else:
            # Execute via subprocess
            result = subprocess.run(
                command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding='utf-8',
                errors='replace'
            )

            completed_at = datetime.now()
            status = 'SUCCESS' if result.returncode == 0 else 'FAILED'
            output = result.stdout[:10000] if result.stdout else None
            error = result.stderr[:5000] if result.stderr else None

            # For reviewer scripts, exit code 1 means "issues found" not "error"
            if result.returncode == 1 and ('review' in job_name.lower() or 'monitor' in job_name.lower()):
                status = 'ISSUES_FOUND'

        print(f"  Status: {status}")

    except subprocess.TimeoutExpired:
        completed_at = datetime.now()
        status = 'TIMEOUT'
        output = None
        error = f'Job timed out after {timeout} seconds'
        print(f"  Status: TIMEOUT")

    except Exception as e:
        completed_at = datetime.now()
        status = 'ERROR'
        output = None
        error = str(e)
        print(f"  Status: ERROR - {e}")

    # Update run history
    cur.execute("""
        UPDATE claude.job_run_history
        SET completed_at = %s, status = %s, output = %s, error_message = %s
        WHERE id = %s
    """, (completed_at, status, output, error, run_id))

    # Update job record
    next_run = calculate_next_run(job['schedule'], completed_at)
    cur.execute("""
        UPDATE claude.scheduled_jobs
        SET last_run = %s,
            last_status = %s,
            last_output = %s,
            last_error = %s,
            next_run = %s,
            run_count = COALESCE(run_count, 0) + 1,
            success_count = COALESCE(success_count, 0) + CASE WHEN %s IN ('SUCCESS', 'ISSUES_FOUND') THEN 1 ELSE 0 END
        WHERE job_id = %s
    """, (completed_at, status, output, error, next_run, status, job_id))

    conn.commit()

    return {
        'job_name': job_name,
        'status': status,
        'duration_seconds': (completed_at - started_at).total_seconds(),
        'next_run': next_run
    }


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Run scheduled jobs')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without executing')
    parser.add_argument('--force', type=str, help='Force run a specific job by name')
    parser.add_argument('--list', action='store_true', help='List all scheduled jobs')
    args = parser.parse_args()

    print("=" * 60)
    print("Scheduler Runner")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    conn = get_db_connection()

    if args.list:
        cur = conn.cursor()
        cur.execute("""
            SELECT job_name, trigger_type, schedule, is_active, last_run, next_run, last_status
            FROM claude.scheduled_jobs
            WHERE command IS NOT NULL
            ORDER BY trigger_type, job_name
        """)
        jobs = cur.fetchall()
        print(f"\nFound {len(jobs)} jobs with commands:\n")
        for job in jobs:
            status_icon = "✅" if job['is_active'] else "⏸️"
            last = job['last_run'].strftime('%Y-%m-%d %H:%M') if job['last_run'] else 'Never'
            next_r = job['next_run'].strftime('%Y-%m-%d %H:%M') if job['next_run'] else 'Not set'
            print(f"{status_icon} {job['job_name']}")
            print(f"   Type: {job['trigger_type']} | Schedule: {job['schedule']}")
            print(f"   Last: {last} ({job['last_status'] or 'N/A'}) | Next: {next_r}")
        conn.close()
        return 0

    if args.force:
        cur = conn.cursor()
        cur.execute("""
            SELECT job_id, job_name, command, working_directory, schedule,
                   trigger_type, timeout_seconds, last_run, next_run, priority
            FROM claude.scheduled_jobs
            WHERE job_name ILIKE %s AND command IS NOT NULL
        """, (f'%{args.force}%',))
        jobs = [dict(row) for row in cur.fetchall()]
        if not jobs:
            print(f"No job found matching '{args.force}'")
            conn.close()
            return 1
    else:
        jobs = get_due_jobs(conn)

    if not jobs:
        print("\n✅ No jobs due to run")
        conn.close()
        return 0

    print(f"\n📋 Found {len(jobs)} job(s) to run:")
    for job in jobs:
        print(f"  - {job['job_name']} (schedule: {job['schedule']})")

    if args.dry_run:
        print("\n[DRY RUN] Would execute the above jobs")
        conn.close()
        return 0

    # Execute jobs
    results = []
    for job in jobs:
        result = run_job(job, conn)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    success = sum(1 for r in results if r['status'] in ('SUCCESS', 'ISSUES_FOUND'))
    failed = len(results) - success

    for r in results:
        icon = "✅" if r['status'] in ('SUCCESS', 'ISSUES_FOUND') else "❌"
        next_str = r['next_run'].strftime('%Y-%m-%d %H:%M') if r['next_run'] else 'N/A'
        print(f"  {icon} {r['job_name']}: {r['status']} ({r['duration_seconds']:.1f}s) → Next: {next_str}")

    print(f"\nTotal: {success} succeeded, {failed} failed")

    conn.close()
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
