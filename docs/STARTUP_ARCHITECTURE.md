# Claude Family Startup Architecture

**Version**: 2.0
**Last Updated**: 2025-11-04
**Status**: ✅ Operational

---

## Overview

The Claude Family uses a **centralized startup system** that loads identity, context, and knowledge from PostgreSQL at the beginning of each session. This ensures consistent behavior across all Claude instances and eliminates knowledge duplication.

**Key Principle**: Every Claude should start with full awareness of:
- Who they are (identity and role)
- What they know (shared knowledge across all projects)
- What they've done recently (session history)
- What other Claudes have done (family activity)
- Where they are (current project context)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   Claude Instance Startup                        │
│                                                                   │
│  1. User triggers: /session-start                                │
│  2. Runs: C:\claude\shared\scripts\load_claude_startup_context.py│
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                PostgreSQL: ai_company_foundation                  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  claude_family Schema                                    │   │
│  │                                                           │   │
│  │  • identities          (who am I?)                       │   │
│  │  • shared_knowledge    (what patterns/techniques exist?) │   │
│  │  • session_history     (what have we done?)             │   │
│  │  • project_workspaces  (where are projects?)             │   │
│  │  • procedure_registry  (what procedures exist?)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Project-Specific Schemas                                │   │
│  │                                                           │   │
│  │  • nimbus_context     (Nimbus project context)          │   │
│  │  • claude_pm          (ClaudePM project context)         │   │
│  │  • public             (Work packages, SOPs)              │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Formatted Startup Brief                              │
│                                                                   │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│  🤖 IDENTITY LOADED: claude-code-unified                         │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
│                                                                   │
│  WHO AM I: Project-Aware CLI for all projects                   │
│  MY CAPABILITIES: postgres, memory, filesystem, github...        │
│                                                                   │
│  📚 SHARED KNOWLEDGE (Top 5 patterns)                           │
│  📅 MY RECENT SESSIONS (Last 5)                                 │
│  👥 OTHER CLAUDE FAMILY MEMBERS                                 │
│  📋 CURRENT PROJECT CONTEXT (if applicable)                     │
│                                                                   │
│  ✅ READY TO WORK                                               │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              Saved to Logs                                        │
│                                                                   │
│  C:\claude\shared\logs\startup_context_{identity}_{timestamp}.txt│
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

### C:\claude\shared\ (Canonical Location)

```
C:\claude\shared\
├── scripts/
│   ├── load_claude_startup_context.py  ← MAIN startup script
│   ├── sync_workspaces.py              ← Generate workspaces.json
│   ├── sync_postgres_to_mcp.py         ← Sync DB to MCP configs
│   ├── sync_mcp_approvals.py           ← Sync approvals
│   └── select_project.py               ← Project selector
├── docs/
│   ├── ANTI-HALLUCINATION.md           ← Query before proposing
│   ├── csharp-desktop-mcp-guide.md     ← C# MCP usage
│   ├── ROSLYN-WORKFLOW.md              ← C# compliance workflow
│   └── MIGRATION_GUIDE.md              ← Workspace isolation guide
├── logs/
│   └── startup_context_*.txt           ← Session startup logs
└── commands/
    └── (legacy - now in project .claude dirs)
```

### C:\Projects\claude-family\ (Git Repository)

```
C:\Projects\claude-family\
├── .claude/
│   └── commands/
│       ├── session-start.md            ← /session-start slash command
│       └── session-end.md              ← /session-end slash command
├── docs/
│   ├── STARTUP_ARCHITECTURE.md         ← This file
│   ├── STARTUP_SYSTEM_AUDIT_2025-11-04.md
│   └── ... (other docs)
├── scripts/
│   ├── load_claude_startup_context.py  ← Synced from C:\claude\shared\
│   ├── sync_slash_commands.py          ← Distribute commands to projects
│   ├── audit_docs.py                   ← Documentation audit
│   ├── install_git_hooks.py            ← Git hook installer
│   └── ... (other scripts)
├── CLAUDE.md                           ← Project-specific context
├── README.md
└── workspaces.json                     ← Auto-generated from DB
```

**Important**: `C:\claude\shared\scripts\` is the **source of truth** for startup scripts. Git repo scripts are synced FROM shared, not TO shared.

---

## Startup Workflow (Step by Step)

### Phase 1: Session Start Command

**Trigger**: User runs `/session-start` in any Claude instance

**File**: `.claude/commands/session-start.md`

**What Happens**:
1. Claude sees the command content and executes each step
2. Calls Python scripts (requires Windows path quoting!)
3. Interacts with PostgreSQL via MCP
4. Loads context from memory graph via MCP

### Phase 2: Load Startup Context

**Script**: `C:\claude\shared\scripts\load_claude_startup_context.py`

**Command** (note the quotes!):
```bash
python "C:\claude\shared\scripts\load_claude_startup_context.py"
```

**Process**:
1. Detect platform (`claude-code-console`, `desktop`, `cursor`, etc.)
2. Detect current project from `os.getcwd()`
3. Query `claude_family.identities` for matching identity by platform
4. Load shared knowledge via `get_universal_knowledge()` function
5. Load recent sessions via `get_recent_sessions()` function
6. Load project-specific context if in known project
7. Format beautiful startup brief
8. Save to `C:\claude\shared\logs\`
9. Print to Claude's context

**Key Functions Used**:
```sql
-- Get identity by platform
SELECT * FROM claude_family.identities
WHERE platform = 'claude-code-console' AND status = 'active'
ORDER BY last_active_at DESC LIMIT 1;

-- Update last active timestamp
UPDATE claude_family.identities
SET last_active_at = CURRENT_TIMESTAMP
WHERE identity_id = '<uuid>';
```

### Phase 3: Sync Workspaces

**Script**: `C:\claude\shared\scripts\sync_workspaces.py`

**Command**:
```bash
python "C:\claude\shared\scripts\sync_workspaces.py"
```

**Purpose**: Generate `workspaces.json` from PostgreSQL so Claude knows where projects are located.

**Output**: `workspaces.json` in current directory
```json
{
  "_metadata": {
    "generated_at": "2025-11-04T16:49:12",
    "source": "PostgreSQL (claude_family.project_workspaces)"
  },
  "workspaces": {
    "nimbus-user-loader": {
      "path": "C:\\Projects\\nimbus-user-loader",
      "type": "csharp-winforms",
      "description": "Nimbus user import tool"
    },
    ...
  }
}
```

### Phase 4: Log Session Start

**Method**: Direct PostgreSQL MCP call

**SQL**:
```sql
INSERT INTO claude_family.session_history
(identity_id, session_start, project_name, session_summary)
VALUES (
    (SELECT identity_id FROM claude_family.identities WHERE identity_name = 'claude-code-unified'),
    NOW(),
    'project-name',
    'Brief description of what you plan to work on'
)
RETURNING session_id;
```

**Important**: Save the returned `session_id` - you'll need it for `/session-end`!

### Phase 5: Query Context

**When**: Only if user asks about previous work (don't do this proactively!)

**Memory Graph MCP**:
```
mcp__memory__search_nodes(query="relevant keywords")
```

**Shared Knowledge**:
```sql
SELECT title, description, knowledge_category, confidence_level
FROM claude_family.shared_knowledge
WHERE title ILIKE '%keyword%'
ORDER BY confidence_level DESC, times_applied DESC
LIMIT 10;
```

**Past Sessions**:
```sql
SELECT session_summary, tasks_completed, project_name
FROM claude_family.session_history
WHERE session_summary ILIKE '%keyword%'
ORDER BY session_start DESC LIMIT 10;
```

---

## Session End Workflow

### Trigger: /session-end Command

**File**: `.claude/commands/session-end.md`

**Steps**:

1. **Find Unclosed Session**:
```sql
SELECT session_id, project_name, session_start
FROM claude_family.session_history
WHERE identity_id = (
    SELECT identity_id FROM claude_family.identities
    WHERE identity_name = 'claude-code-unified'
)
AND session_end IS NULL
ORDER BY session_start DESC LIMIT 1;
```

2. **Update Session**:
```sql
UPDATE claude_family.session_history
SET
    session_end = NOW(),
    session_summary = 'Comprehensive summary of what was accomplished',
    tasks_completed = ARRAY['Task 1', 'Task 2'],
    learnings_gained = ARRAY['Learning 1', 'Learning 2'],
    challenges_encountered = ARRAY['Challenge 1']
WHERE session_id = '<uuid-from-step-1>';
```

3. **Store Reusable Knowledge** (if discovered new patterns):
```sql
INSERT INTO claude_family.shared_knowledge
(title, description, knowledge_type, knowledge_category, confidence_level, created_by_identity_id)
VALUES (
    'Pattern Name',
    'Description',
    'pattern',
    'category',
    10,
    (SELECT identity_id FROM claude_family.identities WHERE identity_name = 'claude-code-unified')
);
```

4. **Update Memory Graph** (if relevant):
```
mcp__memory__create_entities(entities=[...])
mcp__memory__create_relations(relations=[...])
```

---

## Database Schema Reference

### claude_family.identities

```sql
CREATE TABLE claude_family.identities (
    identity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_name VARCHAR UNIQUE NOT NULL,
    platform VARCHAR NOT NULL,
    role_description TEXT NOT NULL,
    capabilities JSONB DEFAULT '{}'::jsonb,
    personality_traits JSONB DEFAULT '{}'::jsonb,
    learning_style JSONB DEFAULT '{}'::jsonb,
    status VARCHAR DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Active Identities**:
- `claude-code-unified` - Platform: `claude-code-console`
- `claude-desktop-001` - Platform: `desktop`
- `claude-cursor-001` - Platform: `cursor`
- `claude-pm-001` - Platform: `claude-code-console` (project-specific)
- `diana` - Platform: `orchestrator`

### claude_family.session_history

```sql
CREATE TABLE claude_family.session_history (
    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id UUID REFERENCES identities(identity_id),
    project_schema VARCHAR,
    project_name VARCHAR,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    tasks_completed TEXT[],
    learnings_gained TEXT[],
    challenges_encountered TEXT[],
    session_summary TEXT,
    session_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### claude_family.shared_knowledge

```sql
CREATE TABLE claude_family.shared_knowledge (
    knowledge_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR NOT NULL,
    description TEXT NOT NULL,
    knowledge_type VARCHAR NOT NULL,  -- 'pattern', 'technique', 'gotcha', 'best-practice'
    knowledge_category VARCHAR NOT NULL,  -- 'mcp', 'csharp', 'database', etc.
    confidence_level INTEGER DEFAULT 5,  -- 1-10
    times_applied INTEGER DEFAULT 0,
    created_by_identity_id UUID REFERENCES identities(identity_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Windows Path Quoting (CRITICAL!)

### The Problem

The Bash tool in Claude Code Console requires proper quoting for Windows paths with backslashes:

❌ **WRONG** (backslashes get stripped):
```bash
python C:\claude\shared\scripts\load_claude_startup_context.py
# Becomes: pythonclaudesharedscriptsload_claude_startup_context.py
```

✅ **CORRECT** (quotes preserve path):
```bash
python "C:\claude\shared\scripts\load_claude_startup_context.py"
# Works perfectly!
```

### Rule

**ALWAYS quote Windows absolute paths** when using them in Bash commands in slash command markdown files.

---

## Troubleshooting

### Startup Script Fails with "file not found"

**Symptom**: `can't open file 'C:\\Projects\\...\\claudesharedscripts...'`

**Cause**: Missing quotes around Windows path

**Fix**: Add quotes:
```bash
python "C:\claude\shared\scripts\load_claude_startup_context.py"
```

### "Identity not found for platform"

**Symptom**: `❌ Identity not found for platform: claude-code-console`

**Cause**: No matching identity in database OR platform detection wrong

**Fix**:
1. Check identities: `SELECT * FROM claude_family.identities;`
2. Verify your identity exists with matching platform
3. Check script's `detect_platform()` function

### "Column 'id' does not exist"

**Symptom**: SQL error when querying session_history

**Cause**: Using old documentation with wrong column name

**Fix**: Use `session_id` instead of `id`

### "Table 'universal_knowledge' does not exist"

**Symptom**: SQL error when querying knowledge

**Cause**: Using old table name

**Fix**: Use `shared_knowledge` instead of `universal_knowledge`

---

## Sync Process

### C:\claude\shared\ → Git Repo (Current Practice)

When scripts in `C:\claude\shared\scripts\` are updated, they should be copied back to the git repository:

```bash
cp "C:\claude\shared\scripts\load_claude_startup_context.py" "C:\Projects\claude-family\scripts\"
cd C:\Projects\claude-family
git add scripts/load_claude_startup_context.py
git commit -m "Sync: Updated startup script from shared location"
git push
```

### Git Repo → Other Projects (Slash Commands)

When slash commands in `claude-family/.claude/commands/` are updated, distribute them to other projects:

```bash
cd C:\Projects\claude-family
python scripts/sync_slash_commands.py
```

This copies:
- `session-start.md` → All project `.claude/commands/` directories
- `session-end.md` → All project `.claude/commands/` directories

---

## Best Practices

1. **Always run /session-start** at the beginning of every session
2. **Always run /session-end** before closing Claude
3. **Query existing knowledge** before proposing solutions
4. **Store learnings** in shared_knowledge for reuse
5. **Keep session summaries detailed** - future you will thank you
6. **Use proper path quoting** in all Bash commands
7. **Update last_active_at** automatically (script does this)
8. **Log unclosed sessions** - they indicate crashes or forgotten ends

---

## Maintenance

### Monthly Tasks

1. **Audit documentation**: `python scripts/audit_docs.py`
2. **Review shared knowledge**: Check for duplicates or outdated patterns
3. **Clean up old logs**: Archive logs older than 90 days
4. **Update procedure_registry**: Ensure all procedures are documented

### After Script Changes

1. Update script in `C:\claude\shared\scripts\`
2. Test with multiple Claude instances
3. Copy back to git repo
4. Commit with descriptive message
5. Document changes in this file

---

## Version History

**v2.0 (2025-11-04)**:
- Fixed Windows path quoting in session-start.md
- Corrected table names (universal_knowledge → shared_knowledge)
- Fixed column names in session-end.md
- Synced newer startup script to git repo
- Created this architecture document

**v1.0 (2025-10-21)**:
- Initial implementation of centralized startup system
- Created load_claude_startup_context.py
- Established PostgreSQL schema structure

---

**Maintained by**: Claude Family Infrastructure Team
**Questions?**: Check session history or shared_knowledge table
