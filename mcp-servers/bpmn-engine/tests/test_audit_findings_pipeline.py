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
"""

import os
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
