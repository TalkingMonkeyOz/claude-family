"""
test_job_enqueue.py — Test suite for job_enqueue handler (BT702).

Tests cover:
- Enqueue with template_id + payload produces INSERT
- Enqueue with template_name resolves to correct template_id
- Duplicate idempotency_key (active task exists) returns existing task_id
- Duplicate idempotency_key (only completed task exists) creates new row
- Explicit idempotency_key wins over auto-derived
- Paused template rejected with clear error
- Payload_override merges with template payload (deep merge test)
- Priority defaults to 3, validates 1-5 range

Uses unittest.mock to mock DB operations (no live DB required).
"""

import unittest
from unittest.mock import Mock, MagicMock, patch, call
import json
import psycopg
import sys
from pathlib import Path

# Add handlers to path for import
handlers_dir = Path(__file__).parent.parent / "handlers"
sys.path.insert(0, str(handlers_dir))

from job_enqueue import handle_job_enqueue, _deep_merge


class TestJobEnqueue(unittest.TestCase):
    """Test suite for atomic job_enqueue handler."""

    def setUp(self):
        """Set up mocks for each test."""
        self.mock_conn = MagicMock()
        self.mock_cur = MagicMock()
        self.mock_conn.cursor.return_value = self.mock_cur
        self.mock_conn.__enter__ = Mock(return_value=self.mock_conn)
        self.mock_conn.__exit__ = Mock(return_value=None)

    def test_enqueue_with_template_id_inserts_task(self):
        """Enqueue with template_id + payload produces INSERT."""
        template_id = "123e4567-e89b-12d3-a456-426614174000"
        template_payload = {"command": "echo hello"}
        override_payload = {"extra": "data"}

        # Mock template lookup
        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'echo-template',
                'current_version': 2,
                'is_paused': False,
                'paused_reason': None,
                'payload': template_payload
            },
            {'task_id': '456f5678-f89b-12d3-a456-426614174111'}  # INSERT response
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(
                template_id=template_id,
                payload_override=override_payload,
                priority=2
            )

        assert result['success'] is True
        assert result['action'] == 'enqueued'
        assert result['task_id'] == '456f5678-f89b-12d3-a456-426614174111'
        assert 'idempotency_key' in result
        self.mock_conn.commit.assert_called_once()

    def test_enqueue_with_template_name_resolves(self):
        """Enqueue with template_name resolves to correct template_id."""
        template_id = "223e4567-e89b-12d3-a456-426614174001"

        # Mock template lookup by name
        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'my-template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {"key": "value"}
            },
            {'task_id': '556f5678-f89b-12d3-a456-426614174222'}
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(template_name='my-template')

        assert result['success'] is True
        # Verify second execute call used name lookup
        calls = self.mock_cur.execute.call_args_list
        assert 'WHERE t.name = %s' in calls[0][0][0]

    def test_duplicate_idempotency_key_active_task(self):
        """Duplicate idempotency_key (active task exists) returns existing task_id."""
        template_id = "323e4567-e89b-12d3-a456-426614174002"
        idem_key = "abc123def456"
        existing_task_id = "666f5678-f89b-12d3-a456-426614174333"

        # Mock template lookup
        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            }
        ]

        # Mock IntegrityError on INSERT, then SELECT existing task
        self.mock_cur.execute.side_effect = [
            None,  # template lookup
            psycopg.IntegrityError("duplicate key value violates unique constraint \"idx_task_queue_idem_active\""),
            None,  # existing task SELECT
        ]
        self.mock_cur.fetchone.side_effect = [
            {  # template
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            },
            {'task_id': existing_task_id}  # existing active task
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(
                template_id=template_id,
                idempotency_key=idem_key
            )

        assert result['success'] is True
        assert result['action'] == 'already_active'
        assert result['task_id'] == existing_task_id
        self.mock_conn.rollback.assert_called_once()

    def test_duplicate_idempotency_key_completed_task_creates_new(self):
        """Duplicate idempotency_key (only completed task exists) creates new row."""
        # Note: This test verifies that if a completed task has the same key,
        # the uniqueness constraint on idx_task_queue_idem_active allows a new INSERT
        # because completed is not in ('pending', 'in_progress').

        template_id = "423e4567-e89b-12d3-a456-426614174003"

        # Mock template lookup
        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            },
            {'task_id': '777f5678-f89b-12d3-a456-426614174444'}  # new INSERT
        ]

        # INSERT succeeds (completed task doesn't block new enqueue)
        self.mock_cur.execute.side_effect = None

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(template_id=template_id)

        assert result['success'] is True
        assert result['action'] == 'enqueued'

    def test_explicit_idempotency_key_wins(self):
        """Explicit idempotency_key wins over auto-derived."""
        template_id = "523e4567-e89b-12d3-a456-426614174004"
        explicit_key = "explicit-idem-key-12345"

        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            },
            {'task_id': '888f5678-f89b-12d3-a456-426614174555'}
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(
                template_id=template_id,
                idempotency_key=explicit_key
            )

        assert result['idempotency_key'] == explicit_key

    def test_paused_template_rejected(self):
        """Paused template rejected with clear error."""
        template_id = "623e4567-e89b-12d3-a456-426614174005"

        self.mock_cur.fetchone.return_value = {
            'template_id': template_id,
            'name': 'paused-template',
            'current_version': 1,
            'is_paused': True,
            'paused_reason': 'Too many failures',
            'payload': {}
        }

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            with self.assertRaises(ValueError) as ctx:
                handle_job_enqueue(template_id=template_id)

            assert 'paused' in str(ctx.exception).lower()
            assert 'Too many failures' in str(ctx.exception)

    def test_payload_override_deep_merge(self):
        """Payload_override merges with template payload (deep merge test)."""
        template_id = "723e4567-e89b-12d3-a456-426614174006"
        template_payload = {
            "command": "python",
            "args": ["script.py"],
            "config": {"timeout": 300, "retries": 3}
        }
        override_payload = {
            "args": ["other.py"],
            "config": {"timeout": 600}
        }

        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': template_payload
            },
            {'task_id': '999f5678-f89b-12d3-a456-426614174666'}
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(
                template_id=template_id,
                payload_override=override_payload
            )

        # Check the INSERT call for merged payload
        # The second execute call is the INSERT (first is template lookup)
        execute_calls = [c for c in self.mock_cur.execute.call_args_list if 'INSERT' in str(c)]
        assert len(execute_calls) > 0
        insert_call = execute_calls[0]
        # Arguments are in args[0][1] (the tuple of positional params)
        inserted_payload_json = insert_call[0][1][2]  # payload_override is 3rd param
        inserted_payload = json.loads(inserted_payload_json)

        # Expected: args overridden, config.timeout overridden, config.retries preserved
        assert inserted_payload['command'] == 'python'
        assert inserted_payload['args'] == ['other.py']
        assert inserted_payload['config']['timeout'] == 600
        assert inserted_payload['config']['retries'] == 3

    def test_priority_defaults_to_3(self):
        """Priority defaults to 3 when not provided."""
        template_id = "823e4567-e89b-12d3-a456-426614174007"

        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            },
            {'task_id': 'aaaf5678-f89b-12d3-a456-426614174777'}
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(template_id=template_id)

        # Check INSERT call for default priority
        # The INSERT call contains the priority in its params
        execute_calls = [c for c in self.mock_cur.execute.call_args_list if 'INSERT' in str(c)]
        insert_call = execute_calls[0]
        priority_arg = insert_call[0][1][3]  # priority is 4th positional arg
        assert priority_arg == 3

    def test_priority_validates_range(self):
        """Priority validates 1-5 range."""
        template_id = "923e4567-e89b-12d3-a456-426614174008"

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            # Below range
            with self.assertRaises(ValueError) as ctx:
                handle_job_enqueue(template_id=template_id, priority=0)
            assert 'priority' in str(ctx.exception).lower()

            # Above range
            with self.assertRaises(ValueError) as ctx:
                handle_job_enqueue(template_id=template_id, priority=6)
            assert 'priority' in str(ctx.exception).lower()

    def test_template_not_found_error(self):
        """Missing template raises RuntimeError."""
        template_id = "a23e4567-e89b-12d3-a456-426614174009"

        self.mock_cur.fetchone.return_value = None

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            with self.assertRaises(RuntimeError) as ctx:
                handle_job_enqueue(template_id=template_id)

            assert 'not found' in str(ctx.exception).lower()

    def test_missing_both_template_id_and_name_error(self):
        """Missing both template_id and template_name raises ValueError."""
        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            with self.assertRaises(ValueError) as ctx:
                handle_job_enqueue()

            assert 'required' in str(ctx.exception).lower()

    def test_audit_log_recorded(self):
        """Successful enqueue logs to audit_log."""
        template_id = "b23e4567-e89b-12d3-a456-426614174010"

        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 1,
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            },
            {'task_id': 'bbbf5678-f89b-12d3-a456-426614174888'}
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(template_id=template_id)

        # Verify audit_log INSERT was called
        audit_calls = [c for c in self.mock_cur.execute.call_args_list if 'audit_log' in str(c)]
        assert len(audit_calls) > 0

    def test_explicit_version_lookup(self):
        """Explicit template_version different from current_version triggers version lookup."""
        template_id = "c23e4567-e89b-12d3-a456-426614174011"
        explicit_version = 3

        # Mock template lookup
        self.mock_cur.fetchone.side_effect = [
            {
                'template_id': template_id,
                'name': 'template',
                'current_version': 5,  # current is 5
                'is_paused': False,
                'paused_reason': None,
                'payload': {}
            },
            {'payload': {'versioned': 'payload'}},  # version 3 payload
            {'task_id': 'cccf5678-f89b-12d3-a456-426614174999'}
        ]

        with patch('job_enqueue.get_db_connection', return_value=self.mock_conn):
            result = handle_job_enqueue(
                template_id=template_id,
                template_version=explicit_version
            )

        # Verify version lookup was executed
        version_lookup_calls = [c for c in self.mock_cur.execute.call_args_list if 'job_template_versions' in str(c)]
        assert len(version_lookup_calls) > 0


class TestDeepMerge(unittest.TestCase):
    """Test suite for _deep_merge utility."""

    def test_simple_override(self):
        """Override top-level key."""
        base = {'a': 1, 'b': 2}
        override = {'b': 20}
        result = _deep_merge(base, override)
        assert result == {'a': 1, 'b': 20}

    def test_nested_merge(self):
        """Merge nested dicts."""
        base = {'config': {'timeout': 300, 'retries': 3}}
        override = {'config': {'timeout': 600}}
        result = _deep_merge(base, override)
        assert result['config']['timeout'] == 600
        assert result['config']['retries'] == 3

    def test_deep_nested_merge(self):
        """Merge deeply nested dicts."""
        base = {'a': {'b': {'c': 1}}}
        override = {'a': {'b': {'c': 2}}}
        result = _deep_merge(base, override)
        assert result == {'a': {'b': {'c': 2}}}

    def test_new_keys_added(self):
        """New keys in override are added."""
        base = {'a': 1}
        override = {'b': 2}
        result = _deep_merge(base, override)
        assert result == {'a': 1, 'b': 2}

    def test_override_none(self):
        """None override returns base."""
        base = {'a': 1}
        result = _deep_merge(base, None)
        assert result == base

    def test_override_list(self):
        """List values are overridden, not merged."""
        base = {'items': [1, 2, 3]}
        override = {'items': [4, 5]}
        result = _deep_merge(base, override)
        assert result == {'items': [4, 5]}


if __name__ == '__main__':
    unittest.main()
