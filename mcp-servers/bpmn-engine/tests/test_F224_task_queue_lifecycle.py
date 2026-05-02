"""Structural tests for the Task Queue Lifecycle BPMN process (F224).

These tests validate the BPMN model's structure (elements, gateways, flows,
condition wiring) - not runtime execution. The model captures design-time
locks for the local task queue + worker daemon (PG-backed).

Locks asserted (per task-queue-design/full-design-2026-05-02 workfile):
  - Idempotency-checked enqueue with dedup short-circuit
  - SKIP LOCKED + max_concurrent_runs claim with paused-template skip
  - Lease + heartbeat thread before payload execution
  - 4-way result gateway: success / transient / permanent / lease_expired
  - Retry path with exponential backoff (attempts < max_attempts)
  - Dead-letter sticky-until-triaged
  - Reaper re-claim only for idempotent templates
  - Circuit-breaker evaluated on every failure path
  - Tier-2 surfacing on breaker trip (feedback + message)
  - Resolve dead_letter user action (4 resolutions: fixed/wont_fix/rerun/superseded)
  - Sub-process call to agent_finding_routing on success
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
        "task_queue_lifecycle.bpmn",
    )
)
PROCESS_ID = "L2_task_queue_lifecycle"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_spec():
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    return parser.get_spec(PROCESS_ID)


def collect_elements():
    """Return ((task_specs_by_name)) the parsed task names. Spiff stores tasks
    by their BPMN id, so we just iterate task_specs."""
    spec = load_spec()
    return spec.task_specs


def parse_xml():
    """Lightweight DOM walk for shape assertions (avoids depending on Spiff
    internals for gateway / flow inspection)."""
    import xml.etree.ElementTree as ET

    ns = {"bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL"}
    tree = ET.parse(BPMN_FILE)
    proc = tree.getroot().find(f"bpmn:process[@id='{PROCESS_ID}']", ns)
    assert proc is not None, f"Process {PROCESS_ID} not found in {BPMN_FILE}"
    return proc, ns


def element_ids_by_tag(tag):
    proc, ns = parse_xml()
    return {e.get("id") for e in proc.findall(f"bpmn:{tag}", ns)}


def all_element_ids():
    proc, ns = parse_xml()
    ids = set()
    for tag in (
        "startEvent",
        "endEvent",
        "scriptTask",
        "userTask",
        "serviceTask",
        "exclusiveGateway",
        "parallelGateway",
        "callActivity",
    ):
        ids |= element_ids_by_tag(tag)
    return ids


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
# 1. File loads and process exists
# ---------------------------------------------------------------------------

class TestParse:
    def test_bpmn_file_exists(self):
        assert Path(BPMN_FILE).exists()

    def test_process_parses(self):
        spec = load_spec()
        assert spec is not None
        assert spec.name == PROCESS_ID


# ---------------------------------------------------------------------------
# 2. Required elements present
# ---------------------------------------------------------------------------

REQUIRED_SCRIPT_TASKS = {
    "enqueue_task",
    "return_existing_task",
    "claim_task",
    "skip_paused",
    "route_kind",
    "heartbeat_loop",
    "execute_task",
    "mark_completed",
    "reset_breaker_on_success",
    "classify_transient",
    "schedule_retry",
    "mark_dead_letter",
    "reaper_check_idempotent",
    "release_to_pending",
    "evaluate_breaker",
    "trip_breaker",
    "surface_breaker_feedback",
    "apply_resolution",
    "rerun_enqueue",
}

REQUIRED_GATEWAYS = {
    "idem_collision_gw",
    "template_paused_gw",
    "result_gw",
    "attempts_gw",
    "idempotent_gw",
    "breaker_check_merge",
    "trip_gw",
    "failure_end_merge",
    "resolution_gw",
}

REQUIRED_END_EVENTS = {
    "end_deduped",
    "end_idle",
    "end_completed",
    "end_failed",
    "end_resolved",
}


class TestRequiredElements:
    def test_start_event(self):
        assert "start" in element_ids_by_tag("startEvent")

    def test_required_script_tasks_present(self):
        present = element_ids_by_tag("scriptTask")
        missing = REQUIRED_SCRIPT_TASKS - present
        assert not missing, f"Missing script tasks: {missing}"

    def test_required_gateways_present(self):
        present = element_ids_by_tag("exclusiveGateway")
        missing = REQUIRED_GATEWAYS - present
        assert not missing, f"Missing gateways: {missing}"

    def test_required_end_events_present(self):
        present = element_ids_by_tag("endEvent")
        missing = REQUIRED_END_EVENTS - present
        assert not missing, f"Missing end events: {missing}"

    def test_user_triage_task(self):
        """Dead-letter triage is human-in-the-loop -> userTask."""
        assert "user_triage" in element_ids_by_tag("userTask")

    def test_route_findings_call_activity(self):
        """Successful completion calls out to agent_finding_routing."""
        proc, ns = parse_xml()
        ca = proc.findall("bpmn:callActivity", ns)
        called = {(e.get("id"), e.get("calledElement")) for e in ca}
        assert ("route_findings", "agent_finding_routing") in called


# ---------------------------------------------------------------------------
# 3. Result gateway has 4 outputs (success / transient / permanent / lease)
# ---------------------------------------------------------------------------

class TestResultGateway:
    def test_four_branches(self):
        outs = [f for f in flows() if f["from"] == "result_gw"]
        assert len(outs) == 4, f"result_gw must have 4 branches, got {len(outs)}"

    def test_branches_cover_all_kinds(self):
        outs = [f for f in flows() if f["from"] == "result_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {
            "mark_completed",
            "classify_transient",
            "mark_dead_letter",
            "reaper_check_idempotent",
        }

    def test_success_routes_to_findings_then_breaker_reset(self):
        fl = {f["id"]: f for f in flows()}
        assert fl["flow_completed_to_route_findings"]["from"] == "mark_completed"
        assert fl["flow_completed_to_route_findings"]["to"] == "route_findings"
        assert fl["flow_findings_to_breaker_reset"]["to"] == "reset_breaker_on_success"


# ---------------------------------------------------------------------------
# 4. Retry path: attempts gateway -> retry OR dead_letter
# ---------------------------------------------------------------------------

class TestRetryPath:
    def test_attempts_gw_branches(self):
        outs = [f for f in flows() if f["from"] == "attempts_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"schedule_retry", "mark_dead_letter"}

    def test_remaining_attempts_condition(self):
        outs = [f for f in flows() if f["from"] == "attempts_gw" and f["to"] == "schedule_retry"]
        assert len(outs) == 1
        assert "attempts" in (outs[0]["condition"] or "")
        assert "max_attempts" in (outs[0]["condition"] or "")

    def test_retry_feeds_breaker_check(self):
        outs = [f for f in flows() if f["from"] == "schedule_retry"]
        assert len(outs) == 1
        assert outs[0]["to"] == "breaker_check_merge"


# ---------------------------------------------------------------------------
# 5. Lease-expired path: idempotent re-claim or dead_letter
# ---------------------------------------------------------------------------

class TestLeaseExpiredPath:
    def test_reaper_routes_to_idempotent_gw(self):
        outs = [f for f in flows() if f["from"] == "reaper_check_idempotent"]
        assert len(outs) == 1
        assert outs[0]["to"] == "idempotent_gw"

    def test_idempotent_branches(self):
        outs = [f for f in flows() if f["from"] == "idempotent_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"release_to_pending", "mark_dead_letter"}

    def test_release_feeds_breaker_check(self):
        outs = [f for f in flows() if f["from"] == "release_to_pending"]
        assert outs[0]["to"] == "breaker_check_merge"


# ---------------------------------------------------------------------------
# 6. Circuit-breaker funnel: all 3 failure tributaries hit breaker_check_merge
# ---------------------------------------------------------------------------

class TestCircuitBreakerFunnel:
    def test_all_failure_paths_converge_on_breaker(self):
        ins = [f for f in flows() if f["to"] == "breaker_check_merge"]
        sources = {f["from"] for f in ins}
        assert sources == {"schedule_retry", "mark_dead_letter", "release_to_pending"}, (
            f"breaker_check_merge inputs wrong: {sources}"
        )

    def test_breaker_evaluates_then_trip_gw(self):
        outs = [f for f in flows() if f["from"] == "breaker_check_merge"]
        assert outs[0]["to"] == "evaluate_breaker"
        outs = [f for f in flows() if f["from"] == "evaluate_breaker"]
        assert outs[0]["to"] == "trip_gw"

    def test_trip_gw_branches(self):
        outs = [f for f in flows() if f["from"] == "trip_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"trip_breaker", "failure_end_merge"}

    def test_trip_path_surfaces_critical_feedback(self):
        outs = [f for f in flows() if f["from"] == "trip_breaker"]
        assert outs[0]["to"] == "surface_breaker_feedback"
        outs = [f for f in flows() if f["from"] == "surface_breaker_feedback"]
        assert outs[0]["to"] == "failure_end_merge"


# ---------------------------------------------------------------------------
# 7. Idempotency dedup short-circuit
# ---------------------------------------------------------------------------

class TestIdempotencyDedup:
    def test_idem_collision_branches(self):
        outs = [f for f in flows() if f["from"] == "idem_collision_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"return_existing_task", "claim_task"}

    def test_dup_path_terminates_at_end_deduped(self):
        outs = [f for f in flows() if f["from"] == "return_existing_task"]
        assert outs[0]["to"] == "end_deduped"


# ---------------------------------------------------------------------------
# 8. Paused-template skip path
# ---------------------------------------------------------------------------

class TestPausedTemplateSkip:
    def test_paused_branches(self):
        outs = [f for f in flows() if f["from"] == "template_paused_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"skip_paused", "route_kind"}

    def test_skip_terminates_at_idle(self):
        outs = [f for f in flows() if f["from"] == "skip_paused"]
        assert outs[0]["to"] == "end_idle"


# ---------------------------------------------------------------------------
# 9. Resolution path: 4 resolutions, 3 -> apply, rerun -> enqueue
# ---------------------------------------------------------------------------

class TestResolutionPath:
    def test_resolution_gw_has_four_branches(self):
        outs = [f for f in flows() if f["from"] == "resolution_gw"]
        assert len(outs) == 4

    def test_three_resolutions_target_apply(self):
        outs = [f for f in flows() if f["from"] == "resolution_gw" and f["to"] == "apply_resolution"]
        conds = {f["condition"] for f in outs}
        assert any("fixed" in (c or "") for c in conds)
        assert any("wont_fix" in (c or "") for c in conds)
        assert any("superseded" in (c or "") for c in conds)

    def test_rerun_targets_enqueue(self):
        outs = [f for f in flows() if f["from"] == "resolution_gw" and f["to"] == "rerun_enqueue"]
        assert len(outs) == 1
        assert "rerun" in (outs[0]["condition"] or "")

    def test_user_triage_feeds_resolution(self):
        outs = [f for f in flows() if f["from"] == "user_triage"]
        assert outs[0]["to"] == "resolution_gw"


# ---------------------------------------------------------------------------
# 10. Heartbeat present on the run path
# ---------------------------------------------------------------------------

class TestHeartbeat:
    def test_heartbeat_runs_before_execute(self):
        outs = [f for f in flows() if f["from"] == "heartbeat_loop"]
        assert outs[0]["to"] == "execute_task"

    def test_route_kind_runs_before_heartbeat(self):
        outs = [f for f in flows() if f["from"] == "route_kind"]
        assert outs[0]["to"] == "heartbeat_loop"


# ---------------------------------------------------------------------------
# 11. Element naming convention (actor tags)
# ---------------------------------------------------------------------------

class TestActorTags:
    def test_actor_tags_used(self):
        """Every script/user task name should start with [ACTOR]."""
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
        names = [t.get("name") or "" for t in proc.iter() if t.get("name")]
        joined = " ".join(names)
        assert "[DAEMON]" in joined
        assert "[DB]" in joined
        assert "[CLAUDE]" in joined
