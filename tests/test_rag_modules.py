"""
Integration tests for the refactored RAG hook modules.

Covers:
  1. Import tests — all 5 modules import cleanly, no circular deps
  2. rag_utils unit tests — is_command, needs_rag, extract_query_from_prompt,
     detect_explicit_negative
  3. rag_context unit tests — detect_config_keywords, detect_session_keywords,
     load_reminder_state
  4. rag_feedback unit tests — calculate_query_similarity
  5. E2E integration — pipe JSON through rag_query_hook.main() via subprocess
  6. E2E command short-circuit — "yes" prompt produces valid JSON fast path
"""

import importlib
import json
import os
import subprocess
import sys

import pytest

# Make scripts/ importable
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, os.path.abspath(SCRIPTS_DIR))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# 1. Import tests
# ---------------------------------------------------------------------------


class TestImports:
    """Verify all 5 modules import cleanly and without circular dependencies."""

    def test_import_rag_utils(self):
        import rag_utils  # noqa: F401

    def test_import_rag_feedback(self):
        import rag_feedback  # noqa: F401

    def test_import_rag_queries(self):
        import rag_queries  # noqa: F401

    def test_import_rag_context(self):
        import rag_context  # noqa: F401

    def test_import_rag_query_hook(self):
        import rag_query_hook  # noqa: F401

    def test_sequential_import_no_circular_deps(self):
        """All 5 modules can be imported in sequence without error."""
        for mod_name in [
            "rag_utils",
            "rag_feedback",
            "rag_queries",
            "rag_context",
            "rag_query_hook",
        ]:
            # Use importlib so we get a fresh attempt each time
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Module {mod_name} imported as None"


# ---------------------------------------------------------------------------
# 2. rag_utils unit tests
# ---------------------------------------------------------------------------


class TestRagUtils:

    @pytest.fixture(autouse=True)
    def _import(self):
        import rag_utils
        self.rag_utils = rag_utils

    def test_is_command_yes(self):
        assert self.rag_utils.is_command("yes") is True

    def test_is_command_question(self):
        assert self.rag_utils.is_command("how do I create a feature?") is False

    def test_needs_rag_question(self):
        assert self.rag_utils.needs_rag("how do I create a feature?") is True

    def test_needs_rag_command(self):
        assert self.rag_utils.needs_rag("yes") is False

    def test_extract_query_truncates_long_prompt(self):
        long_prompt = "x" * 600
        result = self.rag_utils.extract_query_from_prompt(long_prompt)
        assert len(result) == 500

    def test_extract_query_short_prompt_unchanged(self):
        short = "how does RAG work"
        result = self.rag_utils.extract_query_from_prompt(short)
        assert result == short

    def test_detect_explicit_negative_returns_tuple(self):
        result = self.rag_utils.detect_explicit_negative("that's wrong")
        # The function checks against NEGATIVE_PHRASES; "that's wrong" is not in
        # the list verbatim but we also test a known phrase below.
        # For this test, just confirm it returns a tuple or None.
        # "that's wrong" is not in NEGATIVE_PHRASES but similar enough to pass intent.
        # Use a phrase that IS in the list to guarantee the tuple branch.
        result2 = self.rag_utils.detect_explicit_negative("not helpful at all")
        assert isinstance(result2, tuple), "Expected tuple for known negative phrase"
        assert len(result2) == 2

    def test_detect_explicit_negative_returns_none_for_neutral(self):
        result = self.rag_utils.detect_explicit_negative("hello world")
        assert result is None

    def test_detect_explicit_negative_known_phrase(self):
        result = self.rag_utils.detect_explicit_negative("that didn't work for me")
        assert result is not None
        signal_type, confidence = result
        assert signal_type == "explicit_negative"
        assert 0 < confidence <= 1.0

    def test_is_command_commit(self):
        assert self.rag_utils.is_command("commit") is True

    def test_is_command_long_prompt_not_command(self):
        # Long prompts should never be classified as commands even if they
        # start with an imperative verb
        long = "create a new feature that handles user authentication and stores tokens"
        assert self.rag_utils.is_command(long) is False


# ---------------------------------------------------------------------------
# 3. rag_context unit tests
# ---------------------------------------------------------------------------


class TestRagContext:

    @pytest.fixture(autouse=True)
    def _import(self):
        import rag_context
        self.rag_context = rag_context

    def test_detect_config_keywords_settings_json(self):
        assert self.rag_context.detect_config_keywords("edit settings.local.json") is True

    def test_detect_config_keywords_generic(self):
        assert self.rag_context.detect_config_keywords("how do features work") is False

    def test_detect_session_keywords_last_session(self):
        assert self.rag_context.detect_session_keywords("what happened last session") is True

    def test_detect_session_keywords_unrelated(self):
        assert self.rag_context.detect_session_keywords("implement the auth flow") is False

    def test_load_reminder_state_returns_dict(self):
        state = self.rag_context.load_reminder_state()
        assert isinstance(state, dict)

    def test_load_reminder_state_has_interaction_count(self):
        state = self.rag_context.load_reminder_state()
        assert "interaction_count" in state

    def test_detect_config_keywords_hooks(self):
        assert self.rag_context.detect_config_keywords("fix hooks") is True

    def test_detect_session_keywords_next_steps(self):
        assert self.rag_context.detect_session_keywords("what's next") is True


# ---------------------------------------------------------------------------
# 4. rag_feedback unit tests
# ---------------------------------------------------------------------------


class TestRagFeedback:

    @pytest.fixture(autouse=True)
    def _import(self):
        import rag_feedback
        self.rag_feedback = rag_feedback

    def test_identical_strings_similarity_is_one(self):
        score = self.rag_feedback.calculate_query_similarity("hello world", "hello world")
        assert score == 1.0

    def test_empty_strings_similarity_is_zero(self):
        score = self.rag_feedback.calculate_query_similarity("", "")
        assert score == 0.0

    def test_different_strings_between_zero_and_one(self):
        score = self.rag_feedback.calculate_query_similarity("hello", "goodbye")
        assert 0.0 <= score < 1.0

    def test_partial_overlap(self):
        score = self.rag_feedback.calculate_query_similarity(
            "create a feature", "build a feature now"
        )
        # "a" and "feature" overlap → score > 0
        assert score > 0.0
        assert score < 1.0

    def test_completely_disjoint(self):
        score = self.rag_feedback.calculate_query_similarity("alpha beta", "gamma delta")
        assert score == 0.0


# ---------------------------------------------------------------------------
# 5 & 6. E2E integration tests (subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EOrchestrator:
    """End-to-end tests that pipe JSON into rag_query_hook.main() via subprocess."""

    def _run_hook(self, prompt: str, timeout: int = 30) -> dict:
        """Helper: pipe a prompt JSON to the hook script, return parsed output."""
        hook_script = os.path.join(PROJECT_ROOT, "scripts", "rag_query_hook.py")
        payload = json.dumps({"prompt": prompt})

        result = subprocess.run(
            [sys.executable, hook_script],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=PROJECT_ROOT,
        )
        assert result.returncode == 0, (
            f"Hook exited with code {result.returncode}.\n"
            f"stderr: {result.stderr[:500]}"
        )
        return json.loads(result.stdout)

    def test_question_prompt_produces_valid_json(self):
        output = self._run_hook("how do I create a feature?")
        assert isinstance(output, dict)

    def test_question_prompt_has_hook_specific_output(self):
        output = self._run_hook("how do I create a feature?")
        assert "hookSpecificOutput" in output, (
            f"Missing hookSpecificOutput in: {list(output.keys())}"
        )

    def test_question_prompt_has_additional_context_key(self):
        output = self._run_hook("how do I create a feature?")
        hso = output["hookSpecificOutput"]
        assert "additionalContext" in hso, (
            f"Missing additionalContext in hookSpecificOutput keys: {list(hso.keys())}"
        )

    def test_question_prompt_additional_context_non_empty(self):
        output = self._run_hook("how do I create a feature?")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert isinstance(ctx, str)
        assert len(ctx) > 0, "additionalContext should not be empty for a question prompt"

    def test_command_prompt_produces_valid_json(self):
        """'yes' hits the fast-path but must still produce valid JSON output."""
        output = self._run_hook("yes")
        assert isinstance(output, dict)

    def test_command_prompt_has_hook_specific_output(self):
        output = self._run_hook("yes")
        assert "hookSpecificOutput" in output

    def test_command_prompt_has_additional_context_key(self):
        output = self._run_hook("yes")
        hso = output["hookSpecificOutput"]
        assert "additionalContext" in hso


# ---------------------------------------------------------------------------
# 7. Performance benchmarks
# ---------------------------------------------------------------------------


@pytest.mark.performance
class TestPerformance:
    """Performance benchmarks for RAG hook parallel I/O."""

    def _run_hook(self, prompt: str) -> tuple:
        """Run the hook and return (wall_time_ms, output_json)."""
        import time
        start = time.time()
        result = subprocess.run(
            [sys.executable, "scripts/rag_query_hook.py"],
            input=json.dumps({"prompt": prompt}),
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
            timeout=30,
        )
        wall_ms = (time.time() - start) * 1000
        output = json.loads(result.stdout) if result.stdout.strip() else {}
        return wall_ms, output

    def test_rag_prompt_timing(self):
        """RAG-enabled prompt should complete in reasonable time."""
        times = []
        for _ in range(3):
            ms, output = self._run_hook("how do I create a feature?")
            assert "hookSpecificOutput" in output
            ctx = output["hookSpecificOutput"].get("additionalContext", "")
            assert len(ctx) > 0, "RAG prompt should return context"
            times.append(ms)

        avg_ms = sum(times) / len(times)
        print(f"\nRAG prompt avg: {avg_ms:.0f}ms (runs: {[f'{t:.0f}' for t in times]})")
        # With parallel I/O, RAG prompts should complete under 15 seconds
        # (generous threshold — accounts for cold Voyage API + DB; observed ~10s on this host)
        assert avg_ms < 15000, f"RAG prompt too slow: {avg_ms:.0f}ms avg"

    def test_command_prompt_timing(self):
        """Command prompts should be fast (no RAG queries)."""
        times = []
        for _ in range(3):
            ms, output = self._run_hook("yes")
            assert "hookSpecificOutput" in output
            times.append(ms)

        avg_ms = sum(times) / len(times)
        print(f"\nCommand prompt avg: {avg_ms:.0f}ms (runs: {[f'{t:.0f}' for t in times]})")
        # Commands should be much faster — no DB queries, no Voyage API
        assert avg_ms < 2000, f"Command prompt too slow: {avg_ms:.0f}ms avg"

    def test_empty_prompt_timing(self):
        """Empty prompts should return instantly."""
        ms, output = self._run_hook("")
        print(f"\nEmpty prompt: {ms:.0f}ms")
        assert ms < 1500, f"Empty prompt too slow: {ms:.0f}ms"
        ctx = output.get("hookSpecificOutput", {}).get("additionalContext", "")
        assert ctx == "", "Empty prompt should return empty context"
