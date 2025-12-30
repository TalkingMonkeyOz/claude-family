# Data Gateway Workflow Tools - Quick Reference Guide

**Date**: 2025-12-04
**Purpose**: Quick reference for using Feedback & Documentation workflow tools
**Audience**: Claude Code agents, human developers

---

## Quick Start

### Create Bug Report

```sql
SELECT claude.create_feedback(
  p_project_id := (SELECT project_id FROM claude.projects WHERE project_name = 'nimbus' LIMIT 1),
  p_feedback_type := 'bug',
  p_description := 'Describe the bug in detail: what happened, what was expected, steps to reproduce...',
  p_priority := 'high',  -- or 'medium', 'low'
  p_screenshot_paths := ARRAY['/path/to/screenshot.png']
);
```

### Add Comment to Feedback

```sql
SELECT claude.add_feedback_comment(
  p_feedback_id := 'your-feedback-uuid'::uuid,
  p_author := 'claude-code-unified',
  p_message := 'Update message here...'
);
```

### Resolve Feedback

```sql
-- Mark as fixed
SELECT claude.resolve_feedback(
  p_feedback_id := 'your-feedback-uuid'::uuid,
  p_resolution := 'fixed',
  p_notes := 'Detailed explanation of how it was fixed, including commit reference if applicable...',
  p_resolved_by := 'claude-code-unified'
);

-- Mark as won't fix
SELECT claude.resolve_feedback(
  p_feedback_id := 'your-feedback-uuid'::uuid,
  p_resolution := 'wont_fix',
  p_notes := 'Detailed justification for why this will not be addressed...',
  p_resolved_by := 'claude-code-unified'
);
```

### Register Document

```sql
SELECT claude.register_document(
  p_doc_type := 'ARCHITECTURE',  -- or GUIDE, SPEC, README, etc.
  p_doc_title := 'Document Title Here',
  p_file_path := '/absolute/path/to/document.md',
  p_file_hash := 'sha256-hash-here',
  p_project_ids := ARRAY[(SELECT project_id FROM claude.projects WHERE project_name = 'project-name' LIMIT 1)],
  p_version := '1.0',
  p_tags := ARRAY['tag1', 'tag2'],
  p_is_core := true,  -- only if this is core documentation
  p_core_reason := 'Explanation of why this is core documentation...',
  p_generated_by_agent := 'claude-code-unified'
);
```

### Link Document to Additional Project

```sql
SELECT claude.link_document_to_project(
  p_doc_id := 'your-doc-uuid'::uuid,
  p_project_id := 'project-uuid'::uuid,
  p_is_primary := false,  -- true only for primary project
  p_linked_by := 'claude-code-unified'
);
```

---

## Common Queries

### View Open Feedback for Project

```sql
-- All open feedback for a project
SELECT
  feedback_id::text,
  feedback_type,
  description,
  priority,
  created_at,
  comment_count,
  screenshot_count
FROM claude.feedback_with_stats
WHERE project_name = 'nimbus'
  AND status = 'new'
ORDER BY priority DESC, created_at ASC;

-- High priority bugs only
SELECT
  feedback_id::text,
  description,
  created_at,
  age_hours
FROM claude.feedback_with_stats
WHERE project_name = 'nimbus'
  AND status = 'new'
  AND feedback_type = 'bug'
  AND priority = 'high'
ORDER BY created_at ASC;
```

### View Project Feedback Summary

```sql
SELECT
  project_name,
  new_count,
  open_bugs,
  open_design,
  open_questions,
  open_changes,
  high_priority_count,
  oldest_open_feedback
FROM claude.open_feedback_summary
WHERE project_name = 'nimbus';
```

### View Feedback Conversation

```sql
-- Get feedback with all comments
SELECT
  f.feedback_id::text,
  f.feedback_type,
  f.description,
  f.status,
  f.created_at AS feedback_created,
  fc.author AS commenter,
  fc.message AS comment,
  fc.created_at AS comment_created
FROM claude.feedback f
LEFT JOIN claude.feedback_comments fc ON f.feedback_id = fc.feedback_id
WHERE f.feedback_id = 'your-feedback-uuid'::uuid
ORDER BY fc.created_at ASC NULLS FIRST;
```

### Find Documents by Type

```sql
-- Core architecture docs
SELECT
  doc_id::text,
  doc_title,
  file_path,
  version,
  primary_project_name,
  project_names
FROM claude.documents_with_projects
WHERE doc_type = 'ARCHITECTURE'
  AND is_core = true
  AND is_archived = false
ORDER BY doc_title;

-- All docs for a project
SELECT
  doc_type,
  doc_title,
  file_path,
  version,
  is_core,
  created_at
FROM claude.documents_with_projects
WHERE 'nimbus' = ANY(project_names)
  AND is_archived = false
ORDER BY doc_type, doc_title;
```

### Search Documents by Keywords

```sql
-- Search in tags
SELECT
  doc_id::text,
  doc_type,
  doc_title,
  file_path,
  tags
FROM claude.documents
WHERE 'architecture' = ANY(tags)
  AND is_archived = false;

-- Search in title
SELECT
  doc_id::text,
  doc_type,
  doc_title,
  file_path
FROM claude.documents
WHERE doc_title ILIKE '%claude family%'
  AND is_archived = false;
```

---

## Validation Rules Reference

### Feedback Creation

| Field | Rule |
|-------|------|
| project_id | REQUIRED, must exist in projects table |
| feedback_type | REQUIRED, must be: bug, design, question, change |
| description | REQUIRED, min 10 chars (50+ recommended for bugs) |
| priority | OPTIONAL, default: medium, must be: high, medium, low |
| status | AUTO-SET to 'new' |
| created_at | AUTO-SET to now() |

### Feedback Resolution

| Field | Rule |
|-------|------|
| resolution | REQUIRED, must be: fixed, wont_fix |
| notes | REQUIRED, min 20 chars (50+ for wont_fix) |
| resolved_by | REQUIRED |
| Current status | Must be 'new' (cannot re-resolve) |

### Document Registration

| Field | Rule |
|-------|------|
| doc_type | REQUIRED, must be one of 16 types (UPPERCASE) |
| doc_title | REQUIRED, min 5 chars |
| file_path | REQUIRED, absolute path |
| file_hash | STRONGLY RECOMMENDED (SHA-256) |
| status | AUTO-SET to 'ACTIVE' |
| category | AUTO-SET to lowercase(doc_type) |
| is_core + core_reason | If is_core=true, core_reason required (min 10 chars) |

### Document-Project Linking

| Field | Rule |
|-------|------|
| doc_id | REQUIRED, must exist in documents table |
| project_id | REQUIRED, must exist in projects table |
| is_primary | OPTIONAL, default: false, only one primary per document |
| Uniqueness | Cannot link same doc to same project twice |

---

## Valid Values Reference

### feedback_type

- `bug` - Software defects
- `design` - UI/UX issues
- `question` - Questions/clarifications
- `change` - Feature requests/changes

### feedback.status

- `new` - Not yet addressed
- `in_progress` - Work in progress (future)
- `fixed` - Resolved successfully
- `wont_fix` - Decided not to address

### feedback.priority

- `high` - Urgent/blocking
- `medium` - Standard priority
- `low` - Nice to have

### doc_type (UPPERCASE)

- `ADR` - Architecture Decision Records
- `API` - API documentation
- `ARCHITECTURE` - System architecture
- `ARCHIVE` - Archived content
- `CLAUDE_CONFIG` - Configuration files
- `COMPLETION_REPORT` - Session reports
- `GUIDE` - How-to guides
- `MIGRATION` - Migration guides
- `OTHER` - Miscellaneous
- `README` - Project READMEs
- `REFERENCE` - Reference docs
- `SESSION_NOTE` - Session notes
- `SOP` - Standard Operating Procedures
- `SPEC` - Specifications
- `TEST_DOC` - Test documentation
- `TROUBLESHOOTING` - Troubleshooting guides

### documents.status

- `ACTIVE` - Currently valid
- `ARCHIVED` - Archived, not current

---

## Error Messages & Troubleshooting

### "Project not found"

**Cause**: Invalid project_id
**Solution**: Query projects first
```sql
SELECT project_id, project_name FROM claude.projects;
```

### "Invalid feedback_type"

**Cause**: Typo or wrong value
**Solution**: Use exactly: bug, design, question, or change (lowercase)

### "Description too short"

**Cause**: Description < 10 characters
**Solution**: Provide detailed description (50+ for bugs)

### "Feedback already resolved"

**Cause**: Attempting to resolve already-resolved feedback
**Solution**: Create new feedback if issue reopened, or add comment to existing

### "Invalid doc_type"

**Cause**: Typo or wrong case
**Solution**: Use uppercase values from list above

### "Link already exists"

**Cause**: Document already linked to this project
**Solution**: Check existing links first
```sql
SELECT * FROM claude.document_projects WHERE doc_id = 'your-uuid'::uuid;
```

### "Core documents must have a core_reason"

**Cause**: is_core=true but core_reason is NULL or too short
**Solution**: Provide detailed core_reason (min 10 characters)

---

## Best Practices

### Feedback Management

1. **Bug Reports**:
   - Include detailed reproduction steps
   - Attach screenshots when possible
   - Set priority based on severity/impact
   - Link to related feedback if duplicate

2. **Design Feedback**:
   - Include mockups or sketches
   - Reference design system guidelines
   - Explain user impact

3. **Questions**:
   - Provide context for the question
   - Tag relevant people in comments
   - Close with answer in resolution notes

4. **Changes**:
   - Explain business value
   - Consider effort vs. benefit
   - Link to related requirements

### Documentation Management

1. **Versioning**:
   - Use semantic versioning (1.0, 1.1, 2.0)
   - Increment version on significant changes
   - Archive old versions, don't delete

2. **Core Documentation**:
   - Mark truly essential docs as core
   - Provide clear core_reason
   - Review core status quarterly
   - Typical core docs: CLAUDE.md, main README, architecture

3. **Tags**:
   - Use consistent, lowercase tags
   - Include technology tags (e.g., 'postgresql', 'python')
   - Include domain tags (e.g., 'authentication', 'billing')
   - Include audience tags (e.g., 'developer', 'user')

4. **File Hashes**:
   - Always calculate and store file_hash
   - Use for detecting document changes
   - Update hash when file changes

5. **Project Links**:
   - Link to all relevant projects
   - Set is_primary for main project
   - Program-level docs: link to all program projects

---

## Python Helper Functions

### Calculate File Hash

```python
import hashlib

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of file."""
    with open(file_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# Usage
file_hash = calculate_file_hash('/path/to/document.md')
```

### Create Feedback (Python)

```python
import psycopg2
import uuid
from typing import List, Optional

def create_feedback(
    conn,
    project_id: uuid.UUID,
    feedback_type: str,
    description: str,
    priority: str = 'medium',
    screenshot_paths: Optional[List[str]] = None
) -> uuid.UUID:
    """Create feedback using PostgreSQL function."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT claude.create_feedback(%s, %s, %s, %s, %s, %s)",
            (
                project_id,
                feedback_type,
                description,
                priority,
                None,  # assigned_to
                screenshot_paths or []
            )
        )
        feedback_id = cur.fetchone()[0]
        conn.commit()
        return feedback_id

# Usage
feedback_id = create_feedback(
    conn=db_conn,
    project_id=uuid.UUID('a1b2c3d4-...'),
    feedback_type='bug',
    description='Login button not working on mobile Safari...',
    priority='high',
    screenshot_paths=['/screenshots/bug-001.png']
)
```

### Register Document (Python)

```python
def register_document(
    conn,
    doc_type: str,
    doc_title: str,
    file_path: str,
    project_ids: Optional[List[uuid.UUID]] = None,
    version: Optional[str] = None,
    is_core: bool = False,
    core_reason: Optional[str] = None,
    generated_by_agent: str = 'script'
) -> uuid.UUID:
    """Register document using PostgreSQL function."""
    # Calculate file hash
    file_hash = calculate_file_hash(file_path)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT claude.register_document(
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """,
            (
                doc_type,
                doc_title,
                file_path,
                file_hash,
                project_ids or [],
                version,
                [],  # tags
                is_core,
                core_reason,
                generated_by_agent
            )
        )
        doc_id = cur.fetchone()[0]
        conn.commit()
        return doc_id

# Usage
doc_id = register_document(
    conn=db_conn,
    doc_type='ARCHITECTURE',
    doc_title='Multi-Agent System Architecture',
    file_path='/docs/architecture.md',
    project_ids=[uuid.UUID('a1b2c3d4-...')],
    version='2.0',
    is_core=True,
    core_reason='Core architectural documentation',
    generated_by_agent='claude-code-unified'
)
```

---

## Slash Command Integration

### Example: /feedback-create Command

```python
# In .claude/commands/feedback-create.md or similar

# Command: /feedback-create
# Description: Create new feedback item interactively

You are creating a new feedback item.

Ask the user for:
1. Project name (or auto-detect from current working directory)
2. Feedback type (bug, design, question, change)
3. Description (detailed)
4. Priority (high, medium, low)
5. Screenshot paths (optional)

Then execute:
```sql
SELECT claude.create_feedback(
  p_project_id := (SELECT project_id FROM claude.projects WHERE project_name = '[PROJECT]' LIMIT 1),
  p_feedback_type := '[TYPE]',
  p_description := '[DESCRIPTION]',
  p_priority := '[PRIORITY]',
  p_screenshot_paths := [ARRAY or NULL]
);
```

Return the feedback_id to the user.
```

---

## Changelog

### Version 1.0 (2025-12-04)
- Initial documentation
- Created 5 core workflow tools
- Added 3 utility views
- Documented validation rules

### Planned for Version 1.1
- Add update_feedback_status (to support in_progress)
- Add archive_document function
- Add search_feedback function with filters
- Add feedback relationship support (duplicates, blocks)

---

**Document Type**: Quick Reference Guide
**Related Documents**:
- DATA_GATEWAY_DOMAIN_ANALYSIS.md (full analysis)
- DATA_GATEWAY_WORKFLOW_TOOLS_SQL.md (SQL implementation)
**Last Updated**: 2025-12-04
**Owner**: Claude Code Infrastructure Team
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/DATA_GATEWAY_QUICK_REFERENCE.md
