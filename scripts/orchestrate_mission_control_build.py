#!/usr/bin/env python3
"""
Mission Control Build Orchestrator

Uses orchestrator MCP to spawn specialized agents to build Mission Control in parallel.

Usage:
    python scripts/orchestrate_mission_control_build.py

Requires:
    - orchestrator MCP server running
    - File access to C:/Projects/claude-mission-control

Author: claude-code-unified
Created: 2025-11-15
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import MCP tools
sys.path.insert(0, str(Path(__file__).parent.parent))

# Task specifications for each build component
TASKS = [
    {
        "id": "database_layer",
        "name": "Database Layer",
        "agent": "coder-haiku",
        "timeout": 300,
        "description": "Build complete database layer with connection pooling and query modules",
        "files": [
            "src/database/connection.py",
            "src/database/projects.py",
            "src/database/sessions.py",
            "src/database/feedback.py",
            "src/database/procedures.py",
            "src/database/knowledge.py"
        ],
        "task_spec": """Build the database layer for Claude Mission Control.

Location: C:/Projects/claude-mission-control/src/database/

Create these 6 files:

1. **connection.py** - PostgreSQL connection management
   - get_connection_pool() -> SimpleConnectionPool
   - class DatabaseConnection (context manager for connections)
   - execute_query(query, params=None, fetch=True) -> list[dict] | None
   - Use psycopg2 with RealDictCursor (return dicts, not tuples)
   - Load credentials from .env file (dotenv)

2. **projects.py** - Project workspace queries
   Schema: claude_family.project_workspaces
   Functions:
   - get_all_projects() -> list[dict]
   - get_project_by_name(project_name: str) -> dict | None
   - get_project_summary() -> list[dict]  # With last session + open feedback count

3. **sessions.py** - Session history queries
   Schema: claude_family.session_history
   Functions:
   - get_recent_sessions(limit: int = 20) -> list[dict]
   - get_sessions_by_project(project_name: str) -> list[dict]
   - get_sessions_by_identity(identity_id: uuid) -> list[dict]
   - get_session_by_id(session_id: uuid) -> dict | None
   - get_unclosed_sessions() -> list[dict]

4. **feedback.py** - Feedback CRUD operations
   Schema: claude_pm.project_feedback, claude_pm.project_feedback_comments
   Functions:
   - get_all_feedback(filters: dict = None) -> list[dict]
   - get_feedback_by_id(feedback_id: uuid) -> dict | None
   - create_feedback(project_id: uuid, feedback_type: str, description: str, ...) -> uuid
   - update_feedback_status(feedback_id: uuid, status: str) -> None
   - add_comment(feedback_id: uuid, comment_text: str, author_identity_id: uuid) -> uuid
   - get_comments(feedback_id: uuid) -> list[dict]

5. **procedures.py** - Procedure registry queries
   Schema: claude_family.procedure_registry
   Functions:
   - get_all_procedures() -> list[dict]
   - get_procedures_for_project(project_name: str) -> list[dict]
   - get_mandatory_procedures() -> list[dict]
   - get_procedure_by_id(procedure_id: uuid) -> dict | None

6. **knowledge.py** - Shared knowledge queries
   Schema: claude_family.shared_knowledge
   Functions:
   - search_knowledge(query: str) -> list[dict]
   - get_knowledge_by_category(category: str) -> list[dict]
   - get_all_knowledge() -> list[dict]

Requirements:
- All functions have comprehensive docstrings with examples
- Use parameterized queries (never string concatenation)
- Return list of dicts (RealDictCursor)
- Proper error handling
- Type hints on all functions

Reference: C:/Projects/claude-family/scripts/load_claude_startup_context.py for PostgreSQL patterns.
"""
    },

    {
        "id": "models_layer",
        "name": "Models Layer",
        "agent": "coder-haiku",
        "timeout": 180,
        "description": "Create dataclass models for type safety",
        "files": [
            "src/models/project.py",
            "src/models/session.py",
            "src/models/feedback.py",
            "src/models/procedure.py"
        ],
        "task_spec": """Build the models layer using Python dataclasses.

Location: C:/Projects/claude-mission-control/src/models/

Create these 4 files with dataclasses:

1. **project.py**
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

@dataclass
class Project:
    workspace_id: UUID
    project_name: str
    project_path: str
    project_type: str
    description: str
    created_at: datetime
    updated_at: datetime
    last_session_time: Optional[datetime] = None
    last_session_identity: Optional[str] = None
    open_feedback_count: int = 0
```

2. **session.py** - Session dataclass with all session_history fields

3. **feedback.py** - FeedbackItem and FeedbackComment dataclasses

4. **procedure.py** - Procedure dataclass

Requirements:
- Use dataclasses for all models
- Include type hints (UUID, datetime, Optional, etc.)
- Add __str__ methods for debugging
- Include from_dict() class method to create from database row
"""
    },

    {
        "id": "services_layer",
        "name": "Services Layer",
        "agent": "coder-haiku",
        "timeout": 240,
        "description": "Build business logic services",
        "files": [
            "src/services/launcher_service.py",
            "src/services/sql_generator.py"
        ],
        "task_spec": """Build the services layer.

Location: C:/Projects/claude-mission-control/src/services/

Create these 2 files:

1. **launcher_service.py**
   Functions:
   - launch_claude_code(project_path: str, project_name: str) -> bool
     - Use subprocess.Popen to spawn Claude Code
     - Set working directory to project_path
     - Return True if successful

   - check_unclosed_sessions(project_name: str) -> list[dict]
     - Query database for unclosed sessions in this project
     - Return list of session dicts

   - get_mandatory_procedures(project_name: str) -> list[str]
     - Query procedure_registry for mandatory procedures
     - Return list of procedure names

   - generate_launch_context(project_name: str) -> str
     - Generate summary text for user before launching
     - Include: unclosed sessions, mandatory procedures, open feedback

2. **sql_generator.py**
   Functions:
   - generate_session_end_sql(session_id: uuid) -> str
     - Generate pre-filled UPDATE query for session_history
     - Include placeholders for user to fill in (summary, tasks, learnings)

   - generate_create_feedback_sql(project_id: uuid, feedback_type: str) -> str
     - Generate INSERT query for project_feedback

   - generate_add_knowledge_sql(title: str, category: str) -> str
     - Generate INSERT query for shared_knowledge

Requirements:
- All SQL strings properly formatted (multi-line, indented)
- Placeholder comments for user-fillable values
- Proper error handling
"""
    }
]

def print_header(text: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def build_with_orchestrator():
    """
    Execute build using orchestrator MCP to spawn agents.

    Note: This script documents the PLAN but cannot actually spawn agents
    because we're running in a session without MCP access in the script.

    To execute for real:
    1. Copy this task spec to Mission Control implementation plan
    2. User manually spawns agents via orchestrator MCP
    3. OR build a proper MCP client script
    """

    print_header("Mission Control Build Plan - Orchestrator Strategy")

    print("This script documents the build plan using orchestrator agents.")
    print("To execute, spawn these agents manually:\n")

    for i, task in enumerate(TASKS, 1):
        print(f"{i}. Agent: {task['agent']}")
        print(f"   Task: {task['name']}")
        print(f"   Timeout: {task['timeout']}s")
        print(f"   Files: {len(task['files'])}")
        print(f"   ID: {task['id']}")
        print()

    print("\nTo spawn an agent:")
    print("  mcp__orchestrator__spawn_agent(")
    print("      agent_type='coder-haiku',")
    print("      task='<task_spec from TASKS[i]>',")
    print("      workspace_dir='C:/Projects/claude-mission-control',")
    print("      timeout=300")
    print("  )")

    print("\nTask specifications saved to:")
    tasks_dir = Path("C:/Projects/claude-family/docs/mission-control-tasks")
    tasks_dir.mkdir(exist_ok=True)

    for task in TASKS:
        task_file = tasks_dir / f"{task['id']}.md"
        with open(task_file, 'w') as f:
            f.write(f"# {task['name']}\n\n")
            f.write(f"**Agent:** {task['agent']}\n")
            f.write(f"**Timeout:** {task['timeout']}s\n")
            f.write(f"**Files:** {len(task['files'])}\n\n")
            f.write("## Task Specification\n\n")
            f.write(task['task_spec'])

        print(f"  - {task_file}")

    print("\n" + "="*60)
    print("  Build plan ready!")
    print("="*60)

if __name__ == "__main__":
    build_with_orchestrator()
