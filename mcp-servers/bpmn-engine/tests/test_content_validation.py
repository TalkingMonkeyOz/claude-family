"""
Tests for the Content Validation Pipeline BPMN process.

Models the combined PreToolUse hooks for Write/Edit operations:
  - Governed File Check (BT581/F194): blocks direct edits to generated files
  - Context Injector (context_injector_hook.py): adds context
  - Standards Validator (standards_validator.py): validates content

Test scenarios:
  1. DB unavailable → allow (fail-open)
  2. No matching standards → allow (no validation needed)
  3. Validation passes → allow
  4. Validation fails, no fix suggestion → deny (block)
  5. Validation fails, can suggest fix → ask (middleware correction)
  6. Context rules loaded → context injected + validation passes
  7. Governed file inside deployed target → deny (use tool instead)
  8. Governed file + bypass → allow (emergency override)
  9. Pattern matches but outside deployed target → allow (FB331)
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

# Default data for all gateway variables (prevents NameError on non-taken paths)
_DEFAULT_DATA = {
    "has_file_path": True,
    "pattern_match": False,
    "inside_deployed_target": True,
    "bypass_governance": False,
    "correct_tool": "",
    "db_available": True,
    "has_context_rules": False,
    "has_matching_standards": False,
    "validation_passed": True,
    "can_suggest_fix": False,
}


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    data = dict(_DEFAULT_DATA)
    if initial_data:
        data.update(initial_data)
    start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
    assert start_tasks, "Could not find BPMN start event"
    start_tasks[0].data.update(data)
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
            "has_context_rules": True,
            "has_matching_standards": True,
            "validation_passed": True,
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


class TestGovernedFileDenied:
    """Governed file (CLAUDE.md, settings.local.json) inside deployed target → deny."""

    def test_governed_file_blocked(self):
        wf = load_workflow({
            "pattern_match": True,
            "inside_deployed_target": True,
            "correct_tool": "update_claude_md()",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_governed_file" in names
        assert "check_deployed_target" in names
        assert "deny_governed" in names
        assert "end_governed_denied" in names
        # Should NOT reach DB or validation
        assert "connect_db" not in names
        assert "load_context_rules" not in names
        assert "validate_content" not in names


class TestGovernedFileBypass:
    """Governed file + bypass enabled → allow (emergency override)."""

    def test_governed_with_bypass_continues(self):
        wf = load_workflow({
            "pattern_match": True,
            "inside_deployed_target": True,
            "bypass_governance": True,
            "correct_tool": "update_claude_md()",
            "has_matching_standards": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_governed_file" in names
        assert "check_deployed_target" in names
        # Should continue past governance to normal pipeline
        assert "connect_db" in names
        assert "deny_governed" not in names
        assert "end_governed_denied" not in names


class TestNonGovernedFilePassesThrough:
    """Non-governed file skips governance check entirely."""

    def test_normal_file_not_affected(self):
        wf = load_workflow({
            "pattern_match": False,
            "has_matching_standards": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_governed_file" in names
        # Did not need to evaluate the path-scoping decision
        assert "check_deployed_target" not in names
        assert "deny_governed" not in names
        assert "connect_db" in names
        assert "allow_no_standards" in names


class TestPatternMatchOutsideDeployedTarget:
    """FB331: pattern matches but file is outside any registered workspace and not in /.claude/.
    Path-scoping must skip governance and let the operation proceed (e.g. fixture CLAUDE.md).
    """

    def test_outside_target_passes_through(self):
        wf = load_workflow({
            "pattern_match": True,
            "inside_deployed_target": False,
            "correct_tool": "update_claude_md()",
            "has_matching_standards": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "check_governed_file" in names
        assert "check_deployed_target" in names
        # Outside-target → governance skipped, normal pipeline runs
        assert "deny_governed" not in names
        assert "end_governed_denied" not in names
        assert "connect_db" in names
        assert "allow_no_standards" in names
