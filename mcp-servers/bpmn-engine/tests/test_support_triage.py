"""
Tests for the Support Triage BPMN process.

Uses SpiffWorkflow 3.x API directly against the support_triage.bpmn definition.
No external database required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Flow summary:
  start → receive_ticket (inject: is_duplicate, decision)
       → extract_details → check_duplicates → is_duplicate_gateway
           [is_duplicate==True]  → link_duplicate → end_duplicate
           [default]             → query_knowledge → ai_suggest_resolution
                                 → human_review (inject: decision)
                                 → review_decision_gateway
                                     [decision=="escalate"] → escalate_ticket → end_escalated
                                     [decision=="modify"]   → modify_response → send_response_modified
                                                             → end_resolved_modified
                                     [default/approve]      → send_response → end_resolved
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "nimbus", "support_triage.bpmn")
)
PROCESS_ID = "support_triage"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past the start event and any initial automated steps
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


class TestDuplicateTicket:
    """
    Ticket is detected as a duplicate.

    Flow:
        start → receive_ticket [is_duplicate=True]
             → extract_details → check_duplicates
             → is_duplicate_gateway [is_duplicate==True]
             → link_duplicate → end_duplicate

    Verifies:
        - linked == True
        - status == "duplicate"
        - query_knowledge NOT in completed (short-circuited)
        - end_duplicate reached
    """

    def test_duplicate_ticket(self):
        workflow = load_workflow()

        # Inject is_duplicate=True so the gateway routes to link_duplicate.
        # decision is not needed on this path but providing a safe default prevents
        # KeyError if the engine evaluates all gateway conditions eagerly.
        complete_user_task(workflow, "receive_ticket", {"is_duplicate": True, "decision": "approve"})

        assert workflow.is_completed(), "Workflow should be completed after duplicate short-circuit"

        names = completed_spec_names(workflow)
        assert "extract_details" in names, "extract_details must have run"
        assert "check_duplicates" in names, "check_duplicates must have run"
        assert "link_duplicate" in names, "link_duplicate script must have run"
        assert "end_duplicate" in names, "end_duplicate end event must be reached"
        assert "query_knowledge" not in names, (
            "query_knowledge must NOT be executed for duplicate tickets"
        )
        assert "end_resolved" not in names, "end_resolved must NOT be reached on duplicate path"
        assert "end_escalated" not in names, "end_escalated must NOT be reached on duplicate path"

        assert workflow.data.get("linked") is True, (
            "link_duplicate should have set linked=True"
        )
        assert workflow.data.get("status") == "duplicate", (
            "link_duplicate should have set status='duplicate'"
        )


class TestAutoResolvedTicket:
    """
    Ticket is not a duplicate; human reviewer approves the AI suggestion as-is.

    Flow:
        start → receive_ticket [is_duplicate=False]
             → extract_details → check_duplicates
             → is_duplicate_gateway [default / not duplicate]
             → query_knowledge → ai_suggest_resolution
             → human_review [decision="approve"]
             → review_decision_gateway [default / approve]
             → send_response → end_resolved

    Verifies:
        - status == "resolved"
        - response_sent == True
        - suggestion_generated == True
        - modify_response NOT in completed
        - end_resolved reached
    """

    def test_auto_resolved_ticket(self):
        workflow = load_workflow()

        # Route past the duplicate gateway (default = not duplicate).
        # decision key must be present before review_decision_gateway fires.
        complete_user_task(workflow, "receive_ticket", {"is_duplicate": False, "decision": "approve"})

        # After receive_ticket, engine runs extract_details, check_duplicates, gateway
        # (takes not-duplicate default), query_knowledge, ai_suggest_resolution, then
        # stops at human_review.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "human_review" in ready_names, (
            f"human_review should be READY after AI suggestion, got: {ready_names}"
        )

        # Human approves - default path taken by review_decision_gateway.
        complete_user_task(workflow, "human_review", {"decision": "approve"})

        assert workflow.is_completed(), "Workflow should be completed after approval"

        names = completed_spec_names(workflow)
        assert "query_knowledge" in names, "query_knowledge script must have run"
        assert "ai_suggest_resolution" in names, "ai_suggest_resolution script must have run"
        assert "send_response" in names, "send_response script must have run"
        assert "end_resolved" in names, "end_resolved end event must be reached"
        assert "modify_response" not in names, (
            "modify_response must NOT be executed on approve path"
        )
        assert "escalate_ticket" not in names, (
            "escalate_ticket must NOT be executed on approve path"
        )
        assert "end_resolved_modified" not in names, (
            "end_resolved_modified must NOT be reached on approve path"
        )

        assert workflow.data.get("response_sent") is True, (
            "send_response should have set response_sent=True"
        )
        assert workflow.data.get("status") == "resolved", (
            "send_response should have set status='resolved'"
        )
        assert workflow.data.get("suggestion_generated") is True, (
            "ai_suggest_resolution should have set suggestion_generated=True"
        )


class TestModifiedResponse:
    """
    Human reviewer chooses to modify the AI suggestion before sending.

    Flow:
        start → receive_ticket [is_duplicate=False]
             → ... → human_review [decision="modify"]
             → review_decision_gateway [decision=="modify"]
             → modify_response → send_response_modified → end_resolved_modified

    Verifies:
        - modify_response in completed
        - send_response_modified in completed
        - end_resolved_modified reached
        - status == "resolved"
        - response_sent == True
        - send_response (approve path) NOT in completed
    """

    def test_modified_response(self):
        workflow = load_workflow()

        # Route past duplicate gateway; inject decision early so the gateway has the key.
        complete_user_task(workflow, "receive_ticket", {"is_duplicate": False, "decision": "modify"})

        # Engine stops at human_review.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "human_review" in ready_names, (
            f"human_review should be READY, got: {ready_names}"
        )

        # Human requests modification.
        complete_user_task(workflow, "human_review", {"decision": "modify"})

        # Engine stops at modify_response (user task).
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "modify_response" in ready_names, (
            f"modify_response should be READY after 'modify' decision, got: {ready_names}"
        )

        # Human submits the modified response.
        complete_user_task(workflow, "modify_response", {})

        assert workflow.is_completed(), "Workflow should be completed after sending modified response"

        names = completed_spec_names(workflow)
        assert "modify_response" in names, "modify_response must have been completed"
        assert "send_response_modified" in names, "send_response_modified script must have run"
        assert "end_resolved_modified" in names, "end_resolved_modified end event must be reached"
        assert "send_response" not in names, (
            "send_response (approve path) must NOT be executed on modify path"
        )
        assert "escalate_ticket" not in names, (
            "escalate_ticket must NOT be executed on modify path"
        )

        assert workflow.data.get("response_sent") is True, (
            "send_response_modified should have set response_sent=True"
        )
        assert workflow.data.get("status") == "resolved", (
            "send_response_modified should have set status='resolved'"
        )


class TestEscalatedTicket:
    """
    Human reviewer decides the ticket needs escalation.

    Flow:
        start → receive_ticket [is_duplicate=False]
             → ... → human_review [decision="escalate"]
             → review_decision_gateway [decision=="escalate"]
             → escalate_ticket → end_escalated

    Verifies:
        - escalated == True
        - status == "escalated"
        - response_sent NOT True (ticket was not resolved)
        - end_escalated reached
        - send_response NOT in completed
    """

    def test_escalated_ticket(self):
        workflow = load_workflow()

        # Route past duplicate gateway; inject decision key early.
        complete_user_task(workflow, "receive_ticket", {"is_duplicate": False, "decision": "escalate"})

        # Engine stops at human_review.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "human_review" in ready_names, (
            f"human_review should be READY, got: {ready_names}"
        )

        # Human escalates.
        complete_user_task(workflow, "human_review", {"decision": "escalate"})

        assert workflow.is_completed(), "Workflow should be completed after escalation"

        names = completed_spec_names(workflow)
        assert "escalate_ticket" in names, "escalate_ticket script must have run"
        assert "end_escalated" in names, "end_escalated end event must be reached"
        assert "send_response" not in names, (
            "send_response must NOT be executed on escalation path"
        )
        assert "send_response_modified" not in names, (
            "send_response_modified must NOT be executed on escalation path"
        )
        assert "modify_response" not in names, (
            "modify_response must NOT be executed on escalation path"
        )
        assert "end_resolved" not in names, "end_resolved must NOT be reached on escalation path"

        assert workflow.data.get("escalated") is True, (
            "escalate_ticket should have set escalated=True"
        )
        assert workflow.data.get("status") == "escalated", (
            "escalate_ticket should have set status='escalated'"
        )
        # response_sent should either be absent from data or explicitly False
        assert not workflow.data.get("response_sent"), (
            "response_sent must not be True when ticket was escalated (not resolved)"
        )
