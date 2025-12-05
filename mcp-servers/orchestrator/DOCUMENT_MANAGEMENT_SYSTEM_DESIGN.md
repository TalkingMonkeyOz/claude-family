# Document Management System Design
**Claude Family Infrastructure**

**Version:** 1.0
**Date:** 2025-12-03
**Status:** Design Proposal

---

## Executive Summary

The Claude Family infrastructure currently has **two competing document tables** with significant data quality issues:

- **claude.documents**: 1,727 rows, 94% orphaned, no content storage, legacy design
- **claude.project_docs**: 1 row, proper schema with content storage, underutilized

This design proposes a **migration strategy** to consolidate on `claude.project_docs` as the single source of truth, with filesystem as the canonical source and database as a searchable index with metadata.

**Key Decisions:**
1. **Migrate to project_docs** - Deprecate claude.documents
2. **Filesystem is source of truth** - Database stores metadata + content snapshot
3. **Auto-sync via scheduled job** - Leverage existing infrastructure
4. **Smart classification** - Auto-detect doc types, link to ADRs/knowledge
5. **No data loss** - Archive legacy data before migration

---

## 1. Current State Analysis

### 1.1 Database Schema - Two Competing Tables

#### Table: `claude.documents` (Legacy - **DEPRECATE**)

```sql
Columns:
- doc_id (uuid, PK)
- doc_type (varchar) - 12 types, 75% are "OTHER"
- doc_title (varchar)
- project_id (uuid, FK) - 94% NULL (orphaned)
- file_path (text) - 100% NULL
- file_hash (varchar) - Used but no content validation
- version (varchar)
- status (varchar) - All "ACTIVE"
- created_at (timestamp) - Many NULL
- updated_at (timestamp)
- category (varchar) - Duplicates doc_type
- tags (text[])
- generated_by_agent (varchar)
- last_verified_at (timestamp)

Row count: 1,727
Data quality: 5.3/10 (see DOCUMENTS_DATA_QUALITY_ANALYSIS.md)
```

**Critical Issues:**
- ❌ No `content` column - can't store document text
- ❌ 94% orphaned (no project_id)
- ❌ 100% file_path = NULL
- ❌ 75% categorized as "OTHER"
- ❌ 338 duplicates (19.6% duplication rate)
- ❌ Contains E2E test junk (~26 records)
- ❌ Overlapping doc_type + category fields

#### Table: `claude.project_docs` (New - **ADOPT**)

```sql
Columns:
- document_id (uuid, PK)
- project_id (uuid, FK)
- document_type (varchar)
- title (varchar)
- description (text)
- content (text) ✅ CRITICAL: Stores actual content
- file_path (varchar) ✅ Links to filesystem
- file_hash (varchar) ✅ Detects changes
- last_synced_at (timestamp) ✅ Sync tracking
- status (varchar)
- version (varchar)
- author (varchar)
- approver (varchar)
- approved_at (timestamp)
- created_at (timestamp)
- updated_at (timestamp)
- created_by (varchar)
- metadata (jsonb) ✅ Extensible

Row count: 1 (barely used!)
Design quality: 9/10 - Proper design, just needs adoption
```

**Advantages:**
- ✅ Has `content` column for full-text storage
- ✅ Has `file_hash` for change detection
- ✅ Has `last_synced_at` for sync lifecycle
- ✅ Has `metadata` JSONB for extensibility
- ✅ Proper approval workflow fields
- ✅ Clean, purpose-built schema

### 1.2 Related Tables for Integration

#### `claude.architecture_decisions` (ADR)
```sql
Columns: id, adr_number, title, status, context, decision, consequences, created_at, created_by
Rows: Unknown
Integration: Link ADR documents via metadata->adr_id
```

#### `claude.knowledge`
```sql
Columns: knowledge_id, knowledge_type, title, description, applies_to_projects, code_example, ...
Rows: 144
Integration: Link knowledge entries via metadata->knowledge_ids[]
```

#### `claude.projects`
```sql
Columns: project_id, project_name, project_code, description, status, ...
Rows: Unknown
Integration: FK to project_id
```

### 1.3 Existing Infrastructure

#### Scheduled Job: "Document Scanner"
```sql
job_name: Document Scanner
job_type: indexer
schedule: Daily
is_active: true
last_run: NULL (never executed)
command: python C:\Projects\claude-family\scripts\scan_documents.py
trigger_type: session_start
trigger_condition: {days_since_last_run: 1}
```

**Status:** Registered but never run. Script exists and targets `claude.documents` (legacy table).

#### Script: `scan_documents.py`
**Location:** `C:\Projects\claude-family\scripts\scan_documents.py`
**Status:** Implemented, 263 lines
**Current Behavior:**
- Scans PROJECT_ROOT (`C:/Projects`) and SHARED_DOCS (`C:/claude/shared/docs`)
- Detects 12 doc types via filename patterns
- Extracts title from first `# heading` in markdown
- Calculates SHA256 file hash
- **Writes to claude.documents** (needs migration to project_docs)
- Supports dry-run mode
- Handles project_id lookup

**Strengths:**
- ✅ Good pattern detection logic
- ✅ Hash-based change detection
- ✅ Project association logic
- ✅ Dry-run support
- ✅ Skip patterns (node_modules, .git, etc.)

**Gaps:**
- ❌ No content extraction
- ❌ No ADR/knowledge linking
- ❌ No metadata extraction (tags, description)
- ❌ Targets wrong table (claude.documents)
- ❌ No cleanup of deleted files
- ❌ No archival strategy

### 1.4 Filesystem State

**Projects Root:** `C:\Projects\`
**Shared Docs:** `C:\claude\shared\docs\`

**Sample Project: claude-family**
```
claude-family/
├── docs/                      # Session notes, architecture
├── .claude/commands/          # Slash command definitions
├── shared/
│   ├── docs/                 # Importable shared docs
│   └── scripts/              # Python utilities
├── CLAUDE.md                 # Project config
├── README.md                 # Project overview
└── mcp-servers/              # MCP server implementations
```

**Document Counts (Estimated):**
- claude-family: ~50 markdown files
- mission-control-web: ~100+ markdown files (from db sample)
- Other projects: Unknown, needs discovery

---

## 2. Design Proposal

### 2.1 Strategic Decisions

#### Decision 1: Migrate to project_docs as Single Source of Truth
**Rationale:**
- project_docs has proper schema with content storage
- documents table is legacy with unfixable design flaws
- Continuing dual-table state creates confusion

**Migration Path:**
1. Archive claude.documents to claude.documents_archive
2. Migrate salvageable records to project_docs
3. Update scan_documents.py to write to project_docs
4. Keep documents table read-only for 90 days, then drop

#### Decision 2: Filesystem is Canonical Source
**Rationale:**
- Documents are edited in IDEs, not database
- Git provides version control, branching, merging
- Database is index for searching/metadata, not editing

**Implementation:**
- Scheduled scanner syncs filesystem → database
- Database stores content snapshot + metadata
- file_hash detects changes
- Deleted files are marked status='ARCHIVED' (not hard deleted)

#### Decision 3: Auto-Sync via Scheduled Job
**Rationale:**
- Existing infrastructure (scheduled_jobs, scan_documents.py)
- Runs on session_start if >24h since last run
- Non-intrusive, runs in background

**Schedule:**
- Trigger: session_start
- Condition: days_since_last_run >= 1
- Timeout: 300 seconds (5 minutes)
- Retry on failure: Yes, max 2 retries

### 2.2 Schema Changes

#### 2.2.1 Enhance `claude.project_docs`

```sql
-- Add indexes for performance
CREATE INDEX idx_project_docs_file_path ON claude.project_docs(file_path);
CREATE INDEX idx_project_docs_file_hash ON claude.project_docs(file_hash);
CREATE INDEX idx_project_docs_project_id ON claude.project_docs(project_id);
CREATE INDEX idx_project_docs_document_type ON claude.project_docs(document_type);
CREATE INDEX idx_project_docs_synced ON claude.project_docs(last_synced_at DESC);

-- Add full-text search index on content
CREATE INDEX idx_project_docs_content_fts
ON claude.project_docs USING gin(to_tsvector('english', content));

-- Add computed column for word count (useful metric)
ALTER TABLE claude.project_docs
ADD COLUMN word_count INTEGER GENERATED ALWAYS AS (
    array_length(regexp_split_to_array(content, '\s+'), 1)
) STORED;

-- Enhance metadata JSONB structure (document expected fields)
-- Expected metadata structure:
-- {
--   "adr_id": "uuid",                    // Link to architecture_decisions
--   "knowledge_ids": ["uuid1", "uuid2"], // Links to knowledge entries
--   "tags": ["tag1", "tag2"],            // Searchable tags
--   "frontmatter": {...},                // Parsed YAML frontmatter
--   "related_docs": ["doc_id1"],         // Related documents
--   "scan_metadata": {
--     "source": "auto_scan",
--     "scanner_version": "1.0",
--     "detected_type": "ARCHITECTURE",
--     "confidence": 0.95
--   }
-- }
```

#### 2.2.2 Add Document Link Table (Many-to-Many)

```sql
-- Link documents to ADRs, knowledge, other docs
CREATE TABLE claude.document_links (
    link_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_doc_id UUID NOT NULL REFERENCES claude.project_docs(document_id) ON DELETE CASCADE,
    target_type VARCHAR(50) NOT NULL, -- 'adr', 'knowledge', 'document'
    target_id UUID NOT NULL,
    link_type VARCHAR(50), -- 'describes', 'implements', 'references', 'supersedes'
    confidence DECIMAL(3,2), -- 0.00-1.00 for auto-detected links
    created_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    CONSTRAINT document_links_valid_type CHECK (target_type IN ('adr', 'knowledge', 'document'))
);

CREATE INDEX idx_document_links_source ON claude.document_links(source_doc_id);
CREATE INDEX idx_document_links_target ON claude.document_links(target_type, target_id);
```

#### 2.2.3 Archive Legacy Table

```sql
-- Rename for safety
ALTER TABLE claude.documents RENAME TO documents_legacy_archive;

-- Add archive metadata
ALTER TABLE claude.documents_legacy_archive
ADD COLUMN archived_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN migration_status VARCHAR(50) DEFAULT 'pending';

-- Prevent writes
REVOKE INSERT, UPDATE, DELETE ON claude.documents_legacy_archive FROM PUBLIC;
```

### 2.3 Document Scanner Job Specification

#### 2.3.1 Enhanced scan_documents.py

**New Features:**

1. **Content Extraction**
   - Read full file content into `content` column
   - Extract YAML frontmatter into `metadata->frontmatter`
   - Calculate word count
   - Extract description (first paragraph after title)

2. **Smart Classification**
   - Multi-pattern matching with confidence scores
   - Frontmatter override (e.g., `doc_type: ARCHITECTURE`)
   - Content analysis (keywords in first 500 chars)
   - Directory-based hints (e.g., `/docs/adr/` → ADR)

3. **ADR Linking**
   - Detect ADR pattern: `ADR-\d+`, `adr/\d+`, `architecture-decision-\d+`
   - Extract ADR number from filename
   - Query `claude.architecture_decisions` for match
   - Create link in `document_links` table

4. **Knowledge Linking**
   - Extract keywords from content
   - Query `claude.knowledge` for matching titles/descriptions
   - Create links with confidence score
   - Store in `metadata->knowledge_ids`

5. **Tag Extraction**
   - From frontmatter: `tags: [react, typescript]`
   - From content: detect project names, tech stack
   - Store in `metadata->tags`

6. **Deletion Detection**
   - Query existing records in project_docs
   - Check if file_path still exists on filesystem
   - Mark missing files as status='ARCHIVED'
   - Store `metadata->archived_reason = 'file_deleted'`

7. **Project Association**
   - Infer from file path: `C:/Projects/nimbus/...` → nimbus
   - Query `claude.projects` for fuzzy match
   - Store project_id (handle missing projects gracefully)

#### 2.3.2 Configuration

```python
# Directories to scan
SCAN_ROOTS = [
    {
        'path': 'C:/Projects',
        'pattern': '**/*.md',
        'exclude': ['node_modules', '.git', '__pycache__', 'venv', '.next', 'dist', 'build'],
        'min_file_size': 50,  # bytes
    },
    {
        'path': 'C:/claude/shared/docs',
        'pattern': '*.md',
        'exclude': [],
        'project_override': 'shared',  # Force project name
    },
]

# Document type detection (enhanced with confidence)
DOC_TYPE_PATTERNS = {
    'ARCHITECTURE': {
        'filename': ['architecture', 'arch_', 'system_design', 'design_doc'],
        'content': ['system design', 'architecture decision', 'component diagram'],
        'directory': ['architecture', 'design'],
        'weight': 0.8,
    },
    'ADR': {
        'filename': ['adr-', 'adr_', 'decision-'],
        'content': ['## Context', '## Decision', '## Consequences'],
        'directory': ['adr', 'decisions'],
        'weight': 0.95,
    },
    # ... (expand all types)
}

# File patterns to EXCLUDE
EXCLUDE_PATTERNS = [
    'E2E Test Document',      # Test junk
    'Delete Test Document',   # Test junk
    'Page snapshot',          # Web crawl artifacts
    'robots.txt',             # Web artifacts
]
```

#### 2.3.3 Execution Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. START: Document Scanner Job                             │
│    - Triggered by: session_start (if >24h since last run)  │
│    - Timeout: 300s                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. DISCOVER: Scan filesystem                                │
│    - Glob patterns: **/*.md, **/*.txt, **/*.rst             │
│    - Apply exclude filters                                  │
│    - Collect file metadata (size, mtime, path)              │
│    - Result: List of candidate files                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. CLASSIFY: Detect doc types                               │
│    - Extract frontmatter (YAML/TOML)                        │
│    - Analyze filename patterns                              │
│    - Analyze directory structure                            │
│    - Scan first 500 chars for keywords                      │
│    - Calculate confidence score (0.0-1.0)                   │
│    - Assign doc_type (use "OTHER" if confidence <0.5)       │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. EXTRACT: Parse document content                          │
│    - Read full content                                      │
│    - Extract title (# heading or frontmatter.title)         │
│    - Extract description (first paragraph)                  │
│    - Parse frontmatter metadata                             │
│    - Extract tags                                           │
│    - Calculate file hash (SHA256)                           │
│    - Calculate word count                                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. LINK: Discover relationships                             │
│    - Detect ADR references (pattern matching)               │
│    - Query architecture_decisions table                     │
│    - Search knowledge table for matching keywords           │
│    - Identify related documents (same project, similar tags)│
│    - Store links with confidence scores                     │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. SYNC: Upsert to database                                 │
│    - Check existing by file_path                            │
│    - If exists:                                             │
│      - Compare file_hash                                    │
│      - If changed: UPDATE with new content, bump version    │
│      - If unchanged: Skip                                   │
│    - If new: INSERT new record                              │
│    - Update last_synced_at = NOW()                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. CLEANUP: Handle deleted files                            │
│    - Query all project_docs with status='ACTIVE'            │
│    - Check if file_path exists on filesystem                │
│    - If missing:                                            │
│      - UPDATE status='ARCHIVED'                             │
│      - Store metadata.archived_reason = 'file_deleted'      │
│      - Store metadata.archived_at = NOW()                   │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. REPORT: Log results                                      │
│    - Insert into job_run_history                            │
│    - Findings JSONB: {                                      │
│        "scanned": 150,                                      │
│        "new": 12,                                           │
│        "updated": 5,                                        │
│        "unchanged": 130,                                    │
│        "archived": 3,                                       │
│        "errors": [],                                        │
│        "execution_time_ms": 4532                            │
│      }                                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Integration Points

### 3.1 Link to Architecture Decisions (ADRs)

**Use Case:** ADR documents should be bidirectionally linked to their database entries

**Detection Logic:**
```python
def detect_adr_link(file_path: Path, content: str) -> Optional[int]:
    """Detect ADR number from filename or content."""
    # Pattern 1: Filename contains ADR-001, adr_001, etc.
    match = re.search(r'adr[-_]?(\d+)', file_path.name, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # Pattern 2: Directory structure: docs/adr/001-title.md
    if 'adr' in file_path.parts:
        match = re.search(r'(\d+)', file_path.name)
        if match:
            return int(match.group(1))

    # Pattern 3: Frontmatter: adr_number: 5
    frontmatter = parse_frontmatter(content)
    if 'adr_number' in frontmatter:
        return frontmatter['adr_number']

    return None
```

**Link Creation:**
```sql
-- After detecting ADR-005 in document
INSERT INTO claude.document_links
(source_doc_id, target_type, target_id, link_type, confidence, created_by)
VALUES
(
    '...doc_id...',
    'adr',
    (SELECT id FROM claude.architecture_decisions WHERE adr_number = 5),
    'describes',
    0.95,
    'document_scanner'
);
```

### 3.2 Link to Knowledge Entries

**Use Case:** Documents that describe patterns, gotchas, or techniques should link to knowledge table

**Detection Logic:**
```python
def detect_knowledge_links(content: str, title: str) -> List[Tuple[uuid.UUID, float]]:
    """Find knowledge entries related to document content."""
    links = []

    # Extract keywords from title and first 1000 chars
    keywords = extract_keywords(title + ' ' + content[:1000])

    # Query knowledge table for fuzzy matches
    for keyword in keywords:
        results = db.execute("""
            SELECT knowledge_id, title, description,
                   similarity(title, %s) as sim
            FROM claude.knowledge
            WHERE title ILIKE %s OR description ILIKE %s
            ORDER BY sim DESC
            LIMIT 3
        """, (keyword, f'%{keyword}%', f'%{keyword}%'))

        for row in results:
            if row['sim'] > 0.6:  # Threshold
                links.append((row['knowledge_id'], row['sim']))

    return links
```

### 3.3 Link to Projects

**Strict Requirement:** Every document MUST have a project_id (no orphans)

**Resolution Logic:**
```python
def resolve_project_id(file_path: Path) -> uuid.UUID:
    """Resolve project_id from file path."""
    # Strategy 1: Extract from path (C:/Projects/nimbus/...)
    if 'Projects' in file_path.parts:
        idx = file_path.parts.index('Projects')
        if idx + 1 < len(file_path.parts):
            project_name = file_path.parts[idx + 1]
            project_id = lookup_project_by_name(project_name)
            if project_id:
                return project_id

    # Strategy 2: Check for CLAUDE.md in parent dirs
    current = file_path.parent
    while current != current.parent:
        claude_md = current / 'CLAUDE.md'
        if claude_md.exists():
            project_name = parse_claude_md_project_name(claude_md)
            return lookup_project_by_name(project_name)
        current = current.parent

    # Strategy 3: Shared docs → create 'shared' project
    if 'claude' in file_path.parts and 'shared' in file_path.parts:
        return ensure_shared_project_exists()

    # Fallback: Create 'uncategorized' project
    return ensure_uncategorized_project_exists()
```

**No Orphans Policy:**
```sql
-- Add NOT NULL constraint after migration
ALTER TABLE claude.project_docs
ALTER COLUMN project_id SET NOT NULL;

-- Add FK constraint
ALTER TABLE claude.project_docs
ADD CONSTRAINT fk_project_docs_project
FOREIGN KEY (project_id) REFERENCES claude.projects(project_id);
```

---

## 4. Migration Strategy

### Phase 1: Preparation (Week 1)

**1.1 Archive Legacy Table**
```sql
-- Safety: Rename and revoke write access
ALTER TABLE claude.documents RENAME TO documents_legacy_archive;
REVOKE INSERT, UPDATE, DELETE ON claude.documents_legacy_archive FROM PUBLIC;

-- Add migration tracking
ALTER TABLE claude.documents_legacy_archive
ADD COLUMN archived_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN migration_status VARCHAR(50) DEFAULT 'pending',
ADD COLUMN migrated_to_doc_id UUID;
```

**1.2 Enhance project_docs**
```sql
-- Run all schema changes from Section 2.2.1
-- Add indexes, FTS, computed columns
```

**1.3 Create document_links table**
```sql
-- Run schema from Section 2.2.2
```

### Phase 2: Selective Migration (Week 1)

**Goal:** Migrate only high-value documents (not garbage)

**2.1 Identify Salvageable Records**
```sql
-- Select records worth migrating
CREATE TEMP TABLE migration_candidates AS
SELECT *
FROM claude.documents_legacy_archive
WHERE
    -- Has project association
    project_id IS NOT NULL
    -- Not test junk
    AND doc_title NOT LIKE '%E2E Test%'
    AND doc_title NOT LIKE '%Delete Test%'
    AND doc_title NOT LIKE 'Page snapshot'
    AND doc_title NOT LIKE 'robots.txt'
    -- Not duplicate (keep latest version)
    AND doc_id IN (
        SELECT doc_id FROM (
            SELECT doc_id,
                   ROW_NUMBER() OVER (PARTITION BY doc_title, doc_type ORDER BY updated_at DESC) as rn
            FROM claude.documents_legacy_archive
        ) sub WHERE rn = 1
    )
    -- Has actual content (file_path exists)
    AND file_path IS NOT NULL;

-- Expected: ~300-400 records (from 1,727)
SELECT COUNT(*) FROM migration_candidates;
```

**2.2 Migrate Records**
```sql
-- Attempt to read content from filesystem
-- This requires Python script:
-- migrate_documents.py --dry-run
-- migrate_documents.py --execute
```

**Python Migration Script:**
```python
# migrate_documents.py
# 1. Read migration_candidates from DB
# 2. For each record:
#    a. Check if file_path exists
#    b. If yes: Read content, calculate new hash
#    c. If no: Skip (mark migration_status='file_not_found')
#    d. Insert into project_docs
#    e. Update legacy record: migrated_to_doc_id, migration_status='migrated'
# 3. Log results
```

### Phase 3: Scanner Update (Week 1-2)

**3.1 Rewrite scan_documents.py**
- Target: claude.project_docs (not documents)
- Add all features from Section 2.3.1
- Test with --dry-run
- Execute on small project first

**3.2 Update Scheduled Job**
```sql
UPDATE claude.scheduled_jobs
SET
    command = 'python C:\\Projects\\claude-family\\scripts\\scan_documents_v2.py',
    job_description = 'Scan and index project documentation to claude.project_docs',
    updated_at = NOW()
WHERE job_name = 'Document Scanner';
```

### Phase 4: Validation (Week 2)

**4.1 Data Quality Checks**
```sql
-- No orphans
SELECT COUNT(*) FROM claude.project_docs WHERE project_id IS NULL;
-- Expected: 0

-- All have content
SELECT COUNT(*) FROM claude.project_docs WHERE content IS NULL OR content = '';
-- Expected: 0

-- File paths exist
-- (Run Python validator script)

-- No duplicates
SELECT title, COUNT(*)
FROM claude.project_docs
GROUP BY title, document_type
HAVING COUNT(*) > 1;
-- Expected: 0 rows
```

**4.2 Integration Tests**
- Test ADR linking for known ADR documents
- Test knowledge linking for known pattern docs
- Verify project associations
- Check metadata JSONB structure

### Phase 5: Production (Week 2-3)

**5.1 Enable Scheduled Job**
```sql
UPDATE claude.scheduled_jobs
SET is_active = true, next_run = NOW() + INTERVAL '1 day'
WHERE job_name = 'Document Scanner';
```

**5.2 Monitor First Runs**
- Check job_run_history for errors
- Review findings JSONB for anomalies
- Validate new document detection

**5.3 Drop Legacy Table (After 90 Days)**
```sql
-- After validation period
DROP TABLE claude.documents_legacy_archive;
```

---

## 5. Cleanup Strategy

### 5.1 Immediate Cleanup (Before Migration)

**Remove E2E Test Junk**
```sql
DELETE FROM claude.documents_legacy_archive
WHERE doc_title LIKE '%E2E Test%'
   OR doc_title LIKE '%Delete Test%'
   OR doc_title = 'Page snapshot'
   OR doc_title = 'robots.txt';

-- Expected: ~100 records deleted
```

**Remove Duplicates (Keep Latest)**
```sql
WITH ranked AS (
    SELECT doc_id,
           ROW_NUMBER() OVER (PARTITION BY doc_title, doc_type ORDER BY updated_at DESC NULLS LAST) as rn
    FROM claude.documents_legacy_archive
)
DELETE FROM claude.documents_legacy_archive
WHERE doc_id IN (SELECT doc_id FROM ranked WHERE rn > 1);

-- Expected: ~338 records deleted
```

### 5.2 Ongoing Cleanup (Post-Migration)

**Archive Deleted Files**
- Scanner marks status='ARCHIVED' when file no longer exists
- Retention: Keep archived records for 1 year
- Purge: Annual job deletes archived records >1 year old

**Deduplication Check**
- Scanner checks for duplicates by (file_path, file_hash)
- If duplicate: Keep only one, log warning

---

## 6. Risks and Mitigations

### Risk 1: Data Loss During Migration
**Severity:** HIGH
**Probability:** MEDIUM

**Mitigation:**
- ✅ Archive original table (rename, not drop)
- ✅ Dry-run mode for migration script
- ✅ Validation queries before/after
- ✅ 90-day retention before permanent deletion
- ✅ Manual review of migration_candidates list

### Risk 2: Scanner Overwrites Manual Edits
**Severity:** MEDIUM
**Probability:** LOW

**Context:** If user manually edits content in database, scanner may overwrite on next sync

**Mitigation:**
- ✅ Filesystem is source of truth (documented)
- ✅ Database is read-only for users (edit files, not DB)
- ✅ Add `manual_override` flag in metadata
- ✅ Scanner skips records with manual_override=true

### Risk 3: Incorrect ADR/Knowledge Linking
**Severity:** LOW
**Probability:** MEDIUM

**Mitigation:**
- ✅ Store confidence scores (0.0-1.0)
- ✅ Manual review for confidence <0.8
- ✅ Soft links (no FK constraints, can be deleted)
- ✅ Audit trail in document_links

### Risk 4: Scanner Performance Impact
**Severity:** LOW
**Probability:** LOW

**Mitigation:**
- ✅ Timeout: 300 seconds max
- ✅ Runs only on session_start (not continuous)
- ✅ Skip unchanged files (hash comparison)
- ✅ Batch inserts (not one-by-one)
- ✅ Async execution (doesn't block user)

### Risk 5: Project Association Errors
**Severity:** MEDIUM
**Probability:** MEDIUM

**Mitigation:**
- ✅ Multiple resolution strategies (path, CLAUDE.md, shared)
- ✅ Fallback to 'uncategorized' project
- ✅ Manual review report for uncategorized docs
- ✅ NOT NULL constraint prevents orphans

---

## 7. Success Metrics

### 7.1 Data Quality Improvement

| Metric | Before (claude.documents) | Target (project_docs) |
|--------|---------------------------|----------------------|
| Orphan rate | 94% (1,625/1,727) | 0% |
| Duplication rate | 19.6% (338 records) | <1% |
| "OTHER" classification | 74.8% | <20% |
| Content storage | 0% (no column) | 100% |
| File path coverage | 0% (all NULL) | 100% |
| Overall quality score | 5.3/10 | >8.5/10 |

### 7.2 Functionality Metrics

- ✅ ADR linking coverage: >90% of ADR documents linked
- ✅ Knowledge linking coverage: >50% of pattern/guide docs linked
- ✅ Scanner uptime: >95% success rate
- ✅ Sync freshness: >90% of docs synced within 24h
- ✅ Search performance: <500ms for full-text queries

### 7.3 User Experience

- ✅ Documents searchable in Mission Control Web UI
- ✅ ADR documents show related knowledge entries
- ✅ Project documentation fully indexed
- ✅ No manual intervention needed for new files

---

## 8. Future Enhancements

### 8.1 Phase 2 Features (Post-MVP)

**Versioning System**
- Store historical versions in separate table
- Track who changed what, when
- Diff view in UI

**Full-Text Search API**
- REST endpoint: `GET /api/documents/search?q=keywords`
- Rank by relevance (ts_rank)
- Filter by project, doc_type, tags

**Document Templates**
- Use existing `claude.doc_templates` table
- Generate new docs from templates
- Enforce structure for ADRs, SOPs

**Smart Recommendations**
- "Related documents you might want to read"
- Based on current session context
- ML-based similarity (future)

### 8.2 Integration with Mission Control Web

**Documents Tab Enhancement**
- Full-text search bar
- Filter by project, type, tags
- Preview pane with markdown rendering
- "Open in editor" button (launches VSCode)

**ADR Browser**
- List all ADRs with status
- Show linked documents
- Timeline view

---

## 9. Implementation Timeline

### Week 1: Foundation
- [ ] Day 1-2: Schema changes (project_docs enhancements, document_links table)
- [ ] Day 3: Archive legacy table, run cleanup scripts
- [ ] Day 4-5: Write + test migration script (dry-run mode)

### Week 2: Migration + Scanner
- [ ] Day 1-2: Execute migration, validate results
- [ ] Day 3-4: Rewrite scan_documents.py (v2)
- [ ] Day 5: Test scanner on small project, fix bugs

### Week 3: Production Rollout
- [ ] Day 1: Deploy scanner v2, update scheduled job
- [ ] Day 2-3: Monitor first runs, fix issues
- [ ] Day 4-5: Document usage, create runbooks

### Week 4+: Validation
- [ ] Monitor data quality metrics
- [ ] User feedback on search/discovery
- [ ] Plan Phase 2 features

---

## 10. Appendix

### A. SQL Queries for Analysis

**Current state of project_docs:**
```sql
SELECT
    COUNT(*) as total_docs,
    COUNT(DISTINCT project_id) as projects,
    COUNT(DISTINCT document_type) as doc_types,
    SUM(CASE WHEN content IS NOT NULL THEN 1 ELSE 0 END) as has_content,
    AVG(LENGTH(content)) as avg_content_length
FROM claude.project_docs;
```

**Migration candidates (salvageable from legacy):**
```sql
SELECT doc_type, category, COUNT(*)
FROM claude.documents_legacy_archive
WHERE project_id IS NOT NULL
  AND doc_title NOT LIKE '%Test%'
  AND doc_title NOT LIKE 'Page snapshot'
GROUP BY doc_type, category
ORDER BY COUNT(*) DESC;
```

### B. Python Script Snippets

**Extract frontmatter:**
```python
import re
import yaml

def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if match:
        try:
            return yaml.safe_load(match.group(1))
        except:
            return {}
    return {}
```

**Calculate confidence score:**
```python
def classify_document(file_path: Path, content: str, frontmatter: dict) -> tuple:
    """Return (doc_type, confidence_score)."""
    scores = {}

    # Check frontmatter override
    if 'doc_type' in frontmatter:
        return (frontmatter['doc_type'].upper(), 1.0)

    # Score each doc type
    for doc_type, patterns in DOC_TYPE_PATTERNS.items():
        score = 0.0

        # Filename patterns
        for pattern in patterns['filename']:
            if pattern in file_path.name.lower():
                score += patterns['weight'] * 0.5

        # Content keywords
        content_lower = content[:500].lower()
        for keyword in patterns['content']:
            if keyword in content_lower:
                score += patterns['weight'] * 0.3

        # Directory structure
        for dir_pattern in patterns['directory']:
            if dir_pattern in str(file_path).lower():
                score += patterns['weight'] * 0.2

        scores[doc_type] = min(score, 1.0)

    # Return highest scoring type
    if scores:
        best_type = max(scores.items(), key=lambda x: x[1])
        if best_type[1] > 0.5:
            return best_type

    return ('OTHER', 0.0)
```

### C. References

- [Data Quality Analysis - documents table](./DOCUMENTS_DATA_QUALITY_ANALYSIS.md)
- [Knowledge Table Analysis](./knowledge-table-analysis.md)
- [Existing Scanner Script](../../scripts/scan_documents.py)
- [ADR Template](https://github.com/joelparkerhenderson/architecture-decision-record)

---

**Document Status:** Draft for Review
**Next Steps:** Review with stakeholders, approve schema changes, begin implementation
**Owner:** Claude Family Infrastructure Team
**Reviewers:** [To be assigned]
