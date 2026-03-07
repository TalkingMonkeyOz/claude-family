"""
Tests for the Session Lifecycle BPMN process (v3 - auto_archive, check_messages, rag_per_prompt, auto_close).

Uses SpiffWorkflow 3.x API directly against the session_lifecycle.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Process flow summary (v3 - 2026-03-07):
  start_event -> auto_archive -> session_start -> check_messages -> load_state
    -> has_prior_state_gateway
      [prior_state==True] -> display_session_summary -> has_prior_tasks_gateway
        [has_prior_tasks==True] -> display_prior_tasks -> prior_tasks_merge
        [default]               -> prior_tasks_merge
      [default] -> fresh_start
    -> work_merge_gateway -> rag_per_prompt -> do_work
    -> work_action_gateway
      [action=="end_session"] -> save_summary -> close_session -> end_normal
      [action=="compact"]     -> save_checkpoint -> do_work (loop)
      [action=="auto_close"]  -> auto_close_session -> end_auto
      [default]               -> do_work (loop, continue working)

New elements vs v2:
  - auto_archive: fires before session_start to archive old sessions (>24h)
  - check_messages: checks inbox before load_state
  - rag_per_prompt: RAG + core protocol injection (per prompt, shown once at startup)
  - auto_close_session / end_auto: SessionEnd hook auto-close path
  - save_checkpoint renamed to include PreCompact detail
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "session_lifecycle.bpmn")
)
PROCESS_ID = "session_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past any initial automated steps (script tasks, start event)
    # auto_archive, session_start, check_messages all auto-run before load_state
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
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
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def completed_spec_names(workflow: BpmnWorkflow) -> list:
    """Return the spec names of all COMPLETED tasks in the workflow."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFreshSession:
    """
    No prior state -> fresh_start -> rag_per_prompt -> do_work -> end_session -> end_normal.

    Flow:
        start_event -> auto_archive -> session_start -> check_messages -> load_state
        -> has_prior_state_gateway [prior_state=False, default] -> fresh_start
        -> work_merge_gateway -> rag_per_prompt -> do_work
        -> work_action_gateway [action="end_session"] -> save_summary
        -> close_session -> end_normal
    """

    def test_fresh_session_completes_normally(self):
        workflow = load_workflow()

        # Engine has auto-run auto_archive, session_start, check_messages (all scriptTasks).
        # Stops at load_state (first userTask).
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "load_state" in ready_names, (
            f"Expected load_state to be READY after startup scripts. Got: {ready_names}"
        )

        # Verify startup scripts ran before load_state
        pre_load_names = completed_spec_names(workflow)
        assert "auto_archive" in pre_load_names, "auto_archive must auto-run before load_state"
        assert "session_start" in pre_load_names, "session_start must auto-run before load_state"
        assert "check_messages" in pre_load_names, "check_messages must auto-run before load_state"

        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # fresh_start, work_merge, rag_per_prompt all auto-run, stops at do_work
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after fresh start. Got: {ready_names}"
        )

        # Verify rag_per_prompt ran on the path to do_work
        mid_names = completed_spec_names(workflow)
        assert "rag_per_prompt" in mid_names, "rag_per_prompt must run before first do_work"

        # Complete do_work with action="end_session" to end the session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed after end_session"

        names = completed_spec_names(workflow)
        assert "auto_archive" in names
        assert "session_start" in names, "session_start script must have run"
        assert "check_messages" in names, "check_messages must have run"
        assert "load_state" in names, "load_state must have run"
        assert "fresh_start" in names, "fresh_start script must have run"
        assert "rag_per_prompt" in names, "rag_per_prompt must have run"
        assert "save_summary" in names, "save_summary script must have run"
        assert "close_session" in names, "close_session script must have run"
        assert "end_normal" in names, "end_normal end event must be reached"

        # The display-only resume flow must NOT run on fresh start
        assert "display_session_summary" not in names, (
            "display_session_summary must NOT run on fresh start"
        )
        assert "display_prior_tasks" not in names, (
            "display_prior_tasks must NOT run on fresh start"
        )

        # Script tasks write flags into task.data
        assert workflow.data.get("auto_archived") is True
        assert workflow.data.get("session_started") is True
        assert workflow.data.get("messages_checked") is True
        assert workflow.data.get("state_loaded") is True
        assert workflow.data.get("context") == "fresh"
        assert workflow.data.get("rag_injected") is True
        assert workflow.data.get("summary_saved") is True
        assert workflow.data.get("session_closed") is True


class TestResumedSession:
    """
    Prior state exists -> display_session_summary -> display_prior_tasks
    -> rag_per_prompt -> do_work -> end_session -> end_normal.
    """

    def test_resumed_session_displays_context_with_tasks(self):
        """Resume with prior state AND prior tasks - both display steps run."""
        workflow = load_workflow()

        # Complete load_state with prior_state=True to take the resume path
        complete_user_task(workflow, "load_state", {
            "state_loaded": True,
            "prior_state": True,
            "has_prior_tasks": True,
        })

        # All scriptTasks auto-run through to do_work
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after resume with tasks. Got: {ready_names}"
        )

        # End the session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "display_session_summary" in names, (
            "display_session_summary must run on resumed session"
        )
        assert "display_prior_tasks" in names, (
            "display_prior_tasks must run when has_prior_tasks=True"
        )
        assert "rag_per_prompt" in names, "rag_per_prompt must run on resumed session"
        assert "fresh_start" not in names, "fresh_start must NOT run on resumed session"
        assert "save_summary" in names
        assert "close_session" in names
        assert "end_normal" in names

        assert workflow.data.get("context_displayed") is True
        assert workflow.data.get("prior_tasks_displayed") is True
        assert workflow.data.get("rag_injected") is True
        assert workflow.data.get("session_closed") is True

    def test_resumed_session_no_prior_tasks(self):
        """Resume with prior state but NO prior tasks - skip display_prior_tasks."""
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {
            "state_loaded": True,
            "prior_state": True,
            "has_prior_tasks": False,
        })

        # Should reach do_work, skipping display_prior_tasks
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY after resume without tasks. Got: {ready_names}"
        )

        complete_user_task(workflow, "do_work", {"action": "end_session"})
        assert workflow.is_completed()

        names = completed_spec_names(workflow)
        assert "display_session_summary" in names, (
            "display_session_summary must always run on resume"
        )
        assert "display_prior_tasks" not in names, (
            "display_prior_tasks must NOT run when has_prior_tasks=False"
        )
        assert workflow.data.get("context_displayed") is True
        assert workflow.data.get("prior_tasks_displayed") is not True, (
            "prior_tasks_displayed should NOT be set when tasks were skipped"
        )


class TestCompactAndContinue:
    """
    do_work with action="compact" -> save_checkpoint (PreCompact hook) -> loop back to do_work
    -> action="end_session" -> end_normal.
    """

    def test_compact_then_end_session(self):
        workflow = load_workflow()

        # Complete load_state with fresh start (no prior state)
        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # Should be at do_work (fresh start path)
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names

        # First do_work pass: compact
        complete_user_task(workflow, "do_work", {"action": "compact"})

        # Engine runs save_checkpoint and loops back to do_work
        assert not workflow.is_completed(), "Workflow must NOT be completed after compact"

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names, (
            f"Expected do_work to be READY again after compact loop. Got: {ready_names}"
        )

        # Verify checkpoint (PreCompact hook) was saved
        comp_names = completed_spec_names(workflow)
        assert "save_checkpoint" in comp_names, (
            "save_checkpoint (PreCompact hook) must run on compact action"
        )

        # Second do_work pass: end session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed(), "Workflow should be completed after end_session"

        names = completed_spec_names(workflow)
        assert "save_summary" in names
        assert "close_session" in names
        assert "end_normal" in names
        assert workflow.data.get("checkpoint_saved") is True
        assert workflow.data.get("summary_saved") is True
        assert workflow.data.get("session_closed") is True

    def test_continue_work_loops_back(self):
        """
        do_work with the default action (no action key set, triggers default flow)
        loops back to do_work, then end_session completes the workflow.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        # First do_work pass: continue (default flow)
        complete_user_task(workflow, "do_work", {"action": "continue"})

        assert not workflow.is_completed()

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names

        # Second pass: end session
        complete_user_task(workflow, "do_work", {"action": "end_session"})

        assert workflow.is_completed()

        names = completed_spec_names(workflow)
        assert "end_normal" in names
        assert "save_checkpoint" not in names


class TestAutoClose:
    """
    do_work with action="auto_close" -> auto_close_session -> end_auto.
    This models the SessionEnd hook firing (process exit) vs manual /session-end.
    """

    def test_auto_close_reaches_end_auto(self):
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {"state_loaded": True, "prior_state": False})

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "do_work" in ready_names

        # Trigger auto_close path (SessionEnd hook)
        complete_user_task(workflow, "do_work", {"action": "auto_close"})

        assert workflow.is_completed(), "Workflow should be completed after auto_close"

        names = completed_spec_names(workflow)
        assert "auto_close_session" in names, (
            "auto_close_session must run on auto_close action"
        )
        assert "end_auto" in names, "end_auto must be reached on auto_close path"

        # Manual session-end path should NOT run
        assert "save_summary" not in names, (
            "save_summary (manual /session-end) must NOT run on auto_close"
        )
        assert "end_normal" not in names, (
            "end_normal (manual close) must NOT be reached on auto_close"
        )

        assert workflow.data.get("session_auto_closed") is True


class TestNoTaskRestoration:
    """
    Explicitly verify that the old restore_context element is gone
    and that no TaskCreate-style restoration happens.
    """

    def test_old_restore_context_element_does_not_exist(self):
        """The old 'restore_context' userTask must not exist in the process."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)

        task_spec_names = list(spec.task_specs.keys())
        assert "restore_context" not in task_spec_names, (
            "The old 'restore_context' userTask must be removed. "
            "It has been replaced with display-only scriptTasks: "
            "display_session_summary and display_prior_tasks."
        )

    def test_resume_path_is_all_script_tasks(self):
        """
        The resume path should be all scriptTasks (automated), not userTasks.
        The first userTask after load_state should be do_work.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "load_state", {
            "state_loaded": True,
            "prior_state": True,
            "has_prior_tasks": True,
        })

        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert ready_names == ["do_work"], (
            f"After resume, only do_work should be READY (all resume steps are automated). "
            f"Got: {ready_names}"
        )

    def test_new_elements_present(self):
        """Verify all v3 elements exist in the model spec."""
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        task_spec_names = list(spec.task_specs.keys())

        assert "auto_archive" in task_spec_names, "auto_archive scriptTask must exist"
        assert "check_messages" in task_spec_names, "check_messages scriptTask must exist"
        assert "rag_per_prompt" in task_spec_names, "rag_per_prompt scriptTask must exist"
        assert "auto_close_session" in task_spec_names, "auto_close_session scriptTask must exist"
        assert "end_auto" in task_spec_names, "end_auto endEvent must exist"
