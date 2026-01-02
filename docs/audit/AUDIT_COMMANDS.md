# Audit: Commands & Skills

**Part of**: [Infrastructure Audit Report](../INFRASTRUCTURE_AUDIT_REPORT.md)

---

## CRITICAL: Broken Commands

### session-start.md 🔴

References **non-existent tables**:
```sql
-- BROKEN
INSERT INTO claude_family.session_history ...
SELECT FROM claude_family.universal_knowledge ...
SELECT FROM claude_pm.project_feedback ...
```

**Fix**: Replace with:
- `claude.sessions`
- `claude.knowledge`
- `claude.feedback`

### session-end.md 🔴

Same issues - references deprecated tables and uses hardcoded `identity_id = 5`.

---

## Working Commands (18)

| Command | Purpose | Status |
|---------|---------|--------|
| /session-resume | Load previous context | ✅ |
| /session-status | Quick status check | ✅ |
| /session-commit | Commit with session log | ✅ |
| /feedback-check | Check open feedback | ✅ |
| /feedback-create | Create new feedback | ✅ |
| /feedback-list | List feedback | ✅ |
| /todo | Persistent todo management | ✅ |
| /check-compliance | Project compliance | ✅ |
| /review-docs | Doc staleness | ✅ |
| /review-data | Data quality | ✅ |
| /project-init | Initialize project | ✅ |
| /retrofit-project | Retrofit existing | ✅ |
| /phase-advance | Advance phase | ✅ |
| /inbox-check | Check messages | ✅ |
| /check-messages | Check messages | ✅ |
| /broadcast | Send to all | ✅ |
| /team-status | Active sessions | ✅ |
| /knowledge-capture | Capture knowledge | ✅ |

---

## Skills (8)

| Skill | Purpose |
|-------|---------|
| database-operations | SQL validation |
| work-item-routing | Route feedback/features |
| session-management | Session lifecycle |
| code-review | Pre-commit review |
| testing-patterns | Test writing |
| agentic-orchestration | Agent spawning |
| project-ops | Project init/retrofit |
| messaging | Inter-Claude comms |

---

**Version**: 1.0
**Created**: 2026-01-03
**Location**: docs/audit/AUDIT_COMMANDS.md
