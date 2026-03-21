# Full Coherence Audit — Consolidated Findings

**Date**: 2026-03-21
**Scope**: All Claude Family infrastructure docs, skills, instructions, memory, Anthropic baseline
**Raw findings**: 58 across 4 sources → **53 unique after dedup**

---

## Source Reports

| Source | Files Checked | Findings | Report |
|--------|--------------|----------|--------|
| Phase 1: Rules + CLAUDE.md | 10 core docs | 20 | [coherence-phase1-review.md](coherence-phase1-review.md) |
| Phase 2a: Skills | 33 skills | 18 | [coherence-skills-audit.md](coherence-skills-audit.md) |
| Phase 2b: Instructions + MEMORY | 12 instructions + 3 memory | 15 | [coherence-instructions-audit.md](coherence-instructions-audit.md) |
| Phase 2c: Anthropic baseline | 10 questions | 5 | Agent output (not written to file) |

---

## Severity Breakdown

| Severity | Count | Description |
|----------|-------|-------------|
| CRITICAL | 0 | — |
| HIGH | 13 | Actively misleading, causes failures |
| MEDIUM | 19 | Confusing, inconsistent, maintenance risk |
| LOW | 21 | Stale but not harmful |
| **Total** | **53** | |

---

## HIGH Priority — Fix These First

### Stale Script/Tool References (fix: find-and-replace)

| # | Finding | Sources | What's Wrong | Fix |
|---|---------|---------|-------------|-----|
| 1 | `generate_project_settings.py` referenced | Phase1-C4, Instr-I11 | Replaced by `sync_project.py` | Update working-memory-rules.md, infrastructure_systems.md |
| 2 | `store_knowledge()` in bpmn-modeling | Skills-H3 | Legacy tool, use `remember()` | Update bpmn-modeling/SKILL.md |
| 3 | `generate_agent_files.py` in agentic-orchestration | Skills-H1 | Script doesn't exist | Remove reference or create script |
| 4 | `python-repl` MCP listed but not configured | Instr-I1 | Not in .mcp.json | Remove from MEMORY.md + CLAUDE.md or add to .mcp.json |
| 5 | `server_v2.py` marked "uncommitted" | Instr-I3 | Has 3+ commits, is production code | Update MEMORY.md gotcha |

### False Claims (fix: remove or correct)

| # | Finding | Sources | What's Wrong | Fix |
|---|---------|---------|-------------|-----|
| 6 | "Stop hook" enforces testing | Phase1-S1 | No Stop hook exists | Remove claim from testing-rules.md |
| 7 | Core protocol: 8 rules documented, 7 exist | Instr-I2 | Rules 3+4 were consolidated | Update MEMORY.md rule mapping |
| 8 | Hook table missing 4 active hooks | Instr-I6 | sql_governance, code_collision, postcompact, task_completed | Update MEMORY.md hook table |

### Wrong Data (fix: correct values)

| # | Finding | Sources | What's Wrong | Fix |
|---|---------|---------|-------------|-----|
| 9 | `feedback_type` incomplete (3 locations) | Phase1-C1, Skills-M6, Instr-I5 | Missing `idea`, `improvement` | Fix database-rules.md, database skill, sql-postgres.instructions.md |
| 10 | Feedback statuses: `fixed`/`implemented` in feature-workflow | Skills-H2 | Legacy values not in WorkflowEngine | Update feature-workflow/SKILL.md |
| 11 | Instruction file count "9" → actually 11 | Instr-I7 | coding-ethos + react-component-architecture added | Update global CLAUDE.md |
| 12 | `synced: false` in markdown template | Instr-I4 | Field deprecated per own standards doc | Remove from markdown.instructions.md |
| 13 | Wrong vault path in sa-plan | Skills-H4 | Missing `workflows/` subfolder | Fix sa-plan/SKILL.md path |

---

## MEDIUM Priority — Causes Confusion

### Contradictions Between Documents

| # | Finding | Sources | Fix |
|---|---------|---------|-----|
| 14 | Phase models conflict: project-ops (5 phases) vs phase-advance (6 phases) | Skills-M2 | Align or document which applies when |
| 15 | `on_hold` feature status in work-item-routing but not in WorkflowEngine | Skills-M3 | Remove `on_hold` from skill |
| 16 | Duplicate "Key Procedures" section in project CLAUDE.md | Phase1-D1 | Delete duplicate |
| 17 | Decision routing: storage-rules covers both paths, working-memory only session | Phase1-D2 | Add Memory path to working-memory-rules |
| 18 | Priority: "5=low" vs "4=low, 5=backlog" | Phase1-T6 | Update database-rules.md to match MCP tool |
| 19 | `session-save` uses invalid memory_type "solution" | Skills-M1 | Change to "decision" |
| 20 | `feature-workflow` promote step uses raw SQL with invalid status | Skills-M7 | Rewrite to use `promote_feedback()` MCP tool |
| 21 | `TODO_NEXT_SESSION.md` referenced in session-management but not generated | Skills-M8 | Remove references |

### Stale Paths and References

| # | Finding | Sources | Fix |
|---|---------|---------|-----|
| 22 | `llms.txt.template.md` doesn't exist | Skills-M4 | Remove from project-ops/SKILL.md |
| 23 | MCP Registry path wrong in doc-keeper | Skills-M5 | Fix to include `mcp-and-tools/` subfolder |
| 24 | `/project-init` in SOP table, skill is `project-ops` | Phase1-S3 | Fix global CLAUDE.md |
| 25 | Table count: "58" in project CLAUDE.md, actual ~63 | Phase1-C2, Instr-I9 | Update or use "60+" |
| 26 | `/session-start` listed as SOP but described as optional | Phase1-C3 | Annotate as optional |
| 27 | infrastructure_systems.md references old deploy scripts | Instr-I11 | Update to `sync_project.py` |
| 28 | MEMORY.md omits `playwright` from MCP table | Instr-I8 | Add playwright entry |

### Anthropic Baseline Mismatches

| # | Finding | Impact | Fix |
|---|---------|--------|-----|
| 29 | `.claude/instructions/` is custom, not native Claude Code | Medium — works via our hook but isn't upstream | Document as custom; native equivalent is `.claude/rules/` with path matching |
| 30 | Only 10 of 24 hook events documented | Low — we don't use the others | Add note listing all available events |
| 31 | `disableAllHooks` claim for agents may be inaccurate | Medium — affects hook behavior assumptions | Verify and correct MEMORY.md |
| 32 | Settings schema has 50+ fields, we document 4 | Low — we use the right ones | No action needed |

---

## LOW Priority — Maintenance Debt (21 items)

| # | Finding | Source |
|---|---------|--------|
| 33 | "v3" vs "v2" Application Layer label drift | Phase1-C5 |
| 34 | Work tracking table in both CLAUDE.md files | Phase1-D3 |
| 35 | MCP tool index split across global/project | Phase1-D4 |
| 36 | `/skill-load-memory-storage` stale path in Recent Changes | Phase1-S4 |
| 37 | F113 reference in system-change-process.md | Phase1-S5 |
| 38 | No guidance on `add_build_task` vs `create_linked_task` | Phase1-T1 |
| 39 | "Notepad" vs "session facts" terminology | Phase1-T2 |
| 40 | "Filing Cabinet" vs "Workfiles" terminology | Phase1-T3 |
| 41 | "Memory" vs "Knowledge" vs "Cognitive Memory" terminology | Phase1-T4 |
| 42 | `check-compliance` audits for retired process router | Skills-L1 |
| 43 | `general-purpose` agent not in agentic-orchestration table | Skills-L2 |
| 44 | `coding-intelligence` skill missing YAML frontmatter | Skills-L3 |
| 45 | `v_project_governance` view existence unverified | Skills-L5 |
| 46 | `skill.md` lowercase in doc-keeper + wpf-ui refs | Skills-L6, Instr-I12 |
| 47 | Hook capture_failure count understated (8 → 11) | Instr-I13 |
| 48 | Empty skill directories (crash-recovery, reinforce-protocol) | Instr-I14 |
| 49 | markdown.instructions.md missing Reports doc type | Instr-I15 |
| 50 | Settings regeneration: MEMORY claims "NOT auto" but hook does auto-run | Instr-I10 |
| 51 | CLAUDE.md loading: ancestor walk + managed policy level undocumented | Baseline |
| 52 | Branch naming: commit-rules adds `task/BT5-*` which global omits | Phase1 |
| 53 | `task/BT5-description` branch pattern only in commit-rules | Phase1 |

---

## Dedup Notes

These findings appeared in multiple sources and were merged:
- **feedback_type incomplete**: Phase1-C1 + Skills-M6 + Instr-I5 → Finding #9
- **Table count stale**: Phase1-C2 + Instr-I9 → Finding #25
- **generate_project_settings.py**: Phase1-C4 + Instr-I11 → Finding #1
- **skill.md lowercase**: Skills-L6 + Instr-I12 → Finding #46
- **Feedback status inconsistency**: Skills-H2 + feature-workflow M7 → Findings #10, #20

---

## Recommended Fix Order

**Batch 1 — Quick wins (find-and-replace, 15 min)**
Findings: 1, 2, 4, 5, 6, 9, 11, 12, 13, 16, 18, 24, 25, 28

**Batch 2 — Skill rewrites (need careful editing, 30 min)**
Findings: 3, 10, 15, 19, 20, 21, 22, 23

**Batch 3 — MEMORY.md overhaul (7, 8, 30, 31, 50 — need verification)**
Findings: 7, 8, 27, 29, 30, 31, 50

**Batch 4 — Design decisions needed (user input required)**
Findings: 14, 17, 29, 38, 39-41

---

**Version**: 1.0
**Created**: 2026-03-21
**Updated**: 2026-03-21
**Location**: docs/coherence-full-audit.md
