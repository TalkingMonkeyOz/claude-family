# Core Documentation and Process System - Implementation Plan

**Status**: READY FOR IMPLEMENTATION  
**Created**: 2025-12-03  
**Project**: claude-family  

---

## Executive Summary

This plan addresses the fragmented documentation and process management in Claude Family infrastructure. The current state has 1,535 documents with 95% orphaned (no project linkage), inconsistent classification (74% marked as "OTHER"), and no clear rules for when to use knowledge vs documents vs tasks.

**Goals:**
1. Link documents to projects (many-to-many)
2. Define clear SOPs for knowledge/documents/tasks usage
3. Automate project scaffolding
4. Document build_tasks lifecycle (as-is)
5. Improve document scanner and scheduling

---

## Phase 1: Database Schema Enhancements

### 1.1 Document-Project Junction Table

Create a many-to-many relationship between documents and projects.

```sql
-- Junction table for document-project relationships
CREATE TABLE claude.document_projects (
    document_project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES claude.documents(doc_id) ON DELETE CASCADE,
    project_id UUID NOT NULL REFERENCES claude.projects(project_id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT false,  -- Is this the primary project for the doc?
    relevance_score INTEGER DEFAULT 100,  -- 1-100, how relevant to this project
    linked_at TIMESTAMP DEFAULT NOW(),
    linked_by VARCHAR(100),  -- 'scanner', 'manual', 'auto'
    notes TEXT,
    UNIQUE(doc_id, project_id)
);

-- Indexes for efficient querying
CREATE INDEX idx_doc_projects_doc_id ON claude.document_projects(doc_id);
CREATE INDEX idx_doc_projects_project_id ON claude.document_projects(project_id);
CREATE INDEX idx_doc_projects_primary ON claude.document_projects(is_primary) WHERE is_primary = true;
```

### 1.2 Core Document Flag

Add ability to mark documents as "core" (apply to all projects).

```sql
-- Add core document flag to documents table
ALTER TABLE claude.documents 
ADD COLUMN is_core BOOLEAN DEFAULT false,
ADD COLUMN core_reason TEXT;  -- Why is this a core doc?

-- Index for core documents
CREATE INDEX idx_documents_core ON claude.documents(is_core) WHERE is_core = true;

-- Mark known core documents
UPDATE claude.documents 
SET is_core = true, core_reason = 'Global Claude instructions'
WHERE doc_type = 'CLAUDE_CONFIG' AND file_path LIKE '%\.claude\CLAUDE.md';

UPDATE claude.documents 
SET is_core = true, core_reason = 'Session workflow command'
WHERE file_path LIKE '%session-start.md' OR file_path LIKE '%session-end.md';
```

### 1.3 Document Status Lifecycle

Standardize document statuses:

```sql
-- Add status check constraint (optional - soft enforcement)
-- Note: Don't add hard constraint if existing data has other values
-- Instead, use this as the official list:
-- ACTIVE, DRAFT, REVIEW, DEPRECATED, ARCHIVED, DELETED

-- Add last_verified tracking (if not exists)
ALTER TABLE claude.documents
ADD COLUMN IF NOT EXISTS last_verified_at TIMESTAMP,
ADD COLUMN IF NOT EXISTS verified_by VARCHAR(100);
```

---

## Phase 2: Decision Framework SOPs

### 2.1 SOP-001: Knowledge vs Documents vs Tasks

**File**: `C:\Projects\claude-family\docs\sops\SOP-001-KNOWLEDGE-DOCS-TASKS.md`

**Content Outline:**

```markdown
# SOP-001: Knowledge vs Documents vs Tasks Decision Framework

## When to Use KNOWLEDGE Table

Use `claude.knowledge` when:
- Recording a reusable pattern or best practice
- Documenting a bug fix that might recur
- Capturing a "gotcha" or non-obvious behavior
- Storing API reference or troubleshooting steps
- Information applies across multiple projects

Knowledge Types (8 standardized):
- api-reference
- architecture
- best-practice
- bug-fix
- gotcha
- pattern
- reference
- troubleshooting

## When to Use DOCUMENTS Table

Use `claude.documents` when:
- Indexing a file that EXISTS on the filesystem
- The file is a spec, guide, README, or architecture doc
- Content is project-specific or version-controlled
- Document needs status tracking (ACTIVE, DEPRECATED, etc.)

Document Categories (14 defined):
- adr, api, architecture, claude_config, completion_report
- guide, migration, other, readme, reference
- session_note, sop, spec, troubleshooting

## When to Use BUILD_TASKS Table

Use `claude.build_tasks` when:
- Task is tied to a specific component or feature
- Task is technical implementation work
- MCW (Mission Control Web) will track/display it
- Task follows: todo -> completed lifecycle

Use `claude.pm_tasks` when:
- Task is phase/work-package based
- Task has dates (start, due, completion)
- Task is project management (not technical)

## Decision Flowchart

1. Is it a reusable learning? -> KNOWLEDGE
2. Is it a file on disk? -> DOCUMENTS  
3. Is it development work? -> BUILD_TASKS
4. Is it PM/planning work? -> PM_TASKS
```

### 2.2 SOP-002: Build Task Lifecycle

**File**: `C:\Projects\claude-family\docs\sops\SOP-002-BUILD-TASK-LIFECYCLE.md`

**Content Outline:**

```markdown
# SOP-002: Build Task Lifecycle

## Status Values
- `todo` - Task created, not started
- `completed` - Task finished

## Task Types
- `code` - Implementation task
- `test` - Testing task

## Priority Scale
- 1-4: Critical (do first)
- 5: Normal priority
- 6-7: Low priority (nice to have)
- 8-10: Backlog

## Creating Build Tasks

1. Task MUST be linked to either:
   - A component (component_id)
   - A feature (feature_id)
   - Both (preferred)

2. Required fields:
   - task_name: Clear, action-oriented
   - task_type: 'code' or 'test'
   - status: Start as 'todo'
   - priority: 1-10

3. Optional tracking:
   - estimated_hours: Pre-work estimate
   - actual_hours: Post-completion actual
   - blocked_reason: If stuck
   - blocked_by_task_id: Dependency

## Completing Tasks

1. Set status = 'completed'
2. Set completed_at = NOW()
3. Optionally record actual_hours
4. MCW will update related component/feature progress
```

### 2.3 SOP-003: Document Classification

**File**: `C:\Projects\claude-family\docs\sops\SOP-003-DOCUMENT-CLASSIFICATION.md`

**Content Outline:**

```markdown
# SOP-003: Document Classification Guide

## Document Type Detection

| Type | Patterns in Filename | Example |
|------|---------------------|---------|
| ADR | adr-, adr_, /adr/ | adr-001-use-postgres.md |
| ARCHITECTURE | architecture, arch_, system_design | ARCHITECTURE.md |
| CLAUDE_CONFIG | claude.md | CLAUDE.md |
| README | readme | README.md |
| SOP | sop, procedure, workflow | SOP-001-KNOWLEDGE.md |
| GUIDE | guide, how-to, tutorial | QUICK_START_GUIDE.md |
| API | api, swagger, openapi | API_REFERENCE.md |
| SPEC | spec, requirement, prd | REQUIREMENTS_SPEC.md |
| SESSION_NOTE | session_note, completion_report | SESSION_2025-12-03.md |
| MIGRATION | migration, upgrade | MIGRATION_v2.md |
| TROUBLESHOOTING | troubleshoot, debug, fix | TROUBLESHOOTING.md |

## Core Documents

These documents are marked is_core=true:
- ~/.claude/CLAUDE.md (global user instructions)
- Project CLAUDE.md files
- Session workflow commands (session-start.md, session-end.md)
- Architecture decision records affecting all projects

## Project Linking Rules

1. Scanner detects project from file path (C:\Projects\{project-name}\...)
2. Shared docs in C:\claude\shared\ are marked is_core=true
3. Documents can belong to multiple projects via document_projects table
```

---

## Phase 3: Project Scaffolding System

### 3.1 Template Repository Structure

**Location**: `C:\Projects\claude-family\templates\`

```
templates/
├── CLAUDE.md                    # Already exists
├── README.template.md           # New
├── .docs-manifest.template.json # New
├── .gitignore.template          # New
├── project-types/
│   ├── infrastructure/
│   │   └── README.md
│   ├── web-app/
│   │   ├── src/
│   │   ├── tests/
│   │   └── package.json.template
│   ├── python-tool/
│   │   ├── src/
│   │   ├── tests/
│   │   └── pyproject.toml.template
│   └── csharp-desktop/
│       ├── src/
│       ├── tests/
│       └── .csproj.template
└── docs/
    ├── PROJECT_BRIEF.template.md
    ├── ARCHITECTURE.template.md
    └── EXECUTION_PLAN.template.md
```

### 3.2 create-project.py Script

**File**: `C:\Projects\claude-family\scripts\create_project.py`

**Specification:**

```python
"""
create_project.py - One-command project scaffolding

Usage:
    python scripts/create_project.py <name> <type> [--no-git] [--no-db]

Arguments:
    name: Project name (will become folder name)
    type: infrastructure | web-app | python-tool | csharp-desktop

Options:
    --no-git: Skip git initialization
    --no-db: Skip database registration

Actions:
    1. Create project folder at C:\Projects\{name}
    2. Copy type-specific template structure
    3. Render CLAUDE.md with project name
    4. Initialize .docs-manifest.json
    5. Initialize git repository
    6. Register project in claude.projects table
    7. Add to workspaces.json
    8. Run init_project_docs.py for manifest setup
    9. Print next steps

Example:
    python scripts/create_project.py nimbus-v2 python-tool
"""
```

**Key Functions:**
- `create_folder_structure(name, type)` - Copy templates
- `render_templates(name, type)` - Replace placeholders
- `register_in_database(name, type)` - Insert into claude.projects
- `add_to_workspaces(name, path)` - Update workspaces.json
- `initialize_git(path)` - git init + initial commit
- `run_post_setup(path)` - Call init_project_docs.py

---

## Phase 4: Document Scanner Improvements

### 4.1 Enhanced scan_documents.py

**Changes to existing file**: `C:\Projects\claude-family\scripts\scan_documents.py`

**New Features:**

1. **Auto-detect project from path:**
```python
def detect_project_from_path(file_path: Path) -> str:
    """Extract project name from file path."""
    parts = file_path.parts
    if 'Projects' in parts:
        idx = parts.index('Projects')
        if len(parts) > idx + 1:
            return parts[idx + 1]
    return None
```

2. **Core document detection:**
```python
CORE_DOC_PATTERNS = [
    r'\.claude[/\\]CLAUDE\.md$',
    r'session-start\.md$',
    r'session-end\.md$',
    r'[/\\]shared[/\\]docs[/\\]',
]

def is_core_document(file_path: str) -> bool:
    """Check if document is a core/universal document."""
    for pattern in CORE_DOC_PATTERNS:
        if re.search(pattern, file_path, re.IGNORECASE):
            return True
    return False
```

3. **Improved type detection:**
```python
# Add more patterns to reduce "OTHER" classification
DOC_TYPE_PATTERNS = {
    # ... existing patterns ...
    'CHANGELOG': ['changelog', 'history', 'release_notes'],
    'CONFIG': ['config', 'settings', '.json', '.yaml', '.toml'],
    'TEST_DOC': ['test_', '_test', 'testing'],
    'DESIGN': ['design', 'mockup', 'wireframe', 'prototype'],
}
```

4. **Project linking:**
```python
def link_document_to_project(conn, doc_id: str, project_id: str, linked_by: str = 'scanner'):
    """Create document-project relationship."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claude.document_projects (doc_id, project_id, linked_by)
        VALUES (%s, %s, %s)
        ON CONFLICT (doc_id, project_id) DO NOTHING
    """, (doc_id, project_id, linked_by))
    cur.close()
```

### 4.2 New: link_checker.py

**File**: `C:\Projects\claude-family\scripts\link_checker.py`

**Purpose**: Verify file_path references still exist on disk.

```python
"""
link_checker.py - Verify document file paths exist

Checks:
1. All documents with file_path - does the file exist?
2. All scheduled_jobs with command paths - do scripts exist?
3. All procedure_registry with file_path - do files exist?

Output:
- List of broken links
- Optionally mark documents as DELETED status
"""
```

### 4.3 New: orphan_report.py

**File**: `C:\Projects\claude-family\scripts\orphan_report.py`

**Purpose**: Report documents without project linkage.

```python
"""
orphan_report.py - Report orphaned documents

Reports:
1. Documents with no project_id and not is_core
2. Documents with no document_projects entries
3. Suggestions for which project to link to (based on path)

Output:
- CSV report of orphans
- SQL to auto-link obvious cases
"""
```

---

## Phase 5: Scheduled Jobs Configuration

### 5.1 Update Existing Jobs

```sql
-- Update Document Scanner job with new command
UPDATE claude.scheduled_jobs 
SET command = 'python C:\\Projects\\claude-family\\scripts\\scan_documents.py --link-projects',
    job_description = 'Scan and index documents, auto-link to projects'
WHERE job_name = 'Document Scanner';
```

### 5.2 Add New Jobs

```sql
-- Link Checker (weekly)
INSERT INTO claude.scheduled_jobs (
    job_id, job_name, job_description, job_type, schedule, 
    command, working_directory, is_active, timeout_seconds
) VALUES (
    gen_random_uuid(),
    'Document Link Checker',
    'Verify all file_path references exist on disk',
    'audit',
    'Weekly (Monday @ 6am)',
    'python C:\\Projects\\claude-family\\scripts\\link_checker.py',
    'C:\\Projects\\claude-family',
    true,
    300
);

-- Orphan Report (weekly)
INSERT INTO claude.scheduled_jobs (
    job_id, job_name, job_description, job_type, schedule,
    command, working_directory, is_active, timeout_seconds
) VALUES (
    gen_random_uuid(),
    'Orphan Document Report',
    'Report documents without project linkage',
    'audit',
    'Weekly (Monday @ 6:30am)',
    'python C:\\Projects\\claude-family\\scripts\\orphan_report.py --output logs/orphan_report.csv',
    'C:\\Projects\\claude-family',
    true,
    300
);
```

---

## Phase 6: Procedure Registry Updates

### 6.1 Register New SOPs

```sql
-- SOP-001: Knowledge vs Documents vs Tasks
INSERT INTO claude_family.procedure_registry (
    procedure_name, procedure_type, short_description,
    location_type, file_path, applies_to_projects, mandatory, frequency
) VALUES (
    'Knowledge-Documents-Tasks Decision',
    'documentation',
    'Decision framework: when to use knowledge table vs documents vs tasks',
    'file',
    'C:\Projects\claude-family\docs\sops\SOP-001-KNOWLEDGE-DOCS-TASKS.md',
    ARRAY['all'],
    true,
    'reference'
);

-- SOP-002: Build Task Lifecycle
INSERT INTO claude_family.procedure_registry (
    procedure_name, procedure_type, short_description,
    location_type, file_path, applies_to_projects, mandatory, frequency
) VALUES (
    'Build Task Lifecycle',
    'documentation',
    'Lifecycle and rules for build_tasks: todo -> completed',
    'file',
    'C:\Projects\claude-family\docs\sops\SOP-002-BUILD-TASK-LIFECYCLE.md',
    ARRAY['all', 'claude-mission-control'],
    false,
    'reference'
);

-- SOP-003: Document Classification
INSERT INTO claude_family.procedure_registry (
    procedure_name, procedure_type, short_description,
    location_type, file_path, applies_to_projects, mandatory, frequency
) VALUES (
    'Document Classification Guide',
    'documentation',
    'How documents are classified by type and category',
    'file',
    'C:\Projects\claude-family\docs\sops\SOP-003-DOCUMENT-CLASSIFICATION.md',
    ARRAY['all'],
    false,
    'reference'
);

-- Project Scaffolding
INSERT INTO claude_family.procedure_registry (
    procedure_name, procedure_type, short_description,
    location_type, file_path, applies_to_projects, mandatory, frequency
) VALUES (
    'Project Scaffolding',
    'infrastructure-maintenance',
    'One-command project creation: python scripts/create_project.py <name> <type>',
    'script',
    'C:\Projects\claude-family\scripts\create_project.py',
    ARRAY['claude-family'],
    false,
    'on-demand'
);
```

---

## Implementation Sequence

### Week 1: Database and SOPs
1. Run Phase 1 SQL (schema changes)
2. Create SOP-001, SOP-002, SOP-003 markdown files
3. Register SOPs in procedure_registry
4. Test junction table with manual inserts

### Week 2: Scanner and Scripts
1. Update scan_documents.py with new features
2. Create link_checker.py
3. Create orphan_report.py
4. Test all scripts in dry-run mode

### Week 3: Scaffolding and Jobs
1. Create template repository structure
2. Create create_project.py script
3. Add new scheduled jobs
4. Test project creation end-to-end

### Week 4: Migration and Cleanup
1. Run scanner to link existing documents
2. Review orphan report
3. Manually link remaining documents
4. Update MCW to show linked projects (send to MCW Claude)

---

## Files to Create/Modify Summary

### New Files
| File | Purpose |
|------|---------|
| `docs/sops/SOP-001-KNOWLEDGE-DOCS-TASKS.md` | Decision framework |
| `docs/sops/SOP-002-BUILD-TASK-LIFECYCLE.md` | Build task rules |
| `docs/sops/SOP-003-DOCUMENT-CLASSIFICATION.md` | Classification guide |
| `scripts/create_project.py` | Project scaffolding |
| `scripts/link_checker.py` | Verify file references |
| `scripts/orphan_report.py` | Report unlinked docs |
| `templates/README.template.md` | README template |
| `templates/.docs-manifest.template.json` | Manifest template |
| `templates/project-types/...` | Type-specific templates |

### Modified Files
| File | Changes |
|------|---------|
| `scripts/scan_documents.py` | Add project linking, core detection, improved classification |

### Database Changes
| Object | Type | Action |
|--------|------|--------|
| `claude.document_projects` | Table | CREATE |
| `claude.documents.is_core` | Column | ADD |
| `claude.documents.core_reason` | Column | ADD |
| `claude.scheduled_jobs` | Rows | INSERT (2 new jobs) |
| `claude_family.procedure_registry` | Rows | INSERT (4 new SOPs) |

---

## Success Criteria

1. **Document Linking**: Less than 10% orphaned documents (down from 95%)
2. **Classification**: Less than 20% "OTHER" type (down from 74%)
3. **Project Setup**: New project in under 5 minutes via single command
4. **SOPs**: All decision rules documented and queryable
5. **Scheduled Jobs**: Scanner runs daily, linker/orphan weekly

---

## Notes for MCW (Mission Control Web)

After implementing this plan, send message to MCW Claude instance:

```
New document_projects junction table available. 
- Query: SELECT dp.*, d.doc_title, p.project_name 
         FROM claude.document_projects dp 
         JOIN claude.documents d ON dp.doc_id = d.doc_id 
         JOIN claude.projects p ON dp.project_id = p.project_id
- UI: Show document's linked projects in Documents view
- UI: Filter documents by project in sidebar
- Core docs (is_core=true) should show in all projects
```

---

## Critical Files for Implementation

1. **`C:\Projects\claude-family\scripts\scan_documents.py`** - Core scanner to enhance with project linking and improved classification
2. **`C:\Projects\claude-family\scripts\init_project_docs.py`** - Existing scaffolding to integrate with new create_project.py
3. **`C:\Projects\claude-family\templates\CLAUDE.md`** - Template to expand with additional project types
4. **`C:\Projects\claude-family\.docs-manifest.json`** - Reference for manifest structure
5. **`C:\Projects\claude-family\scripts\sync_slash_commands.py`** - Pattern to follow for distributing core files
