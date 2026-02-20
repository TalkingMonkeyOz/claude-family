"""
Tests for Todo Sync and Task Sync BPMN processes.

Todo Sync (todo_sync):
  1. Happy path: todos parsed → DB available → fuzzy match → insert/update → synced
  2. Empty todos: no todos → end_empty
  3. DB unavailable: todos exist but DB down → end_no_db
  4. Fuzzy match update: existing todo found → update (not insert)
  5. Deleted todo: status=deleted → mark_archived
  6. Multi-todo loop: 3 todos → process all → synced

Task Sync (task_sync):
  7. TaskCreate path: create → insert todo → no build_task match → map updated
  8. TaskCreate with build_task match: create → insert → matched → linked → map updated
  9. TaskUpdate path: update → lookup map → update status → not completed → end
  10. TaskUpdate completed + linked: update → advance build_task → check siblings
  11. TaskUpdate all siblings done: advance → all done → surface feature completion
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

TODO_SYNC_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "todo_sync.bpmn")
)
TASK_SYNC_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "task_sync.bpmn")
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(bpmn_file: str, process_id: str, initial_data: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(bpmn_file)
    spec = parser.get_spec(process_id)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ===========================================================================
# TODO SYNC TESTS
# ===========================================================================

class TestTodoSyncHappyPath:
    """Single todo → DB available → fuzzy match miss → insert → synced."""

    def test_single_todo_inserted(self):
        wf = load_workflow(TODO_SYNC_FILE, "todo_sync", {
            "todos": [{"content": "Fix the bug", "status": "pending"}],
            "todo_count": 1,
            "has_todos": True,
            "db_available": True,
            "has_match": False,
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "parse_input" in names
        assert "connect_db" in names
        assert "init_loop" in names
        assert "fuzzy_match" in names
        assert "insert_new" in names
        assert "commit_changes" in names
        assert "end_synced" in names
        assert "update_existing" not in names
        assert wf.data.get("sync_complete") is True
        assert wf.data.get("inserted_count") == 1
        assert wf.data.get("updated_count") == 0


class TestTodoSyncEmpty:
    """No todos → end_empty."""

    def test_empty_todos(self):
        wf = load_workflow(TODO_SYNC_FILE, "todo_sync", {
            "todos": [],
            "todo_count": 0,
            "has_todos": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_empty" in names
        assert "connect_db" not in names


class TestTodoSyncDBUnavailable:
    """Todos exist but DB is down → end_no_db."""

    def test_db_down(self):
        wf = load_workflow(TODO_SYNC_FILE, "todo_sync", {
            "todos": [{"content": "Test"}],
            "todo_count": 1,
            "has_todos": True,
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "connect_db" in names
        assert "end_no_db" in names
        assert "init_loop" not in names


class TestTodoSyncFuzzyMatch:
    """Existing todo found → update (not insert)."""

    def test_fuzzy_match_updates(self):
        wf = load_workflow(TODO_SYNC_FILE, "todo_sync", {
            "todos": [{"content": "Fix the bug", "status": "completed"}],
            "todo_count": 1,
            "has_todos": True,
            "db_available": True,
            "has_match": True,
            "is_deleted": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "update_existing" in names
        assert "insert_new" not in names
        assert wf.data.get("updated_count") == 1
        assert wf.data.get("inserted_count") == 0


class TestTodoSyncDeleted:
    """Todo with deleted status → mark_archived."""

    def test_deleted_archived(self):
        wf = load_workflow(TODO_SYNC_FILE, "todo_sync", {
            "todos": [{"content": "Old todo", "status": "deleted"}],
            "todo_count": 1,
            "has_todos": True,
            "db_available": True,
            "has_match": True,
            "is_deleted": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "mark_archived" in names
        assert wf.data.get("archived_count") == 1


class TestTodoSyncMultiTodo:
    """3 todos → process all → synced."""

    def test_three_todos_loop(self):
        wf = load_workflow(TODO_SYNC_FILE, "todo_sync", {
            "todos": [{"content": "A"}, {"content": "B"}, {"content": "C"}],
            "todo_count": 3,
            "has_todos": True,
            "db_available": True,
            "has_match": False,
            "is_deleted": False,
        })

        assert wf.is_completed()
        assert wf.data.get("sync_complete") is True
        assert wf.data.get("inserted_count") == 3
        assert wf.data.get("current_index") == 3


# ===========================================================================
# TASK SYNC TESTS
# ===========================================================================

class TestTaskSyncCreate:
    """TaskCreate → insert todo → no build_task match → map updated."""

    def test_create_no_bt_match(self):
        wf = load_workflow(TASK_SYNC_FILE, "task_sync", {
            "operation": "create",
            "is_create": True,
            "has_build_task_match": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "insert_todo" in names
        assert "check_build_task_match" in names
        assert "update_task_map" in names
        assert "link_build_task" not in names
        assert "lookup_task_map" not in names
        assert wf.data.get("map_updated") is True


class TestTaskSyncCreateWithBTMatch:
    """TaskCreate → insert → matched build_task → linked."""

    def test_create_with_bt_match(self):
        wf = load_workflow(TASK_SYNC_FILE, "task_sync", {
            "operation": "create",
            "is_create": True,
            "has_build_task_match": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "insert_todo" in names
        assert "link_build_task" in names
        assert wf.data.get("build_task_linked") is True


class TestTaskSyncUpdateNotCompleted:
    """TaskUpdate → lookup → update status → not completed → end."""

    def test_update_not_completed(self):
        wf = load_workflow(TASK_SYNC_FILE, "task_sync", {
            "operation": "update",
            "is_create": False,
            "task_found_in_map": True,
            "is_completed": False,
            "has_linked_build_task": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "lookup_task_map" in names
        assert "update_todo_status" in names
        assert "update_task_map" in names
        assert "advance_build_task" not in names
        assert "insert_todo" not in names


class TestTaskSyncUpdateCompletedLinked:
    """TaskUpdate completed + linked → advance build_task → check siblings."""

    def test_update_completed_linked(self):
        wf = load_workflow(TASK_SYNC_FILE, "task_sync", {
            "operation": "update",
            "is_create": False,
            "task_found_in_map": True,
            "is_completed": True,
            "has_linked_build_task": True,
            "all_siblings_done": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "advance_build_task" in names
        assert "check_sibling_tasks" in names
        assert "surface_feature_completion" not in names
        assert wf.data.get("build_task_advanced") is True


class TestTaskSyncAllSiblingsDone:
    """All sibling tasks done → surface feature completion."""

    def test_feature_completion_surfaced(self):
        wf = load_workflow(TASK_SYNC_FILE, "task_sync", {
            "operation": "update",
            "is_create": False,
            "task_found_in_map": True,
            "is_completed": True,
            "has_linked_build_task": True,
            "all_siblings_done": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "surface_feature_completion" in names
        assert wf.data.get("feature_completion_surfaced") is True
