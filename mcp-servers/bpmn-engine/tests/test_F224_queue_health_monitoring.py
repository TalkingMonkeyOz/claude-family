"""Structural tests for the Queue Health Monitoring BPMN process (F224).

The model is a single process with three monitoring tiers selected via the
`level` data input (L1 in-process / L2 scheduled / L3 monitor-the-monitor).

Locks asserted (per task-queue-design/full-design-2026-05-02 workfile,
section "Queue health monitoring"):
  - L1 SessionStart watchdog respawns dead worker daemon
  - L2 cron job runs 4 parallel metric checks every 15 minutes
  - L2 metrics: backlog_overflow, leaked_leases, dead_letter_spike, drain_stall
  - L2 routes breaches via agent_finding_routing call activity
  - L2 records run timestamp in scheduled_jobs.last_run_at
  - L3 SessionStart liveness check reads L2's last_run_at
  - L3 surfaces critical feedback if L2 stale, then re-arms job_runner
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
        "queue_health_monitoring.bpmn",
    )
)
PROCESS_ID = "L2_queue_health_monitoring"


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
# 2. Level dispatch gateway
# ---------------------------------------------------------------------------

class TestLevelGateway:
    def test_level_gw_present(self):
        assert "level_gw" in element_ids_by_tag("exclusiveGateway")

    def test_three_branches(self):
        outs = [f for f in flows() if f["from"] == "level_gw"]
        assert len(outs) == 3

    def test_branches_target_correct_entries(self):
        outs = {f["to"] for f in flows() if f["from"] == "level_gw"}
        assert outs == {"l1_resolve_pid", "l2_split", "l3_load_last_run"}

    def test_branch_conditions_use_level_var(self):
        conds = {f["condition"] for f in flows() if f["from"] == "level_gw"}
        levels_seen = set()
        for c in conds:
            if c and "L1" in c:
                levels_seen.add("L1")
            if c and "L2" in c:
                levels_seen.add("L2")
            if c and "L3" in c:
                levels_seen.add("L3")
        assert levels_seen == {"L1", "L2", "L3"}


# ---------------------------------------------------------------------------
# 3. L1 - in-process watchdog
# ---------------------------------------------------------------------------

class TestL1Watchdog:
    def test_l1_pipeline_present(self):
        scripts = element_ids_by_tag("scriptTask")
        assert {"l1_resolve_pid", "l1_check_alive", "l1_respawn"} <= scripts

    def test_l1_alive_gw_branches(self):
        outs = [f for f in flows() if f["from"] == "l1_alive_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"end_l1_alive", "l1_respawn"}

    def test_l1_respawn_terminates(self):
        outs = [f for f in flows() if f["from"] == "l1_respawn"]
        assert outs[0]["to"] == "end_l1_respawned"


# ---------------------------------------------------------------------------
# 4. L2 - scheduled health check (parallel metrics)
# ---------------------------------------------------------------------------

L2_METRIC_CHECKS = {
    "l2_check_backlog",
    "l2_check_leaks",
    "l2_check_dlq",
    "l2_check_drain",
}


class TestL2HealthCheck:
    def test_parallel_split_present(self):
        assert "l2_split" in element_ids_by_tag("parallelGateway")
        assert "l2_join" in element_ids_by_tag("parallelGateway")

    def test_split_fans_out_to_four_metrics(self):
        outs = {f["to"] for f in flows() if f["from"] == "l2_split"}
        assert outs == L2_METRIC_CHECKS

    def test_metrics_join_in_parallel(self):
        ins = {f["from"] for f in flows() if f["to"] == "l2_join"}
        assert ins == L2_METRIC_CHECKS

    def test_aggregate_then_breach_gateway(self):
        outs = [f for f in flows() if f["from"] == "l2_join"]
        assert outs[0]["to"] == "l2_aggregate"
        outs = [f for f in flows() if f["from"] == "l2_aggregate"]
        assert outs[0]["to"] == "l2_breach_gw"

    def test_breach_routes_to_finding_routing(self):
        outs = [f for f in flows() if f["from"] == "l2_breach_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"l2_route_findings", "l2_record_run"}

    def test_l2_calls_finding_routing(self):
        proc, ns = parse_xml()
        ca = proc.findall("bpmn:callActivity", ns)
        called = {(e.get("id"), e.get("calledElement")) for e in ca}
        assert ("l2_route_findings", "agent_finding_routing") in called

    def test_l2_records_last_run_at(self):
        outs = [f for f in flows() if f["from"] == "l2_record_run"]
        assert outs[0]["to"] == "end_l2_complete"


# ---------------------------------------------------------------------------
# 5. L3 - monitor-the-monitor
# ---------------------------------------------------------------------------

class TestL3Liveness:
    def test_l3_pipeline_present(self):
        scripts = element_ids_by_tag("scriptTask")
        assert {"l3_load_last_run", "l3_surface_dead_monitor", "l3_rearm_runner"} <= scripts

    def test_age_gw_branches(self):
        outs = [f for f in flows() if f["from"] == "l3_age_gw"]
        targets = {f["to"] for f in outs}
        assert targets == {"l3_surface_dead_monitor", "end_l3_fresh"}

    def test_stale_path_surfaces_then_rearms(self):
        outs = [f for f in flows() if f["from"] == "l3_surface_dead_monitor"]
        assert outs[0]["to"] == "l3_rearm_runner"
        outs = [f for f in flows() if f["from"] == "l3_rearm_runner"]
        assert outs[0]["to"] == "end_l3_rearmed"


# ---------------------------------------------------------------------------
# 6. End-event coverage (one per terminal state across 3 levels)
# ---------------------------------------------------------------------------

class TestEndEvents:
    def test_required_ends_present(self):
        ends = element_ids_by_tag("endEvent")
        required = {
            "end_l1_alive",
            "end_l1_respawned",
            "end_l2_complete",
            "end_l3_fresh",
            "end_l3_rearmed",
        }
        assert required <= ends


# ---------------------------------------------------------------------------
# 7. Actor tags follow convention
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
        assert "[HOOK]" in names
        assert "[DB]" in names
