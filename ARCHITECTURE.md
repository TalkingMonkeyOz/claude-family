# Architecture - Claude Family Infrastructure

**Project**: claude-family
**Version**: 1.2
**Updated**: 2025-12-09
**Status**: Active

---

## Overview

Claude Family is the infrastructure layer that enables coordinated AI-assisted software development across multiple Claude Code instances. It provides shared configuration, commands, scripts, and a PostgreSQL-backed state management system.

```
┌─────────────────────────────────────────────────────────────────┐
│                    User (John) - Desktop                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│   │ Claude Code  │  │ Claude Code  │  │ Claude Code  │        │
│   │ Instance #1  │  │ Instance #2  │  │ Instance #3  │        │
│   └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│          │                 │                 │                 │
│          └────────────────┬┴─────────────────┘                 │
│                           │                                    │
│   ┌───────────────────────▼─────────────────────────────────┐  │
│   │              Shared Infrastructure Layer                 │  │
│   │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │  │
│   │  │ CLAUDE.md   │  │  /commands  │  │  MCP Servers    │  │  │
│   │  │ (per proj)  │  │  (shared)   │  │  (postgres,etc) │  │  │
│   │  └─────────────┘  └─────────────┘  └─────────────────┘  │  │
│   └─────────────────────────┬───────────────────────────────┘  │
│                             │                                  │
│   ┌─────────────────────────▼───────────────────────────────┐  │
│   │           PostgreSQL: ai_company_foundation              │  │
│   │                    claude schema                         │  │
│   │  ┌────────────┐ ┌────────────┐ ┌────────────┐          │  │
│   │  │  sessions  │ │  projects  │ │  documents │          │  │
│   │  │  messages  │ │  features  │ │  feedback  │          │  │
│   │  │  activity  │ │  tasks     │ │  reminders │          │  │
│   │  └────────────┘ └────────────┘ └────────────┘          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                                                                 │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │         Mission Control Web (MCW) - Visibility           │  │
│   └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## System Components

### 1. Claude Code Instances

Multiple Claude Code instances can run simultaneously, each working on different projects. They share:
- Slash commands (session-start, session-end, etc.)
- Global CLAUDE.md (`~/.claude/CLAUDE.md`)
- Database access via MCP postgres server
- Memory graph via MCP memory server

### 2. Project Layer

Each project in `C:\Projects\` has:
- **CLAUDE.md** - AI-readable configuration and context
- **PROBLEM_STATEMENT.md** - What problem the project solves
- **ARCHITECTURE.md** - System design (this document pattern)
- **docs/** - Additional documentation

### 3. PostgreSQL Database

**Schema**: `claude`
**Tables**: 36 (as of 2025-12-04)

Key table groups:

| Group | Tables | Purpose |
|-------|--------|---------|
| Sessions | sessions, session_history, session_state | Track Claude sessions |
| Projects | projects, project_tech_stack | Project registry |
| Documents | documents, document_projects | Documentation index |
| Work | features, build_tasks, work_tasks | Work tracking |
| Feedback | feedback | Ideas, bugs, questions |
| System | activity_feed, reminders, messages | Coordination |
| Quality | column_registry | Data validation |

### 4. MCP Servers

Model Context Protocol servers provide Claude instances with capabilities:

| Server | Purpose |
|--------|---------|
| postgres | Database access, session logging |
| memory | Persistent knowledge graph |
| filesystem | File operations |
| orchestrator | Agent spawning, messages |
| python-repl | Python execution |
| sequential-thinking | Complex problem solving |

### 5. Mission Control Web (MCW)

Next.js web application providing visibility into:
- Active sessions and history
- Project status and documents
- Work items (features, tasks)
- Feedback/issues
- Activity feed

---

## Key Workflows

### Session Lifecycle

```
START                                               END
  │                                                  │
  ▼                                                  ▼
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│ /session-start │───▶│   DO WORK      │───▶│  /session-end  │
└────────────────┘    └────────────────┘    └────────────────┘
        │                                           │
        ▼                                           ▼
  - Check reminders                           - Log summary
  - Check messages                            - Record outcome
  - Load context                              - Update state
  - Log session start                         - Close session
```

### Document Indexing

```
┌─────────────────┐      ┌─────────────────┐      ┌──────────────┐
│ scan_documents  │─────▶│ claude.documents│─────▶│ MCW Display  │
│     .py         │      │     table       │      │              │
└─────────────────┘      └─────────────────┘      └──────────────┘
        │
        ├── Detect doc type (ARCHITECTURE, SOP, etc.)
        ├── Extract title from # heading
        ├── Calculate file hash (change detection)
        ├── Detect core docs (CLAUDE.md, shared/)
        └── Link to projects (junction table)
```

### Work Tracking Flow

```
IDEA ──▶ feedback (type='idea')
                │
                ▼ (approved)
         features table
                │
                ▼ (breakdown)
         build_tasks table
                │
                ▼ (in session)
          TodoWrite tool
```

---

## Data Quality

### Column Registry

The `claude.column_registry` table defines valid values for constrained columns. CHECK constraints enforce at database level.

```sql
-- Check valid values before INSERT/UPDATE
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

### Enforcement Hierarchy

```
Weak ───────────────────────────────────────────▶ Strong

CLAUDE.md    Slash      Hooks      DB         Reviewer
(guidance) ─▶ Commands ─▶ (block) ─▶ Constraints ─▶ Agents
              (manual)              (reject)      (verify)
```

---

## Directory Structure

```
C:\Projects\claude-family\
├── .claude/
│   ├── commands/          # Slash commands
│   │   ├── session-start.md
│   │   ├── session-end.md
│   │   └── team-status.md
│   └── hooks.json         # Pre/post tool hooks
├── .claude-plugins/       # Plugin ecosystem
│   └── claude-family-core/
├── docs/
│   ├── CLAUDE_GOVERNANCE_SYSTEM_PLAN.md
│   ├── TODO_NEXT_SESSION.md
│   └── sops/              # Standard operating procedures
├── mcp-servers/
│   └── orchestrator/      # Agent orchestration
├── scripts/
│   ├── scan_documents.py
│   ├── link_checker.py
│   └── orphan_report.py
├── templates/             # Project templates
├── CLAUDE.md
├── PROBLEM_STATEMENT.md
├── ARCHITECTURE.md        # This document
└── README.md
```

---

## Integration Points

### 1. New Project Creation

Future `/project-init` command will:
1. Create directory structure
2. Generate CLAUDE.md from template
3. Create PROBLEM_STATEMENT.md (prompting user)
4. Register in claude.projects table
5. Link documents via junction table

### 2. MCW Dashboards

MCW reads from `claude` schema to display:
- `claude.sessions` → Sessions view
- `claude.projects` → Projects view
- `claude.documents` → Documents view
- `claude.activity_feed` → Activity timeline
- `claude.feedback` → Feedback/issues

### 3. Agent Orchestration

The orchestrator MCP server can spawn specialized agents:
- coder-haiku: Quick coding tasks
- reviewer-sonnet: Code review
- architect-opus: Design decisions
- tester-haiku: Test writing

**Current**: Agents spawn synchronously (caller blocks until completion)
**Planned**: Async spawn with messaging-based result delivery (ADR-003)

---

## Scheduled Jobs

**IMPORTANT**: Job execution gap identified 2025-12-06.

The `claude.scheduled_jobs` table registers scheduled jobs, but **no execution mechanism exists**. The `session_startup_hook.py` checks for due jobs and reports them but does NOT execute them.

```
STATUS (2025-12-06):
- 11 jobs registered, 0 have ever run
- Jobs are reported to Claude at session start
- Claude must manually run or delegate jobs
- MCW task requested to build job runner
```

**Planned resolution**: MCW job runner integration (see docs/TODO_NEXT_SESSION.md)

---

## Enforcement Reality

The enforcement hierarchy exists but with gaps:

| Level | Mechanism | Status |
|-------|-----------|--------|
| CLAUDE.md | Guidance | Active (not always followed) |
| Slash Commands | Manual | Active |
| Hooks | Pre-tool validation | Active (3 validators) |
| DB Constraints | CHECK constraints | Active (limited coverage) |
| Reviewer Agents | Async verification | Not yet implemented |

**Recent additions** (2025-12-06):
- `validate_parent_links.py` - Prevents orphan records at INSERT time
- Updated hooks.json to include parent validation

---

## Security Considerations

- Database credentials in local MCP config only
- No secrets in committed CLAUDE.md files
- Project IDs are UUIDs (not sequential)
- All projects default to PRIVATE repos

---

## Related Documents

- `docs/CLAUDE_GOVERNANCE_SYSTEM_PLAN.md` - Full governance implementation plan
- `docs/DATA_GATEWAY_MASTER_PLAN.md` - Data quality system details
- `~/.claude/CLAUDE.md` - Global Claude configuration
- `C:\claude\shared\docs\` - Shared documentation

---

## Process Router & Workflow System

The process router (`scripts/process_router.py`) detects user intent and triggers appropriate workflows.

### Classification Architecture (Hybrid)

```
User Prompt
    │
    ▼
┌─────────────────────────────────────────┐
│ TIER 1: Fast Regex/Keywords (0-1ms)    │
│ - 53 triggers across 32 processes       │
│ - Cost: $0                              │
└─────────────────────────────────────────┘
    │ (if no match)
    ▼
┌─────────────────────────────────────────┐
│ TIER 2: LLM Classification (2-4s)       │
│ - Claude Haiku semantic understanding   │
│ - Cost: ~$0.001 per call                │
│ - Catches edge cases                    │
└─────────────────────────────────────────┘
    │
    ▼
Return workflow steps + standards guidance
```

### Workflow Inventory (32 Total)

| Category | Count | Examples |
|----------|-------|----------|
| SESSION  | 4 | Start, End, Commit, Resume |
| DEV      | 7 | Bug Fix, Feature, Code Review, Testing |
| DOC      | 4 | Create Doc, ADR, CLAUDE.md Update |
| PROJECT  | 5 | Init, Retrofit, Compliance Check |
| COMM     | 4 | Feedback, Broadcast, Messages |
| DATA     | 4 | Knowledge Capture, DB Validation |
| QA       | 4 | Pre-Commit, Schema, API Smoke |

### User Testing Results (2025-12-09)

| Metric | Result |
|--------|--------|
| Workflows tested | 19/32 (59%) |
| Classification accuracy | 17/19 (89%) |
| LLM fallback accuracy | 2/3 (67%) |
| Issues fixed | 3 |

**Key Findings:**
- Regex/keywords handle ~90% of cases correctly
- LLM catches semantic variations ("system crashing" → Bug Fix)
- Keyword collisions can cause misclassification
- Session Resume needed user-facing triggers

**Test Report**: `docs/test-reports/WORKFLOW_USER_TESTING_2025-12-09.md`

---

## Architectural Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | Schema Consolidation | Accepted |
| ADR-002 | Core Documentation System | Accepted |
| ADR-003 | Async Agent Workflow | Proposed |

See `claude.architecture_decisions` table and `docs/adr/` folder for full records.

---

**Maintained by**: Claude Family Infrastructure Team
**Review Cycle**: Monthly or on major changes
