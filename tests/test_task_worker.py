#!/usr/bin/env python3
"""
Tests for scripts/task_worker.py -- F224 BT697.

Coverage:
  - claim_next_task returns task when pending exists
  - claim_next_task returns None when template is paused
  - claim_next_task respects max_concurrent_runs (refuses when N already running)
  - execute_task happy path: updates completed + calls route_findings
  - execute_task transient failure: schedules retry with backoff
  - execute_task permanent failure: -> dead_letter
  - execute_task max_attempts exceeded: -> dead_letter regardless of error class
  - route_findings creates feedback for severity='high'
  - route_findings creates message + feedback for severity='critical'
  - graceful_drain: sets _shutting_down, waits for futures, exits within deadline
"""

import json
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional
from unittest import TestCase
from unittest.mock import MagicMock, call, patch

# Add scripts directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

# ---------------------------------------------------------------------------
# DB mock infrastructure
# ---------------------------------------------------------------------------

class MockCursor:
    """Minimal psycopg2 cursor mock."""

    def __init__(self, rows=None, description=None):
        self._rows = list(rows or [])
        self._execute_calls: List[Dict] = []
        self.description = description or [
            # Fake column description list for tuple-style rows
        ]

    def execute(self, sql, args=None):
        self._execute_calls.append({"sql": sql, "args": args})

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows = list(self._rows)
        self._rows.clear()
        return rows

    def close(self):
        pass


class MockConn:
    """Minimal psycopg2 connection mock."""

    def __init__(self, cursor: MockCursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False
        self.closed_flag = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        self.closed_flag = True


# ---------------------------------------------------------------------------
# Helpers to build realistic task dicts
# ---------------------------------------------------------------------------

def _make_task(
    kind="script",
    status="pending",
    attempts=1,
    max_attempts=3,
    is_idempotent=False,
    transient_error_classes=None,
    pause_threshold_fails=5,
    pause_threshold_window_secs=600,
    template_id=None,
    project_id=None,
) -> Dict[str, Any]:
    return {
        "task_id": str(uuid.uuid4()),
        "template_id": template_id or str(uuid.uuid4()),
        "template_version": 1,
        "payload_override": None,
        "status": status,
        "priority": 3,
        "project_id": project_id or str(uuid.uuid4()),
        "attempts": attempts,
        "started_at": None,
        "claimed_until": None,
        "cancel_requested": False,
        "template_name": "test-template",
        "kind": kind,
        "lease_duration_secs": 300,
        "max_attempts": max_attempts,
        "transient_error_classes": transient_error_classes
        or ["ConnectionError", "TimeoutError", "OSError"],
        "retry_backoff_base": 30,
        "retry_backoff_max": 3600,
        "retry_jitter_pct": 25,
        "is_idempotent": is_idempotent,
        "pause_threshold_fails": pause_threshold_fails,
        "pause_threshold_window_secs": pause_threshold_window_secs,
    }


# ---------------------------------------------------------------------------
# Test: claim_next_task
# ---------------------------------------------------------------------------

class TestClaimNextTask(TestCase):

    @patch("task_worker._get_conn")
    def test_returns_task_when_pending_exists(self, mock_get_conn):
        """claim_next_task returns a dict when the DB returns a claimed row."""
        task_id = str(uuid.uuid4())
        template_id = str(uuid.uuid4())

        # The UPDATE ... RETURNING row as a dict (simulates RealDictRow)
        returned_row = {
            "task_id": task_id,
            "template_id": template_id,
            "template_version": 1,
            "payload_override": None,
            "status": "in_progress",
            "priority": 3,
            "project_id": str(uuid.uuid4()),
            "attempts": 1,
            "started_at": None,
            "claimed_until": None,
            "cancel_requested": False,
            "template_name": "test-template",
            "kind": "script",
            "lease_duration_secs": 300,
            "max_attempts": 3,
            "transient_error_classes": ["ConnectionError"],
            "retry_backoff_base": 30,
            "retry_backoff_max": 3600,
            "retry_jitter_pct": 25,
            "is_idempotent": False,
            "pause_threshold_fails": 5,
            "pause_threshold_window_secs": 600,
        }

        cur = MockCursor(rows=[returned_row])
        conn = MockConn(cur)
        mock_get_conn.return_value = conn

        from task_worker import claim_next_task

        result = claim_next_task("worker-test")

        self.assertIsNotNone(result)
        self.assertEqual(result["task_id"], task_id)
        self.assertEqual(result["kind"], "script")
        self.assertTrue(conn.committed)

    @patch("task_worker._get_conn")
    def test_returns_none_when_no_claimable_task(self, mock_get_conn):
        """claim_next_task returns None when the UPDATE ... RETURNING has no rows."""
        cur = MockCursor(rows=[])  # no rows returned
        conn = MockConn(cur)
        mock_get_conn.return_value = conn

        from task_worker import claim_next_task

        result = claim_next_task("worker-test")
        self.assertIsNone(result)

    @patch("task_worker._get_conn")
    def test_returns_none_when_template_is_paused(self, mock_get_conn):
        """
        When all pending tasks have paused templates, the WHERE clause filters them
        out and the UPDATE returns no rows -> claim_next_task returns None.
        """
        # Simulate: paused template means the CTE returns nothing -> UPDATE has no match
        cur = MockCursor(rows=[])
        conn = MockConn(cur)
        mock_get_conn.return_value = conn

        from task_worker import claim_next_task

        result = claim_next_task("worker-test")
        self.assertIsNone(result)

        # Verify the SQL was issued (i.e. function did issue the query)
        self.assertTrue(len(cur._execute_calls) > 0)
        sql = cur._execute_calls[0]["sql"]
        self.assertIn("is_paused", sql)

    @patch("task_worker._get_conn")
    def test_respects_max_concurrent_runs(self, mock_get_conn):
        """
        When the subquery counting in_progress tasks equals max_concurrent_runs,
        the WHERE clause rejects all candidates -> UPDATE returns no rows -> None.
        """
        cur = MockCursor(rows=[])  # DB filtered everything out
        conn = MockConn(cur)
        mock_get_conn.return_value = conn

        from task_worker import claim_next_task

        result = claim_next_task("worker-test")
        self.assertIsNone(result)

        sql = cur._execute_calls[0]["sql"]
        self.assertIn("max_concurrent_runs", sql)
        self.assertIn("SKIP LOCKED", sql)


# ---------------------------------------------------------------------------
# Test: execute_task
# ---------------------------------------------------------------------------

class TestExecuteTask(TestCase):

    def _db_side_effect_factory(self, rows_by_call: List[List]):
        """Return a _get_conn side_effect that cycles through rows_by_call."""
        call_index = [0]

        def side_effect():
            idx = call_index[0]
            call_index[0] += 1
            rows = rows_by_call[idx] if idx < len(rows_by_call) else []
            return MockConn(MockCursor(rows=rows))

        return side_effect

    @patch("task_worker.route_findings")
    @patch("task_worker._is_lease_revoked", return_value=False)
    @patch("task_worker._resolve_payload", return_value={"command": ["echo", "ok"]})
    @patch("task_worker._run_script", return_value={"output": "ok", "findings": [], "return_code": 0, "duration_secs": 0.1})
    @patch("task_worker._get_conn")
    def test_happy_path_script_completes(
        self,
        mock_get_conn,
        mock_run_script,
        mock_resolve_payload,
        mock_lease_revoked,
        mock_route_findings,
    ):
        """execute_task on success: calls _run_script, writes status=completed, calls route_findings."""
        conn = MockConn(MockCursor(rows=[]))
        mock_get_conn.return_value = conn

        task = _make_task(kind="script")

        from task_worker import execute_task
        execute_task(task)

        mock_run_script.assert_called_once()
        mock_route_findings.assert_called_once()

        # Check the SQL written was a completed update
        sql_calls = conn._cursor._execute_calls
        status_update_sqls = [c["sql"] for c in sql_calls if "completed" in c["sql"]]
        self.assertTrue(len(status_update_sqls) > 0, "Expected a 'completed' UPDATE")

    @patch("task_worker.CircuitBreaker")
    @patch("task_worker._is_lease_revoked", return_value=False)
    @patch("task_worker._resolve_payload", return_value={"command": ["echo"]})
    @patch("task_worker._run_script", side_effect=ConnectionError("DB gone"))
    @patch("task_worker._get_conn")
    def test_transient_failure_schedules_retry(
        self,
        mock_get_conn,
        mock_run_script,
        mock_resolve_payload,
        mock_lease_revoked,
        mock_cb_class,
    ):
        """execute_task on transient error: writes status=pending with next_attempt_at."""
        conn = MockConn(MockCursor(rows=[]))
        mock_get_conn.return_value = conn

        task = _make_task(
            kind="script",
            attempts=1,
            max_attempts=3,
            transient_error_classes=["ConnectionError"],
        )

        from task_worker import execute_task
        execute_task(task)

        sql_calls = conn._cursor._execute_calls
        pending_sqls = [c["sql"] for c in sql_calls if "'pending'" in c["sql"] and "next_attempt_at" in c["sql"]]
        self.assertTrue(len(pending_sqls) > 0, "Expected a retry/pending UPDATE")
        # Circuit breaker should NOT be called for a retryable transient failure
        mock_cb_class.assert_not_called()

    @patch("task_worker.CircuitBreaker")
    @patch("task_worker._is_lease_revoked", return_value=False)
    @patch("task_worker._resolve_payload", return_value={"command": ["echo"]})
    @patch("task_worker._run_script", side_effect=ValueError("bad payload -- permanent"))
    @patch("task_worker._get_conn")
    def test_permanent_failure_goes_to_dead_letter(
        self,
        mock_get_conn,
        mock_run_script,
        mock_resolve_payload,
        mock_lease_revoked,
        mock_cb_class,
    ):
        """execute_task on permanent error (not transient): writes status=dead_letter."""
        conn = MockConn(MockCursor(rows=[]))
        mock_get_conn.return_value = conn

        task = _make_task(
            kind="script",
            attempts=1,
            max_attempts=3,
            transient_error_classes=["ConnectionError"],  # ValueError not in list
        )

        from task_worker import execute_task
        execute_task(task)

        sql_calls = conn._cursor._execute_calls
        dl_sqls = [c["sql"] for c in sql_calls if "dead_letter" in c["sql"]]
        self.assertTrue(len(dl_sqls) > 0, "Expected a dead_letter UPDATE")
        # Circuit breaker should be tripped for permanent failure
        mock_cb_class.assert_called_once()

    @patch("task_worker.CircuitBreaker")
    @patch("task_worker._is_lease_revoked", return_value=False)
    @patch("task_worker._resolve_payload", return_value={"command": ["echo"]})
    @patch("task_worker._run_script", side_effect=ConnectionError("timeout"))
    @patch("task_worker._get_conn")
    def test_max_attempts_exceeded_goes_to_dead_letter(
        self,
        mock_get_conn,
        mock_run_script,
        mock_resolve_payload,
        mock_lease_revoked,
        mock_cb_class,
    ):
        """execute_task: transient error but attempts >= max_attempts -> dead_letter."""
        conn = MockConn(MockCursor(rows=[]))
        mock_get_conn.return_value = conn

        task = _make_task(
            kind="script",
            attempts=3,        # already at max
            max_attempts=3,
            transient_error_classes=["ConnectionError"],
        )

        from task_worker import execute_task
        execute_task(task)

        sql_calls = conn._cursor._execute_calls
        dl_sqls = [c["sql"] for c in sql_calls if "dead_letter" in c["sql"]]
        self.assertTrue(len(dl_sqls) > 0, "Expected dead_letter even for transient when max_attempts hit")
        mock_cb_class.assert_called_once()


# ---------------------------------------------------------------------------
# Test: route_findings
# ---------------------------------------------------------------------------

class TestRouteFindings(TestCase):

    @patch("task_worker._resolve_payload")
    @patch("task_worker._get_conn")
    def test_creates_feedback_for_high_severity(
        self, mock_get_conn, mock_resolve_payload
    ):
        """route_findings creates a feedback row for severity='high'."""
        mock_resolve_payload.return_value = {
            "on_finding_route": {"high": "feedback", "default": "message"}
        }

        # First call: feedback INSERT RETURNING; second: surfaced_as UPDATE
        feedback_id = str(uuid.uuid4())
        conn1 = MockConn(MockCursor(rows=[(feedback_id,)]))
        conn2 = MockConn(MockCursor(rows=[]))
        call_count = [0]

        def conn_factory():
            idx = call_count[0]
            call_count[0] += 1
            return [conn1, conn2][min(idx, 1)]

        mock_get_conn.side_effect = conn_factory

        task = _make_task()
        result = {
            "findings": [
                {
                    "severity": "high",
                    "title": "Memory leak detected",
                    "body": "RSS growing unbounded",
                    "suggested_action": "Restart service",
                }
            ]
        }

        from task_worker import route_findings
        route_findings(task, result)

        # The first connection's cursor should have executed an INSERT into feedback
        feedback_sql = conn1._cursor._execute_calls[0]["sql"]
        self.assertIn("claude.feedback", feedback_sql)

    @patch("task_worker._resolve_payload")
    @patch("task_worker._get_conn")
    def test_creates_message_and_feedback_for_critical(
        self, mock_get_conn, mock_resolve_payload
    ):
        """route_findings creates both feedback AND message for severity='critical'."""
        mock_resolve_payload.return_value = {
            "on_finding_route": {"critical": "both", "default": "message"}
        }

        feedback_id = str(uuid.uuid4())
        connections = [
            MockConn(MockCursor(rows=[(feedback_id,)])),  # feedback INSERT
            MockConn(MockCursor(rows=[])),                  # message INSERT
            MockConn(MockCursor(rows=[])),                  # surfaced_as UPDATE
        ]
        call_count = [0]

        def conn_factory():
            idx = min(call_count[0], len(connections) - 1)
            call_count[0] += 1
            return connections[idx]

        mock_get_conn.side_effect = conn_factory

        task = _make_task()
        result = {
            "findings": [
                {
                    "severity": "critical",
                    "title": "Service down",
                    "body": "Process exited with OOM",
                    "suggested_action": "Investigate memory",
                }
            ]
        }

        from task_worker import route_findings
        route_findings(task, result)

        # Verify feedback INSERT
        feedback_sql = connections[0]._cursor._execute_calls[0]["sql"]
        self.assertIn("claude.feedback", feedback_sql)

        # Verify message INSERT
        message_sql = connections[1]._cursor._execute_calls[0]["sql"]
        self.assertIn("claude.messages", message_sql)

    @patch("task_worker._resolve_payload")
    @patch("task_worker._get_conn")
    def test_no_findings_is_noop(self, mock_get_conn, mock_resolve_payload):
        """route_findings does nothing when findings list is empty."""
        mock_resolve_payload.return_value = {}

        from task_worker import route_findings
        route_findings(_make_task(), {"findings": []})

        mock_get_conn.assert_not_called()


# ---------------------------------------------------------------------------
# Test: graceful_drain
# ---------------------------------------------------------------------------

class TestGracefulDrain(TestCase):

    def test_sets_shutting_down_flag(self):
        """graceful_drain sets _shutting_down within deadline."""
        import task_worker as tw

        # Reset state
        tw._shutting_down.clear()
        with tw._futures_lock:
            tw._active_futures.clear()

        # Run drain with no active futures (should return instantly)
        start = time.monotonic()
        tw.graceful_drain(deadline_secs=5)
        elapsed = time.monotonic() - start

        self.assertTrue(tw._shutting_down.is_set())
        self.assertLess(elapsed, 3.0, "graceful_drain should finish quickly with no futures")

        # Cleanup for other tests
        tw._shutting_down.clear()

    def test_waits_for_futures_within_deadline(self):
        """graceful_drain waits for an in-flight future to complete."""
        import task_worker as tw
        from concurrent.futures import Future

        tw._shutting_down.clear()

        done_event = threading.Event()
        f = Future()

        with tw._futures_lock:
            tw._active_futures.clear()
            tw._active_futures.append(f)

        # Complete the future in a background thread after 0.1s
        def _complete():
            time.sleep(0.1)
            f.set_result(None)
            done_event.set()

        t = threading.Thread(target=_complete, daemon=True)
        t.start()

        start = time.monotonic()
        tw.graceful_drain(deadline_secs=5)
        elapsed = time.monotonic() - start

        self.assertTrue(done_event.is_set(), "Future should have completed")
        self.assertLess(elapsed, 3.0, "Should not have waited full deadline")

        # Cleanup
        tw._shutting_down.clear()
        with tw._futures_lock:
            tw._active_futures.clear()

    def test_hard_exit_after_deadline_log(self):
        """graceful_drain logs a warning and returns when futures don't finish in time."""
        import task_worker as tw
        from concurrent.futures import Future

        tw._shutting_down.clear()

        # A future that will never complete
        f = Future()
        with tw._futures_lock:
            tw._active_futures.clear()
            tw._active_futures.append(f)

        start = time.monotonic()
        with self.assertLogs("task-worker", level="WARNING") as log_ctx:
            tw.graceful_drain(deadline_secs=1)  # very short deadline
        elapsed = time.monotonic() - start

        # Should have returned within ~2s of the deadline
        self.assertLess(elapsed, 4.0)
        # A warning should have been emitted
        warnings = [m for m in log_ctx.output if "hard exit" in m or "still running" in m]
        self.assertTrue(len(warnings) > 0, "Expected a hard-exit warning log")

        # Cleanup
        tw._shutting_down.clear()
        with tw._futures_lock:
            tw._active_futures.clear()
        # Resolve the stuck future so the test doesn't leak threads
        f.set_result(None)


# ---------------------------------------------------------------------------
# Test: error classification helper
# ---------------------------------------------------------------------------

class TestIsTransient(TestCase):

    def test_recognises_connection_error(self):
        from task_worker import _is_transient
        exc = ConnectionError("lost connection")
        self.assertTrue(_is_transient(exc, ["ConnectionError", "TimeoutError"]))

    def test_value_error_not_transient(self):
        from task_worker import _is_transient
        exc = ValueError("bad data")
        self.assertFalse(_is_transient(exc, ["ConnectionError", "TimeoutError"]))

    def test_not_implemented_error_not_transient(self):
        from task_worker import _is_transient
        exc = NotImplementedError("stub")
        self.assertFalse(_is_transient(exc, ["ConnectionError", "TimeoutError"]))

    def test_timeout_error_is_transient(self):
        from task_worker import _is_transient
        exc = TimeoutError("deadline exceeded")
        self.assertTrue(_is_transient(exc, ["TimeoutError"]))


# ---------------------------------------------------------------------------
# Test: set_template_paused
# ---------------------------------------------------------------------------

class TestSetTemplatePaused(TestCase):

    @patch("task_worker._get_conn")
    def test_issues_update(self, mock_get_conn):
        conn = MockConn(MockCursor(rows=[]))
        mock_get_conn.return_value = conn

        from task_worker import set_template_paused
        template_id = str(uuid.uuid4())
        set_template_paused(template_id, "breaker tripped")

        sql_calls = conn._cursor._execute_calls
        self.assertTrue(
            any("is_paused" in c["sql"] for c in sql_calls),
            "Expected an UPDATE setting is_paused",
        )
        self.assertTrue(conn.committed)


# ---------------------------------------------------------------------------
# Test: _resolve_payload
# ---------------------------------------------------------------------------

class TestResolvePayload(TestCase):

    @patch("task_worker._get_conn")
    def test_merges_override_on_top_of_base(self, mock_get_conn):
        base_payload = {"command": ["python", "foo.py"], "timeout": 120}
        override = {"timeout": 60}  # override wins

        conn = MockConn(MockCursor(rows=[{"payload": base_payload}]))
        mock_get_conn.return_value = conn

        task = _make_task()
        task["payload_override"] = override

        from task_worker import _resolve_payload
        result = _resolve_payload(task)

        self.assertEqual(result["timeout"], 60, "Override should win")
        self.assertEqual(result["command"], ["python", "foo.py"])

    @patch("task_worker._get_conn")
    def test_returns_override_only_when_no_template_version(self, mock_get_conn):
        conn = MockConn(MockCursor(rows=[]))  # no template version row found
        mock_get_conn.return_value = conn

        task = _make_task()
        task["payload_override"] = {"command": ["echo", "hi"]}
        task["template_version"] = None

        from task_worker import _resolve_payload
        result = _resolve_payload(task)

        # Base is empty (no version found), override is applied
        self.assertEqual(result.get("command"), ["echo", "hi"])


# ---------------------------------------------------------------------------
# Test: agent-kind stub raises NotImplementedError
# ---------------------------------------------------------------------------

class TestAgentKindStub(TestCase):

    def test_run_agent_raises_not_implemented(self):
        from task_worker import _run_agent
        task = _make_task(kind="agent")
        cancel_flag = threading.Event()
        with self.assertRaises(NotImplementedError):
            _run_agent(task, {}, cancel_flag)

    @patch("task_worker.CircuitBreaker")
    @patch("task_worker._is_lease_revoked", return_value=False)
    @patch("task_worker._resolve_payload", return_value={})
    @patch("task_worker._get_conn")
    def test_agent_task_lands_in_dead_letter(
        self, mock_get_conn, mock_resolve_payload, mock_lease_revoked, mock_cb_class
    ):
        """agent-kind tasks go to dead_letter immediately (NotImplementedError is permanent)."""
        conn = MockConn(MockCursor(rows=[]))
        mock_get_conn.return_value = conn

        task = _make_task(kind="agent", attempts=1, max_attempts=3)

        from task_worker import execute_task
        execute_task(task)

        sql_calls = conn._cursor._execute_calls
        dl_sqls = [c["sql"] for c in sql_calls if "dead_letter" in c["sql"]]
        self.assertTrue(len(dl_sqls) > 0, "Agent stub should produce dead_letter")


if __name__ == "__main__":
    import unittest
    unittest.main()
