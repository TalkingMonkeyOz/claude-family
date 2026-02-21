"""
Tests for the Process Governance BPMN process.

The meta-process that governs how Claude discovers BPMN models and follows them.
Covers both the system-change path (BPMN-first mandatory) and regular work path
(BPMN guidance optional).

Paths tested:
  1. System change, model exists, tests pass:
       classify(system) → rule → search(found) → load → identify_gap → update_bpmn
       → validate(pass) → implement → check_alignment → commit → end
  2. System change, no model, tests pass:
       classify(system) → rule → search(not found) → create_bpmn
       → validate(pass) → implement → alignment → commit → end
  3. System change, tests fail then pass:
       classify(system) → rule → search(not found) → create_bpmn
       → validate(fail) → fix_model → validate(pass) → implement → alignment → commit → end
  4. Regular work, process found:
       classify(regular) → search(found) → get_current_step(not done) → execute_step
       → get_current_step(done) → end
  5. Regular work, no process:
       classify(regular) → search(not found) → proceed_without_bpmn → end

Key notes:
  - classify_task sets is_system_change; task_type_gw: is_system_change == True → rule_fires
  - rule_fires is a scriptTask (auto-runs when is_system_change=True)
  - search_existing_models is a scriptTask; model_found controls model_exists_gw
  - model_exists_gw: model_found == True → load_current_model; default → create_bpmn
  - validate_model is a scriptTask; tests_pass controls tests_pass_gw
  - tests_pass_gw: tests_pass == False → fix_model; default → implement_code
  - search_for_process is a scriptTask; process_found controls process_found_gw
  - process_found_gw: process_found == True → get_current_step; default → proceed_without_bpmn
  - process_done_gw: is_completed == True → end_merge; default → execute_step (loop)
  - identify_gap, update_bpmn, implement_code, commit_together, fix_model are userTasks
  - execute_step and proceed_without_bpmn are userTasks

Implementation: .claude/rules/system-change-process.md, mcp-servers/bpmn-engine/server.py,
               scripts/task_discipline_hook.py
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "development", "process_governance.bpmn")
)
PROCESS_ID = "process_governance"


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
# Test 1: System Change, Model Exists, Tests Pass
# ---------------------------------------------------------------------------

class TestSystemChangeModelExistsTestsPass:
    """
    classify(system) → rule_fires (script) → search(model_found=True) → load_current_model (script)
    → identify_gap (userTask) → update_bpmn (userTask) → validate_merge → validate_model (script, pass)
    → implement_code (userTask) → check_alignment (script) → commit_together (userTask) → end.
    """

    def test_system_change_model_exists_tests_pass(self):
        wf = load_workflow(initial_data={"model_found": True, "tests_pass": True})

        # classify_task is the first userTask
        assert "classify_task" in ready_task_names(wf)
        complete_user_task(wf, "classify_task", {"is_system_change": True})

        # rule_fires (script) → search_existing_models (script, model_found=True)
        # → load_current_model (script) → identify_gap (userTask)
        assert "identify_gap" in ready_task_names(wf), (
            f"Expected identify_gap when model exists. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "identify_gap", {})

        # update_bpmn is a userTask
        assert "update_bpmn" in ready_task_names(wf)
        complete_user_task(wf, "update_bpmn", {})

        # validate_model (script, tests_pass=True) → implement_code (userTask)
        assert "implement_code" in ready_task_names(wf), (
            f"Expected implement_code after validate passes. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "implement_code", {})

        # check_alignment (script) → commit_together (userTask)
        assert "commit_together" in ready_task_names(wf)
        complete_user_task(wf, "commit_together", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "rule_fires" in names
        assert "search_existing_models" in names
        assert "load_current_model" in names
        assert "identify_gap" in names
        assert "update_bpmn" in names
        assert "validate_model" in names
        assert "implement_code" in names
        assert "check_alignment" in names
        assert "commit_together" in names
        assert "end" in names

        # Create path must not appear
        assert "create_bpmn" not in names
        # Fix loop must not appear
        assert "fix_model" not in names
        # Regular work path must not appear
        assert "search_for_process" not in names


# ---------------------------------------------------------------------------
# Test 2: System Change, No Model, Tests Pass
# ---------------------------------------------------------------------------

class TestSystemChangeNoModelTestsPass:
    """
    classify(system) → rule (script) → search(model_found=False) → create_bpmn (userTask)
    → validate_merge → validate(pass) → implement (userTask) → alignment (script)
    → commit (userTask) → end.
    """

    def test_system_change_no_model_tests_pass(self):
        wf = load_workflow(initial_data={"model_found": False, "tests_pass": True})

        complete_user_task(wf, "classify_task", {"is_system_change": True})

        # search_existing_models (script, model_found=False) → create_bpmn (userTask)
        assert "create_bpmn" in ready_task_names(wf), (
            f"Expected create_bpmn when model not found. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "create_bpmn", {})

        # validate_model (script, pass) → implement_code (userTask)
        assert "implement_code" in ready_task_names(wf)
        complete_user_task(wf, "implement_code", {})

        assert "commit_together" in ready_task_names(wf)
        complete_user_task(wf, "commit_together", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "create_bpmn" in names
        assert "validate_model" in names
        assert "implement_code" in names
        assert "commit_together" in names

        # Update-model path must not appear
        assert "load_current_model" not in names
        assert "identify_gap" not in names
        assert "update_bpmn" not in names
        assert "fix_model" not in names


# ---------------------------------------------------------------------------
# Test 3: System Change, Tests Fail Then Pass
# ---------------------------------------------------------------------------

class TestSystemChangeTestsFailThenPass:
    """
    classify(system) → rule → search(not found) → create_bpmn → validate(fail)
    → fix_model → validate(pass) → implement → alignment → commit → end.

    Second call to validate_model must use tests_pass=True.
    """

    def test_system_change_tests_fail_then_pass(self):
        # First validate will fail (tests_pass=False in initial data)
        wf = load_workflow(initial_data={"model_found": False, "tests_pass": False})

        complete_user_task(wf, "classify_task", {"is_system_change": True})

        complete_user_task(wf, "create_bpmn", {})

        # validate_model (script, tests_pass=False) → fix_model (userTask)
        assert "fix_model" in ready_task_names(wf), (
            f"Expected fix_model when tests fail. Got: {ready_task_names(wf)}"
        )

        # Fix the model - inject tests_pass=True so next validate passes
        complete_user_task(wf, "fix_model", {"tests_pass": True})

        # validate_model runs again (tests_pass=True now) → implement_code
        assert "implement_code" in ready_task_names(wf), (
            f"Expected implement_code after fix. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "implement_code", {})

        complete_user_task(wf, "commit_together", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "create_bpmn" in names
        assert "fix_model" in names
        assert "implement_code" in names
        assert "commit_together" in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Test 4: Regular Work, Process Found
# ---------------------------------------------------------------------------

class TestRegularWorkProcessFound:
    """
    classify(regular) → search_for_process(found) → get_current_step(not done)
    → execute_step → get_current_step(done) → end_merge → end.
    """

    def test_regular_work_process_found_and_followed(self):
        wf = load_workflow(initial_data={"process_found": True, "is_completed": False})

        complete_user_task(wf, "classify_task", {"is_system_change": False})

        # search_for_process (script, process_found=True) → get_current_step (script, is_completed=False)
        # → process_done_gw(not done) → execute_step (userTask)
        assert "execute_step" in ready_task_names(wf), (
            f"Expected execute_step when process found and not done. Got: {ready_task_names(wf)}"
        )

        # Execute step, mark process completed on next iteration
        complete_user_task(wf, "execute_step", {"is_completed": True})

        # get_current_step runs again (is_completed=True) → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "search_for_process" in names
        assert "get_current_step" in names
        assert "execute_step" in names
        assert "end" in names

        # System change steps must not appear
        assert "rule_fires" not in names
        assert "create_bpmn" not in names
        assert "proceed_without_bpmn" not in names


# ---------------------------------------------------------------------------
# Test 5: Regular Work, No Process Found
# ---------------------------------------------------------------------------

class TestRegularWorkNoProcess:
    """
    classify(regular) → search_for_process(not found) → proceed_without_bpmn (userTask) → end.
    """

    def test_regular_work_no_process(self):
        wf = load_workflow(initial_data={"process_found": False})

        complete_user_task(wf, "classify_task", {"is_system_change": False})

        # search_for_process (script, process_found=False) → proceed_without_bpmn (userTask)
        assert "proceed_without_bpmn" in ready_task_names(wf), (
            f"Expected proceed_without_bpmn when no process found. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "proceed_without_bpmn", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "search_for_process" in names
        assert "proceed_without_bpmn" in names
        assert "end" in names

        assert "get_current_step" not in names
        assert "execute_step" not in names
        assert "rule_fires" not in names


# ---------------------------------------------------------------------------
# Test 6: System Change Path Does Not Use Regular Work Steps
# ---------------------------------------------------------------------------

class TestSystemChangeDoesNotUseRegularWorkPath:
    """
    Confirm that taking the system change path never activates search_for_process
    or proceed_without_bpmn (those belong to the regular work path).
    """

    def test_system_change_excludes_regular_work_steps(self):
        wf = load_workflow(initial_data={"model_found": True, "tests_pass": True})

        complete_user_task(wf, "classify_task", {"is_system_change": True})
        complete_user_task(wf, "identify_gap", {})
        complete_user_task(wf, "update_bpmn", {})
        complete_user_task(wf, "implement_code", {})
        complete_user_task(wf, "commit_together", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "search_for_process" not in names
        assert "proceed_without_bpmn" not in names
        assert "execute_step" not in names


# ---------------------------------------------------------------------------
# Test 7: Multiple Step Loop Before Completion
# ---------------------------------------------------------------------------

class TestRegularWorkMultipleSteps:
    """
    Regular work with two execute_step iterations before is_completed=True.
    Proves the get_current_step → execute_step loop works multiple times.
    """

    def test_multiple_steps_before_completion(self):
        wf = load_workflow(initial_data={"process_found": True, "is_completed": False})

        complete_user_task(wf, "classify_task", {"is_system_change": False})

        # Step 1: not done yet
        assert "execute_step" in ready_task_names(wf)
        complete_user_task(wf, "execute_step", {"is_completed": False})

        # Step 2: still not done (loop back)
        assert not wf.is_completed()
        assert "execute_step" in ready_task_names(wf), (
            f"Expected execute_step loop. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "execute_step", {"is_completed": True})

        # Now done
        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "execute_step" in names
        assert "end" in names
