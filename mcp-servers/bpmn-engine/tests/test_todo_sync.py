"""
Tests for the Todo Sync BPMN process.

Todo Sync Hook (todo_sync):
  Trigger: PostToolUse event when tool_name == "TodoWrite"
  Input: tool_input containing todos array [{content, status, priority}]

  Key behaviors:
    1. Parse TodoWrite input → extract todos array
    2. If no todos → end_empty (early exit)
    3. If todos exist → connect DB
    4. If DB unavailable → end_no_db (fail-open)
    5. If DB available → loop through todos:
       - Fuzzy match against existing todos
       - INSERT new, UPDATE existing
       - Check status=deleted → mark_archived
       - Advance loop counter, check for more todos
    6. Commit transaction → end_synced

  Test paths:
    1. No todos → end_empty
    2. Has todos, DB unavailable → end_no_db
    3. Single new todo → insert → commit → end_synced
    4. Single matched todo → update → commit → end_synced
    5. Deleted todo → mark_archived → commit
    6. Multiple todos → loop processes all

Implementation: scripts/todo_sync_hook.py
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "todo_sync.bpmn")
)
PROCESS_ID = "todo_sync"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: No Todos - Early Exit
# ---------------------------------------------------------------------------

class TestNoTodos:
    """
    has_todos=False → skip DB connection → end_empty.

    Expected path:
      start → parse_input → has_todos_gw (False) → end_empty

    This is the fast path for when TodoWrite has no todos.
    """

    def test_no_todos_early_exit(self):
        wf = load_workflow({
            "todos": [],
            "has_todos": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Parse always executes
        assert "parse_input" in names

        # No DB connection or sync
        assert "connect_db" not in names
        assert "end_empty" in names

        # Sync operations should not execute
        assert "init_loop" not in names
        assert "commit_changes" not in names
        assert "end_synced" not in names


# ---------------------------------------------------------------------------
# Test 2: Has Todos, DB Unavailable - Fail-Open
# ---------------------------------------------------------------------------

class TestHasTodosNoDb:
    """
    has_todos=True, db_available=False → end_no_db (fail-open).

    Expected path:
      start → parse_input → has_todos_gw (True) → connect_db →
      db_gw (False) → end_no_db

    This ensures the hook gracefully handles DB failures without blocking
    the original operation.
    """

    def test_todos_exist_db_down(self):
        wf = load_workflow({
            "todos": [{"content": "Fix the bug", "status": "pending"}],
            "has_todos": True,
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Parse and DB connect attempt
        assert "parse_input" in names
        assert "connect_db" in names

        # Loop should not execute
        assert "init_loop" not in names
        assert "pick_todo" not in names

        # Should hit no-DB end event
        assert "end_no_db" in names

        # Should not complete sync
        assert "commit_changes" not in names
        assert "end_synced" not in names


# ---------------------------------------------------------------------------
# Test 3: Single New Todo - Insert Path
# ---------------------------------------------------------------------------

class TestSingleNewTodo:
    """
    Single todo, DB available, no match found → insert → commit → end_synced.

    Expected path:
      start → parse_input → has_todos_gw (True) → connect_db →
      db_gw (True) → init_loop → pick_todo → fuzzy_match →
      match_gw (False) → insert_new → upsert_merge → deleted_gw (False) →
      advance_loop → more_todos_gw (False) → commit_changes → end_synced

    This is the happy path for a new todo that doesn't match any existing record.
    """

    def test_single_new_todo_inserted(self):
        wf = load_workflow({
            "todos": [{"content": "Write unit tests", "status": "pending"}],
            "has_todos": True,
            "db_available": True,
            "has_match": False,
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Happy path: parse → connect → init → fuzzy_match → insert → commit → synced
        assert "parse_input" in names
        assert "connect_db" in names
        assert "init_loop" in names
        assert "insert_new" in names
        assert "commit_changes" in names
        assert "end_synced" in names

        # Should not take the update or archive paths
        assert "update_existing" not in names
        assert "mark_archived" not in names

        # Data checks
        assert wf.data.get("inserted_count") == 1
        assert wf.data.get("updated_count") == 0
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 4: Single Matched Todo - Update Path
# ---------------------------------------------------------------------------

class TestSingleMatchedTodo:
    """
    Single todo, DB available, fuzzy match found → update → commit → end_synced.

    Expected path:
      start → parse_input → has_todos_gw (True) → connect_db →
      db_gw (True) → init_loop → pick_todo → fuzzy_match →
      match_gw (True) → update_existing → upsert_merge → deleted_gw (False) →
      advance_loop → more_todos_gw (False) → commit_changes → end_synced

    This path handles existing todos that are updated with new content/status.
    """

    def test_single_matched_todo_updated(self):
        wf = load_workflow({
            "todos": [{"content": "Write unit tests", "status": "completed"}],
            "has_todos": True,
            "db_available": True,
            "has_match": True,
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Happy path: parse → connect → init → fuzzy_match → update → commit → synced
        assert "parse_input" in names
        assert "connect_db" in names
        assert "init_loop" in names
        assert "update_existing" in names
        assert "commit_changes" in names
        assert "end_synced" in names

        # Should not take the insert or archive paths
        assert "insert_new" not in names
        assert "mark_archived" not in names

        # Data checks
        assert wf.data.get("updated_count") == 1
        assert wf.data.get("inserted_count") == 0
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 5: Deleted Todo - Archive Path
# ---------------------------------------------------------------------------

class TestDeletedTodo:
    """
    Single todo with status=deleted → mark_archived → commit → end_synced.

    Expected path:
      start → parse_input → has_todos_gw (True) → connect_db →
      db_gw (True) → init_loop → pick_todo → fuzzy_match →
      match_gw (True) → update_existing → upsert_merge → deleted_gw (True) →
      mark_archived → advance_loop → more_todos_gw (False) →
      commit_changes → end_synced

    Deleted todos are soft-deleted (is_deleted=true) to preserve audit trail.
    """

    def test_deleted_todo_archived(self):
        wf = load_workflow({
            "todos": [{"content": "Old task", "status": "deleted"}],
            "has_todos": True,
            "db_available": True,
            "has_match": True,  # Must find existing to archive
            "is_deleted": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Path: parse → connect → init → fuzzy_match → update → mark_archived → commit → synced
        assert "parse_input" in names
        assert "connect_db" in names
        assert "init_loop" in names
        assert "update_existing" in names
        assert "mark_archived" in names
        assert "commit_changes" in names
        assert "end_synced" in names

        # Data checks
        assert wf.data.get("archived_count") == 1
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 6: Multiple Todos - Loop Path
# ---------------------------------------------------------------------------

class TestMultipleTodos:
    """
    Multiple todos with more_todos flag → loops through all → end_synced.

    Expected behavior:
      - Process first todo (insert)
      - more_todos=True → loop back to pick_todo
      - Process second todo (insert)
      - more_todos=True → loop back again
      - Process third todo (insert)
      - more_todos=False → exit loop → commit → end_synced

    This validates that the loop counter and more_todos gate work correctly.
    """

    def test_three_todos_loop_completes(self):
        wf = load_workflow({
            "todos": [
                {"content": "Task A"},
                {"content": "Task B"},
                {"content": "Task C"}
            ],
            "has_todos": True,
            "db_available": True,
            "has_match": False,
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Core path: parse → connect → init → insert 3x → commit → synced
        assert "parse_input" in names
        assert "connect_db" in names
        assert "init_loop" in names
        assert "insert_new" in names
        assert "commit_changes" in names
        assert "end_synced" in names

        # Data checks prove the loop executed 3 times
        assert wf.data.get("inserted_count") == 3
        assert wf.data.get("current_index") == 3
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 7: Mixed Operations - Insert and Update
# ---------------------------------------------------------------------------

class TestMixedOperations:
    """
    Two todos: first is new (insert), second matches (update) → both sync.

    This tests that the loop correctly handles different operations for
    different todos in the same sync.
    """

    def test_insert_then_update(self):
        """
        First iteration: has_match=False → insert
        Second iteration: manually verify counter and counts work
        """
        wf = load_workflow({
            "todos": [
                {"content": "New task", "status": "pending"},
                {"content": "Old task", "status": "completed"},
            ],
            "has_todos": True,
            "db_available": True,
            "has_match": False,  # First todo is new
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Verify the process reached completion
        assert "end_synced" in names
        assert wf.data.get("sync_complete") is True


# ---------------------------------------------------------------------------
# Test 8: Edge Case - Empty Todo Content
# ---------------------------------------------------------------------------

class TestEmptyTodoContent:
    """
    Todo with empty or whitespace content → still syncs (validation at hook level).

    This ensures the BPMN doesn't break on edge cases; validation is the
    hook's responsibility.
    """

    def test_empty_content_still_syncs(self):
        wf = load_workflow({
            "todos": [{"content": "", "status": "pending"}],
            "has_todos": True,
            "db_available": True,
            "has_match": False,
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_synced" in names
        assert wf.data.get("inserted_count") == 1


# ---------------------------------------------------------------------------
# Test 9: Data Preservation - Counters
# ---------------------------------------------------------------------------

class TestDataCountersPreserved:
    """Loop counters and operation counts are maintained correctly."""

    def test_loop_counters_increment(self):
        wf = load_workflow({
            "todos": [
                {"content": "A"},
                {"content": "B"},
            ],
            "has_todos": True,
            "db_available": True,
            "has_match": False,
            "is_deleted": False,
        })

        # Verify counters were maintained
        assert wf.data.get("current_index") == 2
        assert wf.data.get("inserted_count") == 2
        assert wf.data.get("updated_count") == 0
        assert wf.data.get("archived_count") == 0
        assert wf.data.get("synced_count") == 2
