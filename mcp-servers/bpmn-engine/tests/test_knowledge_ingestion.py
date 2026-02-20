"""
Tests for the Knowledge Ingestion Pipeline BPMN process.

Uses SpiffWorkflow 3.x API directly against the knowledge_ingestion.bpmn definition.
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
  start → receive_source [user sets source_type]
       → detect_source_type → source_type_gateway
           [source_type=="api_spec"]  → parse_api_spec  → parse_merge
           [source_type=="odata"]     → parse_odata_schema → parse_merge
           [default/unstructured]     → parse_unstructured → parse_merge
       → validate_content [user sets validation]
       → validation_gateway
           [validation=="rejected"] → flag_for_review → end_flagged
           [default/valid]          → generate_embeddings → index_knowledge
                                    → notify_available → end_ingested
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "nimbus", "knowledge_ingestion.bpmn")
)
PROCESS_ID = "knowledge_ingestion"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    # Advance past any initial automated steps (e.g. the start event)
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


class TestApiSpecIngestion:
    """
    API spec source: receive_source [source_type="api_spec"] → parse_api_spec
    → validate_content [validation="approved"] → generate_embeddings
    → index_knowledge → notify_available → end_ingested.

    Verifies: content_type=="api_spec", status=="ingested", parse_odata_schema
              and parse_unstructured NOT executed.
    """

    def test_api_spec_ingestion(self):
        workflow = load_workflow()

        # --- Receive Source ------------------------------------------------
        # source_type="api_spec" routes to parse_api_spec branch.
        complete_user_task(workflow, "receive_source", {"source_type": "api_spec"})

        # Engine stops at validate_content (user task) after parse_api_spec
        # runs through parse_merge automatically.
        ready_names = [t.task_spec.name for t in get_ready_user_tasks(workflow)]
        assert "validate_content" in ready_names, (
            f"validate_content should be READY after parsing, got: {ready_names}"
        )

        # --- Validate Content (approved - default path) --------------------
        # Not setting validation="rejected" so validation_gateway takes the default branch.
        complete_user_task(workflow, "validate_content", {"validation": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "detect_source_type" in names, "detect_source_type script must have run"
        assert "parse_api_spec" in names, "parse_api_spec script must have run"
        assert "parse_odata_schema" not in names, "parse_odata_schema must NOT run on api_spec path"
        assert "parse_unstructured" not in names, "parse_unstructured must NOT run on api_spec path"
        assert "generate_embeddings" in names, "generate_embeddings script must have run"
        assert "index_knowledge" in names, "index_knowledge script must have run"
        assert "notify_available" in names, "notify_available script must have run"
        assert "end_ingested" in names, "end_ingested end event must be reached"
        assert "end_flagged" not in names, "end_flagged must NOT be reached on happy path"

        assert workflow.data.get("content_type") == "api_spec", (
            "parse_api_spec should have set content_type='api_spec'"
        )
        assert workflow.data.get("status") == "ingested", (
            "notify_available should have set status='ingested'"
        )
        assert workflow.data.get("parsed") is True, (
            "parse_api_spec should have set parsed=True"
        )
        assert workflow.data.get("embedded") is True, (
            "generate_embeddings should have set embedded=True"
        )
        assert workflow.data.get("indexed") is True, (
            "index_knowledge should have set indexed=True"
        )
        assert workflow.data.get("available") is True, (
            "notify_available should have set available=True"
        )


class TestODataIngestion:
    """
    OData schema source: receive_source [source_type="odata"] → parse_odata_schema
    → validate_content [approved] → generate_embeddings → index_knowledge
    → notify_available → end_ingested.

    Verifies: content_type=="odata", parse_api_spec and parse_unstructured NOT executed.
    """

    def test_odata_ingestion(self):
        workflow = load_workflow()

        # --- Receive Source ------------------------------------------------
        # source_type="odata" routes to parse_odata_schema branch.
        complete_user_task(workflow, "receive_source", {"source_type": "odata"})

        # --- Validate Content (approved) -----------------------------------
        complete_user_task(workflow, "validate_content", {"validation": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "parse_odata_schema" in names, "parse_odata_schema script must have run"
        assert "parse_api_spec" not in names, "parse_api_spec must NOT run on odata path"
        assert "parse_unstructured" not in names, "parse_unstructured must NOT run on odata path"
        assert "generate_embeddings" in names, "generate_embeddings script must have run"
        assert "index_knowledge" in names, "index_knowledge script must have run"
        assert "end_ingested" in names, "end_ingested end event must be reached"
        assert "end_flagged" not in names, "end_flagged must NOT be reached on happy path"

        assert workflow.data.get("content_type") == "odata", (
            "parse_odata_schema should have set content_type='odata'"
        )
        assert workflow.data.get("status") == "ingested", (
            "notify_available should have set status='ingested'"
        )
        assert workflow.data.get("parsed") is True, (
            "parse_odata_schema should have set parsed=True"
        )


class TestUnstructuredIngestion:
    """
    Unstructured source: receive_source [no special source_type] → parse_unstructured
    (default gateway branch) → validate_content [approved] → generate_embeddings
    → index_knowledge → notify_available → end_ingested.

    Verifies: content_type=="unstructured", parse_api_spec and parse_odata_schema
              NOT executed.
    """

    def test_unstructured_ingestion(self):
        workflow = load_workflow()

        # --- Receive Source ------------------------------------------------
        # source_type is neither "api_spec" nor "odata", so the default branch
        # (flow_unstructured) fires to parse_unstructured.
        complete_user_task(workflow, "receive_source", {"source_type": "document"})

        # --- Validate Content (approved) -----------------------------------
        complete_user_task(workflow, "validate_content", {"validation": "approved"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)
        assert "parse_unstructured" in names, "parse_unstructured script must have run"
        assert "parse_api_spec" not in names, "parse_api_spec must NOT run on unstructured path"
        assert "parse_odata_schema" not in names, "parse_odata_schema must NOT run on unstructured path"
        assert "generate_embeddings" in names, "generate_embeddings script must have run"
        assert "index_knowledge" in names, "index_knowledge script must have run"
        assert "end_ingested" in names, "end_ingested end event must be reached"
        assert "end_flagged" not in names, "end_flagged must NOT be reached on happy path"

        assert workflow.data.get("content_type") == "unstructured", (
            "parse_unstructured should have set content_type='unstructured'"
        )
        assert workflow.data.get("status") == "ingested", (
            "notify_available should have set status='ingested'"
        )
        assert workflow.data.get("parsed") is True, (
            "parse_unstructured should have set parsed=True"
        )


class TestValidationRejection:
    """
    Validation rejected: any source type → validate_content [validation="rejected"]
    → flag_for_review → end_flagged.

    Verifies: flagged==True, index_knowledge NOT completed, end_ingested NOT reached.
    Uses api_spec source as representative case.
    """

    def test_validation_rejection(self):
        workflow = load_workflow()

        # --- Receive Source ------------------------------------------------
        # Use api_spec as the source type (representative - any type leads to rejection).
        complete_user_task(workflow, "receive_source", {"source_type": "api_spec"})

        # --- Validate Content (rejected) -----------------------------------
        # validation="rejected" routes to flag_for_review via flow_rejected.
        complete_user_task(workflow, "validate_content", {"validation": "rejected"})

        # --- Assertions ----------------------------------------------------
        assert workflow.is_completed(), "Workflow should be completed after rejection"

        names = completed_spec_names(workflow)
        assert "flag_for_review" in names, "flag_for_review script must have run"
        assert "end_flagged" in names, "end_flagged end event must be reached"
        assert "generate_embeddings" not in names, (
            "generate_embeddings must NOT run when validation is rejected"
        )
        assert "index_knowledge" not in names, (
            "index_knowledge must NOT run when validation is rejected"
        )
        assert "notify_available" not in names, (
            "notify_available must NOT run when validation is rejected"
        )
        assert "end_ingested" not in names, "end_ingested must NOT be reached on rejection path"

        assert workflow.data.get("flagged") is True, (
            "flag_for_review should have set flagged=True"
        )
        # status should NOT be "ingested" on the rejected path
        assert workflow.data.get("status") != "ingested", (
            "status must not be 'ingested' when knowledge was rejected"
        )
