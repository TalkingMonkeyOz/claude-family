#!/usr/bin/env python3
"""
CKG Daemon — Persistent HTTP server for Code Knowledge Graph operations.

Eliminates ~560ms Python startup overhead per hook call by keeping a warm
process with DB connection pool. Hooks call this via curl (~10ms).

Lifecycle:
  - Spawned by session_startup_hook_enhanced.py on SessionStart
  - Listens on localhost:{port} (port derived from project name hash)
  - Auto-exits after 30 minutes of idle time
  - PID file: ~/.claude/ckg-daemon-{project}.pid
  - Log file: ~/.claude/logs/ckg-daemon-{project}.log

Endpoints:
  GET  /health           — Returns status, project, uptime
  POST /collision-check  — Symbol collision detection (replaces code_collision_hook.py)
  POST /reindex-file     — Incremental file re-indexing (future: F161)

Usage:
  python ckg_daemon.py <project_name> <project_path>

Author: Project HAL (F160 CKG Performance Fix)
Created: 2026-03-28
Refactored: 2026-05-02 (BT698 — extracted daemon_helper.py)
"""

import sys
import os
import json
import re
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Optional

# Import shared daemon infrastructure (BT698)
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
from daemon_helper import DaemonContext

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
IDLE_TIMEOUT_SECS = 30 * 60  # 30 minutes
REINDEX_DEBOUNCE_SECS = 2.0   # Wait this long after last request before running indexer

# Symbol extraction patterns (same as code_collision_hook.py)
SYMBOL_PATTERNS = [
    (re.compile(r'^\s*(?:async\s+)?def\s+(\w+)\s*\(', re.MULTILINE), 'function'),
    (re.compile(r'^\s*class\s+(\w+)\s*[\(:]', re.MULTILINE), 'class'),
    (re.compile(r'^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[\(<]', re.MULTILINE), 'function'),
    (re.compile(r'^\s*(?:export\s+)?class\s+(\w+)\s*[\{<]', re.MULTILINE), 'class'),
    (re.compile(r'^\s*(?:export\s+)?interface\s+(\w+)\s*[\{<]', re.MULTILINE), 'interface'),
    (re.compile(r'^\s*(?:public|private|protected|internal)?\s*(?:static\s+)?(?:async\s+)?(?:[\w<>\[\]]+\s+)+(\w+)\s*\(', re.MULTILINE), 'method'),
    (re.compile(r'^\s*(?:pub\s+)?fn\s+(\w+)\s*[\(<]', re.MULTILINE), 'function'),
    (re.compile(r'^\s*(?:pub\s+)?struct\s+(\w+)\s*[\{<]', re.MULTILINE), 'class'),
    (re.compile(r'^\s*(?:pub\s+)?enum\s+(\w+)\s*[\{<]', re.MULTILINE), 'enum'),
]

SKIP_NAMES = {
    'main', 'init', 'new', 'run', 'test', 'setup', 'teardown',
    'get', 'set', 'update', 'delete', 'create', 'list',
    '__init__', '__str__', '__repr__', '__eq__', '__hash__',
    'toString', 'equals', 'hashCode', 'clone',
}


# Port resolution is now in DaemonContext (daemon_helper.py)


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
class DBPool:
    """Minimal connection holder using the shared config module."""

    def __init__(self, project_name: str):
        self.project_name = project_name
        self.project_id: Optional[str] = None
        self._conn = None
        self._connect()

    def _connect(self):
        """Establish DB connection via config module."""
        scripts_dir = os.path.dirname(os.path.abspath(__file__))
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from config import get_db_connection
        self._conn = get_db_connection(strict=True)
        # Cache project_id
        cur = self._conn.cursor()
        cur.execute(
            "SELECT project_id FROM claude.projects WHERE project_name = %s",
            (self.project_name,)
        )
        row = cur.fetchone()
        if row:
            self.project_id = row[0] if not isinstance(row, dict) else row['project_id']
        cur.close()

    def get_conn(self):
        """Get connection, reconnecting if needed."""
        try:
            if self._conn is None or self._conn.closed:
                self._connect()
            # Verify connection is alive with a lightweight query
            cur = self._conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
        except Exception:
            self._connect()
        return self._conn

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()


# ---------------------------------------------------------------------------
# Symbol extraction (shared logic from code_collision_hook.py)
# ---------------------------------------------------------------------------
def extract_new_symbols(content: str, old_content: str = "") -> list[str]:
    """Extract symbol names from new content not in old content."""
    new_names = set()
    old_names = set()
    for pattern, _ in SYMBOL_PATTERNS:
        for match in pattern.finditer(content):
            name = match.group(1)
            if name not in SKIP_NAMES and len(name) > 2:
                new_names.add(name)
        if old_content:
            for match in pattern.finditer(old_content):
                old_names.add(match.group(1))
    return list(new_names - old_names)


def check_collisions(db: DBPool, names: list[str], file_path: str) -> list[dict]:
    """Query DB for symbol collisions."""
    if not names or not db.project_id:
        return []
    conn = db.get_conn()
    cur = conn.cursor()
    placeholders = ','.join(['%s'] * len(names))
    cur.execute(f"""
        SELECT name, kind, file_path, line_number, visibility
        FROM claude.code_symbols
        WHERE project_id = %s
          AND name IN ({placeholders})
          AND file_path != %s
          AND visibility != 'private'
        ORDER BY name, file_path
    """, [db.project_id] + names + [file_path])
    results = cur.fetchall()
    cur.close()
    if results and isinstance(results[0], dict):
        return results
    return [
        {'name': r[0], 'kind': r[1], 'file_path': r[2],
         'line_number': r[3], 'visibility': r[4]}
        for r in results
    ]


# ---------------------------------------------------------------------------
# Reindex Queue — debounces and serializes indexer runs
# ---------------------------------------------------------------------------
class ReindexQueue:
    """Debouncing, serializing queue for code_indexer.py runs.

    Accepts reindex requests (file paths), waits REINDEX_DEBOUNCE_SECS after
    the last request, then runs code_indexer.py ONCE. If the indexer is already
    running, the queued files are held until it finishes, then a new run starts.
    """

    def __init__(self, project_name: str, project_path: str):
        self.project_name = project_name
        self.project_path = project_path
        self._pending_files: set[str] = set()
        self._lock = threading.Lock()
        self._debounce_timer: Optional[threading.Timer] = None
        self._indexer_running = False
        self._run_again_after = False  # Files arrived while indexer was running

    def enqueue(self, file_path: str) -> dict:
        """Add a file to the reindex queue. Returns status info."""
        with self._lock:
            self._pending_files.add(file_path)
            queued_count = len(self._pending_files)

            # Reset debounce timer — wait for more files before running
            if self._debounce_timer:
                self._debounce_timer.cancel()

            if self._indexer_running:
                # Indexer is already running — will run again when it finishes
                self._run_again_after = True
                return {
                    'status': 'queued',
                    'message': f'Indexer running, {queued_count} files queued for next run',
                    'queued_files': queued_count,
                }

            self._debounce_timer = threading.Timer(
                REINDEX_DEBOUNCE_SECS, self._run_indexer
            )
            self._debounce_timer.daemon = True
            self._debounce_timer.start()

            return {
                'status': 'accepted',
                'message': f'{queued_count} files queued, indexer starts in {REINDEX_DEBOUNCE_SECS}s',
                'queued_files': queued_count,
            }

    def _run_indexer(self):
        """Run code_indexer.py once for all pending files."""
        with self._lock:
            if self._indexer_running:
                self._run_again_after = True
                return
            files = self._pending_files.copy()
            self._pending_files.clear()
            self._indexer_running = True
            self._run_again_after = False

        logger.info(f"Reindex starting: {len(files)} files queued")

        try:
            import subprocess as _sp
            indexer_script = Path(__file__).parent / "code_indexer.py"
            if not indexer_script.exists():
                logger.error("code_indexer.py not found")
                return

            # Run synchronously in this thread — we ARE the serializer
            result = _sp.run(
                [sys.executable, str(indexer_script),
                 self.project_name, self.project_path],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                logger.warning(f"Indexer exited with code {result.returncode}: {result.stderr[:500]}")
            else:
                logger.info(f"Reindex completed for {len(files)} files")

        except _sp.TimeoutExpired:
            logger.error("Indexer timed out after 300s")
        except Exception as e:
            logger.error(f"Indexer error: {e}")
        finally:
            with self._lock:
                self._indexer_running = False
                # If more files arrived while we were running, schedule another run
                if self._run_again_after or self._pending_files:
                    self._run_again_after = False
                    self._debounce_timer = threading.Timer(
                        REINDEX_DEBOUNCE_SECS, self._run_indexer
                    )
                    self._debounce_timer.daemon = True
                    self._debounce_timer.start()
                    logger.info(f"More files queued during run, scheduling another indexer pass")


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class CKGHandler(BaseHTTPRequestHandler):
    """Handles CKG daemon HTTP requests."""

    # Use HTTP/1.0 to avoid keep-alive connection hanging
    protocol_version = "HTTP/1.0"

    # Suppress default stderr logging (we use our own logger)
    def log_message(self, format, *args):
        logger.debug(f"HTTP: {format % args}")

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)
        self.wfile.flush()

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        if self.path == '/health':
            self.server.reset_idle_timer()
            self._send_json({
                'status': 'ok',
                'project': self.server.project_name,
                'uptime': int(time.time() - self.server.start_time),
                'symbols': self.server.symbol_count,
            })
        else:
            self._send_json({'error': 'not found'}, 404)

    def do_POST(self):
        self.server.reset_idle_timer()

        if self.path == '/collision-check':
            self._handle_collision_check()
        elif self.path == '/reindex-file':
            self._handle_reindex()
        else:
            self._send_json({'error': 'not found'}, 404)

    def _handle_collision_check(self):
        """Handle collision check — same protocol as PreToolUse hook."""
        start = time.perf_counter()
        try:
            data = self._read_body()
            tool_name = data.get('tool_name', '')
            tool_input = data.get('tool_input', {})

            if tool_name not in ('Write', 'Edit'):
                self._send_json({'decision': 'allow'})
                return

            file_path = tool_input.get('file_path', '')
            if not file_path:
                self._send_json({'decision': 'allow'})
                return

            if tool_name == 'Write':
                content = tool_input.get('content', '')
                old_content = ''
            else:
                content = tool_input.get('new_string', '')
                old_content = tool_input.get('old_string', '')

            if not content:
                self._send_json({'decision': 'allow'})
                return

            new_symbols = extract_new_symbols(content, old_content)
            if not new_symbols:
                elapsed_ms = (time.perf_counter() - start) * 1000
                logger.debug(f"No new symbols [{elapsed_ms:.1f}ms]")
                self._send_json({'decision': 'allow'})
                return

            # Normalize path
            norm_path = file_path.replace('\\', '/').replace(
                f'C:/Projects/{self.server.project_name}/', '')

            collisions = check_collisions(self.server.db, new_symbols, norm_path)
            elapsed_ms = (time.perf_counter() - start) * 1000

            if not collisions:
                logger.info(f"Collision check: {len(new_symbols)} symbols, 0 hits [{elapsed_ms:.1f}ms]")
                self._send_json({'decision': 'allow'})
                return

            warnings = []
            for c in collisions[:5]:
                warnings.append(
                    f"  - {c['kind']} '{c['name']}' already exists in {c['file_path']}:{c['line_number']}"
                )
            warning_text = "Code Knowledge Graph — Symbol collision warning:\n" + "\n".join(warnings)
            if len(collisions) > 5:
                warning_text += f"\n  ... and {len(collisions) - 5} more"

            logger.info(f"Collision check: {len(collisions)} hits [{elapsed_ms:.1f}ms]")
            self._send_json({
                'decision': 'allow',
                'additionalContext': warning_text,
            })

        except Exception as e:
            logger.error(f"Collision check error: {e}")
            self._send_json({'decision': 'allow'})

    def _handle_reindex(self):
        """Queue a file for re-indexing via the serializing ReindexQueue.

        The queue debounces requests (waits 2s after last request) and runs
        code_indexer.py at most once at a time, preventing the N-process
        explosion that was causing 90%+ CPU/memory (FB278).
        """
        start = time.perf_counter()
        try:
            data = self._read_body()
            file_path = data.get('file_path', '')

            result = self.server.reindex_queue.enqueue(file_path or 'project')

            elapsed_ms = (time.perf_counter() - start) * 1000
            logger.info(f"Reindex queued for {file_path or 'project'} [{elapsed_ms:.1f}ms]")
            self._send_json(result)
        except Exception as e:
            logger.error(f"Reindex error: {e}")
            self._send_json({'status': 'error', 'message': str(e)}, 500)


# ---------------------------------------------------------------------------
# Server with idle timeout
# ---------------------------------------------------------------------------
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Thread-per-request HTTP server."""
    daemon_threads = True
    # FB220: refuse port-stealing on Windows. Default HTTPServer enables
    # SO_REUSEADDR which lets a second daemon "succeed" binding the same port,
    # then the kernel routes connections to the first listener — making port
    # collisions silent. We want the second bind to fail loudly so the scan
    # can pick a different port.
    allow_reuse_address = False


class CKGServer(ThreadingHTTPServer):
    """HTTP server with idle timeout and project context."""

    def __init__(self, project_name: str, project_path: str, port: int, daemon_ctx: DaemonContext):
        self.project_name = project_name
        self.project_path = project_path
        self.daemon_ctx = daemon_ctx
        self.start_time = time.time()
        self.symbol_count = 0

        # Initialize reindex queue (serializes indexer runs — FB278 fix)
        self.reindex_queue = ReindexQueue(project_name, project_path)

        # Initialize DB
        self.db = DBPool(project_name)

        # Get symbol count for health endpoint
        try:
            conn = self.db.get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT count(*) as cnt FROM claude.code_symbols WHERE project_id = %s",
                (self.db.project_id,)
            )
            row = cur.fetchone()
            if row:
                self.symbol_count = row['cnt'] if isinstance(row, dict) else row[0]
            cur.close()
        except Exception:
            pass

        super().__init__(('127.0.0.1', port), CKGHandler)
        self.reset_idle_timer()

    def reset_idle_timer(self):
        """Reset the idle shutdown timer."""
        self.daemon_ctx.reset_idle_timer(self._idle_shutdown)

    def _idle_shutdown(self):
        """Shut down after idle timeout."""
        logger.info(f"Idle timeout ({IDLE_TIMEOUT_SECS}s) — shutting down")
        self.shutdown()

    def cleanup(self):
        """Clean up resources on shutdown."""
        self.daemon_ctx.cancel_idle_timer()
        self.db.close()
        self.daemon_ctx.cleanup()
        logger.info("Cleanup complete")


# PID file functions are now in DaemonContext (daemon_helper.py)
# Public API wrappers for backward compatibility:

def read_port_file(project_name: str) -> Optional[int]:
    """Return the actual bound port from the PID file, or None if absent.

    Clients (collision hook, reindex hook, session startup health check) MUST
    prefer this over resolve_port() so they find the daemon even when port
    collision pushed it off its hash slot. Falls back to None on legacy files
    that only carry a PID — caller should then use resolve_port().
    """
    ctx = DaemonContext('ckg-daemon', project_name)
    info = ctx.read_pid_file()
    if info:
        return info.get('port')
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global logger

    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <project_name> <project_path>", file=sys.stderr)
        sys.exit(1)

    project_name = sys.argv[1]
    project_path = sys.argv[2]

    # Create daemon context for lifecycle management (BT698)
    daemon_ctx = DaemonContext(
        'ckg-daemon',
        project_name,
        port_range_start=9800,
        port_range_size=100,
        idle_timeout_secs=IDLE_TIMEOUT_SECS,
    )

    # Set up logging
    logger = daemon_ctx.setup_logger()

    # Check if already running (FB220 — prefer existing daemon's port)
    if daemon_ctx.is_daemon_alive():
        info = daemon_ctx.read_pid_file()
        existing_port = info.get('port') if info else None
        logger.info(
            f"Daemon already running (PID {info['pid']}, port {existing_port}), exiting"
        )
        sys.exit(0)

    # Pick a free port — bind-first scan to avoid TOCTOU races
    hashed = daemon_ctx.resolve_port()
    server = None
    port = None
    last_err: Optional[OSError] = None

    # Scan available ports using daemon_ctx's prime-step logic
    from daemon_helper import PORT_SCAN_OFFSETS
    for offset in PORT_SCAN_OFFSETS:
        candidate = daemon_ctx.port_range_start + ((hashed - daemon_ctx.port_range_start + offset) % daemon_ctx.port_range_size)
        try:
            server = CKGServer(project_name, project_path, candidate, daemon_ctx)
            port = candidate
            break
        except OSError as e:
            last_err = e
            if e.errno == 10048 or 'Address already in use' in str(e):
                logger.info(f"Port {candidate} in use, trying next offset")
                continue
            raise

    if server is None:
        logger.error(
            f"All scanned ports busy for {project_name} (last error: {last_err}). "
            f"If a stale daemon is running, kill it and retry."
        )
        sys.exit(1)

    if port != hashed:
        logger.info(
            f"Port collision: hashed {hashed} was taken, bound on {port} "
            f"instead (persisted to PID file for clients)"
        )

    # Write PID + actual bound port AFTER successful bind
    daemon_ctx.write_pid_file(os.getpid(), port)

    try:
        logger.info(
            f"CKG daemon started: project={project_name} port={port} "
            f"symbols={server.symbol_count} pid={os.getpid()}"
        )

        # Handle graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down gracefully")
            server.shutdown()

        import signal as signal_module
        signal_module.signal(signal_module.SIGTERM, signal_handler)
        if sys.platform != 'win32':
            signal_module.signal(signal_module.SIGHUP, signal_handler)

        server.serve_forever()

    except Exception as e:
        logger.error(f"Daemon failed: {e}")
        raise
    finally:
        if server is not None:
            server.cleanup()


if __name__ == '__main__':
    main()
