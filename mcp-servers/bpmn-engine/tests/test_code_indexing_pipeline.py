"""
Tests for the Code Knowledge Graph indexing pipeline BPMN model.

Structural-assertion tests: verify the model parses and that the
extract_symbols script task documents the wrapper-node patterns the
indexer must traverse (FB406 decorated_definition, FB404 object
literals). The flow itself is unchanged by FB404/FB406 — only the
extract step's behaviour was clarified — so we assert on model
integrity, not flow execution.
"""

import os
import xml.etree.ElementTree as ET

import pytest

from SpiffWorkflow.bpmn.parser import BpmnParser

BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "processes",
        "infrastructure",
        "code_knowledge_graph.bpmn",
    )
)
PROCESS_ID = "code_indexing_pipeline"

NS = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}


def _load_extract_symbols_task():
    """Return the <scriptTask id='extract_symbols'> element from the BPMN."""
    tree = ET.parse(BPMN_FILE)
    root = tree.getroot()
    for proc in root.findall("bpmn:process", NS):
        if proc.get("id") == PROCESS_ID:
            for st in proc.findall("bpmn:scriptTask", NS):
                if st.get("id") == "extract_symbols":
                    return st
    raise AssertionError("extract_symbols scriptTask not found in BPMN model")


# ---------------------------------------------------------------------------
# Model integrity
# ---------------------------------------------------------------------------


class TestBpmnModelParses:
    def test_bpmn_file_exists(self):
        assert os.path.isfile(BPMN_FILE), f"BPMN file missing: {BPMN_FILE}"

    def test_spiff_can_parse_process(self):
        parser = BpmnParser()
        parser.add_bpmn_file(BPMN_FILE)
        spec = parser.get_spec(PROCESS_ID)
        assert spec is not None
        assert spec.name == PROCESS_ID

    def test_extract_symbols_task_present(self):
        task = _load_extract_symbols_task()
        assert task is not None
        assert task.get("name") == "[TOOL] Extract Symbols"


# ---------------------------------------------------------------------------
# Behaviour clarification (FB404 / FB406)
# ---------------------------------------------------------------------------


class TestExtractSymbolsHandlesWrapperNodes:
    """
    FB404 (TS object literals) and FB406 (Python @decorator) both stem
    from the indexer not recursing through grammar wrapper nodes that
    carry no symbol name themselves. The BPMN model's extract_symbols
    task must document both patterns so the model and code stay aligned.
    """

    def test_decorated_definition_documented(self):
        task = _load_extract_symbols_task()
        body = ET.tostring(task, encoding="unicode")
        assert "decorated_definition" in body, (
            "extract_symbols must document the Python decorated_definition "
            "wrapper (FB406)"
        )
        assert "FB406" in body, "FB406 traceability missing from extract_symbols"

    def test_object_literal_documented(self):
        task = _load_extract_symbols_task()
        body = ET.tostring(task, encoding="unicode")
        # Either the lexical_declaration wrapper or the object value type
        assert "lexical_declaration" in body or "object" in body, (
            "extract_symbols must document the TS object-literal const "
            "wrapper (FB404)"
        )
        assert "FB404" in body, "FB404 traceability missing from extract_symbols"

    def test_documentation_block_present(self):
        task = _load_extract_symbols_task()
        docs = task.findall("bpmn:documentation", NS)
        assert len(docs) >= 1, (
            "extract_symbols should carry a <bpmn:documentation> block "
            "explaining the wrapper-node behaviour"
        )


# ---------------------------------------------------------------------------
# Wave 3 — FB401, FB402, FB403, FB405 annotations
# ---------------------------------------------------------------------------


def _load_task(task_id: str):
    """Return any scriptTask by id from any process in the BPMN."""
    tree = ET.parse(BPMN_FILE)
    root = tree.getroot()
    for proc in root.findall("bpmn:process", NS):
        for st in proc.findall("bpmn:scriptTask", NS):
            if st.get("id") == task_id:
                return st
    raise AssertionError(f"scriptTask '{task_id}' not found in BPMN model")


class TestWave3RefResolutionAnnotations:
    """FB402 (cross-language scoping) + FB403 (object-method dispatch)
    are documented on extract_references and resolve_cross_refs."""

    def test_extract_references_documents_fb402_and_fb403(self):
        task = _load_task("extract_references")
        body = ET.tostring(task, encoding="unicode")
        assert "FB402" in body, "FB402 traceability missing from extract_references"
        assert "FB403" in body, "FB403 traceability missing from extract_references"
        # The model must mention language scoping AND receiver capture so
        # future Claude can tell what the collector + resolver are doing.
        assert "language" in body.lower(), (
            "FB402 — extract_references must document language-scoped resolution"
        )
        assert "receiver" in body.lower(), (
            "FB403 — extract_references must document receiver expression capture"
        )

    def test_extract_references_documents_fb405(self):
        task = _load_task("extract_references")
        body = ET.tostring(task, encoding="unicode")
        assert "FB405" in body, "FB405 traceability missing from extract_references"
        assert "barrel" in body.lower() or "re-export" in body.lower() or "re_export" in body.lower(), (
            "FB405 — extract_references must mention barrel/re-export handling"
        )

    def test_resolve_cross_refs_documents_two_pass(self):
        task = _load_task("resolve_cross_refs")
        body = ET.tostring(task, encoding="unicode")
        assert "FB402" in body, "FB402 traceability missing from resolve_cross_refs"
        assert "FB403" in body, "FB403 traceability missing from resolve_cross_refs"
        # The model must document the two-pass design.
        assert "Pass 1" in body or "pass 1" in body.lower()
        assert "Pass 2" in body or "pass 2" in body.lower()


class TestWave3GetModuleMapAnnotations:
    """FB401 (TOC envelope) + FB405 (barrel response) are documented on
    the module_map task in the code_query_tools process."""

    def test_module_map_documents_fb401(self):
        task = _load_task("module_map")
        body = ET.tostring(task, encoding="unicode")
        assert "FB401" in body, "FB401 traceability missing from module_map"
        assert "section_id" in body, (
            "FB401 — module_map must document section_id navigation"
        )
        assert "TOC" in body or "toc" in body.lower(), (
            "FB401 — module_map must document TOC envelope"
        )
        assert "truncate" in body.lower() or "truncation" in body.lower(), (
            "FB401 — must mention 'no truncation' principle"
        )

    def test_module_map_documents_fb405(self):
        task = _load_task("module_map")
        body = ET.tostring(task, encoding="unicode")
        assert "FB405" in body, "FB405 traceability missing from module_map"
        assert "barrel" in body.lower(), (
            "FB405 — module_map must document barrel response"
        )

    def test_module_map_has_documentation_block(self):
        task = _load_task("module_map")
        docs = task.findall("bpmn:documentation", NS)
        assert len(docs) >= 1, (
            "module_map should carry a <bpmn:documentation> block "
            "explaining the FB401/FB405 envelope shapes"
        )


class TestWave3SummarizeAnnotations:
    """FB401 dry_run aggregate is documented on the summarize task."""

    def test_summarize_documents_fb401_dry_run(self):
        task = _load_task("summarize")
        body = ET.tostring(task, encoding="unicode")
        assert "FB401" in body, "FB401 traceability missing from summarize"
        assert "verbose" in body.lower(), (
            "FB401 — summarize must mention verbose mode for full detail"
        )
