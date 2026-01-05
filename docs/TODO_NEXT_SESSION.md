# Next Session TODO

**Last Updated**: 2026-01-05
**Last Session**: Implemented Boss-Worker Architecture - 70% token reduction

---

## Priority 1: Boss-Worker Architecture (COMPLETED)

- [x] Research progressive discovery pattern for orchestrator ✅
- [x] Implement search_agents tool ✅ (server.py:557-638)
- [x] Update ORCHESTRATOR_MCP_AUDIT.md with resolution ✅
- [x] Implement usage tracking ✅ (Fixed session_id mismatch)
- [x] **Boss-Worker Architecture** ✅ (2026-01-05)
  - Reduced global MCPs: 7 → 3 (orchestrator, postgres, sequential-thinking)
  - Token reduction: 42k → 12k (~70% savings)
  - Added mui-coder-sonnet agent (Sonnet for MUI design quality)
  - Added git-haiku agent (pure git operations)
  - Updated database project_type_configs
  - Updated vault docs (Orchestrator MCP.md v4.0)
- [ ] Update spawn_agent to use string instead of enum (optional)

---

## Priority 2: Standards System

- [ ] Add C#, TypeScript/MUI, Rust standards to database
- [ ] Add Azure standards (Bicep, Functions, Logic Apps)
- [ ] Add Security/OWASP standards
- [ ] Regenerate all standards files
- [ ] Test SessionStart loads standards correctly

---

## Priority 3: Vault/Documentation

- [ ] Complete YAML frontmatter for vault docs (0% compliance)
- [ ] Split oversized vault documents (3 files)
- [ ] Tune RAG threshold 0.50 to 0.40
- [ ] Update vault documentation with standards system docs
- [ ] Consolidate documentation process into single source
- [ ] Decide on ~/.claude/instructions/ files fate

---

## Priority 4: Database Cleanup

- [ ] Audit unused database tables for project/work tracking
- [ ] Plan database schema for enforced project work compliance
- [ ] Add FK constraints to prevent orphaned records

---

## Priority 5: Session/Hooks

- [ ] Test complete session lifecycle end-to-end
- [ ] Investigate startup warning: Config deployment skipped
- [ ] Research stop hook enforcement (make more active)

---

## Backlog

- [ ] Test ATO project - Verify logic gates, data capture
- [ ] Create ATO-Infrastructure project with Azure + MS Learn MCPs
- [ ] Review other projects for duplicate session commands

---

## Open Feedback (5 items)

| Type | Description | Priority |
|------|-------------|----------|
| design | Claude Launcher: Desktop App | 1 |
| design | Claude Launcher: Startup Config | 2 |
| design | MCW: Claude Config Tree View | 2 |
| design | MCW: Observability Dashboard | 2 |
| change | Documentation Keeper Agent | medium |

---

**Database Stats**:
- Pending todos: ~34 items (cleaned from 100+)
- Open feedback: 5 items
- Active features: 0

---

**Version**: 7.0
**Created**: 2026-01-02
**Updated**: 2026-01-03
**Location**: docs/TODO_NEXT_SESSION.md
