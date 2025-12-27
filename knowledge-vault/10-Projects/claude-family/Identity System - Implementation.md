---
projects:
  - claude-family
tags:
  - identity
  - implementation
  - migration
synced: false
---

# Identity System - Implementation

**Status**: ✅ COMPLETED (2025-12-26)
**See Also**: [[Identity System - Overview]] - Concept and benefits

This document describes the technical implementation and migration plan for identity-per-project.

---

## Database Schema Changes

### 1. Add default_identity_id to projects

```sql
ALTER TABLE claude.projects
ADD COLUMN default_identity_id uuid;

ALTER TABLE claude.projects
ADD CONSTRAINT projects_identity_fkey
FOREIGN KEY (default_identity_id) REFERENCES claude.identities(identity_id);
```

### 2. Add Foreign Key Constraints

```sql
-- Sessions must reference valid identity
ALTER TABLE claude.sessions
ADD CONSTRAINT sessions_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude.identities(identity_id);

-- Workspaces track who added them
ALTER TABLE claude.workspaces
ADD CONSTRAINT workspaces_identity_fkey
FOREIGN KEY (added_by_identity_id) REFERENCES claude.identities(identity_id);
```

---

## Session Hook Implementation

**File**: `scripts/session_startup_hook_enhanced.py`

### Identity Resolution Function

```python
def determine_identity(project_name: str) -> str:
    """Determine identity in priority order."""

    # 1. Try CLAUDE.md frontmatter
    claude_md_path = os.path.join(os.getcwd(), 'CLAUDE.md')
    if os.path.exists(claude_md_path):
        with open(claude_md_path) as f:
            content = f.read()
            if content.startswith('---'):
                yaml_match = re.search(r'---\n(.*?)\n---', content, re.DOTALL)
                if yaml_match:
                    frontmatter = yaml.safe_load(yaml_match.group(1))
                    if 'identity_id' in frontmatter:
                        return frontmatter['identity_id']

    # 2. Try projects.default_identity_id
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT default_identity_id
            FROM claude.projects
            WHERE project_name = %s
            AND default_identity_id IS NOT NULL
        """, (project_name,))
        row = cursor.fetchone()
        if row:
            return str(row[0])

    # 3. Fallback
    return DEFAULT_IDENTITY_ID
```

### Environment Variable Exports

```python
# Export for downstream tools (MCP loggers, etc.)
os.environ['CLAUDE_SESSION_ID'] = str(session_id)
os.environ['CLAUDE_IDENTITY_ID'] = str(identity_id)
os.environ['CLAUDE_PROJECT_NAME'] = project_name
```

---

## Migration Plan (Completed)

### Phase 1: Create Project Identities ✅

**(Implementation SQL truncated - see git history for full migration)**

### Phase 2: Link Projects to Identities ✅
**(Implementation details truncated - see git history)**

### Phase 3: Update CLAUDE.md Files ✅

Add identity to each project's CLAUDE.md frontmatter:

```markdown
---
project_id: 20b5627c-e72c-4501-8537-95b559731b59
identity_id: ff32276f-9d05-4a18-b092-31b54c82fff9
---

# Project Name
```

### Phase 4: Backfill NULL Identities ✅

```sql
-- Update sessions with NULL identity to use claude-code-unified
UPDATE claude.sessions
SET identity_id = 'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid
WHERE identity_id IS NULL;

-- Result: 39 sessions backfilled
```

---

## Testing the Implementation

### Test 1: Verify Identity from CLAUDE.md

```bash
# 1. Add identity_id to CLAUDE.md
cat <<EOF > CLAUDE.md
---
identity_id: ff32276f-9d05-4a18-b092-31b54c82fff9
---
# Test Project
EOF

# 2. Start Claude
claude

# 3. Check session was created with correct identity
psql -d ai_company_foundation -c "
SELECT session_id::text, identity_id::text, project_name
FROM claude.sessions
ORDER BY session_start DESC LIMIT 1;
"
```

### Test 2: Verify Fallback to projects.default_identity_id

```sql
-- 1. Set default identity for project
UPDATE claude.projects
SET default_identity_id = 'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid
WHERE project_name = 'test-project';

-- 2. Start Claude (without CLAUDE.md identity field)
-- 3. Verify session uses project's default_identity_id
```

### Test 3: Verify Environment Variables

```bash
# In session, check environment
echo $CLAUDE_IDENTITY_ID
echo $CLAUDE_SESSION_ID

# Should match database
psql -d ai_company_foundation -c "
SELECT session_id::text, identity_id::text
FROM claude.sessions
WHERE session_id = '$CLAUDE_SESSION_ID'::uuid;
"
```

---

## Verification Queries

### Check All Projects Have Identities

```sql
SELECT
    p.project_name,
    p.status,
    i.identity_name
FROM claude.projects p
LEFT JOIN claude.identities i ON p.default_identity_id = i.identity_id
WHERE p.status = 'active'
ORDER BY p.project_name;
```

Expected: All active projects have identity_name populated.

### Check Session Identity Coverage

```sql
SELECT
    COUNT(*) FILTER (WHERE identity_id IS NULL) as missing,
    COUNT(*) as total,
    ROUND(100.0 * COUNT(*) FILTER (WHERE identity_id IS NOT NULL) / COUNT(*), 1) as coverage_pct
FROM claude.sessions;
```

Expected: coverage_pct = 100%

### Check Identity Distribution

```sql
SELECT
    i.identity_name,
    COUNT(*) as sessions,
    MIN(s.session_start) as first_session,
    MAX(s.session_start) as last_session
FROM claude.sessions s
JOIN claude.identities i ON s.identity_id = i.identity_id
GROUP BY i.identity_name
ORDER BY sessions DESC;
```

---

## Launcher Integration (Future)

**File**: `ClaudeLauncherWinForms\Services\LaunchService.cs`

When launcher is updated, it should:

```csharp
// 1. Look up project in workspaces table
var workspace = GetWorkspace(projectName);

// 2. Look up project identity
var project = GetProject(workspace.project_name);
var identityId = project?.default_identity_id ?? DEFAULT_IDENTITY_ID;

// 3. Set environment variable BEFORE starting Claude
Environment.SetEnvironmentVariable("CLAUDE_IDENTITY_ID", identityId.ToString());

// 4. Launch Claude
Process.Start("wt.exe", $"-d \"{projectPath}\" claude");
```

**Current Status**: Not implemented yet - identity resolution happens in session hook.

---

## Troubleshooting

### Issue: Sessions Still Using claude-code-unified

**Check**: Does CLAUDE.md have identity_id?

```bash
grep -A 5 "^---$" CLAUDE.md
```

**Check**: Does project have default_identity_id?

```sql
SELECT project_name, default_identity_id
FROM claude.projects
WHERE project_name = 'your-project';
```

### Issue: Identity ID Not in Environment

**Check**: Session hook exports?

```bash
echo $CLAUDE_IDENTITY_ID
echo $CLAUDE_SESSION_ID
```

**Fix**: Restart Claude session - hook runs on startup.

---

**Version**: 1.0 (Implementation)
**Created**: 2025-12-27
**Updated**: 2025-12-27
**Location**: knowledge-vault/10-Projects/claude-family/Identity System - Implementation.md
