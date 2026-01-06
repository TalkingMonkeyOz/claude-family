# Next Session TODO

**Last Updated**: 2026-01-06
**Last Session**: Implemented Agent Coordination System (context injection, status tracking, boss control)

---

## Priority 1: Agent Coordination System (COMPLETED 2026-01-06)

- [x] Created `claude.context_rules` table (8 seed rules for DB-driven standards injection)
- [x] Created `claude.agent_status` table (real-time agent progress tracking)
- [x] Created `claude.agent_commands` table (boss-to-agent control: ABORT, REDIRECT, etc.)
- [x] Added 5 new MCP tools:
  - `get_context_for_task` - Compose context from DB rules
  - `update_agent_status` - Agent reports progress
  - `get_agent_statuses` - Boss monitors agents
  - `send_agent_command` - Boss controls agents
  - `check_agent_commands` - Agent checks for commands
- [x] Enhanced spawn_agent with auto-context injection
- [x] Updated vault docs (Orchestrator MCP.md v4.0)

---

## Priority 2: Missing Standards (NEW)

- [ ] Add sql-postgres standard to `claude.coding_standards`
- [ ] Verify all `context_rules.inject_standards` have matching DB entries
- [ ] Add winforms standard content to database

---

## Priority 3: Session Handoff Fix (NEW)

- [ ] Fix /session-resume to query database instead of TODO file
- [ ] Or: Auto-update TODO_NEXT_SESSION.md in /session-end workflow
- [ ] Test complete session lifecycle end-to-end

---

## Priority 4: Expand Native Instructions

- [ ] Add rust.instructions.md to ~/.claude/instructions/
- [ ] Add azure.instructions.md (Bicep, Functions, Logic Apps)
- [ ] Add docker.instructions.md
- [ ] Test file-type auto-apply works

---

## Priority 5: Standards Validator Enhancement (OPTIONAL)

- [ ] Implement forbidden_patterns in standards_validator.py
- [ ] Implement required_patterns checks
- [ ] Implement naming_checks
- [ ] Add more validation rules to database

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

**Version**: 9.0
**Created**: 2026-01-02
**Updated**: 2026-01-06
**Location**: docs/TODO_NEXT_SESSION.md
