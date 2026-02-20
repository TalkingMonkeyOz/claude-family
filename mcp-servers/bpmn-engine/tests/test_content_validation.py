"""
Tests for the Content Validation Pipeline BPMN process.

Models the combined PreToolUse hooks for Write/Edit operations:
  - Context Injector (context_injector_hook.py): adds context
  - Standards Validator (standards_validator.py): validates content

Test scenarios:
  1. DB unavailable → allow (fail-open)
  2. No matching standards → allow (no validation needed)
  3. Validation passes → allow
  4. Validation fails, no fix suggestion → deny (block)
  5. Validation fails, can suggest fix → ask (middleware correction)
  6. Context rules loaded → context injected + validation passes
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "infrastructure", "content_validation.bpmn")
)
PROCESS_ID = "content_validation"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
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


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDBUnavailable:
    """DB down → fail-open → allow."""

    def test_no_db_allows(self):
        wf = load_workflow({
            "has_file_path": True,
            "db_available": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "allow_no_db" in names
        assert "end_allowed" in names
        assert "load_context_rules" not in names
        assert wf.data.get("decision") == "allow"


class TestNoMatchingStandards:
    """DB available but no standards match file → allow."""

    def test_no_standards_allows(self):
        wf = load_workflow({
            "has_file_path": True,
            "db_available": True,
            "has_context_rules": False,
            "has_matching_standards": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "load_context_rules" in names
        assert "inject_context" in names
        assert "load_standards" in names
        assert "allow_no_standards" in names
        assert "end_allowed" in names
        assert "validate_content" not in names
        assert wf.data.get("decision") == "allow"


class TestValidationPasses:
    """Standards match, content validates → allow."""

    def test_validation_passes_allows(self):
        wf = load_workflow({
            "has_file_path": True,
            "db_available": True,
            "has_context_rules": True,
            "has_matching_standards": True,
            "validation_passed": True,
            "can_suggest_fix": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "validate_content" in names
        assert "allow_validated" in names
        assert "end_allowed" in names
        assert "deny_violation" not in names
        assert wf.data.get("decision") == "allow"


class TestValidationDenied:
    """Standards match, content fails, no suggestion → deny (block)."""

    def test_validation_fails_denies(self):
        wf = load_workflow({
            "has_file_path": True,
            "db_available": True,
            "has_context_rules": False,
            "has_matching_standards": True,
            "validation_passed": False,
            "can_suggest_fix": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "validate_content" in names
        assert "deny_violation" in names
        assert "end_denied" in names
        assert "allow_validated" not in names
        assert wf.data.get("decision") == "deny"


class TestValidationAskWithFix:
    """Standards match, content fails, can suggest → ask (middleware)."""

    def test_validation_suggests_fix(self):
        wf = load_workflow({
            "has_file_path": True,
            "db_available": True,
            "has_context_rules": False,
            "has_matching_standards": True,
            "validation_passed": False,
            "can_suggest_fix": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "validate_content" in names
        assert "ask_with_correction" in names
        assert "end_asked" in names
        assert "deny_violation" not in names
        assert wf.data.get("decision") == "ask"


class TestContextInjectedAndValidated:
    """Context rules loaded, standards pass → context injected + allowed."""

    def test_full_pipeline(self):
        wf = load_workflow({
            "has_file_path": True,
            "db_available": True,
            "has_context_rules": True,
            "has_matching_standards": True,
            "validation_passed": True,
            "can_suggest_fix": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "load_context_rules" in names
        assert "inject_context" in names
        assert "load_standards" in names
        assert "validate_content" in names
        assert "allow_validated" in names
        assert wf.data.get("context_injected") is True
        assert wf.data.get("decision") == "allow"
