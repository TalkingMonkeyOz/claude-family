"""
test_f226_backfill.py — F226 / BT717 verification.

Read-only assertions that the backfill produced the expected counts
across legacy tables, established parent_id links via legacy code lookups,
and that work_item_resolve_legacy() now resolves real FB/F/BT/TODO codes.
"""
from __future__ import annotations


class TestBackfillRowCounts:
    def test_features_backfilled(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM claude.features")
            src = cur.fetchone()["c"]
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.work_items "
                "WHERE attributes->>'legacy_table'='features'"
            )
            dst = cur.fetchone()["c"]
        assert dst == src, f"features backfill mismatch: {src} src vs {dst} work_items"

    def test_build_tasks_backfilled(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM claude.build_tasks")
            src = cur.fetchone()["c"]
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.work_items "
                "WHERE attributes->>'legacy_table'='build_tasks'"
            )
            dst = cur.fetchone()["c"]
        assert dst == src

    def test_feedback_backfilled(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM claude.feedback")
            src = cur.fetchone()["c"]
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.work_items "
                "WHERE attributes->>'legacy_table'='feedback'"
            )
            dst = cur.fetchone()["c"]
        assert dst == src

    def test_todos_backfilled(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS c FROM claude.todos")
            src = cur.fetchone()["c"]
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.work_items "
                "WHERE attributes->>'legacy_table'='todos'"
            )
            dst = cur.fetchone()["c"]
        assert dst == src


class TestCodeHistoryCoverage:
    def test_canonical_w_codes_match_work_items(self, db_conn):
        """Every backfilled work_item must have a 'canonical' W### entry."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS missing FROM claude.work_items wi "
                "WHERE wi.attributes ? 'legacy_table' "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM claude.work_item_code_history h "
                "  WHERE h.work_item_id = wi.work_item_id AND h.code_kind='canonical'"
                ")"
            )
            assert cur.fetchone()["missing"] == 0

    def test_legacy_codes_resolve(self, db_conn):
        """Pick known short codes from each source and resolve them."""
        with db_conn.cursor() as cur:
            cur.execute("SELECT 'F' || short_code AS code FROM claude.features LIMIT 3")
            f_codes = [r["code"] for r in cur.fetchall()]
            cur.execute("SELECT 'BT' || short_code AS code FROM claude.build_tasks LIMIT 3")
            bt_codes = [r["code"] for r in cur.fetchall()]
            cur.execute("SELECT 'FB' || short_code AS code FROM claude.feedback LIMIT 3")
            fb_codes = [r["code"] for r in cur.fetchall()]

            for code in f_codes + bt_codes + fb_codes:
                cur.execute(
                    "SELECT claude.work_item_resolve_legacy(%s) AS resolved",
                    (code,),
                )
                assert cur.fetchone()["resolved"] is not None, f"failed to resolve {code}"


class TestParentLinks:
    """build_tasks.feature_id and features.parent_feature_id must propagate to work_items.parent_id."""

    def test_build_task_parents_propagated(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS missing "
                "FROM claude.build_tasks bt "
                "JOIN claude.work_item_code_history h_self "
                "  ON h_self.short_code = 'BT' || bt.short_code AND h_self.code_kind='legacy' "
                "JOIN claude.work_items wi "
                "  ON wi.work_item_id = h_self.work_item_id "
                "JOIN claude.features f "
                "  ON f.feature_id = bt.feature_id "
                "WHERE bt.feature_id IS NOT NULL "
                "  AND wi.parent_id IS NULL"
            )
            missing = cur.fetchone()["missing"]
        assert missing == 0, f"{missing} build_tasks rows with feature_id but no work_items.parent_id"

    def test_feature_stream_parents_propagated(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS missing "
                "FROM claude.features f "
                "JOIN claude.work_item_code_history h_self "
                "  ON h_self.short_code = 'F' || f.short_code AND h_self.code_kind='legacy' "
                "JOIN claude.work_items wi "
                "  ON wi.work_item_id = h_self.work_item_id "
                "WHERE f.parent_feature_id IS NOT NULL "
                "  AND wi.parent_id IS NULL"
            )
            missing = cur.fetchone()["missing"]
        assert missing == 0


class TestStageMapping:
    """Spot-check stage mapping for known closed legacy rows."""

    def test_completed_features_map_to_done(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS mismatched "
                "FROM claude.features f "
                "JOIN claude.work_item_code_history h "
                "  ON h.short_code = 'F' || f.short_code AND h.code_kind='legacy' "
                "JOIN claude.work_items wi ON wi.work_item_id = h.work_item_id "
                "WHERE f.status = 'completed' AND wi.stage <> 'done'"
            )
            assert cur.fetchone()["mismatched"] == 0

    def test_resolved_feedback_maps_to_done(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS mismatched "
                "FROM claude.feedback fb "
                "JOIN claude.work_item_code_history h "
                "  ON h.short_code = 'FB' || fb.short_code AND h.code_kind='legacy' "
                "JOIN claude.work_items wi ON wi.work_item_id = h.work_item_id "
                "WHERE fb.status = 'resolved' AND wi.stage <> 'done'"
            )
            assert cur.fetchone()["mismatched"] == 0
