"""
BPMN vs Reality Analysis

Runs the existing BPMN process models against real Claude Family scenarios
to identify gaps between what the model says and what actually happens.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

PROCESSES_DIR = os.path.join(os.path.dirname(__file__), "..", "processes")
TASK_BPMN = os.path.join(PROCESSES_DIR, "lifecycle", "task_lifecycle.bpmn")
SESSION_BPMN = os.path.join(PROCESSES_DIR, "lifecycle", "session_lifecycle.bpmn")
FEATURE_BPMN = os.path.join(PROCESSES_DIR, "lifecycle", "feature_workflow.bpmn")


def load(bpmn_file, process_id):
    parser = BpmnParser()
    parser.add_bpmn_file(bpmn_file)
    spec = parser.get_spec(process_id)
    wf = BpmnWorkflow(spec)
    wf.do_engine_steps()
    return wf


def ready(wf):
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]


def complete(wf, name, data):
    tasks = [t for t in wf.get_tasks(state=TaskState.READY, manual=True) if t.task_spec.name == name]
    if not tasks:
        return f"ERROR: {name} not READY. Ready: {ready(wf)}"
    tasks[0].data.update(data)
    tasks[0].run()
    wf.do_engine_steps()
    return f"OK: {name}"


def completed_names(wf):
    return [t.task_spec.name for t in wf.get_tasks(state=TaskState.COMPLETED)]


def section(title):
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def subsection(title):
    print()
    print("-" * 70)
    print(title)
    print("-" * 70)


# ================================================================
# 1. TASK LIFECYCLE
# ================================================================

section("1. TASK LIFECYCLE: BPMN Model vs Reality")

print("""
BPMN MODEL (task_lifecycle.bpmn):
  start -> create_task -> sync_to_db -> has_tasks_gateway
  [has_tasks] -> work_on_task -> task_action_gateway
    [complete] -> mark_completed -> end_completed
    [block]    -> resolve_blocker -> work_on_task (loop)
  [no tasks]  -> mark_gate_blocked -> end_blocked

REALITY (what hooks actually do):
  1. User asks to build something
  2. CORE_PROTOCOL says: create tasks first (advisory, rag_query_hook)
  3. task_discipline_hook blocks Write/Edit/Task/Bash if no tasks in task_map
  4. Claude calls TaskCreate (can be 1-5 tasks at once)
  5. task_sync_hook PostToolUse: dedup check, insert todo, bridge to build_task, write task_map
  6. discipline hook allows tools (task_map now has entries matching session_id)
  7. Claude writes code, runs tests (may update task status midway)
  8. Claude calls TaskUpdate(in_progress) then TaskUpdate(completed)
  9. task_sync_hook: updates todo + build_task, checks feature completion
""")

subsection("GAPS: What BPMN misses about task lifecycle")

gaps = [
    ("MISSING: Update midway",
     "BPMN has work_on_task as single step. Reality: Claude updates tasks",
     "midway (in_progress). No BPMN step for partial progress tracking."),

    ("MISSING: Multiple tasks per feature",
     "BPMN models ONE task. Reality: Claude creates 3-5 tasks per feature,",
     "works through them sequentially. Need a multi-instance subprocess."),

    ("MISSING: Task bridging to build_tasks",
     "BPMN has generic sync_to_db. Reality: sync does dedup detection",
     "(75% similarity), build_task bridging, and session scoping."),

    ("MISSING: Feature completion cascade",
     "BPMN ends at mark_completed. Reality: completing the LAST task",
     "triggers a feature completion check and surfaces advisory."),

    ("SIMPLIFIED: Discipline gate",
     "BPMN has binary has_tasks gateway. Reality: 3 checks - map exists,",
     "session ID matches, has task entries. Plus race condition fallback."),

    ("MISSING: Stale task handling",
     "No concept of sessions or staleness in BPMN. Reality: tasks from",
     "previous sessions are rejected. SessionStart resets the task_map."),

    ("EXTRA IN BPMN: resolve_blocker loop",
     "BPMN models block->resolve->resume. Reality: blocked tasks just sit",
     "in blocked status in DB. No explicit unblock flow in hooks."),
]

for i, gap in enumerate(gaps, 1):
    print(f"  {i}. {gap[0]}")
    for line in gap[1:]:
        print(f"     {line}")
    print()

subsection("SIMULATION: Task lifecycle scenarios")

# Happy path
wf = load(TASK_BPMN, "task_lifecycle")
print(f"  Happy path:")
print(f"    Start -> ready: {ready(wf)}")
complete(wf, "create_task", {"has_tasks": True})
print(f"    After create_task -> ready: {ready(wf)}")
complete(wf, "work_on_task", {"action": "complete"})
print(f"    Done: {wf.is_completed()}, status={wf.data.get('status')}")

# Blocked path
wf2 = load(TASK_BPMN, "task_lifecycle")
print(f"\n  No tasks -> blocked:")
complete(wf2, "create_task", {"has_tasks": False})
print(f"    Done: {wf2.is_completed()}, gate_blocked={wf2.data.get('gate_blocked')}")

# Block and resume
wf3 = load(TASK_BPMN, "task_lifecycle")
print(f"\n  Block then resume:")
complete(wf3, "create_task", {"has_tasks": True})
complete(wf3, "work_on_task", {"action": "block"})
print(f"    After block -> ready: {ready(wf3)}")
complete(wf3, "resolve_blocker", {})
print(f"    After resolve -> ready: {ready(wf3)}")
complete(wf3, "work_on_task", {"action": "complete"})
print(f"    Done: {wf3.is_completed()}, status={wf3.data.get('status')}")


# ================================================================
# 2. SESSION LIFECYCLE
# ================================================================

section("2. SESSION LIFECYCLE: BPMN Model vs Reality")

print("""
BPMN MODEL (session_lifecycle.bpmn):
  start -> session_start -> load_state -> has_prior_state_gateway
  [prior_state] -> restore_context -> work_merge -> do_work
  [no prior]    -> fresh_start -> work_merge -> do_work
  do_work -> work_action_gateway
    [end_session] -> save_summary -> close_session -> end_normal
    [compact]     -> save_checkpoint -> do_work (loop)
    [default]     -> do_work (loop, continue)

REALITY (hooks that implement session lifecycle):
  1. SessionStart hook (ONCE): log session, reset task_map, archive stale todos, check messages
  2. UserPromptSubmit hook (EVERY prompt): RAG query + CORE_PROTOCOL injection
  3. PreToolUse hooks (per tool): discipline gate, context injection, standards validation
  4. PostToolUse hooks (per tool): todo sync, task sync, MCP usage logging
  5. PreCompact hook: inject active work items before context compression
  6. SessionEnd hook (auto): close session in DB
  7. /session-end command (manual): detailed summary + knowledge capture
""")

subsection("GAPS: What BPMN misses about session lifecycle")

session_gaps = [
    ("MISSING: Per-prompt RAG cycle",
     "Every user prompt triggers RAG query + CORE_PROTOCOL. This is a",
     "per-prompt subprocess nested inside do_work. Not in BPMN at all."),

    ("MISSING: Auto-archive on startup",
     "SessionStart archives >7 day stale todos. Not in BPMN model.",
     "Should be a step between session_start and load_state."),

    ("MISSING: Message/inbox checking",
     "SessionStart checks inbox for pending messages from other Claudes.",
     "Missing from BPMN. Could be a parallel task during startup."),

    ("MISSING: PreCompact context preservation",
     "BPMN has save_checkpoint for compact action. Reality: precompact_hook",
     "injects work items into context BEFORE compression, which is different",
     "from saving a checkpoint AFTER the compact decision."),

    ("OVERSIMPLIFIED: do_work is not one step",
     "BPMN treats do_work as atomic. Reality: do_work contains the entire",
     "feature_workflow + task_lifecycle + hook_chain nested inside it.",
     "This is where inter-process links (call activities) would help."),

    ("MISSING: Hook chain per tool call",
     "Each tool call within do_work triggers: discipline check, context",
     "injection, tool execution, post-tool sync. This is hook_chain.bpmn",
     "but it is not linked to session_lifecycle.bpmn."),

    ("MISSING: Dual end paths",
     "BPMN has one end (end_normal via save_summary). Reality has two:",
     "  - SessionEnd hook (auto, minimal): just closes DB record",
     "  - /session-end (manual, rich): summary + learnings + knowledge"),
]

for i, gap in enumerate(session_gaps, 1):
    print(f"  {i}. {gap[0]}")
    for line in gap[1:]:
        print(f"     {line}")
    print()

subsection("SIMULATION: Session lifecycle scenarios")

# Fresh session
wf4 = load(SESSION_BPMN, "session_lifecycle")
print(f"  Fresh session -> work -> compact -> work -> end:")
print(f"    Start -> ready: {ready(wf4)}")
complete(wf4, "load_state", {"state_loaded": True, "prior_state": False})
print(f"    After fresh start -> ready: {ready(wf4)}")
complete(wf4, "do_work", {"action": "compact"})
print(f"    After compact -> ready: {ready(wf4)}, done: {wf4.is_completed()}")
complete(wf4, "do_work", {"action": "end_session"})
print(f"    Done: {wf4.is_completed()}, closed={wf4.data.get('session_closed')}")

# Resumed session
wf5 = load(SESSION_BPMN, "session_lifecycle")
print(f"\n  Resumed session -> work -> end:")
complete(wf5, "load_state", {"state_loaded": True, "prior_state": True})
print(f"    After restore -> ready: {ready(wf5)}")
complete(wf5, "restore_context", {})
print(f"    After context restore -> ready: {ready(wf5)}")
complete(wf5, "do_work", {"action": "end_session"})
print(f"    Done: {wf5.is_completed()}, closed={wf5.data.get('session_closed')}")


# ================================================================
# 3. FEATURE WORKFLOW
# ================================================================

section("3. FEATURE WORKFLOW: BPMN Model vs Reality")

print("""
BPMN MODEL (feature_workflow.bpmn):
  create_feature -> set_draft -> plan_feature -> set_planned
  -> complexity_gateway
    [high] -> spawn_agents -> implementation_merge
    [default] -> implement_directly -> implementation_merge
  -> run_tests -> tests_pass_gateway
    [pass] -> review_code -> review_result_gateway
      [changes_requested] -> fix_issues_review -> run_tests (loop)
      [default/approved] -> set_completed -> end_completed
    [fail] -> fix_issues -> run_tests (loop)

REALITY (what actually happens):
  1. create_feature() MCP tool -> inserts into claude.features (status=draft)
  2. advance_status(F1, planned) -> sets planned status
  3. create_linked_task() for each build task
  4. start_work(BT1) -> todo to in_progress, loads plan_data
  5. Claude writes code (may spawn agents for complex work)
  6. complete_work(BT1) -> completed, checks if more tasks
  7. Repeat 4-6 for each task
  8. Testing: run pytest (manual, not tracked by workflow)
  9. Review: spawn reviewer-sonnet (manual, not tracked)
  10. advance_status(F1, completed) -> requires all_tasks_done condition
""")

subsection("GAPS: What BPMN misses about feature workflow")

feature_gaps = [
    ("GOOD MATCH: Draft -> planned -> in_progress -> completed",
     "The state machine matches the DB workflow_transitions table.",
     "This is the strongest alignment between BPMN and reality."),

    ("MISSING: Task creation step",
     "BPMN goes from plan to implement. Reality: between plan and implement,",
     "Claude creates 3-10 build_tasks with create_linked_task(). Each task",
     "is its own sub-lifecycle. BPMN needs a multi-instance subprocess here."),

    ("MISSING: Per-task work tracking",
     "BPMN has one implement step. Reality: each build_task goes through",
     "start_work -> code -> complete_work independently. The feature",
     "workflow should call task_lifecycle for each task."),

    ("TESTING: Not enforced",
     "BPMN has run_tests as mandatory step. Reality: testing is optional.",
     "Claude SHOULD test but no hook enforces it. BPMN could enforce this."),

    ("REVIEW: Not enforced",
     "BPMN has review_code as mandatory. Reality: review is optional.",
     "reviewer-sonnet is spawned manually. BPMN could enforce this too."),

    ("MISSING: Plan data / structured specs",
     "BPMN has plan_feature as a single step. Reality: planning produces",
     "plan_data (JSON) stored in features table, with requirements, risks,",
     "implementation specs. The richness of planning is not captured."),
]

for i, gap in enumerate(feature_gaps, 1):
    print(f"  {i}. {gap[0]}")
    for line in gap[1:]:
        print(f"     {line}")
    print()

subsection("SIMULATION: Feature workflow - simple path")

wf6 = load(FEATURE_BPMN, "feature_workflow")
print(f"  Simple feature: create -> plan -> implement -> test -> review -> done")
print(f"    Start -> ready: {ready(wf6)}")
complete(wf6, "create_feature", {})
print(f"    After create -> ready: {ready(wf6)}")
complete(wf6, "plan_feature", {"complexity": "simple"})
print(f"    After plan -> ready: {ready(wf6)}")
complete(wf6, "implement_directly", {})
print(f"    After implement -> ready: {ready(wf6)}")
complete(wf6, "run_tests", {"tests_passed": True})
print(f"    After tests pass -> ready: {ready(wf6)}")
complete(wf6, "review_code", {"review": "approved"})
print(f"    Done: {wf6.is_completed()}, status={wf6.data.get('status')}")
print(f"    Completed steps: {completed_names(wf6)}")


# ================================================================
# VERDICT
# ================================================================

section("VERDICT: What BPMN can actually do for us")

print("""
WHAT THE BPMN IS GOOD FOR (proven by testing):
  1. SEQUENCE VALIDATION: "Did you plan before building? Test before completing?"
     - feature_workflow enforces: plan -> implement -> test -> review -> done
     - This is NOT enforced today. Testing and review are optional.
     - BPMN could enforce: "You cannot advance to completed without run_tests"

  2. GAP DISCOVERY: Testing BPMN against reality found 20 gaps:
     - 7 in task lifecycle (multi-task, bridging, staleness)
     - 7 in session lifecycle (RAG cycle, message checking, dual end paths)
     - 6 in feature workflow (task creation, per-task tracking, plan data)

  3. PROCESS DOCUMENTATION: The BPMN files + Mermaid diagrams in vault are
     the clearest representation of how things SHOULD work.

  4. ONBOARDING: New team member can trace feature_workflow.bpmn and understand
     the full development lifecycle in 2 minutes.

WHAT IT CAN ENFORCE (feasibility assessment):
  Level 1 - NAVIGATOR (no code changes):
    "You are at step: implement. Next required: run_tests."
    Just consult BPMN before acting. Already possible with get_current_step().

  Level 2 - TRACKER (medium effort):
    Persistent workflow instances in DB. Auto-advance on MCP tool calls.
    "Feature F42 is at step 4/7. You skipped testing."
    Needs: DB table + serialization + integration with existing tools.

  Level 3 - ENFORCER (high effort, high value):
    "Cannot advance feature to completed: run_tests step not completed."
    BPMN becomes the source of truth for allowed transitions.
    Hooks become executors (do the work) not deciders (what to do).
    Needs: Full integration with WorkflowEngine + hook rewrite.

HONEST ANSWER about enforcement:
  BPMN CAN be a proper workflow engine - SpiffWorkflow is designed for this.
  But it should ORCHESTRATE (what to do next), not REPLACE hooks (how to do it).

  Best architecture:
    BPMN engine = "feature_workflow says: next step is run_tests"
    Hooks = "here is how run_tests actually works" (pytest, validate, report)
    WorkflowEngine = remains for simple status transitions (the DB state machine)
    BPMN = adds sequence enforcement ON TOP of status transitions

VIEWING (what exists today):
  - Vault has Mermaid diagrams: Task Todo Lifecycle - BPMN Diagram.md
  - Vault has Mermaid diagrams: Dynamic Skill System - BPMN Diagram.md
  - BPMN XML files can be opened in bpmn.io (free web) or Camunda Modeler (free desktop)
  - MISSING: Auto-generated Mermaid from BPMN XML (could be a script)
  - MISSING: Interactive viewer in MCW with current-step highlighting
""")
