# Claude Family System - Core Documents Reference

**Version**: 1.0
**Date**: 2025-12-18
**Purpose**: Definitive list of documents that make the system work

---

## Overview

The Claude Family system has **three tiers** of documents:

| Tier | Purpose | Without These |
|------|---------|---------------|
| **Tier 1: ESSENTIAL** | System won't function | Nothing works |
| **Tier 2: CONTENT** | Knowledge the system serves | Works but empty |
| **Tier 3: SUPPORTING** | Governance, standards, tests | Works but ungoverned |

---

## Tier 1: ESSENTIAL DOCUMENTS

These documents ARE the system. Without them, nothing works.

### 1.1 PID Development Process

**File**: `pid-development-process.md`
**Location**: `C:\Users\johnd\OneDrive\Documents\AI_projects\`
**Purpose**: The METHODOLOGY for how to properly develop and validate anything

**What It Does**:
- Phase 1: Initial document review with gap analysis
- Phase 2: Question resolution with REAL DATA validation
- Phase 3: Technical validation (verify against actual APIs/DB)
- Phase 4: Application design (UI, data management, logging)
- Phase 5: Final review with end-to-end walkthrough

**Key Principle**: "Don't assume - always verify against real data/APIs"

**When To Use**:
- Starting any new feature
- Validating implementation specs
- Before building anything significant

---

### 1.2 CLAUDE.md Template

**File**: `CLAUDE.md`
**Location**: Every project root
**Purpose**: Project-specific configuration that Claude Code auto-loads

**What It Contains**:
```markdown
# {Project Name}

## Tech Stack
- Language, frameworks, databases

## Critical Rules
- ALWAYS do X
- NEVER do Y

## Project Structure
- Where things live

## Current Focus
- What we're working on now

## Quick Commands
- Build, test, run commands
```

**Key Principle**: Keep under 250 lines - this loads on EVERY interaction

**When To Use**: Every project must have one

---

### 1.3 hooks.json

**File**: `.claude/hooks.json`
**Location**: Each project's `.claude/` folder
**Purpose**: Tells Claude Code which hooks to fire

**What It Contains**:
```json
{
  "hooks": {
    "UserPromptSubmit": [
      {"type": "command", "command": "python scripts/knowledge_retriever.py"},
      {"type": "command", "command": "python scripts/stop_hook_enforcer.py"}
    ]
  }
}
```

**Key Principle**: Hooks fire BEFORE Claude sees the prompt - they inject context

**When To Use**: Any project that needs knowledge injection or reminders

---

### 1.4 Hook Scripts

**Files**:
- `scripts/knowledge_retriever.py` - RAG knowledge injection
- `scripts/stop_hook_enforcer.py` - Counter-based reminders

**Location**: Project `scripts/` folder
**Purpose**: The actual code that finds and injects relevant context

**What They Do**:
1. Receive user prompt via stdin
2. Extract keywords / check counters
3. Query database or check state
4. Output context to stdout (gets injected)

**Key Principle**: Must exit 0 and be fast (<200ms)

---

### 1.5 Architecture Document

**File**: `ARCHITECTURE.md`
**Location**: Project `docs/` or root
**Purpose**: How all the pieces connect

**What It Contains**:
- System overview diagram
- Component descriptions
- Data flow
- Integration points
- Key workflows

**Key Principle**: This is the "map" - if you're lost, read this

**When To Use**: Understanding the system, onboarding, major changes

---

## Tier 2: CONTENT DOCUMENTS

These provide the actual KNOWLEDGE the system serves. Without them, the hooks fire but find nothing.

### 2.1 Knowledge Entries (Database)

**Table**: `claude.knowledge`
**Purpose**: Reusable patterns, gotchas, solutions

**What It Contains**:
| Field | Purpose |
|-------|---------|
| title | Quick identifier ("Nimbus OData Field Naming") |
| description | The actual knowledge |
| knowledge_category | Domain ("nimbus-api", "database", "testing") |
| knowledge_type | Kind ("pattern", "gotcha", "api-reference") |
| confidence_level | Quality ranking (1-100) |

**Key Principle**: This is what knowledge_retriever.py searches

**Current State**: 161 entries across multiple domains

---

### 2.2 Process Registry (Database)

**Tables**:
- `claude.process_registry` - Workflow definitions
- `claude.process_steps` - Steps for each workflow
- `claude.process_triggers` - What activates each workflow

**Purpose**: Standardized workflows (feature dev, bug fix, docs, etc.)

**What It Contains**:
| Workflow | Triggers |
|----------|----------|
| PROC-DEV-001 Feature Implementation | "feature", "implement", "build" |
| PROC-DEV-002 Bug Fix | "bug", "fix", "error" |
| PROC-DOC-001 Documentation | "document", "docs" |
| PROC-SESSION-001 Session Start | /session-start |

**Key Principle**: Provides consistent steps for common work types

**Current State**: 32 workflows defined

---

### 2.3 Skills (Future)

**Location**: `.claude/skills/{skill-name}/SKILL.md`
**Purpose**: Deep guides loaded on-demand

**What They Would Contain**:
```
.claude/skills/
├── nimbus-api/SKILL.md       # Complete Nimbus API guide
├── feature-workflow/SKILL.md  # How to implement features
├── database/SKILL.md          # Database patterns
└── testing/SKILL.md           # Testing standards
```

**Key Principle**: Only loaded when Claude determines relevance (not every prompt)

**Current State**: Not implemented yet - enhancement

---

## Tier 3: SUPPORTING DOCUMENTS

These govern HOW the system is used and maintained.

### 3.1 Governance Plan

**File**: `CLAUDE_GOVERNANCE_SYSTEM_PLAN.md`
**Purpose**: Rules, enforcement, compliance

**What It Contains**:
- Core document standards
- Project initiation process
- Work tracking system
- Enforcement mechanisms
- Retrofit plan for existing projects

**Key Principle**: How we ensure consistency

---

### 3.2 Documentation Standards

**File**: `DOCUMENTATION_STANDARDS_v1.md`
**Purpose**: How to write docs consistently

**What It Contains**:
- Document types and templates
- Naming conventions
- Version control
- Deprecation process

**Key Principle**: Consistency enables automation

---

### 3.3 Implementation Specs

**File**: Various `*_SPEC_*.md` or `*_PLAN_*.md`
**Purpose**: Detailed specs for specific features

**What They Contain**:
- Problem statement
- Proposed solution
- User stories
- Success criteria
- Implementation phases

**Key Principle**: Follow PID process to validate these

---

### 3.4 Test Suites

**File**: `run_regression_tests.py` and related
**Purpose**: Validate the system works

**What They Contain**:
- User story tests
- Integration tests
- Performance benchmarks

**Key Principle**: Run tests after any changes

---

## Document Relationships

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         TIER 1: ESSENTIAL                               │
│                         (The System Itself)                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ PID Process  │    │  CLAUDE.md   │    │  hooks.json  │             │
│  │ (Methodology)│    │  (Per Project)│    │  (Hook Config)│            │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│          │                   │                   │                     │
│          │                   │                   │                     │
│          ▼                   ▼                   ▼                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ Validates    │    │ Auto-loaded  │    │ Fires hooks: │             │
│  │ all specs    │    │ every session│    │ knowledge_   │             │
│  │ and plans    │    │              │    │ retriever.py │             │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         TIER 2: CONTENT                                 │
│                         (What Gets Served)                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────────────────────────────────────────────────────┐    │
│  │                     PostgreSQL Database                         │    │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │    │
│  │  │ claude.      │  │ claude.      │  │ claude.      │         │    │
│  │  │ knowledge    │  │ process_     │  │ sessions     │         │    │
│  │  │ (161 entries)│  │ registry (32)│  │ (198 logs)   │         │    │
│  │  └──────────────┘  └──────────────┘  └──────────────┘         │    │
│  └────────────────────────────────────────────────────────────────┘    │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                         TIER 3: SUPPORTING                              │
│                         (Governance & Quality)                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐             │
│  │ Governance   │    │ Doc Standards│    │ Test Suites  │             │
│  │ Plan         │    │              │    │              │             │
│  └──────────────┘    └──────────────┘    └──────────────┘             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## How They Work Together

### Scenario: "Add a feature for [anything]"

1. **PID Process** (Tier 1)
   - Guides HOW to approach the work
   - Ensures we validate before building

2. **CLAUDE.md** (Tier 1)
   - Already loaded - Claude knows project standards
   - Knows tech stack, rules, structure

3. **hooks.json → knowledge_retriever.py** (Tier 1)
   - Fires on the prompt
   - Queries `claude.knowledge` (Tier 2)
   - Injects relevant patterns/gotchas

4. **Process Registry** (Tier 2)
   - Detects "Feature Implementation" workflow
   - Provides standard steps

5. **Governance Plan** (Tier 3)
   - Ensures we follow the rules
   - Tracks compliance

---

## Quick Reference: What Goes Where

| I want to... | Document | Tier |
|--------------|----------|------|
| Learn the development methodology | PID Process | 1 |
| Configure a project for Claude | CLAUDE.md | 1 |
| Enable knowledge injection | hooks.json + scripts | 1 |
| Understand system architecture | ARCHITECTURE.md | 1 |
| Store a reusable pattern | claude.knowledge table | 2 |
| Define a standard workflow | claude.process_registry | 2 |
| Create a deep guide | .claude/skills/*.md | 2 |
| Set governance rules | Governance Plan | 3 |
| Define doc standards | Documentation Standards | 3 |
| Test the system | Test suites | 3 |

---

## Minimum Viable System

To get the Claude Family system working for ANY project, you need:

### Absolute Minimum (4 things):

1. **CLAUDE.md** in the project
2. **hooks.json** in `.claude/`
3. **knowledge_retriever.py** in `scripts/`
4. **Knowledge entries** in database

### Recommended Addition (2 more):

5. **stop_hook_enforcer.py** for reminders
6. **PID Process** for methodology

### Full System (everything):

All documents in Tier 1, 2, and 3.

---

## Summary

| Tier | Documents | Purpose |
|------|-----------|---------|
| **1 ESSENTIAL** | PID Process, CLAUDE.md, hooks.json, Hook Scripts, ARCHITECTURE.md | THE SYSTEM |
| **2 CONTENT** | Knowledge entries, Process registry, Skills | WHAT IT SERVES |
| **3 SUPPORTING** | Governance, Standards, Tests | HOW IT'S GOVERNED |

The **core question** "How does Claude know what to do?" is answered by:

1. **CLAUDE.md** - Loaded at session start (project context)
2. **Hooks** - Fire on every prompt (inject relevant knowledge)
3. **Database** - Contains the actual knowledge to inject
4. **PID Process** - Ensures everything is properly validated

---

**Document Status**: COMPLETE
**This IS the Core Documents Reference**
