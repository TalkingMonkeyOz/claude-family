#!/usr/bin/env python3
"""
daemon_helper.py — Shared daemon scaffolding for Claude Family infrastructure.

Extracted from ckg_daemon.py to be reusable across daemons (ckg_daemon,
task_worker, future ones). Single source for PID/log/port/idle/SIGTERM
patterns.

Provides:
- DaemonContext: Encapsulates lifecycle resources (PID, log, port, idle timer, SIGTERM)
- watchdog_respawn: SessionStart hook to check-and-respawn dead daemons

F224 BT698 — extracted 2026-05-02.
"""

import os
import sys
import signal
import logging
import hashlib
import threading
import subprocess
from pathlib import Path
from typing import Optional, Callable
from http.server import HTTPServer
import socket

# Constants (configurable per daemon)
PORT_SCAN_OFFSETS = (0, 7, 13, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71)
PID_DIR = Path.home() / ".claude"
LOG_DIR = Path.home() / ".claude" / "logs"


def _is_port_free(port: int) -> bool:
    """Return True if 127.0.0.1:port can be bound right now."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
    except OSError:
        return False
    finally:
        s.close()
    return True


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


def _parse_pid_file(text: str) -> dict:
    """Parse PID-file text. Accepts both legacy ('<pid>') and kv ('pid=…\\nport=…') forms."""
    out: dict = {}
    text = (text or "").strip()
    if not text:
        return out
    if "=" not in text:
        # Legacy format — just a bare PID.
        try:
            out["pid"] = int(text)
        except ValueError:
            pass
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        if key in ("pid", "port"):
            try:
                out[key] = int(value)
            except ValueError:
                continue
        else:
            out[key] = value
    return out


class DaemonContext:
    """Encapsulates a daemon's lifecycle resources.

    Manages PID file, log file with rotation, port allocation (hashed + prime-step scan),
    idle timeout, and graceful SIGTERM handling.
    """

    def __init__(
        self,
        name: str,                    # e.g. 'ckg-daemon', 'task-worker'
        project_name: str,
        port_range_start: int = 9800,
        port_range_size: int = 100,
        idle_timeout_secs: int = 1800,
        log_max_bytes: int = 10_485_760,   # 10MB
        log_backup_count: int = 5,
    ):
        """Initialize daemon context.

        Args:
            name: Daemon name (used in PID/log filenames, e.g. 'ckg-daemon')
            project_name: Project name (part of PID/log path)
            port_range_start: Base port for hashed allocation
            port_range_size: Range size (e.g. 100 = 9800-9899)
            idle_timeout_secs: Idle shutdown timeout
            log_max_bytes: Max size before rotating log file
            log_backup_count: Number of backup log files to keep
        """
        self.name = name
        self.project_name = project_name
        self.port_range_start = port_range_start
        self.port_range_size = port_range_size
        self.idle_timeout_secs = idle_timeout_secs
        self.log_max_bytes = log_max_bytes
        self.log_backup_count = log_backup_count

        self._logger: Optional[logging.Logger] = None
        self._idle_timer: Optional[threading.Timer] = None
        self._shutting_down = False

    def _pid_file_path(self) -> Path:
        """Return the PID file path for this daemon."""
        return PID_DIR / f"{self.name}-{self.project_name}.pid"

    def pid_file_path(self) -> Path:
        """Return the PID file path (public API)."""
        return self._pid_file_path()

    def _log_file_path(self) -> Path:
        """Return the log file path for this daemon."""
        return LOG_DIR / f"{self.name}-{self.project_name}.log"

    def log_file_path(self) -> Path:
        """Return the log file path (public API)."""
        return self._log_file_path()

    def resolve_port(self) -> int:
        """Deterministic preferred port from daemon name + project.

        Used as a first guess for both daemon spawn and client lookup.
        The daemon may end up on a different port if the hashed slot is taken
        (~21% collision probability with 7+ projects); the actual port is then
        persisted to the PID file. Clients should call read_pid_file() before
        falling back to this function. Uses hashlib (not hash()) for cross-process
        determinism.

        Returns:
            Port in range [port_range_start, port_range_start + port_range_size)
        """
        key = f"{self.name}-{self.project_name}"
        digest = int(hashlib.md5(key.encode()).hexdigest(), 16)
        return self.port_range_start + (digest % self.port_range_size)

    def find_available_port(self) -> int:
        """Find a free port for this daemon, preferring the hashed slot.

        Scans the hash + prime-step offsets, wrapping inside the configured range.
        If every offset is taken (extreme contention) returns the hashed port and
        lets bind fail upstream — better to fail loudly than silently use a stranger's port.

        Returns:
            A port in the configured range (not guaranteed to be free, but tried)
        """
        base = self.resolve_port()
        for offset in PORT_SCAN_OFFSETS:
            candidate = self.port_range_start + ((base - self.port_range_start + offset) % self.port_range_size)
            if _is_port_free(candidate):
                return candidate
        return base

    def write_pid_file(self, pid: int, port: int) -> Path:
        """Write PID + actual bound port atomically.

        Args:
            pid: Process ID to write
            port: Actual bound port

        Returns:
            Path to the PID file
        """
        pid_file = self._pid_file_path()
        payload = f"pid={pid}\nport={port}\n"
        tmp = pid_file.with_suffix(pid_file.suffix + ".tmp")
        tmp.write_text(payload)
        os.replace(tmp, pid_file)
        return pid_file

    def read_pid_file(self) -> Optional[dict]:
        """Read PID + port from the PID file.

        Returns:
            dict with 'pid' and optionally 'port' keys, or None if file doesn't exist or is empty
        """
        pid_file = self._pid_file_path()
        if not pid_file.exists():
            return None
        try:
            info = _parse_pid_file(pid_file.read_text())
            return info if info else None
        except OSError:
            return None

    def is_daemon_alive(self) -> bool:
        """Check if the daemon currently running matches the PID file.

        Returns:
            True if a process with the PID in the file is running, False otherwise
        """
        info = self.read_pid_file()
        if not info or 'pid' not in info:
            return False
        return is_process_running(info['pid'])

    def setup_logger(self) -> logging.Logger:
        """Set up a logger with rotating FileHandler.

        Returns:
            Configured logging.Logger instance
        """
        if self._logger is not None:
            return self._logger

        LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_file = self._log_file_path()

        # Use RotatingFileHandler for size/count based rotation
        from logging.handlers import RotatingFileHandler

        handler = RotatingFileHandler(
            str(log_file),
            maxBytes=self.log_max_bytes,
            backupCount=self.log_backup_count,
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))

        self._logger = logging.getLogger(f'{self.name}-{self.project_name}')
        self._logger.setLevel(logging.INFO)
        self._logger.addHandler(handler)

        return self._logger

    def install_sigterm_handler(self, on_shutdown: Callable[[int, object], None]) -> None:
        """Install a SIGTERM handler for graceful shutdown.

        The handler is a standard Python signal handler accepting (signum, frame).

        Args:
            on_shutdown: Callable(signum, frame) that performs graceful shutdown
        """
        def signal_handler(signum, frame):
            if self._logger:
                self._logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self._shutting_down = True
            on_shutdown(signum, frame)

        signal.signal(signal.SIGTERM, signal_handler)
        if sys.platform != 'win32':
            signal.signal(signal.SIGHUP, signal_handler)

    def reset_idle_timer(self, idle_callback: Callable[[], None]) -> None:
        """Reset the idle shutdown timer.

        Cancels any pending timer and schedules a new one. Call this whenever
        the daemon receives a request.

        Args:
            idle_callback: Callable() that performs shutdown (e.g., server.shutdown())
        """
        if self._idle_timer:
            self._idle_timer.cancel()
        self._idle_timer = threading.Timer(
            self.idle_timeout_secs,
            idle_callback
        )
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def cancel_idle_timer(self) -> None:
        """Cancel the idle shutdown timer (e.g., during cleanup)."""
        if self._idle_timer:
            self._idle_timer.cancel()
            self._idle_timer = None

    def cleanup(self) -> None:
        """Clean up resources on shutdown (close logger, remove PID file, cancel timers)."""
        self.cancel_idle_timer()
        try:
            self._pid_file_path().unlink(missing_ok=True)
        except OSError:
            pass
        if self._logger:
            for handler in self._logger.handlers[:]:
                handler.close()
                self._logger.removeHandler(handler)


def watchdog_respawn(
    name: str,
    project_name: str,
    daemon_module_path: str,
    extra_args: list | None = None,
) -> bool:
    """Called by SessionStart hook. Check PID file + heartbeat; respawn if dead.

    If the daemon is not running, spawns a new one via the provided module.
    On Windows, the child is detached (DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP)
    so it survives the SessionStart hook process exit.

    Returns True only after a post-spawn liveness check confirms the child is
    still alive (catches the FB451 class of bug where wrong argv causes the
    daemon to exit immediately).

    Args:
        name: Daemon name (e.g. 'ckg-daemon')
        project_name: Project name
        daemon_module_path: Path to daemon module (e.g. 'scripts.task_worker')
        extra_args: Positional args appended after `python -m <module>`.
            Required for daemons whose entry script reads sys.argv.

    Returns:
        True if respawn was triggered AND the child is still alive after a
        short settle window. False if the daemon was already healthy or the
        respawn failed.
    """
    ctx = DaemonContext(name, project_name)

    # Check if daemon is alive
    if ctx.is_daemon_alive():
        return False

    # Daemon is dead — respawn it
    try:
        argv = [sys.executable, '-m', daemon_module_path]
        if extra_args:
            argv.extend(str(a) for a in extra_args)

        popen_kwargs = dict(
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if sys.platform == 'win32':
            # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            popen_kwargs['creationflags'] = 0x00000008 | 0x00000200
        else:
            popen_kwargs['start_new_session'] = True

        proc = subprocess.Popen(argv, **popen_kwargs)

        # Settle window: catch immediate-exit failures (wrong argv, import error).
        try:
            rc = proc.wait(timeout=1.0)
            # Process exited within 1s — respawn failed.
            return False
        except subprocess.TimeoutExpired:
            # Still running after settle window — success.
            return True
    except Exception:
        return False
