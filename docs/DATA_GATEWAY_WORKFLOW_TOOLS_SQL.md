# Data Gateway Workflow Tools - SQL Implementation Specifications

**Date**: 2025-12-04
**Purpose**: SQL implementation details for Feedback & Documentation workflow tools
**Companion Document**: DATA_GATEWAY_DOMAIN_ANALYSIS.md

---

## Tool 1: `create_feedback`

### Function Signature

```sql
CREATE OR REPLACE FUNCTION claude.create_feedback(
  p_project_id UUID,
  p_feedback_type VARCHAR,
  p_description TEXT,
  p_priority VARCHAR DEFAULT 'medium',
  p_assigned_to VARCHAR DEFAULT NULL,
  p_screenshot_paths TEXT[] DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  v_feedback_id UUID;
  v_screenshot_path TEXT;
BEGIN
  -- Validate project exists
  IF NOT EXISTS (SELECT 1 FROM claude.projects WHERE project_id = p_project_id) THEN
    RAISE EXCEPTION 'Project not found: %', p_project_id;
  END IF;

  -- Validate feedback_type
  IF p_feedback_type NOT IN ('bug', 'design', 'question', 'change') THEN
    RAISE EXCEPTION 'Invalid feedback_type: %. Must be bug, design, question, or change', p_feedback_type;
  END IF;

  -- Validate description length
  IF LENGTH(TRIM(p_description)) < 10 THEN
    RAISE EXCEPTION 'Description too short. Minimum 10 characters required.';
  END IF;

  -- Additional validation for bugs
  IF p_feedback_type = 'bug' AND LENGTH(TRIM(p_description)) < 50 THEN
    RAISE WARNING 'Bug descriptions should be at least 50 characters for clarity. Current: %', LENGTH(TRIM(p_description));
  END IF;

  -- Validate priority
  IF p_priority NOT IN ('high', 'medium', 'low') THEN
    RAISE EXCEPTION 'Invalid priority: %. Must be high, medium, or low', p_priority;
  END IF;

  -- Create feedback record
  INSERT INTO claude.feedback (
    feedback_id,
    project_id,
    feedback_type,
    description,
    priority,
    status,
    assigned_to,
    created_at,
    updated_at
  ) VALUES (
    uuid_generate_v4(),
    p_project_id,
    p_feedback_type,
    TRIM(p_description),
    p_priority,
    'new',
    p_assigned_to,
    now(),
    now()
  ) RETURNING feedback_id INTO v_feedback_id;

  -- Handle screenshots if provided
  IF p_screenshot_paths IS NOT NULL THEN
    FOREACH v_screenshot_path IN ARRAY p_screenshot_paths
    LOOP
      -- Note: File existence validation should be done by calling application
      INSERT INTO claude.feedback_screenshots (
        id,
        feedback_id,
        file_path,
        uploaded_at
      ) VALUES (
        uuid_generate_v4(),
        v_feedback_id,
        v_screenshot_path,
        now()
      );
    END LOOP;
  END IF;

  -- Log quality warnings
  IF p_feedback_type = 'bug' AND p_screenshot_paths IS NULL THEN
    RAISE NOTICE 'Bug report created without screenshots. Consider adding visual evidence.';
  END IF;

  RETURN v_feedback_id;
END;
$$;
```

### Usage Example

```sql
-- Create bug report with screenshots
SELECT claude.create_feedback(
  p_project_id := 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
  p_feedback_type := 'bug',
  p_description := 'Login button does not respond on mobile Safari. Steps to reproduce: 1) Open app on iPhone, 2) Navigate to login page, 3) Tap login button - nothing happens.',
  p_priority := 'high',
  p_screenshot_paths := ARRAY['/screenshots/login-bug-001.png', '/screenshots/login-bug-002.png']
);

-- Create design feedback
SELECT claude.create_feedback(
  p_project_id := 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
  p_feedback_type := 'design',
  p_description := 'Navigation menu is difficult to use on small screens. Consider hamburger menu design.',
  p_priority := 'medium'
);
```

---

## Tool 2: `add_feedback_comment`

### Function Signature

```sql
CREATE OR REPLACE FUNCTION claude.add_feedback_comment(
  p_feedback_id UUID,
  p_author VARCHAR,
  p_message TEXT,
  p_screenshot_path TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  v_comment_id UUID;
BEGIN
  -- Validate feedback exists
  IF NOT EXISTS (SELECT 1 FROM claude.feedback WHERE feedback_id = p_feedback_id) THEN
    RAISE EXCEPTION 'Feedback not found: %', p_feedback_id;
  END IF;

  -- Validate message length
  IF LENGTH(TRIM(p_message)) < 5 THEN
    RAISE EXCEPTION 'Comment message too short. Minimum 5 characters required.';
  END IF;

  -- Validate author
  IF TRIM(p_author) = '' THEN
    RAISE EXCEPTION 'Author is required';
  END IF;

  -- Insert comment
  INSERT INTO claude.feedback_comments (
    id,
    feedback_id,
    author,
    message,
    created_at
  ) VALUES (
    uuid_generate_v4(),
    p_feedback_id,
    TRIM(p_author),
    TRIM(p_message),
    now()
  ) RETURNING id INTO v_comment_id;

  -- Update parent feedback timestamp
  UPDATE claude.feedback
  SET updated_at = now()
  WHERE feedback_id = p_feedback_id;

  -- Add screenshot if provided
  IF p_screenshot_path IS NOT NULL THEN
    INSERT INTO claude.feedback_screenshots (
      id,
      feedback_id,
      file_path,
      caption,
      uploaded_at
    ) VALUES (
      uuid_generate_v4(),
      p_feedback_id,
      p_screenshot_path,
      'Attached to comment by ' || p_author,
      now()
    );
  END IF;

  RETURN v_comment_id;
END;
$$;
```

### Usage Example

```sql
-- Add comment to feedback
SELECT claude.add_feedback_comment(
  p_feedback_id := 'f1e2d3c4-b5a6-7890-cdef-1234567890ab'::uuid,
  p_author := 'claude-code-unified',
  p_message := 'Investigated this issue. The problem occurs because the onclick handler is not properly bound on iOS Safari. Working on a fix.'
);

-- Add comment with screenshot
SELECT claude.add_feedback_comment(
  p_feedback_id := 'f1e2d3c4-b5a6-7890-cdef-1234567890ab'::uuid,
  p_author := 'claude-pm-agent',
  p_message := 'Here is a screenshot showing the console error that appears when this bug occurs.',
  p_screenshot_path := '/screenshots/console-error.png'
);
```

---

## Tool 3: `resolve_feedback`

### Function Signature

```sql
CREATE OR REPLACE FUNCTION claude.resolve_feedback(
  p_feedback_id UUID,
  p_resolution VARCHAR, -- 'fixed' or 'wont_fix'
  p_notes TEXT,
  p_resolved_by VARCHAR
)
RETURNS JSONB
LANGUAGE plpgsql
AS $$
DECLARE
  v_current_status VARCHAR;
  v_result JSONB;
BEGIN
  -- Get current status
  SELECT status INTO v_current_status
  FROM claude.feedback
  WHERE feedback_id = p_feedback_id;

  IF NOT FOUND THEN
    RAISE EXCEPTION 'Feedback not found: %', p_feedback_id;
  END IF;

  -- Check if already resolved
  IF v_current_status IN ('fixed', 'wont_fix') THEN
    RAISE EXCEPTION 'Feedback already resolved with status: %. Cannot re-resolve.', v_current_status;
  END IF;

  -- Validate resolution
  IF p_resolution NOT IN ('fixed', 'wont_fix') THEN
    RAISE EXCEPTION 'Invalid resolution: %. Must be fixed or wont_fix', p_resolution;
  END IF;

  -- Validate notes length
  IF LENGTH(TRIM(p_notes)) < 20 THEN
    RAISE EXCEPTION 'Resolution notes too short. Minimum 20 characters required for proper documentation.';
  END IF;

  -- Additional validation for wont_fix
  IF p_resolution = 'wont_fix' AND LENGTH(TRIM(p_notes)) < 50 THEN
    RAISE EXCEPTION 'wont_fix resolution requires detailed justification. Minimum 50 characters.';
  END IF;

  -- Update feedback
  UPDATE claude.feedback
  SET
    status = p_resolution,
    notes = TRIM(p_notes),
    resolved_at = now(),
    updated_at = now()
  WHERE feedback_id = p_feedback_id
    AND status = 'new'
  RETURNING
    jsonb_build_object(
      'feedback_id', feedback_id::text,
      'status', status,
      'resolved_at', resolved_at,
      'notes', notes
    ) INTO v_result;

  -- Add resolution comment for audit trail
  INSERT INTO claude.feedback_comments (
    id,
    feedback_id,
    author,
    message,
    created_at
  ) VALUES (
    uuid_generate_v4(),
    p_feedback_id,
    p_resolved_by,
    'Resolved as ' || p_resolution || E':\n\n' || TRIM(p_notes),
    now()
  );

  RETURN v_result;
END;
$$;
```

### Usage Example

```sql
-- Resolve as fixed
SELECT claude.resolve_feedback(
  p_feedback_id := 'f1e2d3c4-b5a6-7890-cdef-1234567890ab'::uuid,
  p_resolution := 'fixed',
  p_notes := 'Fixed in commit abc123. Added proper event listener binding for iOS Safari. Tested on iPhone 12, iOS 15.4.',
  p_resolved_by := 'claude-code-unified'
);

-- Resolve as won't fix
SELECT claude.resolve_feedback(
  p_feedback_id := 'f1e2d3c4-b5a6-7890-cdef-1234567890ab'::uuid,
  p_resolution := 'wont_fix',
  p_notes := 'This behavior is intentional. The navigation menu is designed for desktop use and the mobile app has a separate native interface. No changes needed to web version.',
  p_resolved_by := 'claude-pm-agent'
);
```

---

## Tool 4: `register_document`

### Function Signature

```sql
CREATE OR REPLACE FUNCTION claude.register_document(
  p_doc_type VARCHAR,
  p_doc_title VARCHAR,
  p_file_path TEXT,
  p_file_hash VARCHAR DEFAULT NULL,
  p_project_ids UUID[] DEFAULT NULL,
  p_version VARCHAR DEFAULT NULL,
  p_tags TEXT[] DEFAULT NULL,
  p_is_core BOOLEAN DEFAULT false,
  p_core_reason TEXT DEFAULT NULL,
  p_generated_by_agent VARCHAR DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  v_doc_id UUID;
  v_project_id UUID;
  v_is_first BOOLEAN := true;
BEGIN
  -- Validate doc_type
  IF p_doc_type NOT IN (
    'ADR', 'API', 'ARCHITECTURE', 'ARCHIVE', 'CLAUDE_CONFIG',
    'COMPLETION_REPORT', 'GUIDE', 'MIGRATION', 'OTHER', 'README',
    'REFERENCE', 'SESSION_NOTE', 'SOP', 'SPEC', 'TEST_DOC', 'TROUBLESHOOTING'
  ) THEN
    RAISE EXCEPTION 'Invalid doc_type: %. Must be one of the 16 standard types (uppercase)', p_doc_type;
  END IF;

  -- Validate title length
  IF LENGTH(TRIM(p_doc_title)) < 5 THEN
    RAISE EXCEPTION 'Document title too short. Minimum 5 characters required.';
  END IF;

  -- Validate file_path
  IF TRIM(p_file_path) = '' THEN
    RAISE EXCEPTION 'File path is required';
  END IF;

  -- Validate core documentation requirements
  IF p_is_core = true AND (p_core_reason IS NULL OR LENGTH(TRIM(p_core_reason)) < 10) THEN
    RAISE EXCEPTION 'Core documents must have a core_reason with minimum 10 characters explaining why it is core';
  END IF;

  -- Check for duplicate file_path
  IF EXISTS (SELECT 1 FROM claude.documents WHERE file_path = p_file_path AND is_archived = false) THEN
    RAISE WARNING 'Document with this file_path already exists: %', p_file_path;
  END IF;

  -- Insert document
  INSERT INTO claude.documents (
    doc_id,
    doc_type,
    doc_title,
    file_path,
    file_hash,
    version,
    status,
    category,
    tags,
    generated_by_agent,
    is_core,
    core_reason,
    is_archived,
    created_at,
    updated_at,
    last_verified_at
  ) VALUES (
    uuid_generate_v4(),
    p_doc_type,
    TRIM(p_doc_title),
    p_file_path,
    p_file_hash,
    p_version,
    'ACTIVE',
    LOWER(p_doc_type), -- Auto-derive category from doc_type
    p_tags,
    p_generated_by_agent,
    p_is_core,
    p_core_reason,
    false,
    now(),
    now(),
    now()
  ) RETURNING doc_id INTO v_doc_id;

  -- Link to projects if provided
  IF p_project_ids IS NOT NULL AND array_length(p_project_ids, 1) > 0 THEN
    FOREACH v_project_id IN ARRAY p_project_ids
    LOOP
      -- Validate project exists
      IF NOT EXISTS (SELECT 1 FROM claude.projects WHERE project_id = v_project_id) THEN
        RAISE WARNING 'Project not found, skipping link: %', v_project_id;
        CONTINUE;
      END IF;

      -- Insert link (first project is primary, rest are secondary)
      INSERT INTO claude.document_projects (
        document_project_id,
        doc_id,
        project_id,
        is_primary,
        linked_by,
        linked_at
      ) VALUES (
        uuid_generate_v4(),
        v_doc_id,
        v_project_id,
        v_is_first,
        p_generated_by_agent,
        now()
      );

      v_is_first := false;
    END LOOP;
  END IF;

  -- Log quality notices
  IF p_file_hash IS NULL THEN
    RAISE NOTICE 'Document registered without file_hash. Consider adding for change detection.';
  END IF;

  IF p_version IS NULL THEN
    RAISE NOTICE 'Document registered without version. Consider adding for tracking.';
  END IF;

  RETURN v_doc_id;
END;
$$;
```

### Usage Example

```sql
-- Register architecture document
SELECT claude.register_document(
  p_doc_type := 'ARCHITECTURE',
  p_doc_title := 'Claude Family Multi-Agent Architecture',
  p_file_path := '/docs/architecture/multi-agent-system.md',
  p_file_hash := 'abc123def456...',
  p_project_ids := ARRAY[
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
    'b2c3d4e5-f6a7-8901-bcde-f12345678901'::uuid
  ],
  p_version := '2.0',
  p_tags := ARRAY['architecture', 'multi-agent', 'orchestration'],
  p_is_core := true,
  p_core_reason := 'Core architectural documentation defining the entire Claude Family agent orchestration system',
  p_generated_by_agent := 'claude-code-unified'
);

-- Register simple README
SELECT claude.register_document(
  p_doc_type := 'README',
  p_doc_title := 'Project Setup Guide',
  p_file_path := '/README.md',
  p_project_ids := ARRAY['a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid],
  p_version := '1.0'
);
```

---

## Tool 5: `link_document_to_project`

### Function Signature

```sql
CREATE OR REPLACE FUNCTION claude.link_document_to_project(
  p_doc_id UUID,
  p_project_id UUID,
  p_is_primary BOOLEAN DEFAULT false,
  p_linked_by VARCHAR DEFAULT NULL
)
RETURNS UUID
LANGUAGE plpgsql
AS $$
DECLARE
  v_document_project_id UUID;
  v_existing_primary_count INT;
BEGIN
  -- Validate document exists
  IF NOT EXISTS (SELECT 1 FROM claude.documents WHERE doc_id = p_doc_id) THEN
    RAISE EXCEPTION 'Document not found: %', p_doc_id;
  END IF;

  -- Validate project exists
  IF NOT EXISTS (SELECT 1 FROM claude.projects WHERE project_id = p_project_id) THEN
    RAISE EXCEPTION 'Project not found: %', p_project_id;
  END IF;

  -- Check if link already exists
  IF EXISTS (
    SELECT 1 FROM claude.document_projects
    WHERE doc_id = p_doc_id AND project_id = p_project_id
  ) THEN
    RAISE EXCEPTION 'Link already exists between document % and project %', p_doc_id, p_project_id;
  END IF;

  -- If setting as primary, check for existing primary
  IF p_is_primary = true THEN
    SELECT COUNT(*) INTO v_existing_primary_count
    FROM claude.document_projects
    WHERE doc_id = p_doc_id AND is_primary = true;

    IF v_existing_primary_count > 0 THEN
      RAISE NOTICE 'Document already has % primary project link(s). Clearing them to set new primary.', v_existing_primary_count;

      -- Clear existing primary flags
      UPDATE claude.document_projects
      SET is_primary = false
      WHERE doc_id = p_doc_id AND is_primary = true;
    END IF;
  END IF;

  -- Insert link
  INSERT INTO claude.document_projects (
    document_project_id,
    doc_id,
    project_id,
    is_primary,
    linked_by,
    linked_at
  ) VALUES (
    uuid_generate_v4(),
    p_doc_id,
    p_project_id,
    p_is_primary,
    p_linked_by,
    now()
  ) RETURNING document_project_id INTO v_document_project_id;

  RETURN v_document_project_id;
END;
$$;
```

### Usage Example

```sql
-- Link document as primary to project
SELECT claude.link_document_to_project(
  p_doc_id := 'd1e2f3a4-b5c6-7890-defg-1234567890cd'::uuid,
  p_project_id := 'a1b2c3d4-e5f6-7890-abcd-ef1234567890'::uuid,
  p_is_primary := true,
  p_linked_by := 'claude-code-unified'
);

-- Link document as secondary to another project
SELECT claude.link_document_to_project(
  p_doc_id := 'd1e2f3a4-b5c6-7890-defg-1234567890cd'::uuid,
  p_project_id := 'b2c3d4e5-f6a7-8901-bcde-f12345678901'::uuid,
  p_is_primary := false,
  p_linked_by := 'claude-pm-agent'
);
```

---

## Utility Views for Workflow Tools

### View: Feedback with Comments Count

```sql
CREATE OR REPLACE VIEW claude.feedback_with_stats AS
SELECT
  f.feedback_id,
  f.project_id,
  p.project_name,
  f.feedback_type,
  f.description,
  f.status,
  f.priority,
  f.assigned_to,
  f.created_at,
  f.updated_at,
  f.resolved_at,
  f.notes,
  COUNT(DISTINCT fc.id) AS comment_count,
  COUNT(DISTINCT fs.id) AS screenshot_count,
  CASE
    WHEN f.status IN ('fixed', 'wont_fix') THEN
      EXTRACT(EPOCH FROM (f.resolved_at - f.created_at)) / 3600.0
    ELSE
      EXTRACT(EPOCH FROM (now() - f.created_at)) / 3600.0
  END AS age_hours
FROM claude.feedback f
LEFT JOIN claude.projects p ON f.project_id = p.project_id
LEFT JOIN claude.feedback_comments fc ON f.feedback_id = fc.feedback_id
LEFT JOIN claude.feedback_screenshots fs ON f.feedback_id = fs.feedback_id
GROUP BY
  f.feedback_id, f.project_id, p.project_name, f.feedback_type,
  f.description, f.status, f.priority, f.assigned_to,
  f.created_at, f.updated_at, f.resolved_at, f.notes;
```

### View: Documents with Project Links

```sql
CREATE OR REPLACE VIEW claude.documents_with_projects AS
SELECT
  d.doc_id,
  d.doc_type,
  d.doc_title,
  d.file_path,
  d.version,
  d.status,
  d.is_core,
  d.is_archived,
  d.created_at,
  d.updated_at,
  ARRAY_AGG(DISTINCT dp.project_id) FILTER (WHERE dp.project_id IS NOT NULL) AS project_ids,
  ARRAY_AGG(DISTINCT p.project_name) FILTER (WHERE p.project_name IS NOT NULL) AS project_names,
  (SELECT dp2.project_id FROM claude.document_projects dp2 WHERE dp2.doc_id = d.doc_id AND dp2.is_primary = true LIMIT 1) AS primary_project_id,
  (SELECT p2.project_name FROM claude.document_projects dp3 JOIN claude.projects p2 ON dp3.project_id = p2.project_id WHERE dp3.doc_id = d.doc_id AND dp3.is_primary = true LIMIT 1) AS primary_project_name
FROM claude.documents d
LEFT JOIN claude.document_projects dp ON d.doc_id = dp.doc_id
LEFT JOIN claude.projects p ON dp.project_id = p.project_id
GROUP BY d.doc_id;
```

### View: Open Feedback Summary by Project

```sql
CREATE OR REPLACE VIEW claude.open_feedback_summary AS
SELECT
  p.project_id,
  p.project_name,
  COUNT(*) FILTER (WHERE f.status = 'new') AS new_count,
  COUNT(*) FILTER (WHERE f.feedback_type = 'bug' AND f.status = 'new') AS open_bugs,
  COUNT(*) FILTER (WHERE f.feedback_type = 'design' AND f.status = 'new') AS open_design,
  COUNT(*) FILTER (WHERE f.feedback_type = 'question' AND f.status = 'new') AS open_questions,
  COUNT(*) FILTER (WHERE f.feedback_type = 'change' AND f.status = 'new') AS open_changes,
  COUNT(*) FILTER (WHERE f.priority = 'high' AND f.status = 'new') AS high_priority_count,
  MAX(f.created_at) AS most_recent_feedback,
  MIN(f.created_at) FILTER (WHERE f.status = 'new') AS oldest_open_feedback
FROM claude.projects p
LEFT JOIN claude.feedback f ON p.project_id = f.project_id
GROUP BY p.project_id, p.project_name;
```

---

## Database Constraints to Add

### Feedback Domain Constraints

```sql
-- Ensure critical fields are not null
ALTER TABLE claude.feedback
  ALTER COLUMN project_id SET NOT NULL,
  ALTER COLUMN feedback_type SET NOT NULL,
  ALTER COLUMN description SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN priority SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN created_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET NOT NULL,
  ALTER COLUMN updated_at SET DEFAULT now();

-- Add check constraints for valid values
ALTER TABLE claude.feedback
  ADD CONSTRAINT check_feedback_type
    CHECK (feedback_type IN ('bug', 'design', 'question', 'change')),
  ADD CONSTRAINT check_status
    CHECK (status IN ('new', 'in_progress', 'fixed', 'wont_fix')),
  ADD CONSTRAINT check_priority
    CHECK (priority IN ('high', 'medium', 'low')),
  ADD CONSTRAINT check_description_length
    CHECK (LENGTH(TRIM(description)) >= 10),
  ADD CONSTRAINT check_resolved_at_with_status
    CHECK (
      (status IN ('fixed', 'wont_fix') AND resolved_at IS NOT NULL) OR
      (status NOT IN ('fixed', 'wont_fix') AND resolved_at IS NULL)
    );

-- Feedback comments constraints
ALTER TABLE claude.feedback_comments
  ALTER COLUMN feedback_id SET NOT NULL,
  ALTER COLUMN author SET NOT NULL,
  ALTER COLUMN message SET NOT NULL,
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN created_at SET DEFAULT now(),
  ADD CONSTRAINT check_message_length
    CHECK (LENGTH(TRIM(message)) >= 5);

-- Feedback screenshots constraints
ALTER TABLE claude.feedback_screenshots
  ALTER COLUMN feedback_id SET NOT NULL,
  ALTER COLUMN file_path SET NOT NULL,
  ALTER COLUMN uploaded_at SET NOT NULL,
  ALTER COLUMN uploaded_at SET DEFAULT now();
```

### Documentation Domain Constraints

```sql
-- Ensure critical fields are not null
ALTER TABLE claude.documents
  ALTER COLUMN doc_type SET NOT NULL,
  ALTER COLUMN doc_title SET NOT NULL,
  ALTER COLUMN file_path SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN status SET DEFAULT 'ACTIVE',
  ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN created_at SET DEFAULT now(),
  ALTER COLUMN updated_at SET NOT NULL,
  ALTER COLUMN updated_at SET DEFAULT now();

-- Add check constraints
ALTER TABLE claude.documents
  ADD CONSTRAINT check_doc_type
    CHECK (doc_type IN (
      'ADR', 'API', 'ARCHITECTURE', 'ARCHIVE', 'CLAUDE_CONFIG',
      'COMPLETION_REPORT', 'GUIDE', 'MIGRATION', 'OTHER', 'README',
      'REFERENCE', 'SESSION_NOTE', 'SOP', 'SPEC', 'TEST_DOC', 'TROUBLESHOOTING'
    )),
  ADD CONSTRAINT check_status
    CHECK (status IN ('ACTIVE', 'ARCHIVED')),
  ADD CONSTRAINT check_title_length
    CHECK (LENGTH(TRIM(doc_title)) >= 5),
  ADD CONSTRAINT check_archive_consistency
    CHECK (
      (status = 'ARCHIVED' AND is_archived = true) OR
      (status != 'ARCHIVED' AND is_archived = false)
    ),
  ADD CONSTRAINT check_archived_timestamp
    CHECK (
      (is_archived = true AND archived_at IS NOT NULL) OR
      (is_archived = false)
    ),
  ADD CONSTRAINT check_core_reason
    CHECK (
      (is_core = true AND core_reason IS NOT NULL AND LENGTH(TRIM(core_reason)) >= 10) OR
      (is_core = false)
    );

-- Document-project links constraints (already mostly in place)
-- Just ensure consistency
ALTER TABLE claude.document_projects
  ADD CONSTRAINT check_only_one_primary_per_document
    EXCLUDE USING btree (doc_id WITH =) WHERE (is_primary = true);
```

---

## Installation Script

```sql
-- Install all workflow functions
\i create_feedback.sql
\i add_feedback_comment.sql
\i resolve_feedback.sql
\i register_document.sql
\i link_document_to_project.sql

-- Create utility views
\i feedback_with_stats_view.sql
\i documents_with_projects_view.sql
\i open_feedback_summary_view.sql

-- Add constraints (run with caution - will fail if data doesn't conform)
-- Recommend cleaning data first
\i add_feedback_constraints.sql
\i add_document_constraints.sql

-- Grant permissions
GRANT EXECUTE ON FUNCTION claude.create_feedback TO claude_agents;
GRANT EXECUTE ON FUNCTION claude.add_feedback_comment TO claude_agents;
GRANT EXECUTE ON FUNCTION claude.resolve_feedback TO claude_agents;
GRANT EXECUTE ON FUNCTION claude.register_document TO claude_agents;
GRANT EXECUTE ON FUNCTION claude.link_document_to_project TO claude_agents;

GRANT SELECT ON claude.feedback_with_stats TO claude_agents;
GRANT SELECT ON claude.documents_with_projects TO claude_agents;
GRANT SELECT ON claude.open_feedback_summary TO claude_agents;
```

---

**Document Version**: 1.0
**Last Updated**: 2025-12-04
**Next Review**: 2026-01-04
**Related**: DATA_GATEWAY_DOMAIN_ANALYSIS.md
