# Claude Governance System - Implementation Plan

**Status**: DRAFT - AWAITING APPROVAL
**Created**: 2025-12-04
**Author**: claude-code-unified
**Project**: claude-family (infrastructure)

---

## Executive Summary

This plan establishes a governance system for AI-assisted software development that ensures:
1. Consistent project structure across all projects
2. Enforced procedures via hooks, MCW, and database constraints
3. Living documentation that stays current
4. Clear work tracking with one path per item type
5. Spec-driven development with approval gates

**Problem**: Claude instances currently work ad-hoc, creating inconsistent data, stale documentation, and no enforced procedures.

**Solution**: A structured governance system with templates, enforcement hooks, MCW integration, and automated quality checks.

---

## Table of Contents

1. [Core Documents Standard](#1-core-documents-standard)
2. [Project Initiation Process](#2-project-initiation-process)
3. [Spec-Driven Development Phases](#3-spec-driven-development-phases)
4. [Work Tracking System](#4-work-tracking-system)
5. [Enforcement Mechanisms](#5-enforcement-mechanisms)
6. [MCW Integration](#6-mcw-integration)
7. [Document Maintenance](#7-document-maintenance)
8. [Retrofit Plan for Existing Projects](#8-retrofit-plan-for-existing-projects)
9. [Implementation Phases](#9-implementation-phases)

---

## 1. Core Documents Standard

### 1.1 Required Documents (Every Project)

| Document | Purpose | Created | Updated |
|----------|---------|---------|---------|
| `CLAUDE.md` | AI constitution - coding standards, project state, procedures | Project init | Every session |
| `PROBLEM_STATEMENT.md` | What problem, for whom, why worth solving | Project init | When scope changes |
| `ARCHITECTURE.md` | System design overview, links to sub-docs | Design phase | When architecture changes |

### 1.2 Supporting Documents (As Needed)

| Document | Purpose | Location |
|----------|---------|----------|
| `ADR-XXX.md` | Architecture Decision Records | `docs/adr/` |
| `SOP-XXX.md` | Standard Operating Procedures | `docs/sop/` |
| `SCHEMA.md` | Database schema documentation | `docs/` |
| `API.md` | API documentation | `docs/` |
| Sub-system docs | Detailed architecture for specific systems | `docs/architecture/` |

### 1.3 Project Folder Structure

```
project-name/
├── CLAUDE.md                    # AI constitution (REQUIRED)
├── PROBLEM_STATEMENT.md         # Problem definition (REQUIRED)
├── ARCHITECTURE.md              # System design (REQUIRED)
├── README.md                    # Human-readable overview
├── .claude/
│   ├── commands/                # Slash commands
│   └── settings.local.json      # Local Claude settings
├── docs/
│   ├── architecture/            # Sub-system documentation
│   ├── adr/                     # Architecture Decision Records
│   └── sop/                     # Standard Operating Procedures
├── src/                         # Source code
└── tests/                       # Test files
```

### 1.4 CLAUDE.md Template Structure

```markdown
# {Project Name} - Project Context

**Type**: {Work/Infrastructure/Personal}
**Status**: {Initiation/Requirements/Design/Implementation/Maintenance}
**Project ID**: {UUID from database}

---

## Problem Statement
{Brief summary - links to PROBLEM_STATEMENT.md for details}

## Current Phase
{What phase we're in, what's the focus}

## Architecture Overview
{Brief summary - links to ARCHITECTURE.md for details}

## Coding Standards
{Language-specific standards, naming conventions}

## Work Tracking
- Ideas/Backlog: feedback table (type=idea)
- Bugs: feedback table (type=bug)
- Features: features table
- Tasks: build_tasks table
- This session: TodoWrite

## Key Procedures
{Links to relevant SOPs}

## Recent Changes
{Last 3-5 significant changes with dates}

---
**Version**: X.X
**Updated**: YYYY-MM-DD
```

---

## 2. Project Initiation Process

### 2.1 Overview

When user says "Let's build X", follow this exact process:

```
USER REQUEST
    ↓
PHASE 0: INITIATION (create structure)
    ↓
USER APPROVAL ← ← ← ← Stop if not approved
    ↓
PHASE 1: REQUIREMENTS (document needs)
    ↓
USER APPROVAL ← ← ← ← Stop if not approved
    ↓
PHASE 2: DESIGN (architecture)
    ↓
USER APPROVAL ← ← ← ← Stop if not approved
    ↓
PHASE 3: PLANNING (tasks/estimates)
    ↓
USER APPROVAL ← ← ← ← Stop if not approved
    ↓
PHASE 4: IMPLEMENTATION (build)
```

### 2.2 Phase 0: Initiation

**Trigger**: User requests new project
**Duration**: ~15 minutes
**Output**: Project structure created

**Steps**:
1. Run `/project-init {name} {type}` command
2. Script creates:
   - Folder at `C:\Projects\{name}\`
   - CLAUDE.md from template
   - PROBLEM_STATEMENT.md (skeleton)
   - .claude/commands/ folder
   - docs/ folder structure
3. Register project in `claude.projects` table
4. Present structure to user for approval

**Approval Gate**: User confirms structure is correct

### 2.3 Phase 1: Requirements

**Trigger**: Phase 0 approved
**Duration**: 30-60 minutes (discussion)
**Output**: Requirements documented

**Steps**:
1. Discuss with user:
   - What problem are we solving?
   - Who has this problem?
   - How is it currently solved?
   - Why is it worth solving?
   - What does success look like?
2. Document in PROBLEM_STATEMENT.md:
   - Problem definition
   - Target users
   - Success criteria
   - Constraints
   - Out of scope
3. Create initial features in database (high-level)
4. Present requirements to user for approval

**Approval Gate**: User confirms requirements are complete

### 2.4 Phase 2: Design

**Trigger**: Phase 1 approved
**Duration**: 1-2 hours
**Output**: Architecture documented

**Steps**:
1. Design system architecture:
   - Components/services
   - Data models
   - Integrations
   - Technology choices
2. Create ARCHITECTURE.md:
   - System overview diagram (text-based)
   - Component descriptions
   - Data flow
   - Key decisions (link to ADRs)
3. Create ADRs for significant decisions
4. If database needed, create SCHEMA.md
5. Present design to user for approval

**Approval Gate**: User confirms design is acceptable

### 2.5 Phase 3: Planning

**Trigger**: Phase 2 approved
**Duration**: 30-60 minutes
**Output**: Build plan in database

**Steps**:
1. Break features into components
2. Break components into tasks
3. Estimate effort (hours)
4. Set priorities
5. Enter into build_tasks table
6. Present plan in MCW Build Tracker for approval

**Approval Gate**: User confirms plan is realistic

### 2.6 Phase 4: Implementation

**Trigger**: Phase 3 approved
**Duration**: Varies
**Output**: Working software

**Steps**:
1. Work through tasks in priority order
2. Update task status as work progresses
3. Update documentation when architecture changes
4. Create ADRs for new significant decisions
5. Regular check-ins with user
6. Update CLAUDE.md "Recent Changes" section

---

## 3. Spec-Driven Development Phases

### 3.1 Phase Status Tracking

Each project has a current phase stored in:
- `claude.projects.status` field
- Valid values: `initiation`, `requirements`, `design`, `planning`, `implementation`, `maintenance`

### 3.2 Phase Transition Rules

| From | To | Requirement |
|------|-----|-------------|
| (new) | initiation | User requests project |
| initiation | requirements | Structure approved |
| requirements | design | Requirements approved |
| design | planning | Architecture approved |
| planning | implementation | Build plan approved |
| implementation | maintenance | MVP delivered |

### 3.3 Enforcement

**Hook enforcement**: Before creating build_tasks, check project is in `planning` or `implementation` phase.

**MCW enforcement**: Show phase badge on project, gate certain actions by phase.

---

## 4. Work Tracking System

### 4.1 Decision Matrix

| I have... | Put it in... | Table | Type/Status |
|-----------|--------------|-------|-------------|
| An idea for later | Feedback | `claude.feedback` | type='idea' |
| A bug to fix | Feedback | `claude.feedback` | type='bug' |
| A design question | Feedback | `claude.feedback` | type='question' |
| A change request | Feedback | `claude.feedback` | type='change' |
| A planned feature | Features | `claude.features` | status='planned' |
| A task to implement | Build Tasks | `claude.build_tasks` | status='todo' |
| Work for this session | TodoWrite | (in-memory) | - |

### 4.2 Workflow

```
IDEA
  ↓ (approved)
FEATURE
  ↓ (broken down)
BUILD_TASKS
  ↓ (completed)
DONE
```

### 4.3 Status Values (Enforced)

**Feedback**:
- `new` → `in_progress` → `resolved` | `wont_fix` | `duplicate`

**Features**:
- `not_started` → `planned` → `in_progress` → `completed` | `cancelled`

**Build Tasks**:
- `todo` → `in_progress` → `completed` | `blocked`

### 4.4 Priority Scale (All Tables)

| Priority | Meaning |
|----------|---------|
| 1 | Critical - do immediately |
| 2 | High - do soon |
| 3 | Medium - normal priority |
| 4 | Low - when time permits |
| 5 | Backlog - someday/maybe |

---

## 5. Enforcement Mechanisms

### 5.1 Enforcement Hierarchy

| Level | Mechanism | Type | Current State |
|-------|-----------|------|---------------|
| 1 | CLAUDE.md | Suggestion | EXISTS - needs update |
| 2 | Slash commands | Manual | EXISTS - needs expansion |
| 3 | Pre-action hooks | Automated | PARTIAL - needs enhancement |
| 4 | Database constraints | Hard stop | EXISTS - complete |
| 5 | Reviewer agents | Automated | MISSING - to build |

### 5.2 Hook Enhancements Needed

**Pre-tool-call hooks**:
```python
# Before writing to database
def validate_data_write(table, data):
    # Check against column_registry
    # Block if invalid values
    # Return error with valid options

# Before creating build_task
def validate_build_task(project_id):
    # Check project phase is planning or implementation
    # Block if in wrong phase

# Before committing code
def validate_commit():
    # Check CLAUDE.md was updated this session
    # Warn if architecture changed but docs not updated
```

**Session-end hooks**:
```python
def session_end_check():
    # Did you update CLAUDE.md?
    # Did you update architecture docs if needed?
    # Are all tasks marked with correct status?
```

### 5.3 MCW Enforcement (See Section 6)

---

## 6. MCW Integration

### 6.1 Current MCW Features

- Projects list with overview
- Documents view (needs Core Docs fix)
- Feedback view (bugs, ideas)
- Build Tracker (features, components, tasks)
- Tasks view (work_tasks)

### 6.2 Required MCW Enhancements

#### 6.2.1 Project Phase Indicator

**Location**: Project overview, project card
**Display**: Badge showing current phase
**Colors**:
- Initiation: Gray
- Requirements: Blue
- Design: Purple
- Planning: Orange
- Implementation: Green
- Maintenance: Teal

#### 6.2.2 Phase Gate Actions

**New button**: "Advance Phase"
**Behavior**:
- Shows checklist of requirements for next phase
- User confirms checklist complete
- Updates project.status
- Logs phase transition in activity_feed

#### 6.2.3 Core Documents Section Fix

**Current**: Shows all `is_core=true` docs (37 items)
**Fix**: Filter to show only:
- CLAUDE.md (this project's)
- PROBLEM_STATEMENT.md
- ARCHITECTURE.md
- Status = ACTIVE
- is_current_version = true

#### 6.2.4 Document Health Indicators

**Per document**:
- Last updated badge (green < 7 days, yellow < 30 days, red > 30 days)
- "Stale" warning if older than threshold

**Per project**:
- Documentation health score
- Missing required docs warning

#### 6.2.5 Work Tracking Guidance

**On Feedback "New" button**:
- Pre-filled type selector with descriptions
- "Idea", "Bug", "Question", "Change"

**On Build Tracker**:
- Phase check: Can only add tasks if in planning/implementation
- Warning if adding task to feature in wrong status

#### 6.2.6 Governance Dashboard (New)

**Location**: New sidebar item or Dashboard section
**Shows**:
- Projects by phase (pie chart)
- Documentation health across projects
- Recent phase transitions
- Overdue document updates
- Enforcement violations log

### 6.3 MCW Database Views Needed

```sql
-- Project governance status
CREATE VIEW claude.project_governance AS
SELECT
    p.project_id,
    p.project_name,
    p.status as phase,
    (SELECT COUNT(*) FROM claude.documents d
     JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
     WHERE dp.project_id = p.project_id
     AND d.doc_type = 'CLAUDE_CONFIG' AND d.status = 'ACTIVE') as has_claude_md,
    (SELECT COUNT(*) FROM claude.documents d
     JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
     WHERE dp.project_id = p.project_id
     AND d.doc_title LIKE '%PROBLEM%' AND d.status = 'ACTIVE') as has_problem_statement,
    (SELECT COUNT(*) FROM claude.documents d
     JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
     WHERE dp.project_id = p.project_id
     AND d.doc_type = 'ARCHITECTURE' AND d.status = 'ACTIVE') as has_architecture
FROM claude.projects p
WHERE p.is_archived = false;
```

---

## 7. Document Maintenance

### 7.1 Update Triggers

| Event | Document to Update |
|-------|-------------------|
| Session start | Check CLAUDE.md is current |
| Architecture change | ARCHITECTURE.md, relevant ADR |
| New decision | Create ADR-XXX.md |
| Schema change | SCHEMA.md |
| API change | API.md |
| Session end | CLAUDE.md "Recent Changes" |

### 7.2 Staleness Detection

**Scheduled job**: Weekly document audit

**Checks**:
- Required docs exist per project
- Docs updated within threshold
- No DEPRECATED docs in Core Documents
- All version flags correct

**Output**:
- Report to activity_feed
- Reminders created for stale docs

### 7.3 Version Control

**For major document updates**:
1. Create new version (e.g., ARCHITECTURE_v2.md)
2. Mark old version `is_current_version = false`
3. Update references in CLAUDE.md

**For minor updates**:
1. Edit in place
2. Update version number in doc footer
3. Update `updated_at` in database

---

## 8. Retrofit Plan for Existing Projects

### 8.1 Current Projects

| Project | Status | Needs |
|---------|--------|-------|
| claude-family | Infrastructure | Update CLAUDE.md, add governance |
| mission-control-web | Active | Full retrofit |
| nimbus-user-loader | Active | Full retrofit |
| ATO-Tax-Agent | Active | Full retrofit + import issues |

### 8.2 Retrofit Process Per Project

**Step 1: Audit** (30 min)
- Check existing CLAUDE.md
- Check for PROBLEM_STATEMENT.md
- Check for ARCHITECTURE.md
- List what's missing

**Step 2: Create Missing Docs** (1-2 hours)
- Create PROBLEM_STATEMENT.md from existing knowledge
- Create/update ARCHITECTURE.md
- Update CLAUDE.md to new template

**Step 3: Database Alignment** (30 min)
- Verify project in claude.projects
- Set correct phase status
- Link documents via document_projects

**Step 4: Verify in MCW** (15 min)
- Check Core Documents shows correctly
- Check Build Tracker has features
- Check phase badge correct

### 8.3 Retrofit Order

1. **claude-family** (this project) - Do first as template
2. **mission-control-web** - High activity, needs governance
3. **nimbus-user-loader** - Simpler, good test case
4. **ATO-Tax-Agent** - Complex, has issue import need

---

## 9. Implementation Phases

### Phase A: Foundation (This Session)

**Goal**: Get claude-family project compliant as template

**Tasks**:
- [ ] A1: Update claude-family CLAUDE.md to new standard
- [ ] A2: Create PROBLEM_STATEMENT.md for claude-family
- [ ] A3: Create/update ARCHITECTURE.md for claude-family
- [ ] A4: Update project phase in database
- [ ] A5: Test governance view query

**Deliverable**: claude-family is model project

### Phase B: Templates & Commands (Next Session)

**Goal**: Create reusable templates and commands

**Tasks**:
- [ ] B1: Create CLAUDE.md template
- [ ] B2: Create PROBLEM_STATEMENT.md template
- [ ] B3: Create ARCHITECTURE.md template
- [ ] B4: Create `/project-init` slash command
- [ ] B5: Create `/phase-advance` slash command
- [ ] B6: Document templates in SOP

**Deliverable**: New projects can use `/project-init`

### Phase C: Enforcement Hooks (Following Session)

**Goal**: Add automated enforcement

**Tasks**:
- [ ] C1: Add data validation hook
- [ ] C2: Add phase-check hook for build_tasks
- [ ] C3: Add session-end doc check
- [ ] C4: Test all hooks
- [ ] C5: Document hook behavior

**Deliverable**: Violations are blocked automatically

### Phase D: MCW Integration (Coordinate with MCW)

**Goal**: MCW shows governance features

**Tasks**:
- [ ] D1: Add phase badge to projects
- [ ] D2: Fix Core Documents filter
- [ ] D3: Add document staleness indicators
- [ ] D4: Add phase advance button
- [ ] D5: Add governance dashboard

**Deliverable**: Full visibility in MCW

### Phase E: Retrofit Existing Projects

**Goal**: All active projects compliant

**Tasks**:
- [ ] E1: Retrofit mission-control-web
- [ ] E2: Retrofit nimbus-user-loader
- [ ] E3: Retrofit ATO-Tax-Agent (including issue import)
- [ ] E4: Verify all in MCW

**Deliverable**: All projects governed

### Phase F: Auto-Review Agents

**Goal**: Automated quality checks

**Tasks**:
- [ ] F1: Create doc-reviewer agent
- [ ] F2: Create code-standards agent
- [ ] F3: Add to orchestrator
- [ ] F4: Schedule periodic reviews

**Deliverable**: Continuous quality enforcement

---

## Appendix A: Database Changes Required

### New Columns

```sql
-- Already added
ALTER TABLE claude.documents ADD COLUMN is_current_version BOOLEAN DEFAULT true;

-- Project phase (if not using status)
-- Note: status field exists, ensure valid values include phases
```

### New Views

```sql
-- Project governance status (see Section 6.3)
CREATE VIEW claude.project_governance AS ...

-- Core documents per project
CREATE VIEW claude.core_documents AS
SELECT d.*, p.project_name
FROM claude.documents d
JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
JOIN claude.projects p ON dp.project_id = p.project_id
WHERE d.status = 'ACTIVE'
  AND d.is_current_version = true
  AND d.doc_type IN ('CLAUDE_CONFIG', 'ARCHITECTURE', 'SPEC')
  AND d.doc_title NOT LIKE '%DEPRECATED%';
```

---

## Appendix B: Slash Commands to Create

| Command | Purpose | Phase |
|---------|---------|-------|
| `/project-init` | Create new project structure | B |
| `/phase-advance` | Move project to next phase | B |
| `/doc-check` | Verify required docs exist | B |
| `/governance-status` | Show project compliance | D |

---

## Appendix C: Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Projects with CLAUDE.md | 4/4 | 4/4 |
| Projects with PROBLEM_STATEMENT | 0/4 | 4/4 |
| Projects with ARCHITECTURE | ~2/4 | 4/4 |
| Test data in tables | Present | Zero |
| Phase tracking | None | All projects |
| Doc staleness alerts | None | Automated |
| Enforcement violations blocked | 0% | 100% |

---

## Approval

**Plan Status**: DRAFT

**Approval Required From**: John (User)

**To Approve**: Confirm this plan addresses requirements and authorize Phase A implementation.

---

**Document Version**: 1.0
**Created**: 2025-12-04
**Location**: C:\Projects\claude-family\docs\CLAUDE_GOVERNANCE_SYSTEM_PLAN.md
