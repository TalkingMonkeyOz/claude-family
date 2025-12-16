# Feature Deep Dive - December 2025

**Purpose**: Detailed low-level design for each feature to ensure implementability
**Status**: IN PROGRESS
**Author**: claude-opus-4-5 + John

---

## Feature 1: Stop Hook Enforcer (C4)

### 1.1 Problem Statement
"I'LL FORGET TO USE IT SO WILL YOU" - Manual slash commands and checks get forgotten during work.

### 1.2 Current State
- **stop_hook_enforcer.py**: Does NOT exist
- **hooks.json**: No Stop hook configured
- Manual reminders via SessionEnd prompt (easily ignored)

### 1.3 Proposed Solution
Counter-based automatic reminders triggered on Stop hook (runs after every Claude response).

### 1.4 Technical Design

**File**: `scripts/stop_hook_enforcer.py`

```python
#!/usr/bin/env python3
"""
Stop Hook Enforcer - Counter-based automatic reminders

Runs after every Claude response. Tracks interaction count and triggers
reminders at specified intervals.

State persisted to: ~/.claude/state/enforcement_state.json
"""

import sys
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
STATE_FILE = Path.home() / ".claude" / "state" / "enforcement_state.json"
INTERVALS = {
    "git_check": 5,          # Every 5 responses
    "inbox_check": 10,       # Every 10 responses
    "claude_md_refresh": 20, # Every 20 responses
}

def load_state() -> dict:
    """Load state from file or return defaults."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "interaction_count": 0,
        "last_git_check": 0,
        "last_inbox_check": 0,
        "last_claude_md_check": 0,
        "code_changes_since_test": 0,
        "files_changed_this_session": [],
        "session_start": datetime.now().isoformat()
    }

def save_state(state: dict):
    """Persist state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def check_git_status() -> tuple[bool, str]:
    """Check if there are uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            return True, f"{len(lines)} uncommitted changes"
        return False, ""
    except Exception:
        return False, ""

def get_reminders(state: dict) -> list[str]:
    """Generate reminders based on current state."""
    reminders = []
    count = state["interaction_count"]

    # Git check reminder
    if count - state["last_git_check"] >= INTERVALS["git_check"]:
        has_changes, msg = check_git_status()
        if has_changes:
            reminders.append(f"💾 Git: {msg}. Consider committing.")
        state["last_git_check"] = count

    # Inbox check reminder
    if count - state["last_inbox_check"] >= INTERVALS["inbox_check"]:
        reminders.append("📬 Run /inbox-check for messages from other Claude instances.")
        state["last_inbox_check"] = count

    # CLAUDE.md refresh reminder
    if count - state["last_claude_md_check"] >= INTERVALS["claude_md_refresh"]:
        reminders.append("📖 Consider re-reading CLAUDE.md to refresh context.")
        state["last_claude_md_check"] = count

    # Test tracking reminder
    if state.get("code_changes_since_test", 0) >= 3:
        reminders.append(f"🧪 {state['code_changes_since_test']} code changes without tests.")

    return reminders

def main():
    """Main entry point."""
    # Load state
    state = load_state()

    # Increment counter
    state["interaction_count"] += 1

    # Get reminders
    reminders = get_reminders(state)

    # Save state
    save_state(state)

    # Output reminders if any
    if reminders:
        output = {
            "systemPrompt": "\n".join([
                "<stop-hook-reminder>",
                "🔔 PERIODIC REMINDERS:",
                *reminders,
                "</stop-hook-reminder>"
            ])
        }
        print(json.dumps(output))
    else:
        print(json.dumps({}))

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 1.5 Hook Configuration

**Add to `.claude/hooks.json`:**
```json
{
  "Stop": [
    {
      "hooks": [
        {
          "type": "command",
          "command": "python \"C:/Projects/claude-family/scripts/stop_hook_enforcer.py\"",
          "timeout": 5,
          "description": "Counter-based periodic reminders"
        }
      ]
    }
  ]
}
```

### 1.6 State File Structure

**Location**: `~/.claude/state/enforcement_state.json`

```json
{
  "interaction_count": 47,
  "last_git_check": 45,
  "last_inbox_check": 40,
  "last_claude_md_check": 40,
  "code_changes_since_test": 3,
  "files_changed_this_session": ["src/api.ts", "src/utils.ts"],
  "session_start": "2025-12-16T10:30:00"
}
```

### 1.7 Testing Checklist
- [ ] Script runs without errors
- [ ] State file created on first run
- [ ] Counter increments each run
- [ ] Git reminder triggers at correct interval
- [ ] Reminders appear in Claude output
- [ ] State persists between runs

### 1.8 Known Limitations
- Stop hook runs AFTER response, so reminder shows on NEXT response
- Git check requires git in PATH
- State file is per-machine, not per-project

---

## Feature 2: Knowledge Auto-Injection (C5)

### 2.1 Problem Statement
161 knowledge entries exist in `claude.knowledge` but are never used because Claude doesn't know to look for them.

### 2.2 Current State
- **process_router.py**: Has standards injection but NO knowledge injection
- **claude.knowledge table**: 161 rows of valuable info
- Knowledge is queried manually via SQL (rare)

### 2.3 Proposed Solution
On UserPromptSubmit, detect topics from user prompt and inject relevant knowledge entries.

### 2.4 Technical Design

**Modify**: `scripts/process_router.py`

Add new function after `build_standards_guidance`:

```python
# Topic to keyword mapping for knowledge retrieval
KNOWLEDGE_TOPICS = {
    "nimbus": ["nimbus", "shift", "schedule", "employment", "employee", "roster", "timesheet"],
    "api": ["api", "odata", "rest", "endpoint", "request", "response", "http", "fetch"],
    "import": ["import", "importer", "loader", "sync", "migration", "etl", "data load"],
    "tax": ["tax", "ato", "tfn", "abn", "bas", "payg", "super", "stp", "payroll"],
    "database": ["database", "postgres", "sql", "query", "schema", "table", "migration"],
    "react": ["react", "component", "hook", "state", "props", "jsx", "tsx", "nextjs"],
    "mcp": ["mcp", "server", "tool", "protocol", "model context"],
    "windows": ["windows", "winforms", "wpf", "flaui", "automation", ".net", "csharp"],
}

def detect_topics(user_prompt: str) -> set:
    """Detect relevant topics from user prompt."""
    prompt_lower = user_prompt.lower()
    detected = set()

    for topic, keywords in KNOWLEDGE_TOPICS.items():
        if any(kw in prompt_lower for kw in keywords):
            detected.add(topic)

    return detected

def get_relevant_knowledge(conn, topics: set, limit: int = 5) -> list:
    """Query knowledge base for relevant entries."""
    if not conn or not topics:
        return []

    # Build keyword list from topics
    all_keywords = []
    for topic in topics:
        all_keywords.extend(KNOWLEDGE_TOPICS.get(topic, []))

    if not all_keywords:
        return []

    cur = conn.cursor()

    # Search in title, description, and tags
    # Using ILIKE for case-insensitive matching
    keyword_conditions = " OR ".join([
        f"(LOWER(title) LIKE '%{kw}%' OR LOWER(description) LIKE '%{kw}%' OR LOWER(tags::text) LIKE '%{kw}%')"
        for kw in all_keywords[:10]  # Limit to avoid huge queries
    ])

    cur.execute(f"""
        SELECT
            knowledge_id,
            title,
            description,
            category,
            tags,
            confidence_level,
            times_applied
        FROM claude.knowledge
        WHERE {keyword_conditions}
        ORDER BY confidence_level DESC, times_applied DESC
        LIMIT %s
    """, (limit,))

    return [dict(row) for row in cur.fetchall()]

def build_knowledge_guidance(knowledge_entries: list) -> str:
    """Build knowledge injection text."""
    if not knowledge_entries:
        return ""

    parts = ["<relevant-knowledge>", f"[RELEVANT KNOWLEDGE RETRIEVED - {len(knowledge_entries)} entries]", ""]

    for entry in knowledge_entries:
        parts.append(f"### {entry['title']}")
        parts.append(f"**Category**: {entry.get('category', 'general')} | **Confidence**: {entry.get('confidence_level', 5)}/10")
        if entry.get('tags'):
            parts.append(f"**Tags**: {', '.join(entry['tags']) if isinstance(entry['tags'], list) else entry['tags']}")
        parts.append("")
        parts.append(entry.get('description', '')[:500])  # Truncate long descriptions
        parts.append("")
        parts.append("---")
        parts.append("")

    parts.append("</relevant-knowledge>")
    return "\n".join(parts)
```

**Integrate into main():**

```python
def main():
    # ... existing code ...

    # NEW: Detect topics and get relevant knowledge
    detected_topics = detect_topics(user_prompt)
    knowledge_entries = get_relevant_knowledge(conn, detected_topics)
    knowledge_guidance = build_knowledge_guidance(knowledge_entries)

    # Build combined guidance (add knowledge to existing)
    guidance_parts = []

    if knowledge_guidance:
        guidance_parts.append(knowledge_guidance)

    if process_guidance_result["guidance_text"]:
        guidance_parts.append(f"<process-guidance>...")

    if standards_guidance:
        guidance_parts.append(f"<standards-guidance>...")
```

### 2.5 Database Requirements

**Table**: `claude.knowledge` (already exists)

Verify columns:
```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'claude' AND table_name = 'knowledge';
```

Expected: knowledge_id, title, description, category, tags, confidence_level, times_applied, etc.

### 2.6 Testing Checklist
- [ ] Topic detection works for each category
- [ ] Knowledge query returns relevant results
- [ ] Knowledge injection appears in Claude context
- [ ] Performance: < 500ms added latency
- [ ] No errors when knowledge table is empty
- [ ] Handles null/missing fields gracefully

### 2.7 Example Output

User prompt: "I need to import shift data from Nimbus API"

Injected:
```xml
<relevant-knowledge>
[RELEVANT KNOWLEDGE RETRIEVED - 3 entries]

### Nimbus API - Shifts Endpoint
**Category**: api | **Confidence**: 8/10
**Tags**: nimbus, shifts, odata

GET /odata/Shifts returns shift records. Key fields: EmployeeId, StartTime, EndTime...

---

### Nimbus OData Quirks
**Category**: gotcha | **Confidence**: 9/10
**Tags**: nimbus, odata, pagination

Nimbus OData requires $top and $skip for pagination. Max 1000 records per request...

---
</relevant-knowledge>
```

---

## Feature 3: Database Integrity Fixes

### 3.1 Problem Statement
15 missing FK constraints identified. Risk of orphaned records.

### 3.2 Current State
- Usage tables (api_usage_data, etc.) have FKs but NO ON DELETE action
- Array columns (related_knowledge) have no validation
- No projects_registry table for consistent project names

### 3.3 SQL Fix Script

**File**: `scripts/sql/db_integrity_fix.sql`

```sql
-- ============================================================
-- DATABASE INTEGRITY FIX SCRIPT
-- Claude Family System Redesign - December 2025
-- ============================================================

-- Run as: psql -U postgres -d ai_company_foundation -f db_integrity_fix.sql

BEGIN;

-- ============================================================
-- PHASE 1: Fix ON DELETE actions for usage tables
-- ============================================================

-- api_usage_data
ALTER TABLE claude_family.api_usage_data
DROP CONSTRAINT IF EXISTS api_usage_data_identity_id_fkey;

ALTER TABLE claude_family.api_usage_data
ADD CONSTRAINT api_usage_data_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- api_cost_data
ALTER TABLE claude_family.api_cost_data
DROP CONSTRAINT IF EXISTS api_cost_data_identity_id_fkey;

ALTER TABLE claude_family.api_cost_data
ADD CONSTRAINT api_cost_data_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- usage_summary
ALTER TABLE claude_family.usage_summary
DROP CONSTRAINT IF EXISTS usage_summary_identity_id_fkey;

ALTER TABLE claude_family.usage_summary
ADD CONSTRAINT usage_summary_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- budget_alerts (two FK columns)
ALTER TABLE claude_family.budget_alerts
DROP CONSTRAINT IF EXISTS budget_alerts_identity_id_fkey;

ALTER TABLE claude_family.budget_alerts
ADD CONSTRAINT budget_alerts_identity_id_fkey
FOREIGN KEY (identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

ALTER TABLE claude_family.budget_alerts
DROP CONSTRAINT IF EXISTS budget_alerts_created_by_identity_id_fkey;

ALTER TABLE claude_family.budget_alerts
ADD CONSTRAINT budget_alerts_created_by_identity_id_fkey
FOREIGN KEY (created_by_identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- usage_sync_status
ALTER TABLE claude_family.usage_sync_status
DROP CONSTRAINT IF EXISTS usage_sync_status_synced_by_identity_id_fkey;

ALTER TABLE claude_family.usage_sync_status
ADD CONSTRAINT usage_sync_status_synced_by_identity_id_fkey
FOREIGN KEY (synced_by_identity_id) REFERENCES claude_family.identities(identity_id)
ON DELETE SET NULL;

-- ============================================================
-- PHASE 2: Add CHECK constraints for enum-like columns
-- ============================================================

-- shared_knowledge.knowledge_type
ALTER TABLE claude_family.shared_knowledge
DROP CONSTRAINT IF EXISTS knowledge_type_check;

ALTER TABLE claude_family.shared_knowledge
ADD CONSTRAINT knowledge_type_check CHECK (
    knowledge_type IN (
        'pattern', 'gotcha', 'bug-fix', 'architecture', 'technique',
        'best-practice', 'troubleshooting', 'process', 'configuration',
        'mcp-tool', 'mcp-server'
    )
);

-- startup_context.context_type (if exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables
               WHERE table_schema = 'claude_family' AND table_name = 'startup_context') THEN
        ALTER TABLE claude_family.startup_context
        DROP CONSTRAINT IF EXISTS context_type_check;

        ALTER TABLE claude_family.startup_context
        ADD CONSTRAINT context_type_check CHECK (
            context_type IN ('constraint', 'preference', 'reminder', 'warning')
        );
    END IF;
END $$;

-- api_usage_data.bucket_width (if column exists)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.columns
               WHERE table_schema = 'claude_family'
               AND table_name = 'api_usage_data'
               AND column_name = 'bucket_width') THEN
        ALTER TABLE claude_family.api_usage_data
        DROP CONSTRAINT IF EXISTS bucket_width_check;

        ALTER TABLE claude_family.api_usage_data
        ADD CONSTRAINT bucket_width_check CHECK (
            bucket_width IN ('1m', '1h', '1d')
        );
    END IF;
END $$;

-- ============================================================
-- PHASE 3: Create projects_registry table
-- ============================================================

CREATE TABLE IF NOT EXISTS claude_family.projects_registry (
    project_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_name VARCHAR(255) UNIQUE NOT NULL,
    project_schema VARCHAR(100),
    project_type VARCHAR(50) CHECK (project_type IN ('work', 'internal', 'research', 'archived')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed with known projects
INSERT INTO claude_family.projects_registry (project_name, project_schema, project_type, is_active)
VALUES
    ('claude-family', 'claude', 'internal', true),
    ('mission-control-web', 'claude', 'internal', true),
    ('nimbus-user-loader', 'nimbus_context', 'work', true),
    ('nimbus-import', 'nimbus_context', 'work', true),
    ('ATO-Tax-Agent', 'public', 'work', true)
ON CONFLICT (project_name) DO NOTHING;

-- ============================================================
-- PHASE 4: Create knowledge_relations junction table
-- ============================================================

CREATE TABLE IF NOT EXISTS claude_family.knowledge_relations (
    relation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_knowledge_id UUID NOT NULL,
    related_knowledge_id UUID NOT NULL,
    relation_type VARCHAR(50) CHECK (relation_type IN ('builds_on', 'contradicts', 'validates', 'related')),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_parent_knowledge
        FOREIGN KEY (parent_knowledge_id)
        REFERENCES claude_family.shared_knowledge(knowledge_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_related_knowledge
        FOREIGN KEY (related_knowledge_id)
        REFERENCES claude_family.shared_knowledge(knowledge_id)
        ON DELETE CASCADE,

    CONSTRAINT no_self_reference
        CHECK (parent_knowledge_id != related_knowledge_id),

    UNIQUE(parent_knowledge_id, related_knowledge_id)
);

-- ============================================================
-- PHASE 5: Create stored_tests table (for TDD feature)
-- ============================================================

CREATE TABLE IF NOT EXISTS claude.stored_tests (
    test_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES claude.projects(project_id) ON DELETE CASCADE,
    test_name VARCHAR(255) NOT NULL,
    test_type VARCHAR(50) CHECK (test_type IN ('unit', 'integration', 'e2e', 'process', 'workflow')),
    test_definition JSONB NOT NULL,
    last_run_at TIMESTAMPTZ,
    last_result VARCHAR(20) CHECK (last_result IN ('pass', 'fail', 'skip', 'error')),
    run_count INTEGER DEFAULT 0,
    is_archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by_identity_id UUID REFERENCES claude_family.identities(identity_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_stored_tests_project ON claude.stored_tests(project_id);
CREATE INDEX IF NOT EXISTS idx_stored_tests_type ON claude.stored_tests(test_type);

-- ============================================================
-- VERIFICATION QUERIES
-- ============================================================

-- List all FK constraints with their actions
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table,
    rc.delete_rule
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu
    ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu
    ON tc.constraint_name = ccu.constraint_name
JOIN information_schema.referential_constraints rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.table_schema = 'claude_family'
    AND tc.constraint_type = 'FOREIGN KEY'
ORDER BY tc.table_name;

-- List all CHECK constraints
SELECT
    table_name,
    constraint_name,
    check_clause
FROM information_schema.check_constraints
WHERE constraint_schema = 'claude_family'
ORDER BY table_name;

COMMIT;

-- ============================================================
-- POST-COMMIT: Show summary
-- ============================================================

\echo ''
\echo '=== DATABASE INTEGRITY FIX COMPLETE ==='
\echo ''
\echo 'Fixed:'
\echo '  - 6 FK constraints now have ON DELETE SET NULL'
\echo '  - 3 CHECK constraints added for enum columns'
\echo '  - projects_registry table created'
\echo '  - knowledge_relations junction table created'
\echo '  - stored_tests table created'
\echo ''
```

### 3.4 Testing Checklist
- [ ] Script runs without errors
- [ ] All FK constraints have ON DELETE actions
- [ ] CHECK constraints reject invalid values
- [ ] projects_registry populated with seed data
- [ ] Deleting identity sets FKs to NULL (not cascade delete)

---

## Feature 4: TDD Enforcement (/test-first)

### 4.1 Problem Statement
0% test coverage. Code ships without tests.

### 4.2 Current State
- No /test-first command
- PreCommit hook exists but doesn't check for tests
- stored_tests table doesn't exist

### 4.3 Proposed Solution
1. Create /test-first slash command
2. Enhance PreCommit hook to check for test files
3. Create stored_tests table (in DB integrity script above)

### 4.4 Slash Command

**File**: `.claude/commands/test-first.md`

```markdown
# Test-First Development Mode

You are now in TDD (Test-Driven Development) mode for: $ARGUMENTS

## MANDATORY STEPS

### Step 1: Write Tests FIRST
Before writing ANY implementation code:
- Create test file in appropriate location
- Write tests for:
  - [ ] Happy path (valid inputs)
  - [ ] Edge cases (nulls, empty, boundaries)
  - [ ] Error cases (invalid inputs, failures)
  - [ ] Integration points (if applicable)

### Step 2: Run Tests - Confirm Failure
- Execute the test suite
- VERIFY tests fail (they should - no implementation yet)
- If tests pass, they're not testing the new functionality

### Step 3: Write Minimal Implementation
- Write ONLY enough code to make tests pass
- No extra features
- No premature optimization
- No "nice to haves"

### Step 4: Run Tests - Confirm Pass
- Execute the test suite again
- ALL tests must pass
- If any fail, fix implementation (not tests)

### Step 5: Refactor (Optional)
- Clean up code while keeping tests green
- Extract common patterns
- Improve readability
- Run tests after each change

## Test Patterns by Type

### Unit Test (Function/Class)
```typescript
describe('functionName', () => {
  it('should handle valid input', () => {});
  it('should throw on null input', () => {});
  it('should return default for empty', () => {});
});
```

### API Test (Endpoint)
```typescript
describe('POST /api/endpoint', () => {
  it('should return 200 with valid body', () => {});
  it('should return 400 with missing fields', () => {});
  it('should return 401 without auth', () => {});
});
```

### Component Test (React)
```typescript
describe('ComponentName', () => {
  it('should render correctly', () => {});
  it('should handle click events', () => {});
  it('should show loading state', () => {});
  it('should show error state', () => {});
});
```

## Remember
- Tests are documentation
- Tests prevent regression
- Tests enable refactoring
- Write tests YOU would want to maintain
```

### 4.5 PreCommit Enhancement

**Modify**: `scripts/pre_commit_check.py`

Add after existing checks:

```python
def check_test_coverage(staged_files: list) -> tuple[bool, str]:
    """Check if code changes include corresponding tests."""
    code_extensions = {'.py', '.ts', '.tsx', '.js', '.jsx'}
    test_patterns = ['test', 'spec', '__tests__']

    code_files = [f for f in staged_files
                  if any(f.endswith(ext) for ext in code_extensions)
                  and not any(p in f.lower() for p in test_patterns)]

    test_files = [f for f in staged_files
                  if any(p in f.lower() for p in test_patterns)]

    if code_files and not test_files:
        return False, f"Code changes ({len(code_files)} files) without tests. Use /test-first or add tests."

    return True, f"OK: {len(code_files)} code files, {len(test_files)} test files"
```

### 4.6 Testing Checklist
- [ ] /test-first command loads correctly
- [ ] PreCommit blocks commits without tests
- [ ] stored_tests table accepts entries
- [ ] Clear guidance provided in command output

---

## Feature 5: Session Context Persistence

### 5.1 Problem Statement
Context is lost between sessions. Claude Desktop loses context quickly.

### 5.2 Current State
- session_startup_hook.py exists (loads context)
- SessionEnd hook prompts for /session-end
- TODO_NEXT_SESSION.md used as backup
- No automatic session state persistence

### 5.3 Proposed Solution
Enhance session hooks to automatically persist and restore context.

### 5.4 Session State Structure

**Database**: `claude.sessions` table (exists)
**New Column**: `session_state JSONB`

```json
{
  "work_focus": "Implementing feature X",
  "active_files": [
    "/src/components/Feature.tsx",
    "/src/api/feature.ts"
  ],
  "todo_list": [
    {"content": "Write tests", "status": "pending"},
    {"content": "Implement handler", "status": "completed"}
  ],
  "key_decisions": [
    "Using React Query for data fetching",
    "Storing state in PostgreSQL, not memory"
  ],
  "blockers": [],
  "next_steps": [
    "Complete API integration",
    "Add error handling"
  ]
}
```

### 5.5 Hook Modifications

**SessionStart**: Load previous session state
**SessionEnd**: Save current session state

### 5.6 Testing Checklist
- [ ] Session state saves on /session-end
- [ ] Session state loads on startup
- [ ] TODO list persists between sessions
- [ ] Key decisions carry over
- [ ] Works when database unavailable (graceful fallback)

---

## Feature 6: KNOWLEDGE_INDEX.md

### 6.1 Problem Statement
Claude doesn't know what features/commands/SOPs exist.

### 6.2 Current State
- CLAUDE.md has some pointers
- 100+ docs in docs/ folder
- No master index

### 6.3 Proposed Solution
Create KNOWLEDGE_INDEX.md as master resource list that CLAUDE.md points to.

### 6.4 Document Structure

**File**: `docs/KNOWLEDGE_INDEX.md`

```markdown
# Claude Family Knowledge Index

**Purpose**: Master reference of all available resources
**Updated**: [auto-generated timestamp]

---

## Quick Navigation

| I need to... | Use this |
|--------------|----------|
| Start a session | SessionStart hook (automatic) |
| End a session | /session-end command |
| Create a project | /project-init command |
| Report a bug | /feedback-create type=bug |
| Add knowledge | INSERT INTO claude.knowledge |
| Check messages | /inbox-check command |

---

## Slash Commands

| Command | Purpose | Location |
|---------|---------|----------|
| /session-commit | Commit with message | .claude/commands/session-commit.md |
| /feedback-create | Create feedback entry | .claude/commands/feedback-create.md |
| /feedback-list | List feedback items | .claude/commands/feedback-list.md |
| /feedback-check | Check feedback status | .claude/commands/feedback-check.md |
| /project-init | Initialize new project | .claude/commands/project-init.md |
| /phase-advance | Move project to next phase | .claude/commands/phase-advance.md |
| /check-compliance | Run compliance audit | .claude/commands/check-compliance.md |
| /review-data | Review data quality | .claude/commands/review-data.md |
| /review-docs | Review doc quality | .claude/commands/review-docs.md |
| /retrofit-project | Add governance to existing | .claude/commands/retrofit-project.md |

---

## Standard Operating Procedures (SOPs)

| SOP | Purpose | Location |
|-----|---------|----------|
| SOP-001 | Knowledge Docs & Tasks | docs/sops/SOP-001-KNOWLEDGE-DOCS-TASKS.md |
| SOP-002 | Build Task Lifecycle | docs/sops/SOP-002-BUILD-TASK-LIFECYCLE.md |
| SOP-003 | Document Classification | docs/sops/SOP-003-DOCUMENT-CLASSIFICATION.md |
| SOP-004 | Project Initialization | docs/sops/SOP-004-PROJECT-INITIALIZATION.md |
| SOP-005 | Auto-Reviewers | docs/sops/SOP-005-AUTO-REVIEWERS.md |
| SOP-006 | Testing Process | docs/sops/SOP-006-TESTING-PROCESS.md |
| SOP-007 | Slash Command Management | docs/sops/SOP-007-SLASH-COMMAND-MANAGEMENT.md |

---

## Standards Documents

| Standard | Purpose | Location |
|----------|---------|----------|
| API Standards | REST patterns, errors | docs/standards/API_STANDARDS.md |
| Database Standards | Schema design, queries | docs/standards/DATABASE_STANDARDS.md |
| Development Standards | Coding conventions | docs/standards/DEVELOPMENT_STANDARDS.md |
| UI Component Standards | Tables, forms, states | docs/standards/UI_COMPONENT_STANDARDS.md |
| Workflow Standards | Dev lifecycle, reviews | docs/standards/WORKFLOW_STANDARDS.md |

---

## Database Tables (Key)

| Table | Purpose | Schema |
|-------|---------|--------|
| sessions | Track Claude sessions | claude |
| projects | Project registry | claude |
| features | Feature tracking | claude |
| build_tasks | Task tracking | claude |
| feedback | Ideas, bugs, questions | claude |
| knowledge | Shared knowledge | claude |
| documents | Document index | claude |
| process_registry | Workflow definitions | claude |
| identities | Claude identities | claude_family |
| shared_knowledge | Cross-project knowledge | claude_family |

---

## MCP Servers Available

| Server | Purpose |
|--------|---------|
| postgres | Database access |
| memory | Knowledge graph |
| filesystem | File operations |
| orchestrator | Agent spawning, messaging |
| sequential-thinking | Complex problem solving |
| tool-search | On-demand tool discovery |

---

## Agent Types (Orchestrator)

| Agent | Model | Use Case |
|-------|-------|----------|
| coder-haiku | Haiku | General coding |
| python-coder-haiku | Haiku | Python specific |
| reviewer-sonnet | Sonnet | Code review |
| web-tester-haiku | Haiku | E2E testing |
| architect-opus | Opus | Planning, design |
| researcher-opus | Opus | Research tasks |
| ux-tax-screen-analyzer | Haiku | ATO screen analysis |

---

## Key Files

| File | Purpose |
|------|---------|
| CLAUDE.md / claude.md | Project constitution |
| ARCHITECTURE.md | System design |
| PROBLEM_STATEMENT.md | Problem definition |
| .claude/hooks.json | Hook configuration |
| .claude/commands/ | Slash commands |

---

**Auto-updated by**: scripts/update_knowledge_index.py
**Last updated**: {timestamp}
```

### 6.5 Testing Checklist
- [ ] All commands listed accurately
- [ ] All SOPs listed accurately
- [ ] Links work (relative paths)
- [ ] CLAUDE.md points to this file
- [ ] Easy to find what you need

---

## Implementation Priority

| Priority | Feature | Effort | Impact |
|----------|---------|--------|--------|
| 1 | Stop Hook Enforcer | 2h | HIGH - solves "forget to use" |
| 2 | Database Integrity | 1h | HIGH - prevents data corruption |
| 3 | KNOWLEDGE_INDEX.md | 1h | HIGH - enables discovery |
| 4 | Knowledge Auto-Injection | 3h | MEDIUM - uses existing data |
| 5 | TDD Command | 1h | MEDIUM - encourages testing |
| 6 | Session Persistence | 2h | MEDIUM - improves continuity |

---

**Version**: 1.0
**Created**: 2025-12-16
**Location**: /home/user/claude-family/docs/FEATURE_DEEP_DIVE_2025-12.md
