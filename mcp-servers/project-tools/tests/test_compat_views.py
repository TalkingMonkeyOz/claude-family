"""
test_compat_views.py — F226 / BT718 verification.

Confirms the 4 row-shape compat views over claude.work_items match the
legacy tables 1:1 in row count and reverse-map status accurately.
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize("legacy,compat", [
    ("claude.features",    "claude.v_features_compat"),
    ("claude.build_tasks", "claude.v_build_tasks_compat"),
    ("claude.feedback",    "claude.v_feedback_compat"),
    ("claude.todos",       "claude.v_todos_compat"),
])
def test_row_count_parity(db_conn, legacy, compat):
    with db_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS c FROM {legacy}")
        legacy_n = cur.fetchone()["c"]
        cur.execute(f"SELECT COUNT(*) AS c FROM {compat}")
        compat_n = cur.fetchone()["c"]
    assert legacy_n == compat_n, f"{compat} {compat_n} vs {legacy} {legacy_n}"


def test_features_status_distribution_matches(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.features GROUP BY status"
        )
        legacy = {r['status']: r['c'] for r in cur.fetchall()}
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.v_features_compat GROUP BY status"
        )
        compat = {r['status']: r['c'] for r in cur.fetchall()}
    assert compat == legacy


def test_build_tasks_status_distribution_matches(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.build_tasks GROUP BY status"
        )
        legacy = {r['status']: r['c'] for r in cur.fetchall()}
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.v_build_tasks_compat GROUP BY status"
        )
        compat = {r['status']: r['c'] for r in cur.fetchall()}
    assert compat == legacy


def test_feedback_status_distribution_matches(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.feedback GROUP BY status"
        )
        legacy = {r['status']: r['c'] for r in cur.fetchall()}
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.v_feedback_compat GROUP BY status"
        )
        compat = {r['status']: r['c'] for r in cur.fetchall()}
    assert compat == legacy


def test_todos_status_distribution_matches(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.todos GROUP BY status"
        )
        legacy = {r['status']: r['c'] for r in cur.fetchall()}
        cur.execute(
            "SELECT status, COUNT(*) AS c FROM claude.v_todos_compat GROUP BY status"
        )
        compat = {r['status']: r['c'] for r in cur.fetchall()}
    assert compat == legacy


def test_features_short_codes_match(db_conn):
    """Each legacy short_code must appear once in the compat view."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT short_code FROM claude.features ORDER BY short_code")
        legacy = [r['short_code'] for r in cur.fetchall()]
        cur.execute("SELECT short_code FROM claude.v_features_compat ORDER BY short_code")
        compat = [r['short_code'] for r in cur.fetchall()]
    assert legacy == compat


def test_feedback_priority_reverse_maps(db_conn):
    """Legacy priority values (high/medium/low) must round-trip through the compat view."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT priority, COUNT(*) AS c FROM claude.feedback "
            "WHERE priority IS NOT NULL GROUP BY priority"
        )
        legacy = {r['priority']: r['c'] for r in cur.fetchall()}
        cur.execute(
            "SELECT priority, COUNT(*) AS c FROM claude.v_feedback_compat "
            "WHERE priority IS NOT NULL GROUP BY priority"
        )
        compat = {r['priority']: r['c'] for r in cur.fetchall()}
    # Legacy NULL priorities collapse on backfill — exclude when comparing.
    for k in legacy:
        assert compat.get(k, 0) == legacy[k], f"priority {k!r}: legacy={legacy[k]} compat={compat.get(k, 0)}"
