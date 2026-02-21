"""
Tests for the Working Memory BPMN process.

Session facts are Claude's persistent scratchpad - key-value pairs that survive
context compaction and can be recalled across sessions.

Paths tested:
  1. Store normal fact: identify(store) → classify(not sensitive) → store_normal → end
  2. Store sensitive fact: identify(store) → classify(sensitive) → store_sensitive → end
  3. Recall found: identify(recall) → recall_fact(found) → apply_fact → end
  4. Recall not found: identify(recall) → recall_fact(not found) → fact_missing → end
  5. Compaction survival: identify(compaction) → precompact → query → build → post_compact_recovery → end
  6. Cross-session recall: identify(cross_session) → recall_previous → merge_with_current → end

Key notes:
  - action_gw default (no condition) routes to classify_fact (store path)
  - action == "recall" → recall_fact (scriptTask)
  - action == "compaction" → precompact_fires (scriptTask)
  - action == "cross_session" → recall_previous (scriptTask)
  - sensitive_gw: is_sensitive == True → store_sensitive, default → store_normal
  - found_gw: fact_found == False → fact_missing, default → apply_fact
  - All paths converge at end_merge → end

Implementation: mcp-servers/project-tools/server_v2.py, scripts/precompact_hook.py
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "working_memory.bpmn")
)
PROCESS_ID = "working_memory"


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


def get_ready_user_tasks(wf: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return wf.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(wf: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(wf)]


def complete_user_task(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """Find named READY user task, merge data, run it, advance engine."""
    ready = get_ready_user_tasks(wf)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    wf.do_engine_steps()


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Store Normal Fact
# ---------------------------------------------------------------------------

class TestStoreNormalFact:
    """
    Store path, non-sensitive:
    identify(store) → classify_fact(not sensitive) → store_normal → end_merge → end.
    """

    def test_store_normal_fact(self):
        wf = load_workflow()

        # identify_action is the first userTask
        assert "identify_action" in ready_task_names(wf)

        # action="store" routes to the store path (default gateway branch)
        complete_user_task(wf, "identify_action", {"action": "store"})

        # classify_fact is a userTask
        assert "classify_fact" in ready_task_names(wf)
        complete_user_task(wf, "classify_fact", {"is_sensitive": False})

        # store_normal is a scriptTask (auto-runs) → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "classify_fact" in names
        assert "store_normal" in names
        assert "store_sensitive" not in names
        assert "end" in names

        assert wf.data.get("stored") is True
        assert wf.data.get("is_sensitive") is False


# ---------------------------------------------------------------------------
# Test 2: Store Sensitive Fact
# ---------------------------------------------------------------------------

class TestStoreSensitiveFact:
    """
    Store path, sensitive:
    identify(store) → classify_fact(sensitive=True) → store_sensitive → end_merge → end.
    """

    def test_store_sensitive_fact(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "store"})
        complete_user_task(wf, "classify_fact", {"is_sensitive": True})

        # store_sensitive is a scriptTask (auto-runs) → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "store_sensitive" in names
        assert "store_normal" not in names

        assert wf.data.get("stored") is True
        assert wf.data.get("is_sensitive") is True


# ---------------------------------------------------------------------------
# Test 3: Recall - Fact Found
# ---------------------------------------------------------------------------

class TestRecallFactFound:
    """
    Recall path, found:
    identify(recall) → recall_fact (script, fact_found=True) → apply_fact → end.

    fact_found defaults to True in the script try/except.
    """

    def test_recall_fact_found(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "recall"})

        # recall_fact is a scriptTask (auto-runs, fact_found defaults True)
        # apply_fact is a userTask
        assert "apply_fact" in ready_task_names(wf), (
            f"Expected apply_fact when fact_found=True. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "apply_fact", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "recall_fact" in names
        assert "apply_fact" in names
        assert "fact_missing" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Test 4: Recall - Fact Not Found
# ---------------------------------------------------------------------------

class TestRecallFactNotFound:
    """
    Recall path, not found:
    identify(recall) → recall_fact (script, fact_found=False) → fact_missing → end.

    We inject fact_found=False via initial_data since it's set by the scriptTask.
    """

    def test_recall_fact_not_found(self):
        wf = load_workflow(initial_data={"fact_found": False})

        complete_user_task(wf, "identify_action", {"action": "recall"})

        # recall_fact runs (reads fact_found=False from data) → fact_missing (userTask)
        assert "fact_missing" in ready_task_names(wf), (
            f"Expected fact_missing when fact_found=False. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "fact_missing", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "recall_fact" in names
        assert "fact_missing" in names
        assert "apply_fact" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Test 5: Compaction Survival
# ---------------------------------------------------------------------------

class TestCompactionSurvival:
    """
    Compaction path:
    identify(compaction) → precompact_fires (script) → query_facts_for_injection (script)
    → build_system_message (script) → post_compact_recovery (userTask) → end.
    """

    def test_compaction_path(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "compaction"})

        # precompact_fires, query_facts_for_injection, build_system_message are all scriptTasks
        # post_compact_recovery is a userTask
        assert "post_compact_recovery" in ready_task_names(wf), (
            f"Expected post_compact_recovery after compaction scripts. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "post_compact_recovery", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "precompact_fires" in names
        assert "query_facts_for_injection" in names
        assert "build_system_message" in names
        assert "post_compact_recovery" in names
        assert "end" in names

        assert wf.data.get("precompact_triggered") is True
        assert wf.data.get("facts_queried") is True
        assert wf.data.get("message_built") is True


# ---------------------------------------------------------------------------
# Test 6: Cross-Session Recall
# ---------------------------------------------------------------------------

class TestCrossSessionRecall:
    """
    Cross-session path:
    identify(cross_session) → recall_previous (script) → merge_with_current (userTask) → end.
    """

    def test_cross_session_recall(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "cross_session"})

        # recall_previous is a scriptTask → merge_with_current is a userTask
        assert "merge_with_current" in ready_task_names(wf), (
            f"Expected merge_with_current after recall_previous. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "merge_with_current", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "recall_previous" in names
        assert "merge_with_current" in names
        assert "end" in names

        # recall_previous sets previous_facts to [] by default
        assert "previous_facts" in wf.data


# ---------------------------------------------------------------------------
# Test 7: Store Path - Script Data Flags
# ---------------------------------------------------------------------------

class TestStorePathDataIntegrity:
    """Both store branches set stored=True and the correct is_sensitive value."""

    def test_store_normal_sets_flags(self):
        wf = load_workflow()
        complete_user_task(wf, "identify_action", {"action": "store"})
        complete_user_task(wf, "classify_fact", {"is_sensitive": False})
        assert wf.is_completed()
        assert wf.data.get("stored") is True
        assert wf.data.get("is_sensitive") is False

    def test_store_sensitive_sets_flags(self):
        wf = load_workflow()
        complete_user_task(wf, "identify_action", {"action": "store"})
        complete_user_task(wf, "classify_fact", {"is_sensitive": True})
        assert wf.is_completed()
        assert wf.data.get("stored") is True
        assert wf.data.get("is_sensitive") is True
