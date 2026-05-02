"""Structural tests for the Agent Finding Routing BPMN process (F224).

Severity-routed downstream of any agent run / health check that emits
structured findings. Called as a sub-process from
task_queue_lifecycle (success path) and queue_health_monitoring (L2 breach).

Locks asserted (per task-queue-design/full-design-2026-05-02 workfile,
section "Failure handling - locked", routing matrix):
  info     -> log only (output_text + result jsonb)
  warning  -> channel-messaging only
  high     -> claude.feedback only + linkage to task_queue
  critical -> BOTH feedback + send_message + linkage
  - Highest-severity finding wins for surfaced_as_feedback_id linkage
  - Loop iterates over the findings list; advance_index + more_findings_gw
"""

import os
from pathlib import Path

from SpiffWorkflow.bpmn.parser import BpmnParser


BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "processes",
        "infrastructure",
        "agent_finding_routing.bpmn",
    )
)
PROCESS_ID = "agent_finding_routing"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_spec():
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    return parser.get_spec(PROCESS_ID)


def parse_xml():
    import xml.etree.ElementTree as ET

    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
    tree = ET.parse(BPMN_FILE)
    proc = tree.getroot().find(f"bpmn:process[@id='{PROCESS_ID}']", ns)
    assert proc is not None
    return proc, ns


def element_ids_by_tag(tag):
    proc, ns = parse_xml()
    return {e.get("id") for e in proc.findall(f"bpmn:{tag}", ns)}


def flows():
    proc, ns = parse_xml()
    return [
        {
            "id": f.get("id"),
            "from": f.get("sourceRef"),
            "to": f.get("targetRef"),
            "condition": (f.findtext("bpmn:conditionExpression", default=None, namespaces=ns) or "").strip() or None,
        }
        for f in proc.findall("bpmn:sequenceFlow", ns)
    ]


# ---------------------------------------------------------------------------
# 1. Parse + structure
# ---------------------------------------------------------------------------

class TestParse:
    def test_bpmn_file_exists(self):
        assert Path(BPMN_FILE).exists()

    def test_process_parses(self):
        spec = load_spec()
        assert spec is not None
        assert spec.name == PROCESS_ID


# ---------------------------------------------------------------------------
# 2. Required elements
# ---------------------------------------------------------------------------

REQUIRED_TASKS = {
    "validate_findings",
    "pick_finding",
    "log_only",
    "send_warning_message",
    "create_high_feedback",
    "link_high_feedback_to_task",
    "create_critical_feedback",
    "send_critical_message",
    "link_critical_feedback_to_task",
    "advance_index",
    "summarize",
}

REQUIRED_GATEWAYS = {
    "has_findings_gw",
    "severity_gw",
    "more_findings_gw",
}

REQUIRED_END_EVENTS = {
    "end_no_findings",
    "end_routed",
}


class TestRequiredElements:
    def test_required_tasks_present(self):
        present = element_ids_by_tag("scriptTask")
        missing = REQUIRED_TASKS - present
        assert not missing, f"Missing tasks: {missing}"

    def test_required_gateways_present(self):
        present = element_ids_by_tag("exclusiveGateway")
        missing = REQUIRED_GATEWAYS - present
        assert not missing, f"Missing gateways: {missing}"

    def test_required_ends_present(self):
        present = element_ids_by_tag("endEvent")
        missing = REQUIRED_END_EVENTS - present
        assert not missing, f"Missing end events: {missing}"


# ---------------------------------------------------------------------------
# 3. Severity gateway has 4 branches matching the routing matrix
# ---------------------------------------------------------------------------

class TestSeverityRouting:
    def test_severity_gw_has_four_branches(self):
        outs = [f for f in flows() if f["from"] == "severity_gw"]
        assert len(outs) == 4

    def test_severity_targets(self):
        outs = [f for f in flows() if f["from"] == "severity_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {
            "log_only",
            "send_warning_message",
            "create_high_feedback",
            "create_critical_feedback",
        }

    def test_each_branch_has_severity_condition(self):
        outs = [f for f in flows() if f["from"] == "severity_gw"]
        conds = " ".join((f["condition"] or "") for f in outs)
        for sev in ("info", "warning", "high", "critical"):
            assert sev in conds, f"Severity {sev!r} missing from gateway conditions"


# ---------------------------------------------------------------------------
# 4. INFO path: log only -> advance (no message, no feedback)
# ---------------------------------------------------------------------------

class TestInfoPath:
    def test_info_routes_to_log_only(self):
        outs = [f for f in flows() if f["from"] == "severity_gw" and f["to"] == "log_only"]
        assert len(outs) == 1
        assert "info" in (outs[0]["condition"] or "")

    def test_log_only_advances_loop(self):
        outs = [f for f in flows() if f["from"] == "log_only"]
        assert outs[0]["to"] == "advance_index"


# ---------------------------------------------------------------------------
# 5. WARNING path: message only -> advance (no feedback)
# ---------------------------------------------------------------------------

class TestWarningPath:
    def test_warning_routes_to_message(self):
        outs = [f for f in flows() if f["from"] == "severity_gw" and f["to"] == "send_warning_message"]
        assert len(outs) == 1
        assert "warning" in (outs[0]["condition"] or "")

    def test_warning_advances_directly(self):
        outs = [f for f in flows() if f["from"] == "send_warning_message"]
        assert outs[0]["to"] == "advance_index"


# ---------------------------------------------------------------------------
# 6. HIGH path: feedback + linkage, no message
# ---------------------------------------------------------------------------

class TestHighPath:
    def test_high_routes_to_feedback(self):
        outs = [f for f in flows() if f["from"] == "severity_gw" and f["to"] == "create_high_feedback"]
        assert len(outs) == 1

    def test_high_creates_then_links(self):
        outs = [f for f in flows() if f["from"] == "create_high_feedback"]
        assert outs[0]["to"] == "link_high_feedback_to_task"
        outs = [f for f in flows() if f["from"] == "link_high_feedback_to_task"]
        assert outs[0]["to"] == "advance_index"

    def test_high_path_does_not_send_message(self):
        """high path must not flow into send_warning_message or send_critical_message."""
        msg_targets = {"send_warning_message", "send_critical_message"}
        # Every direct successor of create_high_feedback / link_high_feedback_to_task
        # must be outside msg_targets.
        for src in ("create_high_feedback", "link_high_feedback_to_task"):
            outs = [f for f in flows() if f["from"] == src]
            for f in outs:
                assert f["to"] not in msg_targets, f"high path reaches {f['to']}"


# ---------------------------------------------------------------------------
# 7. CRITICAL path: feedback + message + linkage
# ---------------------------------------------------------------------------

class TestCriticalPath:
    def test_critical_routes_to_feedback(self):
        outs = [f for f in flows() if f["from"] == "severity_gw" and f["to"] == "create_critical_feedback"]
        assert len(outs) == 1

    def test_critical_full_chain(self):
        outs = [f for f in flows() if f["from"] == "create_critical_feedback"]
        assert outs[0]["to"] == "send_critical_message"
        outs = [f for f in flows() if f["from"] == "send_critical_message"]
        assert outs[0]["to"] == "link_critical_feedback_to_task"
        outs = [f for f in flows() if f["from"] == "link_critical_feedback_to_task"]
        assert outs[0]["to"] == "advance_index"


# ---------------------------------------------------------------------------
# 8. Loop semantics
# ---------------------------------------------------------------------------

class TestLoop:
    def test_pick_finding_has_two_inputs(self):
        """pick_finding entered from the has_findings yes-edge AND the loop tail."""
        ins = [f for f in flows() if f["to"] == "pick_finding"]
        sources = {f["from"] for f in ins}
        assert sources == {"has_findings_gw", "more_findings_gw"}

    def test_more_findings_branches(self):
        outs = [f for f in flows() if f["from"] == "more_findings_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"pick_finding", "summarize"}

    def test_advance_increments_into_more_gw(self):
        outs = [f for f in flows() if f["from"] == "advance_index"]
        assert outs[0]["to"] == "more_findings_gw"

    def test_summarize_terminates(self):
        outs = [f for f in flows() if f["from"] == "summarize"]
        assert outs[0]["to"] == "end_routed"


# ---------------------------------------------------------------------------
# 9. Empty findings short-circuit
# ---------------------------------------------------------------------------

class TestEmptyFindings:
    def test_no_findings_skips_loop(self):
        outs = [f for f in flows() if f["from"] == "has_findings_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"pick_finding", "end_no_findings"}


# ---------------------------------------------------------------------------
# 10. Actor tags follow convention
# ---------------------------------------------------------------------------

class TestActorTags:
    def test_actor_tags_used(self):
        proc, ns = parse_xml()
        tasks = (
            proc.findall("bpmn:scriptTask", ns)
            + proc.findall("bpmn:userTask", ns)
            + proc.findall("bpmn:serviceTask", ns)
        )
        for t in tasks:
            name = t.get("name") or ""
            assert name.startswith("["), f"Task {t.get('id')} missing actor tag: {name!r}"

    def test_expected_actors_present(self):
        proc, ns = parse_xml()
        names = " ".join((t.get("name") or "") for t in proc.iter() if t.get("name"))
        assert "[MCP]" in names
        assert "[HOOK]" in names
        assert "[DB]" in names
