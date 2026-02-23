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

_SERVER_DIR = Path(__file__).resolve().parent

def get_processes_dir() -> Path:
    """Return the processes directory, honouring the env-var override."""
    env_override = os.environ.get("BPMN_PROCESSES_DIR")
    if env_override:
        return Path(env_override)
    return _SERVER_DIR / "processes"


def get_tests_dir() -> Path:
    """Return the tests directory.

    Priority:
    1. BPMN_TESTS_DIR env var (explicit override)
    2. tests/ sibling to BPMN_PROCESSES_DIR (if overridden)
    3. tests/ next to server.py (default for claude-family)
    """
    env_override = os.environ.get("BPMN_TESTS_DIR")
    if env_override:
        return Path(env_override)
    # If processes dir is overridden, look for tests relative to it
    if os.environ.get("BPMN_PROCESSES_DIR"):
        candidate = Path(os.environ["BPMN_PROCESSES_DIR"]).parent / "tests"
        if candidate.exists():
            return candidate
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

    # Fast path: conventional filename (check root and subdirectories)
    candidate = processes_dir / f"{process_id}.bpmn"
    if candidate.exists():
        return candidate
    # Check subdirectories
    for sub_candidate in processes_dir.glob(f"**/{process_id}.bpmn"):
        return sub_candidate

    # Slow path: scan all BPMN files for a matching process id
    for bpmn_file in processes_dir.glob("**/*.bpmn"):
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

def _load_workflow(bpmn_path: Path, process_id: str, extra_bpmn_files: list = None):
    """
    Parse the BPMN and return an initialised BpmnWorkflow.
    Raises ImportError if SpiffWorkflow is not installed.
    Raises RuntimeError (or parser errors) for malformed BPMN.

    Args:
        bpmn_path: Path to the primary BPMN file.
        process_id: The process ID to load as the root spec.
        extra_bpmn_files: Optional list of additional BPMN file paths whose
                          processes can be resolved as subprocess specs (e.g.
                          L1 files when loading an L0 process).
    """
    from SpiffWorkflow.bpmn.parser import BpmnParser  # noqa: PLC0415
    from SpiffWorkflow.bpmn.workflow import BpmnWorkflow  # noqa: PLC0415

    parser = BpmnParser()
    parser.add_bpmn_file(str(bpmn_path))
    if extra_bpmn_files:
        for f in extra_bpmn_files:
            parser.add_bpmn_file(str(f))
    spec = parser.get_spec(process_id)
    subspecs = parser.get_subprocess_specs(process_id) if extra_bpmn_files else {}
    workflow = BpmnWorkflow(spec, subspecs)
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
        for bpmn_file in sorted(processes_dir.glob("**/*.bpmn")):
            try:
                root = etree.parse(str(bpmn_file)).getroot()
                for process_el in root.iter(f"{BPMN_TAG}process"):
                    # Include relative path from processes dir for subdirectory support
                    rel_path = bpmn_file.relative_to(processes_dir)
                    results.append({
                        "file": str(rel_path),
                        "process_id": process_el.get("id", bpmn_file.stem),
                        "name": process_el.get("name", bpmn_file.stem),
                        "category": rel_path.parent.name if rel_path.parent.name != "." else "root",
                    })
            except Exception as parse_err:
                rel_path = bpmn_file.relative_to(processes_dir)
                results.append({
                    "file": str(rel_path),
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
# Tool 6: get_dependency_tree
# ============================================================================


def _detect_level(process_id: str) -> str:
    """Return the hierarchy level string for a process_id based on its prefix."""
    if process_id.startswith("L0_"):
        return "L0"
    if process_id.startswith("L1_"):
        return "L1"
    return "L2"


def _collect_call_activities(process_id: str, called_by: Optional[str], visited: set, flat_list: list) -> None:
    """
    Recursively walk callActivity elements starting from process_id.

    Populates flat_list in-place with one entry per discovered process.
    Uses visited to prevent infinite recursion on cyclic references.
    """
    if process_id in visited:
        return
    visited.add(process_id)

    bpmn_path = _find_bpmn_file(process_id)
    if bpmn_path is None:
        return

    try:
        root = _parse_xml(bpmn_path)
    except Exception:
        return

    # Locate the process element for this process_id
    target_process = None
    for process_el in root.iter(f"{BPMN_TAG}process"):
        if process_el.get("id") == process_id:
            target_process = process_el
            break

    if target_process is None:
        return

    processes_dir = get_processes_dir()
    try:
        rel_file = str(bpmn_path.relative_to(processes_dir))
    except ValueError:
        rel_file = bpmn_path.name

    level = _detect_level(process_id)
    entry: dict = {
        "process_id": process_id,
        "name": target_process.get("name", process_id),
        "file": rel_file,
        "level": level,
    }
    if called_by is not None:
        entry["called_by"] = called_by

    flat_list.append(entry)

    # Find all callActivity children and recurse
    for child in target_process:
        if child.tag == f"{BPMN_TAG}callActivity":
            called_element = child.get("calledElement")
            if called_element:
                _collect_call_activities(called_element, process_id, visited, flat_list)


@mcp.tool()
def get_dependency_tree(process_id: str) -> dict:
    """Build a recursive dependency tree by walking callActivity elements.

    Use when: you want to understand how processes relate to each other
              across the L0 -> L1 -> L2 hierarchy.

    Returns: {success, root, tree, depth, total_processes}
      - root: the entry-point process {process_id, name, file, level}
      - tree: flat list of all dependent processes with called_by links
      - depth: maximum nesting depth discovered
      - total_processes: total count including root
    """
    try:
        bpmn_path = _find_bpmn_file(process_id)
        if bpmn_path is None:
            return {
                "success": False,
                "error": f"Process '{process_id}' not found in {get_processes_dir()}",
            }

        visited: set = set()
        flat_list: list = []

        # Walk the full tree starting from the root process
        _collect_call_activities(process_id, None, visited, flat_list)

        if not flat_list:
            return {
                "success": False,
                "error": f"No process element found for '{process_id}'",
            }

        # The root is the first entry (no called_by key)
        root_entry = flat_list[0]
        root = {k: v for k, v in root_entry.items() if k != "called_by"}
        tree = flat_list[1:]  # everything after the root

        # Calculate depth: BFS level counting via called_by chain
        depth_map: dict[str, int] = {process_id: 1}
        for entry in tree:
            parent = entry.get("called_by")
            parent_depth = depth_map.get(parent, 1)
            depth_map[entry["process_id"]] = parent_depth + 1
        max_depth = max(depth_map.values()) if depth_map else 1

        return {
            "success": True,
            "root": root,
            "tree": tree,
            "depth": max_depth,
            "total_processes": len(flat_list),
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ============================================================================
# Tool 7: search_processes
# ============================================================================


@mcp.tool()
def search_processes(query: str, actor: Optional[str] = None, level: Optional[str] = None) -> dict:
    """Search process elements by keyword across all BPMN files.

    Use when: you want to find which processes contain a particular task,
              actor, or keyword (e.g. "[HOOK]", "discipline", "spawn").

    Args:
        query:  Case-insensitive substring to match against element names,
                process names, and condition expressions.
        actor:  Optional actor filter (e.g. "[HOOK]", "[CLAUDE]", "[DB]").
                Matched as a case-insensitive substring of element names.
        level:  Optional hierarchy level filter: "L0", "L1", or "L2".
                Determined by the process_id prefix convention.

    Returns: {success, query, match_count, matches}
      - matches: list of {process_id, process_name, file, matching_elements}
      - matching_elements: [{id, type, name}] that satisfy all filters
    """
    try:
        processes_dir = get_processes_dir()
        if not processes_dir.exists():
            return {
                "success": True,
                "query": query,
                "match_count": 0,
                "matches": [],
            }

        from lxml import etree  # noqa: PLC0415

        query_lower = query.lower()
        actor_lower = actor.lower() if actor else None
        level_filter = level.upper() if level else None

        matches = []

        for bpmn_file in sorted(processes_dir.glob("**/*.bpmn")):
            try:
                root = etree.parse(str(bpmn_file)).getroot()
            except Exception:
                continue

            rel_path = bpmn_file.relative_to(processes_dir)

            for process_el in root.iter(f"{BPMN_TAG}process"):
                pid = process_el.get("id", "")
                pname = process_el.get("name", pid)

                # Apply level filter before scanning elements
                if level_filter is not None and _detect_level(pid) != level_filter:
                    continue

                elements, flows = _extract_process_elements(process_el)

                # Build a set of condition strings for flow matching
                condition_texts = {
                    f["condition"].lower()
                    for f in flows
                    if f.get("condition")
                }

                matching_elements = []
                for el in elements:
                    el_name = el["name"]
                    el_name_lower = el_name.lower()

                    # Check if the element name matches the query
                    name_matches_query = query_lower in el_name_lower
                    # Check if the process name matches the query
                    process_name_matches = query_lower in pname.lower()
                    # Check condition expressions
                    condition_matches = any(query_lower in c for c in condition_texts)

                    # At least one of name/process/condition must match the query
                    if not (name_matches_query or process_name_matches or condition_matches):
                        continue

                    # Apply actor filter: actor must appear in the element name
                    if actor_lower is not None and actor_lower not in el_name_lower:
                        continue

                    matching_elements.append({
                        "id": el["id"],
                        "type": el["type"],
                        "name": el_name,
                    })

                if matching_elements:
                    matches.append({
                        "process_id": pid,
                        "process_name": pname,
                        "file": str(rel_path),
                        "matching_elements": matching_elements,
                    })

        return {
            "success": True,
            "query": query,
            "match_count": sum(len(m["matching_elements"]) for m in matches),
            "matches": matches,
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ============================================================================
# Tool 8: check_alignment
# ============================================================================

# Known mappings: BPMN element name → code artifact
# These are manually curated to establish ground truth for validation.
_ARTIFACT_REGISTRY: dict[str, dict] = {
    # hook_chain.bpmn elements → actual hook scripts
    "check_session_changed": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Session ID comparison in RAG hook (FB141 fix)",
    },
    "reset_task_map": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Task map reset on session change",
    },
    "classify_prompt": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Action vs question classification for RAG gating",
    },
    "query_rag": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "hook_event": "UserPromptSubmit",
    },
    "query_skill_suggestions": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Skill content similarity search (FB138 fix)",
    },
    "inject_rag_context": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Injects RAG results + notepad + skills into context",
    },
    "check_discipline": {
        "type": "hook_script",
        "file": "scripts/task_discipline_hook.py",
        "hook_event": "PreToolUse",
    },
    "inject_tool_context": {
        "type": "hook_script",
        "file": "scripts/context_injector_hook.py",
        "hook_event": "PreToolUse",
    },
    "post_tool_sync": {
        "type": "hook_script",
        "file": "scripts/todo_sync_hook.py",
        "hook_event": "PostToolUse",
        "also": ["scripts/task_sync_hook.py", "scripts/mcp_usage_logger.py"],
    },
    "mark_blocked": {
        "type": "hook_output",
        "description": "task_discipline_hook returns permissionDecision=deny",
    },
    # Legacy alias for old BPMN models
    "rag_query": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "hook_event": "UserPromptSubmit",
    },
    "inject_context": {
        "type": "hook_script",
        "file": "scripts/context_injector_hook.py",
        "hook_event": "PreToolUse",
    },
    # session_lifecycle.bpmn elements → hook scripts
    "session_start": {
        "type": "hook_script",
        "file": "scripts/session_startup_hook_enhanced.py",
        "hook_event": "SessionStart",
    },
    "load_state": {
        "type": "hook_script",
        "file": "scripts/session_startup_hook_enhanced.py",
        "description": "Loads prior state during session startup",
    },
    "save_checkpoint": {
        "type": "hook_script",
        "file": "scripts/precompact_hook.py",
        "hook_event": "PreCompact",
    },
    "close_session": {
        "type": "hook_script",
        "file": "scripts/session_end_hook.py",
        "hook_event": "SessionEnd",
    },
    # session_continuation.bpmn elements
    "precompact_inject": {
        "type": "hook_script",
        "file": "scripts/precompact_hook.py",
        "hook_event": "PreCompact",
    },
    # task_lifecycle.bpmn elements → MCP tools + hooks
    "create_task": {
        "type": "mcp_tool",
        "tool": "TaskCreate",
        "description": "Claude Code built-in TaskCreate tool",
    },
    "sync_to_db": {
        "type": "hook_script",
        "file": "scripts/task_sync_hook.py",
        "hook_event": "PostToolUse(TaskCreate)",
    },
    "work_on_task": {
        "type": "mcp_tool",
        "tool": "start_work / complete_work",
        "description": "project-tools MCP workflow tools",
    },
    # feature_workflow.bpmn elements → MCP tools
    "create_feature": {
        "type": "mcp_tool",
        "tool": "create_feature",
        "description": "project-tools MCP tool",
    },
    "plan_feature": {
        "type": "mcp_tool",
        "tool": "advance_status(features, F*, planned)",
        "description": "WorkflowEngine state transition",
    },
    "run_tests": {
        "type": "command",
        "command": "pytest",
        "description": "Manual test execution",
    },
    "review_code": {
        "type": "agent",
        "agent": "reviewer-sonnet",
        "description": "Spawned via orchestrator.spawn_agent",
    },
    # L2_task_work_cycle.bpmn elements
    "decompose_prompt": {
        "type": "claude_behavior",
        "description": "CORE_PROTOCOL rule #1 enforced via rag_query_hook + task_discipline_hook gate",
        "enforcement": "advisory (protocol) + blocking (discipline hook)",
    },
    "sync_tasks_to_db": {
        "type": "hook_script",
        "file": "scripts/task_sync_hook.py",
        "hook_event": "PostToolUse(TaskCreate)",
        "description": "Syncs TaskCreate calls to claude.todos via substring+fuzzy matching",
    },
    "gate_blocked": {
        "type": "hook_script",
        "file": "scripts/task_discipline_hook.py",
        "hook_event": "PreToolUse",
        "description": "Returns permissionDecision=deny when no tasks exist",
    },
    "select_next_task": {
        "type": "claude_behavior",
        "description": "Claude manually selects next task from ready list (userTask decision point)",
    },
    "mark_in_progress": {
        "type": "claude_behavior",
        "description": "Claude manually calls TaskUpdate(status=in_progress) - NO auto hook",
        "gap": "Model expects hook automation but status change is manual",
    },
    "bpmn_first_check": {
        "type": "rule_file",
        "file": ".claude/rules/system-change-process.md",
        "description": "Advisory rule for BPMN-first on hook/workflow changes - no enforcement",
    },
    "call_core_claude": {
        "type": "bpmn_call_activity",
        "calledElement": "L1_core_claude",
        "description": "CallActivity to core Claude prompt processing model",
    },
    "mark_completed": {
        "type": "hook_script",
        "file": "scripts/task_sync_hook.py",
        "hook_event": "PostToolUse(TaskUpdate)",
        "description": "task_sync_hook auto-checkpoints on TaskUpdate(completed) - upserts session_state",
    },
    "check_feature": {
        "type": "mcp_tool",
        "tool": "complete_work",
        "description": "complete_work() checks sibling tasks - but requires manual invocation",
    },
    "record_blocker": {
        "type": "claude_behavior",
        "description": "Claude freetext in task description - no structured blocker capture",
    },
    "snapshot_states": {
        "type": "hook_script",
        "file": "scripts/precompact_hook.py",
        "description": "PreCompact injects work items but no explicit per-session snapshot",
        "gap": "Only fires on compaction, not on session end",
    },
    "store_session_context": {
        "type": "mcp_tool",
        "tool": "end_session",
        "description": "MCP tool stores summary+next_steps - requires manual /session-end",
        "also": ["scripts/session_end_hook.py"],
    },
    # L1_claude_family_extensions.bpmn elements
    "hook_log_session": {
        "type": "hook_script",
        "file": "scripts/session_startup_hook_enhanced.py",
        "hook_event": "SessionStart",
        "description": "Logs session to claude.sessions with 60s dedup guard",
    },
    "hook_init_task_map": {
        "type": "hook_script",
        "file": "scripts/session_startup_hook_enhanced.py",
        "description": "_reset_task_map() in session startup creates fresh task map",
    },
    "hook_archive_stale": {
        "type": "hook_script",
        "file": "scripts/session_startup_hook_enhanced.py",
        "description": "Archives stale todos from previous sessions during startup",
    },
    "hook_check_inbox": {
        "type": "hook_script",
        "file": "scripts/session_startup_hook_enhanced.py",
        "description": "Checks orchestrator inbox during session startup (passive display)",
    },
    "restore_context": {
        "type": "claude_behavior",
        "description": "Claude uses /session-resume to restore prior session context",
    },
    "fresh_session": {
        "type": "claude_behavior",
        "description": "Default path when no prior state exists",
    },
    "receive_prompt": {
        "type": "claude_behavior",
        "description": "Claude receives user prompt - loop entry point",
    },
    "hook_check_session": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Session ID comparison - detects session change",
    },
    "hook_reset_task_map": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Resets task map when session ID changes",
    },
    "hook_classify_prompt": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Classifies prompt as action vs question for RAG gating",
    },
    "hook_query_rag": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "hook_event": "UserPromptSubmit",
        "description": "Voyage AI semantic search over knowledge vault",
    },
    "hook_suggest_skills": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Skill content similarity search",
    },
    "hook_inject_context": {
        "type": "hook_script",
        "file": "scripts/rag_query_hook.py",
        "description": "Injects RAG results + core protocol + skills into context",
    },
    "hook_post_sync": {
        "type": "hook_script",
        "file": "scripts/todo_sync_hook.py",
        "hook_event": "PostToolUse",
        "also": ["scripts/task_sync_hook.py", "scripts/mcp_usage_logger.py"],
        "description": "Post-tool sync: todos, tasks, MCP usage logging",
    },
    "log_continuation": {
        "type": "claude_behavior",
        "description": "Claude logs warning when session ID changes mid-conversation",
    },
    "auto_close": {
        "type": "hook_script",
        "file": "scripts/session_end_hook.py",
        "hook_event": "SessionEnd",
        "description": "Auto-closes unclosed sessions (< 24h old)",
    },
    "write_summary": {
        "type": "claude_behavior",
        "description": "Claude writes session summary via /session-end skill",
    },
    "capture_knowledge": {
        "type": "mcp_tool",
        "tool": "store_knowledge / extract_insights",
        "description": "Knowledge capture via project-tools MCP",
    },
    "manual_close": {
        "type": "mcp_tool",
        "tool": "end_session",
        "description": "Closes session with summary in claude.sessions",
    },
}


def _check_artifact_exists(artifact: dict, project_root: Path) -> dict:
    """Check if a code artifact actually exists on disk."""
    result = {"exists": False, "details": ""}

    if artifact["type"] == "hook_script":
        filepath = project_root / artifact["file"]
        result["exists"] = filepath.exists()
        result["details"] = f"File: {artifact['file']}"
        if "hook_event" in artifact:
            result["details"] += f" (event: {artifact['hook_event']})"
        if "also" in artifact:
            also_exist = all((project_root / f).exists() for f in artifact["also"])
            result["details"] += f" + {len(artifact['also'])} related scripts (all exist: {also_exist})"

    elif artifact["type"] == "mcp_tool":
        result["exists"] = True  # MCP tools are assumed present if configured
        result["details"] = f"MCP: {artifact.get('tool', 'unknown')}"

    elif artifact["type"] == "hook_output":
        result["exists"] = True  # Hook outputs are implicit
        result["details"] = artifact.get("description", "implicit")

    elif artifact["type"] == "command":
        result["exists"] = True  # External commands are assumed available
        result["details"] = f"Command: {artifact.get('command', 'unknown')}"

    elif artifact["type"] == "agent":
        result["exists"] = True  # Agents are assumed available
        result["details"] = f"Agent: {artifact.get('agent', 'unknown')}"

    return result


@mcp.tool()
def check_alignment(process_id: str) -> dict:
    """Check alignment between a BPMN process model and actual code artifacts.

    Parses the BPMN process, extracts all tasks (user/script/service), and
    checks each against a registry of known code artifacts (hook scripts,
    MCP tools, DB operations). Reports which elements are mapped, unmapped,
    or have missing artifacts.

    Use when: you want to verify that a BPMN model accurately reflects
    the actual implementation, or to find gaps between model and reality.

    Returns: {process_id, total_elements, mapped, unmapped, missing_artifacts,
              coverage_pct, alignment_report}
    """
    try:
        bpmn_path = _find_bpmn_file(process_id)
        if bpmn_path is None:
            return {
                "success": False,
                "error": f"Process '{process_id}' not found in {get_processes_dir()}",
            }

        root = _parse_xml(bpmn_path)

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

        elements, _ = _extract_process_elements(target_process)

        # Filter to actionable elements (tasks), skip events and gateways
        actionable_types = {"userTask", "scriptTask", "serviceTask", "task", "callActivity"}
        tasks = [e for e in elements if e["type"] in actionable_types]

        # Determine project root (2 levels up from server.py)
        project_root = _SERVER_DIR.parent.parent

        mapped = []
        unmapped = []
        missing_artifacts = []

        for task in tasks:
            task_id = task["id"]
            task_name = task["name"]

            if task_id in _ARTIFACT_REGISTRY:
                artifact = _ARTIFACT_REGISTRY[task_id]
                check_result = _check_artifact_exists(artifact, project_root)

                entry = {
                    "element_id": task_id,
                    "element_name": task_name,
                    "element_type": task["type"],
                    "artifact_type": artifact["type"],
                    "artifact_details": check_result["details"],
                    "artifact_exists": check_result["exists"],
                }
                mapped.append(entry)

                if not check_result["exists"]:
                    missing_artifacts.append(entry)
            else:
                unmapped.append({
                    "element_id": task_id,
                    "element_name": task_name,
                    "element_type": task["type"],
                    "suggestion": _suggest_artifact(task_name),
                })

        total = len(tasks)
        mapped_count = len(mapped)
        coverage_pct = round((mapped_count / total * 100), 1) if total > 0 else 0.0

        return {
            "success": True,
            "process_id": process_id,
            "file": bpmn_path.name,
            "total_elements": total,
            "mapped_count": mapped_count,
            "unmapped_count": len(unmapped),
            "missing_artifact_count": len(missing_artifacts),
            "coverage_pct": coverage_pct,
            "mapped": mapped,
            "unmapped": unmapped,
            "missing_artifacts": missing_artifacts,
        }

    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _suggest_artifact(task_name: str) -> str:
    """Suggest what code artifact a BPMN task might map to based on its name."""
    name_lower = task_name.lower()

    if "[hook]" in name_lower:
        return "Likely a hook script in scripts/"
    if "[tool]" in name_lower:
        return "Likely an MCP tool call"
    if "[db]" in name_lower:
        return "Likely a database operation"
    if "[claude]" in name_lower:
        return "Claude decision/action - no specific code artifact"
    if "[km]" in name_lower:
        return "Knowledge management operation (RAG/vault)"

    # Check for common patterns
    if any(kw in name_lower for kw in ("check", "validate", "verify")):
        return "Validation logic - check hooks or MCP tools"
    if any(kw in name_lower for kw in ("save", "store", "persist", "write")):
        return "Persistence operation - check DB or file write"
    if any(kw in name_lower for kw in ("spawn", "delegate", "agent")):
        return "Agent orchestration - check orchestrator MCP"

    return "No suggestion - add to _ARTIFACT_REGISTRY"


# ============================================================================
# Entry point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
