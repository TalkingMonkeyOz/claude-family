"""
test_job_cancel.py — Tests for BT703 job_cancel MCP handler.

Covers:
- pending → cancelled
- in_progress + soft → cancel_requested set
- in_progress + force → cancelled + lease revoked
- terminal status → error returned
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime
import psycopg

# Import the handler
import sys
from pathlib import Path
handlers_dir = Path(__file__).parent.parent / 'handlers'
sys.path.insert(0, str(handlers_dir))
from job_cancel import handle_job_cancel, get_db_connection


class TestJobCancel:
    """Test suite for job_cancel handler."""

    @patch('job_cancel.get_db_connection')
    def test_cancel_pending_task(self, mock_get_db):
        """Test cancelling a pending task — immediate status change."""
        # Setup mock connection and cursor
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        # Mock: fetch task status as pending
        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-123', 'status': 'pending', 'claimed_until': None, 'started_at': None},
            None,  # No second fetch (audit log doesn't return rows)
        ]

        # Call handler
        result = handle_job_cancel(
            task_id='task-123',
            force=False,
            reason='Test cancel'
        )

        # Verify result
        assert result['success'] is True
        assert result['task_id'] == 'task-123'
        assert result['previous_status'] == 'pending'
        assert result['action'] == 'cancelled'
        assert 'Task task-123 cancelled' in result['message']

        # Verify UPDATE was called for pending → cancelled
        update_calls = [call for call in mock_cur.execute.call_args_list
                       if 'UPDATE claude.task_queue' in str(call) and "status = 'cancelled'" in str(call)]
        assert len(update_calls) > 0

        # Verify commit was called
        mock_conn.commit.assert_called_once()

    @patch('job_cancel.get_db_connection')
    def test_cancel_in_progress_soft(self, mock_get_db):
        """Test soft cancel of in_progress task — sets cancel_requested."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        # Mock: fetch task status as in_progress
        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-456', 'status': 'in_progress', 'claimed_until': '2026-05-02T10:00:00Z', 'started_at': '2026-05-02T09:00:00Z'},
            None,
        ]

        # Call handler with soft cancel (default)
        result = handle_job_cancel(
            task_id='task-456',
            force=False,
            reason='User requested cancellation'
        )

        # Verify result
        assert result['success'] is True
        assert result['task_id'] == 'task-456'
        assert result['previous_status'] == 'in_progress'
        assert result['action'] == 'cancel_requested'
        assert result['force_applied'] is False
        assert 'cancel requested' in result['message'].lower()

        # Verify UPDATE was called for cancel_requested
        update_calls = [call for call in mock_cur.execute.call_args_list
                       if 'UPDATE claude.task_queue' in str(call) and 'cancel_requested' in str(call)]
        assert len(update_calls) > 0

        mock_conn.commit.assert_called_once()

    @patch('job_cancel.get_db_connection')
    def test_cancel_in_progress_force(self, mock_get_db):
        """Test hard (force) cancel of in_progress task — revokes lease + cancels."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        # Mock: fetch task status as in_progress
        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-789', 'status': 'in_progress', 'claimed_until': '2026-05-02T10:00:00Z', 'started_at': '2026-05-02T09:00:00Z'},
            None,
        ]

        # Call handler with force cancel
        result = handle_job_cancel(
            task_id='task-789',
            force=True,
            reason='Force cancel due to timeout'
        )

        # Verify result
        assert result['success'] is True
        assert result['task_id'] == 'task-789'
        assert result['previous_status'] == 'in_progress'
        assert result['action'] == 'cancelled'
        assert result['force_applied'] is True
        assert 'lease revoked' in result['message'].lower()

        # Verify UPDATE was called for status + claimed_until
        update_calls = [call for call in mock_cur.execute.call_args_list
                       if 'UPDATE claude.task_queue' in str(call) and "status = 'cancelled'" in str(call)]
        assert len(update_calls) > 0

        # Check that claimed_until was updated
        update_query = update_calls[0][0][0]
        assert 'claimed_until' in update_query

        mock_conn.commit.assert_called_once()

    @patch('job_cancel.get_db_connection')
    def test_cancel_terminal_task_error(self, mock_get_db):
        """Test cancelling a terminal task — returns error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        # Mock: fetch task with terminal status (completed)
        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-completed', 'status': 'completed', 'claimed_until': None, 'started_at': '2026-05-02T09:00:00Z'},
        ]

        # Call handler
        result = handle_job_cancel(task_id='task-completed', force=False)

        # Verify result shows error
        assert result['success'] is False
        assert result['task_id'] == 'task-completed'
        assert result['previous_status'] == 'completed'
        assert result['action'] == 'already_terminal'
        assert 'already_terminal' in str(result).lower() or 'cannot cancel' in result['message'].lower()

        # Verify NO UPDATE was called (no cancellation)
        update_calls = [call for call in mock_cur.execute.call_args_list
                       if 'UPDATE claude.task_queue' in str(call)]
        assert len(update_calls) == 0

        # Verify NO commit (rolled back)
        mock_conn.commit.assert_not_called()

    @patch('job_cancel.get_db_connection')
    def test_cancel_task_not_found(self, mock_get_db):
        """Test cancelling a non-existent task — raises RuntimeError."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        # Mock: task not found
        mock_cur.fetchone.return_value = None

        # Call handler and expect error
        with pytest.raises(RuntimeError, match="Task not found"):
            handle_job_cancel(task_id='non-existent-task-id')

    @patch('job_cancel.get_db_connection')
    def test_cancel_missing_task_id_error(self, mock_get_db):
        """Test cancelling with missing task_id — raises ValueError."""
        with pytest.raises(ValueError, match="task_id is required"):
            handle_job_cancel(task_id='')

    @patch('job_cancel.get_db_connection')
    def test_cancel_audit_logged(self, mock_get_db):
        """Test that cancellation is audited to audit_log."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-audit', 'status': 'pending', 'claimed_until': None, 'started_at': None},
            None,
        ]

        result = handle_job_cancel(
            task_id='task-audit',
            reason='Audit test',
            cancelling_session_id='session-xyz'
        )

        assert result['success'] is True

        # Verify audit_log INSERT was called
        audit_calls = [call for call in mock_cur.execute.call_args_list
                      if 'INSERT INTO claude.audit_log' in str(call)]
        assert len(audit_calls) > 0

        # Verify audit includes reason and session_id
        audit_call_args = audit_calls[0][0]
        audit_query = audit_call_args[0]
        assert 'session_id' in audit_query
        assert 'session-xyz' in str(audit_call_args)

    @patch('job_cancel.get_db_connection')
    def test_cancel_cancelled_task_already_cancelled(self, mock_get_db):
        """Test cancelling a task that's already cancelled — terminal status error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-already-cancelled', 'status': 'cancelled', 'claimed_until': None, 'started_at': None},
        ]

        result = handle_job_cancel(task_id='task-already-cancelled', force=False)

        assert result['success'] is False
        assert result['action'] == 'already_terminal'
        assert 'Cannot cancel' in result['message']

    @patch('job_cancel.get_db_connection')
    def test_cancel_failed_task_already_failed(self, mock_get_db):
        """Test cancelling a task that already failed — terminal status error."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-failed', 'status': 'failed', 'claimed_until': None, 'started_at': None},
        ]

        result = handle_job_cancel(task_id='task-failed', force=False)

        assert result['success'] is False
        assert result['action'] == 'already_terminal'

    @patch('job_cancel.get_db_connection')
    def test_cancel_with_reason(self, mock_get_db):
        """Test cancellation with custom reason — audited correctly."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        mock_cur.fetchone.side_effect = [
            {'task_id': 'task-reason', 'status': 'pending', 'claimed_until': None, 'started_at': None},
            None,
        ]

        result = handle_job_cancel(
            task_id='task-reason',
            reason='User cancelled due to timeout'
        )

        assert result['success'] is True

        # Verify reason is included in audit log call
        audit_calls = [call for call in mock_cur.execute.call_args_list
                      if 'INSERT INTO claude.audit_log' in str(call)]
        assert len(audit_calls) > 0
        audit_args = audit_calls[0][0]
        assert 'User cancelled due to timeout' in str(audit_args)

    @patch('job_cancel.get_db_connection')
    def test_db_connection_error(self, mock_get_db):
        """Test handling of database connection error."""
        mock_get_db.side_effect = RuntimeError("DATABASE_URI not set")

        with pytest.raises(RuntimeError, match="DATABASE_URI"):
            handle_job_cancel(task_id='task-123')

    @patch('job_cancel.get_db_connection')
    def test_cancel_requested_column_missing_error(self, mock_get_db):
        """Test handling of missing cancel_requested column (schema migration BT694 not applied)."""
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_get_db.return_value = mock_conn

        # Task is in_progress, soft cancel requested
        mock_cur.fetchone.return_value = {
            'task_id': 'task-soft-cancel',
            'status': 'in_progress',
            'claimed_until': '2026-05-02T10:00:00Z',
            'started_at': '2026-05-02T09:00:00Z'
        }

        # But the UPDATE fails because cancel_requested column doesn't exist
        mock_cur.execute.side_effect = [
            None,  # SELECT succeeds
            psycopg.ProgrammingError("column \"cancel_requested\" of relation \"task_queue\" does not exist"),
        ]

        with pytest.raises(RuntimeError, match="Schema migration BT694"):
            handle_job_cancel(task_id='task-soft-cancel', force=False)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
