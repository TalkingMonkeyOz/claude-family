# Mission Control Strategy Document

**Purpose**: Define the unified operating system for Claude Family
**Created**: 2025-11-30
**For**: mission-control-web implementation

---

## Executive Summary

Mission Control should be the central hub that makes Claude instances more effective by:
1. Providing structured knowledge at the right time
2. Enforcing consistent workflows across projects
3. Enabling hierarchical agent orchestration
4. Tracking session continuity and progress

---

## Current State Analysis

### What Exists

| Component | Count | Status |
|-----------|-------|--------|
| shared_knowledge entries | 125 | Poorly categorized (34 different types!) |
| procedure_registry | 18 | Better structured (6 types) |
| session_history | 146 | Working, needs better summaries |
| project_workspaces | 6 | Active projects tracked |
| session_state | NEW | Todo persistence implemented |

### Key Problem

**Knowledge exists but is unusable:**
- 34 different `knowledge_type` values (pattern, PATTERN, code-pattern, design-pattern, etc.)
- No consistency = no discoverability
- "Dump everything in, hope to find it later" approach

---

## Proposed Architecture

### Module 1: Knowledge Hub

**Purpose**: Structured, searchable, usage-tracked knowledge base

**Canonical Categories** (enforce these only):
| Category | Description | Example |
|----------|-------------|---------|
| PATTERN | Reusable code/architecture patterns | "Use UPSERT for session state" |
| GOTCHA | Things that cause problems | "psycopg2 vs psycopg3 API differences" |
| SOLUTION | Specific problem fixes | "Fix for file locking on Windows" |
| ARCHITECTURE | System design decisions | "Why we use PostgreSQL over SQLite" |
| PROCESS | How to do things | "PR review workflow" |

**UI Features Needed**:
- Category filter dropdown
- Confidence score display (1-10)
- Usage count ("applied 15 times")
- Search with relevance ranking
- "Mark as outdated" action

**Data Migration**:
```sql
-- Normalize existing types
UPDATE claude_family.shared_knowledge SET knowledge_type = 'PATTERN'
WHERE knowledge_type IN ('pattern', 'PATTERN', 'code-pattern', 'design-pattern', 'api-pattern', 'technical-pattern');
-- etc for other categories
```

### Module 2: SOP Library

**Purpose**: Step-by-step procedures triggered at the right time

**Structure**:
```
SOPs/
├── session-workflow/     # Start/end session
├── compliance/           # C# standards, security checks
├── quality-assurance/    # Testing, review procedures
├── infrastructure/       # MCP setup, database maintenance
└── project-lifecycle/    # New project, onboarding, archival
```

**Trigger System**:
| Trigger | SOP |
|---------|-----|
| "starting new C# project" | → compliance/csharp-setup |
| "reviewing code" | → quality-assurance/code-review |
| "session starting" | → session-workflow/session-start |

**UI Features Needed**:
- Browse by category
- "When to use" description
- Version history
- Mark as mandatory/optional

### Module 3: Project Center

**Purpose**: All projects with status, health, recent activity

**Data to Show**:
- Project name, path, type
- Tech stack (auto-detected or manual)
- Health metrics: last session, open issues, test status
- Recent activity: who worked on what, when
- Quick links: CLAUDE.md, git repo, docs

**UI Features Needed**:
- Project cards with health indicators
- Click to see project detail
- "Register new project" wizard
- Link to feedback system

### Module 4: Agent Orchestrator

**Purpose**: Spawn, monitor, and manage agent hierarchies

**Agent Types** (now available):
| Type | Model | Purpose | Can Spawn? |
|------|-------|---------|------------|
| test-coordinator-sonnet | Sonnet | Orchestrate test suites | ✅ |
| review-coordinator-sonnet | Sonnet | Orchestrate code reviews | ✅ |
| refactor-coordinator-sonnet | Sonnet | Orchestrate refactoring | ✅ |
| onboarding-coordinator-sonnet | Sonnet | Onboard new codebases | ✅ |
| coder-haiku | Haiku | Write code | ❌ |
| tester-haiku | Haiku | Write tests | ❌ |
| reviewer-sonnet | Sonnet | Review code | ❌ |
| architect-opus | Opus | Design systems | ❌ |
| ... | ... | ... | ... |

**Hierarchical Flow**:
```
User Request
    ↓
Main Claude (Opus/Sonnet)
    ↓
Coordinator Agent (spawned)
    ├── Worker Agent 1 (spawned by coordinator)
    ├── Worker Agent 2 (spawned by coordinator)
    └── Worker Agent 3 (spawned by coordinator)
    ↓
Results aggregated by coordinator
    ↓
Returned to main Claude
```

**UI Features Needed**:
- List of agent types with descriptions
- "Spawn agent" form (select type, provide task)
- Running agents view (if async in future)
- Cost estimates per agent type

### Module 5: Session Tracker

**Purpose**: Who's working where, session continuity

**Data to Show**:
- Active sessions (Claude instances currently running)
- Recent sessions by project
- Session state (todo lists, current focus)
- "Resume from" quick links

**UI Features Needed**:
- Session timeline view
- Click to see session details
- "Where I left off" summary per project
- Session quality metrics (did they save state? log learnings?)

### Module 6: Quality Gates

**Purpose**: Checklists before shipping

**Gate Types**:
| Gate | When | Checks |
|------|------|--------|
| Pre-commit | Before git commit | Tests pass, no secrets, linting |
| Pre-PR | Before creating PR | Code review complete, docs updated |
| Pre-release | Before deploying | Security scan, regression tests |
| Session-end | Before closing session | State saved, learnings logged |

**UI Features Needed**:
- Gate definition editor
- Checklist view during work
- Gate pass/fail history
- Link gates to projects

---

## The Claude Workflow

This is the flow Mission Control should support/enforce:

```
┌─────────────────────────────────────────────────────────────┐
│                      SESSION START                          │
├─────────────────────────────────────────────────────────────┤
│ 1. Load identity (who am I?)                                │
│ 2. Check session_state (where did I leave off?)             │
│ 3. Load project context (CLAUDE.md, recent sessions)        │
│ 4. Check pending messages (any handoffs from other Claudes?)│
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      TASK INTAKE                            │
├─────────────────────────────────────────────────────────────┤
│ 1. Understand the request                                   │
│ 2. Search Knowledge Hub (have we solved this before?)       │
│ 3. Find relevant SOPs (is there a procedure for this?)      │
│ 4. Check feedback items (any related issues?)               │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      PLANNING                               │
├─────────────────────────────────────────────────────────────┤
│ 1. Break down into tasks (TodoWrite)                        │
│ 2. Identify what can be delegated to sub-agents             │
│ 3. Spawn coordinator if complex multi-part work             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      EXECUTION                              │
├─────────────────────────────────────────────────────────────┤
│ 1. Follow SOPs where applicable                             │
│ 2. Use patterns from Knowledge Hub                          │
│ 3. Track progress (TodoWrite)                               │
│ 4. Capture learnings as you go                              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      QUALITY                                │
├─────────────────────────────────────────────────────────────┤
│ 1. Run quality gate checks                                  │
│ 2. Get reviews if needed (spawn review-coordinator)         │
│ 3. Fix issues before completion                             │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                      SESSION END                            │
├─────────────────────────────────────────────────────────────┤
│ 1. Save session_state (todo list, focus, files modified)    │
│ 2. Log session summary to session_history                   │
│ 3. Store new knowledge in Knowledge Hub                     │
│ 4. Update SOPs if procedures changed                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Lifecycle Phases

### Phase 1: New Project

**Trigger**: User starts working in unknown codebase

**Actions**:
1. Spawn onboarding-coordinator
2. Generate CLAUDE.md
3. Register in project_workspaces
4. Document tech stack, patterns, gotchas
5. Create initial feedback items if issues found

**Mission Control Support**:
- "New Project" wizard
- Template CLAUDE.md
- Auto-registration

### Phase 2: Active Development

**Trigger**: Regular work on registered project

**Actions**:
1. Session start/end workflow
2. Task tracking with TodoWrite
3. Knowledge capture during work
4. Feedback creation for issues found
5. Review coordination for significant changes

**Mission Control Support**:
- Session dashboard
- Todo visibility
- Quick feedback creation
- Agent spawning UI

### Phase 3: Maintenance

**Trigger**: Project in stable state, occasional updates

**Actions**:
1. Bug triage workflow
2. Regression prevention (run tests)
3. Documentation updates
4. Dependency updates
5. Archive stale SOPs/knowledge

**Mission Control Support**:
- Bug triage view
- Dependency health dashboard
- Archive suggestions

---

## Implementation Priority

### Phase 1 (MVP)
1. Knowledge Hub with normalized categories
2. Project Center with registration
3. Session Tracker with "where I left off"

### Phase 2
4. SOP Library with triggers
5. Agent Orchestrator UI
6. Quality Gates

### Phase 3
7. Async agent spawning
8. Hierarchical orchestration dashboard
9. Cross-project insights

---

## Database Schema Changes Needed

```sql
-- Normalize knowledge types
ALTER TABLE claude_family.shared_knowledge
ADD CONSTRAINT valid_knowledge_type
CHECK (knowledge_type IN ('PATTERN', 'GOTCHA', 'SOLUTION', 'ARCHITECTURE', 'PROCESS'));

-- Add project health metrics
ALTER TABLE claude_family.project_workspaces
ADD COLUMN last_session_at TIMESTAMP,
ADD COLUMN health_status VARCHAR(20) DEFAULT 'unknown',
ADD COLUMN tech_stack JSONB DEFAULT '[]';

-- Add SOP triggers
CREATE TABLE claude_family.sop_triggers (
    trigger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trigger_pattern TEXT NOT NULL,  -- regex or keyword
    procedure_id INTEGER REFERENCES claude_family.procedure_registry(id),
    priority INTEGER DEFAULT 5
);
```

---

## Next Steps

1. **mission-control-web**: Implement Knowledge Hub UI first
2. **Data migration**: Normalize shared_knowledge types
3. **Claude Family**: Start using /session-start and /session-end consistently
4. **Testing**: Try coordinator agents on a real task

---

*This document should be the north star for Mission Control development.*
