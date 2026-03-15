# Inter-Claude Messaging System Audit

**Date**: 2026-03-15
**Total Messages**: 208
**Detail**: See [messaging-audit-2026-03-15-detail.md](messaging-audit-2026-03-15-detail.md)

---

## Key Findings

**CRITICAL: 109 unactioned messages, oldest pending 109 days (2025-11-26).** Only 8 of 208 messages (3.8%) have ever been `actioned`. The inbox is effectively unmaintained.

- 19 messages routed to non-existent projects — will never be delivered
- `claude-desktop-config` has 4 pending messages; last session was 2026-01-12 (63 days ago)
- 1 urgent breaking-change notification (`nimbus-mui → monash-nimbus-reports`, 2026-03-10) still pending
- ATO workspace duplicate: `ATO-tax-agent` and `ATO-Tax-Agent` both exist as active workspaces
- `send_message()` accepts any arbitrary `to_project` string — no workspace validation

---

## Status Breakdown

| Status | Count |
|--------|-------|
| acknowledged | 93 |
| read | 85 |
| pending | 22 |
| actioned | 8 |
| deferred | 0 |

## Message Type Breakdown

| Type | Count |
|------|-------|
| notification | 83 |
| task_request | 47 |
| status_update | 38 |
| broadcast | 26 |
| question | 12 |
| handoff | 2 |

## Volume by Month

| Month | Count |
|-------|-------|
| 2025-11 | 15 |
| 2025-12 | 109 |
| 2026-01 | 52 |
| 2026-02 | 11 |
| 2026-03 | 21 |

Peak: December 2025 (system rollout). Volume dropped sharply since.

---

## Data Quality Issues

| Issue | Count | Severity |
|-------|-------|----------|
| Messages to non-existent `to_project` | 19 | High |
| ATO duplicate workspaces | 2 | Medium |
| `claude-desktop-config` pending (project inactive 63d) | 4 | Medium |
| `actioned` rate only 3.8% | 200 of 208 | High |
| Urgent unactioned: keyring breaking change notification | 1 | High |
| `NULL` from_project (legacy, no sender) | ~15 | Low |

---

## Recommended Actions

1. **Immediate**: Action or defer `nimbus-mui → monash-nimbus-reports` urgent keyring notification (2026-03-10)
2. **Bulk deferred**: All messages older than 60 days still in `pending`/`acknowledged`
3. **Deactivate `claude-desktop-config`** workspace or archive — messages unreachable
4. **Fix ATO duplication**: Deactivate `ATO-tax-agent`, keep `ATO-Tax-Agent` as canonical
5. **Add validation** in `send_message()` — reject `to_project` not in `claude.workspaces`
6. **Triage task_requests/questions**: 47 task requests + 12 questions never actioned

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: C:\Projects\claude-family\docs\messaging-audit-2026-03-15.md
