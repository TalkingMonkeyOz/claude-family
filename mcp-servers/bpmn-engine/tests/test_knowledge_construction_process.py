"""Tests for the Knowledge Construction Process BPMN.

Validates the 5 construction rules + 2 safeguards from storage-rules v8:
  Rule 1 Shape parity        — `summary_populated` + `shape_parity_ok`
  Rule 2 Hierarchy required  — `parent_assigned`
  Rule 3 MOC fulfilment      — `is_moc` + `moc_children_tracked`
  Rule 4 Specific edge types — `edge_specific` (operator decision, not gated)
  Rule 5 Change → memory     — `is_system_change` + `change_remembered`
  Rule 6 Non-destructive     — `destructive`
  Rule 7 Tool-discovery      — `tool_discovered`

Each test exercises one path through the process. The "happy path" walks the
full chain to `end_done`. Each rule violation shunts to a `BLOCKED:` end event.
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
        "knowledge_construction_process.bpmn",
    )
)
PROCESS_ID = "knowledge_construction_process"


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
    end_tasks = [t for t in completed if t.task_spec.bpmn_name and "BLOCKED" in (t.task_spec.bpmn_name or "")]
    if end_tasks:
        return end_tasks[-1].task_spec.bpmn_name
    end_tasks = [t for t in completed if t.task_spec.bpmn_name == "Knowledge Construction Complete"]
    if end_tasks:
        return "Knowledge Construction Complete"
    return ""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_happy_path_non_moc_non_system_change():
    """Knowledge write that satisfies all rules and is not MOC, not system change."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": True})
    complete_user_task(wf, "choose_edge_type", {"edge_specific": True, "is_moc": False})
    complete_user_task(wf, "verify_shape_parity", {"shape_parity_ok": True, "is_system_change": False})
    assert wf.is_completed()
    assert end_event_name(wf) == "Knowledge Construction Complete"


def test_happy_path_moc_article_with_tracked_children():
    """Article that IS an MOC and has all promised children either as articles or tracked tasks."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "article", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": True})
    complete_user_task(wf, "choose_edge_type", {"edge_specific": True, "is_moc": True})
    complete_user_task(wf, "register_moc_children", {"moc_children_tracked": True})
    complete_user_task(wf, "verify_shape_parity", {"shape_parity_ok": True, "is_system_change": False})
    assert wf.is_completed()
    assert end_event_name(wf) == "Knowledge Construction Complete"


def test_happy_path_system_change_remembered():
    """System change that gets remember()'d before commit."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": True})
    complete_user_task(wf, "choose_edge_type", {"edge_specific": True, "is_moc": False})
    complete_user_task(wf, "verify_shape_parity", {"shape_parity_ok": True, "is_system_change": True})
    complete_user_task(wf, "record_change_memory", {"change_remembered": True})
    assert wf.is_completed()
    assert end_event_name(wf) == "Knowledge Construction Complete"


# ---------------------------------------------------------------------------
# Rule violation paths — must hit a BLOCKED end event
# ---------------------------------------------------------------------------


def test_rule6_destructive_change_blocked():
    """Rule 6: a destructive change (DROP/RENAME/NOT NULL without default) is blocked early."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": True})
    assert wf.is_completed()
    assert "BLOCKED: Destructive Change" in end_event_name(wf)


def test_rule2_no_parent_blocked():
    """Rule 2: missing hierarchy → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": False})
    assert wf.is_completed()
    assert "BLOCKED: Hierarchy Missing" in end_event_name(wf)


def test_rule1_no_summary_blocked():
    """Rule 1: missing summary → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": False})
    assert wf.is_completed()
    assert "BLOCKED: Summary Missing" in end_event_name(wf)


def test_rule3_moc_unfulfilled_blocked():
    """Rule 3: MOC article with unfulfilled child promises → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "article", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": True})
    complete_user_task(wf, "choose_edge_type", {"edge_specific": True, "is_moc": True})
    complete_user_task(wf, "register_moc_children", {"moc_children_tracked": False})
    assert wf.is_completed()
    assert "BLOCKED: MOC Promise Unfulfilled" in end_event_name(wf)


def test_rule1_shape_drift_blocked():
    """Rule 1: detected shape drift across atomic stores → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": True})
    complete_user_task(wf, "choose_edge_type", {"edge_specific": True, "is_moc": False})
    complete_user_task(wf, "verify_shape_parity", {"shape_parity_ok": False, "is_system_change": False})
    assert wf.is_completed()
    assert "BLOCKED: Shape Drift Detected" in end_event_name(wf)


def test_rule5_system_change_not_remembered_blocked():
    """Rule 5: system change without memory record → blocked."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": True})
    complete_user_task(wf, "determine_target_store", {"target_store": "knowledge", "destructive": False})
    complete_user_task(wf, "assign_parent", {"parent_assigned": True})
    complete_user_task(wf, "populate_summary", {"summary_populated": True})
    complete_user_task(wf, "choose_edge_type", {"edge_specific": True, "is_moc": False})
    complete_user_task(wf, "verify_shape_parity", {"shape_parity_ok": True, "is_system_change": True})
    complete_user_task(wf, "record_change_memory", {"change_remembered": False})
    assert wf.is_completed()
    assert "BLOCKED: System Change Not Remembered" in end_event_name(wf)


def test_rule7_tool_unknown_takes_gap_path_then_continues():
    """Rule 7: tool not discovered → gap-filing path, then process continues."""
    wf = load_workflow()
    complete_user_task(wf, "check_tool_discovery", {"tool_discovered": False})
    # The gap-filing user task should now be ready
    ready_names = [t.task_spec.name for t in get_ready_user_tasks(wf)]
    assert "file_discovery_gap" in ready_names, (
        f"Expected file_discovery_gap to be READY after tool_discovered=False; got {ready_names}"
    )
    complete_user_task(wf, "file_discovery_gap", {})
    # Process should now be at determine_target_store
    ready_names = [t.task_spec.name for t in get_ready_user_tasks(wf)]
    assert "determine_target_store" in ready_names
