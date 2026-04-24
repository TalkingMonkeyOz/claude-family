"""Regression tests for knowledge_consolidation v2 (2026-04-24).

v2 fixed the bug where consolidation appended memory content into
`claude.entities.properties.gotchas` arrays, creating 10K-token blobs per
hub. v2 links memories to concepts via `consolidated_into` only; memory
content stays in `claude.knowledge`.

These tests do NOT require the database. They read the source of the
consolidation script to assert the dangerous pattern is absent and the
replacement function is present. Cheap to run, catches regressions fast.
"""
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT = _REPO_ROOT / "scripts" / "knowledge_consolidation.py"


@pytest.fixture(scope="module")
def script_source() -> str:
    assert _SCRIPT.exists(), f"consolidation script not found at {_SCRIPT}"
    return _SCRIPT.read_text(encoding="utf-8")


def test_no_append_to_entity_properties(script_source):
    """v2 must never write into claude.entities.properties.

    The previous (broken) version ran:
        UPDATE claude.entities SET properties = jsonb_set(
            ..., '{gotchas}', ... || %s::jsonb)
    Any reappearance of that pattern is a regression.
    """
    forbidden_fragments = [
        "UPDATE claude.entities",
        "jsonb_set",
        "'{gotchas}'",
        "SET properties =",
    ]
    offenders = [frag for frag in forbidden_fragments if frag in script_source]
    assert not offenders, (
        "knowledge_consolidation.py contains forbidden property-mutation "
        f"patterns: {offenders}. v2 links via consolidated_into only."
    )


def test_link_and_mark_function_present(script_source):
    """The v2 replacement function must exist."""
    assert "def link_and_mark(" in script_source, \
        "v2 link_and_mark function missing — the linking logic has no home"


def test_old_functions_removed(script_source):
    """Removed v1 helpers must not sneak back in."""
    for removed in ("def extract_new_knowledge(", "def merge_and_mark(",
                    "def is_duplicate_gotcha("):
        assert removed not in script_source, \
            f"{removed} reintroduced — was removed in v2 cleanup"


def test_consolidated_into_is_the_link(script_source):
    """consolidated_into column must be the load-bearing update."""
    assert "SET consolidated_into" in script_source, \
        "consolidated_into UPDATE missing — v2 cannot link memories"


def test_audit_event_type_updated(script_source):
    """v2 uses a distinct audit event_type to differentiate from v1."""
    assert "memories_linked_to_concept" in script_source, \
        "v2 audit event_type missing — historical audit_log would conflate v1/v2"
