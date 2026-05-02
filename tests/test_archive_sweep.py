"""Tests for archive_sweep.py (F224 — retention policy)."""
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
SWEEP_SCRIPT = os.path.join(SCRIPT_DIR, "scripts", "jobs", "archive_sweep.py")

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
    """Helper: delete test task rows from both tables."""
    if task_ids:
        placeholders = ",".join(["%s"] * len(task_ids))
        cur.execute(f"DELETE FROM claude.task_queue WHERE task_id IN ({placeholders})", task_ids)
        cur.execute(f"DELETE FROM claude.task_queue_archive WHERE task_id IN ({placeholders})", task_ids)


class TestArchiveSweep:
    """Test archive_sweep.py behavior."""

    def test_completed_over_90_days_archived(self, db_conn):
        """Completed task > 90 days old should be archived."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=100)

        try:
            # Create an old completed task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at
                ) VALUES (%s, 'completed', %s)
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
            assert output["success"]
            assert output["archived_count"] == 1

            # Verify task was moved to archive
            cur.execute("SELECT task_id FROM claude.task_queue_archive WHERE task_id = %s", (task_id,))
            assert cur.fetchone() is not None, "Task not in archive"

            # Verify task removed from live table
            cur.execute("SELECT task_id FROM claude.task_queue WHERE task_id = %s", (task_id,))
            assert cur.fetchone() is None, "Task still in live table"

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_completed_under_90_days_preserved(self, db_conn):
        """Completed task < 90 days old should NOT be archived."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=60)

        try:
            # Create a recent completed task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at
                ) VALUES (%s, 'completed', %s)
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
            assert output["archived_count"] == 0, "Should not archive recent completed task"

            # Verify task still in live table
            cur.execute("SELECT task_id FROM claude.task_queue WHERE task_id = %s", (task_id,))
            assert cur.fetchone() is not None

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_unresolved_dead_letter_never_archived(self, db_conn):
        """Unresolved dead_letter should NEVER be archived (sticky-until-triaged)."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=100)

        try:
            # Create an old unresolved dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, resolution_status
                ) VALUES (%s, 'dead_letter', %s, NULL)
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
            assert output["archived_count"] == 0, "Should never archive unresolved dead_letter"

            # Verify task still in live table
            cur.execute("SELECT task_id FROM claude.task_queue WHERE task_id = %s", (task_id,))
            assert cur.fetchone() is not None

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_resolved_dead_letter_over_30_days_archived(self, db_conn):
        """Resolved dead_letter > 30 days old should be archived."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        resolved_at = datetime.utcnow() - timedelta(days=40)

        try:
            # Create an old resolved dead_letter task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at, resolution_status, resolved_at
                ) VALUES (%s, 'dead_letter', %s, 'fixed', %s)
            """, (task_id, resolved_at - timedelta(hours=1), resolved_at))
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
            assert output["archived_count"] == 1

            # Verify task was moved to archive
            cur.execute("SELECT task_id FROM claude.task_queue_archive WHERE task_id = %s", (task_id,))
            assert cur.fetchone() is not None

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_cancelled_over_30_days_archived(self, db_conn):
        """Cancelled task > 30 days old should be archived."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=40)

        try:
            # Create an old cancelled task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at
                ) VALUES (%s, 'cancelled', %s)
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
            assert output["archived_count"] == 1

            # Verify task was moved to archive
            cur.execute("SELECT task_id FROM claude.task_queue_archive WHERE task_id = %s", (task_id,))
            assert cur.fetchone() is not None

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()

    def test_idempotent_rerun(self, db_conn):
        """Running sweep twice should produce zero archival on second run."""
        cur = db_conn.cursor()
        task_id = str(uuid4())
        completed_at = datetime.utcnow() - timedelta(days=100)

        try:
            # Create an old completed task
            cur.execute("""
                INSERT INTO claude.task_queue (
                    task_id, status, completed_at
                ) VALUES (%s, 'completed', %s)
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
            assert output1["archived_count"] == 1

            # Run sweep second time
            result2 = subprocess.run(
                [sys.executable, SWEEP_SCRIPT],
                capture_output=True,
                text=True,
                env={**os.environ, "DATABASE_URI": DB_URI},
            )
            assert result2.returncode == 0
            output2 = json.loads(result2.stdout)
            assert output2["archived_count"] == 0, "Second run should archive zero new rows"

            # Cleanup
            cleanup_test_tasks(cur, [task_id])
            db_conn.commit()
        finally:
            cur.close()
