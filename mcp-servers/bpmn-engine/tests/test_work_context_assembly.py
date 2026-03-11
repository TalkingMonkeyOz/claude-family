"""
Tests for the Work Context Assembly (WCC) BPMN process.

Uses SpiffWorkflow 3.x API against work_context_assembly.bpmn.
No external database or network required - all assertions on task.data.

Process overview:
  start_event
    -> detect_activity [userTask]
    -> activity_detected_gw
         [activity_detected == True] -> activity_changed_gw
         [default]                   -> end_no_activity

  activity_changed_gw:
    [activity_changed == True] -> parallel_start (6 sources) -> parallel_join
                                -> budget_cap_rank -> cache_wcc -> inject_merge_gw -> inject_wcc -> end_wcc_injected
    [default]                  -> cache_valid_gw
                                    [cache_valid == True] -> load_cached_wcc -> inject_merge_gw -> inject_wcc -> end_wcc_injected
                                    [default]             -> parallel_start (6 sources) -> ... -> end_wcc_injected
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "work_context_assembly.bpmn")
)
PROCESS_ID = "work_context_assembly"


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
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
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


class TestNoActivityDetected:
    """No activity detected -> end_no_activity (normal RAG fallback)."""

    def test_no_activity_path(self):
        wf = load_workflow()
        complete_user_task(wf, "detect_activity", {
            "activity_detected": False,
            "activity_changed": False,
            "cache_valid": False,
        })
        completed = completed_spec_names(wf)
        assert "end_no_activity" in completed
        assert "parallel_start" not in completed
        assert wf.is_completed()


class TestActivityChangedFullAssembly:
    """Activity changed -> parallel assembly of 6 sources -> cache -> inject."""

    def test_activity_changed_assembly(self):
        wf = load_workflow()
        complete_user_task(wf, "detect_activity", {
            "activity_detected": True,
            "activity_changed": True,
            "cache_valid": False,
        })
        completed = completed_spec_names(wf)

        # All 6 sources should have been queried
        assert "query_workfiles" in completed
        assert "query_knowledge" in completed
        assert "query_features" in completed
        assert "query_session_facts" in completed
        assert "query_vault_rag" in completed
        assert "query_skills_bpmn" in completed

        # Budget cap, cache, and inject should complete
        assert "budget_cap_rank" in completed
        assert "cache_wcc" in completed
        assert "inject_wcc" in completed
        assert "end_wcc_injected" in completed

        assert wf.is_completed()
        assert wf.data.get("wcc_injected") is True
        assert wf.data.get("wcc_source") == "assembled"


class TestActivityUnchangedCacheHit:
    """Activity unchanged + valid cache -> load cached WCC -> inject."""

    def test_cache_hit_path(self):
        wf = load_workflow()
        complete_user_task(wf, "detect_activity", {
            "activity_detected": True,
            "activity_changed": False,
            "cache_valid": True,
        })
        completed = completed_spec_names(wf)

        # Should load from cache, NOT run parallel assembly
        assert "load_cached_wcc" in completed
        assert "inject_wcc" in completed
        assert "end_wcc_injected" in completed

        # Parallel sources should NOT have been queried
        assert "query_workfiles" not in completed
        assert "query_knowledge" not in completed

        assert wf.is_completed()
        assert wf.data.get("wcc_source") == "cache"


class TestActivityUnchangedCacheMiss:
    """Activity unchanged but cache invalid -> full assembly."""

    def test_cache_miss_triggers_assembly(self):
        wf = load_workflow()
        complete_user_task(wf, "detect_activity", {
            "activity_detected": True,
            "activity_changed": False,
            "cache_valid": False,
        })
        completed = completed_spec_names(wf)

        # Cache miss should trigger parallel assembly
        assert "query_workfiles" in completed
        assert "query_knowledge" in completed
        assert "budget_cap_rank" in completed
        assert "cache_wcc" in completed
        assert "inject_wcc" in completed
        assert "end_wcc_injected" in completed

        assert wf.is_completed()
        assert wf.data.get("wcc_source") == "assembled"


class TestBPMNParsesClean:
    """Verify the BPMN file parses without errors."""

    def test_parse(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        assert spec is not None
        assert spec.name == "work_context_assembly"
