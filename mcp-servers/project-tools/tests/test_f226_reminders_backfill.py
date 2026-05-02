"""
test_f226_reminders_backfill.py — F226 / BT720.

Verifies claude.scheduled_reminders rows backfilled into work_items
with kind='reminder' and that RM### codes resolve via
work_item_resolve_legacy().
"""
from __future__ import annotations


def test_all_reminders_backfilled(db_conn):
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM claude.scheduled_reminders")
        legacy_n = cur.fetchone()['c']
        cur.execute(
            "SELECT COUNT(*) AS c FROM claude.work_items WHERE kind='reminder'"
        )
        wi_n = cur.fetchone()['c']
    assert wi_n == legacy_n, f"reminders: {legacy_n} legacy vs {wi_n} work_items"


def test_rm_codes_resolve(db_conn):
    """Every legacy RM### code from scheduled_reminders must resolve to a work_item."""
    with db_conn.cursor() as cur:
        cur.execute("SELECT short_code FROM claude.scheduled_reminders")
        rm_codes = [r['short_code'] for r in cur.fetchall()]
        for code in rm_codes:
            cur.execute(
                "SELECT claude.work_item_resolve_legacy(%s) AS resolved", (code,)
            )
            assert cur.fetchone()['resolved'] is not None, f"RM code {code!r} did not resolve"


def test_due_at_typed_column_populated(db_conn):
    """Backfilled reminders must have due_at populated from scheduled_reminders.due_at."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM claude.work_items "
            "WHERE kind='reminder' AND due_at IS NULL"
        )
        assert cur.fetchone()['c'] == 0


def test_surfaced_reminders_mapped_to_done(db_conn):
    """scheduled_reminders rows with surfaced_at IS NOT NULL must map to stage='done'."""
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM claude.work_items wi "
            "JOIN claude.work_item_code_history h "
            "  ON h.work_item_id = wi.work_item_id AND h.code_kind='legacy' "
            "JOIN claude.scheduled_reminders sr ON sr.short_code = h.short_code "
            "WHERE wi.kind='reminder' "
            "  AND sr.surfaced_at IS NOT NULL "
            "  AND wi.stage <> 'done'"
        )
        assert cur.fetchone()['c'] == 0


def test_unfired_reminders_mapped_to_planned(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM claude.work_items wi "
            "JOIN claude.work_item_code_history h "
            "  ON h.work_item_id = wi.work_item_id AND h.code_kind='legacy' "
            "JOIN claude.scheduled_reminders sr ON sr.short_code = h.short_code "
            "WHERE wi.kind='reminder' "
            "  AND sr.surfaced_at IS NULL "
            "  AND wi.stage <> 'planned'"
        )
        assert cur.fetchone()['c'] == 0


def test_task_scope_persistent(db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) AS c FROM claude.work_items "
            "WHERE kind='reminder' AND task_scope <> 'persistent'"
        )
        assert cur.fetchone()['c'] == 0
