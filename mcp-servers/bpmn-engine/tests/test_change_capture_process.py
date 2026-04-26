"""Tests for the Change Capture Process BPMN.

Validates Rule 7 (Memory-Update Discipline) from storage-rules v8.

Paths:
  - happy: system file → remember() → traceability → commit
  - skipped: non-system file (e.g. README.md edit)
  - blocked: system change not recorded in memory
  - blocked: memory recorded but no FB/F/BT/commit traceability
  - in-progress: memory + traceability done, no commit yet (valid state)
"""
import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "processes",
        "development",
        "change_capture_process.bpmn",
    )
)
PROCESS_ID = "change_capture_process"


def load_workflow() -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"User task '{task_name}' is not READY. Ready tasks: "
        f"{[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def end_event_name(workflow: BpmnWorkflow) -> str:
    completed = workflow.get_tasks(state=TaskState.COMPLETED)
    end_tasks = [t for t in completed if t.task_spec.bpmn_name and (
        "BLOCKED" in t.task_spec.bpmn_name
        or "Skipped" in t.task_spec.bpmn_name
        or "Memory Recorded" in t.task_spec.bpmn_name
        or "Change Captured" in t.task_spec.bpmn_name
    )]
    return end_tasks[-1].task_spec.bpmn_name if end_tasks else ""


def test_skipped_non_system_file():
    """Editing README.md / other non-system files exits early."""
    wf = load_workflow()
    complete_user_task(wf, "classify_file", {"is_system_change_file": False})
    assert wf.is_completed()
    assert "Skipped" in end_event_name(wf)


def test_happy_path_system_change_committed():
    """Edit a hook file → remember() → cite FB → commit."""
    wf = load_workflow()
    complete_user_task(wf, "classify_file", {"is_system_change_file": True})
    complete_user_task(wf, "record_change_memory", {"change_memory_recorded": True})
    complete_user_task(wf, "check_traceability", {"has_traceability": True, "commit_attempt": True})
    assert wf.is_completed()
    assert "Change Captured + Committed" in end_event_name(wf)


def test_in_progress_memory_no_commit_yet():
    """Memory recorded, traceability cited, but commit not yet attempted — valid in-progress state."""
    wf = load_workflow()
    complete_user_task(wf, "classify_file", {"is_system_change_file": True})
    complete_user_task(wf, "record_change_memory", {"change_memory_recorded": True})
    complete_user_task(wf, "check_traceability", {"has_traceability": True, "commit_attempt": False})
    assert wf.is_completed()
    assert "Memory Recorded" in end_event_name(wf)


def test_blocked_change_not_remembered():
    """System change but no remember() call → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "classify_file", {"is_system_change_file": True})
    complete_user_task(wf, "record_change_memory", {"change_memory_recorded": False})
    assert wf.is_completed()
    assert "BLOCKED: Change Not Remembered" in end_event_name(wf)


def test_blocked_no_traceability():
    """remember() called but no FB/F/BT/commit citation → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "classify_file", {"is_system_change_file": True})
    complete_user_task(wf, "record_change_memory", {"change_memory_recorded": True})
    complete_user_task(wf, "check_traceability", {"has_traceability": False, "commit_attempt": True})
    assert wf.is_completed()
    assert "BLOCKED: No Traceability" in end_event_name(wf)
