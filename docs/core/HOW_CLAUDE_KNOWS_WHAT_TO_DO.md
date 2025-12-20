# How Claude Knows What To Do
## Complete Implementation Guide for Claude Family Knowledge System

**Version**: 1.0
**Date**: 2025-12-18
**Status**: IMPLEMENTATION GUIDE

---

## The Core Question

> "I've been coding for an hour and the user asks me to write a new feature for Nimbus data retrieval. How do I know what to do?"

This document explains exactly how Claude discovers relevant knowledge WITHOUT the user explicitly telling it.

---

## Part 1: The Four Discovery Mechanisms

Claude has **four ways** to discover relevant information:

| Mechanism | When It Fires | What It Provides | Storage Location |
|-----------|---------------|------------------|------------------|
| **1. CLAUDE.md** | Session start | Project config, standards, rules | `{project}/CLAUDE.md` |
| **2. Knowledge Hooks** | Every prompt | Relevant patterns, gotchas, examples | `claude.knowledge` table |
| **3. Skills** | On-demand | Deep guides, tutorials, workflows | `.claude/skills/*.md` |
| **4. Process Router** | Every prompt | Workflow steps, checklists | `claude.process_registry` |

### How They Work Together

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USER PROMPT                                      │
│            "Add a data retrieval feature for Nimbus"                    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MECHANISM 1: CLAUDE.md                               │
│                    (Already loaded at session start)                    │
│                                                                         │
│  Contains: Project standards, tech stack, coding rules                  │
│  Claude already knows: "This is a C# project using WinForms"           │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MECHANISM 2: Knowledge Hook                          │
│                    (Fires on UserPromptSubmit)                          │
│                                                                         │
│  Hook: knowledge_retriever.py                                           │
│  Action: Extracts keywords ["nimbus", "data", "retrieval", "feature"]   │
│  Query: SELECT * FROM claude.knowledge WHERE title ILIKE '%nimbus%'...  │
│  Finds: 5 relevant entries about Nimbus API                            │
│  Injects: <relevant-knowledge>...</relevant-knowledge>                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MECHANISM 3: Skills (Future)                         │
│                    (Loaded when Claude detects relevance)               │
│                                                                         │
│  Skill: .claude/skills/nimbus-api/SKILL.md                             │
│  Contains: Complete Nimbus API guide, authentication, examples          │
│  Loaded: When Claude's reasoning determines it's needed                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MECHANISM 4: Process Router                          │
│                    (Fires on UserPromptSubmit)                          │
│                                                                         │
│  Hook: process_router.py (integrated into knowledge_retriever)         │
│  Detects: "Feature Implementation" workflow (PROC-DEV-001)             │
│  Injects: Workflow steps, standards to follow                          │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    COMBINED CONTEXT TO CLAUDE                           │
│                                                                         │
│  <relevant-knowledge>                                                   │
│  ### 1. Nimbus OData Field Naming                                      │
│  Use "Description" not "Name" for all label fields...                  │
│                                                                         │
│  ### 2. Nimbus RESTApi CRUD Pattern                                    │
│  POST handles both create AND update operations...                     │
│                                                                         │
│  ### 3. Nimbus ScheduleShift Time Fields                               │
│  Only send LOCAL times - UTC is auto-calculated...                     │
│  </relevant-knowledge>                                                  │
│                                                                         │
│  ### Matched Workflow: Feature Implementation (PROC-DEV-001)           │
│  Steps:                                                                 │
│  1. Understand requirements                                             │
│  2. Check existing patterns                                             │
│  3. Design solution                                                     │
│  4. Create build_task                                                   │
│  5. Implement                                                           │
│  6. Test                                                                │
│                                                                         │
│  ⚠️ Session Checkpoint (15 interactions):                              │
│  - Consider committing your changes                                     │
│                                                                         │
│  [User prompt]: Add a data retrieval feature for Nimbus                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CLAUDE RESPONDS                                       │
│                                                                         │
│  "I'll implement a data retrieval feature for Nimbus. Based on the     │
│  Nimbus API patterns, I'll:                                            │
│                                                                         │
│  1. Use the OData endpoint with 'Description' fields (not 'Name')      │
│  2. Handle the non-standard REST pattern where POST does updates       │
│  3. Send only local times for any scheduling data                      │
│                                                                         │
│  Let me start by understanding your requirements..."                   │
│                                                                         │
│  USER DIDN'T TELL CLAUDE ANY OF THIS - THE SYSTEM DID                 │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 2: What Documents Are Needed?

### Document Type 1: CLAUDE.md (Per Project)

**Location**: `{project_root}/CLAUDE.md`
**Loaded**: Automatically at session start
**Size**: Keep under 250 lines (context efficiency)

**Purpose**: Project-specific configuration Claude needs for EVERY interaction

**Template**:
```markdown
# {Project Name}

## Tech Stack
- Language: C#/.NET 8
- UI: WinForms
- Database: PostgreSQL
- APIs: Nimbus WFM (OData + REST)

## Critical Rules
- ALWAYS use Roslyn MCP for C# validation
- NEVER hardcode API credentials
- Use DateTimeOffset for all time operations

## Project Structure
src/
├── Services/      # API clients, business logic
├── Models/        # Data models
├── Forms/         # UI forms
└── Utils/         # Helpers

## Current Focus
Working on: Nimbus data import features
Recent changes: Added shift scheduling

## Quick Commands
- Build: dotnet build
- Test: dotnet test
- Run: dotnet run
```

### Document Type 2: Knowledge Entries (Database)

**Location**: `claude.knowledge` table
**Loaded**: On-demand via hook when keywords match
**Size**: Each entry ~200-500 words

**Purpose**: Reusable patterns, gotchas, solutions discovered during work

**Schema**:
```sql
CREATE TABLE claude.knowledge (
    knowledge_id UUID PRIMARY KEY,
    title VARCHAR(200) NOT NULL,          -- "Nimbus OData Field Naming"
    description TEXT NOT NULL,            -- The actual knowledge
    knowledge_category VARCHAR(100),      -- "nimbus-api", "database", "testing"
    knowledge_type VARCHAR(50),           -- "pattern", "gotcha", "api-reference"
    code_example TEXT,                    -- Optional code snippet
    confidence_level INTEGER,             -- 1-100, affects ranking
    applies_to_projects TEXT[],           -- Which projects this applies to
    times_applied INTEGER DEFAULT 0       -- Usage tracking
);
```

**What To Store**:
| Type | Example | When to Create |
|------|---------|----------------|
| `pattern` | "Nimbus OData Field Naming" | Discovered a reusable approach |
| `gotcha` | "POST does update AND create" | Found non-obvious behavior |
| `api-reference` | "ScheduleShift Time Fields" | API quirk worth remembering |
| `bug-fix` | "UTC time conversion issue" | Fixed a tricky bug |
| `best-practice` | "Use CookieContainer for sessions" | Found optimal approach |

### Document Type 3: Skills (Future Enhancement)

**Location**: `.claude/skills/{skill-name}/SKILL.md`
**Loaded**: When Claude's reasoning determines relevance
**Size**: Can be longer (1000+ lines) - only loaded when needed

**Purpose**: Deep guides, tutorials, complete workflows

**Structure**:
```
.claude/skills/
├── nimbus-api/
│   └── SKILL.md          # Complete Nimbus API guide
├── feature-workflow/
│   └── SKILL.md          # How to implement features
├── testing/
│   └── SKILL.md          # Testing standards and patterns
└── database/
    └── SKILL.md          # Database patterns and queries
```

**Example SKILL.md**:
```markdown
# Nimbus API Skill

## Overview
This skill provides guidance for working with the Nimbus WFM API.

## Authentication
1. Get bearer token from /auth endpoint
2. Include in all requests: Authorization: Bearer {token}
3. Token expires after 24 hours

## OData Endpoints
- /odata/Employees - Employee records
- /odata/Shifts - Shift schedules
- /odata/Activities - Activity definitions

## Common Patterns
[detailed examples...]

## Gotchas
- Use Description not Name for labels
- POST handles both create and update
- Filter on Deleted doesn't work server-side
```

### Document Type 4: Process Registry (Database)

**Location**: `claude.process_registry` + `claude.process_steps`
**Loaded**: Via process router hook when workflow detected
**Purpose**: Standardized workflows with steps and checklists

**Current Workflows (32 total)**:
| ID | Name | Trigger Keywords |
|----|------|------------------|
| PROC-DEV-001 | Feature Implementation | "feature", "implement", "build", "add" |
| PROC-DEV-002 | Bug Fix | "bug", "fix", "error", "broken" |
| PROC-DOC-001 | Documentation Update | "document", "docs", "readme" |
| PROC-SESSION-001 | Session Start | /session-start command |

---

## Part 3: How Is It Stored? (Best Practices)

### Storage Decision Matrix

| Content Type | Best Storage | Why |
|--------------|--------------|-----|
| Project config | CLAUDE.md file | Auto-loaded, version controlled |
| Reusable patterns | Database (knowledge table) | Queryable, cross-project |
| Deep guides | Skills folders | Lazy-loaded, detailed |
| Workflows | Database (process_registry) | Queryable, consistent |
| Quick reference | Markdown in docs/ | Human readable, git tracked |
| Session state | JSON file + Database | Persistence across restarts |

### The Hybrid Approach

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYERS                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Layer 1: ALWAYS LOADED (Small, Essential)                             │
│  ├── CLAUDE.md (~200 lines)                                            │
│  └── Global config (~50 lines)                                         │
│                                                                         │
│  Layer 2: HOOK-LOADED (On-Demand, Relevant)                            │
│  ├── Knowledge entries (top 5 matches)                                 │
│  ├── Workflow steps (when detected)                                    │
│  └── Reminders (at intervals)                                          │
│                                                                         │
│  Layer 3: SKILL-LOADED (Deep, When Needed)                             │
│  ├── Detailed API guides                                               │
│  ├── Complete tutorials                                                │
│  └── Reference documentation                                           │
│                                                                         │
│  Layer 4: NEVER LOADED (Archive, History)                              │
│  ├── Old session logs                                                  │
│  ├── Deprecated patterns                                               │
│  └── Historical decisions                                              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Part 4: Complete Deployment Steps

### Step 1: Deploy Hook Scripts

```bash
# Copy to your project
cd C:\Projects\claude-family

# Create scripts directory if needed
mkdir scripts

# Copy the three scripts:
# - knowledge_retriever.py (RAG hook)
# - stop_hook_enforcer.py (Counter reminders)
# - run_regression_tests.py (Test suite)
```

### Step 2: Configure hooks.json

Create/update `.claude/hooks.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python scripts/knowledge_retriever.py",
        "description": "Auto-inject relevant knowledge from database"
      },
      {
        "type": "command",
        "command": "python scripts/stop_hook_enforcer.py",
        "description": "Counter-based reminders at 5/10/20 intervals"
      }
    ]
  }
}
```

### Step 3: Set Environment Variables

```bash
# Windows
set CLAUDE_DB_HOST=localhost
set CLAUDE_DB_NAME=ai_company_foundation
set CLAUDE_DB_USER=postgres
set CLAUDE_DB_PASSWORD=your_password

# Or add to .env file
echo CLAUDE_DB_HOST=localhost >> .env
echo CLAUDE_DB_NAME=ai_company_foundation >> .env
```

### Step 4: Verify Knowledge Exists

```sql
-- Check you have relevant knowledge
SELECT COUNT(*) as nimbus_entries
FROM claude.knowledge
WHERE title ILIKE '%nimbus%' OR knowledge_category ILIKE '%nimbus%';

-- Should return: 18+ entries
```

### Step 5: Test the Flow

```bash
# Run regression tests
cd C:\Projects\claude-family
python scripts/run_regression_tests.py --quick

# Expected: 5/5 tests pass
```

### Step 6: Verify in Real Session

Start a Claude Code session and try:
```
User: "How do I call the Nimbus API?"
```

**Expected**: Claude responds with knowledge about Nimbus OData patterns, field naming, etc. WITHOUT you telling it.

---

## Part 5: The Complete Scenario Walkthrough

### Scenario: "Add data retrieval feature for Nimbus"

**Pre-conditions**:
- Claude Code session running for 1 hour (~15 interactions)
- Working in nimbus-user-loader project
- hooks.json configured with knowledge_retriever and stop_hook_enforcer
- Database has 18 Nimbus knowledge entries

**Step-by-Step Flow**:

1. **User types**: "Add a data retrieval feature for Nimbus"

2. **Claude Code intercepts** (before sending to Claude)

3. **Hook 1 fires**: `knowledge_retriever.py`
   ```python
   # Extracts keywords
   keywords = ["nimbus", "data", "retrieval", "feature"]

   # Queries database
   SELECT * FROM claude.knowledge
   WHERE title ILIKE '%nimbus%' OR title ILIKE '%data%'...

   # Finds 5 entries:
   # - Nimbus OData Field Naming
   # - Nimbus RESTApi CRUD Pattern
   # - Nimbus ScheduleShift Time Fields
   # - Nimbus OData Deleted Field Filter
   # - Nimbus UserSDK Batch Import

   # Formats and outputs
   print("<relevant-knowledge>...")
   ```

4. **Hook 2 fires**: `stop_hook_enforcer.py`
   ```python
   # Reads state: interaction_count = 14
   # Increments to 15
   # 15 % 5 == 0 → Reminder due!

   # Checks git status
   # Finds 3 modified files

   # Outputs reminder
   print("⚠️ Session Checkpoint (15 interactions)...")
   ```

5. **Combined context assembled**:
   ```
   <relevant-knowledge>
   ### 1. Nimbus OData Field Naming - Description not Name
   In the Nimbus WFM OData API, all entities use "Description"
   for name/label fields, NOT "Name"...

   ### 2. Nimbus RESTApi CRUD Pattern - Non-Standard POST
   Nimbus uses non-standard REST API patterns where POST handles
   both create and update operations...

   ### 3. Nimbus ScheduleShift Time Fields - Local and UTC
   ScheduleShift API only needs LOCAL times - UTC is auto-calculated...
   </relevant-knowledge>

   ⚠️ Session Checkpoint (15 interactions):
   - Consider: Have you committed your changes?
   - Modified files: 3
     - src/Services/NimbusService.cs
     - src/Models/ShiftData.cs
     - src/Forms/ImportForm.cs

   Add a data retrieval feature for Nimbus
   ```

6. **Claude receives enriched prompt**

7. **Claude responds** (informed by injected knowledge):
   ```
   I'll implement a data retrieval feature for Nimbus. Based on the
   API patterns I'm aware of:

   1. I'll use the OData endpoint and query the `Description` field
      (not `Name`) for any label data

   2. For any updates, I'll use POST which handles both create and
      update in Nimbus's non-standard REST pattern

   3. For shift data, I'll only send local times since UTC is
      auto-calculated by the API

   First, let me understand your requirements:
   - What data do you need to retrieve? (Employees, Shifts, Activities?)
   - How should it be displayed in the UI?
   - Should it support filtering?

   Also, I notice you have 3 uncommitted files. Would you like to
   commit those first before we start the new feature?
   ```

**RESULT**: Claude knew about Nimbus API patterns, field naming conventions, and reminded about uncommitted changes - ALL WITHOUT THE USER TELLING IT.

---

## Part 6: Verification Checklist

### Is It Working?

Run this verification after deployment:

```sql
-- Check 1: Knowledge entries exist
SELECT COUNT(*) FROM claude.knowledge;
-- Expected: 161+

-- Check 2: Nimbus knowledge specifically
SELECT COUNT(*) FROM claude.knowledge
WHERE title ILIKE '%nimbus%';
-- Expected: 18+

-- Check 3: Retrieval logging works
SELECT COUNT(*) FROM claude.knowledge_retrieval_log
WHERE retrieved_at > NOW() - INTERVAL '1 hour';
-- After using system: Should show queries

-- Check 4: Enforcement logging works
SELECT COUNT(*) FROM claude.enforcement_log
WHERE triggered_at > NOW() - INTERVAL '1 hour';
-- After 5+ interactions: Should show reminders
```

### Quick Test

In Claude Code, type:
```
How do I call the Nimbus Shifts API?
```

**If working**: Claude mentions OData, Description fields, time handling
**If not working**: Claude gives generic API advice, asks for details

---

## Part 7: Adding New Knowledge

When you discover something worth remembering:

### Option 1: Via SQL (Direct)

```sql
INSERT INTO claude.knowledge (
    title,
    description,
    knowledge_category,
    knowledge_type,
    confidence_level
) VALUES (
    'Nimbus Rate Limiting - 100 requests per minute',
    'The Nimbus API enforces rate limiting at 100 requests per minute per user.
    Exceeding this returns HTTP 429. Implement exponential backoff with initial
    delay of 1 second. Use batch endpoints where available to reduce request count.',
    'nimbus-api',
    'gotcha',
    85
);
```

### Option 2: Via Slash Command (Future)

```
/knowledge-add "Nimbus Rate Limiting" "100 requests per minute limit..."
```

### Option 3: During Session

Ask Claude: "Remember this for future sessions: Nimbus API has a 100 req/min rate limit"

Claude should (when working):
1. Detect this is a knowledge capture request
2. Format and insert into database
3. Confirm it's stored

---

## Summary

### How Claude Knows What To Do

| Question | Answer |
|----------|--------|
| **What documents are needed?** | CLAUDE.md (always), Knowledge entries (on-demand), Skills (deep guides) |
| **How are they stored?** | Files (CLAUDE.md, Skills) + Database (knowledge, workflows) |
| **What mechanism finds them?** | UserPromptSubmit hooks query DB on every prompt |
| **How does Claude know they exist?** | Hooks inject relevant content into context automatically |

### The Key Insight

**Claude doesn't "know" - the SYSTEM tells Claude at the right moment.**

The hooks transform this:
```
User: "Add Nimbus feature"
```

Into this:
```
[Knowledge about Nimbus API patterns]
[Reminder about uncommitted code]
[Workflow steps for features]
User: "Add Nimbus feature"
```

Claude then responds as if it "knew" all along - but really, the hooks provided just-in-time context.

---

**Document Version**: 1.0
**Status**: COMPLETE IMPLEMENTATION GUIDE
**Ready For**: Deployment to Claude Code projects
