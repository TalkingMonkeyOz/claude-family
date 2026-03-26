"""
Tests for the Prompt Context Injection BPMN process.

Uses SpiffWorkflow 3.x API directly against the prompt_context_injection.bpmn definition.
No external database, Voyage AI, or network access required - all assertions are on
task.data values set by script tasks within the BPMN model.

Process overview:

  start_event
    -> select_flow  [userTask - sets flow_type to route through gateway]
    -> flow_gateway
         [flow_type == "session_start"]  -> FLOW 1: SESSION START
         [default / "per_prompt"]        -> FLOW 2: PER-PROMPT INJECTION
         [flow_type == "on_demand_rag"]  -> FLOW 3: ON-DEMAND RAG

  FLOW 1 (Session Start — context pre-computation, once per session):
    read_active_features -> load_pinned_workfiles -> load_previous_session_facts
    -> write_session_cache -> end_cache_ready

  FLOW 2 (Per-Prompt Injection — fast path, file reads only, no Voyage AI):
    read_core_protocol -> read_session_cache -> combine_context
    -> return_json -> end_context_injected

  FLOW 3 (On-Demand RAG — Claude calls MCP, uses Voyage AI + pgvector):
    call_mcp_tools -> voyage_embedding -> pgvector_search
    -> return_results -> end_knowledge_retrieved

CRITICAL: All gateway variables must be pre-seeded in task.data at select_flow
before the gateway evaluates. The default branch is "per_prompt" (Flow 2).
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

# Absolute path to the BPMN file
BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "prompt_context_injection.bpmn")
)
PROCESS_ID = "prompt_context_injection"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow() -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    wf.do_engine_steps()
    return wf


def get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() so the engine advances through subsequent automated tasks.
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
# Test: BPMN parses correctly
# ---------------------------------------------------------------------------


class TestProcessParsing:
    """Verify the BPMN file can be parsed and a workflow instantiated."""

    def test_bpmn_file_exists(self):
        assert os.path.exists(BPMN_FILE), f"BPMN file not found at {BPMN_FILE}"

    def test_process_parses_and_starts(self):
        workflow = load_workflow()
        ready = get_ready_user_tasks(workflow)
        assert len(ready) == 1, "Should have exactly one ready user task (select_flow)"
        assert ready[0].task_spec.name == "select_flow"


# ---------------------------------------------------------------------------
# Test: Flow 1 — Session Start (context pre-computation)
# ---------------------------------------------------------------------------


class TestFlow1SessionStart:
    """
    Flow 1: SessionStart hook fires, pre-computes context cache.

    Flow:
        start_event -> select_flow [flow_type="session_start"]
        -> flow_gateway [session_start] -> read_active_features
        -> load_pinned_workfiles -> load_previous_session_facts
        -> write_session_cache -> end_cache_ready

    Verifies: All four session start tasks complete in sequence;
              Flow 2 and Flow 3 tasks do NOT execute.
    """

    def test_session_start_flow_completes(self):
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "session_start",
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Flow 1 tasks must have run
        assert "read_active_features" in names
        assert "load_pinned_workfiles" in names
        assert "load_previous_session_facts" in names
        assert "write_session_cache" in names
        assert "end_cache_ready" in names

        # Flow 2 tasks must NOT have run
        assert "read_core_protocol" not in names
        assert "read_session_cache" not in names
        assert "combine_context" not in names
        assert "return_json" not in names

        # Flow 3 tasks must NOT have run
        assert "call_mcp_tools" not in names
        assert "voyage_embedding" not in names
        assert "pgvector_search" not in names
        assert "return_results" not in names

    def test_session_start_sets_data_flags(self):
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "session_start",
        })

        assert workflow.data.get("features_loaded") is True
        assert workflow.data.get("workfiles_loaded") is True
        assert workflow.data.get("session_facts_loaded") is True
        assert workflow.data.get("cache_written") is True


# ---------------------------------------------------------------------------
# Test: Flow 2 — Per-Prompt Injection (fast path, no Voyage AI)
# ---------------------------------------------------------------------------


class TestFlow2PerPromptInjection:
    """
    Flow 2: Per-prompt injection completes WITHOUT requiring Voyage AI.

    This is the default (most frequent) path. The gateway's default branch
    routes here when flow_type is not "session_start" or "on_demand_rag".

    Flow:
        start_event -> select_flow [flow_type="per_prompt" or default]
        -> flow_gateway [default] -> read_core_protocol
        -> read_session_cache -> combine_context
        -> return_json -> end_context_injected

    Verifies: All four per-prompt tasks complete; NO Voyage AI or DB tasks
              from Flow 3 execute; NO session start tasks from Flow 1 execute.
    """

    def test_per_prompt_flow_completes(self):
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "per_prompt",
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Flow 2 tasks must have run
        assert "read_core_protocol" in names
        assert "read_session_cache" in names
        assert "combine_context" in names
        assert "return_json" in names
        assert "end_context_injected" in names

        # Flow 1 tasks must NOT have run
        assert "read_active_features" not in names
        assert "load_pinned_workfiles" not in names
        assert "load_previous_session_facts" not in names
        assert "write_session_cache" not in names

        # Flow 3 tasks must NOT have run (no Voyage AI on per-prompt path)
        assert "call_mcp_tools" not in names
        assert "voyage_embedding" not in names
        assert "pgvector_search" not in names
        assert "return_results" not in names

    def test_per_prompt_does_not_use_voyage_ai(self):
        """
        Critical test: the per-prompt path must never touch Voyage AI.
        Voyage AI tasks (voyage_embedding) only exist in Flow 3.
        """
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "per_prompt",
        })

        names = completed_spec_names(workflow)

        # Explicit assertion that voyage_embedding is NOT reached
        assert "voyage_embedding" not in names, (
            "Per-prompt injection must NEVER call Voyage AI. "
            "Voyage AI is only available in Flow 3 (on-demand RAG)."
        )

    def test_per_prompt_is_default_path(self):
        """The default gateway branch should route to per-prompt (Flow 2)."""
        workflow = load_workflow()

        # Use a value that doesn't match any condition — should take default
        complete_user_task(workflow, "select_flow", {
            "flow_type": "anything_else",
        })

        assert workflow.is_completed()
        names = completed_spec_names(workflow)
        assert "read_core_protocol" in names, "Default path should be per-prompt"
        assert "end_context_injected" in names

    def test_per_prompt_sets_data_flags(self):
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "per_prompt",
        })

        assert workflow.data.get("core_protocol_read") is True
        assert workflow.data.get("session_cache_read") is True
        assert workflow.data.get("context_combined") is True
        assert workflow.data.get("json_returned") is True


# ---------------------------------------------------------------------------
# Test: Flow 3 — On-Demand RAG (separate from per-prompt)
# ---------------------------------------------------------------------------


class TestFlow3OnDemandRag:
    """
    Flow 3: On-demand RAG is a SEPARATE flow from per-prompt injection.

    Claude explicitly calls MCP tools (recall_memories / assemble_context),
    which triggers Voyage AI embedding + pgvector search. This flow is
    independent of the per-prompt hook pipeline.

    Flow:
        start_event -> select_flow [flow_type="on_demand_rag"]
        -> flow_gateway [on_demand_rag] -> call_mcp_tools
        -> voyage_embedding -> pgvector_search
        -> return_results -> end_knowledge_retrieved

    Verifies: All four RAG tasks complete; per-prompt tasks do NOT execute;
              session start tasks do NOT execute.
    """

    def test_on_demand_rag_flow_completes(self):
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "on_demand_rag",
        })

        assert workflow.is_completed(), "Workflow should be completed"

        names = completed_spec_names(workflow)

        # Flow 3 tasks must have run
        assert "call_mcp_tools" in names
        assert "voyage_embedding" in names
        assert "pgvector_search" in names
        assert "return_results" in names
        assert "end_knowledge_retrieved" in names

        # Flow 2 tasks must NOT have run
        assert "read_core_protocol" not in names
        assert "read_session_cache" not in names
        assert "combine_context" not in names
        assert "return_json" not in names

        # Flow 1 tasks must NOT have run
        assert "read_active_features" not in names
        assert "write_session_cache" not in names

    def test_on_demand_rag_is_separate_from_per_prompt(self):
        """
        Critical test: On-demand RAG and per-prompt injection are
        mutually exclusive flows. They never execute together.
        """
        # Run per-prompt
        wf_prompt = load_workflow()
        complete_user_task(wf_prompt, "select_flow", {"flow_type": "per_prompt"})
        prompt_names = set(completed_spec_names(wf_prompt))

        # Run on-demand RAG
        wf_rag = load_workflow()
        complete_user_task(wf_rag, "select_flow", {"flow_type": "on_demand_rag"})
        rag_names = set(completed_spec_names(wf_rag))

        # The task sets should not overlap (except shared infrastructure:
        # start, select, gateway, and SpiffWorkflow internal nodes)
        shared = {"start_event", "select_flow", "flow_gateway", "Start", "Root",
                  "End", "prompt_context_injection.EndJoin"}
        prompt_unique = prompt_names - shared
        rag_unique = rag_names - shared

        overlap = prompt_unique & rag_unique
        assert len(overlap) == 0, (
            f"Per-prompt and on-demand RAG flows should not share tasks. "
            f"Overlapping tasks: {overlap}"
        )

    def test_on_demand_rag_sets_data_flags(self):
        workflow = load_workflow()

        complete_user_task(workflow, "select_flow", {
            "flow_type": "on_demand_rag",
        })

        assert workflow.data.get("mcp_called") is True
        assert workflow.data.get("embedding_generated") is True
        assert workflow.data.get("search_completed") is True
        assert workflow.data.get("results_returned") is True
