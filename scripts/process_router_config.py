#!/usr/bin/env python3
"""
Configuration for Process Router and LLM Classifier

Environment variables:
- PROCESS_ROUTER_LLM_ENABLED: Enable LLM fallback (default: true)
- LLM_CONFIDENCE_THRESHOLD: Minimum confidence for LLM matches (default: 0.5)
- LLM_TIMEOUT_MS: Timeout for LLM calls (default: 1000)
- LLM_CACHE_TTL: Cache TTL in seconds (default: 3600)
- LLM_MAX_PROCESSES: Max processes in classification prompt (default: 25)
- ANTHROPIC_API_KEY: API key for Anthropic (required if LLM enabled)

Author: claude-code-unified
Date: 2025-12-08
Updated: 2025-12-09 - Use secure config from ai-workspace
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from config import ANTHROPIC_API_KEY as SECURE_API_KEY
except ImportError:
    SECURE_API_KEY = None

# LLM Classification Configuration
# Default to enabled if API key is available (safe since it's read-only classification)
LLM_CONFIG = {
    "enabled": os.getenv("PROCESS_ROUTER_LLM_ENABLED", "true").lower() == "true",
    "confidence_threshold": float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.5")),
    "timeout_ms": int(os.getenv("LLM_TIMEOUT_MS", "1000")),
    "cache_ttl_seconds": int(os.getenv("LLM_CACHE_TTL", "3600")),
    "max_processes_in_prompt": int(os.getenv("LLM_MAX_PROCESSES", "25")),
    "model": os.getenv("LLM_CLASSIFIER_MODEL", "claude-3-5-haiku-20241022"),
    "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "500")),
}

# Anthropic API Key - prefer secure config over environment
ANTHROPIC_API_KEY = SECURE_API_KEY or os.getenv("ANTHROPIC_API_KEY", "")

# Feature flags
FEATURES = {
    "llm_fallback": LLM_CONFIG["enabled"],
    "classification_logging": os.getenv("CLASSIFICATION_LOGGING", "true").lower() == "true",
    "fuzzy_matching": False,  # Future enhancement
    "learning_mode": False    # Future: Learn from corrections
}

# Database connection (inherits from parent config)
# NOTE: Do not hardcode credentials - use environment variable or config module
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Cost tracking (Haiku pricing as of Dec 2024)
PRICING = {
    "input_per_million": 1.00,   # $1.00 per 1M input tokens
    "output_per_million": 5.00,  # $5.00 per 1M output tokens
}


def get_config_summary() -> str:
    """Return a summary of current configuration."""
    return f"""Process Router Configuration:
  LLM Fallback: {'ENABLED' if FEATURES['llm_fallback'] else 'DISABLED'}
  Model: {LLM_CONFIG['model']}
  Confidence Threshold: {LLM_CONFIG['confidence_threshold']}
  Cache TTL: {LLM_CONFIG['cache_ttl_seconds']}s
  Classification Logging: {'ENABLED' if FEATURES['classification_logging'] else 'DISABLED'}
  API Key: {'SET' if ANTHROPIC_API_KEY else 'NOT SET'}
"""


if __name__ == "__main__":
    print(get_config_summary())
