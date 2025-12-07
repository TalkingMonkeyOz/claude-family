# Process Library - Claude Family

**Version**: 1.0
**Created**: 2025-12-07
**Status**: Active
**Purpose**: Comprehensive catalog of all processes, workflows, and patterns for AI-assisted development

---

## Overview

This library catalogs all documented processes in the Claude Family ecosystem. Each process has:
- **Trigger patterns** - How to detect when this process should be used
- **Steps** - What to do in order
- **Enforcement level** - How strictly this is enforced
- **Related SOPs/Docs** - Where to find detailed documentation

---

## Process Categories

| Category | Description | Count |
|----------|-------------|-------|
| Session Management | Start/end session workflows | 4 |
| Project Lifecycle | Project creation, phases, archival | 5 |
| Development Workflow | Coding, testing, reviewing | 6 |
| Data Management | Database writes, quality checks | 4 |
| Documentation | Creating, updating, reviewing docs | 4 |
| Communication | Feedback, messaging, coordination | 4 |
| Quality Assurance | Testing, reviews, compliance | 5 |

---

## 1. Session Management Processes

### PROC-SESSION-001: Session Start
**Trigger Patterns**:
- User opens Claude Code
- New conversation starts
- `SessionStart` hook event

**Steps**:
1. Load identity from database
2. Load project context from working directory
3. Query memory graph for relevant context
4. Create session record in `claude.sessions`
5. Check for pending messages/tasks
6. Present startup summary

**Enforcement**: Automated (SessionStart hook)
**SOP**: `SESSION_WORKFLOWS.md`, `/session-start` command

---

### PROC-SESSION-002: Session End
**Trigger Patterns**:
- User says "goodbye", "end session", "done for now"
- Context is getting full
- `SessionEnd` hook event

**Steps**:
1. Update PostgreSQL session record with summary
2. Store reusable patterns in knowledge table
3. Create entities/relations in memory graph
4. Check if documentation needs updating
5. Remind about git operations

**Enforcement**: Semi-automated (SessionEnd hook + prompt)
**SOP**: `SESSION_WORKFLOWS.md`, `/session-end` command

---

### PROC-SESSION-003: Session Commit (End + Git)
**Trigger Patterns**:
- User says "commit", "save and commit"
- Work session complete with code changes

**Steps**:
1. All steps from Session End
2. Review git status/diff
3. Stage appropriate files
4. Create formatted commit message
5. Push to remote

**Enforcement**: Manual (slash command)
**SOP**: `SESSION_WORKFLOWS.md`, `/session-commit` command

---

### PROC-SESSION-004: Session Resume
**Trigger Patterns**:
- Conversation continued from summary
- User references previous work

**Steps**:
1. Load previous session state
2. Restore todo list
3. Check what was in progress
4. Resume from last checkpoint

**Enforcement**: Automated (SessionStart hook --resume)
**SOP**: `SESSION_WORKFLOWS.md`

---

## 2. Project Lifecycle Processes

### PROC-PROJECT-001: Project Initialization
**Trigger Patterns**:
- User says "create new project", "let's build X"
- User says "start a new project"
- User wants to convert something to new project

**Steps**:
1. **STOP** - Confirm user wants new project (not modifying existing)
2. Validate project name (lowercase, hyphens)
3. Create folder at `C:\Projects\{name}\`
4. Generate core documents from templates:
   - CLAUDE.md
   - PROBLEM_STATEMENT.md
   - ARCHITECTURE.md
   - README.md
5. Register in `claude.projects` (phase='planning')
6. Run document scanner
7. Verify compliance

**Enforcement**: Manual (but should use `/project-init`)
**SOP**: `SOP-004-PROJECT-INITIALIZATION.md`, `/project-init` command

---

### PROC-PROJECT-002: Phase Advancement
**Trigger Patterns**:
- User says "advance phase", "move to implementation"
- Project meets requirements for next phase

**Phase Progression**:
```
idea → research → planning → implementation → maintenance → archived
```

**Steps**:
1. Identify current phase
2. Check requirements for next phase:
   - idea→research: Problem statement, user identified
   - research→planning: PROBLEM_STATEMENT.md complete
   - planning→implementation: CLAUDE.md, ARCHITECTURE.md, features defined
   - implementation→maintenance: Core functionality complete
3. If met: Update phase, log transition
4. If not met: Report blockers, offer help

**Enforcement**: Manual + Database constraint on phase values
**SOP**: `/phase-advance` command

---

### PROC-PROJECT-003: Project Retrofit
**Trigger Patterns**:
- Existing project missing governance docs
- Compliance check fails
- User says "bring project up to standard"

**Steps**:
1. Check current compliance
2. For each missing document:
   - Ask user relevant questions
   - Generate from template
3. Update CLAUDE.md to standard
4. Register/update in database
5. Rescan documents
6. Verify 100% compliance

**Enforcement**: Manual
**SOP**: `/retrofit-project` command

---

### PROC-PROJECT-004: Compliance Check
**Trigger Patterns**:
- Before major changes
- After project modifications
- User asks "check compliance"

**Steps**:
1. Query `claude.v_project_governance`
2. Report document status
3. Show compliance percentage
4. If not 100%, suggest retrofit

**Enforcement**: Manual (can be hooked)
**SOP**: `/check-compliance` command

---

### PROC-PROJECT-005: Major Change Assessment
**Trigger Patterns**:
- User requests converting project (to Electron, mobile, etc.)
- User wants to add major technology
- Scope significantly expands

**Steps**:
1. **STOP** - Recognize this is a major change
2. Ask user: "This is a significant architectural change. Options:"
   a) Create new project (fork)
   b) Major refactor of existing (create ADR)
   c) Hold for further discussion
3. If new project: Use PROC-PROJECT-001
4. If refactor: Create ADR, update ARCHITECTURE.md

**Enforcement**: Should be in UserPromptSubmit hook
**SOP**: None (TO BE CREATED)

---

## 3. Development Workflow Processes

### PROC-DEV-001: Feature Implementation
**Trigger Patterns**:
- User says "implement feature X"
- Build task assigned
- Feature moved to in_progress

**Steps**:
1. Verify project in implementation phase
2. Check feature has build_tasks
3. Create/update TodoWrite with tasks
4. For each task:
   a) Mark task in_progress
   b) Implement code
   c) Write/update tests
   d) Mark task completed
5. Update feature status when all tasks done

**Enforcement**: Hook checks phase on build_task creation
**SOP**: `SOP-002-BUILD-TASK-LIFECYCLE.md`

---

### PROC-DEV-002: Bug Fix Workflow
**Trigger Patterns**:
- User reports bug
- Feedback type='bug' created
- Error encountered during work

**Steps**:
1. Create feedback entry (type='bug')
2. Investigate root cause
3. Create build_task if fix needed
4. Implement fix
5. Add test to prevent regression
6. Mark feedback resolved
7. Consider: Add to knowledge if reusable lesson

**Enforcement**: Feedback type constraint
**SOP**: `SOP-002-BUILD-TASK-LIFECYCLE.md`

---

### PROC-DEV-003: Code Review
**Trigger Patterns**:
- PR created
- User asks for review
- Significant code complete

**Steps**:
1. Check code against project standards (CLAUDE.md)
2. Review for:
   - Logic errors
   - Security issues
   - Performance concerns
   - Test coverage
3. Provide feedback
4. If issues found, track as feedback items

**Enforcement**: Manual (reviewer agent available)
**SOP**: `SOP-005-AUTO-REVIEWERS.md`

---

### PROC-DEV-004: Testing Process
**Trigger Patterns**:
- Before commit
- After code changes
- User says "run tests"

**Test Levels**:
- **Level 1** (30s): Type check, lint, schema validation - Before commit
- **Level 2** (2min): API smoke, unit tests - Before push
- **Level 3** (5-10min): E2E, cross-project validation - Before release

**Steps**:
1. Determine appropriate test level
2. Run tests for that level
3. If failures:
   a) Report failures
   b) Create build_tasks for fixes
   c) Block commit/push until fixed

**Enforcement**: PreCommit hook (Level 1)
**SOP**: `SOP-006-TESTING-PROCESS.md`

---

### PROC-DEV-005: Parallel Development (Worktrees)
**Trigger Patterns**:
- Multiple features need parallel work
- Multiple Claude instances on same repo
- Quick fix needed while feature work in progress

**Steps**:
1. Create worktree: `git worktree add -b feature/X ../project-X main`
2. Assign Claude instance to worktree
3. Work independently
4. Merge when complete: `git merge feature/X`
5. Remove worktree: `git worktree remove ../project-X`

**Enforcement**: Manual
**SOP**: `GIT_WORKTREES_FOR_PARALLEL_WORK.md`

---

### PROC-DEV-006: Agent Spawn Pattern
**Trigger Patterns**:
- Task matches agent specialty
- Parallel work beneficial
- Complex task needs specialist

**Steps**:
1. Identify appropriate agent type
2. Prepare workspace (worktree if needed)
3. Spawn agent with clear task description
4. Monitor progress (async or sync)
5. Integrate results

**Enforcement**: Manual
**SOP**: `docs/adr/ADR-003-ASYNC-AGENT-WORKFLOW.md`

---

## 4. Data Management Processes

### PROC-DATA-001: Database Write Validation
**Trigger Patterns**:
- INSERT or UPDATE to claude.* tables
- `mcp__postgres__execute_sql` called

**Steps**:
1. Parse SQL to identify table/columns
2. Check `claude.column_registry` for valid values
3. If constrained column with invalid value:
   - Block the operation
   - Return valid values to user
4. If valid: Allow operation

**Enforcement**: PreToolUse hook + DB CHECK constraints
**SOP**: `ENFORCEMENT_HIERARCHY.md`, `DATA_GATEWAY_MASTER_PLAN.md`

---

### PROC-DATA-002: Data Quality Review
**Trigger Patterns**:
- Scheduled (weekly)
- User requests review
- Before release

**Steps**:
1. Check constraint violations
2. Check orphaned records
3. Check test data patterns
4. Check stale data
5. Report findings with severity
6. Provide fix SQL where possible

**Enforcement**: Scheduled job + reviewer agent
**SOP**: `SOP-005-AUTO-REVIEWERS.md`

---

### PROC-DATA-003: Knowledge Capture
**Trigger Patterns**:
- Bug fix with reusable lesson
- Pattern discovered
- Gotcha/trap encountered

**Steps**:
1. Determine knowledge type (pattern, gotcha, best-practice, etc.)
2. Write concise, actionable content
3. Set applies_to_projects (or NULL for universal)
4. INSERT into `claude.knowledge`

**Enforcement**: Manual (should be prompted at session end)
**SOP**: `SOP-001-KNOWLEDGE-DOCS-TASKS.md`

---

### PROC-DATA-004: Work Item Classification
**Trigger Patterns**:
- User mentions idea, bug, task
- Work item needs tracking

**Decision Matrix**:
| I have... | Put it in... | Type |
|-----------|--------------|------|
| An idea | feedback | idea |
| A bug | feedback | bug |
| A design question | feedback | question |
| A change request | feedback | change |
| A feature to build | features | - |
| A task to do | build_tasks | code/test |
| Session work | TodoWrite | - |

**Enforcement**: Column registry + hook
**SOP**: `SOP-001-KNOWLEDGE-DOCS-TASKS.md`

---

## 5. Documentation Processes

### PROC-DOC-001: Document Creation
**Trigger Patterns**:
- New decision (ADR needed)
- New procedure (SOP needed)
- Architecture change (update needed)

**Steps**:
1. Identify document type
2. Use appropriate template
3. Fill required sections
4. Add version footer
5. Register in database (scanner or manual)

**Enforcement**: Manual
**SOP**: `SOP-003-DOCUMENT-CLASSIFICATION.md`

---

### PROC-DOC-002: Document Staleness Check
**Trigger Patterns**:
- Scheduled (weekly)
- Session start
- User requests review

**Steps**:
1. Query documents not updated in threshold
2. Check critical docs (CLAUDE.md, ARCHITECTURE.md)
3. Check for missing file references
4. Report findings
5. Archive documents with missing files (optional)

**Enforcement**: Scheduled job + reviewer agent
**SOP**: `reviewer_doc_staleness.py`

---

### PROC-DOC-003: CLAUDE.md Update
**Trigger Patterns**:
- Session end
- Architecture change
- Significant code change

**Steps**:
1. Update "Recent Changes" section
2. Update version number
3. Update "Updated" date
4. If architecture changed: Update Architecture Overview
5. If procedures changed: Update Key Procedures

**Enforcement**: SessionEnd hook (reminder)
**SOP**: `SESSION_WORKFLOWS.md`

---

### PROC-DOC-004: ADR Creation
**Trigger Patterns**:
- Significant technical decision made
- Alternative approaches considered
- Future Claude needs context

**Steps**:
1. Create `ADR-XXX-title.md` in `docs/adr/`
2. Fill sections:
   - Context
   - Decision
   - Consequences
   - Alternatives considered
3. Link from ARCHITECTURE.md

**Enforcement**: Manual
**SOP**: None (standard ADR format)

---

## 6. Communication Processes

### PROC-COMM-001: Feedback Creation
**Trigger Patterns**:
- User reports issue
- Idea generated
- Question arises
- Change needed

**Steps**:
1. Determine feedback type (bug, design, question, change, idea)
2. Create entry in `claude.feedback`
3. Set priority (1-5)
4. Link to project
5. Notify if urgent

**Enforcement**: Column registry constraint on type
**SOP**: `/feedback-create` command

---

### PROC-COMM-002: Message Check
**Trigger Patterns**:
- Session start
- User asks about messages
- Periodic check

**Steps**:
1. Query `mcp__orchestrator__check_inbox`
2. Display pending messages
3. Acknowledge read messages

**Enforcement**: SessionStart hook
**SOP**: `/inbox-check` command

---

### PROC-COMM-003: Broadcast Message
**Trigger Patterns**:
- Important announcement
- Cross-instance coordination needed

**Steps**:
1. Compose message
2. Set priority
3. Send via `mcp__orchestrator__broadcast`

**Enforcement**: Manual
**SOP**: `/broadcast` command

---

### PROC-COMM-004: Team Status Check
**Trigger Patterns**:
- User asks about active instances
- Coordination needed

**Steps**:
1. Query `mcp__orchestrator__get_active_sessions`
2. Display active instances and their work

**Enforcement**: Manual
**SOP**: `/team-status` command

---

## 7. Quality Assurance Processes

### PROC-QA-001: Pre-Commit Check
**Trigger Patterns**:
- Git commit attempted
- PreCommit hook event

**Steps**:
1. Schema validation (if schema files changed)
2. Sensitive file check (credentials, env files)
3. Basic lint/type check
4. Block if issues found

**Enforcement**: PreCommit hook (blocking)
**SOP**: `SOP-006-TESTING-PROCESS.md`

---

### PROC-QA-002: Schema Validation
**Trigger Patterns**:
- Database view/table changed
- Before release

**Steps**:
1. Identify consumers of changed object
2. Verify all expected columns exist
3. Report any missing columns/types

**Enforcement**: Manual (script available)
**SOP**: `SOP-006-TESTING-PROCESS.md`

---

### PROC-QA-003: API Smoke Test
**Trigger Patterns**:
- Before release
- After API changes

**Steps**:
1. Hit all API endpoints
2. Verify 200 (or expected) status
3. Report failures

**Enforcement**: Manual (Level 2 test)
**SOP**: `SOP-006-TESTING-PROCESS.md`

---

### PROC-QA-004: Cross-Project Validation
**Trigger Patterns**:
- Shared infrastructure changed
- Before merging to main

**Steps**:
1. Identify projects using changed files
2. Run their smoke tests
3. Report any failures

**Enforcement**: Manual (Level 3 test)
**SOP**: `SOP-006-TESTING-PROCESS.md`

---

### PROC-QA-005: Compliance Verification
**Trigger Patterns**:
- Before release
- After significant changes
- User requests

**Steps**:
1. Check project governance (docs exist)
2. Run data quality review
3. Run doc staleness review
4. Report aggregate compliance

**Enforcement**: Scheduled + Manual
**SOP**: `/check-compliance` command

---

## Agentic Workflow Patterns (From Research)

These patterns from industry research should be integrated:

### Pattern: Planning
**Source**: Weaviate, LangGraph
**Use**: Complex tasks needing breakdown
**Implementation**: Sequential thinking MCP + TodoWrite

### Pattern: Tool Use Selection
**Source**: Anthropic, AWS
**Use**: Choose appropriate tool for task
**Implementation**: Existing Claude capability + hook guidance

### Pattern: Reflection
**Source**: Weaviate, Microsoft
**Use**: Self-check before completing
**Implementation**: Post-action verification step

### Pattern: Sequential Orchestration
**Source**: Microsoft, AWS
**Use**: Steps must run in order
**Implementation**: Coordinator agents

### Pattern: Concurrent Orchestration
**Source**: Microsoft
**Use**: Independent tasks run in parallel
**Implementation**: Multiple agent spawns

### Pattern: Handoff
**Source**: Microsoft Magentic
**Use**: Specialized agent takes over
**Implementation**: Orchestrator spawn_agent

---

## Process Registry Requirements

For the UserPromptSubmit hook to route properly, each process needs:

```yaml
process_id: PROC-XXX-NNN
name: "Process Name"
category: session|project|dev|data|doc|comm|qa
trigger_patterns:
  - regex: "create new project"
  - regex: "let's build"
  - keywords: ["new project", "start project"]
enforcement: automated|semi-automated|manual
steps:
  - step: 1
    action: "Do something"
    blocking: true|false
sop_ref: "SOP-XXX.md or null"
command_ref: "/command or null"
```

---

## Next Steps

1. Create database schema for process registry
2. Populate registry with all processes above
3. Build UserPromptSubmit hook that queries registry
4. Test trigger pattern matching
5. Implement enforcement routing

---

**Version**: 1.0
**Created**: 2025-12-07
**Location**: C:\Projects\claude-family\docs\PROCESS_LIBRARY.md
