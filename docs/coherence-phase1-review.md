# Design Coherence Check — Phase 1: Findings

**Scope**: Claude Family infrastructure docs (10 files)
**Date**: 2026-03-21
**Concepts table**: See `coherence-phase1-analysis.md`

---

## Contradictions

### C1: feedback_type — database-rules omits "improvement"
- **database-rules.md**: valid = `bug, design, question, change, idea`
- **MCP tool** (`server_v2.py` line 4064): valid = `bug, design, idea, question, change, improvement`
- **Impact**: A Claude reading database-rules.md before filing type `improvement` may reject it as invalid.
- **Fix**: Add `improvement` to database-rules.md.

### C2: Table count — global CLAUDE.md (60+) vs project CLAUDE.md (58)
- Same project CLAUDE.md notes 3 new tables added in Entity Catalog, making 58 stale in the same file.
- **Fix**: Align both or drop the count.

### C3: /session-start listed as SOP command but described as optional in the same doc
- **global CLAUDE.md** SOP table: Session workflow → `/session-start`
- **global CLAUDE.md** note: "Manual `/session-start` is optional for extra context loading."
- **Fix**: Annotate the SOP table entry as "(optional)" or remove it.

### C4: working-memory-rules.md references the replaced script `generate_project_settings.py`
- **working-memory-rules.md** line 22: "run `generate_project_settings.py`"
- **Reality**: `sync_project.py` replaced it (its header says "Replaces: generate_project_settings.py").
- **Impact**: High. Following the old instruction bypasses the unified deployment script.
- **Fix**: Update working-memory-rules.md to reference `sync_project.py`.

### C5: "v3 Application Layer" in project CLAUDE.md vs "v2" in MEMORY.md
- Same tools, different version labels. MEMORY.md entry is the older one.
- **Impact**: Low. Historical artifact, not operationally misleading.

---

## Duplicate Definitions

### D1: "Key Procedures" section is copy-pasted twice in project CLAUDE.md
- Lines 160–165 and 167–172 are byte-for-byte identical.
- **Impact**: High. Updates to one copy will not propagate to the other.
- **Fix**: Delete one copy.

### D2: Decision routing split across two rule files
- **storage-rules.md**: "Decision made this session" → Notepad; "Decision future Claudes need" → Memory.
- **working-memory-rules.md**: Only covers the session case, omitting the Memory path.
- **Impact**: Medium. A Claude reading only working-memory-rules.md will store all decisions as session facts.
- **Fix**: Add to working-memory-rules.md: "For decisions future Claudes need, use `remember()` instead."

### D3: Work tracking table in both CLAUDE.md files
- Global and project each define a work tracking table with overlapping but non-identical rows.
- **Impact**: Low. Double maintenance risk; project adds TodoWrite which global omits.
- **Fix**: Consolidate into global; project file references global.

### D4: MCP tool index split across global and project CLAUDE.md
- Global has the general index; project has workflow tools + config tools subset. Neither is complete.
- **Impact**: Low. Config tools (`update_config`, `update_claude_md`, etc.) appear only in project file.
- **Fix**: Add config tools to global CLAUDE.md tool index.

---

## Stale References

### S1: "Stop hook" in testing-rules.md — enforcement no longer exists
- **testing-rules.md**: "The stop hook will remind you to test after modifying 3+ code files."
- **Reality**: `stop_hook_enforcer.py` was merged into `rag_query_hook.py` and deleted. No `Stop` event is registered in `settings.local.json`. Registered events: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PreCompact, PostCompact, SubagentStart, TaskCompleted, ConfigChange.
- **Impact**: High. The rule claims enforcement exists when it does not.
- **Fix**: Remove the stop hook claim. Reimplement as SessionEnd or TaskCompleted hook if the reminder is needed.

### S2: `generate_project_settings.py` in working-memory-rules.md
- Covered under C4. The script exists on disk but `sync_project.py` is the current unified tool.

### S3: `/project-init` in global CLAUDE.md SOP table — skill is named `project-ops`
- **global CLAUDE.md** line 161: New project SOP → `/project-init`
- **Reality**: Skill is `project-ops` at `.claude/skills/project-ops/SKILL.md`. No `project-init` skill exists.
- **Impact**: Medium. A Claude following the SOP table and invoking `/project-init` will fail.
- **Fix**: Update global CLAUDE.md SOP table to reference `project-ops`.

### S4: `/skill-load-memory-storage` in project CLAUDE.md Recent Changes
- No skill by this name exists in `.claude/skills/`.
- **Impact**: Low (historical log, not operational guidance).
- **Fix**: Update the entry to reflect the current skill name or note it was merged/removed.

### S5: Feature reference F113 in system-change-process.md
- Line 41: "Feature: F113 (BPMN Process Coverage + Self-Enforcement)"
- **Impact**: Informational only. The BPMN file referenced does exist.
- **Fix**: Optional — remove feature references from rule files as they are not operationally useful.

---

## Terminology Drift

### T1: `add_build_task` vs `create_linked_task` — no guidance on which to use
- **global CLAUDE.md**: "Create build task" → `add_build_task`
- **project CLAUDE.md**: "A task to do" → `create_linked_task`
- Both exist. `create_linked_task` enforces quality gates (≥100 char description, verification, files). No doc explains when to use each.
- **Fix**: Add: "`create_linked_task` is preferred for feature work; `add_build_task` for quick/informal tasks."

### T2: "Notepad" vs "session facts" — same system, two primary terms
- storage-rules.md uses "Notepad"; working-memory-rules.md uses "Session Facts = Your Notepad"; global CLAUDE.md uses "Notepad (session facts)".
- **Fix**: Standardize on "Notepad" in operational guidance; reserve "session facts" for DB table context.

### T3: "Filing Cabinet" vs "Workfiles" vs "Project Workfiles" — same system
- storage-rules.md: "Filing Cabinet". global CLAUDE.md: "Filing Cabinet (component work)". MEMORY.md: "Project Workfiles". DB table: `claude.project_workfiles`.
- **Fix**: Standardize on "Workfiles" as the system name; "Filing Cabinet" as metaphor/explanation only.

### T4: "Memory" vs "Knowledge" vs "Knowledge System" vs "Cognitive Memory System"
- Four names used across docs for the same system (DB table: `claude.knowledge`, tools: `remember`/`recall_memories`).
- **Fix**: Standardize on "Memory" in prose. Reserve "knowledge table" for DB-level discussion.

### T5: "Stop hook" is not a real Claude Code hook event type
- Covered under S1. The term came from the deleted `stop_hook_enforcer.py`.
- **Fix**: Replace "stop hook" with the accurate mechanism name, or remove entirely.

### T6: Priority scale — "5=low" (database-rules) vs "4=low, 5=backlog" (MCP tool)
- **database-rules.md**: "1=critical, 5=low"
- **MCP tool docstrings**: "1=critical, 2=high, 3=normal, 4=low, 5=backlog"
- **Impact**: Medium. A Claude following database-rules.md sets 5 for "low" items, never using priority 4.
- **Fix**: Update database-rules.md to: "1=critical, 2=high, 3=normal, 4=low, 5=backlog".

---

## Summary

| Category | Count | Highest-impact |
|---|---|---|
| Contradictions | 5 | C4: stale script in working-memory-rules |
| Duplicates | 4 | D1: exact duplicate section in project CLAUDE.md |
| Stale References | 5 | S1: stop hook enforcement claim is false |
| Terminology Drift | 6 | T6: priority scale mismatch |
| **Total** | **20** | |

**Top 7 fixes by operational impact**:
1. S1/T5 — Remove stop hook claim from testing-rules.md (false enforcement)
2. C4/S2 — Update working-memory-rules.md: `sync_project.py` not `generate_project_settings.py`
3. D1 — Delete duplicate "Key Procedures" section in project CLAUDE.md
4. S3 — Fix global CLAUDE.md SOP table: `/project-init` → `project-ops`
5. C1 — Add `improvement` to database-rules.md feedback_type list
6. T6 — Fix priority scale in database-rules.md: 4=low, 5=backlog
7. T1 — Document when to use `add_build_task` vs `create_linked_task`

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: docs/coherence-phase1-review.md
