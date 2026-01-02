# Next Session TODO

**Last Updated**: 2026-01-03
**Last Session**: Comprehensive infrastructure audit

---

## 🔴 CRITICAL - Fix Immediately

1. **session-start.md** - References non-existent tables:
   - `claude_family.session_history` → `claude.sessions`
   - `claude_family.universal_knowledge` → `claude.knowledge`
   - `claude_pm.project_feedback` → `claude.feedback`

2. **session-end.md** - Same deprecated table references

---

## Completed This Session

- [x] Comprehensive infrastructure audit (10 phases)
- [x] Created audit reports: `docs/INFRASTRUCTURE_AUDIT_REPORT.md`
- [x] Detailed sub-reports in `docs/audit/`
- [x] Verified all hooks working correctly
- [x] Confirmed best practices compliance

---

## Audit Findings Summary

| Area | Health | Issues |
|------|--------|--------|
| Database | 69% | 1 duplicate FK, 10 missing indexes |
| Hooks | 85% | Minor race condition in todo_sync |
| Commands | 🔴 | 2 broken commands |
| Vault | 68% | 9 broken links, 0% YAML compliance |

---

## Priority Actions

1. Fix session-start.md and session-end.md
2. Add 10 missing indexes on FK columns
3. Fix 9 broken wiki-links in vault
4. Add YAML frontmatter to vault docs

---

**Version**: 5.0
**Created**: 2026-01-02
**Updated**: 2026-01-03
**Location**: docs/TODO_NEXT_SESSION.md
