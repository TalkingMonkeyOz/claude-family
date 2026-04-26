"""Tests for FB339 drift detector.

Pure-function tests for term extraction + word-boundary matching. DB-touching
paths skip cleanly when DB unreachable.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import drift_detector as dd


# ---------------------------------------------------------------------------
# extract_deprecated_terms
# ---------------------------------------------------------------------------


def test_extract_quoted_term_was_retired():
    body = '"Mission Control Web" was retired months ago in favour of claude-manager-mui.'
    terms = dd.extract_deprecated_terms(body)
    assert "Mission Control Web" in terms


def test_extract_acronym_is_dead():
    body = "MCW is dead — do not use the term anymore."
    terms = dd.extract_deprecated_terms(body)
    assert "MCW" in terms


def test_extract_title_case_with_acronym_paren():
    body = "Mission Control Web (MCW) was retired in 2026-04."
    terms = dd.extract_deprecated_terms(body)
    assert any("Mission Control Web" in t for t in terms)


def test_extract_replace_X_with_Y():
    body = "Replace MCW with claude-manager-mui in all references."
    terms = dd.extract_deprecated_terms(body)
    assert "MCW" in terms


def test_extract_do_not_use_pattern():
    body = "DO NOT use the term Vault for new operational knowledge."
    terms = dd.extract_deprecated_terms(body)
    assert "Vault" in terms


def test_no_match_in_neutral_text():
    body = "The system is running fine, no incidents to report."
    terms = dd.extract_deprecated_terms(body)
    assert terms == set()


def test_stop_terms_excluded():
    body = '"the" was deprecated and "all" is dead too'
    terms = dd.extract_deprecated_terms(body)
    assert not any(t.lower() in dd.STOP_TERMS for t in terms)


def test_empty_input():
    assert dd.extract_deprecated_terms("") == set()
    assert dd.extract_deprecated_terms(None) == set()


# ---------------------------------------------------------------------------
# whole_word_present
# ---------------------------------------------------------------------------


def test_whole_word_match_simple():
    assert dd.whole_word_present("MCW", "Use MCW dashboard for visibility.")


def test_whole_word_no_partial_match():
    # 'MCW' should not match inside 'MCWeb' (no word boundary)
    assert not dd.whole_word_present("MCW", "Configure MCWeb for routing.")


def test_whole_word_case_insensitive():
    assert dd.whole_word_present("Mission Control Web", "the mission control web service")


def test_whole_word_punctuation_boundary():
    assert dd.whole_word_present("MCW", "Open the (MCW), then proceed.")


def test_whole_word_empty_inputs():
    assert not dd.whole_word_present("", "anything")
    assert not dd.whole_word_present("MCW", "")


# ---------------------------------------------------------------------------
# Realistic combined scenarios
# ---------------------------------------------------------------------------


def test_mcw_scenario_end_to_end():
    """The exact session scenario: MCW retired, surface still says MCW."""
    memory = (
        '"Mission Control Web" was retired months ago. The active app is '
        "claude-manager-mui. DO NOT use the term MCW anymore."
    )
    surface = "**UI**: Mission Control Web (MCW) for visibility"
    terms = dd.extract_deprecated_terms(memory)
    flagged = [t for t in terms if dd.whole_word_present(t, surface)]
    assert flagged, f"Should have flagged at least one term, got terms={terms}"
    assert any("MCW" in f or "Mission Control Web" in f for f in flagged)


def test_vault_sunset_scenario():
    memory = (
        '"vault" is sunset per Architecture v2 — replace knowledge-vault with '
        "DB-first storage."
    )
    surface = "knowledge-vault is the primary docs layer for Claude operational knowledge."
    terms = dd.extract_deprecated_terms(memory)
    flagged = [t for t in terms if dd.whole_word_present(t, surface)]
    assert flagged, f"Should have flagged vault-class drift, got terms={terms}"
