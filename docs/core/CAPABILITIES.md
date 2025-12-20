# Claude Family Capabilities

**Document Type**: Reference
**Version**: 1.0
**Created**: 2025-12-08
**Status**: Active
**Purpose**: Central documentation of all Claude Family capabilities

---

## Overview

This document catalogs all capabilities available to Claude Family members:
- **16** slash commands
- **28** agent types
- **13** scheduled jobs
- **6** active hooks
- **8** MCP servers

---

## 1. Slash Commands

Available via `/command-name` in any Claude session.

### Session Management

| Command | Purpose |
|---------|---------|
| `/session-start` | Start session, log to database, load context |
| `/session-end` | End session, save summary and next steps |
| `/session-resume` | Resume from previous session state |
| `/session-commit` | Commit changes with session context |

### Communication

| Command | Purpose |
|---------|---------|
| `/broadcast` | Send message to all Claude instances |
| `/inbox-check` | Check for pending messages |
| `/team-status` | View active Claude instances and their work |

### Feedback & Issues

| Command | Purpose |
|---------|---------|
| `/feedback-check` | View open feedback for current project |
| `/feedback-create` | Create new feedback item |
| `/feedback-list` | List all feedback with filters |

### Project Management

| Command | Purpose |
|---------|---------|
| `/project-init` | Initialize new project with governance docs |
| `/retrofit-project` | Add governance docs to existing project |
| `/phase-advance` | Advance project to next phase |

### Quality & Compliance

| Command | Purpose |
|---------|---------|
| `/check-compliance` | Verify project against standards |
| `/review-docs` | Run documentation quality review |
| `/review-data` | Run data quality review |

---

## 2. Agent Types

Spawnable via `mcp__orchestrator__spawn_agent`. Organized by tier.

### Tier 1: Fast Execution (Haiku - $0.01-0.08/task)

| Agent | Use Case | MCP Servers |
|-------|----------|-------------|
| `lightweight-haiku` | Simple file operations | filesystem |
| `coder-haiku` | New features, refactoring, bug fixes | filesystem, orchestrator |
| `python-coder-haiku` | Python scripts, REPL testing, DB work | filesystem, postgres, python-repl |
| `csharp-coder-haiku` | C#/.NET, WPF, Entity Framework | filesystem, roslyn |
| `tester-haiku` | Unit tests, integration tests | filesystem |
| `debugger-haiku` | Run tests, analyze failures | filesystem (read-only) |
| `web-tester-haiku` | E2E web testing with Playwright | playwright, filesystem |
| `nextjs-tester-haiku` | Next.js/React testing | playwright, filesystem, postgres |
| `screenshot-tester-haiku` | Visual regression testing | playwright, filesystem |
| `computer-use-haiku` | GUI testing with Computer Use | filesystem |
| `sandbox-haiku` | Isolated Docker execution | filesystem |
| `ux-tax-screen-analyzer` | ATO wizard screen analysis | postgres, playwright |

### Tier 2: Analysis & Coordination (Sonnet - $0.10-0.35/task)

| Agent | Use Case | MCP Servers |
|-------|----------|-------------|
| `reviewer-sonnet` | Code review, LLM-as-Judge | tree-sitter (read-only) |
| `security-sonnet` | Security audits, OWASP checks | tree-sitter, sequential-thinking (read-only) |
| `analyst-sonnet` | Research, documentation, architecture | sequential-thinking, memory |
| `planner-sonnet` | Sprint planning, task breakdown | sequential-thinking |
| `test-coordinator-sonnet` | Orchestrate parallel test suites | filesystem, postgres, sequential-thinking |
| `review-coordinator-sonnet` | Multi-aspect code review | filesystem, postgres, sequential-thinking |
| `refactor-coordinator-sonnet` | Large refactoring coordination | filesystem, postgres, sequential-thinking |
| `agent-creator-sonnet` | Create new agent profiles | filesystem, postgres, sequential-thinking |
| `onboarding-coordinator-sonnet` | New project onboarding | filesystem, postgres, sequential-thinking |
| `doc-reviewer-sonnet` | Documentation quality review | filesystem, postgres, tree-sitter |
| `data-reviewer-sonnet` | Database data quality review | postgres |

### Tier 3: Deep Reasoning (Opus - $0.72-1.00/task)

| Agent | Use Case | MCP Servers |
|-------|----------|-------------|
| `architect-opus` | System design, complex decisions | sequential-thinking, memory |
| `security-opus` | Deep security audits, threat modeling | sequential-thinking (read-only) |
| `researcher-opus` | Complex analysis, tech evaluation | sequential-thinking, memory (read-only) |

### Tier 4: Local Models (FREE)

| Agent | Use Case | MCP Servers |
|-------|----------|-------------|
| `local-reasoner-deepseek` | Math, logic, privacy-sensitive | ollama (read-only) |
| `local-coder-qwen` | Code completion, simple implementations | ollama (read-only) |

---

## 3. Scheduled Jobs

Configured in `claude.scheduled_jobs`. Active jobs run on schedule.

### Document Management

| Job | Description | Schedule |
|-----|-------------|----------|
| Document Scanner | Index project docs to `claude.documents` | Weekly |
| Documentation Audit | Check all docs for staleness | Monthly |
| doc-staleness-review | Flag stale documentation | Weekly |
| Link Checker | Verify file paths exist | Weekly |
| Orphan Report | Find unlinked documents | Weekly |

### Data Quality

| Job | Description | Schedule |
|-----|-------------|----------|
| data-quality-review | Scan for test data and issues | Daily |
| governance-compliance-check | Verify governance documents | Weekly |

### System Maintenance

| Job | Description | Schedule |
|-----|-------------|----------|
| PostgreSQL Backup | Backup database to OneDrive | Weekly |
| MCP Memory Sync | Sync PostgreSQL to MCP memory | Daily |
| Review Local LLM Usage | Check llama3.3 usage | Weekly |
| Anthropic Docs Monitor | Check for new features/updates | Daily |
| sync-anthropic-usage | Sync API usage for budgeting | Weekly |

---

## 4. Active Hooks

Configured in `.claude/hooks.json`. Run automatically on events.

### SessionStart
- **session_startup_hook.py**: Auto-log session, load state, check messages

### SessionEnd
- **check_doc_updates.py**: Check if docs need updating
- **Prompt**: Remind to save session state

### UserPromptSubmit
- **process_router.py**: Route prompt to appropriate workflow, inject standards

### PreToolUse
- **validate_claude_md.py**: Validate CLAUDE.md on Write/Edit
- **validate_db_write.py**: Check column_registry before SQL writes
- **validate_phase.py**: Check project phase for build_tasks
- **validate_parent_links.py**: Prevent orphan creation

### PostToolUse
- **inbox reminder**: After checking inbox

### PreCommit
- **pre_commit_check.py**: Run Level 1 tests before commits

---

## 5. MCP Servers

Always-available servers for Claude sessions.

| Server | Purpose | Key Tools |
|--------|---------|-----------|
| `postgres` | Database access | execute_sql, list_schemas, explain_query |
| `memory` | Persistent knowledge graph | create_entities, search_nodes, add_observations |
| `filesystem` | File operations | read_file, write_file, list_directory |
| `orchestrator` | Agent spawning, messaging | spawn_agent, send_message, broadcast |
| `sequential-thinking` | Complex problem solving | sequentialthinking |
| `tree-sitter` | Code structure analysis | parse_file, get_symbols |
| `python-repl` | Python execution | execute_python, install_package |
| `playwright` | Web automation | navigate, click, screenshot |

---

## 6. Database Workflows

Key tables and their purposes.

### Work Tracking

| Table | Purpose |
|-------|---------|
| `claude.feedback` | Ideas, bugs, questions |
| `claude.features` | Approved features to build |
| `claude.build_tasks` | Individual implementation tasks |
| `claude.sessions` | Work sessions with summaries |

### Knowledge & State

| Table | Purpose |
|-------|---------|
| `claude.knowledge` | Shared knowledge items |
| `claude.session_state` | Saved todos, focus, next steps |
| `claude.documents` | Indexed documentation |
| `claude.column_registry` | Valid values for constrained columns |

### Communication

| Table | Purpose |
|-------|---------|
| `claude.messages` | Inter-Claude messages |
| `claude.scheduled_jobs` | Automated job configs |
| `claude.reminders` | Timed reminders |

---

## 7. Standards Documents

Located in `docs/standards/`. Injected by process router based on task type.

| Standard | When Used |
|----------|-----------|
| DEVELOPMENT_STANDARDS.md | All code work |
| UI_COMPONENT_STANDARDS.md | UI/component tasks |
| API_STANDARDS.md | API/endpoint work |
| DATABASE_STANDARDS.md | Database/SQL tasks |
| WORKFLOW_STANDARDS.md | Process/workflow tasks |
| COMPLIANCE_CHECKLIST.md | Compliance audits |

---

## 8. Enforcement Status

How each capability is enforced across the Claude Family.

### Fully Automated (No user action needed)

| Capability | Mechanism | Scope |
|------------|-----------|-------|
| Session logging | SessionStart hook | All 4 projects |
| Standards injection | UserPromptSubmit hook | All 4 projects |
| CLAUDE.md validation | PreToolUse hook | All 4 projects |
| Column registry validation | PreToolUse hook | All 4 projects |
| Parent link validation | PreToolUse hook | All 4 projects |
| PreCommit tests | PreCommit hook | All 4 projects |

### Semi-Automated (Prompts/reminders)

| Capability | Mechanism | Gap |
|------------|-----------|-----|
| Session end | SessionEnd hook prompt | User can ignore |
| Testing requirements | Process router injection | Advisory only |
| Documentation updates | SessionEnd hook | Advisory only |

### Manual (User must invoke)

| Capability | Trigger | Gap |
|------------|---------|-----|
| Agent spawning | User request | Not enforced |
| /check-compliance | User invokes | No scheduled audit |
| /review-docs | User invokes | No scheduled audit |
| /review-data | User invokes | No scheduled audit |
| Message acknowledgment | User reads | No enforcement |

### Scheduled (Runs automatically on schedule)

| Capability | Schedule | Status |
|------------|----------|--------|
| Document Scanner | Weekly | **ACTIVE** |
| doc-staleness-review | Weekly | **ACTIVE** |
| data-quality-review | Daily | **ACTIVE** |
| consistency-check | Daily | **ACTIVE** (NEW) |
| Anthropic Docs Monitor | Daily | **ACTIVE** |
| MCP Memory Sync | Daily | **ACTIVE** |

### Not Yet Implemented

| Capability | Plan |
|------------|------|
| Compliance audits | Scheduler → Message → Claude reads → Runs audit |
| Test enforcement | Level 2/3 tests before push/release |
| Review escalation | Block releases if critical issues |

---

## Quick Reference

### Start a Session
```
/session-start
```

### End a Session
```
/session-end
```

### Spawn an Agent
```sql
mcp__orchestrator__spawn_agent(
  agent_type="coder-haiku",
  task="Implement feature X",
  workspace_dir="C:/Projects/myproject"
)
```

### Send a Message
```sql
mcp__orchestrator__send_message(
  to_project="mission-control-web",
  message_type="notification",
  subject="Update",
  body="Work complete on feature X"
)
```

### Check Valid Values
```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'feedback' AND column_name = 'status';
```

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial version |
| 1.1 | 2025-12-08 | Added Section 8: Enforcement Status |

---

**Location**: C:\Projects\claude-family\docs\CAPABILITIES.md
