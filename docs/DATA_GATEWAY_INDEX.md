# Data Gateway Documentation Index

**Date**: 2025-12-04
**Purpose**: Navigation guide for Data Gateway workflow tools documentation
**Status**: Complete - Phase 1

---

## Overview

The **Data Gateway** is a set of PostgreSQL workflow tools designed to provide a structured, validated interface for Claude agents to interact with the Feedback and Documentation domains in the `claude` schema.

Instead of requiring agents to write custom SQL with validation logic, these workflow tools encapsulate business rules, data quality checks, and relationship management in reusable PostgreSQL functions.

---

## Documentation Suite

### 1. Domain Analysis

**File**: `DATA_GATEWAY_DOMAIN_ANALYSIS.md`
**Purpose**: Comprehensive analysis of table structures, valid values, and business rules
**Audience**: Architects, developers designing new workflow tools

**Contents**:
- Complete schema documentation for 5 tables
- Valid status/type values extracted from production data
- Required fields and constraints analysis
- Workflow transition diagrams
- Data quality observations
- Relationship mappings
- Future enhancement recommendations

**When to use**:
- Understanding the domain model
- Designing new workflow tools
- Planning schema migrations
- Investigating data quality issues
- Documenting business rules

**Key sections**:
- Section 1: Feedback Domain (3 tables)
- Section 2: Documentation Domain (2 tables)
- Section 3: Workflow Tool Specifications (5 tools)
- Section 4: Data Quality Observations
- Section 5: Future Enhancements
- Section 6: Summary & Recommendations

---

### 2. SQL Implementation Specifications

**File**: `DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md`
**Purpose**: Complete SQL function definitions with validation and business logic
**Audience**: Database developers, DevOps engineers

**Contents**:
- 5 workflow tool function definitions (PL/pgSQL)
- 3 utility view definitions
- Validation logic and error handling
- Usage examples for each tool
- Recommended database constraints
- Installation scripts

**When to use**:
- Implementing workflow tools in database
- Understanding function parameters and return values
- Debugging SQL errors
- Adding new constraints
- Reviewing validation logic

**Workflow tools implemented**:
1. `create_feedback` - Create new feedback item
2. `add_feedback_comment` - Add comment to feedback
3. `resolve_feedback` - Mark feedback as fixed/won't fix
4. `register_document` - Register new document
5. `link_document_to_project` - Link document to project

**Utility views**:
1. `feedback_with_stats` - Feedback with comment/screenshot counts
2. `documents_with_projects` - Documents with all linked projects
3. `open_feedback_summary` - Project-level feedback summary

---

### 3. Quick Reference Guide

**File**: `DATA_GATEWAY_QUICK_REFERENCE.md`
**Purpose**: Quick lookup for common operations and queries
**Audience**: Claude Code agents, developers using the tools

**Contents**:
- Quick start examples for each tool
- Common query patterns
- Validation rules summary table
- Valid values reference
- Error messages and troubleshooting
- Best practices
- Python helper functions
- Slash command integration examples

**When to use**:
- Creating feedback or registering documents
- Looking up valid values
- Troubleshooting errors
- Writing queries to view feedback/documents
- Building automation scripts

**Quick start sections**:
- Create Bug Report
- Add Comment to Feedback
- Resolve Feedback
- Register Document
- Link Document to Additional Project

**Common queries**:
- View Open Feedback for Project
- View Project Feedback Summary
- View Feedback Conversation
- Find Documents by Type
- Search Documents by Keywords

---

## Document Relationships

```
DATA_GATEWAY_INDEX.md (this file)
├─ DATA_GATEWAY_DOMAIN_ANALYSIS.md
│  ├─ Schema structure and analysis
│  ├─ Business rules documentation
│  └─ Workflow specifications (conceptual)
│
├─ DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md
│  ├─ SQL function implementations
│  ├─ Validation logic
│  └─ Database constraints
│
└─ DATA_GATEWAY_QUICK_REFERENCE.md
   ├─ Quick start examples
   ├─ Common queries
   └─ Troubleshooting guide
```

---

## Getting Started

### For Claude Code Agents

**Goal**: Create a bug report for a project

1. Read: `DATA_GATEWAY_QUICK_REFERENCE.md` → "Create Bug Report"
2. Execute the SQL query pattern, replacing placeholders
3. If errors occur, see "Error Messages & Troubleshooting" section

**Goal**: Register a new documentation file

1. Read: `DATA_GATEWAY_QUICK_REFERENCE.md` → "Register Document"
2. Calculate file hash (see Python helper function)
3. Execute the SQL query with correct doc_type from valid values table
4. Link to project(s) using `link_document_to_project` if needed

### For Database Developers

**Goal**: Install workflow tools in database

1. Read: `DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md` → "Installation Script"
2. Run function creation scripts in order
3. Create utility views
4. OPTIONAL: Add database constraints (review data quality first)
5. Grant permissions to claude_agents role

**Goal**: Add a new workflow tool

1. Read: `DATA_GATEWAY_DOMAIN_ANALYSIS.md` to understand domain
2. Design tool specification (Section 3 format)
3. Implement SQL function (use existing tools as templates)
4. Add to `DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md`
5. Add quick start section to `DATA_GATEWAY_QUICK_REFERENCE.md`

### For Architects/Planners

**Goal**: Understand current state and plan improvements

1. Read: `DATA_GATEWAY_DOMAIN_ANALYSIS.md` → Sections 4-6
2. Review data quality observations
3. Review future enhancement recommendations
4. Prioritize improvements based on business needs
5. Document decisions in new ADR

**Goal**: Plan schema migration

1. Read: `DATA_GATEWAY_DOMAIN_ANALYSIS.md` → Section 4.2
2. Review schema migration recommendations
3. Check impact on existing workflow tools
4. Plan migration in phases (high → medium → low priority)
5. Update workflow tools to reflect schema changes

---

## Workflow Tool Matrix

| Tool Name | Input | Output | Status | Priority |
|-----------|-------|--------|--------|----------|
| create_feedback | project_id, type, description, priority | feedback_id | ✅ Implemented | P0 |
| add_feedback_comment | feedback_id, author, message | comment_id | ✅ Implemented | P1 |
| resolve_feedback | feedback_id, resolution, notes | updated record | ✅ Implemented | P0 |
| register_document | doc_type, title, path, etc. | doc_id | ✅ Implemented | P0 |
| link_document_to_project | doc_id, project_id | link_id | ✅ Implemented | P1 |
| update_feedback_status | feedback_id, new_status | updated record | 🔄 Planned | P1 |
| archive_document | doc_id, reason | success | 🔄 Planned | P2 |
| search_feedback | filters, sort | feedback[] | 🔄 Planned | P2 |
| search_documents | query, filters | documents[] | 🔄 Planned | P2 |
| link_related_items | item1_id, item2_id, type | link_id | 💭 Proposed | P3 |

**Legend**:
- ✅ Implemented: SQL function exists and documented
- 🔄 Planned: Specified but not yet implemented
- 💭 Proposed: Concept only, not yet specified

---

## Schema Coverage

### Feedback Domain

| Table | Coverage | Workflow Tools | Views |
|-------|----------|----------------|-------|
| feedback | ✅ Complete | create_feedback, resolve_feedback | feedback_with_stats, open_feedback_summary |
| feedback_comments | ✅ Complete | add_feedback_comment | feedback_with_stats (count) |
| feedback_screenshots | ✅ Complete | create_feedback (array param), add_feedback_comment | feedback_with_stats (count) |

### Documentation Domain

| Table | Coverage | Workflow Tools | Views |
|-------|----------|----------------|-------|
| documents | ✅ Complete | register_document | documents_with_projects |
| document_projects | ✅ Complete | link_document_to_project, register_document | documents_with_projects |

---

## Data Quality Status

### Feedback Domain

**Overall Quality**: ⚠️ Good with minor issues

**Issues**:
- Missing timestamps on some test data (LOW impact)
- One resolved item missing resolution notes (LOW impact)
- Low comment usage (usage pattern, not quality issue)

**Recommended actions**:
1. Add NOT NULL constraints on critical fields
2. Add CHECK constraint for resolution notes
3. Add 'in_progress' status

### Documentation Domain

**Overall Quality**: ✅ Excellent

**Issues**:
- 293 documents still use deprecated project_id column (MEDIUM impact)
- category field redundant (LOW impact)

**Recommended actions**:
1. Migrate documents.project_id → document_projects
2. Drop category column after migration
3. Add CHECK constraints for archive consistency

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-12-04 | Initial documentation suite created | Claude Code |
| | | - Domain analysis complete | |
| | | - 5 workflow tools implemented | |
| | | - 3 utility views created | |
| | | - Quick reference guide published | |

---

## Next Steps

### Phase 2: Enhanced Workflow Tools (Planned)

1. **update_feedback_status** - Support 'in_progress' status
2. **archive_document** - Automated archival with validation
3. **search_feedback** - Advanced filtering and sorting
4. **search_documents** - Full-text search with tag filters

### Phase 3: Advanced Features (Proposed)

1. **link_related_items** - Cross-domain relationships
2. **feedback_relationships** - Duplicate/blocks/related tracking
3. **document_versioning** - Version history support
4. **review_workflow** - Document review process

### Phase 4: Integration (Proposed)

1. Slash command wrappers for all workflow tools
2. Python SDK for workflow tools
3. CLI utilities for common operations
4. Web UI for feedback management

---

## Support & Maintenance

### Documentation Ownership

- **Primary Owner**: Claude Code Infrastructure Team
- **Review Cycle**: Quarterly (every 3 months)
- **Update Policy**: Update within 1 week of schema changes

### Getting Help

1. **For usage questions**: See `DATA_GATEWAY_QUICK_REFERENCE.md`
2. **For errors**: See "Error Messages & Troubleshooting" section
3. **For new requirements**: Discuss in architecture review
4. **For bugs**: Create feedback using `/feedback-create` command

### Contributing

To propose a new workflow tool:

1. Document the business need
2. Design the function signature (parameters, return value)
3. Define validation rules
4. Add to `DATA_GATEWAY_DOMAIN_ANALYSIS.md` Section 3
5. Implement SQL function in `DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md`
6. Add quick start to `DATA_GATEWAY_QUICK_REFERENCE.md`
7. Update this index with tool status

---

## Related Documentation

**Project Level**:
- `CLAUDE.md` - Claude Family project instructions
- `README.md` - Project overview

**Claude Family System**:
- `docs/SCHEMA_DETAIL_claude_family.md` - Claude Family schema
- `docs/ARCHITECTURE_PLAN_v2.md` - Overall architecture
- `docs/sops/` - Standard Operating Procedures

**Database**:
- Schema: `claude` (base tables)
- Schema: `claude_pm` (views/interface)
- Schema: `claude_family` (identities, sessions)

---

**Document Type**: Index / Navigation Guide
**Status**: ✅ Complete
**Last Updated**: 2025-12-04
**Next Review**: 2026-03-04
**Version**: 1.0
