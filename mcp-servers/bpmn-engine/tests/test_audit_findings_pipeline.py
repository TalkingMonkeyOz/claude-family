"""
Tests for the Audit Findings Pipeline BPMN process.

Models how discoveries from systematic analysis become tracked work items.

Test scenarios:
  1. No findings → end_empty
  2. Single actionable finding needing planning → feature created + build tasks + linked
  3. Single actionable quick fix → feedback filed + linked
  4. Non-actionable finding → knowledge stored
  5. Mixed batch: 3 findings (feature + feedback + knowledge) → all processed
  6. Feature path increments features_created counter
  7. Feedback path increments feedback_filed counter
  8. Knowledge path increments knowledge_stored counter
  9. _classify_gap: classification rules match BPMN model
  10. _check_artifact_exists: 3 new artifact types handled
"""

import os
import sys
from pathlib import Path

import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState


BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "development", "audit_findings_pipeline.bpmn")
)
PROCESS_ID = "audit_findings_pipeline"


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

class TestNoFindings:
    """No findings → end_empty."""

    def test_empty_findings(self):
        wf = load_workflow({
            "has_findings": False,
            "finding_count": 0,
            "is_actionable": False,
            "needs_planning": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "end_empty" in names
        assert "pick_finding" not in names
        assert "classify_finding" not in names


class TestFeaturePath:
    """Actionable finding needing planning → feature + build tasks + linked."""

    def test_creates_feature_and_tasks(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 1,
            "is_actionable": True,
            "needs_planning": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "classify_finding" in names
        assert "create_feature" in names
        assert "create_build_tasks" in names
        assert "link_to_source" in names
        assert "build_summary" in names
        assert "end_tracked" in names
        assert "create_feedback" not in names
        assert "store_as_knowledge" not in names
        assert wf.data.get("features_created") == 1
        assert wf.data.get("feedback_filed") == 0
        assert wf.data.get("pipeline_complete") is True


class TestFeedbackPath:
    """Actionable quick fix → feedback filed + linked."""

    def test_creates_feedback(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 1,
            "is_actionable": True,
            "needs_planning": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "classify_feedback_type" in names
        assert "create_feedback" in names
        assert "link_to_source" in names
        assert "end_tracked" in names
        assert "create_feature" not in names
        assert "store_as_knowledge" not in names
        assert wf.data.get("feedback_filed") == 1
        assert wf.data.get("features_created") == 0


class TestKnowledgePath:
    """Non-actionable observation → knowledge stored."""

    def test_stores_knowledge(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 1,
            "is_actionable": False,
            "needs_planning": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "store_as_knowledge" in names
        assert "advance_loop" in names
        assert "end_tracked" in names
        assert "create_feature" not in names
        assert "create_feedback" not in names
        assert wf.data.get("knowledge_stored") == 1


class TestMixedBatch:
    """3 findings with different classifications → all processed correctly.

    Since SpiffWorkflow uses the same data namespace for the loop,
    we test with 3 findings where the classification flags stay constant.
    In reality, Claude would change is_actionable/needs_planning per finding.
    Here we test the loop counter mechanics with 3 feedback items.
    """

    def test_three_findings_loop(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 3,
            "is_actionable": True,
            "needs_planning": False,
        })

        assert wf.is_completed()
        assert wf.data.get("pipeline_complete") is True
        assert wf.data.get("current_index") == 3
        assert wf.data.get("feedback_filed") == 3


class TestFeatureCounter:
    """Feature path increments features_created correctly for 2 items."""

    def test_two_features(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 2,
            "is_actionable": True,
            "needs_planning": True,
        })

        assert wf.is_completed()
        assert wf.data.get("features_created") == 2
        assert wf.data.get("feedback_filed") == 0


class TestKnowledgeCounter:
    """Knowledge path increments knowledge_stored for 2 observations."""

    def test_two_observations(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 2,
            "is_actionable": False,
            "needs_planning": False,
        })

        assert wf.is_completed()
        assert wf.data.get("knowledge_stored") == 2
        assert wf.data.get("features_created") == 0
        assert wf.data.get("feedback_filed") == 0


class TestSummaryReport:
    """Pipeline builds summary report at end."""

    def test_summary_built(self):
        wf = load_workflow({
            "has_findings": True,
            "finding_count": 1,
            "is_actionable": True,
            "needs_planning": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)
        assert "build_summary" in names
        assert wf.data.get("pipeline_complete") is True


# ---------------------------------------------------------------------------
# Unit tests for _classify_gap and _check_artifact_exists
# ---------------------------------------------------------------------------

# Import from server module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from server import _classify_gap, _check_artifact_exists


class TestClassifyGap:
    """_classify_gap implements audit_findings_pipeline classification rules."""

    def test_hook_unmapped_is_improvement_high(self):
        gap = {"element_id": "run_hook", "element_name": "[HOOK] Run startup", "element_type": "scriptTask"}
        result = _classify_gap(gap)
        assert result is not None
        assert result["feedback_type"] == "improvement"
        assert result["priority"] == "high"

    def test_hook_missing_artifact_is_bug_high(self):
        gap = {
            "element_id": "run_hook",
            "element_name": "[HOOK] Run startup",
            "element_type": "scriptTask",
            "artifact_exists": False,
            "artifact_type": "hook_script",
            "artifact_details": "File: scripts/missing.py",
        }
        result = _classify_gap(gap)
        assert result is not None
        assert result["feedback_type"] == "bug"
        assert result["priority"] == "high"

    def test_db_unmapped_is_improvement_medium(self):
        gap = {"element_id": "query_db", "element_name": "[DB] Query sessions", "element_type": "serviceTask"}
        result = _classify_gap(gap)
        assert result is not None
        assert result["feedback_type"] == "improvement"
        assert result["priority"] == "medium"

    def test_mcp_unmapped_is_improvement_medium(self):
        gap = {"element_id": "call_tool", "element_name": "[MCP] Store knowledge", "element_type": "serviceTask"}
        result = _classify_gap(gap)
        assert result is not None
        assert result["feedback_type"] == "improvement"
        assert result["priority"] == "medium"

    def test_tool_unmapped_is_improvement_medium(self):
        gap = {"element_id": "use_tool", "element_name": "[TOOL] Validate input", "element_type": "serviceTask"}
        result = _classify_gap(gap)
        assert result is not None
        assert result["priority"] == "medium"

    def test_claude_element_skipped(self):
        gap = {"element_id": "decide", "element_name": "[CLAUDE] Decide next step", "element_type": "userTask"}
        result = _classify_gap(gap)
        assert result is None

    def test_core_element_skipped(self):
        gap = {"element_id": "core_init", "element_name": "[CORE] Initialize", "element_type": "task"}
        result = _classify_gap(gap)
        assert result is None

    def test_call_activity_skipped(self):
        gap = {"element_id": "sub_process", "element_name": "Run sub-process", "element_type": "callActivity"}
        result = _classify_gap(gap)
        assert result is None

    def test_other_unmapped_is_improvement_low(self):
        gap = {"element_id": "something", "element_name": "Do something", "element_type": "task"}
        result = _classify_gap(gap)
        assert result is not None
        assert result["feedback_type"] == "improvement"
        assert result["priority"] == "low"

    def test_title_contains_element_name(self):
        gap = {"element_id": "xyz", "element_name": "[HOOK] My hook", "element_type": "scriptTask"}
        result = _classify_gap(gap)
        assert "[HOOK] My hook" in result["title"]

    def test_description_contains_element_id(self):
        gap = {"element_id": "my_element_123", "element_name": "[DB] Query", "element_type": "serviceTask"}
        result = _classify_gap(gap)
        assert "my_element_123" in result["description"]


class TestCheckArtifactExists:
    """_check_artifact_exists handles all artifact types including 3 new ones."""

    def test_claude_behavior_always_exists(self):
        artifact = {"type": "claude_behavior", "description": "Claude decides"}
        result = _check_artifact_exists(artifact, Path("."))
        assert result["exists"] is True
        assert "Claude decides" in result["details"]

    def test_bpmn_call_activity_always_exists(self):
        artifact = {"type": "bpmn_call_activity", "calledElement": "L2_session_start"}
        result = _check_artifact_exists(artifact, Path("."))
        assert result["exists"] is True
        assert "CallActivity" in result["details"]
        assert "L2_session_start" in result["details"]

    def test_rule_file_exists(self, tmp_path):
        rule_file = tmp_path / "rules" / "test.md"
        rule_file.parent.mkdir(parents=True)
        rule_file.write_text("rule content")
        artifact = {"type": "rule_file", "file": "rules/test.md"}
        result = _check_artifact_exists(artifact, tmp_path)
        assert result["exists"] is True
        assert "Rule" in result["details"]

    def test_rule_file_missing(self, tmp_path):
        artifact = {"type": "rule_file", "file": "rules/nonexistent.md"}
        result = _check_artifact_exists(artifact, tmp_path)
        assert result["exists"] is False

    def test_mcp_tool_always_exists(self):
        artifact = {"type": "mcp_tool", "tool": "start_session"}
        result = _check_artifact_exists(artifact, Path("."))
        assert result["exists"] is True

    def test_hook_script_missing(self, tmp_path):
        artifact = {"type": "hook_script", "file": "scripts/nonexistent.py"}
        result = _check_artifact_exists(artifact, tmp_path)
        assert result["exists"] is False

    def test_unknown_type_defaults_false(self):
        artifact = {"type": "totally_unknown"}
        result = _check_artifact_exists(artifact, Path("."))
        assert result["exists"] is False
