"""Unit tests for tier classification in tool_remember.

Does not touch the database — exercises the classification branches by
inspecting the short/mid/long type maps hardcoded in server.tool_remember.
If those maps change, update the expected sets here.
"""
import inspect

import pytest


def _extract_type_sets():
    """Parse server.tool_remember source to pull out the three type sets.

    We read the function source rather than importing module-level constants
    because the sets are currently defined inline in the function body.
    Refactoring to module level is a follow-up — for now we make the test
    robust to that location.
    """
    import server
    src = inspect.getsource(server.tool_remember)

    def _find_set(label):
        # Expect a line like: `short_types = {"credential", "config", "endpoint"}`
        marker = f"{label} = " + "{"
        idx = src.find(marker)
        if idx < 0:
            pytest.fail(f"Could not find `{label}` set in tool_remember source")
        end = src.find("}", idx)
        literal = src[idx + len(f"{label} = "): end + 1]
        # eval is safe: we just parsed it out of our own source
        return eval(literal, {"__builtins__": {}}, {})

    return _find_set("short_types"), _find_set("mid_types"), _find_set("long_types")


def test_classification_sets_disjoint():
    short, mid, long = _extract_type_sets()
    assert not (short & mid), f"short ∩ mid = {short & mid}"
    assert not (short & long), f"short ∩ long = {short & long}"
    assert not (mid & long), f"mid ∩ long = {mid & long}"


def test_short_covers_secrets_and_config():
    short, _, _ = _extract_type_sets()
    assert "credential" in short
    assert "config" in short
    assert "endpoint" in short


def test_long_covers_patterns_and_gotchas():
    _, _, long = _extract_type_sets()
    assert "pattern" in long
    assert "gotcha" in long
    assert "procedure" in long


def test_mid_covers_learnings_and_decisions():
    _, mid, _ = _extract_type_sets()
    assert "learned" in mid
    assert "decision" in mid
    assert "fact" in mid
