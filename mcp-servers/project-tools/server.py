#!/usr/bin/env python3
"""
Claude Project Tools - MCP Server for Project Support

Provides project-aware tooling that makes development easier:
- Project context loading (CLAUDE.md, settings, tech stack)
- Todo management (restore, convert to build_tasks)
- Work tracking (feedback, features, build_tasks) with validation
- Skill discovery (search skill_content by task)

Tools:
- get_project_context: Load project info, settings, active work
- get_incomplete_todos: Get unfinished todos from any session
- restore_session_todos: Load past session's todos (returns data for TodoWrite)
- create_feedback: Create feedback with column_registry validation
- create_feature: Create feature with plan_data
- add_build_task: Add task to a feature
- get_ready_tasks: Get unblocked build_tasks for a project
- update_work_status: Update status of feedback/feature/build_task
- find_skill: Search skill_content by task description
- todos_to_build_tasks: Convert session todos to persistent build_tasks

Author: Claude Family
Created: 2026-01-17
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime
import re

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# PostgreSQL (supports both psycopg2 and psycopg3)
POSTGRES_AVAILABLE = False
psycopg = None

try:
    import psycopg
    from psycopg.rows import dict_row
    POSTGRES_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        POSTGRES_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        POSTGRES_AVAILABLE = False
        PSYCOPG_VERSION = 0
        print("ERROR: Neither psycopg nor psycopg2 installed.", file=sys.stderr)
        sys.exit(1)

# Initialize MCP server
app = Server("claude-project-tools")

# ============================================================================
# Database Connection
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        # Local development fallback
        conn_string = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost:5432/ai_company_foundation'

    if PSYCOPG_VERSION == 3:
        return psycopg.connect(conn_string, row_factory=dict_row)
    else:
        return psycopg.connect(conn_string, cursor_factory=RealDictCursor)


# ============================================================================
# Validation Helpers
# ============================================================================

# Cache for column_registry valid values
_valid_values_cache: Dict[str, Dict[str, List]] = {}

def get_valid_values(table_name: str, column_name: str) -> Optional[List]:
    """Get valid values from column_registry with caching."""
    cache_key = f"{table_name}.{column_name}"

    if cache_key not in _valid_values_cache:
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT valid_values FROM claude.column_registry
                WHERE table_name = %s AND column_name = %s
            """, (table_name, column_name))
            row = cur.fetchone()
            cur.close()
            _valid_values_cache[cache_key] = row['valid_values'] if row else None
        finally:
            conn.close()

    return _valid_values_cache.get(cache_key)


def validate_value(table_name: str, column_name: str, value: Any) -> tuple[bool, str]:
    """Validate a value against column_registry."""
    valid_values = get_valid_values(table_name, column_name)
    if valid_values is None:
        return True, ""  # No constraint defined

    if value not in valid_values:
        return False, f"Invalid {column_name}: '{value}'. Valid values: {valid_values}"

    return True, ""


def get_project_id(project_identifier: str) -> Optional[str]:
    """Get project_id from name or path."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Try by name first
        cur.execute("""
            SELECT p.project_id::text
            FROM claude.projects p
            JOIN claude.workspaces w ON p.project_id = w.project_id
            WHERE w.project_name = %s OR w.project_path = %s OR p.project_name = %s
            LIMIT 1
        """, (project_identifier, project_identifier, project_identifier))
        row = cur.fetchone()
        cur.close()
        return row['project_id'] if row else None
    finally:
        conn.close()


# ============================================================================
# Tool Implementations
# ============================================================================

async def tool_get_project_context(project_path: str) -> Dict:
    """
    Load comprehensive project context.

    Returns: project info, settings, tech stack, active features, pending todos
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get project and workspace info
        cur.execute("""
            SELECT
                p.project_id::text,
                p.project_name,
                p.status as project_status,
                p.phase,
                p.priority,
                w.project_path,
                w.project_type,
                w.startup_config
            FROM claude.workspaces w
            LEFT JOIN claude.projects p ON w.project_id = p.project_id
            WHERE w.project_path = %s OR w.project_name = %s
            LIMIT 1
        """, (project_path, project_path))

        project_row = cur.fetchone()
        if not project_row:
            return {"error": f"Project not found: {project_path}"}

        project_id = project_row['project_id']
        result = {
            "project_id": project_id,
            "project_name": project_row['project_name'],
            "project_path": project_row['project_path'],
            "project_type": project_row['project_type'],
            "status": project_row['project_status'],
            "phase": project_row['phase'],
            "priority": project_row['priority'],
            "startup_config": project_row['startup_config'] or {}
        }

        if project_id:
            # Get active features
            cur.execute("""
                SELECT 'F' || short_code as code, feature_name, status, priority
                FROM claude.features
                WHERE project_id = %s::uuid
                  AND status NOT IN ('completed', 'cancelled')
                ORDER BY priority, short_code
                LIMIT 10
            """, (project_id,))
            result["active_features"] = [dict(r) for r in cur.fetchall()]

            # Get pending feedback count
            cur.execute("""
                SELECT COUNT(*) as count
                FROM claude.feedback
                WHERE project_id = %s::uuid
                  AND status IN ('new', 'triaged', 'in_progress')
            """, (project_id,))
            result["pending_feedback_count"] = cur.fetchone()['count']

            # Get incomplete todos
            cur.execute("""
                SELECT COUNT(*) as count
                FROM claude.todos
                WHERE project_id = %s::uuid
                  AND status IN ('pending', 'in_progress')
                  AND NOT is_deleted
            """, (project_id,))
            result["incomplete_todos_count"] = cur.fetchone()['count']

            # Get last session
            cur.execute("""
                SELECT session_id::text, session_start, session_summary
                FROM claude.sessions
                WHERE project_name = %s
                ORDER BY session_start DESC
                LIMIT 1
            """, (project_row['project_name'],))
            last_session = cur.fetchone()
            if last_session:
                result["last_session"] = {
                    "session_id": last_session['session_id'],
                    "started": last_session['session_start'].isoformat() if last_session['session_start'] else None,
                    "summary": last_session['session_summary']
                }

        # Try to detect tech stack from project_type
        tech_stack = []
        project_type = project_row['project_type'] or ''
        if 'react' in project_type.lower() or 'tauri' in project_type.lower():
            tech_stack.extend(['React', 'TypeScript'])
        if 'tauri' in project_type.lower():
            tech_stack.extend(['Tauri', 'Rust'])
        if 'mui' in project_type.lower():
            tech_stack.append('MUI')
        if 'winforms' in project_type.lower():
            tech_stack.extend(['C#', 'WinForms'])
        if 'wpf' in project_type.lower():
            tech_stack.extend(['C#', 'WPF'])
        if 'nextjs' in project_type.lower():
            tech_stack.extend(['Next.js', 'React', 'TypeScript'])
        if 'python' in project_type.lower():
            tech_stack.append('Python')

        result["tech_stack"] = list(set(tech_stack))

        cur.close()
        return result

    finally:
        conn.close()


async def tool_get_incomplete_todos(project: str) -> Dict:
    """Get incomplete todos for a project."""
    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project not found: {project}"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                t.todo_id::text,
                t.content,
                t.active_form,
                t.status,
                t.priority,
                t.display_order,
                t.created_session_id::text,
                s.session_start
            FROM claude.todos t
            LEFT JOIN claude.sessions s ON t.created_session_id = s.session_id
            WHERE t.project_id = %s::uuid
              AND t.status IN ('pending', 'in_progress')
              AND NOT t.is_deleted
            ORDER BY
                CASE t.status WHEN 'in_progress' THEN 0 ELSE 1 END,
                t.priority,
                t.display_order
        """, (project_id,))

        todos = []
        for row in cur.fetchall():
            todos.append({
                "todo_id": row['todo_id'],
                "content": row['content'],
                "active_form": row['active_form'],
                "status": row['status'],
                "priority": row['priority'],
                "display_order": row['display_order'],
                "session_id": row['created_session_id'],
                "session_date": row['session_start'].isoformat() if row['session_start'] else None
            })

        cur.close()

        return {
            "project_id": project_id,
            "total": len(todos),
            "in_progress": len([t for t in todos if t['status'] == 'in_progress']),
            "pending": len([t for t in todos if t['status'] == 'pending']),
            "todos": todos
        }

    finally:
        conn.close()


async def tool_restore_session_todos(session_id: str) -> Dict:
    """
    Get todos from a specific session for restoration.

    Returns data formatted for use with TodoWrite tool.
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get session info
        cur.execute("""
            SELECT session_id::text, project_name, session_start
            FROM claude.sessions
            WHERE session_id = %s::uuid
        """, (session_id,))
        session = cur.fetchone()

        if not session:
            return {"error": f"Session not found: {session_id}"}

        # Get todos from that session (incomplete ones)
        cur.execute("""
            SELECT
                content,
                active_form,
                status,
                priority
            FROM claude.todos
            WHERE created_session_id = %s::uuid
              AND status IN ('pending', 'in_progress')
              AND NOT is_deleted
            ORDER BY
                CASE status WHEN 'in_progress' THEN 0 ELSE 1 END,
                priority,
                display_order
        """, (session_id,))

        todos_for_todowrite = []
        for row in cur.fetchall():
            todos_for_todowrite.append({
                "content": row['content'],
                "activeForm": row['active_form'],
                "status": row['status']
            })

        cur.close()

        return {
            "session_id": session['session_id'],
            "project_name": session['project_name'],
            "session_date": session['session_start'].isoformat() if session['session_start'] else None,
            "todo_count": len(todos_for_todowrite),
            "todos_for_todowrite": todos_for_todowrite,
            "usage": "Pass the 'todos_for_todowrite' array to TodoWrite to restore these todos"
        }

    finally:
        conn.close()


async def tool_create_feedback(
    project: str,
    feedback_type: str,
    description: str,
    title: Optional[str] = None,
    priority: str = "medium"
) -> Dict:
    """Create feedback with validation."""
    # Validate
    valid, msg = validate_value('feedback', 'feedback_type', feedback_type)
    if not valid:
        return {"error": msg}

    valid, msg = validate_value('feedback', 'priority', priority)
    if not valid:
        return {"error": msg}

    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project not found: {project}"}

    # Get current session ID from environment if available
    session_id = os.environ.get('CLAUDE_SESSION_ID')

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.feedback
                (feedback_id, project_id, feedback_type, title, description, priority, status, created_at, created_session_id)
            VALUES
                (gen_random_uuid(), %s::uuid, %s, %s, %s, %s, 'new', NOW(), %s)
            RETURNING feedback_id::text, short_code
        """, (project_id, feedback_type, title or description[:50], description, priority,
              session_id if session_id else None))

        result = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "success": True,
            "feedback_id": result['feedback_id'],
            "short_code": f"FB{result['short_code']}",
            "message": f"Created feedback FB{result['short_code']}: {title or description[:50]}"
        }

    finally:
        conn.close()


async def tool_create_feature(
    project: str,
    feature_name: str,
    description: str,
    feature_type: str = "feature",
    priority: int = 3,
    plan_data: Optional[Dict] = None
) -> Dict:
    """Create a feature with optional plan_data."""
    # Validate
    valid, msg = validate_value('features', 'feature_type', feature_type)
    if not valid:
        return {"error": msg}

    valid, msg = validate_value('features', 'priority', priority)
    if not valid:
        return {"error": msg}

    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project not found: {project}"}

    session_id = os.environ.get('CLAUDE_SESSION_ID')

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.features
                (feature_id, project_id, feature_name, description, feature_type, priority,
                 status, plan_data, created_at, created_session_id)
            VALUES
                (gen_random_uuid(), %s::uuid, %s, %s, %s, %s, 'planned', %s, NOW(), %s)
            RETURNING feature_id::text, short_code
        """, (project_id, feature_name, description, feature_type, priority,
              json.dumps(plan_data) if plan_data else None,
              session_id if session_id else None))

        result = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "success": True,
            "feature_id": result['feature_id'],
            "short_code": f"F{result['short_code']}",
            "message": f"Created feature F{result['short_code']}: {feature_name}"
        }

    finally:
        conn.close()


async def tool_add_build_task(
    feature_id: str,
    task_name: str,
    task_description: Optional[str] = None,
    task_type: str = "implementation",
    files_affected: Optional[List[str]] = None,
    blocked_by_task_id: Optional[str] = None
) -> Dict:
    """Add a build_task to a feature."""
    # Validate
    valid, msg = validate_value('build_tasks', 'task_type', task_type)
    if not valid:
        return {"error": msg}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get feature and project info (handle both UUID and short_code like "F69")
        if feature_id.upper().startswith('F') and feature_id[1:].isdigit():
            # Short code format (F69)
            cur.execute("""
                SELECT feature_id, project_id::text, feature_name
                FROM claude.features
                WHERE short_code = %s
            """, (int(feature_id[1:]),))
        else:
            # UUID format
            cur.execute("""
                SELECT feature_id, project_id::text, feature_name
                FROM claude.features
                WHERE feature_id = %s::uuid
            """, (feature_id,))
        feature = cur.fetchone()

        if not feature:
            return {"error": f"Feature not found: {feature_id}"}

        # Get next step_order
        cur.execute("""
            SELECT COALESCE(MAX(step_order), 0) + 1 as next_order
            FROM claude.build_tasks
            WHERE feature_id = %s
        """, (feature['feature_id'],))
        next_order = cur.fetchone()['next_order']

        session_id = os.environ.get('CLAUDE_SESSION_ID')

        cur.execute("""
            INSERT INTO claude.build_tasks
                (task_id, feature_id, project_id, task_name, task_description, task_type,
                 status, step_order, files_affected, blocked_by_task_id, created_at, created_session_id)
            VALUES
                (gen_random_uuid(), %s, %s::uuid, %s, %s, %s, 'todo', %s, %s, %s, NOW(), %s)
            RETURNING task_id::text, short_code
        """, (feature['feature_id'], feature['project_id'], task_name, task_description, task_type,
              next_order, files_affected,
              blocked_by_task_id if blocked_by_task_id else None,
              session_id if session_id else None))

        result = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "success": True,
            "task_id": result['task_id'],
            "short_code": f"BT{result['short_code']}",
            "feature": f"F{feature['feature_name']}",
            "step_order": next_order,
            "message": f"Created task BT{result['short_code']}: {task_name}"
        }

    finally:
        conn.close()


async def tool_get_ready_tasks(project: str) -> Dict:
    """Get build_tasks that are ready to work on (not blocked)."""
    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project not found: {project}"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                'BT' || bt.short_code as task_code,
                bt.task_name,
                bt.task_description,
                bt.task_type,
                bt.step_order,
                bt.files_affected,
                'F' || f.short_code as feature_code,
                f.feature_name
            FROM claude.build_tasks bt
            JOIN claude.features f ON bt.feature_id = f.feature_id
            WHERE bt.project_id = %s::uuid
              AND bt.status = 'todo'
              AND (bt.blocked_by_task_id IS NULL
                   OR bt.blocked_by_task_id IN (
                       SELECT task_id FROM claude.build_tasks WHERE status = 'completed'
                   ))
            ORDER BY f.priority, f.short_code, bt.step_order
        """, (project_id,))

        tasks = [dict(r) for r in cur.fetchall()]
        cur.close()

        return {
            "project_id": project_id,
            "ready_tasks": len(tasks),
            "tasks": tasks
        }

    finally:
        conn.close()


async def tool_update_work_status(
    item_type: str,
    item_id: str,
    new_status: str
) -> Dict:
    """Update status of feedback, feature, or build_task."""
    if item_type not in ('feedback', 'feature', 'build_task'):
        return {"error": f"Invalid item_type: {item_type}. Use: feedback, feature, build_task"}

    # Map to table
    table_map = {
        'feedback': ('feedback', 'feedback_id', 'FB'),
        'feature': ('features', 'feature_id', 'F'),
        'build_task': ('build_tasks', 'task_id', 'BT')
    }
    table, id_col, prefix = table_map[item_type]

    # Validate status
    valid, msg = validate_value(table, 'status', new_status)
    if not valid:
        return {"error": msg}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Handle short_code format (e.g., "FB12", "F5", "BT23")
        if item_id.upper().startswith(prefix):
            short_code = item_id[len(prefix):]
            cur.execute(f"""
                UPDATE claude.{table}
                SET status = %s, updated_at = NOW()
                WHERE short_code = %s
                RETURNING {id_col}::text, short_code
            """, (new_status, int(short_code)))
        else:
            # Assume UUID
            cur.execute(f"""
                UPDATE claude.{table}
                SET status = %s, updated_at = NOW()
                WHERE {id_col} = %s::uuid
                RETURNING {id_col}::text, short_code
            """, (new_status, item_id))

        result = cur.fetchone()
        if not result:
            return {"error": f"{item_type} not found: {item_id}"}

        conn.commit()
        cur.close()

        return {
            "success": True,
            "item_type": item_type,
            "item_id": result[id_col],
            "short_code": f"{prefix}{result['short_code']}",
            "new_status": new_status
        }

    finally:
        conn.close()


async def tool_find_skill(task_description: str, limit: int = 5) -> Dict:
    """Search skill_content by task description keywords."""
    # Extract keywords (simple approach)
    keywords = [w.lower() for w in re.findall(r'\b\w{3,}\b', task_description)]

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Search by task_keywords overlap - rank by cardinality of matching keywords
        cur.execute("""
            SELECT
                content_id::text,
                name,
                description,
                category,
                task_keywords,
                applies_to,
                LENGTH(content) as content_length,
                (SELECT COUNT(*) FROM unnest(task_keywords) tk
                 WHERE tk = ANY(%s::text[])) as match_count
            FROM claude.skill_content
            WHERE active = true
              AND task_keywords && %s::text[]
            ORDER BY
                match_count DESC,
                priority DESC
            LIMIT %s
        """, (keywords, keywords, limit))

        skills = [dict(r) for r in cur.fetchall()]
        cur.close()

        return {
            "query": task_description,
            "keywords_extracted": keywords[:10],
            "skills_found": len(skills),
            "skills": skills
        }

    finally:
        conn.close()


async def tool_todos_to_build_tasks(
    feature_id: str,
    project: str,
    include_completed: bool = False
) -> Dict:
    """Convert session todos to build_tasks for a feature."""
    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project not found: {project}"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Verify feature exists
        cur.execute("""
            SELECT feature_id, feature_name, short_code
            FROM claude.features
            WHERE (feature_id = %s::uuid OR ('F' || short_code) = %s)
              AND project_id = %s::uuid
        """, (feature_id, feature_id, project_id))
        feature = cur.fetchone()

        if not feature:
            return {"error": f"Feature not found: {feature_id}"}

        # Get todos to convert
        status_filter = "('pending', 'in_progress', 'completed')" if include_completed else "('pending', 'in_progress')"
        cur.execute(f"""
            SELECT todo_id, content, status
            FROM claude.todos
            WHERE project_id = %s::uuid
              AND status IN {status_filter}
              AND NOT is_deleted
            ORDER BY display_order
        """, (project_id,))

        todos = list(cur.fetchall())
        if not todos:
            return {"message": "No todos to convert"}

        # Get next step_order
        cur.execute("""
            SELECT COALESCE(MAX(step_order), 0) as max_order
            FROM claude.build_tasks
            WHERE feature_id = %s
        """, (feature['feature_id'],))
        step_order = cur.fetchone()['max_order']

        created_tasks = []
        session_id = os.environ.get('CLAUDE_SESSION_ID')

        for todo in todos:
            step_order += 1
            task_status = 'completed' if todo['status'] == 'completed' else 'todo'

            cur.execute("""
                INSERT INTO claude.build_tasks
                    (task_id, feature_id, project_id, task_name, status, step_order,
                     created_at, created_session_id)
                VALUES
                    (gen_random_uuid(), %s, %s::uuid, %s, %s, %s, NOW(), %s)
                RETURNING task_id::text, short_code
            """, (feature['feature_id'], project_id, todo['content'], task_status,
                  step_order, session_id))

            result = cur.fetchone()
            created_tasks.append({
                "task_code": f"BT{result['short_code']}",
                "task_name": todo['content'],
                "status": task_status,
                "from_todo_id": str(todo['todo_id'])
            })

            # Mark todo as archived (converted)
            cur.execute("""
                UPDATE claude.todos
                SET status = 'archived', updated_at = NOW()
                WHERE todo_id = %s
            """, (todo['todo_id'],))

        conn.commit()
        cur.close()

        return {
            "success": True,
            "feature": f"F{feature['short_code']}",
            "feature_name": feature['feature_name'],
            "tasks_created": len(created_tasks),
            "tasks": created_tasks
        }

    finally:
        conn.close()


# ============================================================================
# MCP Tool Definitions
# ============================================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return [
        Tool(
            name="get_project_context",
            description="Load comprehensive project context including CLAUDE.md equivalent info, settings, tech stack, active features, and pending work. Use at session start.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_path": {
                        "type": "string",
                        "description": "Project path or name (e.g., 'C:/Projects/claude-manager-mui' or 'claude-manager-mui')"
                    }
                },
                "required": ["project_path"]
            }
        ),
        Tool(
            name="get_incomplete_todos",
            description="Get all incomplete todos for a project across all sessions. Shows what work is pending/in_progress.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name or path"
                    }
                },
                "required": ["project"]
            }
        ),
        Tool(
            name="restore_session_todos",
            description="Get todos from a specific past session, formatted for use with TodoWrite to restore them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {
                        "type": "string",
                        "description": "Session UUID to restore todos from"
                    }
                },
                "required": ["session_id"]
            }
        ),
        Tool(
            name="create_feedback",
            description="Create a feedback item (bug, idea, question, etc.) with automatic validation against column_registry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project name or path"},
                    "feedback_type": {
                        "type": "string",
                        "description": "Type: bug, design, idea, question, change, improvement"
                    },
                    "description": {"type": "string", "description": "Detailed description"},
                    "title": {"type": "string", "description": "Short title (optional, defaults to first 50 chars of description)"},
                    "priority": {"type": "string", "description": "Priority: high, medium, low (default: medium)"}
                },
                "required": ["project", "feedback_type", "description"]
            }
        ),
        Tool(
            name="create_feature",
            description="Create a feature with optional plan_data for tracking implementation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project name or path"},
                    "feature_name": {"type": "string", "description": "Feature name"},
                    "description": {"type": "string", "description": "Feature description"},
                    "feature_type": {
                        "type": "string",
                        "description": "Type: feature, enhancement, refactor, infrastructure, documentation (default: feature)"
                    },
                    "priority": {"type": "integer", "description": "Priority 1-5 (default: 3)"},
                    "plan_data": {
                        "type": "object",
                        "description": "Optional structured plan data (requirements, risks, etc.)"
                    }
                },
                "required": ["project", "feature_name", "description"]
            }
        ),
        Tool(
            name="add_build_task",
            description="Add a build_task to a feature. Tasks are ordered by step_order.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature ID or short_code (e.g., 'F12')"},
                    "task_name": {"type": "string", "description": "Task name"},
                    "task_description": {"type": "string", "description": "Detailed description (optional)"},
                    "task_type": {
                        "type": "string",
                        "description": "Type: implementation, testing, documentation, deployment, investigation (default: implementation)"
                    },
                    "files_affected": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of files this task will modify (optional)"
                    },
                    "blocked_by_task_id": {"type": "string", "description": "Task ID that blocks this one (optional)"}
                },
                "required": ["feature_id", "task_name"]
            }
        ),
        Tool(
            name="get_ready_tasks",
            description="Get build_tasks that are ready to work on (pending and not blocked).",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {"type": "string", "description": "Project name or path"}
                },
                "required": ["project"]
            }
        ),
        Tool(
            name="update_work_status",
            description="Update status of feedback, feature, or build_task. Validates against column_registry.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "description": "Type: feedback, feature, build_task"
                    },
                    "item_id": {
                        "type": "string",
                        "description": "Item ID or short_code (e.g., 'FB12', 'F5', 'BT23')"
                    },
                    "new_status": {"type": "string", "description": "New status value"}
                },
                "required": ["item_type", "item_id", "new_status"]
            }
        ),
        Tool(
            name="find_skill",
            description="Search skill_content by task description to find relevant skills/guidelines.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_description": {
                        "type": "string",
                        "description": "Description of what you're trying to do"
                    },
                    "limit": {"type": "integer", "description": "Max results (default: 5)"}
                },
                "required": ["task_description"]
            }
        ),
        Tool(
            name="todos_to_build_tasks",
            description="Convert session todos to persistent build_tasks linked to a feature. Archives the converted todos.",
            inputSchema={
                "type": "object",
                "properties": {
                    "feature_id": {"type": "string", "description": "Feature ID or short_code to link tasks to"},
                    "project": {"type": "string", "description": "Project name or path"},
                    "include_completed": {
                        "type": "boolean",
                        "description": "Include completed todos (default: false)"
                    }
                },
                "required": ["feature_id", "project"]
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_project_context":
            result = await tool_get_project_context(arguments['project_path'])
        elif name == "get_incomplete_todos":
            result = await tool_get_incomplete_todos(arguments['project'])
        elif name == "restore_session_todos":
            result = await tool_restore_session_todos(arguments['session_id'])
        elif name == "create_feedback":
            result = await tool_create_feedback(
                arguments['project'],
                arguments['feedback_type'],
                arguments['description'],
                arguments.get('title'),
                arguments.get('priority', 'medium')
            )
        elif name == "create_feature":
            result = await tool_create_feature(
                arguments['project'],
                arguments['feature_name'],
                arguments['description'],
                arguments.get('feature_type', 'feature'),
                arguments.get('priority', 3),
                arguments.get('plan_data')
            )
        elif name == "add_build_task":
            result = await tool_add_build_task(
                arguments['feature_id'],
                arguments['task_name'],
                arguments.get('task_description'),
                arguments.get('task_type', 'implementation'),
                arguments.get('files_affected'),
                arguments.get('blocked_by_task_id')
            )
        elif name == "get_ready_tasks":
            result = await tool_get_ready_tasks(arguments['project'])
        elif name == "update_work_status":
            result = await tool_update_work_status(
                arguments['item_type'],
                arguments['item_id'],
                arguments['new_status']
            )
        elif name == "find_skill":
            result = await tool_find_skill(
                arguments['task_description'],
                arguments.get('limit', 5)
            )
        elif name == "todos_to_build_tasks":
            result = await tool_todos_to_build_tasks(
                arguments['feature_id'],
                arguments['project'],
                arguments.get('include_completed', False)
            )
        else:
            result = {"error": f"Unknown tool: {name}"}

        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
