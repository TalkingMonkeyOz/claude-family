"""Unit tests for scripts/coding_intelligence_writetime_hook.py — F232.P3.

Tests the orchestrator (run()) without touching the live DB or hal MCP.
Mirrors the 10 BPMN test cases at the Python integration layer.
"""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import coding_intelligence_writetime_hook as hook
from coding_intelligence_writetime_hook import (
    INJECTION_HARD_CAP_TOKENS,
    _disabled_aggregator,
    _mock_aggregator,
    compose_injection,
    extract_target,
    is_indexable,
    run,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stub_db(monkeypatch, *, symbols: List[Dict] = None, memories: List[Dict] = None):
    """Stub out DB-touching helpers; pass conn=object() so guards pass."""
    monkeypatch.setattr(hook, "resolve_symbols_for_file",
                        lambda conn, fp: list(symbols or []))
    monkeypatch.setattr(hook, "query_anchored_memories",
                        lambda conn, fp, ids: list(memories or []))
    monkeypatch.setattr(hook, "log_event",
                        lambda *a, **kw: None)


# ---------------------------------------------------------------------------
# Pure helper tests
# ---------------------------------------------------------------------------


class TestIsIndexable:
    @pytest.mark.parametrize("path,expected", [
        ("foo/bar.py", True),
        ("foo/bar.ts", True),
        ("foo/bar.png", False),
        ("foo/bar.min.js", False),
        ("foo/bar.lock", False),
        (None, False),
        ("", False),
    ])
    def test_is_indexable(self, path, expected):
        assert is_indexable(path) is expected


class TestExtractTarget:
    def test_edit_extracts_file_path(self):
        out = extract_target({"tool_name": "Edit",
                              "tool_input": {"file_path": "x.py"}})
        assert out["tool_name"] == "Edit"
        assert out["file_path"] == "x.py"

    def test_bash_returns_no_path(self):
        out = extract_target({"tool_name": "Bash",
                              "tool_input": {"command": "ls"}})
        assert out["file_path"] is None


class TestComposeInjection:
    def test_empty_returns_empty_string(self):
        assert compose_injection(file_path="x.py", memories=[],
                                 overlay_results=[], similar_siblings=[]) == ""

    def test_includes_intent_invariants_concerns(self):
        text = compose_injection(
            file_path="x.py", memories=[],
            overlay_results=[{
                "intent": {"purpose": "auth flow"},
                "invariants": ["must check token"],
                "concerns": ["auth", "PII"],
            }],
            similar_siblings=[],
        )
        assert "auth flow" in text
        assert "must check token" in text
        assert "auth" in text and "PII" in text

    def test_token_cap_enforced(self):
        big_memories = [{"knowledge_id": f"k{i}", "title": "X" * 200}
                        for i in range(500)]
        text = compose_injection(file_path="x.py", memories=big_memories,
                                 overlay_results=[], similar_siblings=[])
        assert len(text) <= INJECTION_HARD_CAP_TOKENS * 4 + 50  # +marker

    def test_idempotent(self):
        kw = dict(
            file_path="x.py",
            memories=[{"knowledge_id": "k1", "title": "T"}],
            overlay_results=[{"intent": {"purpose": "P"}}],
            similar_siblings=[{"qualified_name": "S"}],
        )
        assert compose_injection(**kw) == compose_injection(**kw)


# ---------------------------------------------------------------------------
# Orchestrator tests
# ---------------------------------------------------------------------------


class TestRunUnindexable:
    def test_png_short_circuits(self, monkeypatch):
        _stub_db(monkeypatch)
        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "icon.png"}}, conn=object())
        assert out["_response"] == {"decision": "allow"}
        assert out["outcome"] == "allowed_no_context"
        assert out["fallback_reason"] == "not_indexable"


class TestRunZeroContext:
    def test_no_symbols_no_memories(self, monkeypatch):
        _stub_db(monkeypatch, symbols=[], memories=[])
        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=_disabled_aggregator, conn=object())
        assert out["outcome"] == "allowed_no_context"
        assert out["_response"] == {"decision": "allow"}


class TestRunMemoriesOnly:
    def test_memories_inject_when_no_overlay(self, monkeypatch):
        _stub_db(monkeypatch, symbols=[], memories=[
            {"knowledge_id": "k1", "title": "use cached resolver"},
        ])
        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=_disabled_aggregator, conn=object())
        assert out["outcome"] == "allowed_with_context"
        assert "use cached resolver" in out["_response"]["additionalContext"]


class TestRunOverlayOnly:
    def test_overlay_via_mock(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[])
        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=_mock_aggregator, conn=object())
        assert out["outcome"] == "allowed_with_context"
        assert "mock intent for foo.bar" in out["_response"]["additionalContext"]
        assert out["overlay_calls_n"] >= 1


class TestRunBothSurfaces:
    def test_both_compose(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[{"knowledge_id": "k1", "title": "auth pattern"}])
        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=_mock_aggregator, conn=object())
        ctx = out["_response"]["additionalContext"]
        assert "auth pattern" in ctx
        assert "mock intent for foo.bar" in ctx


class TestRunInitFailure:
    def test_init_failure_aborts_not_silent(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[])

        def boom(**_kw):
            raise NotImplementedError("aggregator not wired")

        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=boom, conn=object())
        assert out["outcome"] == "aborted_init_failure"
        assert out["fallback_reason"] == "init_failure"
        assert out["_response"] == {"decision": "allow"}


class TestRunOverlayException:
    def test_other_aggregator_failure_falls_back(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[{"knowledge_id": "k1", "title": "fallback ok"}])

        def transient(**_kw):
            raise RuntimeError("network timeout")

        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=transient, conn=object())
        # Memory-only injection survives the overlay failure.
        assert out["outcome"] == "allowed_with_context"
        assert out["fallback_reason"] == "overlay_unavailable"
        assert "fallback ok" in out["_response"]["additionalContext"]


class TestRunProjectMismatchRetry:
    def test_project_mismatch_then_recover(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[])

        calls = {"n": 0}

        def flaky(**kwargs):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"error": "project_mismatch",
                        "symbol_project": "Q", "requested_project": "P"}
            return _mock_aggregator(**kwargs)

        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=flaky, conn=object())
        assert calls["n"] == 2  # initial + retry
        assert out["outcome"] == "allowed_with_context"
        assert "mock intent" in out["_response"]["additionalContext"]


class TestRunIdempotency:
    def test_two_runs_match(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[{"knowledge_id": "k1", "title": "auth pattern"}])
        a = run({"tool_name": "Edit",
                 "tool_input": {"file_path": "src/foo.py"}},
                aggregator=_mock_aggregator, conn=object())
        b = run({"tool_name": "Edit",
                 "tool_input": {"file_path": "src/foo.py"}},
                aggregator=_mock_aggregator, conn=object())
        assert a["_response"] == b["_response"]
        assert a["outcome"] == b["outcome"]


class TestRunDisabledMode:
    def test_disabled_aggregator_skips_overlay(self, monkeypatch):
        _stub_db(monkeypatch,
                 symbols=[{"symbol_id": "s1", "qualified_name": "foo.bar"}],
                 memories=[{"knowledge_id": "k1", "title": "T"}])
        out = run({"tool_name": "Edit",
                   "tool_input": {"file_path": "src/foo.py"}},
                  aggregator=_disabled_aggregator, conn=object())
        assert out["overlay_calls_n"] == 0
        assert out["outcome"] == "allowed_with_context"  # memories survive
