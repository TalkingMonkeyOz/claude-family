#!/usr/bin/env python3
"""
Tests for queue_health_check.py (L2 monitoring script).

Test patterns:
  1. All metrics under threshold → exit 0, no findings
  2. Backlog overflow → high severity finding
  3. Drain stalled (no completion + backlog) → critical severity finding
  4. Leaked leases → high severity finding
  5. Dead-letter spike → high/critical severity finding
  6. Multiple breaches → multiple findings
  7. DB unavailable → critical finding

Uses mocked DB connection and psycopg detection.
"""

import json
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Mock psycopg before any imports
sys.modules['psycopg'] = MagicMock()
sys.modules['psycopg.OperationalError'] = Exception

# Add scripts to path for imports
test_dir = Path(__file__).parent
scripts_dir = test_dir.parent / "scripts"
jobs_dir = scripts_dir / "jobs"
sys.path.insert(0, str(scripts_dir))
sys.path.insert(0, str(jobs_dir))


def create_mock_conn_for_metrics(backlog=50, leaked_leases=0,
                                 dead_letter_1h=2, drain_stall_secs=300):
    """Create a mock connection that returns specific metric values."""
    mock_conn = Mock()
    mock_cur = Mock()

    # Configure fetchone to return metrics in sequence
    mock_cur.fetchone.side_effect = [
        {'cnt': backlog},                    # Backlog query
        {'cnt': leaked_leases},              # Leaked leases query
        {'cnt': dead_letter_1h},             # Dead-letter rate query
        {'stall_secs': drain_stall_secs},   # Drain stall query
    ]

    mock_conn.cursor.return_value = mock_cur
    return mock_conn


@pytest.fixture
def test_module():
    """Import and yield the queue_health_check module."""
    # Patch before import
    with patch('queue_health_check.DB_AVAILABLE', True):
        with patch('queue_health_check.detect_psycopg') as mock_detect:
            mock_detect.return_value = (MagicMock(), '3.0', None, None)
            # Import the module
            import sys as sys2
            if 'queue_health_check' in sys2.modules:
                del sys2.modules['queue_health_check']
            import queue_health_check as qhc
            yield qhc


def test_all_metrics_healthy(test_module):
    """All metrics under threshold → exit 0, no findings."""
    mock_conn = create_mock_conn_for_metrics(backlog=50, leaked_leases=0,
                                              dead_letter_1h=2, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 0
    assert len(result['findings']) == 0
    assert result['summary'] == "All metrics healthy"
    assert result['metrics']['backlog'] == 50


def test_backlog_overflow_high(test_module):
    """Backlog > threshold → high severity finding."""
    mock_conn = create_mock_conn_for_metrics(backlog=150, leaked_leases=0,
                                              dead_letter_1h=2, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 1
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'high'
    assert 'Backlog' in result['findings'][0]['title']


def test_backlog_overflow_critical(test_module):
    """Backlog > threshold * 2 → critical severity finding."""
    mock_conn = create_mock_conn_for_metrics(backlog=250, leaked_leases=0,
                                              dead_letter_1h=2, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 2
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'critical'


def test_leaked_leases_high(test_module):
    """Leaked leases > 0 but <= 5 → high severity."""
    mock_conn = create_mock_conn_for_metrics(backlog=50, leaked_leases=3,
                                              dead_letter_1h=2, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 1
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'high'
    assert 'Leaked' in result['findings'][0]['title']


def test_leaked_leases_critical(test_module):
    """Leaked leases > 5 → critical severity."""
    mock_conn = create_mock_conn_for_metrics(backlog=50, leaked_leases=10,
                                              dead_letter_1h=2, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 2
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'critical'


def test_dead_letter_rate_high(test_module):
    """Dead-letter > threshold but <= 2x → high severity."""
    mock_conn = create_mock_conn_for_metrics(backlog=50, leaked_leases=0,
                                              dead_letter_1h=7, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 1
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'high'
    assert 'Dead-Letter' in result['findings'][0]['title']


def test_dead_letter_rate_critical(test_module):
    """Dead-letter > threshold * 2 → critical severity."""
    mock_conn = create_mock_conn_for_metrics(backlog=50, leaked_leases=0,
                                              dead_letter_1h=15, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 2
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'critical'


def test_drain_stall_critical(test_module):
    """Drain stalled (last_completion > threshold + backlog > 0) → critical."""
    # Drain stall > 1800s (CF_DRAIN_STALL_SECS default) with pending backlog
    mock_conn = create_mock_conn_for_metrics(backlog=50, leaked_leases=0,
                                              dead_letter_1h=2, drain_stall_secs=3600)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 2
    assert len(result['findings']) == 1
    assert result['findings'][0]['severity'] == 'critical'
    assert 'Drain Stalled' in result['findings'][0]['title']


def test_drain_stall_healthy_no_backlog(test_module):
    """Drain stalled but no backlog → healthy (no alert needed)."""
    mock_conn = create_mock_conn_for_metrics(backlog=0, leaked_leases=0,
                                              dead_letter_1h=2, drain_stall_secs=3600)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    # No finding because backlog is 0
    assert result['exit_code'] == 0
    assert len(result['findings']) == 0


def test_multiple_breaches(test_module):
    """Multiple metric breaches → multiple findings, max severity wins."""
    # High backlog + leaked leases + dead-letter spike
    mock_conn = create_mock_conn_for_metrics(backlog=150, leaked_leases=3,
                                              dead_letter_1h=8, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 1  # All are 'high', not critical
    assert len(result['findings']) == 3
    assert all(f['severity'] == 'high' for f in result['findings'])


def test_multiple_breaches_with_critical(test_module):
    """Multiple breaches with at least one critical → exit 2."""
    # Critical backlog + high dead-letter
    mock_conn = create_mock_conn_for_metrics(backlog=250, leaked_leases=0,
                                              dead_letter_1h=7, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['exit_code'] == 2  # Max severity is critical
    assert len(result['findings']) == 2
    severities = [f['severity'] for f in result['findings']]
    assert 'critical' in severities


def test_db_unavailable(test_module):
    """DB connection fails → critical finding."""
    with patch.object(test_module, 'get_db_connection_safe', return_value=None):
        result = test_module.check_queue_health()

        assert result['exit_code'] == 2
        assert len(result['findings']) == 1
        assert result['findings'][0]['severity'] == 'critical'
        assert 'DB Unavailable' in result['findings'][0]['title']
        assert result['metrics'] is None


def test_metrics_dict_present_in_output(test_module):
    """Verify metrics dict is populated in output."""
    mock_conn = create_mock_conn_for_metrics(backlog=75, leaked_leases=1,
                                              dead_letter_1h=3, drain_stall_secs=900)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert result['metrics'] is not None
    assert result['metrics']['backlog'] == 75
    assert result['metrics']['leaked_leases'] == 1
    assert result['metrics']['dead_letter_rate_1h'] == 3
    assert result['metrics']['drain_stall_secs'] == 900


def test_finding_structure(test_module):
    """Verify finding structure has all required fields."""
    mock_conn = create_mock_conn_for_metrics(backlog=150, leaked_leases=0,
                                              dead_letter_1h=2, drain_stall_secs=300)

    with patch.object(test_module, 'get_db_connection_safe', return_value=mock_conn):
        result = test_module.check_queue_health()

    assert len(result['findings']) == 1
    finding = result['findings'][0]
    assert 'severity' in finding
    assert 'title' in finding
    assert 'body' in finding
    assert 'suggested_action' in finding


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
