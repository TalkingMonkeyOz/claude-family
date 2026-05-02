#!/usr/bin/env python3
"""
Test suite for daemon_helper.py

Covers:
- DaemonContext construction with custom port range
- PID file write + read round-trip
- is_daemon_alive for current process and invalid PIDs
- resolve_port determinism
- find_available_port returns a port in range
- log_file_path uses correct convention
- watchdog_respawn behavior (no PID file = respawn needed)
"""

import os
import sys
import tempfile
import threading
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path for imports
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from daemon_helper import (
    DaemonContext,
    is_process_running,
    _parse_pid_file,
    watchdog_respawn,
)


class TestPIDFileParsing:
    """Test _parse_pid_file with both legacy and new formats."""

    def test_parse_legacy_format(self):
        """Legacy format: just a bare PID."""
        result = _parse_pid_file("12345")
        assert result == {"pid": 12345}

    def test_parse_new_format(self):
        """New format: key=value pairs."""
        text = "pid=12345\nport=9883\n"
        result = _parse_pid_file(text)
        assert result == {"pid": 12345, "port": 9883}

    def test_parse_empty(self):
        """Empty or whitespace-only text."""
        assert _parse_pid_file("") == {}
        assert _parse_pid_file("   ") == {}
        assert _parse_pid_file(None) == {}

    def test_parse_invalid_pid(self):
        """Invalid PID value."""
        result = _parse_pid_file("not-a-number")
        assert result == {}

    def test_parse_mixed_format(self):
        """Format with extra keys."""
        text = "pid=12345\nport=9883\nother=value\n"
        result = _parse_pid_file(text)
        assert result["pid"] == 12345
        assert result["port"] == 9883
        assert result["other"] == "value"


class TestDaemonContextConstruction:
    """Test DaemonContext initialization and basic properties."""

    def test_construction_defaults(self):
        """Construct with defaults."""
        ctx = DaemonContext("test-daemon", "test-project")
        assert ctx.name == "test-daemon"
        assert ctx.project_name == "test-project"
        assert ctx.port_range_start == 9800
        assert ctx.port_range_size == 100
        assert ctx.idle_timeout_secs == 1800

    def test_construction_custom_ports(self):
        """Construct with custom port range."""
        ctx = DaemonContext(
            "test-daemon",
            "test-project",
            port_range_start=9900,
            port_range_size=50,
        )
        assert ctx.port_range_start == 9900
        assert ctx.port_range_size == 50

    def test_construction_custom_idle(self):
        """Construct with custom idle timeout."""
        ctx = DaemonContext(
            "test-daemon",
            "test-project",
            idle_timeout_secs=600,
        )
        assert ctx.idle_timeout_secs == 600


class TestPIDFileManagement:
    """Test PID file write/read operations."""

    def test_pid_file_write_and_read(self):
        """Write and read back a PID file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")

                # Write PID file
                ctx.write_pid_file(12345, 9883)

                # Read it back
                info = ctx.read_pid_file()
                assert info is not None
                assert info['pid'] == 12345
                assert info['port'] == 9883

    def test_pid_file_path_convention(self):
        """PID file path follows naming convention."""
        ctx = DaemonContext("my-daemon", "my-project")
        path = ctx.pid_file_path()
        assert "my-daemon-my-project" in str(path)
        assert str(path).endswith(".pid")

    def test_read_nonexistent_pid_file(self):
        """Reading nonexistent PID file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                info = ctx.read_pid_file()
                assert info is None


class TestProcessMonitoring:
    """Test is_daemon_alive and process checking."""

    def test_is_daemon_alive_current_process(self):
        """Current process is alive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                ctx.write_pid_file(os.getpid(), 9883)
                assert ctx.is_daemon_alive() is True

    def test_is_daemon_alive_invalid_pid(self):
        """Invalid PID is not alive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                ctx.write_pid_file(999999, 9883)  # Very unlikely PID
                assert ctx.is_daemon_alive() is False

    def test_is_daemon_alive_no_pid_file(self):
        """No PID file means daemon is not alive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                assert ctx.is_daemon_alive() is False

    def test_is_process_running(self):
        """is_process_running utility."""
        # Current process should be running
        assert is_process_running(os.getpid()) is True
        # Invalid PID should not be running
        assert is_process_running(999999) is False


class TestPortAllocation:
    """Test port resolution and allocation."""

    def test_resolve_port_deterministic(self):
        """resolve_port is deterministic for same inputs."""
        ctx1 = DaemonContext("test-daemon", "test-project")
        ctx2 = DaemonContext("test-daemon", "test-project")

        port1 = ctx1.resolve_port()
        port2 = ctx2.resolve_port()

        assert port1 == port2
        assert ctx1.port_range_start <= port1 < ctx1.port_range_start + ctx1.port_range_size

    def test_resolve_port_different_names(self):
        """Different names/projects get different ports (usually)."""
        ctx1 = DaemonContext("daemon-a", "project-1")
        ctx2 = DaemonContext("daemon-b", "project-2")

        port1 = ctx1.resolve_port()
        port2 = ctx2.resolve_port()

        # High probability they differ (though not guaranteed)
        # Just verify they're in range
        assert ctx1.port_range_start <= port1 < ctx1.port_range_start + ctx1.port_range_size
        assert ctx2.port_range_start <= port2 < ctx2.port_range_start + ctx2.port_range_size

    def test_resolve_port_custom_range(self):
        """resolve_port respects custom port range."""
        ctx = DaemonContext(
            "test-daemon",
            "test-project",
            port_range_start=9900,
            port_range_size=50,
        )
        port = ctx.resolve_port()
        assert 9900 <= port < 9950

    def test_find_available_port_in_range(self):
        """find_available_port returns port in configured range."""
        ctx = DaemonContext("test-daemon", "test-project")
        port = ctx.find_available_port()

        assert ctx.port_range_start <= port < ctx.port_range_start + ctx.port_range_size


class TestLogFileManagement:
    """Test log file path conventions and logger setup."""

    def test_log_file_path_convention(self):
        """Log file path follows naming convention."""
        ctx = DaemonContext("my-daemon", "my-project")
        path = ctx.log_file_path()
        assert "my-daemon-my-project" in str(path)
        assert str(path).endswith(".log")
        assert "logs" in str(path)

    def test_setup_logger_creates_handler(self):
        """setup_logger returns a logger with a handler."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.LOG_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                logger = ctx.setup_logger()

                try:
                    assert logger is not None
                    assert len(logger.handlers) > 0

                    # Log a message and verify file is created
                    logger.info("Test message")
                    log_file = ctx.log_file_path()
                    assert log_file.exists()
                finally:
                    # Cleanup logger handlers
                    ctx.cleanup()

    def test_setup_logger_rotation_config(self):
        """setup_logger uses rotation with correct parameters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.LOG_DIR', Path(tmpdir)):
                ctx = DaemonContext(
                    "test-daemon",
                    "test-project",
                    log_max_bytes=1024,
                    log_backup_count=3,
                )
                logger = ctx.setup_logger()

                try:
                    # Verify RotatingFileHandler is configured
                    from logging.handlers import RotatingFileHandler
                    rotating_handler = next(
                        (h for h in logger.handlers if isinstance(h, RotatingFileHandler)),
                        None
                    )
                    assert rotating_handler is not None
                    assert rotating_handler.maxBytes == 1024
                    assert rotating_handler.backupCount == 3
                finally:
                    # Cleanup logger handlers
                    ctx.cleanup()


class TestIdleTimerManagement:
    """Test idle timeout timer installation and cancellation."""

    def test_reset_idle_timer(self):
        """reset_idle_timer schedules a callback."""
        ctx = DaemonContext("test-daemon", "test-project", idle_timeout_secs=1)
        callback_called = threading.Event()

        def callback():
            callback_called.set()

        ctx.reset_idle_timer(callback)

        # Wait for the timer to fire
        assert callback_called.wait(timeout=2.0)

    def test_cancel_idle_timer(self):
        """cancel_idle_timer stops the timer."""
        ctx = DaemonContext("test-daemon", "test-project", idle_timeout_secs=10)
        callback_called = threading.Event()

        def callback():
            callback_called.set()

        ctx.reset_idle_timer(callback)
        ctx.cancel_idle_timer()

        # Give it time to fire if not cancelled
        time.sleep(0.1)
        assert not callback_called.is_set()


class TestCleanup:
    """Test cleanup behavior."""

    def test_cleanup_removes_pid_file(self):
        """cleanup removes the PID file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                ctx.write_pid_file(12345, 9883)

                # Verify file exists
                assert ctx.pid_file_path().exists()

                # Cleanup
                ctx.cleanup()

                # Verify file is gone
                assert not ctx.pid_file_path().exists()

    def test_cleanup_cancels_timer(self):
        """cleanup cancels any pending timer."""
        ctx = DaemonContext("test-daemon", "test-project", idle_timeout_secs=10)
        callback_called = threading.Event()

        def callback():
            callback_called.set()

        ctx.reset_idle_timer(callback)
        ctx.cleanup()

        time.sleep(0.1)
        assert not callback_called.is_set()


class TestWatchdogRespawn:
    """Test watchdog_respawn helper."""

    def test_watchdog_respawn_no_pid_file(self):
        """watchdog_respawn returns True when no PID file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                # Mock subprocess.Popen to avoid actually spawning
                with patch('subprocess.Popen') as mock_popen:
                    result = watchdog_respawn("test-daemon", "test-project", "dummy_module")
                    # Should detect missing PID file and return True (respawn triggered)
                    assert result is True
                    # Popen should have been called
                    assert mock_popen.called

    def test_watchdog_respawn_daemon_alive(self):
        """watchdog_respawn returns False when daemon is healthy."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                ctx.write_pid_file(os.getpid(), 9883)

                result = watchdog_respawn("test-daemon", "test-project", "dummy_module")
                # Daemon is healthy (current process), so no respawn
                assert result is False

    def test_watchdog_respawn_daemon_dead(self):
        """watchdog_respawn returns True when daemon PID is not running."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('daemon_helper.PID_DIR', Path(tmpdir)):
                ctx = DaemonContext("test-daemon", "test-project")
                ctx.write_pid_file(999999, 9883)  # Invalid PID

                with patch('subprocess.Popen') as mock_popen:
                    result = watchdog_respawn("test-daemon", "test-project", "dummy_module")
                    # Should detect dead PID and attempt respawn
                    assert result is True
                    assert mock_popen.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
