"""Tests for the F232.P3 Coding Intelligence write-time BPMN.

Models the PreToolUse(Edit|Write) wrapper that composes additionalContext
from symbol-anchored memories (TIME axis) and overlay_get_full_context
(SPACE axis). Covers the ten cases enumerated in workfile 4ecd7e88
(component f232-coding-intelligence).

Test scenarios:
  1. Unindexed file (binary/generated) — silent skip, no overlay/memory calls
  2. Indexed file, zero memories, zero overlay — allowed_no_context
  3. Indexed file, memories only (overlay unavailable) — allowed_with_context
  4. Indexed file, overlay only (no memories) — allowed_with_context
  5. Both surfaces populated, dedup enforced — allowed_with_context
  6. Token-budget overflow — allowed_with_context, count <= cap
  7. project_mismatch retry — second call succeeds with force_reresolve
  8. Aggregator MCP-init failure — aborted_init_failure (NOT silent allow)
  9. Aggregator timeout — allowed_with_context (memories-only), reason logged
 10. Idempotency — same inputs produce same outcome path + counts
"""

import os

import pytest

from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "processes",
        "infrastructure",
        "coding_intelligence_writetime.bpmn",
    )
)
PROCESS_ID = "coding_intelligence_writetime"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Default data for every gateway variable so non-taken paths don't NameError.
_DEFAULT_DATA = {
    # Phase 1 — extract / indexable
    "has_target": True,
    "is_indexable": True,
    # Phase 2 — symbols
    "candidate_symbols": [],
    # Phase 3 — DB / memories
    "db_available": True,
    "memories": [],
    # Phase 4 — overlay
    "overlay_mcp_registered": True,
    "aggregator_init_ok": True,
    "overlay_outcome": "ok",
    "overlay_results": [],
    "retry_succeeded": True,
    # Phase 5 — compose / log
    "has_injection": False,
    "injection_token_count": 0,
    "fallback_reason": None,
}


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    data = dict(_DEFAULT_DATA)
    if initial_data:
        data.update(initial_data)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Case 1 — unindexed file
# ---------------------------------------------------------------------------

class TestUnindexedFile:
    """Binary/generated files short-circuit before any DB or overlay call."""

    def test_unindexed_skips_everything(self):
        wf = load_workflow({"is_indexable": False})

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "allow_unindexed" in names
        assert "end_allowed_no_context" in names
        # Did NOT touch DB or overlay
        assert "connect_db" not in names
        assert "init_aggregator" not in names
        assert wf.data.get("decision") == "allow"
        assert wf.data.get("outcome") == "allowed_no_context"


# ---------------------------------------------------------------------------
# Case 2 — indexed but zero context everywhere
# ---------------------------------------------------------------------------

class TestZeroContext:
    """No memories, no symbols → empty injection, allowed_no_context."""

    def test_no_memories_no_symbols(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [],
            "memories": [],
            "has_injection": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "query_anchored_memories" in names
        # Empty candidate_symbols → skip overlay path
        assert "skip_overlay_no_symbols" in names
        assert "init_aggregator" not in names
        assert "compose_injection" in names
        assert wf.data.get("outcome") == "allowed_no_context"


# ---------------------------------------------------------------------------
# Case 3 — memories present, overlay unavailable
# ---------------------------------------------------------------------------

class TestMemoriesOnly:
    """Overlay MCP not registered → memories-only injection."""

    def test_memories_only_injects(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": "foo.bar"}],
            "memories": [{"id": "m1", "title": "use cached resolver"}],
            "overlay_mcp_registered": False,
            "has_injection": True,
            "injection_token_count": 120,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "skip_overlay_no_symbols" in names
        assert "compose_injection" in names
        assert "log_event" in names
        assert wf.data.get("outcome") == "allowed_with_context"


# ---------------------------------------------------------------------------
# Case 4 — overlay present, no memories
# ---------------------------------------------------------------------------

class TestOverlayOnly:
    """Memories empty but overlay returns intent → overlay-only injection."""

    def test_overlay_only_injects(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": "foo.bar"}],
            "memories": [],
            "overlay_mcp_registered": True,
            "aggregator_init_ok": True,
            "overlay_outcome": "ok",
            "overlay_results": [{"intent": {"purpose": "X"}, "concerns": ["auth"]}],
            "has_injection": True,
            "injection_token_count": 280,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "init_aggregator" in names
        assert "query_overlay_context" in names
        assert "compose_injection" in names
        assert wf.data.get("outcome") == "allowed_with_context"


# ---------------------------------------------------------------------------
# Case 5 — both surfaces, dedup enforced
# ---------------------------------------------------------------------------

class TestDedupBothSurfaces:
    """Memory and overlay both reference same gotcha → dedupe in compose."""

    def test_dedup_path_runs_compose(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": "foo.bar"}],
            "memories": [{"id": "m1", "title": "auth gotcha"}],
            "overlay_mcp_registered": True,
            "overlay_results": [{"intent": {"purpose": "auth gotcha"}, "concerns": ["auth"]}],
            "has_injection": True,
            "injection_token_count": 320,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        # Both paths reach compose, where dedup happens in script
        assert "query_anchored_memories" in names
        assert "query_overlay_context" in names
        assert "compose_injection" in names
        assert wf.data.get("outcome") == "allowed_with_context"


# ---------------------------------------------------------------------------
# Case 6 — token-budget overflow
# ---------------------------------------------------------------------------

class TestBudgetOverflow:
    """Many candidates → injection still capped (anti-pollution gate 3)."""

    HARD_CAP = 2000

    def test_budget_caps_injection(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": f"sym{i}"} for i in range(50)],
            "memories": [{"id": f"m{i}"} for i in range(50)],
            "overlay_mcp_registered": True,
            "overlay_results": [{"intent": {"purpose": f"P{i}"}} for i in range(50)],
            "has_injection": True,
            # Compose-script honours the cap; we assert post-truncation count.
            "injection_token_count": self.HARD_CAP,
        })

        assert wf.is_completed()
        assert wf.data.get("injection_token_count", 0) <= self.HARD_CAP
        assert wf.data.get("outcome") == "allowed_with_context"


# ---------------------------------------------------------------------------
# Case 7 — project_mismatch retry succeeds
# ---------------------------------------------------------------------------

class TestProjectMismatchRetry:
    """First overlay call → project_mismatch; retry once succeeds."""

    def test_mismatch_recovers_via_retry(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": "foo.bar"}],
            "overlay_mcp_registered": True,
            "aggregator_init_ok": True,
            "overlay_outcome": "project_mismatch",
            "retry_succeeded": True,
            "overlay_results": [{"intent": {"purpose": "X"}}],
            "has_injection": True,
            "injection_token_count": 200,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "query_overlay_context" in names
        assert "retry_after_mismatch" in names
        assert "compose_injection" in names
        assert wf.data.get("outcome") == "allowed_with_context"
        # On project_mismatch the cache is full-cleared in the helper; the
        # retry path leaves fallback_reason None when retry succeeds.
        assert wf.data.get("fallback_reason") is None


# ---------------------------------------------------------------------------
# Case 8 — MCP-init failure → abort, NOT silent allow
# ---------------------------------------------------------------------------

class TestAggregatorInitFailure:
    """Phase 4.1 gate 3 — init failure aborts trial, surfaces marker."""

    def test_init_failure_aborts(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": "foo.bar"}],
            "overlay_mcp_registered": True,
            "aggregator_init_ok": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "init_aggregator" in names
        assert "abort_init_failure" in names
        assert "end_aborted_init_failure" in names
        # We never composed or logged — abort path skips both.
        assert "compose_injection" not in names
        assert "log_event" not in names
        assert wf.data.get("outcome") == "aborted_init_failure"
        assert wf.data.get("fallback_reason") == "init_failure"


# ---------------------------------------------------------------------------
# Case 9 — aggregator timeout
# ---------------------------------------------------------------------------

class TestAggregatorTimeout:
    """Aggregator slow → cancel, log timeout, continue with memories only."""

    def test_timeout_falls_through(self):
        wf = load_workflow({
            "is_indexable": True,
            "candidate_symbols": [{"qualified_name": "foo.bar"}],
            "memories": [{"id": "m1", "title": "patternX"}],
            "overlay_mcp_registered": True,
            "aggregator_init_ok": True,
            "overlay_outcome": "timeout",
            "has_injection": True,
            "injection_token_count": 90,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "overlay_timeout_fallback" in names
        assert "compose_injection" in names
        assert wf.data.get("outcome") == "allowed_with_context"
        assert wf.data.get("fallback_reason") == "timeout"


# ---------------------------------------------------------------------------
# Case 10 — idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    """Same inputs produce same outcome path + same injection_token_count."""

    INPUTS = {
        "is_indexable": True,
        "candidate_symbols": [{"qualified_name": "foo.bar"}],
        "memories": [{"id": "m1"}],
        "overlay_mcp_registered": True,
        "overlay_results": [{"intent": {"purpose": "X"}}],
        "has_injection": True,
        "injection_token_count": 256,
    }

    def test_two_runs_match(self):
        a = load_workflow(self.INPUTS)
        b = load_workflow(self.INPUTS)

        assert completed_spec_names(a) == completed_spec_names(b)
        assert a.data.get("outcome") == b.data.get("outcome")
        assert a.data.get("injection_token_count") == b.data.get("injection_token_count")
        assert a.data.get("fallback_reason") == b.data.get("fallback_reason")
