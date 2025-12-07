# Governance System Findings & Action Plan

**Date**: 2025-12-07
**Author**: claude-code-unified
**Purpose**: Comprehensive analysis of what documents Claude needs and how to enforce them

---

## Executive Summary

The current governance system has the right structure but critical gaps in:
1. **Core Document Classification** - ARCHITECTURE.md not marked as core (BUG)
2. **Missing Standards Documents** - No UI, API, or development standards
3. **Enforcement Deployment** - Only claude-family has process enforcement hooks
4. **Document Purpose Confusion** - Slash commands marked as "core" instead of reference docs

---

## Research Findings

### Anthropic Best Practices (Sources)

From [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices):
- **CLAUDE.md** is THE primary instruction file - auto-loaded at session start
- **Explore → Plan → Code → Commit** workflow is recommended
- **Test-Driven Development** with explicit TDD mode
- **Subagents** for isolated verification
- **Permission control** - deny-all, allowlist needed tools

From [Claude Agent SDK](https://www.anthropic.com/engineering/building-agents-with-the-claude-agent-sdk):
- **Context → Action → Verify** loop structure
- **Programmatic evaluations** for governance
- **Consistent tool naming** conventions
- **Transparent, testable documentation**

From [Enterprise AI Governance](https://www.ibm.com/think/topics/ai-governance):
- **Stage-gate processes** with review at milestones
- **Clear policies** for development, testing, deployment
- **Comprehensive documentation** of all processes
- **Role-based accountability**

---

## Current State Analysis

### Document Inventory (Active Documents)

| Type | Count | Marked Core | Should Be Core |
|------|-------|-------------|----------------|
| CLAUDE_CONFIG | 17 | 13 | 17 (all) |
| ARCHITECTURE | 43 | 0 | ~10 (main ones) |
| SOP | 23 | 1 | 6 (main SOPs) |
| ADR | 4 | 0 | 4 (all) |
| README | 52 | 0 | ~5 (project READMEs) |
| REFERENCE | 363 | 37 | 0 (these are tools) |
| SESSION_NOTE | 190 | 35 | 0 (these are history) |

**Problem**: 72 slash command files marked as "core" but they're tools, not reference docs.

### Enforcement Status by Project

| Project | CLAUDE.md | hooks.json | UserPromptSubmit | DB Constraints |
|---------|-----------|------------|------------------|----------------|
| claude-family | ✅ | ✅ | ✅ Process routing | ✅ Full |
| ATO-Tax-Agent | ✅ | ✅ | ❌ No routing | ❌ Partial |
| mission-control-web | ✅ | ✅ | ❌ No routing | ❌ Partial |
| nimbus-user-loader | ✅ | ✅ | ❌ No routing | ❌ Partial |

**Problem**: Only 1 of 4 projects has process enforcement.

---

## Required Document Structure

### TIER 1: Project Identity (Per Project - MUST EXIST)

```
project/
├── CLAUDE.md              # Project config, AI instructions
├── ARCHITECTURE.md        # System design, schemas
├── PROBLEM_STATEMENT.md   # Why this exists, goals
└── README.md              # Human-readable overview
```

**These should be marked `is_core = true` for the project.**

### TIER 2: Global Standards (Shared - MUST FOLLOW)

Location: `C:\Projects\claude-family\docs\standards\`

| Document | Purpose | Status |
|----------|---------|--------|
| DEVELOPMENT_STANDARDS.md | Coding patterns, conventions | MISSING |
| UI_COMPONENT_STANDARDS.md | GUI patterns, pagination, filters | MISSING |
| DATABASE_STANDARDS.md | Schema patterns, naming | PARTIAL (Data Gateway) |
| API_STANDARDS.md | Endpoint patterns, responses | MISSING |
| DOCUMENTATION_STANDARDS.md | How to write docs | MISSING |
| WORKFLOW_STANDARDS.md | Design→Build→Test→Document | MISSING |

**These should be marked `is_core = true` globally.**

### TIER 3: Standard Operating Procedures

| SOP | Purpose | Status |
|-----|---------|--------|
| SOP-001 | Knowledge vs Docs vs Tasks | ✅ EXISTS |
| SOP-002 | Build Task Lifecycle | ✅ EXISTS |
| SOP-003 | Document Classification | ✅ EXISTS |
| SOP-004 | Project Initialization | ✅ EXISTS |
| SOP-005 | Auto-Reviewers | ✅ EXISTS |
| SOP-006 | Testing Process | ✅ EXISTS |

---

## What's Missing: UI Component Standards Example

When Claude builds ANY user interface, it should follow:

```markdown
## UI_COMPONENT_STANDARDS.md

### Tables
- ALL tables MUST have pagination (default: 20 rows)
- ALL tables MUST have column sorting
- ALL tables MUST have at least one filter
- Standard page sizes: 10, 20, 50, 100

### Filters
Required filter types by data:
- Text fields: Search input with debounce (300ms)
- Status fields: Dropdown with "All" option
- Date fields: Date range picker
- Boolean fields: Toggle or dropdown

### Standard Actions
Every list view must have:
- Create button (top right)
- Row actions: Edit, Delete (with confirmation)
- Bulk actions: Select all, bulk delete

### States
Every component must handle:
- Loading state (skeleton or spinner)
- Empty state (message + CTA)
- Error state (message + retry)

### Accessibility
- All interactive elements keyboard accessible
- ARIA labels on icons
- Focus management on dialogs
```

**This document doesn't exist. MCW was built without these standards.**

---

## Action Plan

### Phase 1: Fix Core Document Classification (Immediate)

```sql
-- 1. Unmark slash commands as core (they're tools, not reference)
UPDATE claude.documents
SET is_core = false, core_reason = NULL
WHERE file_path LIKE '%\.claude\commands\%'
  AND doc_type IN ('REFERENCE', 'SESSION_NOTE', 'OTHER', 'COMPLETION_REPORT');

-- 2. Mark ARCHITECTURE.md as core for each project
UPDATE claude.documents
SET is_core = true, core_reason = 'System architecture - must be followed'
WHERE (file_path LIKE '%\ARCHITECTURE.md' OR file_path LIKE '%\architecture.md')
  AND doc_type = 'ARCHITECTURE';

-- 3. Mark PROBLEM_STATEMENT.md as core
UPDATE claude.documents
SET is_core = true, core_reason = 'Project goals - provides context'
WHERE file_path LIKE '%\PROBLEM_STATEMENT.md';

-- 4. Mark main SOPs as core
UPDATE claude.documents
SET is_core = true, core_reason = 'Standard procedure - must be followed'
WHERE file_path LIKE '%\docs\sops\SOP-%.md';
```

### Phase 2: Create Missing Standards (This Week)

1. **DEVELOPMENT_STANDARDS.md** - Coding patterns
2. **UI_COMPONENT_STANDARDS.md** - GUI rules
3. **API_STANDARDS.md** - Endpoint conventions
4. **WORKFLOW_STANDARDS.md** - Design→Build→Test→Document

### Phase 3: Deploy Enforcement (This Week)

1. Copy UserPromptSubmit hook config to all projects
2. Update process router to inject relevant standards
3. Add pre-commit checks for standards compliance

### Phase 4: Update MCW (Next Week)

1. Add "Standards" page showing all standards docs
2. Fix documents page to show REAL core docs
3. Add compliance check for standards adherence

---

## Process Router Enhancement

Current router injects process guidance. Enhanced router should also inject:

```python
# When task involves UI work
if matches_ui_task(prompt):
    inject_document("UI_COMPONENT_STANDARDS.md")

# When task involves database
if matches_db_task(prompt):
    inject_document("DATABASE_STANDARDS.md")

# When task involves API
if matches_api_task(prompt):
    inject_document("API_STANDARDS.md")
```

---

## Metrics to Track

| Metric | Current | Target |
|--------|---------|--------|
| Projects with enforcement | 1/4 (25%) | 4/4 (100%) |
| Standards documents | 1/6 (17%) | 6/6 (100%) |
| Core docs correctly marked | ~20% | 100% |
| MCW pages following UI standards | Unknown | 100% |

---

## Conclusion

The governance SYSTEM is sound. The governance CONTENT is incomplete.

**We have:**
- Process routing mechanism (works)
- Enforcement hierarchy (defined)
- 30 processes with steps (complete)
- 6 SOPs (good coverage)

**We need:**
- Standards documents (create 5)
- Fix core classification (SQL updates)
- Deploy to all projects (copy hooks)
- Verify MCW follows standards (audit)

This is not about simplification - it's about COMPLETION.

---

**Next Steps**:
1. Run SQL to fix core classification
2. Create UI_COMPONENT_STANDARDS.md
3. Create DEVELOPMENT_STANDARDS.md
4. Deploy hooks to all projects

---

**Version**: 1.0
**Created**: 2025-12-07
