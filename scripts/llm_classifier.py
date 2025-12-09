#!/usr/bin/env python3
"""
LLM-based Process Classifier

Uses Claude Haiku to classify user prompts into process categories
when regex/keyword matching fails. This is the fallback tier that
provides semantic understanding of user intent.

Architecture:
  TIER 1: Fast regex/keywords (0-1ms, $0)
  TIER 2: LLM Classification (200-500ms, ~$0.0002 per call) <-- This module

Features:
- Anthropic SDK integration (Claude Haiku)
- In-memory caching (1-hour TTL)
- Usage stats tracking
- Confidence threshold filtering
- Graceful error handling

Cost: ~$0.0002 per classification (~$0.60/month for 1000 prompts/day at 10% fallback)

Author: claude-code-unified
Date: 2025-12-08
Based on: mcp-servers/orchestrator/PROCESS_ROUTER_LLM_ENHANCEMENT_PLAN.md
"""

import json
import sys
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ClassificationStats:
    """Track classification statistics for monitoring."""
    total_calls: int = 0
    cache_hits: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost_usd: float = 0.0
    errors: int = 0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "cache_hits": self.cache_hits,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "errors": self.errors,
            "cache_hit_rate": round(self.cache_hits / max(1, self.total_calls + self.cache_hits), 2)
        }


class ProcessClassifier:
    """LLM-based classifier for process intent detection."""

    def __init__(self, api_key: str, config: dict):
        """
        Initialize classifier with API key and config.

        Args:
            api_key: Anthropic API key
            config: Configuration dict with:
                - confidence_threshold: float (0.0-1.0)
                - cache_ttl_seconds: int
                - max_processes_in_prompt: int
                - model: str (model name)
                - max_tokens: int
        """
        self.api_key = api_key
        self.config = config
        self.cache: Dict[str, Tuple[List[Dict], float]] = {}  # prompt -> (matches, timestamp)
        self.stats = ClassificationStats()
        self._client = None

        # Pricing (Haiku as of Dec 2024)
        self.input_price_per_million = 1.00
        self.output_price_per_million = 5.00

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise RuntimeError("anthropic package not installed. Run: pip install anthropic")
        return self._client

    def classify(self, user_prompt: str, processes: List[Dict]) -> List[Dict]:
        """
        Classify user prompt into process matches.

        Args:
            user_prompt: The user's input text
            processes: List of process dicts with:
                - process_id: str
                - name: str
                - description: str
                - category: str
                - keywords: List[str] (optional)

        Returns:
            List of matched processes with confidence scores:
            [{"process_id": "...", "confidence": 0.95, "reasoning": "..."}]
        """
        # Check cache first
        cache_key = self._get_cache_key(user_prompt)
        cached = self._check_cache(cache_key)
        if cached is not None:
            self.stats.cache_hits += 1
            return cached

        # Build classification prompt
        prompt = self._build_prompt(user_prompt, processes)

        # Call API
        try:
            start_time = time.time()

            response = self.client.messages.create(
                model=self.config.get("model", "claude-3-5-haiku-20241022"),
                max_tokens=self.config.get("max_tokens", 500),
                temperature=0,  # Deterministic for classification
                messages=[{"role": "user", "content": prompt}]
            )

            latency_ms = int((time.time() - start_time) * 1000)

            # Update stats
            self.stats.total_calls += 1
            self.stats.total_tokens_in += response.usage.input_tokens
            self.stats.total_tokens_out += response.usage.output_tokens

            # Calculate cost
            cost = (
                response.usage.input_tokens * self.input_price_per_million / 1_000_000 +
                response.usage.output_tokens * self.output_price_per_million / 1_000_000
            )
            self.stats.total_cost_usd += cost

            # Parse response
            matches = self._parse_response(response.content[0].text)

            # Add latency to matches for logging
            for match in matches:
                match['latency_ms'] = latency_ms
                match['cost_usd'] = cost / max(1, len(matches))

            # Cache result
            self._cache_result(cache_key, matches)

            return matches

        except Exception as e:
            self.stats.errors += 1
            print(f"LLM classification error: {e}", file=sys.stderr)
            return []

    def _build_prompt(self, user_prompt: str, processes: List[Dict]) -> str:
        """Build the classification prompt."""
        # Limit processes to avoid token bloat
        max_processes = self.config.get("max_processes_in_prompt", 25)
        processes_limited = processes[:max_processes]

        # Format processes for the prompt
        processes_formatted = []
        for p in processes_limited:
            proc = {
                "process_id": p.get("process_id"),
                "name": p.get("name") or p.get("process_name"),
                "description": p.get("description", ""),
                "category": p.get("category", ""),
            }
            if p.get("keywords"):
                proc["keywords"] = p["keywords"][:10]  # Limit keywords
            processes_formatted.append(proc)

        processes_json = json.dumps(processes_formatted, indent=2)
        threshold = self.config.get("confidence_threshold", 0.5)

        return f"""You are a task classifier for a development workflow system.

Analyze the user's prompt and match it to relevant processes.

USER PROMPT: "{user_prompt}"

AVAILABLE PROCESSES:
{processes_json}

INSTRUCTIONS:
1. Identify the user's primary intent
2. Match to one or more processes (usually just one)
3. Assign confidence scores (0.0-1.0)
4. Provide brief reasoning

OUTPUT FORMAT (JSON only, no other text):
{{
  "matches": [
    {{
      "process_id": "PROC-XXX-XXX",
      "confidence": 0.95,
      "reasoning": "Brief explanation of why this process matches"
    }}
  ]
}}

RULES:
- Only return matches with confidence >= {threshold}
- Return empty matches array if no clear match
- Consider keywords, description, and category
- Be conservative with confidence scores
- Common patterns to recognize:
  * "there is a bug", "found an issue", "something broken" -> bug fix workflow
  * "add feature", "implement", "build", "create" -> feature workflow
  * "update docs", "document" -> documentation workflow
  * "test", "verify", "check" -> testing workflow"""

    def _parse_response(self, response_text: str) -> List[Dict]:
        """Parse LLM response and filter by confidence threshold."""
        try:
            # Extract JSON from response (in case LLM adds extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1

            if json_start == -1 or json_end == 0:
                return []

            json_text = response_text[json_start:json_end]
            data = json.loads(json_text)
            matches = data.get("matches", [])

            # Filter by confidence threshold
            threshold = self.config.get("confidence_threshold", 0.5)
            filtered = [m for m in matches if m.get("confidence", 0) >= threshold]

            return filtered

        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse LLM response: {e}", file=sys.stderr)
            print(f"Response was: {response_text[:200]}...", file=sys.stderr)
            return []

    def _get_cache_key(self, user_prompt: str) -> str:
        """Generate cache key from prompt."""
        # Normalize prompt for caching
        return user_prompt.lower().strip()

    def _check_cache(self, cache_key: str) -> Optional[List[Dict]]:
        """Check if result is in cache and not expired."""
        if cache_key in self.cache:
            matches, timestamp = self.cache[cache_key]
            ttl = self.config.get("cache_ttl_seconds", 3600)
            if time.time() - timestamp < ttl:
                return matches
            else:
                # Expired - remove from cache
                del self.cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, matches: List[Dict]) -> None:
        """Cache classification result."""
        self.cache[cache_key] = (matches, time.time())

        # Simple cache size management (keep last 1000 entries)
        if len(self.cache) > 1000:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

    def get_stats(self) -> dict:
        """Return classification statistics."""
        return self.stats.to_dict()

    def clear_cache(self) -> int:
        """Clear the cache and return number of entries cleared."""
        count = len(self.cache)
        self.cache.clear()
        return count


# Singleton instance for reuse
_classifier_instance: Optional[ProcessClassifier] = None


def get_classifier(api_key: str = None, config: dict = None) -> Optional[ProcessClassifier]:
    """
    Get or create the singleton classifier instance.

    Args:
        api_key: Anthropic API key (required on first call)
        config: Configuration dict (required on first call)

    Returns:
        ProcessClassifier instance or None if not configured
    """
    global _classifier_instance

    if _classifier_instance is None:
        if not api_key:
            return None
        if not config:
            config = {
                "confidence_threshold": 0.5,
                "cache_ttl_seconds": 3600,
                "max_processes_in_prompt": 25,
                "model": "claude-3-5-haiku-20241022",
                "max_tokens": 500
            }
        _classifier_instance = ProcessClassifier(api_key, config)

    return _classifier_instance


if __name__ == "__main__":
    # Simple test
    import os

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    config = {
        "confidence_threshold": 0.5,
        "cache_ttl_seconds": 3600,
        "max_processes_in_prompt": 25,
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": 500
    }

    classifier = ProcessClassifier(api_key, config)

    # Test processes
    processes = [
        {
            "process_id": "PROC-DEV-002",
            "name": "Bug Fix Workflow",
            "description": "Report, investigate, fix, and document bugs",
            "category": "dev",
            "keywords": ["bug", "error", "issue", "broken"]
        },
        {
            "process_id": "PROC-DEV-001",
            "name": "Feature Implementation",
            "description": "Implement feature through build tasks",
            "category": "dev",
            "keywords": ["feature", "build", "create"]
        }
    ]

    # Test prompts
    test_prompts = [
        "there is a bug in the login page",
        "I found an issue with user authentication",
        "create a new dashboard feature",
        "hello world"  # Should not match
    ]

    for prompt in test_prompts:
        print(f"\nPrompt: {prompt}")
        matches = classifier.classify(prompt, processes)
        if matches:
            for m in matches:
                print(f"  -> {m['process_id']} (confidence: {m['confidence']:.2f})")
                print(f"     Reasoning: {m['reasoning']}")
        else:
            print("  -> No match")

    print(f"\nStats: {classifier.get_stats()}")
