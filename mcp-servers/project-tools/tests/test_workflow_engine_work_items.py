"""
test_workflow_engine_work_items.py — F226 / BT715 + BT716.

Tests the WorkflowEngine extension for entity_type='work_items':
  - ENTITY_MAP includes 'work_items' with 'W' prefix
  - _resolve_entity uses 'stage' column instead of 'status'
  - execute_transition UPDATEs work_items.stage (not status)
  - Side effects: set_started_at, set_completed_at (chains check_parent_rollup),
    reopen_clear_completion
  - 22 workflow_transitions rows are present for work_items
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure handler/server import works (mirrors conftest setup, but explicit)
_PROJECT_TOOLS_DIR = Path(__file__).resolve().parents[1]
if str(_PROJECT_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_TOOLS_DIR))


def _project_id(cur) -> str:
    cur.execute(
        "SELECT project_id FROM claude.projects WHERE project_name='claude-family'"
    )
    return cur.fetchone()["project_id"]


def _make_wi(cur, project_id, *, kind="task", stage="planned",
             title="wf-fixture", parent_id=None) -> tuple:
    cur.execute(
        "INSERT INTO claude.work_items "
        "(title, kind, stage, priority, project_id, parent_id) "
        "VALUES (%s, %s, %s, 3, %s, %s) "
        "RETURNING work_item_id, short_code",
        (title, kind, stage, project_id, parent_id),
    )
    row = cur.fetchone()
    return (row["work_item_id"], row["short_code"])


# ---------------------------------------------------------------------------
# workflow_transitions row presence (BT716 verification)
# ---------------------------------------------------------------------------

class TestWorkflowTransitionsRows:

    def test_work_items_has_22_transitions(self, db_conn):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.workflow_transitions "
                "WHERE entity_type='work_items'"
            )
            assert cur.fetchone()["c"] == 22

    @pytest.mark.parametrize("from_stage,to_stage,side_effect", [
        ("triaged",     "in_progress", "set_started_at"),
        ("planned",     "in_progress", "set_started_at"),
        ("blocked",     "in_progress", "set_started_at"),
        ("in_progress", "done",        "set_completed_at"),
        ("in_progress", "dropped",     "set_completed_at"),
        ("triaged",     "dropped",     "set_completed_at"),
        ("planned",     "dropped",     "set_completed_at"),
        ("blocked",     "dropped",     "set_completed_at"),
        ("parked",      "dropped",     "set_completed_at"),
        ("raw",         "dropped",     "set_completed_at"),
        ("done",        "in_progress", "reopen_clear_completion"),
        ("dropped",     "triaged",     "reopen_clear_completion"),
    ])
    def test_side_effect_wired(self, db_conn, from_stage, to_stage, side_effect):
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT side_effect FROM claude.workflow_transitions "
                "WHERE entity_type='work_items' AND from_status=%s AND to_status=%s",
                (from_stage, to_stage),
            )
            row = cur.fetchone()
        assert row is not None, f"missing transition {from_stage}→{to_stage}"
        assert row["side_effect"] == side_effect

    def test_invalid_transition_absent(self, db_conn):
        """raw → in_progress is forbidden per the §5 matrix."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.workflow_transitions "
                "WHERE entity_type='work_items' AND from_status='raw' AND to_status='in_progress'"
            )
            assert cur.fetchone()["c"] == 0


# ---------------------------------------------------------------------------
# WorkflowEngine ENTITY_MAP + stage column dispatch
# ---------------------------------------------------------------------------

class TestEngineEntityMap:

    def test_work_items_in_entity_map(self):
        from server_v2 import WorkflowEngine
        assert 'work_items' in WorkflowEngine.ENTITY_MAP
        table, pk, prefix = WorkflowEngine.ENTITY_MAP['work_items']
        assert table == 'claude.work_items'
        assert pk == 'work_item_id'
        assert prefix == 'W'

    def test_status_col_dispatch(self):
        from server_v2 import WorkflowEngine
        assert WorkflowEngine._status_col('work_items') == 'stage'
        assert WorkflowEngine._status_col('build_tasks') == 'status'
        assert WorkflowEngine._status_col('features') == 'status'
        assert WorkflowEngine._status_col('feedback') == 'status'


# ---------------------------------------------------------------------------
# Side effects via execute_transition
# ---------------------------------------------------------------------------

class TestSideEffectsRoundTrip:
    """Drive transitions through WorkflowEngine and verify side effects fire."""

    def _engine(self, db_conn):
        """Wrap db_conn with a no-commit shim so engine.commit() doesn't break the rollback fixture."""
        from server_v2 import WorkflowEngine

        class _NoCommitConn:
            def __init__(self, inner):
                object.__setattr__(self, "_inner", inner)
            def commit(self):
                return None
            def __getattr__(self, name):
                return getattr(self._inner, name)

        return WorkflowEngine(_NoCommitConn(db_conn))

    def test_set_started_at_fires_on_planned_to_in_progress(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid, code = _make_wi(cur, pid, stage="planned", title="set-started-test")
        engine = self._engine(db_conn)
        result = engine.execute_transition(
            entity_type='work_items',
            item_id=f"W{code}",
            new_status='in_progress',
        )
        assert result['success'], result.get('error')
        assert result['from_status'] == 'planned'
        assert result['to_status'] == 'in_progress'
        assert any(se['name'] == 'set_started_at' for se in result['side_effects'])

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT stage, started_at FROM claude.work_items WHERE work_item_id=%s::uuid",
                (wid,),
            )
            row = cur.fetchone()
        assert row['stage'] == 'in_progress'
        assert row['started_at'] is not None
        db_conn.rollback()

    def test_set_completed_at_fires_on_in_progress_to_done(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid, code = _make_wi(cur, pid, stage="in_progress", title="set-completed-test")
        engine = self._engine(db_conn)
        result = engine.execute_transition(
            entity_type='work_items',
            item_id=f"W{code}",
            new_status='done',
        )
        assert result['success'], result.get('error')
        assert any(se['name'] == 'set_completed_at' for se in result['side_effects'])

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT stage, completed_at FROM claude.work_items WHERE work_item_id=%s::uuid",
                (wid,),
            )
            row = cur.fetchone()
        assert row['stage'] == 'done'
        assert row['completed_at'] is not None
        db_conn.rollback()

    def test_check_parent_rollup_chained_through_set_completed_at(self, db_conn):
        """When the last in_progress child closes, its in_progress parent auto-rolls to done."""
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            parent_wid, parent_code = _make_wi(
                cur, pid, kind="feature", stage="in_progress", title="parent-rollup-test"
            )
            # Single child currently in_progress; closing it should close parent.
            child_wid, child_code = _make_wi(
                cur, pid, kind="task", stage="in_progress", title="child-1",
                parent_id=parent_wid,
            )
        engine = self._engine(db_conn)
        result = engine.execute_transition(
            entity_type='work_items',
            item_id=f"W{child_code}",
            new_status='done',
        )
        assert result['success'], result.get('error')

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT stage, completed_at FROM claude.work_items WHERE work_item_id=%s::uuid",
                (parent_wid,),
            )
            parent_row = cur.fetchone()
        assert parent_row['stage'] == 'done', "parent should auto-rollup to done"
        assert parent_row['completed_at'] is not None
        db_conn.rollback()

    def test_check_parent_rollup_skips_when_siblings_remain(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            parent_wid, parent_code = _make_wi(
                cur, pid, kind="feature", stage="in_progress", title="parent-no-rollup"
            )
            child1_wid, child1_code = _make_wi(
                cur, pid, kind="task", stage="in_progress", title="c1",
                parent_id=parent_wid,
            )
            _, _ = _make_wi(
                cur, pid, kind="task", stage="in_progress", title="c2",
                parent_id=parent_wid,
            )
        engine = self._engine(db_conn)
        result = engine.execute_transition(
            entity_type='work_items',
            item_id=f"W{child1_code}",
            new_status='done',
        )
        assert result['success']

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT stage FROM claude.work_items WHERE work_item_id=%s::uuid",
                (parent_wid,),
            )
            assert cur.fetchone()['stage'] == 'in_progress'
        db_conn.rollback()

    def test_reopen_clears_completion(self, db_conn):
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid, code = _make_wi(cur, pid, stage="in_progress", title="reopen-test")
        engine = self._engine(db_conn)
        # close
        engine.execute_transition(
            entity_type='work_items', item_id=f"W{code}", new_status='done'
        )
        # reopen
        result = engine.execute_transition(
            entity_type='work_items', item_id=f"W{code}", new_status='in_progress'
        )
        assert result['success'], result.get('error')
        assert any(se['name'] == 'reopen_clear_completion' for se in result['side_effects'])

        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT stage, completed_at FROM claude.work_items WHERE work_item_id=%s::uuid",
                (wid,),
            )
            row = cur.fetchone()
        assert row['stage'] == 'in_progress'
        assert row['completed_at'] is None
        db_conn.rollback()

    def test_invalid_transition_rejected(self, db_conn):
        """raw → in_progress is forbidden per the §5 matrix."""
        with db_conn.cursor() as cur:
            pid = _project_id(cur)
            wid, code = _make_wi(cur, pid, stage="raw", title="invalid-trans")
        engine = self._engine(db_conn)
        result = engine.execute_transition(
            entity_type='work_items',
            item_id=f"W{code}",
            new_status='in_progress',
        )
        assert result['success'] is False
        assert 'Invalid transition' in result.get('error', '')
        db_conn.rollback()


# ---------------------------------------------------------------------------
# FB446 backfill verification
# ---------------------------------------------------------------------------

class TestFB446Backfill:
    """Closed build_tasks with a real updated_at should now have completed_at populated."""

    def test_no_recoverable_completed_at_remaining(self, db_conn):
        """build_tasks rows in (completed, cancelled) with non-null updated_at must have completed_at set."""
        with db_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS c FROM claude.build_tasks "
                "WHERE status IN ('completed','cancelled') "
                "  AND updated_at IS NOT NULL "
                "  AND completed_at IS NULL"
            )
            assert cur.fetchone()["c"] == 0
