"""
Tests for the RAG Pipeline BPMN process.

Uses SpiffWorkflow 3.x API directly against the rag_pipeline.bpmn definition.
No external database or network required - all assertions are on task.data values.

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
  - workflow.data is populated from the last completed task's data on workflow completion
  - Gateway conditions are Python expressions eval'd against task.data

Process overview:

  start_event
    -> trigger_pipeline  [userTask - sets pipeline_mode + downstream vars]
    -> pipeline_mode_gateway
         [pipeline_mode == "embed"] -> PATH A: EMBEDDING
         [default]                  -> PATH B: RETRIEVAL

  PATH A (Embedding):
    scan_vault                           [scriptTask - vault_scanned=True]
    -> changes_found_gateway
         [changes_found == True] -> generate_embeddings -> store_in_pgvector -> end_embeddings_updated
         [default]               -> end_no_changes

  PATH B (Retrieval):
    classify_prompt                      [scriptTask - prompt_classified=True]
    -> needs_rag_gateway
         [needs_rag == True] -> query_voyage_embeddings -> inject_context -> end_context_enriched
         [default]           -> end_rag_skipped

CRITICAL: All gateway variables (pipeline_mode, changes_found, needs_rag) must be
pre-seeded in task.data at trigger_pipeline before the first gateway evaluates.
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "rag_pipeline.bpmn")
)
PROCESS_ID = "rag_pipeline"


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


class TestEmbeddingPathWithChanges:
    """
    Embedding path: vault has changes, so full embed pipeline runs.

    Flow:
        start_event -> trigger_pipeline [pipeline_mode="embed", changes_found=True]
        -> pipeline_mode_gateway [embed] -> scan_vault
        -> changes_found_gateway [True] -> generate_embeddings
        -> store_in_pgvector -> end_embeddings_updated

    Verifies: scan_vault, generate_embeddings, store_in_pgvector all complete;
              embeddings_stored is True; retrieve path tasks NOT executed.
    """

    def test_embedding_path_with_changes(self):
        workflow = load_workflow()

        # Pre-seed ALL gateway variables at the single userTask.
        # changes_found=True routes through the "Yes" branch.
        # needs_rag is set defensively (unused on this path, but avoids KeyError
        # if the engine ever evaluates the retrieve-path gateway expression).
        complete_user_task(workflow, "trigger_pipeline", {
            "pipeline_mode": "embed",
            "changes_found": True,
            "needs_rag": False,
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Embed path tasks must have run
        assert "scan_vault" in names, "scan_vault script must have run"
        assert "generate_embeddings" in names, "generate_embeddings script must have run"
        assert "store_in_pgvector" in names, "store_in_pgvector script must have run"
        assert "end_embeddings_updated" in names, "end_embeddings_updated must be reached"

        # Skip/short-circuit tasks must NOT have run
        assert "end_no_changes" not in names, "end_no_changes must NOT be reached when changes exist"

        # Retrieve path tasks must NOT have run
        assert "classify_prompt" not in names, "classify_prompt must NOT run on embed path"
        assert "query_voyage_embeddings" not in names, "query_voyage_embeddings must NOT run on embed path"
        assert "inject_context" not in names, "inject_context must NOT run on embed path"

        # Script task side-effects must be present in final workflow data
        assert workflow.data.get("vault_scanned") is True, (
            "scan_vault should have set vault_scanned=True"
        )
        assert workflow.data.get("embeddings_generated") is True, (
            "generate_embeddings should have set embeddings_generated=True"
        )
        assert workflow.data.get("embeddings_stored") is True, (
            "store_in_pgvector should have set embeddings_stored=True"
        )


class TestEmbeddingPathNoChanges:
    """
    Embedding path: vault has NO changes, so pipeline skips to early end.

    Flow:
        start_event -> trigger_pipeline [pipeline_mode="embed", changes_found=False]
        -> pipeline_mode_gateway [embed] -> scan_vault
        -> changes_found_gateway [default/False] -> end_no_changes

    Verifies: scan_vault completes; generate_embeddings and store_in_pgvector
              do NOT run; workflow reaches end_no_changes.
    """

    def test_embedding_path_no_changes(self):
        workflow = load_workflow()

        # changes_found=False causes changes_found_gateway to take the default
        # (no-changes) branch, skipping generate_embeddings and store_in_pgvector.
        complete_user_task(workflow, "trigger_pipeline", {
            "pipeline_mode": "embed",
            "changes_found": False,
            "needs_rag": False,
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Scan must have run (always happens before the gateway)
        assert "scan_vault" in names, "scan_vault must always run on embed path"
        assert "end_no_changes" in names, "end_no_changes must be reached when no changes"

        # Embedding tasks must NOT have run
        assert "generate_embeddings" not in names, (
            "generate_embeddings must NOT run when no changes detected"
        )
        assert "store_in_pgvector" not in names, (
            "store_in_pgvector must NOT run when no changes detected"
        )
        assert "end_embeddings_updated" not in names, (
            "end_embeddings_updated must NOT be reached when no changes"
        )

        # vault_scanned flag from scan_vault script
        assert workflow.data.get("vault_scanned") is True, (
            "scan_vault should have set vault_scanned=True even when no changes found"
        )


class TestRetrievalPathNeedsRag:
    """
    Retrieval path: prompt is a question/exploration, so RAG context is injected.

    Flow:
        start_event -> trigger_pipeline [pipeline_mode="retrieve", needs_rag=True]
        -> pipeline_mode_gateway [default/retrieve] -> classify_prompt
        -> needs_rag_gateway [True] -> query_voyage_embeddings
        -> inject_context -> end_context_enriched

    Verifies: classify_prompt, query_voyage_embeddings, inject_context all complete;
              context_injected is True; embed path tasks NOT executed.
    """

    def test_retrieval_path_needs_rag(self):
        workflow = load_workflow()

        # pipeline_mode is not "embed" so the default branch (retrieve) fires.
        # needs_rag=True routes through the "Yes" branch of needs_rag_gateway.
        complete_user_task(workflow, "trigger_pipeline", {
            "pipeline_mode": "retrieve",
            "changes_found": False,
            "needs_rag": True,
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Retrieval path tasks must have run
        assert "classify_prompt" in names, "classify_prompt script must have run"
        assert "query_voyage_embeddings" in names, "query_voyage_embeddings script must have run"
        assert "inject_context" in names, "inject_context script must have run"
        assert "end_context_enriched" in names, "end_context_enriched must be reached"

        # Skip end event must NOT have been reached
        assert "end_rag_skipped" not in names, (
            "end_rag_skipped must NOT be reached when RAG is needed"
        )

        # Embed path tasks must NOT have run
        assert "scan_vault" not in names, "scan_vault must NOT run on retrieve path"
        assert "generate_embeddings" not in names, "generate_embeddings must NOT run on retrieve path"
        assert "store_in_pgvector" not in names, "store_in_pgvector must NOT run on retrieve path"

        # Script task side-effects
        assert workflow.data.get("prompt_classified") is True, (
            "classify_prompt should have set prompt_classified=True"
        )
        assert workflow.data.get("vault_docs_retrieved") is True, (
            "query_voyage_embeddings should have set vault_docs_retrieved=True"
        )
        assert workflow.data.get("context_injected") is True, (
            "inject_context should have set context_injected=True"
        )


class TestRetrievalPathSkipRag:
    """
    Retrieval path: prompt is an action command, so RAG is skipped entirely.

    Flow:
        start_event -> trigger_pipeline [pipeline_mode="retrieve", needs_rag=False]
        -> pipeline_mode_gateway [default/retrieve] -> classify_prompt
        -> needs_rag_gateway [default/skip] -> end_rag_skipped

    Verifies: classify_prompt runs; query_voyage_embeddings and inject_context do NOT;
              workflow reaches end_rag_skipped.
    """

    def test_retrieval_path_skip_rag(self):
        workflow = load_workflow()

        # needs_rag=False causes needs_rag_gateway to take the default (skip) branch.
        complete_user_task(workflow, "trigger_pipeline", {
            "pipeline_mode": "retrieve",
            "changes_found": False,
            "needs_rag": False,
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Classify must run (always happens before needs_rag_gateway)
        assert "classify_prompt" in names, "classify_prompt must always run on retrieve path"
        assert "end_rag_skipped" in names, "end_rag_skipped must be reached for action prompts"

        # Context injection tasks must NOT have run
        assert "query_voyage_embeddings" not in names, (
            "query_voyage_embeddings must NOT run when RAG is skipped"
        )
        assert "inject_context" not in names, (
            "inject_context must NOT run when RAG is skipped"
        )
        assert "end_context_enriched" not in names, (
            "end_context_enriched must NOT be reached when RAG is skipped"
        )

        # Embed path tasks must NOT have run
        assert "scan_vault" not in names, "scan_vault must NOT run on retrieve path"

        # prompt_classified flag from classify_prompt script
        assert workflow.data.get("prompt_classified") is True, (
            "classify_prompt should have set prompt_classified=True even when RAG is skipped"
        )
