"""
Tests for the Skill Discovery BPMN process.

Models how Claude discovers, loads, and uses skills via four paths:
  A. Semantic suggestion (RAG hook, UserPromptSubmit) - CURRENTLY DISABLED
  B. Context injection (PreToolUse hook, Write/Edit) - goes direct to end_merge
  C. Manual recall (Claude reads CLAUDE.md / memory) - default trigger path
  D. MCP search (find_skill tool, 0 calls ever recorded)

Paths A, C, D converge at decide_merge → decide_to_load (userTask) → load_skill_gw.
Path B routes directly to end_merge (bypasses decide_to_load entirely).

Key BPMN notes:
  - identify_trigger is a scriptTask; defaults trigger_type to "user_prompt" if unset.
  - trigger_gw default flow is flow_manual → claude_remembers_skill (Path C).
  - skill_suggest_enabled_gw default flow is flow_suggest_disabled → skip_suggestions.
  - rules_matched_gw default flow is flow_no_rules → no_rules_matched.
  - load_skill_gw default flow is flow_skip_loading → skip_skill_loading.
  - claude_remembers_skill, decide_to_load, apply_skill_guidance are userTasks.

Paths tested:
  1. Path A enabled:  trigger=user_prompt, skill_suggestions_enabled=True
                      → query_skill_suggestions → inject_skill_suggestion
                      → decide_to_load(load_skill=True) → invoke_skill_tool
                      → apply_skill_guidance → end
  2. Path A disabled: trigger=user_prompt (default skill_suggestions_enabled=False)
                      → skip_suggestions → decide_to_load(load_skill=False)
                      → skip_skill_loading → end
  3. Path B rules match: trigger=tool_use, rules_matched=True
                         → match_context_rules → load_skill_content → inject_context → end
  4. Path B no rules: trigger=tool_use, rules_matched=False
                      → no_rules_matched → end
  5. Path C manual + load: trigger=manual (default) → claude_remembers_skill
                           → decide_to_load(load_skill=True) → apply_skill_guidance → end
  6. Path D MCP search: trigger=mcp_search → find_skill_mcp
                        → decide_to_load(skip default) → skip_skill_loading → end

Implementation: scripts/rag_query_hook.py, scripts/context_injector_hook.py,
                .claude/skills/*/skill.md, mcp-servers/project-tools/server_v2.py
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "skill_discovery.bpmn")
)
PROCESS_ID = "skill_discovery"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh, initialised workflow instance."""
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


def get_ready_user_tasks(wf: BpmnWorkflow) -> list:
    """Return all READY user tasks (manual=True in SpiffWorkflow terms)."""
    return wf.get_tasks(state=TaskState.READY, manual=True)


def ready_task_names(wf: BpmnWorkflow) -> list:
    """Return names of all READY user tasks."""
    return [t.task_spec.name for t in get_ready_user_tasks(wf)]


def complete_user_task(wf: BpmnWorkflow, task_name: str, data: dict = None) -> None:
    """
    Find the named READY user task, merge data into it, run it, then call
    do_engine_steps() to advance through any subsequent automated tasks.

    Raises AssertionError if the task is not currently READY.
    """
    ready = get_ready_user_tasks(wf)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    if data:
        task.data.update(data)
    task.run()
    wf.do_engine_steps()


def completed_spec_names(wf: BpmnWorkflow) -> set:
    """Return the spec names of all COMPLETED tasks as a set."""
    return {t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Path A Enabled - Semantic Suggestion, User Prompt, Skill Loaded
# ---------------------------------------------------------------------------


class TestPathAEnabled:
    """
    Path A with skill suggestions enabled and Claude decides to load:
    start → identify_trigger(script) → trigger_gw [user_prompt]
    → rag_hook_fires(script) → skill_suggest_enabled_gw [enabled]
    → query_skill_suggestions(script) → inject_skill_suggestion(script)
    → decide_merge → decide_to_load(user, load_skill=True)
    → load_skill_gw [do_load] → invoke_skill_tool(script)
    → apply_skill_guidance(user) → end_merge → end
    """

    def test_path_a_enabled_skill_loaded(self):
        wf = load_workflow(initial_data={"trigger_type": "user_prompt", "skill_suggestions_enabled": True})

        # After engine steps: decide_to_load should be the first READY user task.
        # identify_trigger, rag_hook_fires, query_skill_suggestions, inject_skill_suggestion
        # are all scriptTasks that run automatically.
        assert "decide_to_load" in ready_task_names(wf), (
            f"Expected decide_to_load READY after Path A inject. Got: {ready_task_names(wf)}"
        )

        # Claude decides to load the skill
        complete_user_task(wf, "decide_to_load", {"load_skill": True})

        # invoke_skill_tool is a scriptTask (auto-runs) → apply_skill_guidance is a userTask
        assert "apply_skill_guidance" in ready_task_names(wf), (
            f"Expected apply_skill_guidance READY after invoke_skill_tool. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "apply_skill_guidance", {})

        assert wf.is_completed(), "Workflow should complete after apply_skill_guidance"
        names = completed_spec_names(wf)

        assert "rag_hook_fires" in names
        assert "query_skill_suggestions" in names
        assert "inject_skill_suggestion" in names
        assert "decide_to_load" in names
        assert "invoke_skill_tool" in names
        assert "apply_skill_guidance" in names
        assert "end" in names

        # Path B steps must NOT appear
        assert "context_hook_fires" not in names
        assert "match_context_rules" not in names
        assert "load_skill_content" not in names
        assert "inject_context" not in names

        # Script flags set by automated tasks
        assert wf.data.get("rag_hook_active") is True
        assert wf.data.get("skill_suggestions_found") is True
        assert wf.data.get("suggestion_injected") is True
        assert wf.data.get("skill_loaded") is True


# ---------------------------------------------------------------------------
# Test 2: Path A Disabled - Semantic Suggestion Off (Default), Skill Skipped
# ---------------------------------------------------------------------------


class TestPathADisabled:
    """
    Path A with skill suggestions disabled (the default in production):
    start → identify_trigger(script) → trigger_gw [user_prompt]
    → rag_hook_fires(script) → skill_suggest_enabled_gw [disabled default]
    → skip_suggestions(script) → decide_merge → decide_to_load(user, load_skill=False default)
    → load_skill_gw [skip default] → skip_skill_loading(script) → end_merge → end
    """

    def test_path_a_disabled_skill_skipped(self):
        # skill_suggestions_enabled defaults to False in the scriptTask
        wf = load_workflow(initial_data={"trigger_type": "user_prompt"})

        # skip_suggestions fires automatically; decide_to_load should be READY
        assert "decide_to_load" in ready_task_names(wf), (
            f"Expected decide_to_load READY after skip_suggestions. Got: {ready_task_names(wf)}"
        )

        # Claude does NOT load (default gateway branch: skip)
        complete_user_task(wf, "decide_to_load", {"load_skill": False})

        assert wf.is_completed(), "Workflow should complete via skip_skill_loading"
        names = completed_spec_names(wf)

        assert "rag_hook_fires" in names
        assert "skip_suggestions" in names
        assert "decide_to_load" in names
        assert "skip_skill_loading" in names
        assert "end" in names

        # Enabled branch must NOT appear
        assert "query_skill_suggestions" not in names
        assert "inject_skill_suggestion" not in names
        assert "invoke_skill_tool" not in names
        assert "apply_skill_guidance" not in names

        assert wf.data.get("suggestion_skipped") is True
        assert wf.data.get("skill_skipped") is True


# ---------------------------------------------------------------------------
# Test 3: Path B Rules Match - Context Injection, Skill Injected
# ---------------------------------------------------------------------------


class TestPathBRulesMatch:
    """
    Path B (PreToolUse Write/Edit) with a matching context rule:
    start → identify_trigger(script) → trigger_gw [tool_use]
    → context_hook_fires(script) → match_context_rules(script)
    → rules_matched_gw [rules_found] → load_skill_content(script)
    → inject_context(script) → end_merge → end

    Path B bypasses decide_to_load entirely.
    """

    def test_path_b_rules_match_injects_context(self):
        wf = load_workflow(initial_data={"trigger_type": "tool_use", "rules_matched": True})

        # Path B is fully automated - no userTasks
        assert wf.is_completed(), (
            f"Path B (rules matched) should complete without user interaction. "
            f"READY: {ready_task_names(wf)}"
        )
        names = completed_spec_names(wf)

        assert "context_hook_fires" in names
        assert "match_context_rules" in names
        assert "load_skill_content" in names
        assert "inject_context" in names
        assert "end" in names

        # Paths A/C/D steps must NOT appear
        assert "rag_hook_fires" not in names
        assert "claude_remembers_skill" not in names
        assert "decide_to_load" not in names
        assert "find_skill_mcp" not in names
        assert "no_rules_matched" not in names

        assert wf.data.get("context_hook_active") is True
        assert wf.data.get("skill_content_loaded") is True
        assert wf.data.get("context_injected") is True


# ---------------------------------------------------------------------------
# Test 4: Path B No Rules - Context Hook Fires, No Match
# ---------------------------------------------------------------------------


class TestPathBNoRules:
    """
    Path B (PreToolUse) with no matching context rules:
    start → identify_trigger(script) → trigger_gw [tool_use]
    → context_hook_fires(script) → match_context_rules(script)
    → rules_matched_gw [no match default] → no_rules_matched(script)
    → end_merge → end

    Path B bypasses decide_to_load entirely even on the no-rules branch.
    """

    def test_path_b_no_rules_skips_skill(self):
        wf = load_workflow(initial_data={"trigger_type": "tool_use", "rules_matched": False})

        assert wf.is_completed(), (
            f"Path B (no rules) should complete without user interaction. "
            f"READY: {ready_task_names(wf)}"
        )
        names = completed_spec_names(wf)

        assert "context_hook_fires" in names
        assert "match_context_rules" in names
        assert "no_rules_matched" in names
        assert "end" in names

        # No skill loading happened
        assert "load_skill_content" not in names
        assert "inject_context" not in names
        assert "decide_to_load" not in names

        assert wf.data.get("no_skill_injected") is True


# ---------------------------------------------------------------------------
# Test 5: Path C Manual Recall + Load Skill
# ---------------------------------------------------------------------------


class TestPathCManualLoad:
    """
    Path C (default/manual recall trigger) with Claude choosing to load:
    start → identify_trigger(script) → trigger_gw [default/manual]
    → claude_remembers_skill(user) → decide_merge
    → decide_to_load(user, load_skill=True) → load_skill_gw [do_load]
    → invoke_skill_tool(script) → apply_skill_guidance(user) → end_merge → end

    trigger_type defaults to "user_prompt" in identify_trigger's try/except,
    but the test does not supply trigger_type so trigger_gw falls to the
    default flow_manual branch (claude_remembers_skill).
    """

    def test_path_c_manual_recall_load_skill(self):
        # No trigger_type supplied → identify_trigger sets "user_prompt" default,
        # but the gateway default branch is flow_manual → claude_remembers_skill.
        # We force the manual path explicitly.
        wf = load_workflow(initial_data={"trigger_type": "manual"})

        # claude_remembers_skill is a userTask (Path C default branch)
        assert "claude_remembers_skill" in ready_task_names(wf), (
            f"Expected claude_remembers_skill READY on manual path. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "claude_remembers_skill", {})

        # decide_to_load is the next userTask
        assert "decide_to_load" in ready_task_names(wf), (
            f"Expected decide_to_load READY after claude_remembers_skill. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "decide_to_load", {"load_skill": True})

        # invoke_skill_tool auto-runs; apply_skill_guidance is a userTask
        assert "apply_skill_guidance" in ready_task_names(wf), (
            f"Expected apply_skill_guidance READY after invoke_skill_tool. Got: {ready_task_names(wf)}"
        )
        complete_user_task(wf, "apply_skill_guidance", {})

        assert wf.is_completed(), "Workflow should complete after apply_skill_guidance"
        names = completed_spec_names(wf)

        assert "claude_remembers_skill" in names
        assert "decide_to_load" in names
        assert "invoke_skill_tool" in names
        assert "apply_skill_guidance" in names
        assert "end" in names

        # Path B steps must NOT appear
        assert "context_hook_fires" not in names
        assert "rag_hook_fires" not in names
        assert "find_skill_mcp" not in names

        assert wf.data.get("skill_loaded") is True


# ---------------------------------------------------------------------------
# Test 6: Path D MCP Search + Skip Loading (Default)
# ---------------------------------------------------------------------------


class TestPathDMcpSearch:
    """
    Path D (MCP find_skill search) with Claude skipping load (default):
    start → identify_trigger(script) → trigger_gw [mcp_search]
    → find_skill_mcp(script) → decide_merge
    → decide_to_load(user, no data = default skip) → load_skill_gw [skip default]
    → skip_skill_loading(script) → end_merge → end
    """

    def test_path_d_mcp_search_skip_load(self):
        wf = load_workflow(initial_data={"trigger_type": "mcp_search"})

        # find_skill_mcp is a scriptTask (auto-runs) → decide_to_load is the userTask
        assert "decide_to_load" in ready_task_names(wf), (
            f"Expected decide_to_load READY after find_skill_mcp. Got: {ready_task_names(wf)}"
        )

        # Claude does not load (default gateway: skip)
        complete_user_task(wf, "decide_to_load", {"load_skill": False})

        assert wf.is_completed(), "Workflow should complete via skip_skill_loading"
        names = completed_spec_names(wf)

        assert "find_skill_mcp" in names
        assert "decide_to_load" in names
        assert "skip_skill_loading" in names
        assert "end" in names

        # Skill loading branch must NOT appear
        assert "invoke_skill_tool" not in names
        assert "apply_skill_guidance" not in names

        # Path B steps must NOT appear
        assert "context_hook_fires" not in names
        assert "claude_remembers_skill" not in names

        assert wf.data.get("find_skill_called") is True
        assert wf.data.get("skill_skipped") is True


# ---------------------------------------------------------------------------
# Test 7: Path A vs Path B - decide_to_load Isolation
# ---------------------------------------------------------------------------


class TestPathIsolation:
    """Path B must never reach decide_to_load. Path A always does."""

    def test_path_b_never_reaches_decide_to_load(self):
        """Path B completes without any user interaction."""
        wf = load_workflow(initial_data={"trigger_type": "tool_use", "rules_matched": True})
        assert wf.is_completed()
        assert "decide_to_load" not in completed_spec_names(wf)

    def test_path_a_always_reaches_decide_to_load(self):
        """Path A always pauses at decide_to_load regardless of suggestion outcome."""
        wf = load_workflow(initial_data={"trigger_type": "user_prompt", "skill_suggestions_enabled": True})
        assert "decide_to_load" in ready_task_names(wf)
        # Confirm Path B was NOT taken
        assert "context_hook_fires" not in completed_spec_names(wf)


# ---------------------------------------------------------------------------
# Test 8: Script Data Flags - Automated Task Outputs
# ---------------------------------------------------------------------------


class TestScriptDataFlags:
    """Verify that scriptTask data flags propagate correctly to wf.data."""

    def test_path_b_rules_match_sets_flags(self):
        wf = load_workflow(initial_data={"trigger_type": "tool_use", "rules_matched": True})
        assert wf.is_completed()
        assert wf.data.get("context_hook_active") is True
        assert wf.data.get("rules_queried") is True
        assert wf.data.get("skill_content_loaded") is True
        assert wf.data.get("context_injected") is True

    def test_path_a_enabled_sets_suggestion_flags(self):
        wf = load_workflow(initial_data={"trigger_type": "user_prompt", "skill_suggestions_enabled": True})
        # Advance past decide_to_load without loading
        complete_user_task(wf, "decide_to_load", {"load_skill": False})
        assert wf.is_completed()
        assert wf.data.get("rag_hook_active") is True
        assert wf.data.get("skill_suggestions_found") is True
        assert wf.data.get("suggestion_injected") is True
        assert wf.data.get("skill_skipped") is True

    def test_path_d_sets_find_skill_flag(self):
        wf = load_workflow(initial_data={"trigger_type": "mcp_search"})
        complete_user_task(wf, "decide_to_load", {"load_skill": False})
        assert wf.is_completed()
        assert wf.data.get("find_skill_called") is True
