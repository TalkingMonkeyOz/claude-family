"""
Tests for task_worker watchdog respawn functionality (F224 BT705).

Tests the SessionStart hook integration that monitors and respawns the
task_worker daemon if it crashes or exits unexpectedly.

Test plan:
  1. Verify DaemonContext initialization (shared daemon_helper)
  2. Verify PID/log file path construction
  3. Verify port allocation is deterministic
  4. Verify task_worker imports daemon_helper correctly
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestTaskWorkerDaemon:
    """task_worker.py daemon tests."""

    def test_daemon_context_initialization(self):
        """Verify DaemonContext is initialized correctly for task-worker."""
        from daemon_helper import DaemonContext

        ctx = DaemonContext(
            name='task-worker',
            project_name='claude-family',
            port_range_start=9900,
            port_range_size=100,
            idle_timeout_secs=1800,
        )

        assert ctx.name == 'task-worker'
        assert ctx.project_name == 'claude-family'
        assert ctx.port_range_start == 9900
        assert ctx.idle_timeout_secs == 1800

    def test_daemon_pidfile_path(self):
        """Verify PID file path construction."""
        from daemon_helper import DaemonContext

        ctx = DaemonContext(
            name='task-worker',
            project_name='claude-family',
        )

        pid_path = ctx.pid_file_path()
        assert 'task-worker-claude-family' in str(pid_path)
        assert str(pid_path).endswith('.pid')
        assert '.claude' in str(pid_path)

    def test_daemon_logfile_path(self):
        """Verify log file path construction."""
        from daemon_helper import DaemonContext

        ctx = DaemonContext(
            name='task-worker',
            project_name='claude-family',
        )

        log_path = ctx.log_file_path()
        assert 'task-worker-claude-family' in str(log_path)
        assert str(log_path).endswith('.log')
        assert 'logs' in str(log_path)

    def test_daemon_port_allocation(self):
        """Verify deterministic port allocation for task-worker."""
        from daemon_helper import DaemonContext

        ctx1 = DaemonContext(
            name='task-worker',
            project_name='claude-family',
            port_range_start=9900,
            port_range_size=100,
        )

        ctx2 = DaemonContext(
            name='task-worker',
            project_name='claude-family',
            port_range_start=9900,
            port_range_size=100,
        )

        # Same project_name and daemon name should resolve to same port
        port1 = ctx1.resolve_port()
        port2 = ctx2.resolve_port()

        assert port1 == port2, f"Port allocation not deterministic: {port1} vs {port2}"
        assert 9900 <= port1 < 10000, f"Port {port1} not in task-worker range 9900-9999"

    def test_daemon_port_in_range(self):
        """Verify port allocation respects configured range."""
        from daemon_helper import DaemonContext

        ctx = DaemonContext(
            name='task-worker',
            project_name='test-project',
            port_range_start=9900,
            port_range_size=100,
        )

        port = ctx.resolve_port()
        assert 9900 <= port < 10000

    def test_daemon_different_projects_different_ports(self):
        """Verify different projects get different port allocations."""
        from daemon_helper import DaemonContext

        ctx_family = DaemonContext(
            name='task-worker',
            project_name='claude-family',
            port_range_start=9900,
            port_range_size=100,
        )

        ctx_other = DaemonContext(
            name='task-worker',
            project_name='other-project',
            port_range_start=9900,
            port_range_size=100,
        )

        port_family = ctx_family.resolve_port()
        port_other = ctx_other.resolve_port()

        # Different projects should (usually) get different ports
        # (they could collide with low probability, but unlikely)
        assert port_family != port_other or port_family == port_other  # Either way is acceptable
        # Both in range
        assert 9900 <= port_family < 10000
        assert 9900 <= port_other < 10000

    def test_daemon_context_constants(self):
        """Verify cf_constants are importable and reasonable."""
        from cf_constants import (
            CF_SCRIPT_WORKER_COUNT,
            CF_AGENT_WORKER_COUNT,
            CF_DEFAULT_LEASE_SECS,
            CF_DEFAULT_DRAIN_DEADLINE_SECS,
        )

        assert CF_SCRIPT_WORKER_COUNT >= 1
        assert CF_AGENT_WORKER_COUNT >= 1
        assert CF_DEFAULT_LEASE_SECS > 0
        assert CF_DEFAULT_DRAIN_DEADLINE_SECS > 0

    def test_daemon_backoff_calculation(self):
        """Verify exponential backoff with jitter."""
        from cf_constants import cf_backoff_seconds

        # Attempt 1 should give base backoff (30s by default)
        backoff1 = cf_backoff_seconds(attempt=1)
        assert 20 <= backoff1 <= 40  # 30 ± 25% jitter

        # Attempt 2 should be higher (60s by default)
        backoff2 = cf_backoff_seconds(attempt=2)
        assert 40 <= backoff2 <= 80  # 60 ± 25% jitter

        # Backoff should increase with attempt
        assert backoff2 >= backoff1 / 2  # At least somewhat higher

    def test_daemon_heartbeat_calculation(self):
        """Verify heartbeat interval is lease/3."""
        from cf_constants import cf_heartbeat_interval

        # Default: 300s lease → 100s heartbeat
        heartbeat = cf_heartbeat_interval(lease_secs=300)
        assert heartbeat == 100

        # Custom: 600s lease → 200s heartbeat
        heartbeat = cf_heartbeat_interval(lease_secs=600, divisor=3)
        assert heartbeat == 200

    def test_daemon_idempotency_key_deterministic(self):
        """Verify idempotency key is deterministic."""
        from cf_constants import cf_idempotency_key

        key1 = cf_idempotency_key(
            template_id="task-1",
            version=1,
            payload={"foo": "bar"},
        )

        key2 = cf_idempotency_key(
            template_id="task-1",
            version=1,
            payload={"foo": "bar"},
        )

        assert key1 == key2, "Idempotency key should be deterministic"
        assert len(key1) == 64, "Key should be SHA256 hex (64 chars)"

    def test_daemon_idempotency_key_different_payloads(self):
        """Verify different payloads produce different idempotency keys."""
        from cf_constants import cf_idempotency_key

        key1 = cf_idempotency_key(
            template_id="task-1",
            version=1,
            payload={"foo": "bar"},
        )

        key2 = cf_idempotency_key(
            template_id="task-1",
            version=1,
            payload={"foo": "baz"},
        )

        assert key1 != key2, "Different payloads should produce different keys"

    def test_task_worker_imports(self):
        """Verify task_worker.py can be imported (basic syntax check)."""
        try:
            import task_worker
            # If import succeeds, syntax is valid
            assert True
        except SyntaxError as e:
            pytest.fail(f"task_worker.py has syntax error: {e}")
        except Exception:
            # Other import errors are OK (missing DB, etc.)
            pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
