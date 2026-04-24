# V3 Push Session — Handoff 2026-04-24 (late)

## Shipped this session (4 commits on master)

| Commit | Change |
|--------|--------|
| `cbbf21e` | B0 context-bloat trim — title-only injection (est. ~13K/prompt saved) |
| `cc5772e` | P5 Stage 1 — `kg_nodes_view` VIEW + `kg_nodes_parity_log` table + `kg_nodes_parity_check.py` daily job. 7-day canary clock started. |
| `cc5de8b` | FB331 — `standards_validator` path-scoping. `.mcp.json` / `settings.local.json` / `CLAUDE.md` blocks now gated on workspace membership. 4 regression tests. |
| `7549514` | FB330 — `deprecated_alias()` decorator + 14 legacy tool wrappers. Dict responses now carry `_deprecation` envelope. 3 decorator tests. |

## Verified this session (no code change)

- W2.P2 `read()` API already supports workfile + entity + domain_concept with TOC.
- W3.P4 shadow scaffolding: 4a decomposer, 4b delegation JSONL, 4c auto-checkpoint all LIVE.
- P5 Stage 1 row parity baseline: 3331 (2659 memory + 640 entity + 32 article_section).

## Canary clocks running

- **P5 Stage 1 parity** — started 2026-04-24. Earliest Stage 2 eligibility: 2026-05-01 (need 7 green days).
- **FB330 alias observation** — new deprecation envelope goes live after MCP restart. Count non-zero legacy calls in `claude.mcp_usage` daily; M1 deletion eligible once counts hit zero.

## Outstanding (next session pick)

- **#779** W3.P4d RECALL-FIRST hook (BPMN-first)
- **#780** W2.P3 CPoU pilot — 5 hook files (was stretch goal; not critical path)
- **#784** Model `standards_validator` governance in BPMN
- **#774** (idea) stamp out a reference tempdir fixture for HAL F245
- **13 stale todos** (10–26 days) — cleanup sprint available
- **64 pending feedback items**

## Blocked / gated

- **W3.P4e** protocol compression 9→4 — needs 7-day observation (#753)
- **W4 P5 Stages 2–5** — 14+14+7 days of Stage 1 canary + dual-write observation
- **W5 P6 + P7** — blocked on W4

## Known issues

- MCP `project-tools` disconnected at end of session; `/mcp` reconnect failed. Restart recovers.
- FB330 decorators live in code but not yet in running MCP process — next session start picks them up.

## Rollback notes (if anything flakes)

- B0: `git revert cbbf21e` — inlined previews return.
- P5.S1: `DROP VIEW claude.kg_nodes_view; DROP TABLE claude.kg_nodes_parity_log; DELETE FROM claude.scheduled_jobs WHERE job_name='kg_nodes_parity_check';` — < 30s, zero data risk.
- FB331: `git revert cc5de8b` — restores basename-only blocks.
- FB330: `git revert 7549514` — removes decorator; legacy tools revert to plain responses.

---
**Version**: 1.0
**Created**: 2026-04-24
**Location**: docs/handoffs/2026-04-24-v3-push-session-end.md
