"""
Tests for the Knowledge Full Cycle BPMN process.

Complete knowledge management lifecycle covering capture, vault embedding,
book references, conversation mining, and all retrieval paths.

Paths tested:
  1. Direct capture (no link): identify(capture) → formulate → embed → store → link_gw(no) → end
  2. Direct capture (with link): identify(capture) → formulate → embed → store → link_gw(yes) → link → end
  3. Vault embedding (changes found): identify(embed_vault) → scan(True) → chunk → upsert → end
  4. Vault embedding (no changes): identify(embed_vault) → scan(False) → end
  5. Book reference: identify(book_reference) → store_book → store_book_reference → end
  6. Conversation mining: identify(mine_conversation) → extract_conversation → extract_insights → end
  7. RAG retrieval (needs RAG): identify(retrieve) → source(rag) → classify(True) → query → inject → end
  8. RAG retrieval (skip): identify(retrieve) → source(rag) → classify(False) → end
  9. Direct search + apply: identify(retrieve) → source(direct) → direct_search → apply → mark → end
  10. Book search + apply: identify(retrieve) → source(books) → book_search → apply → mark → end

Key notes:
  - action_gw default routes to formulate_knowledge (direct capture)
  - action == "embed_vault" → scan_vault (script)
  - action == "book_reference" → store_book (script)
  - action == "mine_conversation" → extract_conversation (script)
  - action == "retrieve" → retrieve_source_gw
  - retrieve_source_gw default → rag_classify; source == "direct"/"books"/"graph"
  - link_gw: has_related == True → link_knowledge; default → end_merge
  - changes_gw: changes_found == True → chunk_and_embed; default → end_merge
  - needs_rag_gw: needs_rag == False → end_merge (skip); default → rag_query
  - direct/book/graph → apply_merge → apply_knowledge → mark_applied → end_merge

Implementation: mcp-servers/project-tools/server_v2.py, scripts/embed_vault_documents.py,
               scripts/rag_query_hook.py
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "knowledge_full_cycle.bpmn")
)
PROCESS_ID = "knowledge_full_cycle"


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
# Test 1: Direct Capture - No Link
# ---------------------------------------------------------------------------

class TestDirectCaptureNoLink:
    """
    identify(capture/default) → formulate → generate_embedding → store_in_knowledge
    → link_gw(has_related=False, default) → end_merge → end.
    """

    def test_direct_capture_no_link(self):
        wf = load_workflow()

        # identify_action is the first userTask
        # action_gw default routes to formulate_knowledge
        complete_user_task(wf, "identify_action", {"action": "capture"})

        # formulate_knowledge is a userTask
        assert "formulate_knowledge" in ready_task_names(wf)
        complete_user_task(wf, "formulate_knowledge", {"has_related": False})

        # generate_embedding → store_in_knowledge are scriptTasks (auto-run)
        # link_gw default (has_related=False) → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "formulate_knowledge" in names
        assert "generate_embedding" in names
        assert "store_in_knowledge" in names
        assert "link_knowledge" not in names
        assert "end" in names

        assert wf.data.get("embedding_generated") is True
        assert wf.data.get("knowledge_stored") is True


# ---------------------------------------------------------------------------
# Test 2: Direct Capture - With Link
# ---------------------------------------------------------------------------

class TestDirectCaptureWithLink:
    """
    identify(capture) → formulate → embed → store
    → link_gw(has_related=True) → link_knowledge → end_merge → end.
    """

    def test_direct_capture_with_link(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "capture"})
        complete_user_task(wf, "formulate_knowledge", {"has_related": True})

        # link_knowledge is a scriptTask → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "generate_embedding" in names
        assert "store_in_knowledge" in names
        assert "link_knowledge" in names
        assert "end" in names

        assert wf.data.get("linked") is True


# ---------------------------------------------------------------------------
# Test 3: Vault Embedding - Changes Found
# ---------------------------------------------------------------------------

class TestVaultEmbeddingChangesFound:
    """
    identify(embed_vault) → scan_vault(changes_found=True)
    → chunk_and_embed → upsert_vectors → end_merge → end.

    scan_vault is a scriptTask with: changes_found defaults to False via try/except.
    We inject changes_found=True via initial_data.
    """

    def test_vault_embedding_with_changes(self):
        wf = load_workflow(initial_data={"changes_found": True})

        complete_user_task(wf, "identify_action", {"action": "embed_vault"})

        # scan_vault (script, reads changes_found=True) → chunk_and_embed → upsert_vectors (scripts)
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "scan_vault" in names
        assert "chunk_and_embed" in names
        assert "upsert_vectors" in names
        assert "end" in names

        assert wf.data.get("chunks_embedded") is True
        assert wf.data.get("vectors_stored") is True


# ---------------------------------------------------------------------------
# Test 4: Vault Embedding - No Changes
# ---------------------------------------------------------------------------

class TestVaultEmbeddingNoChanges:
    """
    identify(embed_vault) → scan_vault(changes_found=False, default)
    → end_merge (skip chunk) → end.
    """

    def test_vault_embedding_no_changes(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "embed_vault"})

        # scan_vault defaults changes_found=False → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "scan_vault" in names
        assert "chunk_and_embed" not in names
        assert "upsert_vectors" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Test 5: Book Reference
# ---------------------------------------------------------------------------

class TestBookReference:
    """
    identify(book_reference) → store_book (script) → store_book_reference (script) → end.
    """

    def test_book_reference_path(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "book_reference"})

        # Both are scriptTasks → auto-run → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "store_book" in names
        assert "store_book_reference" in names
        assert "end" in names

        assert wf.data.get("book_stored") is True
        assert wf.data.get("ref_stored") is True


# ---------------------------------------------------------------------------
# Test 6: Conversation Mining
# ---------------------------------------------------------------------------

class TestConversationMining:
    """
    identify(mine_conversation) → extract_conversation (script) → extract_insights (script) → end.
    """

    def test_conversation_mining_path(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "mine_conversation"})

        # Both are scriptTasks → auto-run → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "extract_conversation" in names
        assert "extract_insights" in names
        assert "end" in names

        assert wf.data.get("conversation_extracted") is True
        assert wf.data.get("insights_extracted") is True


# ---------------------------------------------------------------------------
# Test 7: RAG Retrieval - Needs RAG (default)
# ---------------------------------------------------------------------------

class TestRagRetrievalNeedsRag:
    """
    identify(retrieve) → retrieve_source_gw(default/rag) → rag_classify(needs_rag=True, default)
    → rag_query → inject_context → end_merge → end.

    needs_rag defaults to True in the scriptTask.
    """

    def test_rag_retrieval_needs_rag(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "retrieve"})

        # retrieve_source_gw default → rag_classify (script, needs_rag defaults True)
        # needs_rag_gw default → rag_query (script) → inject_context (script)
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "rag_classify" in names
        assert "rag_query" in names
        assert "inject_context" in names
        assert "apply_knowledge" not in names
        assert "end" in names

        assert wf.data.get("context_injected") is True


# ---------------------------------------------------------------------------
# Test 8: RAG Retrieval - Skip RAG
# ---------------------------------------------------------------------------

class TestRagRetrievalSkip:
    """
    identify(retrieve) → retrieve_source_gw(rag) → rag_classify(needs_rag=False)
    → end_merge (skip rag_query) → end.

    We inject needs_rag=False via initial_data.
    """

    def test_rag_retrieval_skipped(self):
        wf = load_workflow(initial_data={"needs_rag": False})

        complete_user_task(wf, "identify_action", {"action": "retrieve"})

        # rag_classify reads needs_rag=False → skip → end_merge → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "rag_classify" in names
        assert "rag_query" not in names
        assert "inject_context" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Test 9: Direct Search + Apply
# ---------------------------------------------------------------------------

class TestDirectSearchAndApply:
    """
    identify(retrieve) → retrieve_source_gw(source=direct) → direct_search (script)
    → apply_merge → apply_knowledge (userTask) → mark_applied (script) → end.
    """

    def test_direct_search_and_apply(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "retrieve", "source": "direct"})

        # direct_search is a scriptTask → apply_merge → apply_knowledge (userTask)
        assert "apply_knowledge" in ready_task_names(wf), (
            f"Expected apply_knowledge after direct_search. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "apply_knowledge", {})

        # mark_applied is a scriptTask → end
        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "direct_search" in names
        assert "apply_knowledge" in names
        assert "mark_applied" in names
        assert "rag_query" not in names
        assert "end" in names

        assert wf.data.get("confidence_updated") is True


# ---------------------------------------------------------------------------
# Test 10: Book Search + Apply
# ---------------------------------------------------------------------------

class TestBookSearchAndApply:
    """
    identify(retrieve) → retrieve_source_gw(source=books) → book_search (script)
    → apply_merge → apply_knowledge (userTask) → mark_applied (script) → end.
    """

    def test_book_search_and_apply(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "retrieve", "source": "books"})

        # book_search is a scriptTask → apply_merge → apply_knowledge (userTask)
        assert "apply_knowledge" in ready_task_names(wf), (
            f"Expected apply_knowledge after book_search. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "apply_knowledge", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "book_search" in names
        assert "apply_knowledge" in names
        assert "mark_applied" in names
        assert "direct_search" not in names
        assert "end" in names


# ---------------------------------------------------------------------------
# Test 11: Graph Traversal + Apply
# ---------------------------------------------------------------------------

class TestGraphTraversalAndApply:
    """
    identify(retrieve) → retrieve_source_gw(source=graph) → graph_traverse (script)
    → apply_merge → apply_knowledge (userTask) → mark_applied (script) → end.
    """

    def test_graph_traversal_and_apply(self):
        wf = load_workflow()

        complete_user_task(wf, "identify_action", {"action": "retrieve", "source": "graph"})

        assert "apply_knowledge" in ready_task_names(wf), (
            f"Expected apply_knowledge after graph_traverse. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "apply_knowledge", {})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "graph_traverse" in names
        assert "apply_knowledge" in names
        assert "mark_applied" in names
        assert "end" in names
