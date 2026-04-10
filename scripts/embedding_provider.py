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
import logging
from typing import List, Optional

logger = logging.getLogger('embedding_provider')

# Provider selection: 'fastembed' (default) or 'voyage'
PROVIDER = os.environ.get('EMBEDDING_PROVIDER', 'fastembed').lower()

# Lazy-loaded singletons
_fastembed_model = None
_voyage_client = None


def _get_fastembed_model():
    """Lazy-load FastEmbed model (cached after first call)."""
    global _fastembed_model
    if _fastembed_model is None:
        from fastembed import TextEmbedding
        _fastembed_model = TextEmbedding('BAAI/bge-large-en-v1.5')
        logger.info("Loaded FastEmbed model: BAAI/bge-large-en-v1.5 (1024 dims)")
    return _fastembed_model


def _get_voyage_client():
    """Lazy-load Voyage AI client."""
    global _voyage_client
    if _voyage_client is None:
        import voyageai
        api_key = os.environ.get('VOYAGE_API_KEY')
        if not api_key:
            raise ValueError("VOYAGE_API_KEY not set")
        _voyage_client = voyageai.Client(api_key=api_key)
        logger.info("Loaded Voyage AI client")
    return _voyage_client


def embed(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text. Returns list[float] or None on failure."""
    if not text or not text.strip():
        return None
    try:
        if PROVIDER == 'voyage':
            client = _get_voyage_client()
            result = client.embed([text], model="voyage-3", input_type="query")
            return result.embeddings[0]
        else:
            model = _get_fastembed_model()
            embeddings = list(model.embed([text]))
            return embeddings[0].tolist()
    except Exception as e:
        logger.warning(f"Embedding failed ({PROVIDER}): {e}")
        return None


def embed_batch(texts: List[str]) -> Optional[List[List[float]]]:
    """Generate embeddings for multiple texts. Returns list[list[float]] or None."""
    if not texts:
        return None
    try:
        if PROVIDER == 'voyage':
            client = _get_voyage_client()
            result = client.embed(texts, model="voyage-3", input_type="document")
            return result.embeddings
        else:
            model = _get_fastembed_model()
            embeddings = list(model.embed(texts))
            return [e.tolist() for e in embeddings]
    except Exception as e:
        logger.warning(f"Batch embedding failed ({PROVIDER}): {e}")
        return None


def get_provider_info() -> dict:
    """Return info about the current embedding provider."""
    return {
        "provider": PROVIDER,
        "model": "BAAI/bge-large-en-v1.5" if PROVIDER == "fastembed" else "voyage-3",
        "dimensions": 1024,
        "local": PROVIDER == "fastembed",
    }
