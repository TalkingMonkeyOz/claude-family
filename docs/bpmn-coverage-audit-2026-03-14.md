---
projects:
- claude-family
tags:
- bpmn
- audit
- infrastructure
synced: false
---

# BPMN Coverage Audit — 2026-03-14

## Summary

- **Total BPMN models**: 66 files across 6 directories
- **Active hook scripts (registered in settings)**: 14 operational scripts
- **Hook scripts with dedicated BPMN model**: 9 / 14 (64%)
- **Hook scripts covered only by composite model**: 3 / 14 (21%)
- **Hook scripts with no BPMN coverage**: 2 / 14 (14%)
- **Plugin scripts with no BPMN coverage**: 4 additional scripts

Overall coverage is adequate at the composite level but has meaningful gaps at L2 detail for enforcement scripts added in early 2026.

See [[knowledge-vault/10-Projects/Project-Metis/bpmn-coverage-audit-2026-03-14-detail]] for full tables and gap analysis.

---

## Priority Gaps

### High Priority

1. **`sql_governance_hook.py` — no dedicated model**. Added 2026-03-09 for SQL access control. `schema_governance.bpmn` covers schema design, not runtime enforcement. Needs `sql_access_control.bpmn` or a `hook_chain.bpmn` extension.

2. **Plugin validation chain — no BPMN**. Three scripts (`validate_db_write.py`, `validate_phase.py`, `validate_parent_links.py`) run on every `mcp__postgres__execute_sql` call. A single `db_write_enforcement.bpmn` would close this gap.

3. **`session_startup_hook_enhanced.py` — no dedicated model**. Startup logic (session dedup, identity resolution, health check, state loading) is embedded in `session_lifecycle.bpmn` but not isolated. A standalone L2 `session_startup.bpmn` is warranted given this hook's criticality.

### Medium Priority

4. **`task_discipline_hook.py` — composite coverage only**. Task-map staleness check, shared-list mode, and gated-tool enforcement are complex enough for a dedicated model.

5. **`context_injector_hook.py` — no standalone model**. Folded into `content_validation.bpmn` alongside standards validation. These are distinct processes.

### Low Priority

6. **`hook_data_fallback.py` — WAL pattern not modeled**. Library module used by 5 hooks. A `hook_fallback_wal.bpmn` would document the retry/replay pattern for ops runbooks.

7. **`context_monitor_statusline.py` — no model**. StatusLine display concern, lowest risk.

---

## Model Health

L1 architecture models (`L0_claude_family.bpmn`, `L1_*.bpmn`) and composite L2 models (`hook_chain.bpmn`, `session_lifecycle.bpmn`) are structural design documents and are not expected to align 1:1 with scripts. No broken or invalid models were identified.

---

**Version**: 1.0
**Created**: 2026-03-14
**Updated**: 2026-03-14
**Location**: docs/bpmn-coverage-audit-2026-03-14.md
