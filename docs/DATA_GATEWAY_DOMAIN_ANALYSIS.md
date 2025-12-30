# Data Gateway Domain Analysis: Feedback & Documentation

**Analysis Date**: 2025-12-04
**Schema**: `claude` (base tables) + `claude_pm` (views/interface)
**Purpose**: Design workflow tools for centralized feedback and document management

---

## Executive Summary

The Feedback and Documentation domains use a **dual-layer architecture**:
- **Base Layer**: `claude.feedback`, `claude.documents` (actual tables)
- **Interface Layer**: `claude_pm.project_feedback` (view pointing to claude.feedback)

This analysis documents the schema structure, valid values, business rules, and workflow transitions to inform "Data Gateway" tool design.

---

## 1. FEEDBACK DOMAIN

### 1.1 Table: `claude.feedback`

**Primary Key**: `feedback_id` (UUID)

#### Schema Structure

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `feedback_id` | uuid | NO | Primary key |
| `project_id` | uuid | YES | Foreign key to projects table |
| `feedback_type` | varchar | YES | Type of feedback (see valid values) |
| `description` | text | YES | Detailed description of the issue/request |
| `screenshot_path` | text | YES | DEPRECATED: Use feedback_screenshots table |
| `status` | varchar | YES | Current status (see workflow) |
| `priority` | varchar | YES | Priority level |
| `assigned_to` | varchar | YES | Person/agent assigned |
| `notes` | text | YES | Resolution notes or comments |
| `created_at` | timestamp | YES | Creation timestamp |
| `updated_at` | timestamp | YES | Last update timestamp |
| `resolved_at` | timestamp | YES | Resolution timestamp |

#### Valid Values

**feedback_type** (4 types):
- `bug` - Software defects requiring fixes
- `design` - UI/UX design issues or improvements
- `question` - Questions requiring clarification
- `change` - Feature changes or enhancements

**status** (3 states):
- `new` - Newly created, not yet addressed
- `fixed` - Issue resolved/implemented
- `wont_fix` - Decided not to address

**priority** (2 levels observed):
- `high` - Urgent, blocking issues
- `medium` - Standard priority (default)
- `low` - (not observed in data, but should be supported)

#### Required Fields (Business Rules)

**Minimum required for creation**:
1. `feedback_id` - MUST be provided (or auto-generated)
2. `project_id` - SHOULD be provided (orphaned feedback is problematic)
3. `feedback_type` - REQUIRED (one of: bug, design, question, change)
4. `description` - REQUIRED (min length: 10 characters for bugs)
5. `status` - Defaults to 'new' if not provided
6. `priority` - Defaults to 'medium' if not provided
7. `created_at` - Auto-set to CURRENT_TIMESTAMP

**Quality rules for bugs**:
- `description` MUST be >= 50 characters for `feedback_type = 'bug'`
- Bug reports SHOULD include steps to reproduce
- Bug reports with screenshots are preferred

#### Workflow Transitions

```
new → fixed
new → wont_fix

(No observed transitions: new → in_progress → fixed)
(Current schema does NOT have 'in_progress' status)
```

**Transition rules**:
1. **new → fixed**:
   - `resolved_at` MUST be set
   - `notes` SHOULD be populated with resolution details
   - `updated_at` MUST be updated

2. **new → wont_fix**:
   - `resolved_at` MUST be set
   - `notes` MUST be populated with justification
   - `updated_at` MUST be updated

**Data Quality Issues Found**:
- Some resolved feedback missing `notes` (1 of 20 sampled)
- Some feedback missing `created_at` timestamps (test data)
- No enforcement of minimum description length

#### Relationships

**Foreign Keys**:
- `project_id` → `claude.projects.project_id` (NOT NULL constraint recommended but not enforced)

**Child Tables**:
- `claude.feedback_comments` (1-to-many)
- `claude.feedback_screenshots` (1-to-many)

---

### 1.2 Table: `claude.feedback_comments`

**Primary Key**: `id` (UUID)

#### Schema Structure

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | uuid | NO | Primary key |
| `feedback_id` | uuid | YES | Foreign key to feedback |
| `author` | varchar | YES | Comment author (identity name) |
| `message` | text | YES | Comment content |
| `created_at` | timestamp | YES | Comment timestamp |

#### Required Fields

1. `feedback_id` - REQUIRED
2. `author` - REQUIRED
3. `message` - REQUIRED (min length: 5 characters)
4. `created_at` - Auto-set to CURRENT_TIMESTAMP

**Note**: The `claude_pm.project_feedback_comments` view enforces NOT NULL on `feedback_id`, `author`, and `content` (remapped from `message`).

#### Usage Patterns

- **Low usage**: Only 1 comment in current data
- **Primary use case**: Discussions, clarifications, updates
- **Should be used instead of**: Updating feedback.notes repeatedly

---

### 1.3 Table: `claude.feedback_screenshots`

**Primary Key**: `id` (UUID)

#### Schema Structure

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `id` | uuid | NO | Primary key |
| `feedback_id` | uuid | YES | Foreign key to feedback |
| `file_path` | text | YES | Absolute path to screenshot file |
| `caption` | text | YES | Optional description of screenshot |
| `uploaded_at` | timestamp | YES | Upload timestamp |

#### Required Fields

1. `feedback_id` - REQUIRED
2. `file_path` - REQUIRED (must be valid, accessible path)
3. `uploaded_at` - Auto-set to CURRENT_TIMESTAMP

#### Usage Patterns

- **Moderate usage**: 11 screenshots for 5 unique feedback items
- **Multiple screenshots per feedback**: Supported (1-to-many)
- **Missing captions**: 4 of 11 screenshots have no caption (36%)

**Recommendations**:
- Validate file_path exists and is readable
- Encourage (but don't require) captions for accessibility
- Consider file size limits

---

## 2. DOCUMENTATION DOMAIN

### 2.1 Table: `claude.documents`

**Primary Key**: `doc_id` (UUID, auto-generated)

#### Schema Structure

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `doc_id` | uuid | NO | gen_random_uuid() | Primary key |
| `doc_type` | varchar | YES | NULL | Document type (see valid values) |
| `doc_title` | varchar | YES | NULL | Human-readable title |
| `project_id` | uuid | YES | NULL | DEPRECATED: Use document_projects |
| `file_path` | text | YES | NULL | Absolute path to document |
| `file_hash` | varchar | YES | NULL | SHA-256 hash for change detection |
| `version` | varchar | YES | NULL | Version string (e.g., "1.0", "2.3") |
| `status` | varchar | YES | NULL | Document lifecycle status |
| `category` | varchar | YES | NULL | Categorization (lowercase doc_type) |
| `tags` | text[] | YES | NULL | Searchable tags |
| `generated_by_agent` | varchar | YES | NULL | Agent that created document |
| `is_core` | boolean | YES | false | Core documentation flag |
| `core_reason` | text | YES | NULL | Why this is core (if is_core=true) |
| `is_archived` | boolean | YES | false | Archived flag |
| `archived_at` | timestamp | YES | NULL | Archive timestamp |
| `created_at` | timestamp | YES | NULL | Creation timestamp |
| `updated_at` | timestamp | YES | NULL | Last update timestamp |
| `last_verified_at` | timestamp | YES | NULL | Last verification timestamp |

#### Valid Values

**doc_type** (16 types - UPPERCASE):
- `ADR` - Architecture Decision Records
- `API` - API documentation
- `ARCHITECTURE` - System architecture docs
- `ARCHIVE` - Archived documents (type, not status)
- `CLAUDE_CONFIG` - Claude configuration files
- `COMPLETION_REPORT` - Session completion reports
- `GUIDE` - How-to guides and tutorials
- `MIGRATION` - Migration guides
- `OTHER` - Miscellaneous documents
- `README` - Project README files
- `REFERENCE` - Reference documentation
- `SESSION_NOTE` - Session work notes
- `SOP` - Standard Operating Procedures
- `SPEC` - Specifications
- `TEST_DOC` - Test documentation
- `TROUBLESHOOTING` - Troubleshooting guides

**status** (2 states):
- `ACTIVE` - Currently active and valid
- `ARCHIVED` - Archived, not current

**category** (16 categories - lowercase, mirrors doc_type):
- Same values as doc_type, but lowercase
- **Note**: Appears redundant; consider deprecating

**is_core** (boolean):
- `true` - Core documentation (112 of 1734 documents = 6.5%)
- `false` - Standard documentation

**Core documents by type**:
- CLAUDE_CONFIG: 12 core (71% of CLAUDE_CONFIG docs)
- REFERENCE: 37 core (9% of REFERENCE docs)
- SESSION_NOTE: 35 core (15% of SESSION_NOTE docs)
- COMPLETION_REPORT: 5 core (2% of COMPLETION_REPORT docs)
- OTHER: 8 core (25% of OTHER docs)

**is_archived** (boolean):
- `true` - Archived (379 of 1734 documents = 21.8%)
- `false` - Active

#### Required Fields

**Minimum required for creation**:
1. `doc_type` - REQUIRED (one of 16 valid types)
2. `doc_title` - REQUIRED (min length: 5 characters)
3. `file_path` - REQUIRED (must exist and be readable)
4. `file_hash` - STRONGLY RECOMMENDED (for change detection)
5. `status` - Defaults to 'ACTIVE' if not provided
6. `created_at` - Auto-set to CURRENT_TIMESTAMP

**Optional but recommended**:
- `version` - Version number (use semantic versioning)
- `tags` - For searchability
- `generated_by_agent` - Audit trail
- `category` - Auto-derive from doc_type (lowercase)

**Core documentation requirements**:
- If `is_core = true`, then `core_reason` MUST be provided
- Core documents SHOULD NOT be archived without review

#### Workflow Transitions

```
(created) → ACTIVE
ACTIVE → ARCHIVED (via archive process)
ARCHIVED → ACTIVE (via restore process, rare)
```

**Archive workflow**:
1. Set `is_archived = true`
2. Set `archived_at = CURRENT_TIMESTAMP`
3. Set `status = 'ARCHIVED'`
4. Update `updated_at = CURRENT_TIMESTAMP`
5. Consider: Remove from document_projects links? (No, keep history)

**Data Quality Rules**:
- Documents with `status = 'ARCHIVED'` MUST have `is_archived = true`
- Documents with `is_archived = true` MUST have `archived_at` timestamp
- ALL documents MUST have `file_path` (0 missing in current data)
- File at `file_path` SHOULD exist (verify on registration)

#### Relationships

**Foreign Keys**:
- `project_id` - DEPRECATED: Use `document_projects` junction table instead
  - **Data shows**: 293 documents still have direct project_id
  - **Recommendation**: Migrate to document_projects, then drop column

**Child Tables**:
- `claude.document_projects` (many-to-many via junction table)

---

### 2.2 Table: `claude.document_projects`

**Primary Key**: `document_project_id` (UUID, auto-generated)
**Unique Constraint**: `(doc_id, project_id)`

#### Schema Structure

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `document_project_id` | uuid | NO | gen_random_uuid() | Primary key |
| `doc_id` | uuid | NO | - | Foreign key to documents |
| `project_id` | uuid | NO | - | Foreign key to projects |
| `is_primary` | boolean | YES | false | Primary project flag |
| `linked_by` | varchar | YES | NULL | Identity that created link |
| `linked_at` | timestamp | YES | now() | Link creation timestamp |

#### Required Fields

1. `doc_id` - REQUIRED (must exist in documents table)
2. `project_id` - REQUIRED (must exist in projects table)
3. `linked_at` - Auto-set to now()

**Business Rule**: A document can be linked to multiple projects, but only ONE can be `is_primary = true`.

#### Indexes

- Primary key on `document_project_id`
- Unique constraint on `(doc_id, project_id)`
- Index on `doc_id` (for lookups by document)
- Index on `project_id` (for lookups by project)

#### Foreign Keys

- `doc_id` → `claude.documents.doc_id` (ON DELETE CASCADE recommended)
- `project_id` → `claude.projects.project_id` (ON DELETE CASCADE recommended)

#### Usage Patterns

**Current state**: Limited usage, most documents still use documents.project_id directly

**Intended usage**: Many-to-many relationships
- Shared documentation across projects
- Cross-project references
- Program-level documentation

---

## 3. WORKFLOW TOOL SPECIFICATIONS

### 3.1 Tool: `create_feedback`

**Purpose**: Create new feedback item with validation

**Parameters**:
```json
{
  "project_id": "uuid (REQUIRED)",
  "feedback_type": "bug|design|question|change (REQUIRED)",
  "description": "string (REQUIRED, min 10 chars, 50+ for bugs)",
  "priority": "high|medium|low (OPTIONAL, default: medium)",
  "assigned_to": "string (OPTIONAL)",
  "screenshot_paths": "string[] (OPTIONAL)"
}
```

**Returns**: `feedback_id` (UUID)

**Process**:
1. **Validate inputs**:
   - `project_id` exists in projects table
   - `feedback_type` is one of: bug, design, question, change
   - `description` length >= 10 (50+ for bugs)
   - `priority` is one of: high, medium, low

2. **Create feedback record**:
   ```sql
   INSERT INTO claude.feedback (
     feedback_id, project_id, feedback_type, description,
     priority, status, created_at, updated_at
   ) VALUES (
     uuid_generate_v4(), $project_id, $feedback_type, $description,
     COALESCE($priority, 'medium'), 'new', now(), now()
   ) RETURNING feedback_id;
   ```

3. **Handle screenshots** (if provided):
   - For each path in `screenshot_paths`:
     - Validate file exists and is readable
     - Insert into `feedback_screenshots`

4. **Add initial comment** (if workflow includes comments):
   - Author: current identity
   - Message: "Feedback created"

**Quality checks**:
- Warn if bug has no screenshot
- Suggest higher priority if description contains urgent keywords
- Auto-tag with keywords extracted from description

---

### 3.2 Tool: `add_feedback_comment`

**Purpose**: Add comment/update to existing feedback

**Parameters**:
```json
{
  "feedback_id": "uuid (REQUIRED)",
  "author": "string (REQUIRED)",
  "message": "string (REQUIRED, min 5 chars)",
  "attach_screenshot": "string (OPTIONAL, file path)"
}
```

**Returns**: `comment_id` (UUID)

**Process**:
1. **Validate**:
   - `feedback_id` exists
   - `message` length >= 5
   - If screenshot provided, file exists

2. **Insert comment**:
   ```sql
   INSERT INTO claude.feedback_comments (
     id, feedback_id, author, message, created_at
   ) VALUES (
     uuid_generate_v4(), $feedback_id, $author, $message, now()
   ) RETURNING id;
   ```

3. **Update parent feedback**:
   ```sql
   UPDATE claude.feedback
   SET updated_at = now()
   WHERE feedback_id = $feedback_id;
   ```

4. **Handle screenshot** (if provided):
   - Insert into `feedback_screenshots`

**Use cases**:
- Progress updates
- Clarification questions
- Additional details
- Resolution explanations

---

### 3.3 Tool: `resolve_feedback`

**Purpose**: Mark feedback as fixed or won't fix

**Parameters**:
```json
{
  "feedback_id": "uuid (REQUIRED)",
  "resolution": "fixed|wont_fix (REQUIRED)",
  "notes": "string (REQUIRED)",
  "resolved_by": "string (REQUIRED, identity name)"
}
```

**Returns**: Success boolean + updated feedback record

**Process**:
1. **Validate**:
   - `feedback_id` exists
   - Current status is 'new' (can't re-resolve)
   - `notes` length >= 20 characters
   - `resolution` is 'fixed' or 'wont_fix'

2. **Update feedback**:
   ```sql
   UPDATE claude.feedback
   SET
     status = $resolution,
     notes = $notes,
     resolved_at = now(),
     updated_at = now()
   WHERE feedback_id = $feedback_id
     AND status = 'new'
   RETURNING *;
   ```

3. **Add resolution comment**:
   ```sql
   INSERT INTO claude.feedback_comments (
     id, feedback_id, author, message, created_at
   ) VALUES (
     uuid_generate_v4(),
     $feedback_id,
     $resolved_by,
     'Resolved as ' || $resolution || ': ' || $notes,
     now()
   );
   ```

**Business rules**:
- `wont_fix` REQUIRES detailed justification in notes (min 50 chars)
- `fixed` SHOULD reference commit/PR if code change
- Resolution cannot be changed once set (use new feedback for reopening)

**Quality checks**:
- Warn if fixing without assigned_to being set
- Suggest tagging related feedback as duplicates

---

### 3.4 Tool: `register_document`

**Purpose**: Register new document in documentation system

**Parameters**:
```json
{
  "doc_type": "ADR|API|ARCHITECTURE|... (REQUIRED)",
  "doc_title": "string (REQUIRED, min 5 chars)",
  "file_path": "string (REQUIRED, absolute path)",
  "project_ids": "uuid[] (OPTIONAL, for linking)",
  "version": "string (OPTIONAL, e.g., '1.0')",
  "tags": "string[] (OPTIONAL)",
  "is_core": "boolean (OPTIONAL, default: false)",
  "core_reason": "string (REQUIRED if is_core=true)",
  "generated_by_agent": "string (OPTIONAL, identity name)"
}
```

**Returns**: `doc_id` (UUID)

**Process**:
1. **Validate inputs**:
   - `doc_type` is one of 16 valid types (uppercase)
   - `doc_title` length >= 5
   - `file_path` is absolute and file exists
   - If `is_core = true`, then `core_reason` is provided

2. **Calculate file hash**:
   ```python
   import hashlib
   with open(file_path, 'rb') as f:
       file_hash = hashlib.sha256(f.read()).hexdigest()
   ```

3. **Insert document**:
   ```sql
   INSERT INTO claude.documents (
     doc_id, doc_type, doc_title, file_path, file_hash,
     version, status, category, tags, generated_by_agent,
     is_core, core_reason, created_at, updated_at
   ) VALUES (
     uuid_generate_v4(), $doc_type, $doc_title, $file_path, $file_hash,
     $version, 'ACTIVE', LOWER($doc_type), $tags, $generated_by_agent,
     COALESCE($is_core, false), $core_reason, now(), now()
   ) RETURNING doc_id;
   ```

4. **Link to projects** (if project_ids provided):
   - For each project_id:
     - Call `link_document_to_project(doc_id, project_id, is_primary)`
     - First project is primary, rest are secondary

**Quality checks**:
- Warn if file_path contains spaces (potential issues)
- Suggest tags based on doc_type and file content
- Check for duplicate file_path or similar titles

**Auto-detection**:
- Extract version from filename if not provided (e.g., "spec_v2.1.md" → "2.1")
- Extract tags from file content (headers, keywords)
- Detect CLAUDE.md, README.md → auto-mark is_core with reason

---

### 3.5 Tool: `link_document_to_project`

**Purpose**: Create many-to-many link between document and project

**Parameters**:
```json
{
  "doc_id": "uuid (REQUIRED)",
  "project_id": "uuid (REQUIRED)",
  "is_primary": "boolean (OPTIONAL, default: false)",
  "linked_by": "string (OPTIONAL, identity name)"
}
```

**Returns**: `document_project_id` (UUID)

**Process**:
1. **Validate**:
   - `doc_id` exists in documents table
   - `project_id` exists in projects table
   - Link doesn't already exist (unique constraint on doc_id, project_id)
   - If `is_primary = true`, no other primary link exists for this doc_id

2. **Insert link**:
   ```sql
   INSERT INTO claude.document_projects (
     document_project_id, doc_id, project_id, is_primary, linked_by, linked_at
   ) VALUES (
     uuid_generate_v4(), $doc_id, $project_id,
     COALESCE($is_primary, false), $linked_by, now()
   ) RETURNING document_project_id;
   ```

3. **Update primary flags** (if is_primary = true):
   ```sql
   -- Clear other primary flags for this document
   UPDATE claude.document_projects
   SET is_primary = false
   WHERE doc_id = $doc_id
     AND document_project_id != $new_document_project_id;
   ```

**Business rules**:
- A document can have 0 or 1 primary project
- A document can have unlimited secondary projects
- Deleting a project SHOULD cascade delete links (ON DELETE CASCADE)

**Use cases**:
- Link shared architecture docs to multiple projects
- Link program-level docs to all program projects
- Link migration guides to source and target projects

---

## 4. DATA QUALITY OBSERVATIONS

### 4.1 Feedback Domain Issues

1. **Missing timestamps**: Some test feedback has NULL created_at
2. **Missing resolution notes**: 1 of 20 resolved items missing notes
3. **No in_progress status**: Only 'new', 'fixed', 'wont_fix' observed
4. **Low comment usage**: Only 1 comment in entire dataset
5. **Screenshot path redundancy**: Both feedback.screenshot_path and feedback_screenshots table exist

**Recommendations**:
- Add NOT NULL constraints on: project_id, feedback_type, description, created_at
- Add CHECK constraint: description length >= 10 (50 for bugs)
- Add 'in_progress' status for workflow visibility
- Deprecate feedback.screenshot_path column
- Enforce notes on resolution (CHECK constraint)

### 4.2 Documentation Domain Issues

1. **Redundant fields**: `category` mirrors `doc_type` (lowercase)
2. **Deprecated field**: `project_id` column still used (293 documents)
3. **Archive inconsistency**: Some ARCHIVED status docs might not have is_archived=true
4. **Version inconsistency**: Many docs have NULL version

**Recommendations**:
- Migrate documents.project_id → document_projects junction table
- Drop documents.category column (redundant)
- Add CHECK constraint: (status='ARCHIVED') = (is_archived=true)
- Add CHECK constraint: is_archived=true → archived_at NOT NULL
- Add CHECK constraint: is_core=true → core_reason NOT NULL
- Implement version auto-detection from filenames

### 4.3 Cross-Domain Observations

**Shared patterns**:
- Both use UUID primary keys (good)
- Both use status fields (VARCHAR, inconsistent casing)
- Both have created_at/updated_at (audit trail)
- Both support many-to-many project relationships

**Inconsistencies**:
- Feedback: lowercase status values ('new', 'fixed')
- Documents: UPPERCASE status values ('ACTIVE', 'ARCHIVED')
- **Recommendation**: Standardize on lowercase for consistency

---

## 5. FUTURE ENHANCEMENTS

### 5.1 Feedback Enhancements

1. **Add 'in_progress' status**:
   ```sql
   ALTER TABLE claude.feedback
   ADD CONSTRAINT check_status
   CHECK (status IN ('new', 'in_progress', 'fixed', 'wont_fix', 'duplicate'));
   ```

2. **Add relationships between feedback**:
   ```sql
   CREATE TABLE claude.feedback_relationships (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     feedback_id UUID NOT NULL REFERENCES claude.feedback(feedback_id),
     related_feedback_id UUID NOT NULL REFERENCES claude.feedback(feedback_id),
     relationship_type VARCHAR NOT NULL CHECK (relationship_type IN ('duplicate', 'related', 'blocks', 'blocked_by')),
     created_at TIMESTAMP DEFAULT now(),
     UNIQUE(feedback_id, related_feedback_id, relationship_type)
   );
   ```

3. **Add labels/tags**:
   ```sql
   ALTER TABLE claude.feedback ADD COLUMN labels TEXT[];
   ```

4. **Add estimated effort**:
   ```sql
   ALTER TABLE claude.feedback ADD COLUMN estimated_effort VARCHAR CHECK (estimated_effort IN ('trivial', 'small', 'medium', 'large', 'xl'));
   ```

### 5.2 Documentation Enhancements

1. **Add document versioning history**:
   ```sql
   CREATE TABLE claude.document_versions (
     version_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     doc_id UUID NOT NULL REFERENCES claude.documents(doc_id),
     version VARCHAR NOT NULL,
     file_hash VARCHAR NOT NULL,
     file_path TEXT NOT NULL,
     created_at TIMESTAMP DEFAULT now(),
     created_by VARCHAR
   );
   ```

2. **Add document dependencies**:
   ```sql
   CREATE TABLE claude.document_dependencies (
     id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
     doc_id UUID NOT NULL REFERENCES claude.documents(doc_id),
     depends_on_doc_id UUID NOT NULL REFERENCES claude.documents(doc_id),
     dependency_type VARCHAR CHECK (dependency_type IN ('references', 'requires', 'supersedes', 'obsoleted_by'))
   );
   ```

3. **Add review workflow**:
   ```sql
   ALTER TABLE claude.documents ADD COLUMN requires_review BOOLEAN DEFAULT false;
   ALTER TABLE claude.documents ADD COLUMN reviewed_by VARCHAR;
   ALTER TABLE claude.documents ADD COLUMN reviewed_at TIMESTAMP;
   ```

### 5.3 Unified Workflow Tools

**Tool: `create_workflow_item`**
- Unified interface for creating feedback OR task OR issue
- Auto-routes to correct table based on item_type
- Shared validation and audit trail

**Tool: `search_items`**
- Search across feedback, documents, tasks, knowledge
- Unified query interface with filters
- Return mixed results with type indicators

**Tool: `link_items`**
- Create relationships between ANY two items (feedback <-> document, document <-> task, etc.)
- Generic relationship table with polymorphic keys
- Support relationship types: related, blocks, references, implements, etc.

---

## 6. SUMMARY & RECOMMENDATIONS

### Key Findings

1. **Feedback system is functional but underutilized**:
   - Comments: 1 record only
   - Screenshots: 11 records (moderate)
   - Resolution workflow works but needs enforcement

2. **Documentation system is well-established**:
   - 1,734 documents registered
   - 112 core documents (6.5%)
   - 379 archived documents (21.8%)
   - Junction table exists but underutilized

3. **Data quality needs improvement**:
   - Missing NOT NULL constraints
   - Inconsistent status value casing
   - Deprecated columns still in use
   - Weak validation rules

### Recommended Workflow Tools (Priority Order)

**Phase 1: Core CRUD Operations**
1. `create_feedback` - High priority, immediate value
2. `register_document` - High priority, replaces manual INSERT
3. `add_feedback_comment` - Medium priority, improves collaboration
4. `link_document_to_project` - Medium priority, enables many-to-many

**Phase 2: Workflow Management**
5. `resolve_feedback` - High priority, enforces quality
6. `archive_document` - Medium priority, cleanup automation
7. `update_feedback_status` - Medium priority, add in_progress support

**Phase 3: Advanced Features**
8. `search_feedback` - Filter, sort, aggregate
9. `search_documents` - Full-text search, tag filtering
10. `link_related_items` - Cross-domain relationships

### Schema Migration Recommendations

**High Priority**:
1. Add NOT NULL constraints on critical fields
2. Add CHECK constraints for status values
3. Migrate documents.project_id → document_projects
4. Add 'in_progress' status to feedback

**Medium Priority**:
5. Deprecate documents.category (redundant)
6. Deprecate feedback.screenshot_path (use child table)
7. Standardize status value casing (lowercase)

**Low Priority**:
8. Add document versioning support
9. Add feedback relationships (duplicates, blocks, etc.)
10. Add review workflow for documents

---

**Document Version**: 1.0
**Last Updated**: 2025-12-04
**Next Review**: 2026-01-04
**Owner**: Claude Code Infrastructure Team
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/DATA_GATEWAY_DOMAIN_ANALYSIS.md
