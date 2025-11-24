# Services Layer

**Agent:** coder-haiku
**Timeout:** 240s
**Files:** 2

## Task Specification

Build the services layer.

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
