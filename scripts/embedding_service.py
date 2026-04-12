#!/usr/bin/env python3
"""
Embedding Service — Shared HTTP server for text embeddings.

Loads the ONNX model (BAAI/bge-large-en-v1.5, ~1.4GB) ONCE and serves all
Claude instances via HTTP. Eliminates per-instance model duplication.

Lifecycle:
  - Spawned by session startup hook (or manually)
  - Listens on localhost:9900
  - Auto-exits after 60 minutes of idle time
  - PID file: ~/.claude/embedding-service.pid
  - Log file: ~/.claude/logs/embedding-service.log

Endpoints:
  GET  /health       — Status, uptime, model info, call count
  POST /embed        — Single text embedding  {"text": "..."}
  POST /embed_batch  — Batch embedding  {"texts": ["...", "..."]}

Usage:
  python embedding_service.py              # Start service
  python embedding_service.py --status     # Check if running
  python embedding_service.py --stop       # Stop running service

Environment:
  EMBEDDING_SERVICE_PORT  — Override port (default: 9900)
  HF_HUB_OFFLINE=1       — Set automatically to prevent network calls

Author: Claude Family Infrastructure
Created: 2026-04-12
"""

import sys
import os
import json
import time
import signal
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_PORT = 9900
IDLE_TIMEOUT_SECS = 60 * 60  # 60 minutes (longer than CKG — this serves everyone)
MODEL_NAME = 'BAAI/bge-large-en-v1.5'
MODEL_DIMS = 1024
PID_DIR = Path.home() / ".claude"
LOG_DIR = Path.home() / ".claude" / "logs"
PID_FILE = PID_DIR / "embedding-service.pid"
LOG_FILE = LOG_DIR / "embedding-service.log"

# Prevent HuggingFace network calls and ONNX threading issues
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
os.environ.setdefault('OMP_NUM_THREADS', '2')  # Allow 2 threads for embedding perf
os.environ.setdefault('ONNXRUNTIME_PROVIDERS', 'CPUExecutionProvider')

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger('embedding-service')
logger.setLevel(logging.INFO)

# File handler — main log
_file_handler = logging.FileHandler(str(LOG_FILE), encoding='utf-8')
_file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(_file_handler)

# Stderr handler — visible during manual startup
_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s', datefmt='%H:%M:%S'
))
logger.addHandler(_stderr_handler)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------
_model = None
_model_lock = threading.Lock()
_model_load_time: Optional[float] = None


def _load_model():
    """Load FastEmbed ONNX model (thread-safe, one-time)."""
    global _model, _model_load_time
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        logger.info(f"Loading model {MODEL_NAME} (this takes ~10-30s)...")
        start = time.time()
        try:
            from fastembed import TextEmbedding
            _model = TextEmbedding(MODEL_NAME)
            _model_load_time = time.time() - start
            logger.info(f"Model loaded in {_model_load_time:.1f}s ({MODEL_DIMS} dims, ONNX)")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    return _model


# ---------------------------------------------------------------------------
# Embedding functions
# ---------------------------------------------------------------------------
_call_count = 0
_call_lock = threading.Lock()


def embed_single(text: str) -> Optional[list]:
    """Embed a single text string."""
    global _call_count
    if not text or not text.strip():
        return None
    model = _load_model()
    start = time.time()
    embeddings = list(model.embed([text]))
    vec = embeddings[0].tolist()
    elapsed = time.time() - start
    with _call_lock:
        _call_count += 1
        count = _call_count
    if elapsed > 2.0:
        logger.warning(f"Slow embed: {elapsed:.1f}s, {len(text)} chars (call #{count})")
    elif count <= 5 or count % 100 == 0:
        logger.info(f"Embed OK: {elapsed:.3f}s, {len(text)} chars (call #{count})")
    return vec


def embed_batch(texts: list) -> Optional[list]:
    """Embed multiple texts."""
    global _call_count
    if not texts:
        return None
    model = _load_model()
    start = time.time()
    embeddings = list(model.embed(texts))
    vecs = [e.tolist() for e in embeddings]
    elapsed = time.time() - start
    with _call_lock:
        _call_count += len(texts)
        count = _call_count
    logger.info(f"Batch OK: {len(texts)} texts in {elapsed:.1f}s ({elapsed/len(texts):.3f}s/text, total #{count})")
    return vecs


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class EmbeddingHandler(BaseHTTPRequestHandler):
    """Handles embedding HTTP requests."""

    protocol_version = "HTTP/1.0"

    def log_message(self, format, *args):
        """Suppress default HTTP logging — we use our own logger."""
        pass

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
                'model': MODEL_NAME,
                'dimensions': MODEL_DIMS,
                'model_loaded': _model is not None,
                'model_load_time': round(_model_load_time, 1) if _model_load_time else None,
                'call_count': _call_count,
                'uptime_seconds': int(time.time() - self.server.start_time),
                'pid': os.getpid(),
            })
        else:
            self._send_json({'error': 'not found'}, 404)

    def do_POST(self):
        self.server.reset_idle_timer()

        if self.path == '/embed':
            self._handle_embed()
        elif self.path == '/embed_batch':
            self._handle_embed_batch()
        else:
            self._send_json({'error': 'not found'}, 404)

    def _handle_embed(self):
        """Handle single text embedding."""
        try:
            data = self._read_body()
            text = data.get('text', '')
            if not text:
                self._send_json({'error': 'missing "text" field'}, 400)
                return
            vec = embed_single(text)
            if vec is None:
                self._send_json({'error': 'embedding failed'}, 500)
                return
            self._send_json({'embedding': vec, 'dimensions': len(vec)})
        except Exception as e:
            logger.error(f"Embed error: {e}")
            self._send_json({'error': str(e)}, 500)

    def _handle_embed_batch(self):
        """Handle batch text embedding."""
        try:
            data = self._read_body()
            texts = data.get('texts', [])
            if not texts:
                self._send_json({'error': 'missing "texts" field'}, 400)
                return
            vecs = embed_batch(texts)
            if vecs is None:
                self._send_json({'error': 'embedding failed'}, 500)
                return
            self._send_json({'embeddings': vecs, 'count': len(vecs), 'dimensions': MODEL_DIMS})
        except Exception as e:
            logger.error(f"Batch embed error: {e}")
            self._send_json({'error': str(e)}, 500)


# ---------------------------------------------------------------------------
# Server with idle timeout
# ---------------------------------------------------------------------------
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class EmbeddingServer(ThreadingHTTPServer):
    """HTTP server with idle timeout."""

    def __init__(self, port: int):
        self.start_time = time.time()
        self._idle_timer: Optional[threading.Timer] = None
        super().__init__(('127.0.0.1', port), EmbeddingHandler)
        self.reset_idle_timer()

    def reset_idle_timer(self):
        if self._idle_timer:
            self._idle_timer.cancel()
        self._idle_timer = threading.Timer(IDLE_TIMEOUT_SECS, self._idle_shutdown)
        self._idle_timer.daemon = True
        self._idle_timer.start()

    def _idle_shutdown(self):
        logger.info(f"Idle timeout ({IDLE_TIMEOUT_SECS}s) - shutting down")
        self.shutdown()

    def cleanup(self):
        if self._idle_timer:
            self._idle_timer.cancel()
        PID_FILE.unlink(missing_ok=True)
        logger.info(f"Cleanup complete (served {_call_count} embeddings)")


# ---------------------------------------------------------------------------
# PID management
# ---------------------------------------------------------------------------
def write_pid_file():
    PID_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def read_pid() -> Optional[int]:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


def is_process_running(pid: int) -> bool:
    try:
        if sys.platform == 'win32':
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, PermissionError):
        return False


def is_service_healthy(port: int) -> bool:
    """Check if service is responding on the port."""
    import urllib.request
    try:
        req = urllib.request.Request(f'http://127.0.0.1:{port}/health')
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            return data.get('status') == 'ok'
    except Exception:
        return False


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------
def cmd_status(port: int):
    """Check service status."""
    pid = read_pid()
    if pid and is_process_running(pid):
        if is_service_healthy(port):
            import urllib.request
            resp = urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3)
            data = json.loads(resp.read())
            print(f"Embedding service is RUNNING (PID {pid}, port {port})")
            print(f"  Model: {data.get('model', '?')}")
            print(f"  Loaded: {data.get('model_loaded', '?')}")
            print(f"  Calls: {data.get('call_count', 0)}")
            print(f"  Uptime: {data.get('uptime_seconds', 0)}s")
        else:
            print(f"Embedding service PID {pid} exists but not responding on port {port}")
    else:
        print("Embedding service is NOT running")
        if pid:
            PID_FILE.unlink(missing_ok=True)
            print("  (Cleaned up stale PID file)")
    sys.exit(0)


def cmd_stop():
    """Stop running service."""
    pid = read_pid()
    if pid and is_process_running(pid):
        if sys.platform == 'win32':
            os.system(f'taskkill /PID {pid} /F >nul 2>&1')
        else:
            os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        print(f"Embedding service stopped (PID {pid})")
    else:
        print("Embedding service is not running")
        if PID_FILE.exists():
            PID_FILE.unlink(missing_ok=True)
    sys.exit(0)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    port = int(os.environ.get('EMBEDDING_SERVICE_PORT', DEFAULT_PORT))

    # Handle CLI commands
    if '--status' in sys.argv:
        cmd_status(port)
    if '--stop' in sys.argv:
        cmd_stop()

    # Check if already running
    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        if is_service_healthy(port):
            logger.info(f"Service already running (PID {existing_pid}), exiting")
            print(f"Embedding service already running (PID {existing_pid})")
            sys.exit(0)
        else:
            logger.warning(f"Stale PID {existing_pid} (not healthy), taking over")
            PID_FILE.unlink(missing_ok=True)

    # Pre-load model before starting server
    logger.info(f"Starting embedding service on port {port}...")
    _load_model()

    # Write PID and start server
    write_pid_file()

    try:
        server = EmbeddingServer(port)
        logger.info(
            f"Embedding service started: port={port} pid={os.getpid()} "
            f"model={MODEL_NAME} dims={MODEL_DIMS} "
            f"idle_timeout={IDLE_TIMEOUT_SECS}s"
        )
        print(f"Embedding service running on http://127.0.0.1:{port} (PID {os.getpid()})")

        # Graceful shutdown
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down")
            server.shutdown()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        server.serve_forever()

    except OSError as e:
        if e.errno == 10048 or 'Address already in use' in str(e):
            logger.warning(f"Port {port} in use - service likely already running")
            print(f"Port {port} already in use")
            sys.exit(0)
        raise
    except Exception as e:
        logger.error(f"Service failed: {e}")
        raise
    finally:
        if 'server' in locals():
            server.cleanup()


if __name__ == '__main__':
    main()
