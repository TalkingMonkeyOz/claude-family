# Documentation Standards for Claude Family Projects

**Version**: 1.0
**Created**: 2025-10-23
**Status**: ACTIVE
**Based on**: 2025 AI Documentation Best Practices Research

---

## Philosophy

**Problem**: 29+ markdown files, many outdated, hard to find what's current, no clear structure.

**Solution**: AI-optimized documentation system that:
- ✅ Works with Claude Code's 200K token context window
- ✅ Integrates with existing MCP + PostgreSQL infrastructure
- ✅ Follows 2025 AI documentation standards (llms.txt, chunking, structure)
- ✅ Enforces lifecycle management (active → deprecated → archived)
- ✅ Automated where possible

**Core Principle**: **Documentation-first** - Document WHY before WHAT, treat docs as code.

---

## Document Types & Lifecycle

### Type 1: Project Index (`llms.txt`)

**Purpose**: AI-readable entry point for each project
**Location**: Project root (e.g., `C:\Projects\claude-family\llms.txt`)
**Format**: Markdown
**Lifecycle**: PERMANENT (updated, never deprecated)

**Template**:
```markdown
# Project Name

> One-sentence summary of project purpose

## Overview
Brief 2-3 sentence description

## Quick Links
- [Getting Started](./CLAUDE.md) - Project-specific Claude context
- [Architecture](./docs/architecture.md) - System design
- [Contributing](./docs/contributing.md) - How to contribute

## Recent Updates
- 2025-10-23: Latest significant change
- 2025-10-21: Previous change

## Key Documents
### Active Documentation
- CLAUDE.md - Current project context for Claude instances
- README.md - Human-readable project overview

### Historical Documentation
- docs/DEPRECATED_* - Archived old architectures
```

**Rules**:
- Keep under 200 lines
- Update when significant changes occur
- Links to detailed docs, don't duplicate content
- Think: "What does Claude need to know to start working?"

---

### Type 2: Project Context (`CLAUDE.md`)

**Purpose**: Auto-loaded context for Claude Code CLI
**Location**: Project root
**Format**: Markdown with YAML frontmatter
**Lifecycle**: LIVING (updated continuously)
**Max Length**: 250 lines (per ANTI-HALLUCINATION.md)

**Template**:
```markdown
---
project: project-name
type: infrastructure|work|personal
version: 1.0
last_updated: 2025-10-23
status: active
---

# Project Name - Claude Context

**Type**: [infrastructure/work/personal]
**Purpose**: One-line purpose

---

## Build Commands

\`\`\`bash
# Commands Claude needs to know
npm build
pytest
dotnet build
\`\`\`

---

## Critical Rules

**NEVER**:
- Rule 1 (with WHY)
- Rule 2 (with WHY)

**ALWAYS**:
- Rule 1 (with WHY)
- Rule 2 (with WHY)

---

## Project Structure

\`\`\`
project/
├── src/           # Description
├── tests/         # Description
└── docs/          # Description
\`\`\`

---

## Recent Work

\`\`\`sql
-- Query recent sessions from database
SELECT summary, session_start FROM claude_family.session_history
WHERE project_name = 'this-project'
ORDER BY session_start DESC LIMIT 5;
\`\`\`

---

## When Working Here

- Context 1
- Context 2
- Context 3

**Version**: X.X
**Last Updated**: YYYY-MM-DD
```

**Rules**:
- MUST be ≤250 lines (enforced by linter)
- Focus on actionable info Claude needs NOW
- Store detailed knowledge in PostgreSQL/MCP, not here
- Update version number when changing structure

---

### Type 3: Architecture Documents

**Purpose**: System design, technical decisions
**Location**: `docs/architecture/`
**Format**: Markdown with decision records
**Lifecycle**: VERSIONED (v1, v2, v3)

**Template**:
```markdown
# [Component/System] Architecture

**Version**: X.X
**Status**: ACTIVE|DEPRECATED
**Replaced By**: [link if deprecated]
**Date**: YYYY-MM-DD

---

## Decision Record

**Problem**: What problem does this solve?

**Context**: What was the situation?

**Decision**: What did we decide?

**WHY**: Critical - explain reasoning, tradeoffs, alternatives considered

**Consequences**: What are the implications?

---

## System Overview

[Diagram/description]

## Components

### Component 1
- **Purpose**: What it does
- **Dependencies**: What it needs
- **Data Flow**: How data moves

---

## Change History

| Version | Date | Changes | Reason |
|---------|------|---------|--------|
| 2.0 | 2025-10-21 | Simplified from 9 to 2 instances | Official Claude Code guidance |
| 1.0 | 2025-10-10 | Initial architecture | First implementation |
```

**Lifecycle Management**:
- **ACTIVE** → Update in place, increment version
- **DEPRECATED** → Rename to `DEPRECATED_vX_name.md`, add warning banner
- **ARCHIVED** → Move to `docs/archive/YYYY-MM/`

---

### Type 4: Session Notes

**Purpose**: Record work done in specific sessions
**Location**: `docs/session-notes/YYYY-MM-DD_description.md`
**Format**: Structured markdown
**Lifecycle**: APPEND-ONLY (never edit old sessions)

**Template**:
```markdown
# Session: [Brief Description]

**Date**: YYYY-MM-DD
**Claude Instance**: claude-desktop | claude-code-unified
**Project**: project-name
**Duration**: X hours
**Session ID**: [UUID from database]

---

## Objectives
- [ ] Goal 1
- [ ] Goal 2

## What Was Done
1. Task 1 - Result
2. Task 2 - Result

## Key Decisions
- **Decision**: What we decided
- **WHY**: Reasoning
- **Alternatives Considered**: What else we looked at

## Learnings
- Learning 1 (applicable to: all projects | this project only)
- Learning 2

## Next Session
- [ ] Continue with X
- [ ] Address Y

---

## Database Log

\`\`\`sql
-- Logged to claude_family.session_history
-- Session ID: [UUID]
-- Query: SELECT * FROM claude_family.session_history WHERE session_id = '[UUID]'
\`\`\`
```

**Rules**:
- Create ONLY when session produces significant artifacts
- Don't duplicate what's in database (link to it instead)
- Archive after 30 days: `docs/session-notes/archive/YYYY-MM/`

---

### Type 5: Standards & Guidelines

**Purpose**: How-to guides, best practices, standards (like this doc!)
**Location**: `docs/standards/`
**Format**: Markdown
**Lifecycle**: VERSIONED (major changes = new version)

**Naming**: `STANDARD_NAME_vX.md`

**Template**:
```markdown
# Standard Name

**Version**: X.X
**Status**: ACTIVE|DEPRECATED
**Applies To**: All projects | Specific projects
**Date**: YYYY-MM-DD

---

## Purpose
Why this standard exists

## Scope
What it covers

## Rules
1. Rule 1
   - Why
   - How to comply
   - Examples

## Enforcement
- Automated checks: [tool/script]
- Manual review: [when]

## Exceptions
- Exception 1 and when it's allowed

## Version History
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-23 | Initial version |
```

---

## Document Metadata (Required)

Every document MUST have frontmatter:

```yaml
---
title: Document Title
version: X.X
status: active|deprecated|archived
last_updated: YYYY-MM-DD
applies_to: project-name|all
type: index|context|architecture|session|standard
---
```

**Status Values**:
- `active` - Current and maintained
- `deprecated` - Superseded but kept for reference
- `archived` - Historical, no longer relevant

---

## Folder Structure (Enforced)

```
project-root/
├── llms.txt                          # AI entry point
├── CLAUDE.md                         # Project context (≤250 lines)
├── README.md                         # Human-readable overview
├── docs/
│   ├── architecture/                 # System design docs
│   │   ├── current_architecture_v2.md
│   │   └── DEPRECATED_v1_architecture.md
│   ├── standards/                    # Guidelines & processes
│   │   ├── DOCUMENTATION_STANDARDS_v1.md
│   │   └── CODE_REVIEW_PROCESS_v1.md
│   ├── session-notes/                # Work logs
│   │   ├── 2025-10-23_memory-graph-rebuild.md
│   │   └── archive/
│   │       └── 2025-10/              # Archive by month
│   └── archive/                      # Deprecated docs
│       ├── 2025-10/
│       │   ├── DEPRECATED_OCT10_ARCHITECTURE.md
│       │   └── COMPLETE_SETUP_GUIDE.md (outdated)
└── .doc-metadata.json                # Automated tracking
```

---

## Automation & Enforcement

### 1. Pre-Commit Hook (Git)

```bash
# .git/hooks/pre-commit
#!/bin/bash
# Check CLAUDE.md line count
lines=$(wc -l < CLAUDE.md)
if [ "$lines" -gt 250 ]; then
    echo "ERROR: CLAUDE.md exceeds 250 lines ($lines lines)"
    exit 1
fi

# Check for required frontmatter
# [validation script]
```

### 2. Monthly Documentation Audit (Automated)

**Script**: `scripts/audit_documentation.py`

```python
# Runs automatically via cron/Task Scheduler
# Checks:
# - Documents missing metadata
# - Documents not updated in 6+ months
# - CLAUDE.md line count
# - Session notes older than 30 days (move to archive)
# - Deprecated docs older than 90 days (move to archive)
# Outputs: docs/AUDIT_REPORT_YYYY-MM.md
```

### 3. llms.txt Generator (Automated)

**Script**: `scripts/generate_llms_txt.py`

```python
# Regenerates llms.txt from:
# - CLAUDE.md metadata
# - Recent session history (PostgreSQL)
# - Active architecture docs
# Run on: Every commit, or monthly
```

---

## Integration with Existing Systems

### PostgreSQL Database

**Table**: `claude_family.documentation_index`

```sql
CREATE TABLE claude_family.documentation_index (
    doc_id UUID PRIMARY KEY,
    project_name VARCHAR(100),
    doc_path TEXT,
    doc_type VARCHAR(50), -- 'index', 'context', 'architecture', etc.
    title VARCHAR(200),
    version VARCHAR(20),
    status VARCHAR(20), -- 'active', 'deprecated', 'archived'
    last_updated TIMESTAMP,
    applies_to TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexed for fast retrieval
CREATE INDEX idx_doc_status ON claude_family.documentation_index(project_name, status);
CREATE INDEX idx_doc_type ON claude_family.documentation_index(doc_type, status);
```

**Purpose**: Claude can query "What's the current architecture doc?" instead of guessing.

---

### MCP Memory Graph

**Entities to Create**:
- Document entities with status tags
- Relations: "supersedes", "references", "implements"

**Example**:
```python
create_entities([{
    "name": "CLAUDE.md v2.0",
    "entityType": "documentation",
    "observations": [
        "Type: Project context",
        "Status: ACTIVE",
        "Project: claude-family",
        "Lines: 80 (within 250 limit)",
        "Last updated: 2025-10-23",
        "Purpose: Auto-loaded context for Claude Code CLI"
    ]
}])
```

---

## Writing Guidelines (AI-Optimized)

### 1. Semantic Chunking

**DO**: Break into logical sections with clear H2/H3 headings
```markdown
## Component Name
Brief intro (2-3 sentences)

### Purpose
What it does

### Dependencies
What it needs

### Usage
How to use
```

**DON'T**: Long paragraphs without structure

---

### 2. Code Examples (Required)

Every technical concept MUST have:
```markdown
## Concept Name

### Purpose
Why it exists

### Example
\`\`\`python
# Working example with comments
code_here()
\`\`\`

### Common Errors
- Error 1: Why it happens, how to fix
```

---

### 3. Focus on WHY

**BAD**:
```markdown
## Setup
Run `npm install`
```

**GOOD**:
```markdown
## Setup

**WHY**: This project uses Node.js because [reasoning]

**Install dependencies**:
\`\`\`bash
npm install  # Installs packages from package.json
\`\`\`

**What this does**: Downloads 50+ packages including React, Express, etc.
**Troubleshooting**: If you see EACCES errors, [solution]
```

---

### 4. Active Voice for Relations

**DO**: "ClaudePM replaces Diana GUI"
**DON'T**: "Diana GUI was replaced by ClaudePM"

---

## Review & Update Cycle

### Weekly (Automated)
- ✅ Generate llms.txt for all projects
- ✅ Check CLAUDE.md line counts
- ✅ Archive session notes >30 days

### Monthly (Manual)
- ✅ Review deprecated docs >90 days → Archive
- ✅ Run audit script: `python scripts/audit_documentation.py`
- ✅ Update version numbers on changed docs
- ✅ Review MCP memory graph entities

### Quarterly (Manual)
- ✅ Review all ACTIVE architecture docs - still current?
- ✅ Consolidate redundant session notes
- ✅ Update standards based on new learnings

---

## Deprecation Process

When architecture/system changes significantly:

1. **Create New Doc**:
   - Write new doc with updated info
   - Increment version number
   - Set status: `active`

2. **Deprecate Old Doc**:
   - Rename: `DEPRECATED_vX_name.md`
   - Add banner at top:
     ```markdown
     # ⚠️ DEPRECATED - [Title]

     **Deprecated**: YYYY-MM-DD
     **Reason**: [Why it changed]
     **Replaced By**: [Link to new doc]
     ```
   - Set status: `deprecated`
   - Leave in place for 90 days

3. **Archive After 90 Days**:
   - Move to `docs/archive/YYYY-MM/`
   - Update database record
   - Remove from llms.txt

4. **Update References**:
   - Update llms.txt
   - Update CLAUDE.md if it linked to old doc
   - Update database queries
   - Update MCP memory graph

---

## Migration Plan (Immediate Actions)

### Phase 1: Cleanup (Week 1)
- [ ] Audit all 29 markdown files in claude-family
- [ ] Identify: ACTIVE, DEPRECATED, OBSOLETE
- [ ] Rename deprecated docs: `DEPRECATED_*`
- [ ] Move obsolete to `docs/archive/2025-10/`
- [ ] Create documentation_index table in PostgreSQL

### Phase 2: Standardization (Week 2)
- [ ] Create llms.txt for each project
- [ ] Add frontmatter to all active docs
- [ ] Ensure CLAUDE.md files ≤250 lines
- [ ] Generate .doc-metadata.json

### Phase 3: Automation (Week 3)
- [ ] Create pre-commit hook for line limits
- [ ] Create audit script: `audit_documentation.py`
- [ ] Create llms.txt generator script
- [ ] Setup monthly cron job

### Phase 4: Integration (Week 4)
- [ ] Populate documentation_index table
- [ ] Add doc entities to MCP memory graph
- [ ] Test Claude Code loading times with new structure
- [ ] Train on new system

---

## Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Find Time** | <30 seconds to find any doc | User survey |
| **Currency** | 100% docs have status metadata | Audit script |
| **Line Limit** | 100% CLAUDE.md files ≤250 lines | Pre-commit hook |
| **Update Frequency** | Active docs updated ≥monthly | Database query |
| **Deprecation Age** | No deprecated docs >90 days in main folder | Audit script |
| **Claude Context Load** | <5 seconds with new structure | Measure in practice |

---

## Examples

### Good Example: llms.txt

```markdown
# Claude Family Infrastructure

> Shared configuration, scripts, and documentation for Claude instances

## Overview
Infrastructure project for 2 Claude instances (desktop GUI + unified CLI)
working across 4 projects with persistent PostgreSQL memory and MCP integration.

## Quick Start
- [CLAUDE.md](./CLAUDE.md) - Project context (80 lines)
- [Architecture](./docs/architecture/current_v2.md) - Simplified Oct 21, 2025

## Recent Updates
- 2025-10-23: Documentation standards v1.0 created
- 2025-10-21: Simplified from 9 instances to 2
- 2025-10-19: Database bloat elimination

## Key Documents
### Active
- CLAUDE.md (v1.0) - Minimal project context
- ANTI-HALLUCINATION.md - Bloat prevention protocol
- DOCUMENTATION_STANDARDS_v1.md - This doc

### Deprecated
- [Pre-Oct21 Architecture](./docs/archive/2025-10/DEPRECATED_OCT10_ARCHITECTURE.md)

## Database
- PostgreSQL: ai_company_foundation
- Schemas: claude_family (6 tables), public (14 tables)
- Query context: `SELECT * FROM claude_family.session_history`
```

---

### Bad Example: Old README (What NOT to do)

```markdown
# Project

This is a project.

It does stuff. Here's how to use it:

Run the thing.

Then do the other thing.

If it doesn't work, try again.

# History
We started this in 2020. Then we added features. Then more features.
Now there are 50 features but we're not sure which ones work.

# Contributors
Thanks to everyone who helped!
```

**Problems**:
- ❌ No metadata
- ❌ Vague descriptions
- ❌ No structure for AI parsing
- ❌ No WHY explanations
- ❌ Unclear what's current
- ❌ No links to detailed docs

---

## Appendix: Tools & Resources

### Recommended Tools
- **Linter**: Custom Python script for metadata validation
- **Generator**: llms.txt auto-generator from database
- **Auditor**: Monthly doc health check script
- **Viewer**: PostgreSQL queries to find docs by status/type

### Further Reading
- [llms.txt Standard](https://llmstxt.org/)
- [AI Documentation Trends 2025](https://www.mintlify.com/blog/ai-documentation-trends-whats-changing-in-2025)
- [Optimizing Docs for AI](https://biel.ai/blog/optimizing-docs-for-ai-agents-complete-guide)

---

**Version**: 1.0
**Status**: ACTIVE
**Next Review**: 2025-11-23
**Maintained By**: Claude Family System

