# Claude Mission Control - Complete Implementation Plan

**Project:** Claude Family Mission Control (Python + Flet)
**Location:** C:\Projects\claude-mission-control
**Created:** 2025-11-15
**Strategy:** Orchestrator-based parallel agent execution

---

## Executive Summary

Build a Python-based coordination hub for Claude Family using **orchestrator MCP to spawn specialized agents** for parallel development. This approach:

- ✅ Faster development (parallel agent execution)
- ✅ Specialized focus (coder-haiku for code, reviewer-sonnet for review)
- ✅ Consistent patterns (each agent focuses on one layer)
- ✅ Built-in code review (reviewer agent validates coder output)

---

## Architecture Overview

### Technology Stack
- **Language:** Python 3.11+
- **GUI:** Flet (Material Design, cross-platform)
- **Database:** PostgreSQL (ai_company_foundation)
- **Schemas:**
  - `claude_mission_control` (new - app-specific tables)
  - `claude_family` (existing - shared infrastructure)
  - `claude_pm` (existing - feedback tables only)

### Application Structure
```
src/
├── main.py                    # Flet app entry point + navigation
├── database/
│   ├── connection.py          # Connection pool + context manager
│   ├── projects.py            # Project queries
│   ├── sessions.py            # Session queries
│   ├── feedback.py            # Feedback CRUD
│   ├── procedures.py          # Procedure queries
│   └── knowledge.py           # Knowledge queries
├── views/
│   ├── launcher.py            # Project launcher dashboard
│   ├── sessions.py            # Session history viewer
│   ├── feedback.py            # Feedback hub
│   └── procedures.py          # Procedure browser
├── services/
│   ├── launcher_service.py    # Launch Claude Code with context
│   ├── sql_generator.py       # Generate session-end SQL
│   └── orchestrator.py        # Orchestrator MCP integration
└── models/
    ├── project.py             # Project dataclass
    ├── session.py             # Session dataclass
    ├── feedback.py            # Feedback dataclass
    └── procedure.py           # Procedure dataclass
```

---

## Database Schema Strategy

### Do NOT Drop Old Tables
Per user: "keep them for now, not sure if you have done a thorough search"

### Create New Schema: `claude_mission_control`

```sql
CREATE SCHEMA IF NOT EXISTS claude_mission_control;

-- Instance messaging (inter-Claude communication)
CREATE TABLE claude_mission_control.instance_messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    from_identity_id UUID REFERENCES claude_family.identities(identity_id),
    to_identity_id UUID, -- NULL = broadcast to all
    message_type VARCHAR(50) NOT NULL, -- 'task-request', 'status-update', 'question', 'notification'
    message_subject VARCHAR(200),
    message_body JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'unread', -- 'unread', 'read', 'processed'
    read_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),

    CHECK (message_type IN ('task-request', 'status-update', 'question', 'notification')),
    CHECK (status IN ('unread', 'read', 'processed'))
);

CREATE INDEX idx_instance_messages_to ON claude_mission_control.instance_messages(to_identity_id, status);
CREATE INDEX idx_instance_messages_from ON claude_mission_control.instance_messages(from_identity_id);
CREATE INDEX idx_instance_messages_created ON claude_mission_control.instance_messages(created_at DESC);

-- Application settings
CREATE TABLE claude_mission_control.app_settings (
    setting_key VARCHAR(100) PRIMARY KEY,
    setting_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT NOW(),
    updated_by_identity_id UUID REFERENCES claude_family.identities(identity_id)
);

-- Audit log for Mission Control operations
CREATE TABLE claude_mission_control.audit_log (
    audit_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    identity_id UUID REFERENCES claude_family.identities(identity_id),
    operation VARCHAR(100) NOT NULL, -- 'launch_claude', 'create_feedback', 'update_procedure', etc.
    target_type VARCHAR(50), -- 'project', 'session', 'feedback', etc.
    target_id UUID,
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_log_identity ON claude_mission_control.audit_log(identity_id, created_at DESC);
CREATE INDEX idx_audit_log_operation ON claude_mission_control.audit_log(operation, created_at DESC);
```

### Reuse Existing Tables
- ✅ `claude_pm.project_feedback` - Feedback items
- ✅ `claude_pm.project_feedback_comments` - Comment threads
- ✅ `claude_family.session_history` - Session tracking
- ✅ `claude_family.shared_knowledge` - Knowledge base
- ✅ `claude_family.procedure_registry` - Procedures catalog
- ✅ `claude_family.project_workspaces` - Project locations
- ✅ `claude_family.identities` - Claude instances

---

## Orchestrator-Based Build Strategy

### Why Use Orchestrator

1. **Parallel development** - Multiple agents work simultaneously
2. **Specialized agents** - coder-haiku for code, reviewer-sonnet for review
3. **Isolation** - Each agent focuses on one layer (no context bleed)
4. **Built-in QA** - reviewer-sonnet validates coder-haiku output

### Agent Task Breakdown

**Phase 1: Foundation (Sequential)**
1. **coder-haiku**: Database layer (connection.py + query modules)
2. **reviewer-sonnet**: Review database layer for security, patterns
3. **coder-haiku**: Models layer (dataclasses for project, session, feedback, procedure)

**Phase 2: Services (Sequential)**
1. **coder-haiku**: Launcher service (spawn Claude Code with correct working directory)
2. **coder-haiku**: SQL generator service (generate session-end SQL with pre-filled values)
3. **reviewer-sonnet**: Review services for error handling, edge cases

**Phase 3: Views (Parallel - can run simultaneously)**
1. **coder-haiku-1**: Project Launcher view
2. **coder-haiku-2**: Session Dashboard view
3. **coder-haiku-3**: Feedback Hub view
4. **coder-haiku-4**: Procedure Viewer view

**Phase 4: Integration (Sequential)**
1. **coder-haiku**: Main app shell (navigation, routing)
2. **tester-haiku**: Write integration tests
3. **reviewer-sonnet**: Final code review + documentation check

### Orchestrator Command Examples

```python
# Spawn coder agent for database layer
result = mcp__orchestrator__spawn_agent(
    agent_type="coder-haiku",
    task="""Build database layer for Claude Mission Control.

Location: C:/Projects/claude-mission-control/src/database/

Files to create:
1. connection.py - PostgreSQL connection pool with context manager
2. projects.py - Query functions for project_workspaces table
3. sessions.py - Query functions for session_history table
4. feedback.py - CRUD for project_feedback table
5. procedures.py - Query functions for procedure_registry table

Requirements:
- Use psycopg2 connection pooling
- All functions async where possible
- Return list of dicts (not tuples)
- Include comprehensive docstrings
- Error handling with specific exceptions

Reference schema:
- claude_family.project_workspaces
- claude_family.session_history
- claude_pm.project_feedback
- claude_family.procedure_registry

Follow patterns in C:/Projects/claude-family/scripts/load_claude_startup_context.py for PostgreSQL usage.""",
    workspace_dir="C:/Projects/claude-mission-control",
    timeout=300
)

# Spawn reviewer agent to validate
result = mcp__orchestrator__spawn_agent(
    agent_type="reviewer-sonnet",
    task="""Review database layer code for Claude Mission Control.

Location: C:/Projects/claude-mission-control/src/database/

Check for:
1. SQL injection prevention (parameterized queries)
2. Connection pool cleanup (context managers)
3. Error handling (specific exceptions, not catch-all)
4. Docstrings (comprehensive with examples)
5. Type hints (all function parameters and returns)

Provide:
- List of issues found (security, bugs, style)
- Suggested fixes
- Overall code quality score (1-10)""",
    workspace_dir="C:/Projects/claude-mission-control",
    timeout=180
)
```

---

## Detailed Task Specifications

### Task 1: Database Layer

**Agent:** coder-haiku
**Timeout:** 300s
**Output:** 5 Python files in src/database/

**connection.py**
```python
"""
Database connection management.

Provides:
- Connection pooling (psycopg2.pool)
- Context manager (DatabaseConnection)
- Query execution helper (execute_query)
"""

Required functions:
- get_connection_pool() -> SimpleConnectionPool
- class DatabaseConnection (context manager)
- execute_query(query, params=None, fetch=True) -> list[dict] | None
```

**projects.py**
```python
"""
Project-related database queries.

Schema: claude_family.project_workspaces
"""

Required functions:
- get_all_projects() -> list[dict]
- get_project_by_name(project_name: str) -> dict | None
- get_recent_sessions_for_project(project_name: str, limit: int = 5) -> list[dict]
- get_open_feedback_count(project_id: uuid) -> int
```

**sessions.py**
```python
"""
Session history database queries.

Schema: claude_family.session_history
"""

Required functions:
- get_recent_sessions(limit: int = 20) -> list[dict]
- get_sessions_by_project(project_name: str) -> list[dict]
- get_sessions_by_identity(identity_id: uuid) -> list[dict]
- get_session_by_id(session_id: uuid) -> dict | None
- get_unclosed_sessions() -> list[dict]
- generate_session_end_sql(session_id: uuid) -> str
```

**feedback.py**
```python
"""
Feedback CRUD operations.

Schema: claude_pm.project_feedback, claude_pm.project_feedback_comments
"""

Required functions:
- get_all_feedback(filters: dict = None) -> list[dict]
- get_feedback_by_id(feedback_id: uuid) -> dict | None
- create_feedback(project_id: uuid, feedback_type: str, description: str, ...) -> uuid
- update_feedback_status(feedback_id: uuid, status: str) -> None
- add_comment(feedback_id: uuid, comment_text: str, author_identity_id: uuid) -> uuid
- get_comments(feedback_id: uuid) -> list[dict]
```

**procedures.py**
```python
"""
Procedure registry queries.

Schema: claude_family.procedure_registry
"""

Required functions:
- get_all_procedures() -> list[dict]
- get_procedures_for_project(project_name: str) -> list[dict]
- get_mandatory_procedures() -> list[dict]
- get_procedure_by_id(procedure_id: uuid) -> dict | None
```

---

### Task 2: Models Layer

**Agent:** coder-haiku
**Timeout:** 180s
**Output:** 4 Python files in src/models/

Use Python dataclasses for type safety.

**project.py**
```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Project:
    project_name: str
    project_path: str
    project_type: str
    description: str
    last_session: datetime | None
    open_feedback_count: int
```

Similar for Session, Feedback, Procedure.

---

### Task 3: Services Layer

**Agent:** coder-haiku
**Timeout:** 240s
**Output:** 3 Python files in src/services/

**launcher_service.py**
```python
"""
Claude Code launcher service.

Spawns Claude Code process with correct working directory and context.
"""

Required functions:
- launch_claude_code(project_path: str, project_name: str) -> bool
- check_unclosed_sessions(project_name: str) -> list[dict]
- get_mandatory_procedures(project_name: str) -> list[str]
- generate_launch_context(project_name: str) -> str
```

**sql_generator.py**
```python
"""
SQL query generator for common operations.

Generates pre-filled SQL templates to reduce Claude hallucination.
"""

Required functions:
- generate_session_end_sql(session_id: uuid) -> str
- generate_create_feedback_sql(project_id: uuid, feedback_type: str) -> str
- generate_add_knowledge_sql(title: str, category: str) -> str
```

---

### Task 4: Views (Flet UI)

**Agent:** coder-haiku (can spawn 4 in parallel)
**Timeout:** 300s each
**Output:** 4 Python files in src/views/

**launcher.py - Project Launcher View**
```python
"""
Project launcher dashboard.

Features:
- List all projects from project_workspaces
- Show last session time, identity, open feedback count
- "Open in Claude Code" button
- Pre-launch warnings (unclosed sessions, mandatory procedures)
"""

Required components:
- ProjectCard (displays project info)
- LaunchButton (spawns Claude Code)
- WarningDialog (unclosed sessions, procedures)
```

**sessions.py - Session Dashboard**
```python
"""
Session history viewer.

Features:
- Visual timeline of sessions (DataTable)
- Filter by project, identity, date range
- Click session → show details (dialog)
- Generate session-end SQL button
"""

Required components:
- SessionTimeline (DataTable with sessions)
- SessionDetailDialog (show full session info)
- SQLGeneratorButton (creates pre-filled SQL)
```

**feedback.py - Feedback Hub**
```python
"""
Feedback management interface.

Features:
- List all feedback items (filterable)
- Create new feedback via form
- Add comments to feedback
- Update feedback status
- Link to project launcher
"""

Required components:
- FeedbackList (DataTable with feedback items)
- NewFeedbackDialog (creation form)
- FeedbackDetailView (show details + comments)
- CommentThread (display and add comments)
```

**procedures.py - Procedure Viewer**
```python
"""
Procedure browser and manager.

Features:
- List all procedures (filterable)
- Show procedure details
- Highlight mandatory procedures
- Generate checklists for projects
"""

Required components:
- ProcedureList (DataTable)
- ProcedureDetailDialog (show full procedure)
- MandatoryBadge (visual indicator)
```

---

### Task 5: Main Application Shell

**Agent:** coder-haiku
**Timeout:** 180s
**Output:** src/main.py

```python
"""
Main application entry point.

Features:
- Navigation rail (4 views)
- Routing
- Theme management
- Window configuration
"""

Required:
- NavigationRail with 4 destinations
- Route handling
- View switching
- App initialization
```

---

## Testing Strategy

### Task 6: Integration Tests

**Agent:** tester-haiku
**Timeout:** 300s
**Output:** tests/test_*.py

Required test files:
- test_database.py - Database connection, queries
- test_services.py - Launcher, SQL generator
- test_models.py - Dataclass validation
- test_views.py - UI component rendering (if possible with Flet)

---

## Documentation Requirements

### Task 7: Documentation

**Agent:** analyst-sonnet
**Timeout:** 240s
**Output:** Multiple markdown files

Required docs:
- docs/ARCHITECTURE.md - System design, database schema, component diagram
- docs/DEVELOPMENT_GUIDE.md - How to add features, coding standards
- docs/DATABASE_MIGRATION.md - Migration from claude-pm, rollback instructions
- docs/USER_GUIDE.md - How to use Mission Control
- CLAUDE.md - Context for future Claude instances

---

## Execution Plan (Using Orchestrator)

### Manual Coordination Script

```python
"""
Orchestrate Mission Control build using parallel agents.

Run from: C:/Projects/claude-family
"""

import json
from datetime import datetime

# Task definitions
tasks = [
    {
        "phase": 1,
        "name": "Database Layer",
        "agent": "coder-haiku",
        "timeout": 300,
        "task_file": "tasks/01_database_layer.md"
    },
    {
        "phase": 1,
        "name": "Review Database",
        "agent": "reviewer-sonnet",
        "timeout": 180,
        "task_file": "tasks/02_review_database.md",
        "depends_on": ["Database Layer"]
    },
    {
        "phase": 2,
        "name": "Models Layer",
        "agent": "coder-haiku",
        "timeout": 180,
        "task_file": "tasks/03_models_layer.md"
    },
    {
        "phase": 3,
        "name": "Services Layer",
        "agent": "coder-haiku",
        "timeout": 240,
        "task_file": "tasks/04_services_layer.md"
    },
    {
        "phase": 4,
        "name": "Launcher View",
        "agent": "coder-haiku",
        "timeout": 300,
        "task_file": "tasks/05_launcher_view.md",
        "parallel_group": "views"
    },
    {
        "phase": 4,
        "name": "Sessions View",
        "agent": "coder-haiku",
        "timeout": 300,
        "task_file": "tasks/06_sessions_view.md",
        "parallel_group": "views"
    },
    {
        "phase": 4,
        "name": "Feedback View",
        "agent": "coder-haiku",
        "timeout": 300,
        "task_file": "tasks/07_feedback_view.md",
        "parallel_group": "views"
    },
    {
        "phase": 4,
        "name": "Procedures View",
        "agent": "coder-haiku",
        "timeout": 300,
        "task_file": "tasks/08_procedures_view.md",
        "parallel_group": "views"
    },
    {
        "phase": 5,
        "name": "Main App Shell",
        "agent": "coder-haiku",
        "timeout": 180,
        "task_file": "tasks/09_main_app.md",
        "depends_on": ["Launcher View", "Sessions View", "Feedback View", "Procedures View"]
    },
    {
        "phase": 6,
        "name": "Integration Tests",
        "agent": "tester-haiku",
        "timeout": 300,
        "task_file": "tasks/10_tests.md"
    },
    {
        "phase": 7,
        "name": "Documentation",
        "agent": "analyst-sonnet",
        "timeout": 240,
        "task_file": "tasks/11_documentation.md"
    },
    {
        "phase": 8,
        "name": "Final Review",
        "agent": "reviewer-sonnet",
        "timeout": 300,
        "task_file": "tasks/12_final_review.md",
        "depends_on": ["Main App Shell", "Integration Tests", "Documentation"]
    }
]

def execute_orchestrator_build():
    """Execute the build using orchestrator MCP agents."""

    results = []

    for phase in range(1, 9):
        phase_tasks = [t for t in tasks if t["phase"] == phase]

        print(f"\n{'='*60}")
        print(f"PHASE {phase}: {len(phase_tasks)} tasks")
        print(f"{'='*60}\n")

        # Execute parallel tasks in this phase
        for task in phase_tasks:
            print(f"Spawning {task['agent']} for: {task['name']}")

            # Load task specification
            with open(task['task_file']) as f:
                task_spec = f.read()

            # Spawn agent via orchestrator MCP
            result = spawn_agent(
                agent_type=task['agent'],
                task=task_spec,
                workspace_dir="C:/Projects/claude-mission-control",
                timeout=task['timeout']
            )

            results.append({
                "task": task['name'],
                "agent": task['agent'],
                "success": result.get('success'),
                "output": result.get('output')
            })

            print(f"  Result: {'✓' if result.get('success') else '✗'}")

    # Save results
    with open('mission_control_build_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*60}")
    print(f"BUILD COMPLETE")
    print(f"{'='*60}")
    print(f"Results saved to: mission_control_build_results.json")

if __name__ == "__main__":
    execute_orchestrator_build()
```

---

## Success Criteria

### MVP Complete When:
- ✅ All 4 views functional (Launcher, Sessions, Feedback, Procedures)
- ✅ Can launch Claude Code from Mission Control with 1 click
- ✅ Session history browsable without SQL queries
- ✅ Feedback items creatable/viewable via UI
- ✅ Procedures visible with mandatory flag
- ✅ All database queries tested
- ✅ Documentation complete

### Production Ready When:
- ✅ Integration tests passing
- ✅ Error handling comprehensive
- ✅ User guide written
- ✅ Performance acceptable (queries <500ms)
- ✅ Security review passed
- ✅ User acceptance testing complete

---

## Next Steps

1. **Grant file access** to C:\Projects\claude-mission-control
2. **Create task specification files** (tasks/01_database_layer.md, etc.)
3. **Run orchestrator build script** to spawn agents in parallel
4. **Review agent outputs** and iterate
5. **Manual testing** of integrated application
6. **User testing** and feedback
7. **Deploy** to production

---

## Timeline Estimate

Using orchestrator parallel execution:

- Phase 1-3 (Foundation): 2 hours (sequential)
- Phase 4 (Views): 1 hour (4 agents in parallel)
- Phase 5-6 (Integration): 1 hour (sequential)
- Phase 7-8 (Docs + Review): 1 hour (sequential)

**Total: ~5 hours of agent time (not wall clock time due to parallelization)**

---

## Appendix: Orchestrator Agent Capabilities

**coder-haiku:**
- Fast Python code generation
- Follows specifications well
- Good for boilerplate and CRUD operations
- Cost-effective for bulk code generation

**reviewer-sonnet:**
- Thorough code review
- Security-focused
- Catches edge cases
- Good documentation feedback

**tester-haiku:**
- Integration test generation
- Test coverage analysis
- pytest fixtures and parametrization

**analyst-sonnet:**
- Documentation writing
- Architecture analysis
- User guide creation
- Decision documentation

---

**Version:** 1.0
**Created:** 2025-11-15
**Owner:** claude-code-unified
**Status:** Ready for execution
