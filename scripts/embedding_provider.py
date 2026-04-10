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

# Configure logger to write to stderr (MCP servers capture stderr in their logs)
logger = logging.getLogger('embedding_provider')
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Provider selection: 'fastembed' (default) or 'voyage'
PROVIDER = os.environ.get('EMBEDDING_PROVIDER', 'fastembed').lower()

# Lazy-loaded singletons
_fastembed_model = None
_voyage_client = None

# Track cold start timing
_model_loaded = False
_embed_call_count = 0


def _get_fastembed_model():
    """Lazy-load FastEmbed model (cached after first call)."""
    global _fastembed_model, _model_loaded
    if _fastembed_model is None:
        start = time.time()
        logger.info("Loading FastEmbed model BAAI/bge-large-en-v1.5 (cold start)...")
        from fastembed import TextEmbedding
        _fastembed_model = TextEmbedding('BAAI/bge-large-en-v1.5')
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


def embed(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text. Returns list[float] or None on failure."""
    global _embed_call_count
    _embed_call_count += 1

    if not text or not text.strip():
        logger.warning(f"embed() called with empty text (call #{_embed_call_count})")
        return None
    try:
        start = time.time()
        if PROVIDER == 'voyage':
            client = _get_voyage_client()
            result = client.embed([text], model="voyage-3", input_type="query")
            vec = result.embeddings[0]
        else:
            model = _get_fastembed_model()
            embeddings = list(model.embed([text]))
            vec = embeddings[0].tolist()

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
        if PROVIDER == 'voyage':
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
    return {
        "provider": PROVIDER,
        "model": "BAAI/bge-large-en-v1.5" if PROVIDER == "fastembed" else "voyage-3",
        "dimensions": 1024,
        "local": PROVIDER == "fastembed",
        "model_loaded": _model_loaded,
        "embed_call_count": _embed_call_count,
    }
