#!/usr/bin/env python3
"""
Job Runner - Master background job executor for Claude Family.

Reads scheduled jobs from claude.scheduled_jobs, checks if each is due,
runs due jobs as subprocesses, and logs results to claude.job_run_history.

Designed to be triggered by Windows Task Scheduler (hourly + at login).
Silent, lightweight, idempotent. Catches up on missed runs.

Usage:
    python job_runner.py              # Run all due jobs
    python job_runner.py --dry-run    # Show what would run without executing
    python job_runner.py --force JOB  # Force-run a specific job by name
    python job_runner.py --list       # List all jobs and their status

Author: Claude Family
Date: 2026-03-14
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Setup logging - silent by default, logs to file
LOG_DIR = Path.home() / ".claude" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "job_runner.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)
logger = logging.getLogger("job_runner")

# Database connection
DB_URL = os.environ.get("DATABASE_URL", "")
if not DB_URL:
    # Try loading from .env files
    for env_path in [
        Path.home() / ".claude" / ".env",
        Path(__file__).parent.parent / ".env",
    ]:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    DB_URL = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
        if DB_URL:
            break


def get_db_connection():
    """Get a database connection."""
    try:
        import psycopg
        return psycopg.connect(DB_URL, row_factory=psycopg.rows.dict_row)
    except ImportError:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(DB_URL)
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        return conn


def parse_schedule(schedule: str, trigger_type: str) -> dict:
    """Parse schedule string into a normalized format.

    Returns dict with: interval_hours, interval_days, cron (if applicable),
    day_of_week (0=Mon, 6=Sun), hour, minute.
    """
    schedule_lower = schedule.lower().strip() if schedule else ""

    # Cron expressions (e.g., "0 6 * * *")
    if trigger_type == "cron" or (schedule and len(schedule.split()) == 5 and
                                   all(p.replace("*", "").replace("/", "").replace(",", "").replace("-", "").isdigit() or p == "*"
                                       for p in schedule.split())):
        parts = schedule.split()
        return {
            "type": "cron",
            "minute": parts[0],
            "hour": parts[1],
            "day_of_month": parts[2],
            "month": parts[3],
            "day_of_week": parts[4],
        }

    # Human-readable schedules
    if "hourly" in schedule_lower:
        return {"type": "interval", "interval_hours": 1}
    elif "daily" in schedule_lower:
        hour = 6  # default
        if "@" in schedule:
            # Parse "Daily @ 6:00 AM" format
            import re
            match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', schedule, re.IGNORECASE)
            if match:
                hour = int(match.group(1))
                if match.group(3) and match.group(3).upper() == "PM" and hour != 12:
                    hour += 12
        return {"type": "interval", "interval_hours": 24, "preferred_hour": hour}
    elif "weekly" in schedule_lower:
        return {"type": "interval", "interval_hours": 168}  # 7 days
    elif "at logon" in schedule_lower:
        return {"type": "on_login"}

    # Fallback: treat as daily
    return {"type": "interval", "interval_hours": 24}


def is_job_due(job: dict) -> bool:
    """Check if a job is due to run based on its schedule and last_run."""
    if not job.get("is_active"):
        return False

    # Windows scheduler jobs are managed externally
    if job.get("trigger_type") == "windows_scheduler":
        return False

    # Session start jobs should only run during sessions, not from the runner
    if job.get("trigger_type") == "session_start":
        return False

    schedule_info = parse_schedule(job.get("schedule", ""), job.get("trigger_type", ""))
    last_run = job.get("last_run")
    now = datetime.now()

    if last_run is None:
        # Never run before — it's due
        return True

    if schedule_info["type"] == "interval":
        interval = timedelta(hours=schedule_info.get("interval_hours", 24))
        return (now - last_run) >= interval

    elif schedule_info["type"] == "cron":
        # Simplified cron check: has enough time passed since last run?
        # For daily crons (hour specified, * for day), check if we've passed that hour today
        hour = schedule_info.get("hour", "*")
        day_of_week = schedule_info.get("day_of_week", "*")

        if day_of_week != "*":
            # Weekly cron — check if 7 days have passed
            return (now - last_run) >= timedelta(days=7)
        elif hour != "*":
            # Daily cron — check if 24 hours have passed
            return (now - last_run) >= timedelta(hours=24)
        else:
            # Catch-all: run if more than 1 hour since last run
            return (now - last_run) >= timedelta(hours=1)

    elif schedule_info["type"] == "on_login":
        # Run once per day max
        return (now - last_run) >= timedelta(hours=12)

    return False


def run_job(job: dict, conn) -> dict:
    """Execute a single job and return the result."""
    job_name = job["job_name"]
    command = job.get("command", "")
    working_dir = job.get("working_directory", "C:\\Projects\\claude-family")
    timeout = job.get("timeout_seconds") or 300  # 5 minute default

    if not command:
        return {"status": "SKIPPED", "error": "No command defined"}

    # Normalize path separators
    if working_dir:
        working_dir = working_dir.replace("\\\\", "\\").replace("/", "\\")

    logger.info(f"Running job: {job_name}")
    logger.info(f"  Command: {command}")
    logger.info(f"  Working dir: {working_dir}")

    started_at = datetime.now()

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=working_dir if working_dir and os.path.isdir(working_dir) else None,
            env={**os.environ, "DATABASE_URL": DB_URL} if DB_URL else None,
        )

        completed_at = datetime.now()
        status = "SUCCESS" if result.returncode == 0 else "FAILED"
        output = result.stdout[:2000] if result.stdout else ""
        error = result.stderr[:2000] if result.stderr else ""

        if status == "FAILED":
            logger.warning(f"  Job {job_name} failed (exit code {result.returncode})")
            if error:
                logger.warning(f"  stderr: {error[:200]}")
        else:
            logger.info(f"  Job {job_name} completed successfully")

        return {
            "status": status,
            "output": output,
            "error": error,
            "started_at": started_at,
            "completed_at": completed_at,
        }

    except subprocess.TimeoutExpired:
        logger.error(f"  Job {job_name} timed out after {timeout}s")
        return {
            "status": "TIMEOUT",
            "error": f"Timed out after {timeout} seconds",
            "started_at": started_at,
            "completed_at": datetime.now(),
        }
    except Exception as e:
        logger.error(f"  Job {job_name} error: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
            "started_at": started_at,
            "completed_at": datetime.now(),
        }


def log_run(conn, job: dict, result: dict):
    """Log job run to job_run_history and update scheduled_jobs."""
    job_id = job["job_id"]

    with conn.cursor() as cur:
        # Insert into job_run_history
        cur.execute("""
            INSERT INTO claude.job_run_history
                (job_id, started_at, completed_at, triggered_by, status, output, error_message)
            VALUES (%s, %s, %s, 'job_runner', %s, %s, %s)
        """, (
            job_id,
            result["started_at"],
            result.get("completed_at"),
            result["status"],
            result.get("output", "")[:2000],
            result.get("error", "")[:2000],
        ))

        # Update scheduled_jobs
        run_count = (job.get("run_count") or 0) + 1
        success_count = (job.get("success_count") or 0) + (1 if result["status"] == "SUCCESS" else 0)

        cur.execute("""
            UPDATE claude.scheduled_jobs
            SET last_run = %s, last_status = %s, last_output = %s, last_error = %s,
                run_count = %s, success_count = %s
            WHERE job_id = %s
        """, (
            result.get("completed_at") or result["started_at"],
            result["status"],
            result.get("output", "")[:2000],
            result.get("error", "")[:2000],
            run_count,
            success_count,
            job_id,
        ))

    conn.commit()


def list_jobs(conn):
    """List all jobs and their status."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT job_name, schedule, trigger_type, is_active,
                   last_run, last_status, run_count, success_count
            FROM claude.scheduled_jobs
            ORDER BY is_active DESC, trigger_type, job_name
        """)
        jobs = cur.fetchall()

    print(f"\n{'Job Name':<40} {'Schedule':<20} {'Trigger':<15} {'Active':<7} {'Last Run':<12} {'Status':<10} {'Runs':>5}")
    print("-" * 115)
    for j in jobs:
        last_run = j["last_run"].strftime("%Y-%m-%d") if j.get("last_run") else "never"
        print(f"{j['job_name']:<40} {(j['schedule'] or '?'):<20} {(j['trigger_type'] or '?'):<15} "
              f"{'Yes' if j['is_active'] else 'No':<7} {last_run:<12} {(j['last_status'] or '-'):<10} "
              f"{j.get('run_count') or 0:>5}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Claude Family Job Runner")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without executing")
    parser.add_argument("--force", type=str, help="Force-run a specific job by name")
    parser.add_argument("--list", action="store_true", help="List all jobs and status")
    parser.add_argument("--verbose", action="store_true", help="Also print to console")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().addHandler(logging.StreamHandler())

    if not DB_URL:
        logger.error("DATABASE_URL not set. Cannot connect to database.")
        sys.exit(1)

    try:
        conn = get_db_connection()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        sys.exit(1)

    if args.list:
        list_jobs(conn)
        conn.close()
        return

    # Load jobs
    with conn.cursor() as cur:
        if args.force:
            cur.execute("""
                SELECT * FROM claude.scheduled_jobs
                WHERE job_name ILIKE %s AND is_active = true
            """, (f"%{args.force}%",))
        else:
            cur.execute("""
                SELECT * FROM claude.scheduled_jobs
                WHERE is_active = true
                  AND trigger_type NOT IN ('windows_scheduler', 'session_start')
            """)
        jobs = cur.fetchall()

    if not jobs:
        logger.info("No jobs found to process")
        conn.close()
        return

    due_jobs = []
    for job in jobs:
        if args.force or is_job_due(job):
            due_jobs.append(job)

    if not due_jobs:
        logger.info(f"Checked {len(jobs)} jobs — none are due")
        conn.close()
        return

    logger.info(f"Found {len(due_jobs)} due jobs out of {len(jobs)} checked")

    if args.dry_run:
        print(f"\nDry run — {len(due_jobs)} jobs would run:")
        for job in due_jobs:
            last = job["last_run"].strftime("%Y-%m-%d %H:%M") if job.get("last_run") else "never"
            print(f"  - {job['job_name']} (last: {last}, schedule: {job['schedule']})")
        conn.close()
        return

    # Run due jobs
    results = {"success": 0, "failed": 0, "skipped": 0}
    for job in due_jobs:
        result = run_job(job, conn)
        log_run(conn, job, result)

        if result["status"] == "SUCCESS":
            results["success"] += 1
        elif result["status"] == "SKIPPED":
            results["skipped"] += 1
        else:
            results["failed"] += 1

    logger.info(f"Run complete: {results['success']} success, {results['failed']} failed, {results['skipped']} skipped")
    conn.close()


if __name__ == "__main__":
    main()
