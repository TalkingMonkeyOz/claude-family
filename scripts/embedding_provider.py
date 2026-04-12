#!/usr/bin/env python3
"""Embedding provider abstraction — swap between FastEmbed (local) and Voyage AI (API).

FastEmbed is the default: local CPU inference via ONNX Runtime, no API key needed.
Voyage AI is available as fallback via EMBEDDING_PROVIDER=voyage env var.

Usage:
    from embedding_provider import embed, embed_batch

    vector = embed("some text")           # Returns list[float] or None
    vectors = embed_batch(["a", "b"])      # Returns list[list[float]] or None
"""

import os
import sys
import time
import logging
from typing import List, Optional

# Configure logger: hooks.log (standard) + stderr fallback
import logging.handlers
_LOG_FMT = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
_LOG_PATH = os.path.join(os.path.expanduser('~'), '.claude', 'hooks.log')

logger = logging.getLogger('embedding_provider')
if not logger.handlers:
    os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
    # Use plain FileHandler — RotatingFileHandler fails on Windows when
    # another process (MCP server) holds the file open during rotation
    file_handler = logging.FileHandler(_LOG_PATH, encoding='utf-8')
    file_handler.setFormatter(_LOG_FMT)
    logger.addHandler(file_handler)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(_LOG_FMT)
    logger.addHandler(stderr_handler)
    logger.setLevel(logging.INFO)

# Prevent HuggingFace Hub network calls and ONNX threading issues at module load time
# See: https://github.com/qdrant/fastembed/issues/218
os.environ['HF_HUB_OFFLINE'] = '1'  # Force offline — no network calls during model load
os.environ['TOKENIZERS_PARALLELISM'] = 'false'  # Prevent tokenizer fork warnings
os.environ.setdefault('OMP_NUM_THREADS', '1')  # Prevent ONNX OpenMP thread contention
os.environ.setdefault('ONNXRUNTIME_PROVIDERS', 'CPUExecutionProvider')  # CPU only, no GPU probing

# Provider selection: 'http' (shared service, default), 'fastembed' (in-process), or 'voyage' (API)
PROVIDER = os.environ.get('EMBEDDING_PROVIDER', 'http').lower()
HTTP_SERVICE_URL = os.environ.get('EMBEDDING_SERVICE_URL', 'http://127.0.0.1:9900')

# Import FastEmbed at module level to avoid Python import lock deadlock.
# When _run_async spawns a thread that tries `from fastembed import TextEmbedding`
# while the main thread is also importing, Python's import lock blocks forever.
try:
    from fastembed import TextEmbedding as _TextEmbedding
except ImportError:
    _TextEmbedding = None
    logging.getLogger('embedding_provider').warning("fastembed not installed — embedding disabled")

# Lazy-loaded singletons (thread-safe)
import threading
_fastembed_model = None
_fastembed_lock = threading.Lock()
_voyage_client = None

# Track cold start timing
_model_loaded = False
_embed_call_count = 0


def _get_fastembed_model():
    """Lazy-load FastEmbed model (thread-safe, cached after first call)."""
    global _fastembed_model, _model_loaded
    if _fastembed_model is not None:
        return _fastembed_model
    with _fastembed_lock:
        # Double-check after acquiring lock (another thread may have loaded it)
        if _fastembed_model is not None:
            return _fastembed_model
        start = time.time()
        logger.info(f"Loading FastEmbed model (cold start) pid={os.getpid()} module={__name__} id={id(_fastembed_lock)}")
        _fastembed_model = _TextEmbedding('BAAI/bge-large-en-v1.5')
        elapsed = time.time() - start
        _model_loaded = True
        logger.info(f"FastEmbed model loaded in {elapsed:.1f}s (1024 dims, ONNX)")
    return _fastembed_model


def _get_voyage_client():
    """Lazy-load Voyage AI client."""
    global _voyage_client
    if _voyage_client is None:
        import voyageai
        api_key = os.environ.get('VOYAGE_API_KEY')
        if not api_key:
            logger.error("VOYAGE_API_KEY not set — cannot initialize Voyage AI client")
            raise ValueError("VOYAGE_API_KEY not set")
        _voyage_client = voyageai.Client(api_key=api_key)
        logger.info("Loaded Voyage AI client")
    return _voyage_client


def _http_embed(text: str) -> Optional[List[float]]:
    """Call shared embedding service for a single text."""
    import urllib.request
    import json as _json
    try:
        data = _json.dumps({'text': text}).encode('utf-8')
        req = urllib.request.Request(
            f'{HTTP_SERVICE_URL}/embed',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = _json.loads(resp.read())
            return result.get('embedding')
    except urllib.error.URLError as e:
        logger.error(f"Embedding service unreachable at {HTTP_SERVICE_URL}: {e}")
        # Fallback: try loading model in-process if service is down
        logger.warning("Falling back to in-process FastEmbed")
        model = _get_fastembed_model()
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist()
    except Exception as e:
        logger.error(f"HTTP embed failed: {e}")
        return None


def _http_embed_batch(texts: List[str]) -> Optional[List[List[float]]]:
    """Call shared embedding service for batch texts."""
    import urllib.request
    import json as _json
    try:
        data = _json.dumps({'texts': texts}).encode('utf-8')
        req = urllib.request.Request(
            f'{HTTP_SERVICE_URL}/embed_batch',
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = _json.loads(resp.read())
            return result.get('embeddings')
    except urllib.error.URLError as e:
        logger.error(f"Embedding service unreachable at {HTTP_SERVICE_URL}: {e}")
        logger.warning("Falling back to in-process FastEmbed")
        model = _get_fastembed_model()
        embeddings = list(model.embed(texts))
        return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.error(f"HTTP batch embed failed: {e}")
        return None


def embed(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text. Returns list[float] or None on failure."""
    global _embed_call_count
    _embed_call_count += 1

    if not text or not text.strip():
        logger.warning(f"embed() called with empty text (call #{_embed_call_count})")
        return None
    try:
        start = time.time()
        if PROVIDER == 'http':
            vec = _http_embed(text)
        elif PROVIDER == 'voyage':
            client = _get_voyage_client()
            result = client.embed([text], model="voyage-3", input_type="query")
            vec = result.embeddings[0]
        else:
            model = _get_fastembed_model()
            embeddings = list(model.embed([text]))
            vec = embeddings[0].tolist()

        if vec is None:
            logger.warning(f"embed() returned None (call #{_embed_call_count}, provider={PROVIDER})")
            return None

        elapsed = time.time() - start
        # Log slow calls (>2s suggests cold start or issue)
        if elapsed > 2.0:
            logger.warning(f"embed() slow: {elapsed:.1f}s (call #{_embed_call_count}, text={len(text)} chars)")
        elif _embed_call_count <= 3:
            # Log first few calls to confirm pipeline is working
            logger.info(f"embed() OK: {elapsed:.3f}s, {len(vec)} dims (call #{_embed_call_count})")

        return vec
    except Exception as e:
        logger.error(f"embed() FAILED (call #{_embed_call_count}, provider={PROVIDER}): {e}", exc_info=True)
        return None


def embed_batch(texts: List[str]) -> Optional[List[List[float]]]:
    """Generate embeddings for multiple texts. Returns list[list[float]] or None."""
    if not texts:
        logger.warning("embed_batch() called with empty list")
        return None
    try:
        start = time.time()
        if PROVIDER == 'http':
            vecs = _http_embed_batch(texts)
        elif PROVIDER == 'voyage':
            client = _get_voyage_client()
            result = client.embed(texts, model="voyage-3", input_type="document")
            vecs = result.embeddings
        else:
            model = _get_fastembed_model()
            embeddings = list(model.embed(texts))
            vecs = [e.tolist() for e in embeddings]

        elapsed = time.time() - start
        logger.info(f"embed_batch() OK: {len(texts)} texts in {elapsed:.1f}s ({elapsed/len(texts):.3f}s/text)")
        return vecs
    except Exception as e:
        logger.error(f"embed_batch() FAILED ({len(texts)} texts, provider={PROVIDER}): {e}", exc_info=True)
        return None


def get_provider_info() -> dict:
    """Return info about the current embedding provider."""
    model_map = {"fastembed": "BAAI/bge-large-en-v1.5", "voyage": "voyage-3", "http": "BAAI/bge-large-en-v1.5 (via service)"}
    return {
        "provider": PROVIDER,
        "model": model_map.get(PROVIDER, "unknown"),
        "dimensions": 1024,
        "local": PROVIDER in ("fastembed", "http"),
        "service_url": HTTP_SERVICE_URL if PROVIDER == "http" else None,
        "model_loaded": _model_loaded,
        "embed_call_count": _embed_call_count,
    }
