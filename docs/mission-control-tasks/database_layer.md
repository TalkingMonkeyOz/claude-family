# Database Layer

**Agent:** coder-haiku
**Timeout:** 300s
**Files:** 6

## Task Specification

Build the database layer for Claude Mission Control.

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
