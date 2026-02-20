"""
Tests for the Agent Lifecycle BPMN process.

Uses SpiffWorkflow 3.x API directly against the agent_lifecycle.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Process flow summary:
  start_event -> assess_task (user) -> delegation_gateway
    [delegation=="delegate"] -> spawn_agent (script, agent_spawned=True)
                             -> monitor_agent (user, sets agent_result)
                             -> agent_result_gateway
                                 [agent_result=="failure"] -> adjust_and_retry (user)
                                                           -> spawn_agent (loop back)
                                 [default/success]         -> collect_results (script, results_collected=True)
                                                           -> direct_merge
    [default/direct]         -> execute_directly (user) -> direct_merge

  direct_merge -> review_gateway
    [needs_review==True] -> spawn_reviewer (script, review_spawned=True)
                         -> process_review (user) -> end_reviewed
    [default/skip]       -> end_complete
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "agent_lifecycle.bpmn")
)
PROCESS_ID = "agent_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past the start event; first stop is assess_task (user task)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through any subsequent automated
    tasks (script tasks, gateways) until the next user task or end event.

    Raises AssertionError if the task is not currently READY.
    """
    ready = get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_names(workflow: BpmnWorkflow) -> set:
    """Return the spec names of all COMPLETED tasks in the workflow as a set."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDirectExecution:
    """
    Claude evaluates the task as simple and executes it directly.
    No agent spawn, no review needed.

    Flow:
        start_event -> assess_task [delegation="direct", needs_review=False]
        -> delegation_gateway [default/direct]
        -> execute_directly
        -> direct_merge -> review_gateway [default/skip]
        -> end_complete

    Assertions:
      - end_complete reached
      - end_reviewed NOT reached
      - agent_spawned NOT set in workflow.data
      - execute_directly completed
    """

    def test_direct_execution_no_review(self):
        workflow = load_workflow()

        # assess_task: direct execution, no review needed
        # Both delegation and needs_review must be set here so all gateway
        # condition variables exist in task.data before any gateway evaluates.
        complete_user_task(workflow, "assess_task", {
            "delegation": "direct",
            "needs_review": False,
        })

        # Engine takes the direct default path; execute_directly is a user task
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "execute_directly" in ready_names, (
            f"execute_directly should be READY after direct delegation. Got: {ready_names}"
        )

        complete_user_task(workflow, "execute_directly", {})

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_names(workflow)
        assert "execute_directly" in names, "execute_directly must have been completed"
        assert "end_complete" in names, "end_complete must be reached"
        assert "end_reviewed" not in names, "end_reviewed must NOT be reached on skip-review path"
        assert "spawn_agent" not in names, "spawn_agent must NOT run on direct path"
        assert "collect_results" not in names, "collect_results must NOT run on direct path"
        assert "spawn_reviewer" not in names, "spawn_reviewer must NOT run when needs_review=False"

        # agent_spawned is only set by the spawn_agent script task; must be absent
        assert "agent_spawned" not in workflow.data, (
            "agent_spawned must not exist in workflow.data on the direct path"
        )


class TestAgentSuccess:
    """
    Claude delegates to an agent; the agent succeeds on the first attempt.
    No review needed.

    Flow:
        start_event -> assess_task [delegation="delegate", needs_review=False]
        -> delegation_gateway [flow_delegate]
        -> spawn_agent (script, agent_spawned=True)
        -> monitor_agent [agent_result="success"]
        -> agent_result_gateway [default/success]
        -> collect_results (script, results_collected=True)
        -> direct_merge -> review_gateway [default/skip]
        -> end_complete

    Assertions:
      - spawn_agent, collect_results completed
      - adjust_and_retry NOT completed
      - results_collected == True
      - end_complete reached
    """

    def test_agent_success_no_review(self):
        workflow = load_workflow()

        # assess_task: delegate, no review
        complete_user_task(workflow, "assess_task", {
            "delegation": "delegate",
            "needs_review": False,
        })

        # spawn_agent is a script task (runs automatically); engine stops at monitor_agent
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "monitor_agent" in ready_names, (
            f"monitor_agent should be READY after spawn_agent. Got: {ready_names}"
        )

        # Verify spawn_agent ran and set its flag
        names = completed_names(workflow)
        assert "spawn_agent" in names, "spawn_agent script must have run before monitor_agent"

        # monitor_agent: report success
        complete_user_task(workflow, "monitor_agent", {"agent_result": "success"})

        assert workflow.is_completed(), "Workflow should be completed after agent success"

        names = completed_names(workflow)
        assert "spawn_agent" in names, "spawn_agent must have completed"
        assert "monitor_agent" in names, "monitor_agent must have completed"
        assert "collect_results" in names, "collect_results script must have run on success path"
        assert "adjust_and_retry" not in names, "adjust_and_retry must NOT run on success path"
        assert "execute_directly" not in names, "execute_directly must NOT run on delegate path"
        assert "end_complete" in names, "end_complete must be reached"
        assert "end_reviewed" not in names, "end_reviewed must NOT be reached"

        assert workflow.data.get("agent_spawned") is True, (
            "spawn_agent should have set agent_spawned=True"
        )
        assert workflow.data.get("results_collected") is True, (
            "collect_results should have set results_collected=True"
        )


class TestAgentRetryThenSuccess:
    """
    Agent fails on the first attempt; Claude adjusts and retries; second attempt succeeds.

    Flow:
        start_event -> assess_task [delegation="delegate", needs_review=False]
        -> delegation_gateway [flow_delegate]
        -> spawn_agent (1st spawn)
        -> monitor_agent [agent_result="failure"]
        -> agent_result_gateway [flow_agent_failure]
        -> adjust_and_retry
        -> spawn_agent (2nd spawn, via flow_retry)
        -> monitor_agent [agent_result="success"]
        -> agent_result_gateway [default/success]
        -> collect_results
        -> direct_merge -> review_gateway [default/skip]
        -> end_complete

    Assertions:
      - adjust_and_retry completed
      - spawn_agent completed (appears at least once - will appear twice in COMPLETED)
      - results_collected == True
      - end_complete reached
    """

    def test_agent_retry_then_success(self):
        workflow = load_workflow()

        # assess_task: delegate, no review
        complete_user_task(workflow, "assess_task", {
            "delegation": "delegate",
            "needs_review": False,
        })

        # Engine stops at monitor_agent (spawn_agent ran automatically)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "monitor_agent" in ready_names, (
            f"monitor_agent should be READY on first pass. Got: {ready_names}"
        )

        # First monitor_agent pass: failure
        complete_user_task(workflow, "monitor_agent", {"agent_result": "failure"})

        # Engine should stop at adjust_and_retry (user task)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "adjust_and_retry" in ready_names, (
            f"adjust_and_retry should be READY after agent failure. Got: {ready_names}"
        )
        assert not workflow.is_completed(), "Workflow must NOT be completed after failure"

        # adjust_and_retry: confirm the retry path
        complete_user_task(workflow, "adjust_and_retry", {})

        # Engine re-runs spawn_agent (script) and stops at monitor_agent again
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "monitor_agent" in ready_names, (
            f"monitor_agent should be READY again after retry. Got: {ready_names}"
        )
        assert not workflow.is_completed(), "Workflow must NOT be completed before second monitor"

        # Second monitor_agent pass: success
        # Override agent_result to "success" so the default (success) branch fires
        complete_user_task(workflow, "monitor_agent", {"agent_result": "success"})

        assert workflow.is_completed(), "Workflow should be completed after retry success"

        names = completed_names(workflow)
        assert "adjust_and_retry" in names, "adjust_and_retry must have been completed"
        assert "collect_results" in names, "collect_results script must have run"
        assert "end_complete" in names, "end_complete must be reached"
        assert "end_reviewed" not in names, "end_reviewed must NOT be reached"

        assert workflow.data.get("agent_spawned") is True, (
            "agent_spawned must be True after retry path"
        )
        assert workflow.data.get("results_collected") is True, (
            "results_collected must be True after successful retry"
        )


class TestWithReviewGate:
    """
    Claude executes directly but needs review. The reviewer is spawned and
    Claude processes the review feedback before completing.

    Flow:
        start_event -> assess_task [delegation="direct", needs_review=True]
        -> delegation_gateway [default/direct]
        -> execute_directly
        -> direct_merge -> review_gateway [flow_needs_review]
        -> spawn_reviewer (script, review_spawned=True)
        -> process_review (user)
        -> end_reviewed

    Assertions:
      - spawn_reviewer, process_review completed
      - end_reviewed reached
      - end_complete NOT reached
      - review_spawned == True
    """

    def test_direct_execution_with_review(self):
        workflow = load_workflow()

        # assess_task: direct execution, review required
        complete_user_task(workflow, "assess_task", {
            "delegation": "direct",
            "needs_review": True,
        })

        # Engine takes the direct default path; stops at execute_directly
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "execute_directly" in ready_names, (
            f"execute_directly should be READY after direct delegation. Got: {ready_names}"
        )

        complete_user_task(workflow, "execute_directly", {})

        # spawn_reviewer is a script task; engine stops at process_review
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "process_review" in ready_names, (
            f"process_review should be READY after spawn_reviewer. Got: {ready_names}"
        )

        # Verify spawn_reviewer ran
        names = completed_names(workflow)
        assert "spawn_reviewer" in names, "spawn_reviewer script must have run before process_review"

        complete_user_task(workflow, "process_review", {})

        assert workflow.is_completed(), "Workflow should be completed after process_review"

        names = completed_names(workflow)
        assert "execute_directly" in names, "execute_directly must have been completed"
        assert "spawn_reviewer" in names, "spawn_reviewer must have completed"
        assert "process_review" in names, "process_review must have been completed"
        assert "end_reviewed" in names, "end_reviewed must be reached"
        assert "end_complete" not in names, "end_complete must NOT be reached when review was needed"
        assert "spawn_agent" not in names, "spawn_agent must NOT run on direct path"

        assert workflow.data.get("review_spawned") is True, (
            "spawn_reviewer should have set review_spawned=True"
        )
