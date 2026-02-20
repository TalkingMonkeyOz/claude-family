#!/usr/bin/env python3
"""
BPMN Engine MCP Server

Provides tools for discovering, inspecting, validating, and navigating
executable BPMN process definitions using SpiffWorkflow.

Process files are loaded from PROCESSES_DIR (default: processes/ relative to
this file). Override with BPMN_PROCESSES_DIR environment variable.

Author: Claude Family
Created: 2026-02-20
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# ============================================================================
# FastMCP Setup
# ============================================================================

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("ERROR: mcp package not installed. Run: pip install mcp", file=sys.stderr)
    sys.exit(1)

mcp = FastMCP(
    "bpmn-engine",
    instructions=(
        "BPMN process engine for executable, testable process definitions. "
        "Use list_processes to discover available processes, get_process for overview, "
        "get_subprocess for detail, validate_process to run tests."
    ),
)

# ============================================================================
# Configuration
# ============================================================================

_SERVER_DIR = Path(__file__).parent

def get_processes_dir() -> Path:
    """Return the processes directory, honouring the env-var override."""
    env_override = os.environ.get("BPMN_PROCESSES_DIR")
    if env_override:
        return Path(env_override)
    return _SERVER_DIR / "processes"


def get_tests_dir() -> Path:
    """Return the tests directory (always next to server.py)."""
    return _SERVER_DIR / "tests"


# ============================================================================
# BPMN XML helpers
# ============================================================================

BPMN_NS = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMN_TAG = f"{{{BPMN_NS}}}"

# Local tag names we care about
ELEMENT_TAGS = {
    f"{BPMN_TAG}startEvent": "startEvent",
    f"{BPMN_TAG}endEvent": "endEvent",
    f"{BPMN_TAG}userTask": "userTask",
    f"{BPMN_TAG}scriptTask": "scriptTask",
    f"{BPMN_TAG}serviceTask": "serviceTask",
    f"{BPMN_TAG}task": "task",
    f"{BPMN_TAG}exclusiveGateway": "exclusiveGateway",
    f"{BPMN_TAG}inclusiveGateway": "inclusiveGateway",
    f"{BPMN_TAG}parallelGateway": "parallelGateway",
    f"{BPMN_TAG}callActivity": "callActivity",
    f"{BPMN_TAG}subProcess": "subProcess",
    f"{BPMN_TAG}sequenceFlow": "sequenceFlow",
}


def _parse_xml(bpmn_path: Path):
    """Parse a BPMN file with lxml and return the root element."""
    from lxml import etree  # noqa: PLC0415 (late import keeps startup fast)
    return etree.parse(str(bpmn_path)).getroot()


def _extract_process_elements(process_el) -> tuple[list, list]:
    """
    Walk a <bpmn:process> element and return (elements, flows).

    elements: [{id, type, name}]
    flows:    [{id, from, to, condition}]
    """
    elements = []
    flows = []

    for child in process_el:
        tag = child.tag
        if tag not in ELEMENT_TAGS:
            continue

        el_type = ELEMENT_TAGS[tag]
        el_id = child.get("id", "")
        el_name = child.get("name", el_id)

        if el_type == "sequenceFlow":
            condition_el = child.find(f"{BPMN_TAG}conditionExpression")
            flows.append({
                "id": el_id,
                "from": child.get("sourceRef", ""),
                "to": child.get("targetRef", ""),
                "condition": condition_el.text.strip() if condition_el is not None and condition_el.text else None,
            })
        else:
            elements.append({"id": el_id, "type": el_type, "name": el_name})

    return elements, flows


def _find_bpmn_file(process_id: str) -> Optional[Path]:
    """
    Locate the .bpmn file for a given process_id.

    Checks:
      1. <process_id>.bpmn in the processes directory
      2. Any .bpmn file whose <bpmn:process id="..."> matches process_id
    """
    processes_dir = get_processes_dir()
    if not processes_dir.exists():
        return None

    # Fast path: conventional filename
    candidate = processes_dir / f"{process_id}.bpmn"
    if candidate.exists():
        return candidate

    # Slow path: scan all BPMN files for a matching process id
    for bpmn_file in processes_dir.glob("*.bpmn"):
        try:
            root = _parse_xml(bpmn_file)
            for process_el in root.iter(f"{BPMN_TAG}process"):
                if process_el.get("id") == process_id:
                    return bpmn_file
        except Exception:
            continue

    return None


# ============================================================================
# SpiffWorkflow helpers
# ============================================================================

def _load_workflow(bpmn_path: Path, process_id: str):
    """
    Parse the BPMN and return an initialised BpmnWorkflow.
    Raises ImportError if SpiffWorkflow is not installed.
    Raises RuntimeError (or parser errors) for malformed BPMN.
    """
    from SpiffWorkflow.bpmn.parser import BpmnParser  # noqa: PLC0415
    from SpiffWorkflow.bpmn.workflow import BpmnWorkflow  # noqa: PLC0415

    parser = BpmnParser()
    parser.add_bpmn_file(str(bpmn_path))
    spec = parser.get_spec(process_id)
    workflow = BpmnWorkflow(spec)
    workflow.do_engine_steps()
    return workflow


# ============================================================================
# Tool 1: list_processes
# ============================================================================

@mcp.tool()
def list_processes() -> dict:
    """List all available BPMN processes in the processes directory.

    Use when: you want to discover what processes are available.
    Returns: {processes: [{file, process_id, name}]}
    """
    try:
        processes_dir = get_processes_dir()
        if not processes_dir.exists():
            return {
                "success": True,
                "processes": [],
                "processes_dir": str(processes_dir),
                "message": f"Processes directory does not exist: {processes_dir}",
            }

        from lxml import etree  # noqa: PLC0415

        results = []
        for bpmn_file in sorted(processes_dir.glob("*.bpmn")):
            try:
                root = etree.parse(str(bpmn_file)).getroot()
                for process_el in root.iter(f"{BPMN_TAG}process"):
                    results.append({
                        "file": bpmn_file.name,
                        "process_id": process_el.get("id", bpmn_file.stem),
                        "name": process_el.get("name", bpmn_file.stem),
                    })
            except Exception as parse_err:
                results.append({
                    "file": bpmn_file.name,
                    "process_id": None,
                    "name": None,
                    "parse_error": str(parse_err),
                })

        return {
            "success": True,
            "processes_dir": str(processes_dir),
            "count": len(results),
            "processes": results,
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ============================================================================
# Tool 2: get_process
# ============================================================================

@mcp.tool()
def get_process(process_id: str) -> dict:
    """Get a human-readable overview of a BPMN process.

    Use when: you want to understand the structure of a specific process.
    Returns: {process_id, name, elements, flows, subprocesses}
      - elements: [{id, type, name}] — all tasks, events, and gateways
      - flows: [{id, from, to, condition}] — sequence flows
      - subprocesses: [str] — IDs of referenced call activities / sub-processes
    """
    try:
        bpmn_path = _find_bpmn_file(process_id)
        if bpmn_path is None:
            return {
                "success": False,
                "error": f"Process '{process_id}' not found in {get_processes_dir()}",
            }

        root = _parse_xml(bpmn_path)

        # Locate the specific process element
        target_process = None
        for process_el in root.iter(f"{BPMN_TAG}process"):
            if process_el.get("id") == process_id:
                target_process = process_el
                break

        if target_process is None:
            return {
                "success": False,
                "error": f"Process id '{process_id}' not found inside {bpmn_path.name}",
            }

        elements, flows = _extract_process_elements(target_process)

        # Collect call activity / subprocess references
        subprocesses = []
        for el in elements:
            if el["type"] in ("callActivity", "subProcess"):
                subprocesses.append(el["id"])

        return {
            "success": True,
            "process_id": process_id,
            "name": target_process.get("name", process_id),
            "file": bpmn_path.name,
            "element_count": len(elements),
            "flow_count": len(flows),
            "elements": elements,
            "flows": flows,
            "subprocesses": subprocesses,
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ============================================================================
# Tool 3: get_subprocess
# ============================================================================

@mcp.tool()
def get_subprocess(process_id: str, element_id: str) -> dict:
    """Zoom into a specific element of a BPMN process.

    Use when: you want details about a particular task, gateway, or subprocess.
    Returns: {element_id, type, name, details, incoming_flows, outgoing_flows}
      - details: script content for scriptTask, called element for callActivity, etc.
      - incoming_flows / outgoing_flows: sequence flow IDs + conditions
    """
    try:
        bpmn_path = _find_bpmn_file(process_id)
        if bpmn_path is None:
            return {
                "success": False,
                "error": f"Process '{process_id}' not found in {get_processes_dir()}",
            }

        root = _parse_xml(bpmn_path)

        # Locate the process element
        target_process = None
        for process_el in root.iter(f"{BPMN_TAG}process"):
            if process_el.get("id") == process_id:
                target_process = process_el
                break

        if target_process is None:
            return {
                "success": False,
                "error": f"Process '{process_id}' not found inside {bpmn_path.name}",
            }

        # Build a flow lookup: source/target → flow info
        _, all_flows = _extract_process_elements(target_process)
        incoming_map: dict[str, list] = {}
        outgoing_map: dict[str, list] = {}
        for flow in all_flows:
            outgoing_map.setdefault(flow["from"], []).append(flow)
            incoming_map.setdefault(flow["to"], []).append(flow)

        # Locate the element
        target_el = None
        target_type = None
        for child in target_process:
            if child.get("id") == element_id:
                target_el = child
                target_type = ELEMENT_TAGS.get(child.tag, child.tag)
                break

        if target_el is None:
            # Also search inside subProcesses
            for sp in target_process.iter(f"{BPMN_TAG}subProcess"):
                for child in sp:
                    if child.get("id") == element_id:
                        target_el = child
                        target_type = ELEMENT_TAGS.get(child.tag, child.tag)
                        break
                if target_el is not None:
                    break

        if target_el is None:
            return {
                "success": False,
                "error": f"Element '{element_id}' not found in process '{process_id}'",
            }

        # Build details dict based on element type
        details: dict = {}

        if target_type == "scriptTask":
            script_el = target_el.find(f"{BPMN_TAG}script")
            details["script"] = script_el.text.strip() if script_el is not None and script_el.text else ""
            details["scriptFormat"] = target_el.get("scriptFormat", "")

        elif target_type == "callActivity":
            details["calledElement"] = target_el.get("calledElement", "")

        elif target_type == "subProcess":
            # Return the internal structure of the subprocess
            sub_elements, sub_flows = _extract_process_elements(target_el)
            details["internal_elements"] = sub_elements
            details["internal_flows"] = sub_flows

        elif target_type in ("exclusiveGateway", "inclusiveGateway", "parallelGateway"):
            details["gatewayDirection"] = target_el.get("gatewayDirection", "unspecified")
            default_flow = target_el.get("default")
            if default_flow:
                details["defaultFlow"] = default_flow

        return {
            "success": True,
            "element_id": element_id,
            "type": target_type,
            "name": target_el.get("name", element_id),
            "details": details,
            "incoming_flows": incoming_map.get(element_id, []),
            "outgoing_flows": outgoing_map.get(element_id, []),
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ============================================================================
# Tool 4: validate_process
# ============================================================================

@mcp.tool()
def validate_process(process_id: str) -> dict:
    """Validate a BPMN process: parse check + optional pytest run.

    Use when: you want to confirm a process is well-formed and its tests pass.
    Returns: {process_id, parse_valid, parse_errors, tests_found,
               tests_passed, tests_failed, test_output}
    """
    result: dict = {
        "process_id": process_id,
        "parse_valid": False,
        "parse_errors": [],
        "tests_found": False,
        "tests_passed": 0,
        "tests_failed": 0,
        "test_output": "",
    }

    # --- Level 1: Parse validation ----------------------------------------
    bpmn_path = _find_bpmn_file(process_id)
    if bpmn_path is None:
        result["parse_errors"].append(
            f"Process '{process_id}' not found in {get_processes_dir()}"
        )
        return {"success": True, **result}

    try:
        from SpiffWorkflow.bpmn.parser import BpmnParser  # noqa: PLC0415
        parser = BpmnParser()
        parser.add_bpmn_file(str(bpmn_path))
        parser.get_spec(process_id)
        result["parse_valid"] = True
    except Exception as parse_exc:
        result["parse_errors"].append(str(parse_exc))
        return {"success": True, **result}

    # --- Level 2: Test validation -----------------------------------------
    test_file = get_tests_dir() / f"test_{process_id}.py"
    if not test_file.exists():
        result["tests_found"] = False
        return {"success": True, **result}

    result["tests_found"] = True

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = proc.stdout + proc.stderr
        result["test_output"] = output

        # Parse pytest summary line: "X passed, Y failed"
        for line in reversed(output.splitlines()):
            if "passed" in line or "failed" in line or "error" in line:
                import re
                passed_match = re.search(r"(\d+) passed", line)
                failed_match = re.search(r"(\d+) failed", line)
                error_match = re.search(r"(\d+) error", line)
                if passed_match:
                    result["tests_passed"] = int(passed_match.group(1))
                if failed_match:
                    result["tests_failed"] = int(failed_match.group(1))
                elif error_match:
                    result["tests_failed"] = int(error_match.group(1))
                break

    except subprocess.TimeoutExpired:
        result["test_output"] = "ERROR: pytest timed out after 60 seconds"
        result["tests_failed"] = -1
    except Exception as exc:
        result["test_output"] = f"ERROR running pytest: {exc}"
        result["tests_failed"] = -1

    return {"success": True, **result}


# ============================================================================
# Tool 5: get_current_step
# ============================================================================

@mcp.tool()
def get_current_step(
    process_id: str,
    completed_steps: list = [],
    data: dict = {},
) -> dict:
    """Determine what steps are available next given prior completed steps.

    Use when: you want GPS-style navigation — tell it where you are,
              it tells you where to go next.

    Args:
        process_id: The process to navigate.
        completed_steps: List of task spec names already done (in order).
                         Each entry can be a plain string (task name with no data)
                         or a dict {"name": str, "data": dict} to supply task data.
        data: Initial workflow data to seed before running.

    Returns: {process_id, current_tasks, is_completed, data}
      - current_tasks: [{id, name, type}] — READY user tasks
      - is_completed: bool — true if the workflow has reached an end event
      - data: current workflow data dict
    """
    try:
        from SpiffWorkflow.util.task import TaskState  # noqa: PLC0415

        bpmn_path = _find_bpmn_file(process_id)
        if bpmn_path is None:
            return {
                "success": False,
                "error": f"Process '{process_id}' not found in {get_processes_dir()}",
            }

        workflow = _load_workflow(bpmn_path, process_id)

        # Replay completed steps, merging global data into each step
        for step in completed_steps:
            if isinstance(step, dict):
                step_name = step.get("name", "")
                step_data = {**data, **step.get("data", {})}
            else:
                step_name = str(step)
                step_data = dict(data)  # global data applies to plain string steps

            ready_user_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
            matched = [t for t in ready_user_tasks if t.task_spec.name == step_name]

            if not matched:
                # Task may already be completed or name is wrong — skip gracefully
                continue

            task_obj = matched[0]
            if step_data:
                task_obj.data.update(step_data)
            task_obj.run()
            workflow.do_engine_steps()

        # Collect what's ready now
        ready_tasks = workflow.get_tasks(state=TaskState.READY, manual=True)
        current_tasks = [
            {
                "id": t.task_spec.name,
                "name": t.task_spec.description or t.task_spec.name,
                "type": type(t.task_spec).__name__,
            }
            for t in ready_tasks
        ]

        return {
            "success": True,
            "process_id": process_id,
            "current_tasks": current_tasks,
            "is_completed": workflow.is_completed(),
            "data": workflow.data if workflow.is_completed() else {},
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
