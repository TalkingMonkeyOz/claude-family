"""Unit tests for scripts/overlay_resolved_symbol_cache.py — F232.P3.

Covers TTL expiry, project_mismatch full-clear, stale-resolution
invalidation on annotated→unannotated transition, and
force_reresolve override.
"""

from __future__ import annotations

import sys
import os
from typing import Any, Dict, List

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from overlay_resolved_symbol_cache import (
    DEFAULT_TTL_SECONDS,
    ResolvedSymbolCache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class RecordingAggregator:
    """Returns scripted payloads in order; records every call."""

    def __init__(self, payloads: List[Dict[str, Any]]) -> None:
        self._payloads = list(payloads)
        self.calls: List[Dict[str, Any]] = []

    def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        if not self._payloads:
            raise AssertionError("aggregator called more times than scripted")
        return self._payloads.pop(0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCacheHit:
    def test_second_call_hits_cache(self):
        agg = RecordingAggregator([
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
        ])
        cache = ResolvedSymbolCache(aggregator=agg, clock=FakeClock())

        first = cache.get_context_with_cache(
            qualified_name="foo.bar", file_path="a.py", project="P"
        )
        second = cache.get_context_with_cache(
            qualified_name="foo.bar", file_path="a.py", project="P"
        )

        assert first is second
        assert len(agg.calls) == 1


class TestTtlExpiry:
    def test_entry_expires_after_ttl(self):
        clock = FakeClock()
        agg = RecordingAggregator([
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
        ])
        cache = ResolvedSymbolCache(aggregator=agg, clock=clock)

        cache.get_context_with_cache(
            qualified_name="q", file_path="f", project="P"
        )
        clock.advance(DEFAULT_TTL_SECONDS + 1)
        cache.get_context_with_cache(
            qualified_name="q", file_path="f", project="P"
        )

        assert len(agg.calls) == 2


class TestProjectMismatchClearsAll:
    def test_mismatch_full_clears_cache(self):
        agg = RecordingAggregator([
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
            {"resolved_symbol_id": "S2", "coverage_status": "annotated"},
            {"error": "project_mismatch",
             "symbol_project": "Q", "requested_project": "P"},
        ])
        cache = ResolvedSymbolCache(aggregator=agg, clock=FakeClock())

        cache.get_context_with_cache(qualified_name="a", file_path="x", project="P")
        cache.get_context_with_cache(qualified_name="b", file_path="y", project="P")
        assert len(cache) == 2

        result = cache.get_context_with_cache(
            qualified_name="c", file_path="z", project="P"
        )
        assert result.get("error") == "project_mismatch"
        # Full clear, including unrelated entries.
        assert len(cache) == 0


class TestStaleResolutionInvalidation:
    def test_annotated_to_unannotated_replaces_entry(self):
        agg = RecordingAggregator([
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
            {"resolved_symbol_id": "S1", "coverage_status": "unannotated"},
        ])
        cache = ResolvedSymbolCache(aggregator=agg, clock=FakeClock())

        first = cache.get_context_with_cache(
            qualified_name="q", file_path="f", project="P"
        )
        assert first["coverage_status"] == "annotated"

        # force_reresolve bypasses cache → fresh aggregator call returns
        # 'unannotated'. The helper drops the stale 'annotated' entry on put
        # and stores the new payload in its place.
        second = cache.get_context_with_cache(
            qualified_name="q", file_path="f", project="P",
            force_reresolve=True,
        )

        assert second["coverage_status"] == "unannotated"
        # One entry remains (the freshly re-resolved unannotated payload),
        # the stale annotated entry was swept.
        assert len(cache) == 1
        cached = cache.get_context_with_cache(
            qualified_name="q", file_path="f", project="P"
        )
        assert cached["coverage_status"] == "unannotated"


class TestForceReresolveBypass:
    def test_force_reresolve_calls_aggregator_again(self):
        agg = RecordingAggregator([
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
        ])
        cache = ResolvedSymbolCache(aggregator=agg, clock=FakeClock())

        cache.get_context_with_cache(qualified_name="q", file_path="f", project="P")
        cache.get_context_with_cache(
            qualified_name="q", file_path="f", project="P", force_reresolve=True
        )

        assert len(agg.calls) == 2


class TestExplicitInvalidate:
    def test_invalidate_drops_single_key(self):
        agg = RecordingAggregator([
            {"resolved_symbol_id": "S1", "coverage_status": "annotated"},
            {"resolved_symbol_id": "S2", "coverage_status": "annotated"},
        ])
        cache = ResolvedSymbolCache(aggregator=agg, clock=FakeClock())

        cache.get_context_with_cache(qualified_name="a", file_path="x", project="P")
        cache.get_context_with_cache(qualified_name="b", file_path="y", project="P")
        assert len(cache) == 2

        cache.invalidate(("a", "x", "P"))
        assert len(cache) == 1
