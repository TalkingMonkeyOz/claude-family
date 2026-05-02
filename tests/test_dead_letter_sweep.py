"""Tests for dead_letter_sweep.py (F224 — Tier 3 surfacing)."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import psycopg2
import pytest

# Config
SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SWEEP_SCRIPT = os.path.join(SCRIPT_DIR, "scripts", "jobs", "dead_letter_sweep.py")

sys.path.insert(0, os.path.join(SCRIPT_DIR, "scripts"))
try:
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or os.environ.get("DATABASE_URI", "")
except Exception:
    DB_URI = os.environ.get("DATABASE_URI", "")


@pytest.fixture
def db_conn():
    """Fixture: DB connection for test setup/teardown."""
    conn = psycopg2.connect(DB_URI, connect_timeout=5)
    yield conn
    conn.close()


def cleanup_test_tasks(cur, task_ids):
    """Helper: delete test task rows."""
    if task_ids:
        placeholders = ",".join(["%s"] * len(task_ids))
        cur.execute(f"DELETE FROM claude.task_queue WHERE task_id IN ({placeholders})", task_ids)


def cleanup_test_feedback(cur, feedback_ids):
    """Helper: delete test feedback rows."""
    if feedback_ids:
        placeholders = ",".join(["%s"] * len(feedback_ids))
        cur.execute(f"DELETE FROM claude.feedback WHERE feedback_id IN ({placeholders})", feedback_ids)


class TestDeadLetterSweep:
    """Test dead_letter_sweep.py behavior."""

    def test_stuck_dead_letter_creates_feedback(self, db_conn):
        """Stuck dead_letter row (>24h, unsurfaced, unresolved) should create feedback."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=2)

        try:
            # Create a stuck dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, last_error, attempts
                ) VALUES (%s, 'dead_letter', %s, 'Test error', 3)
            """, (task_id, completed_at))
            db_conn.commit()

            # Run sweep
            result = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result.returncode == 0, f"Sweep failed: {result.stderr}"
            output = json.loads(result.stdout)
            assert output["success"], f"Sweep returned error: {output}"
            assert output["stuck_count"] == 1

            # Verify feedback was created and linked
            cur.execute("""
                SELECT feedback_id FROM claude.task_queue WHERE task_id = %s
            """, (task_id,))
            feedback_id = cur.fetchone()[0]
            assert feedback_id is not None, "surfaced_as_feedback_id not set"

            # Verify feedback row exists with correct type
            cur.execute("""
                SELECT feedback_type, priority FROM claude.feedback WHERE feedback_id = %s
            """, (feedback_id,))
            ftype, priority = cur.fetchone()
            assert ftype == "bug"
            assert priority == 2  # medium

            # Cleanup
            cleanup_test_feedback(cur, [feedback_id])
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_already_surfaced_row_skipped(self, db_conn):
        """Row with surfaced_as_feedback_id already set should be skipped."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        feedback_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=2)

        try:
            # Create an already-surfaced dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, surfaced_as_feedback_id, last_error, attempts
                ) VALUES (%s, 'dead_letter', %s, %s, 'Old error', 3)
            """, (task_id, completed_at, feedback_id))
            db_conn.commit()

            # Run sweep
            result = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result.returncode == 0
            output = json.loads(result.stdout)
            assert output["stuck_count"] == 0, "Should skip already-surfaced row"

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_resolved_dead_letter_skipped(self, db_conn):
        """Dead_letter with resolution_status set should be skipped."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=2)

        try:
            # Create a resolved dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, resolution_status, last_error, attempts
                ) VALUES (%s, 'dead_letter', %s, 'fixed', 'Old error', 3)
            """, (task_id, completed_at))
            db_conn.commit()

            # Run sweep
            result = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result.returncode == 0
            output = json.loads(result.stdout)
            assert output["stuck_count"] == 0, "Should skip resolved dead_letter"

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_recent_dead_letter_skipped(self, db_conn):
        """Dead_letter with completed_at < 24h ago should be skipped."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(hours=12)  # Recent

        try:
            # Create a recent dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, last_error, attempts
                ) VALUES (%s, 'dead_letter', %s, 'Test error', 2)
            """, (task_id, completed_at))
            db_conn.commit()

            # Run sweep
            result = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result.returncode == 0
            output = json.loads(result.stdout)
            assert output["stuck_count"] == 0, "Should skip recent dead_letter"

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_idempotent_rerun(self, db_conn):
        """Running sweep twice should produce zero new feedback on second run."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=2)

        try:
            # Create a stuck dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, last_error, attempts
                ) VALUES (%s, 'dead_letter', %s, 'Test error', 3)
            """, (task_id, completed_at))
            db_conn.commit()

            # Run sweep first time
            result1 = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result1.returncode == 0
            output1 = json.loads(result1.stdout)
            assert output1["stuck_count"] == 1

            # Run sweep second time
            result2 = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result2.returncode == 0
            output2 = json.loads(result2.stdout)
            assert output2["stuck_count"] == 0, "Second run should find zero new stuck rows"

            # Cleanup
            cur.execute("SELECT surfaced_as_feedback_id FROM claude.task_queue WHERE task_id = %s", (task_id,))
            feedback_id = cur.fetchone()[0]
            cleanup_test_feedback(cur, [feedback_id])
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()
