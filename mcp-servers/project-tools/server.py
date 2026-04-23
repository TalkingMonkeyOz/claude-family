#!/usr/bin/env python3
"""
Claude Project Tools - MCP Server for Project Support

Provides project-aware tooling that makes development easier:
- Project context loading (CLAUDE.md, settings, tech stack)
- Todo management (restore, convert to build_tasks)
- Work tracking (feedback, features, build_tasks) with validation
- Skill discovery (search skill_content by task)
- Knowledge operations (store, recall, link) with semantic search
- Session facts (crash-resistant cache for important info)

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
- store_knowledge: Store new knowledge with automatic embedding
- recall_knowledge: Semantic search over knowledge entries
- link_knowledge: Create typed relations between knowledge entries
- store_session_fact: Cache important facts (credentials, configs) within session
- recall_session_fact: Retrieve a fact by key
- list_session_facts: List all facts in current session
- recall_previous_session_facts: Recover facts from previous sessions (after compaction)
- store_session_notes: Store structured notes (decisions, progress, blockers) - survives crashes
- get_session_notes: Retrieve session notes for current project

Author: Claude Family
Created: 2026-01-17
Updated: 2026-01-23
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
from datetime import datetime
import re

# For Voyage AI embeddings
try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    print("WARNING: requests not installed. Knowledge embedding disabled.", file=sys.stderr)

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
app = Server("project-tools")

# ============================================================================
# Database Connection
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection."""
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        raise RuntimeError("DATABASE_URI or POSTGRES_CONNECTION_STRING environment variable required")

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
# Embedding Helper
# ============================================================================

EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"  # FastEmbed local model

# Ensure embedding_provider is importable
_embedding_provider_path = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts')
if os.path.abspath(_embedding_provider_path) not in sys.path:
    sys.path.insert(0, os.path.abspath(_embedding_provider_path))


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding using the configured provider (FastEmbed local or Voyage AI API).

    Uses embedding_provider.py abstraction. Default: FastEmbed (local CPU, no API key).
    Set EMBEDDING_PROVIDER=voyage env var to use Voyage AI instead.
    """
    try:
        from embedding_provider import embed
        result = embed(text)
        if result is None:
            # embed() already logs the reason — just note it here
            print(f"[server] generate_embedding returned None for text ({len(text) if text else 0} chars)", file=sys.stderr)
        return result
    except Exception as e:
        import traceback
        print(f"[server] generate_embedding FAILED: {e}\n{traceback.format_exc()}", file=sys.stderr)
        return None


def generate_query_embedding(query: str) -> Optional[List[float]]:
    """Generate embedding for a query. Same as generate_embedding (FastEmbed doesn't distinguish)."""
    return generate_embedding(query)




def format_knowledge_for_embedding(entry: dict) -> str:
    """Format a knowledge entry as text for embedding."""
    parts = []

    if entry.get('title'):
        parts.append(f"# {entry['title']}")

    if entry.get('knowledge_type') or entry.get('knowledge_category'):
        type_cat = f"Type: {entry.get('knowledge_type', 'unknown')}"
        if entry.get('knowledge_category'):
            type_cat += f" | Category: {entry['knowledge_category']}"
        parts.append(type_cat)

    if entry.get('description'):
        parts.append(entry['description'])

    if entry.get('code_example'):
        parts.append(f"\nCode Example:\n{entry['code_example']}")

    if entry.get('applies_to_projects'):
        projects = ', '.join(entry['applies_to_projects']) if isinstance(entry['applies_to_projects'], list) else str(entry['applies_to_projects'])
        parts.append(f"\nApplies to: {projects}")

    return '\n\n'.join(parts)


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

        # Dedup check: reject if a non-cancelled task with same name exists
        cur.execute("""
            SELECT 'BT' || short_code as task_code, status
            FROM claude.build_tasks
            WHERE feature_id = %s AND task_name = %s AND status != 'cancelled'
        """, (feature['feature_id'], task_name))
        existing = cur.fetchone()
        if existing:
            return {
                "error": f"Duplicate: '{task_name}' already exists as {existing['task_code']} "
                         f"(status: {existing['status']})"
            }

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
            "feature": feature['feature_name'],
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
# Knowledge Tool Implementations
# ============================================================================

async def tool_store_knowledge(
    title: str,
    description: str,
    knowledge_type: str = "learned",
    knowledge_category: Optional[str] = None,
    code_example: Optional[str] = None,
    applies_to_projects: Optional[List[str]] = None,
    applies_to_platforms: Optional[List[str]] = None,
    confidence_level: int = 80,
    source: Optional[str] = None
) -> Dict:
    """Store new knowledge with automatic embedding."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Create the knowledge entry
        entry = {
            'title': title,
            'description': description,
            'knowledge_type': knowledge_type,
            'knowledge_category': knowledge_category,
            'code_example': code_example,
            'applies_to_projects': applies_to_projects
        }

        # Generate embedding
        text_for_embedding = format_knowledge_for_embedding(entry)
        embedding = generate_embedding(text_for_embedding)

        if embedding:
            cur.execute("""
                INSERT INTO claude.knowledge
                    (knowledge_id, title, description, knowledge_type, knowledge_category,
                     code_example, applies_to_projects, applies_to_platforms,
                     confidence_level, source, embedding, tier, created_at)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, 'mid', NOW())
                RETURNING knowledge_id::text
            """, (title, description, knowledge_type, knowledge_category, code_example,
                  applies_to_projects, applies_to_platforms, confidence_level, source,
                  embedding))
        else:
            # Store without embedding if generation failed
            cur.execute("""
                INSERT INTO claude.knowledge
                    (knowledge_id, title, description, knowledge_type, knowledge_category,
                     code_example, applies_to_projects, applies_to_platforms,
                     confidence_level, source, tier, created_at)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, 'mid', NOW())
                RETURNING knowledge_id::text
            """, (title, description, knowledge_type, knowledge_category, code_example,
                  applies_to_projects, applies_to_platforms, confidence_level, source))

        result = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "success": True,
            "knowledge_id": result['knowledge_id'],
            "title": title,
            "has_embedding": embedding is not None,
            "message": f"Stored knowledge: {title}"
        }

    except Exception as e:
        return {"error": f"Failed to store knowledge: {str(e)}"}
    finally:
        conn.close()


async def tool_recall_knowledge(
    query: str,
    limit: int = 5,
    knowledge_type: Optional[str] = None,
    project: Optional[str] = None,
    min_similarity: float = 0.5,
    domain: Optional[str] = None,
    source_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    date_range_days: Optional[int] = None
) -> Dict:
    """Semantic search over knowledge entries with structured filters."""
    # Generate query embedding (uses FastEmbed local or Voyage AI based on EMBEDDING_PROVIDER)
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        return {"error": "Failed to generate query embedding — embedding service may be unavailable"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Build query with optional filters
        filters = []
        filter_params = []

        if knowledge_type:
            filters.append("AND knowledge_type = %s")
            filter_params.append(knowledge_type)

        if project:
            filters.append("AND (%s = ANY(applies_to_projects) OR applies_to_projects IS NULL)")
            filter_params.append(project)

        if domain:
            filters.append("AND knowledge_category ILIKE %s")
            filter_params.append(f"%{domain}%")

        if source_type:
            filters.append("AND source ILIKE %s")
            filter_params.append(f"%{source_type}%")

        if tags and len(tags) > 0:
            # No dedicated tags column - match against knowledge_category
            tag_conditions = " OR ".join(["knowledge_category ILIKE %s" for _ in tags])
            filters.append(f"AND ({tag_conditions})")
            filter_params.extend([f"%{t}%" for t in tags])

        if date_range_days is not None and date_range_days > 0:
            filters.append("AND created_at > NOW() - INTERVAL %s")
            filter_params.append(f"{date_range_days} days")

        filter_clause = " ".join(filters)

        # Parameters in order: similarity SELECT, WHERE similarity calc, min_similarity, ...filters, limit
        params = [query_embedding, query_embedding, min_similarity] + filter_params + [limit]

        cur.execute(f"""
            SELECT
                knowledge_id::text,
                title,
                description,
                knowledge_type,
                knowledge_category,
                code_example,
                applies_to_projects,
                confidence_level,
                times_applied,
                1 - (embedding <=> %s::vector) as similarity
            FROM claude.knowledge
            WHERE embedding IS NOT NULL
              AND tier != 'archived'
              AND 1 - (embedding <=> %s::vector) >= %s
              {filter_clause}
            ORDER BY similarity DESC
            LIMIT %s
        """, params)

        results = []
        for row in cur.fetchall():
            # Update access tracking
            cur.execute("""
                UPDATE claude.knowledge
                SET last_accessed_at = NOW(),
                    access_count = COALESCE(access_count, 0) + 1
                WHERE knowledge_id = %s::uuid
            """, (row['knowledge_id'],))

            results.append({
                "knowledge_id": row['knowledge_id'],
                "title": row['title'],
                "description": row['description'],
                "knowledge_type": row['knowledge_type'],
                "knowledge_category": row['knowledge_category'],
                "code_example": row['code_example'],
                "applies_to_projects": row['applies_to_projects'],
                "confidence_level": row['confidence_level'],
                "times_applied": row['times_applied'],
                "similarity": round(float(row['similarity']), 4)
            })

        conn.commit()
        cur.close()

        return {
            "query": query,
            "results_count": len(results),
            "min_similarity": min_similarity,
            "results": results
        }

    except Exception as e:
        return {"error": f"Knowledge recall failed: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Workfile Tools (Project-Scoped Component Working Context)
# ============================================================================

def _section_id(record_id: str, slug: str) -> str:
    """Deterministic section_id for non-persisted section addressing (workfiles, entities).

    Same (record_id, slug) always produces same id. Enables TOC + fetch-section patterns
    without requiring a section table for every record type.
    """
    import hashlib
    h = hashlib.sha1(f"{record_id}|{slug}".encode()).hexdigest()[:12]
    return f"sec-{h}"


def _estimate_tokens_fast(text: str) -> int:
    """Rough token estimate: ~4 chars per token."""
    return max(1, len(text or "") // 4)


# Memory tier truncation threshold (chars). Above this, body is truncated with
# `content_truncated` flag + full length info so Claude knows to re-query for detail.
MEMORY_TRUNCATE_THRESHOLD = 1500
MEMORY_TRUNCATE_TO = 800


def _truncate_memory_content(content: str) -> Tuple[str, bool, int]:
    """Truncate memory content with visibility.

    Returns (content, truncated, full_length). If content <= threshold, returns
    unchanged. Above threshold, returns first N chars + '…' + flag.
    """
    if not content:
        return "", False, 0
    full_len = len(content)
    if full_len <= MEMORY_TRUNCATE_THRESHOLD:
        return content, False, full_len
    trimmed = content[:MEMORY_TRUNCATE_TO].rstrip() + "…"
    return trimmed, True, full_len


def _build_toc(content: str, record_id: str, include_summary: bool = True) -> Dict:
    """Parse markdown content and build TOC envelope.

    Returns {toc: [{section_id, title, slug, token_count, summary?}],
             sections_by_id: {section_id: body},
             section_count: int,
             total_tokens: int}.
    """
    parts = _split_on_h2(content, target_lines=400)
    toc = []
    sections_by_id = {}
    total_tokens = 0
    for slug, body in parts:
        sid = _section_id(record_id, slug)
        # Recover title from body's first H2 line, else use slug
        title = slug.replace('-', ' ').title()
        first_line = body.split('\n', 1)[0].strip() if body else ''
        if first_line.startswith('##'):
            title = first_line.lstrip('#').strip()
        tokens = _estimate_tokens_fast(body)
        entry = {
            "section_id": sid,
            "title": title,
            "slug": slug,
            "token_count": tokens,
        }
        if include_summary:
            # Summary = first non-header non-empty line
            summary = ''
            for ln in body.split('\n'):
                stripped = ln.strip()
                if stripped and not stripped.startswith('#'):
                    summary = stripped[:200]
                    break
            if summary:
                entry["summary"] = summary
        toc.append(entry)
        sections_by_id[sid] = body
        total_tokens += tokens
    return {
        "toc": toc,
        "sections_by_id": sections_by_id,
        "section_count": len(toc),
        "total_tokens": total_tokens,
    }


# Records above this line count auto-qualify for TOC mode when detail is not specified.
TOC_AUTO_THRESHOLD_LINES = 200


def _should_use_toc(content: str, detail: str) -> bool:
    """Decide whether to return TOC envelope vs full body.

    - detail='toc' → always TOC
    - detail='full' → never TOC
    - detail='' (default) → TOC if content has >=2 H2 headers AND exceeds threshold
    """
    if detail == "toc":
        return True
    if detail == "full":
        return False
    if not content:
        return False
    lines = content.count('\n') + 1
    if lines < TOC_AUTO_THRESHOLD_LINES:
        return False
    import re as _re
    h2_count = len(_re.findall(r'(?m)^##\s', content))
    return h2_count >= 2


def _split_on_h2(content: str, target_lines: int = 400) -> List[Tuple[str, str]]:
    """Split markdown content into (section_title, section_body) pairs on H2 headers.

    Returns list of (slug, body) tuples. If no H2 headers present or fewer than 2,
    falls back to size-based splits with generic part-N slugs.
    """
    import re as _re
    lines = content.split('\n')
    h2_indices = [i for i, ln in enumerate(lines) if _re.match(r'^##\s', ln)]

    if len(h2_indices) >= 2:
        # Preamble is everything before the first H2 (becomes "intro" if non-empty)
        parts = []
        if h2_indices[0] > 0:
            preamble = '\n'.join(lines[:h2_indices[0]]).strip()
            if preamble:
                parts.append(("intro", preamble))
        # Each H2 starts a new section
        for idx, start in enumerate(h2_indices):
            end = h2_indices[idx + 1] if idx + 1 < len(h2_indices) else len(lines)
            section_lines = lines[start:end]
            header = section_lines[0].lstrip('#').strip()
            slug = _re.sub(r'[^a-zA-Z0-9\s-]', '', header).strip().lower()
            slug = _re.sub(r'\s+', '-', slug)[:50] or f"section-{idx + 1}"
            body = '\n'.join(section_lines).strip()
            parts.append((slug, body))
        return parts

    # Fallback: size-based split at target_lines boundaries
    parts = []
    for idx in range(0, len(lines), target_lines):
        chunk = '\n'.join(lines[idx:idx + target_lines]).strip()
        if chunk:
            parts.append((f"part-{len(parts) + 1}", chunk))
    return parts


async def tool_stash(
    component: str,
    title: str,
    content: str,
    project: str = "",
    workfile_type: str = "notes",
    tags: Optional[List[str]] = None,
    feature_code: Optional[str] = None,
    is_pinned: bool = False,
    mode: str = "replace",
    auto_chunk: bool = False,
) -> Dict:
    """Store/update a workfile. UPSERT on (project, component, title).

    If auto_chunk=True AND content exceeds 500 lines, the file is automatically
    split on H2 headers (or size-based if none): parent becomes an index with
    links to sub-workfiles named '{title}-{slug}'. Default False preserves
    existing behavior.
    """
    project = project or os.path.basename(os.getcwd())

    # Validate workfile_type
    valid, err = validate_value('project_workfiles', 'workfile_type', workfile_type)
    if not valid:
        return {"error": err}

    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    session_id = _resolve_session_id(project)

    # Auto-chunk path: split into linked records BEFORE writing the main file.
    line_count_in = content.count('\n') + 1
    auto_chunk_info = None
    if auto_chunk and line_count_in > 500 and mode in ('replace', 'append'):
        # For append mode, fetch and concatenate first so chunking sees full content
        if mode == 'append':
            _conn = get_db_connection()
            try:
                _cur = _conn.cursor()
                _cur.execute("""
                    SELECT content FROM claude.project_workfiles
                    WHERE project_id = %s::uuid AND component = %s AND title = %s AND is_active = TRUE
                """, (project_id, component, title))
                _existing = _cur.fetchone()
                if _existing:
                    content = _existing['content'] + "\n---\n" + content
                    line_count_in = content.count('\n') + 1
                _cur.close()
            finally:
                _conn.close()
            mode = 'replace'  # subsequent write is full rewrite of the index

        parts = _split_on_h2(content, target_lines=400)
        if len(parts) >= 2:
            sub_titles = []
            for slug, body in parts:
                sub_title = f"{title}-{slug}"
                sub_line_count = body.count('\n') + 1
                # Recursive inline write for each part (no auto_chunk on sub-writes)
                sub_embed = generate_embedding(f"{component} {sub_title} {body[:500]}")
                _conn2 = get_db_connection()
                try:
                    _cur2 = _conn2.cursor()
                    _cur2.execute("""
                        INSERT INTO claude.project_workfiles
                            (project_id, component, title, content, workfile_type, tags,
                             feature_code, is_pinned, linked_sessions, embedding, updated_at)
                        VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, ARRAY[%s]::uuid[], %s::vector, NOW())
                        ON CONFLICT (project_id, component, title) DO UPDATE SET
                            content = EXCLUDED.content,
                            workfile_type = EXCLUDED.workfile_type,
                            tags = COALESCE(EXCLUDED.tags, project_workfiles.tags),
                            embedding = EXCLUDED.embedding,
                            updated_at = NOW()
                    """, (project_id, component, sub_title, body, workfile_type, tags,
                          feature_code, False, session_id, sub_embed))
                    _conn2.commit()
                    _cur2.close()
                finally:
                    _conn2.close()
                sub_titles.append({"title": sub_title, "lines": sub_line_count})

            # Build index content for the parent
            index_lines = [f"# {title} (INDEX)", ""]
            index_lines.append(
                f"*This workfile was auto-chunked from {line_count_in} lines into "
                f"{len(parts)} linked sub-workfiles per the chunking rule (300-500 lines).*"
            )
            index_lines.append("")
            index_lines.append("## Parts")
            index_lines.append("")
            for st in sub_titles:
                index_lines.append(
                    f"- [{component}/{st['title']}](workfile://{project}/{component}/{st['title']}) "
                    f"({st['lines']} lines)"
                )
            index_lines.append("")
            index_lines.append(
                "Fetch any part with `workfile_read(component, title)` where title is from the list above."
            )
            content = '\n'.join(index_lines)
            auto_chunk_info = {
                "split_into": sub_titles,
                "parent_kept_as_index": True,
                "original_line_count": line_count_in,
            }

    # Generate embedding (after potential index rewrite)
    embed_text = f"{component} {title} {content[:500]}"
    embedding = generate_embedding(embed_text)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if mode == "append":
            # Fetch existing content to append to
            cur.execute("""
                SELECT content FROM claude.project_workfiles
                WHERE project_id = %s::uuid AND component = %s AND title = %s AND is_active = TRUE
            """, (project_id, component, title))
            existing = cur.fetchone()
            if existing:
                content = existing['content'] + "\n---\n" + content

        # UPSERT
        cur.execute("""
            INSERT INTO claude.project_workfiles
                (project_id, component, title, content, workfile_type, tags,
                 feature_code, is_pinned, linked_sessions, embedding, updated_at)
            VALUES (%s::uuid, %s, %s, %s, %s, %s,
                    %s, %s, ARRAY[%s]::uuid[], %s::vector, NOW())
            ON CONFLICT (project_id, component, title)
            DO UPDATE SET
                content = EXCLUDED.content,
                workfile_type = EXCLUDED.workfile_type,
                tags = COALESCE(EXCLUDED.tags, project_workfiles.tags),
                feature_code = COALESCE(EXCLUDED.feature_code, project_workfiles.feature_code),
                is_pinned = EXCLUDED.is_pinned,
                linked_sessions = (
                    SELECT array_agg(DISTINCT s)
                    FROM unnest(project_workfiles.linked_sessions || EXCLUDED.linked_sessions) s
                ),
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            RETURNING workfile_id::text, (xmax = 0) AS is_insert
        """, (
            project_id, component, title, content, workfile_type, tags,
            feature_code, is_pinned, session_id, embedding
        ))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        is_insert = row['is_insert'] if row else True
        action = "created" if is_insert else ("appended" if mode == "append" else "updated")

        # Chunking rule: 300-500 line target. Flag if exceeded so caller can split.
        line_count = content.count('\n') + 1
        result = {
            "success": True,
            "workfile_id": row['workfile_id'] if row else None,
            "action": action,
            "component": component,
            "title": title,
            "line_count": line_count,
        }
        if auto_chunk_info:
            result["auto_chunked"] = True
            result["split_info"] = auto_chunk_info
            result["action"] = "auto_chunked"
        if line_count > 500:
            # Detect natural split points (H2 headers) for the caller.
            h2_lines = [
                i + 1 for i, ln in enumerate(content.split('\n'))
                if re.match(r'^##\s', ln)
            ]
            result["chunking_required"] = True
            result["chunking_reason"] = (
                f"Workfile is {line_count} lines; chunking rule targets 300-500. "
                "Split into linked workfiles: an index with summary + links, "
                "and one sub-workfile per logical section."
            )
            if len(h2_lines) >= 2:
                result["suggested_split_points"] = h2_lines
                result["split_hint"] = (
                    f"Found {len(h2_lines)} H2 headers — split at those line numbers. "
                    f"Title the index '{title}' (keep) and name sub-workfiles "
                    f"'{title}-<section-slug>'."
                )
            else:
                result["split_hint"] = (
                    f"No clear H2 split points — split at ~400-line boundaries "
                    f"and name sub-workfiles '{title}-part-1', '{title}-part-2', etc."
                )
        return result

    except Exception as e:
        conn.rollback()
        return {"error": f"Stash failed: {str(e)}"}
    finally:
        conn.close()


async def tool_unstash(
    component: str,
    title: Optional[str] = None,
    project: str = "",
    detail: str = "",
    section_id: str = "",
) -> Dict:
    """Retrieve workfile(s). If title given, single file. If omitted, all active in component.

    detail:
      '' (default) — full content (backward compat)
      'toc'        — force TOC envelope (section list + summaries, no bodies)
      'full'       — force full content (bypass auto-TOC for large records)
    section_id: when provided, returns only that section's body (requires title).
    """
    project = project or os.path.basename(os.getcwd())

    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if title:
            cur.execute("""
                UPDATE claude.project_workfiles
                SET last_accessed_at = NOW(), access_count = access_count + 1
                WHERE project_id = %s::uuid AND component = %s AND title = %s AND is_active = TRUE
                RETURNING workfile_id::text, title, content, workfile_type,
                          tags, feature_code, is_pinned, updated_at, access_count
            """, (project_id, component, title))
        else:
            # Get all active files in component, update access stats
            cur.execute("""
                UPDATE claude.project_workfiles
                SET last_accessed_at = NOW(), access_count = access_count + 1
                WHERE project_id = %s::uuid AND component = %s AND is_active = TRUE
                RETURNING workfile_id::text, title, content, workfile_type,
                          tags, feature_code, is_pinned, updated_at, access_count
            """, (project_id, component))

        rows = cur.fetchall()
        conn.commit()
        cur.close()

        files = []
        for r in rows:
            content = r['content'] or ''
            record_id = r['workfile_id']
            base = {
                "workfile_id": record_id,
                "title": r['title'],
                "workfile_type": r['workfile_type'],
                "tags": r['tags'],
                "feature_code": r['feature_code'],
                "is_pinned": r['is_pinned'],
                "updated_at": str(r['updated_at']),
                "access_count": r['access_count'],
                "token_count": _estimate_tokens_fast(content),
            }

            # Section-id fetch: single file, specific section
            if section_id and title and r['title'] == title:
                toc_data = _build_toc(content, record_id, include_summary=False)
                section_body = toc_data['sections_by_id'].get(section_id)
                if section_body is None:
                    base["error"] = f"section_id '{section_id}' not found"
                    base["toc"] = toc_data['toc']
                    base["detail_level"] = "toc"
                else:
                    base["content"] = section_body
                    base["section_id"] = section_id
                    base["detail_level"] = "section"
                    base["toc"] = toc_data['toc']
                files.append(base)
                continue

            # Auto-TOC decision
            if _should_use_toc(content, detail):
                toc_data = _build_toc(content, record_id)
                base["toc"] = toc_data['toc']
                base["section_count"] = toc_data['section_count']
                base["total_tokens"] = toc_data['total_tokens']
                base["detail_level"] = "toc"
                base["fetch_section"] = (
                    f'workfile_read(component="{component}", title="{r["title"]}", '
                    f'section_id="<section_id from toc>")'
                )
                base["fetch_full"] = (
                    f'workfile_read(component="{component}", title="{r["title"]}", '
                    f'detail="full")'
                )
            else:
                base["content"] = content
                base["detail_level"] = "full"

            files.append(base)

        return {
            "success": True,
            "component": component,
            "file_count": len(files),
            "files": files,
        }

    except Exception as e:
        return {"error": f"Unstash failed: {str(e)}"}
    finally:
        conn.close()


async def tool_list_workfiles(
    project: str = "",
    component: Optional[str] = None,
    is_active: bool = True,
) -> Dict:
    """Browse the cabinet. Groups by component with file counts."""
    project = project or os.path.basename(os.getcwd())

    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if component:
            cur.execute("""
                SELECT title, workfile_type, is_pinned, updated_at, access_count
                FROM claude.project_workfiles
                WHERE project_id = %s::uuid AND component = %s AND is_active = %s
                ORDER BY is_pinned DESC, updated_at DESC
            """, (project_id, component, is_active))
            rows = cur.fetchall()
            cur.close()

            files = [{
                "title": r['title'],
                "workfile_type": r['workfile_type'],
                "is_pinned": r['is_pinned'],
                "updated_at": str(r['updated_at']),
                "access_count": r['access_count'],
            } for r in rows]

            return {
                "success": True,
                "project": project,
                "component": component,
                "file_count": len(files),
                "files": files,
            }
        else:
            cur.execute("""
                SELECT component,
                       COUNT(*) AS file_count,
                       MAX(updated_at) AS last_updated,
                       COUNT(*) FILTER (WHERE is_pinned) AS pinned_count
                FROM claude.project_workfiles
                WHERE project_id = %s::uuid AND is_active = %s
                GROUP BY component
                ORDER BY last_updated DESC
            """, (project_id, is_active))
            rows = cur.fetchall()
            cur.close()

            components = [{
                "name": r['component'],
                "file_count": r['file_count'],
                "last_updated": str(r['last_updated']),
                "pinned_count": r['pinned_count'],
            } for r in rows]

            return {
                "success": True,
                "project": project,
                "component_count": len(components),
                "components": components,
            }

    except Exception as e:
        return {"error": f"List workfiles failed: {str(e)}"}
    finally:
        conn.close()


async def tool_search_workfiles(
    query: str,
    project: str = "",
    component: Optional[str] = None,
    limit: int = 5,
) -> Dict:
    """Semantic search via Voyage AI embeddings + optional component filter."""
    project = project or os.path.basename(os.getcwd())

    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        return {"error": "Failed to generate query embedding"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if component:
            cur.execute("""
                SELECT workfile_id::text, component, title,
                       LEFT(content, 200) AS preview,
                       workfile_type, tags, is_pinned,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM claude.project_workfiles
                WHERE project_id = %s::uuid AND component = %s
                  AND is_active = TRUE AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, project_id, component, query_embedding, limit))
        else:
            cur.execute("""
                SELECT workfile_id::text, component, title,
                       LEFT(content, 200) AS preview,
                       workfile_type, tags, is_pinned,
                       1 - (embedding <=> %s::vector) AS similarity
                FROM claude.project_workfiles
                WHERE project_id = %s::uuid
                  AND is_active = TRUE AND embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
            """, (query_embedding, project_id, query_embedding, limit))

        rows = cur.fetchall()
        cur.close()

        results = [{
            "component": r['component'],
            "title": r['title'],
            "preview": r['preview'],
            "workfile_type": r['workfile_type'],
            "tags": r['tags'],
            "is_pinned": r['is_pinned'],
            "similarity": round(float(r['similarity']), 4),
        } for r in rows]

        return {
            "success": True,
            "query": query,
            "result_count": len(results),
            "results": results,
        }

    except Exception as e:
        return {"error": f"Search workfiles failed: {str(e)}"}
    finally:
        conn.close()


async def tool_graph_search(
    query: str,
    max_initial_hits: int = 5,
    max_hops: int = 2,
    min_edge_strength: float = 0.3,
    min_similarity: float = 0.5,
    token_budget: int = 500,
) -> Dict:
    """Graph-aware knowledge search: pgvector seed + recursive CTE graph walk."""
    # Generate query embedding (uses FastEmbed local or Voyage AI based on EMBEDDING_PROVIDER)
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        return {"error": "Failed to generate query embedding — embedding service may be unavailable"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Call the SQL function (explicit casts for psycopg type matching)
        cur.execute("""
            SELECT * FROM claude.graph_aware_search(
                %s::vector, %s::integer, %s::integer, %s::numeric, %s::numeric, %s::integer
            )
        """, (query_embedding, max_initial_hits, max_hops,
              min_edge_strength, min_similarity, token_budget))

        results = []
        knowledge_ids = []
        for row in cur.fetchall():
            knowledge_ids.append(row['knowledge_id'])
            results.append({
                "knowledge_id": str(row['knowledge_id']),
                "title": row['title'],
                "knowledge_type": row['knowledge_type'],
                "knowledge_category": row['knowledge_category'],
                "description": row['description'],
                "confidence_level": row['confidence_level'],
                "source_type": row['source_type'],
                "similarity": round(float(row['similarity']), 4),
                "graph_depth": row['graph_depth'],
                "edge_path": row['edge_path'],
                "relevance_score": round(float(row['relevance_score']), 4),
            })

        # Update access stats for all returned entries
        if knowledge_ids:
            cur.execute("""
                SELECT claude.update_knowledge_access(%s)
            """, (knowledge_ids,))

        conn.commit()
        cur.close()

        direct_count = sum(1 for r in results if r['source_type'] == 'direct')
        graph_count = sum(1 for r in results if r['source_type'] == 'graph')

        return {
            "query": query,
            "result_count": len(results),
            "direct_hits": direct_count,
            "graph_discovered": graph_count,
            "max_hops": max_hops,
            "results": results,
        }

    except Exception as e:
        return {"error": f"Graph search failed: {str(e)}"}
    finally:
        conn.close()


async def tool_decay_knowledge(
    min_strength: float = 0.05,
    stale_days: int = 90,
) -> Dict:
    """Apply decay to knowledge graph edges and find stale subgraphs."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT * FROM claude.decay_knowledge_graph(%s, %s)
        """, (min_strength, stale_days))

        row = cur.fetchone()
        conn.commit()
        cur.close()

        stale_ids = row['stale_knowledge_ids'] or []

        return {
            "success": True,
            "decayed_edges": row['decayed_count'],
            "stale_entries": row['stale_count'],
            "stale_knowledge_ids": [str(uid) for uid in stale_ids],
            "message": (
                f"Decayed {row['decayed_count']} edges. "
                f"Found {row['stale_count']} stale knowledge entries."
            ),
        }

    except Exception as e:
        return {"error": f"Knowledge decay failed: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Cognitive Memory Tools (F130)
# ============================================================================

# Token estimation: ~4 chars per token for English text
def _estimate_tokens(text: str) -> int:
    """Rough token estimate for budget management."""
    return max(1, len(text) // 4)


def _quick_knowledge_health(project_name: str, conn) -> Optional[Dict]:
    """Fast health check for a project's knowledge. Returns hint dict or None if healthy.

    Runs two cheap COUNT queries against the existing connection.
    Called from remember() and recall_memories() to nudge maintenance.
    """
    try:
        cur = conn.cursor()

        # Stale: not accessed in 90+ days, low confidence, active only
        cur.execute("""
            SELECT COUNT(*) as cnt FROM claude.knowledge
            WHERE COALESCE(status, 'active') = 'active'
              AND (applies_to_projects IS NULL OR cardinality(applies_to_projects) = 0 OR %s = ANY(applies_to_projects))
              AND COALESCE(last_accessed_at, created_at) < NOW() - INTERVAL '90 days'
              AND COALESCE(confidence_level, 50) < 60
        """, (project_name,))
        stale = cur.fetchone()['cnt']

        # Total active for this project
        cur.execute("""
            SELECT COUNT(*) as cnt FROM claude.knowledge
            WHERE COALESCE(status, 'active') = 'active'
              AND (applies_to_projects IS NULL OR cardinality(applies_to_projects) = 0 OR %s = ANY(applies_to_projects))
        """, (project_name,))
        total = cur.fetchone()['cnt']

        cur.close()

        hints = []
        if stale >= 5:
            hints.append(f"{stale} stale memories (90+ days, low confidence)")
        if total > 100:
            hints.append(f"{total} total memories — consider reviewing with list_memories()")

        if hints:
            return {
                "maintenance_hint": "Knowledge health: " + "; ".join(hints) + ". Use list_memories/archive_memory/merge_memories to clean up.",
                "stale_count": stale,
                "total_count": total,
            }
        return None

    except Exception:
        return None  # Health check is best-effort, never block the main tool


async def tool_recall_memories(
    query: str,
    budget: int = 1000,
    query_type: str = "default",
    project_name: Optional[str] = None,
) -> Dict:
    """Encapsulated 3-tier memory retrieval capped at ~budget tokens.

    Queries SHORT (session_facts), MID (working knowledge), and LONG (proven
    knowledge + 1-hop graph walk) tiers. Returns budget-capped results with
    diversity guarantee (1+ per tier if available).
    """
    if not project_name:
        project_name = os.path.basename(os.getcwd())

    # Budget profiles by query_type
    profiles = {
        "task_specific": {"short": 0.40, "mid": 0.40, "long": 0.20},
        "exploration":   {"short": 0.10, "mid": 0.30, "long": 0.60},
        "default":       {"short": 0.20, "mid": 0.40, "long": 0.40},
    }
    profile = profiles.get(query_type, profiles["default"])

    # Generate query embedding for mid/long tier search
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        return {"error": "Failed to generate query embedding — embedding service may be unavailable"}

    session_id = _resolve_session_id(project_name)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        memories = []

        # --- SHORT TIER: session_facts ---
        short_budget = int(budget * profile["short"])
        if session_id:
            cur.execute("""
                SELECT fact_key, fact_value, fact_type, is_sensitive, created_at
                FROM claude.session_facts
                WHERE project_name = %s
                  AND (session_id = %s::uuid OR session_id IS NULL)
                  AND NOT COALESCE(is_sensitive, false)
                ORDER BY
                    CASE fact_type
                        WHEN 'decision' THEN 1
                        WHEN 'reference' THEN 2
                        WHEN 'note' THEN 3
                        WHEN 'config' THEN 4
                        WHEN 'endpoint' THEN 5
                        WHEN 'data' THEN 6
                        ELSE 7
                    END,
                    created_at DESC
                LIMIT 20
            """, (project_name, session_id))
        else:
            cur.execute("""
                SELECT fact_key, fact_value, fact_type, is_sensitive, created_at
                FROM claude.session_facts
                WHERE project_name = %s
                  AND NOT COALESCE(is_sensitive, false)
                ORDER BY created_at DESC
                LIMIT 10
            """, (project_name,))

        short_tokens_used = 0
        for row in cur.fetchall():
            content = f"{row['fact_key']}: {row['fact_value']}"
            tokens = _estimate_tokens(content)
            if short_tokens_used + tokens > short_budget and short_tokens_used > 0:
                break
            memories.append({
                "tier": "short",
                "title": row['fact_key'],
                "content": row['fact_value'],
                "memory_type": row['fact_type'],
                "score": 1.0 - (short_tokens_used / max(short_budget, 1)) * 0.1,
            })
            short_tokens_used += tokens

        # --- MID TIER: knowledge WHERE tier='mid' ---
        mid_budget = int(budget * profile["mid"])
        cur.execute("""
            SELECT
                knowledge_id::text, title, description, knowledge_type,
                confidence_level, times_applied,
                1 - (embedding <=> %s::vector) as similarity,
                EXTRACT(EPOCH FROM (NOW() - COALESCE(last_accessed_at, created_at))) / 86400.0 as days_since_access
            FROM claude.knowledge
            WHERE embedding IS NOT NULL
              AND tier = 'mid'
              AND COALESCE(status, 'active') = 'active'
              AND 1 - (embedding <=> %s::vector) >= 0.4
              AND (applies_to_projects IS NULL OR cardinality(applies_to_projects) = 0 OR %s = ANY(applies_to_projects))
            ORDER BY embedding <=> %s::vector
            LIMIT 10
        """, (query_embedding, query_embedding, project_name, query_embedding))

        mid_tokens_used = 0
        mid_rows = cur.fetchall()
        for row in mid_rows:
            sim = float(row['similarity'])
            days = float(row['days_since_access']) if row['days_since_access'] else 30
            access_freq = min((row['times_applied'] or 0) / 10.0, 1.0)
            conf = (row['confidence_level'] or 50) / 100.0
            # Composite score: similarity 0.4, recency 0.3, access 0.2, confidence 0.1
            recency = max(0, 1.0 - days / 90.0)
            score = sim * 0.4 + recency * 0.3 + access_freq * 0.2 + conf * 0.1

            full_content = row['description'] or row['title']
            # Phase 2e: truncate oversized memory bodies with visibility
            content, truncated, full_len = _truncate_memory_content(full_content)

            tokens = _estimate_tokens(f"{row['title']}: {content}")
            if mid_tokens_used + tokens > mid_budget and mid_tokens_used > 0:
                break
            entry = {
                "tier": "mid",
                "title": row['title'],
                "content": content,
                "memory_type": row['knowledge_type'],
                "knowledge_id": row['knowledge_id'],
                "score": round(score, 4),
                "similarity": round(sim, 4),
                "confidence": row['confidence_level'],
            }
            if truncated:
                entry["content_truncated"] = True
                entry["full_body_length"] = full_len
                entry["fetch_full"] = (
                    f'memory_manage(action="list", limit=1) filtered to knowledge_id '
                    f'{row["knowledge_id"]} — or re-query with more specific terms'
                )
            memories.append(entry)
            mid_tokens_used += tokens

        # --- LONG TIER: knowledge WHERE tier='long' + 1-hop graph walk ---
        long_budget = int(budget * profile["long"])
        cur.execute("""
            SELECT
                k.knowledge_id::text, k.title, k.description, k.knowledge_type,
                k.confidence_level, k.times_applied,
                1 - (k.embedding <=> %s::vector) as similarity,
                EXTRACT(EPOCH FROM (NOW() - COALESCE(k.last_accessed_at, k.created_at))) / 86400.0 as days_since_access
            FROM claude.knowledge k
            WHERE k.embedding IS NOT NULL
              AND k.tier = 'long'
              AND COALESCE(k.status, 'active') = 'active'
              AND 1 - (k.embedding <=> %s::vector) >= 0.35
              AND (k.applies_to_projects IS NULL OR cardinality(k.applies_to_projects) = 0 OR %s = ANY(k.applies_to_projects))
            ORDER BY k.embedding <=> %s::vector
            LIMIT 8
        """, (query_embedding, query_embedding, project_name, query_embedding))

        long_tokens_used = 0
        long_seed_ids = []
        for row in cur.fetchall():
            sim = float(row['similarity'])
            days = float(row['days_since_access']) if row['days_since_access'] else 60
            access_freq = min((row['times_applied'] or 0) / 10.0, 1.0)
            conf = (row['confidence_level'] or 70) / 100.0
            recency = max(0, 1.0 - days / 180.0)
            score = sim * 0.4 + recency * 0.2 + access_freq * 0.2 + conf * 0.2

            full_content = row['description'] or row['title']
            content, truncated, full_len = _truncate_memory_content(full_content)
            tokens = _estimate_tokens(f"{row['title']}: {content}")
            if long_tokens_used + tokens > long_budget and long_tokens_used > 0:
                break
            entry = {
                "tier": "long",
                "title": row['title'],
                "content": content,
                "memory_type": row['knowledge_type'],
                "knowledge_id": row['knowledge_id'],
                "score": round(score, 4),
                "similarity": round(sim, 4),
                "confidence": row['confidence_level'],
            }
            if truncated:
                entry["content_truncated"] = True
                entry["full_body_length"] = full_len
                entry["fetch_full"] = (
                    f'memory_manage(action="list", limit=1) filtered to knowledge_id '
                    f'{row["knowledge_id"]} — or re-query with more specific terms'
                )
            memories.append(entry)
            long_seed_ids.append(row['knowledge_id'])
            long_tokens_used += tokens

        # 1-hop graph walk from long-tier seeds
        if long_seed_ids and long_tokens_used < long_budget:
            seen_ids = set(m.get('knowledge_id') for m in memories if m.get('knowledge_id'))
            cur.execute("""
                SELECT DISTINCT
                    k.knowledge_id::text, k.title, k.description, k.knowledge_type,
                    k.confidence_level, kr.relation_type
                FROM claude.knowledge_relations kr
                JOIN claude.knowledge k ON (
                    (kr.to_knowledge_id = k.knowledge_id AND kr.from_knowledge_id = ANY(%s::uuid[]))
                    OR
                    (kr.from_knowledge_id = k.knowledge_id AND kr.to_knowledge_id = ANY(%s::uuid[]))
                )
                WHERE k.tier IN ('mid', 'long')
                  AND COALESCE(k.status, 'active') = 'active'
                  AND kr.strength >= 0.3
                LIMIT 5
            """, (long_seed_ids, long_seed_ids))

            for row in cur.fetchall():
                if row['knowledge_id'] in seen_ids:
                    continue
                full_content = row['description'] or row['title']
                content, truncated, full_len = _truncate_memory_content(full_content)
                tokens = _estimate_tokens(f"{row['title']}: {content}")
                if long_tokens_used + tokens > long_budget:
                    break
                entry = {
                    "tier": "long",
                    "title": row['title'],
                    "content": content,
                    "memory_type": row['knowledge_type'],
                    "knowledge_id": row['knowledge_id'],
                    "score": 0.3,  # graph-discovered entries get lower score
                    "relation": row['relation_type'],
                    "confidence": row['confidence_level'],
                }
                if truncated:
                    entry["content_truncated"] = True
                    entry["full_body_length"] = full_len
                memories.append(entry)
                long_tokens_used += tokens

        # --- ARTICLE TIER: knowledge_articles sections (F198) ---
        # Uses 10% of remaining budget, max 2 sections
        article_budget = max(200, int(budget * 0.10))
        article_tokens_used = 0
        try:
            cur.execute("""
                SELECT s.section_id::text, s.title as section_title, s.body, s.summary,
                       a.article_id::text, a.title as article_title, a.article_type,
                       1 - (s.embedding <=> %s::vector) as similarity
                FROM claude.article_sections s
                JOIN claude.knowledge_articles a ON a.article_id = s.article_id
                WHERE s.embedding IS NOT NULL
                  AND a.status != 'archived'
                  AND 1 - (s.embedding <=> %s::vector) >= 0.5
                ORDER BY s.embedding <=> %s::vector
                LIMIT 2
            """, (query_embedding, query_embedding, query_embedding))

            for row in cur.fetchall():
                sim = float(row['similarity'])
                body = row['body'] or ''
                summary = row['summary']
                # Use summary if available, otherwise truncate body — BUT make
                # truncation visible so Claude knows to fetch the full body if needed.
                if summary:
                    content = summary
                    content_truncated = len(body) > len(summary)
                    truncation_source = "summary_used" if content_truncated else None
                elif len(body) > 500:
                    content = body[:500]
                    content_truncated = True
                    truncation_source = "body_truncated_500"
                else:
                    content = body
                    content_truncated = False
                    truncation_source = None
                title = f"[Article: {row['article_title']}] {row['section_title']}"
                tokens = _estimate_tokens(f"{title}: {content}")
                if article_tokens_used + tokens > article_budget and article_tokens_used > 0:
                    break
                entry = {
                    "tier": "article",
                    "title": title,
                    "content": content,
                    "memory_type": row['article_type'],
                    "score": round(sim, 4),
                    "similarity": round(sim, 4),
                    "article_id": row['article_id'],
                    "section_id": row['section_id'],
                    "content_truncated": content_truncated,
                }
                if truncation_source:
                    entry["truncation_source"] = truncation_source
                    entry["full_body_length"] = len(body)
                    entry["fetch_full"] = (
                        f'read_article(article_id="{row["article_id"]}", '
                        f'section_id="{row["section_id"]}")'
                    )
                memories.append(entry)
                article_tokens_used += tokens
        except Exception:
            pass  # Fail gracefully if article tables don't exist yet

        # Update access stats for mid/long entries
        accessed_ids = [m['knowledge_id'] for m in memories if m.get('knowledge_id')]
        if accessed_ids:
            cur.execute("""
                UPDATE claude.knowledge
                SET last_accessed_at = NOW(),
                    access_count = COALESCE(access_count, 0) + 1
                WHERE knowledge_id = ANY(%s::uuid[])
            """, (accessed_ids,))

        conn.commit()
        cur.close()

        # Count by tier
        tier_counts = {"short": 0, "mid": 0, "long": 0, "article": 0}
        for m in memories:
            tier_counts[m["tier"]] = tier_counts.get(m["tier"], 0) + 1

        total_tokens = short_tokens_used + mid_tokens_used + long_tokens_used + article_tokens_used

        result = {
            "query": query,
            "query_type": query_type,
            "total_budget": budget,
            "token_count": total_tokens,
            "memory_count": len(memories),
            "tier_counts": tier_counts,
            "memories": memories,
        }

        # Maintenance nudge (best-effort, never blocks)
        health = _quick_knowledge_health(project_name, conn)
        if health:
            result["maintenance_hint"] = health["maintenance_hint"]

        return result

    except Exception as e:
        return {"error": f"recall_memories failed: {str(e)}"}
    finally:
        conn.close()


async def tool_remember(
    content: str,
    context: str = "",
    memory_type: str = "learned",
    tier_hint: str = "auto",
    project_name: Optional[str] = None,
) -> Dict:
    """Encapsulated memory capture with auto tier classification, dedup/merge, and auto-linking.

    SHORT path (credential/config/endpoint): delegates to session_facts.
    MID/LONG path: generates embedding, checks for duplicates (merge if >0.85 similarity),
    creates knowledge entry, auto-links to nearby entries.
    """
    if not project_name:
        project_name = os.path.basename(os.getcwd())

    # Classify tier
    short_types = {"credential", "config", "endpoint"}
    mid_types = {"learned", "fact", "decision", "note", "data"}
    long_types = {"pattern", "procedure", "gotcha", "preference"}

    if tier_hint != "auto":
        tier = tier_hint
    elif memory_type in short_types:
        tier = "short"
    elif memory_type in long_types:
        tier = "long"
    else:
        tier = "mid"

    # SHORT path: delegate to session_facts
    if tier == "short":
        # Extract a key from the content (first line or first 50 chars)
        fact_key = content.split('\n')[0][:50].strip()
        fact_key = re.sub(r'[^a-zA-Z0-9_\-\s]', '', fact_key).strip().replace(' ', '_')[:30]
        if not fact_key:
            fact_key = f"memory_{datetime.now().strftime('%H%M%S')}"

        fact_type_map = {"credential": "credential", "config": "config", "endpoint": "endpoint"}
        fact_type = fact_type_map.get(memory_type, "note")
        is_sensitive = memory_type == "credential"

        result = await tool_store_session_fact(
            fact_key=fact_key,
            fact_value=content,
            fact_type=fact_type,
            is_sensitive=is_sensitive,
            project_name=project_name,
        )
        if result.get("success"):
            return {
                "success": True,
                "memory_id": result.get("fact_id"),
                "tier": "short",
                "action": "created",
                "relations_created": 0,
                "message": f"Stored as session fact: {fact_key}",
            }
        return result

    # MID/LONG path: quality gate before storage
    # Reject ephemeral task state and short junk content
    JUNK_PATTERNS = [
        r'agent\d+[_\s]complete',
        r'task\s+(done|complete|finished)',
        r'moving\s+to\s+(step|task|phase)',
        r'step\s+\d+\s+of\s+\d+',
        r'^(starting|began|finished)\s+(work|task)',
        r'^(checking|checked)\s+(status|progress)',
    ]

    # Never-not-add-knowledge: if content is too short for MID/LONG,
    # auto-route to session_facts instead of rejecting.
    if len(content) < 80:
        fact_key = content.split('\n')[0][:50].strip()
        fact_key = re.sub(r'[^a-zA-Z0-9_\-\s]', '', fact_key).strip().replace(' ', '_')[:30]
        if not fact_key:
            fact_key = f"memory_{datetime.now().strftime('%H%M%S')}"
        result = await tool_store_session_fact(
            fact_key=fact_key,
            fact_value=content,
            fact_type="note",
            is_sensitive=False,
            project_name=project_name,
        )
        if result.get("success"):
            return {
                "success": True,
                "memory_id": result.get("fact_id"),
                "tier": "short",
                "action": "auto_routed_short",
                "auto_route_reason": f"Content {len(content)} chars < 80 min for MID/LONG; stored as session_fact instead.",
                "relations_created": 0,
                "message": f"Auto-routed to session fact: {fact_key}",
            }
        return result

    content_lower = content.lower().strip()
    for pattern in JUNK_PATTERNS:
        if re.search(pattern, content_lower):
            return {
                "success": False,
                "reason": f"Content matches ephemeral task-state pattern. "
                          "Use store_session_fact() for task progress, "
                          "remember() is for reusable patterns/decisions/gotchas.",
            }

    # Build text for embedding
    embed_text = content
    if context:
        embed_text = f"{context}\n\n{content}"

    embedding = generate_embedding(embed_text)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Dedup check: find high-similarity existing entries in same tier
        action = "created"
        merged_id = None

        if embedding:
            cur.execute("""
                SELECT
                    knowledge_id::text, title, description, confidence_level,
                    1 - (embedding <=> %s::vector) as similarity
                FROM claude.knowledge
                WHERE embedding IS NOT NULL
                  AND tier = %s
                  AND COALESCE(status, 'active') = 'active'
                  AND 1 - (embedding <=> %s::vector) > 0.75
                ORDER BY similarity DESC
                LIMIT 1
            """, (embedding, tier, embedding))

            dup = cur.fetchone()
            if dup:
                # Union-merge: never discard content. Three cases:
                #   1. new ⊆ existing → keep existing (no-op beyond access/confidence bump)
                #   2. existing ⊆ new → promote new (replace)
                #   3. distinct       → concatenate with separator
                existing_desc = dup['description'] or ''
                new_content = content

                def _norm(s: str) -> str:
                    return ' '.join(s.split())

                existing_norm = _norm(existing_desc)
                new_norm = _norm(new_content)

                if not new_norm or new_norm in existing_norm:
                    merge_strategy = "kept_existing_superset"
                    new_desc = existing_desc
                    new_embedding = None  # unchanged
                elif existing_norm in new_norm:
                    merge_strategy = "promoted_new_superset"
                    new_desc = new_content
                    new_embedding = embedding
                else:
                    merge_strategy = "union_concatenated"
                    new_desc = f"{existing_desc}\n\n---\n\n{new_content}"
                    # Re-embed the combined text so future similarity matches reflect it
                    new_embed_text = f"{context}\n\n{new_desc}" if context else new_desc
                    new_embedding = generate_embedding(new_embed_text) or embedding

                new_conf = min(100, (dup['confidence_level'] or 50) + 5)
                line_count = new_desc.count('\n') + 1
                chunking_required = line_count > 500

                # Implicit apply: Claude is re-stating knowledge → mark it as applied.
                # Increments times_applied + last_applied_at alongside access_count.
                # Feeds the MID→LONG promotion signal (promotion rule: times_applied>=2 OR access_count>=5).
                if new_embedding is None:
                    # Case 1: content unchanged, skip embedding write
                    cur.execute("""
                        UPDATE claude.knowledge
                        SET confidence_level = %s,
                            last_accessed_at = NOW(),
                            last_applied_at = NOW(),
                            access_count = COALESCE(access_count, 0) + 1,
                            times_applied = COALESCE(times_applied, 0) + 1
                        WHERE knowledge_id = %s::uuid
                    """, (new_conf, dup['knowledge_id']))
                else:
                    cur.execute("""
                        UPDATE claude.knowledge
                        SET description = %s,
                            embedding = %s::vector,
                            confidence_level = %s,
                            last_accessed_at = NOW(),
                            last_applied_at = NOW(),
                            access_count = COALESCE(access_count, 0) + 1,
                            times_applied = COALESCE(times_applied, 0) + 1
                        WHERE knowledge_id = %s::uuid
                    """, (new_desc, new_embedding, new_conf, dup['knowledge_id']))

                conn.commit()
                cur.close()
                return {
                    "success": True,
                    "memory_id": dup['knowledge_id'],
                    "tier": tier,
                    "action": "merged",
                    "merge_strategy": merge_strategy,
                    "existing_similarity": round(float(dup['similarity']), 4),
                    "new_confidence": new_conf,
                    "relations_created": 0,
                    "chunking_required": chunking_required,
                    "message": f"Merged ({merge_strategy}) with: {dup['title']} (sim={round(float(dup['similarity']), 3)})",
                }

        # Check for contradiction: high-similarity entries with divergent confidence
        contradiction_flag = False
        if embedding:
            cur.execute("""
                SELECT knowledge_id::text, title, confidence_level,
                    1 - (embedding <=> %s::vector) as similarity
                FROM claude.knowledge
                WHERE embedding IS NOT NULL
                  AND COALESCE(status, 'active') = 'active'
                  AND 1 - (embedding <=> %s::vector) > 0.75
                  AND tier IN ('mid', 'long')
                LIMIT 3
            """, (embedding, embedding))

            for row in cur.fetchall():
                # If the new entry would be mid but existing is high-confidence long, flag
                if tier == "mid" and (row['confidence_level'] or 50) >= 80:
                    contradiction_flag = True
                    break

        # Create title from content (first line, max 80 chars)
        title = content.split('\n')[0][:80].strip()
        if not title:
            title = f"Memory {datetime.now().strftime('%Y-%m-%d %H:%M')}"

        # Set confidence based on tier
        confidence = 65 if tier == "mid" else 75

        # Insert
        if embedding:
            cur.execute("""
                INSERT INTO claude.knowledge
                    (knowledge_id, title, description, knowledge_type, tier,
                     confidence_level, source, embedding, created_at,
                     applies_to_projects)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s, %s, 'remember', %s::vector, NOW(), %s)
                RETURNING knowledge_id::text
            """, (title, content, memory_type, tier, confidence, embedding,
                  [project_name] if project_name else None))
        else:
            cur.execute("""
                INSERT INTO claude.knowledge
                    (knowledge_id, title, description, knowledge_type, tier,
                     confidence_level, source, created_at,
                     applies_to_projects)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s, %s, 'remember', NOW(), %s)
                RETURNING knowledge_id::text
            """, (title, content, memory_type, tier, confidence,
                  [project_name] if project_name else None))

        result = cur.fetchone()
        new_id = result['knowledge_id']

        # Auto-link: find nearby knowledge (0.5-0.85 similarity)
        relations_created = 0
        if embedding:
            cur.execute("""
                SELECT knowledge_id::text, title,
                    1 - (embedding <=> %s::vector) as similarity
                FROM claude.knowledge
                WHERE embedding IS NOT NULL
                  AND knowledge_id != %s::uuid
                  AND 1 - (embedding <=> %s::vector) BETWEEN 0.5 AND 0.85
                ORDER BY similarity DESC
                LIMIT 3
            """, (embedding, new_id, embedding))

            for row in cur.fetchall():
                cur.execute("""
                    INSERT INTO claude.knowledge_relations
                        (relation_id, from_knowledge_id, to_knowledge_id, relation_type, strength)
                    VALUES (gen_random_uuid(), %s::uuid, %s::uuid, 'relates_to', %s)
                    ON CONFLICT DO NOTHING
                """, (new_id, row['knowledge_id'], round(float(row['similarity']), 3)))
                relations_created += 1

        conn.commit()
        cur.close()

        action = "contradiction_flagged" if contradiction_flag else "created"
        result = {
            "success": True,
            "memory_id": new_id,
            "tier": tier,
            "action": action,
            "has_embedding": embedding is not None,
            "relations_created": relations_created,
            "message": f"Stored {tier}-tier memory: {title}" + (
                " [CONTRADICTION FLAG: similar high-confidence entry exists]" if contradiction_flag else ""
            ),
        }

        # Maintenance nudge (best-effort, never blocks)
        health = _quick_knowledge_health(project_name, conn)
        if health:
            result["maintenance_hint"] = health["maintenance_hint"]

        return result

    except Exception as e:
        return {"error": f"remember failed: {str(e)}"}
    finally:
        conn.close()


async def tool_consolidate_memories(
    trigger: str = "session_end",
    project_name: Optional[str] = None,
) -> Dict:
    """Encapsulated memory lifecycle management: promote, decay, archive.

    Triggers:
    - session_end: Phase 1 only (short→mid promotion of qualifying session facts)
    - periodic: Phase 2+3 (mid→long promotion, decay, archive)
    - manual: Full cycle (all phases)
    """
    if not project_name:
        project_name = os.path.basename(os.getcwd())

    result = {
        "trigger": trigger,
        "promoted_short_to_mid": 0,
        "promoted_mid_to_long": 0,
        "decayed_edges": 0,
        "archived": 0,
    }

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # ---- PHASE 1: SHORT→MID (session_end or manual) ----
        if trigger in ("session_end", "manual"):
            # Find qualifying session facts from recent closed sessions
            # Criteria: decision/pattern/reference type, length >= 50 chars
            cur.execute("""
                SELECT sf.fact_id, sf.fact_key, sf.fact_value, sf.fact_type, sf.project_name
                FROM claude.session_facts sf
                JOIN claude.sessions s ON sf.session_id = s.session_id
                WHERE sf.project_name = %s
                  AND sf.fact_type IN ('decision', 'reference', 'note', 'data')
                  AND LENGTH(sf.fact_value) >= 50
                  AND s.session_end IS NOT NULL
                  AND s.session_end > NOW() - INTERVAL '7 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM claude.knowledge k
                      WHERE k.title = sf.fact_key AND k.source = 'consolidation'
                        AND k.embedding IS NOT NULL
                  )
                LIMIT 10
            """, (project_name,))

            facts_to_promote = cur.fetchall()
            for fact in facts_to_promote:
                # Generate embedding for the fact
                embed_text = f"{fact['fact_key']}: {fact['fact_value']}"
                embedding = generate_embedding(embed_text)

                # Dedup check against existing mid-tier
                is_dup = False
                if embedding:
                    cur.execute("""
                        SELECT knowledge_id::text, 1 - (embedding <=> %s::vector) as sim
                        FROM claude.knowledge
                        WHERE embedding IS NOT NULL AND 1 - (embedding <=> %s::vector) > 0.85
                        LIMIT 1
                    """, (embedding, embedding))
                    if cur.fetchone():
                        is_dup = True

                if not is_dup:
                    if embedding:
                        cur.execute("""
                            INSERT INTO claude.knowledge
                                (knowledge_id, title, description, knowledge_type, tier,
                                 confidence_level, source, embedding, created_at,
                                 applies_to_projects)
                            VALUES (gen_random_uuid(), %s, %s, %s, 'mid', 65, 'consolidation',
                                    %s::vector, NOW(), %s)
                        """, (fact['fact_key'], fact['fact_value'],
                              'learned' if fact['fact_type'] in ('note', 'data') else fact['fact_type'],
                              embedding,
                              [fact['project_name']] if fact['project_name'] else None))
                    else:
                        cur.execute("""
                            INSERT INTO claude.knowledge
                                (knowledge_id, title, description, knowledge_type, tier,
                                 confidence_level, source, created_at,
                                 applies_to_projects)
                            VALUES (gen_random_uuid(), %s, %s, %s, 'mid', 65, 'consolidation',
                                    NOW(), %s)
                        """, (fact['fact_key'], fact['fact_value'],
                              'learned' if fact['fact_type'] in ('note', 'data') else fact['fact_type'],
                              [fact['project_name']] if fact['project_name'] else None))
                    result["promoted_short_to_mid"] += 1

        # ---- PHASE 2: MID→LONG promotion (periodic or manual) ----
        if trigger in ("periodic", "manual"):
            # Dual-signal promotion:
            # 1. access_count>=5 (retrieval-frequency) — incremented by recall_memories.
            # 2. times_applied>=2 (implicit-apply) — incremented when remember()
            #    hits the dedup path (Claude re-stating = stronger "this was useful").
            # Either signal is sufficient alongside confidence and age thresholds.
            cur.execute("""
                UPDATE claude.knowledge
                SET tier = 'long'
                WHERE tier = 'mid'
                  AND confidence_level >= 60
                  AND created_at < NOW() - INTERVAL '7 days'
                  AND embedding IS NOT NULL
                  AND (
                    COALESCE(access_count, 0) >= 5
                    OR COALESCE(times_applied, 0) >= 2
                  )
                RETURNING knowledge_id
            """)
            result["promoted_mid_to_long"] = cur.rowcount

        # ---- PHASE 3: DECAY + ARCHIVE (periodic or manual) ----
        if trigger in ("periodic", "manual"):
            # Decay edges: 0.95^days formula
            cur.execute("""
                UPDATE claude.knowledge_relations
                SET strength = GREATEST(0.05, strength * POWER(0.95,
                    EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400.0
                ))
                WHERE strength > 0.05
                  AND created_at < NOW() - INTERVAL '7 days'
                RETURNING relation_id
            """)
            result["decayed_edges"] = cur.rowcount

            # Archive: confidence < 30, not accessed in 90+ days
            cur.execute("""
                UPDATE claude.knowledge
                SET tier = 'archived'
                WHERE tier IN ('mid', 'long')
                  AND confidence_level < 30
                  AND COALESCE(last_accessed_at, created_at) < NOW() - INTERVAL '90 days'
                RETURNING knowledge_id
            """)
            result["archived"] = cur.rowcount

        conn.commit()
        cur.close()

        result["success"] = True
        result["message"] = (
            f"Consolidation ({trigger}): "
            f"{result['promoted_short_to_mid']} short→mid, "
            f"{result['promoted_mid_to_long']} mid→long, "
            f"{result['decayed_edges']} edges decayed, "
            f"{result['archived']} archived"
        )
        return result

    except Exception as e:
        return {"error": f"consolidate_memories failed: {str(e)}"}
    finally:
        conn.close()


async def tool_list_memories(
    project_name: Optional[str] = None,
    tier: str = "",
    memory_type: str = "",
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> Dict:
    if not project_name:
        project_name = os.path.basename(os.getcwd())

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        where_parts = []
        params = []

        # Project filter
        where_parts.append("(applies_to_projects IS NULL OR cardinality(applies_to_projects) = 0 OR %s = ANY(applies_to_projects))")
        params.append(project_name)

        # Status filter
        if not include_archived:
            where_parts.append("COALESCE(status, 'active') = 'active'")

        # Tier filter
        if tier:
            where_parts.append("tier = %s")
            params.append(tier)

        # Type filter
        if memory_type:
            where_parts.append("knowledge_type = %s")
            params.append(memory_type)

        where_clause = " AND ".join(where_parts)

        # Get total count
        cur.execute(f"SELECT COUNT(*) as cnt FROM claude.knowledge WHERE {where_clause}", params)
        total = cur.fetchone()['cnt']

        # Get page
        cur.execute(f"""
            SELECT knowledge_id::text, title, LEFT(description, 200) as description_preview,
                   knowledge_type, tier, confidence_level, COALESCE(status, 'active') as status,
                   created_at, last_accessed_at, access_count
            FROM claude.knowledge
            WHERE {where_clause}
            ORDER BY COALESCE(last_accessed_at, created_at) DESC
            LIMIT %s OFFSET %s
        """, params + [limit, offset])

        rows = cur.fetchall()
        cur.close()

        memories = [{
            "knowledge_id": r['knowledge_id'],
            "title": r['title'],
            "description_preview": r['description_preview'],
            "memory_type": r['knowledge_type'],
            "tier": r['tier'],
            "confidence": r['confidence_level'],
            "status": r['status'],
            "created_at": str(r['created_at']) if r['created_at'] else None,
            "last_accessed_at": str(r['last_accessed_at']) if r['last_accessed_at'] else None,
            "access_count": r['access_count'],
        } for r in rows]

        return {
            "success": True,
            "project": project_name,
            "total_count": total,
            "showing": len(memories),
            "offset": offset,
            "memories": memories,
        }
    except Exception as e:
        return {"error": f"list_memories failed: {str(e)}"}
    finally:
        conn.close()


async def tool_update_memory(
    memory_id: str,
    content: str = "",
    title: str = "",
    tier: str = "",
    memory_type: str = "",
) -> Dict:
    if not memory_id:
        return {"error": "memory_id is required"}

    updates = []
    params = []
    updated_fields = []

    if content:
        updates.append("description = %s")
        params.append(content)
        updated_fields.append("content")

    if title:
        updates.append("title = %s")
        params.append(title)
        updated_fields.append("title")

    if tier:
        if tier not in ('mid', 'long'):
            return {"error": "tier must be 'mid' or 'long'"}
        updates.append("tier = %s")
        params.append(tier)
        updated_fields.append("tier")

    if memory_type:
        updates.append("knowledge_type = %s")
        params.append(memory_type)
        updated_fields.append("memory_type")

    if not updates:
        return {"error": "No fields to update. Provide at least one of: content, title, tier, memory_type"}

    # Re-embed if content changed
    re_embedded = False
    if content:
        embedding = generate_embedding(content)
        if embedding:
            updates.append("embedding = %s::vector")
            params.append(embedding)
            re_embedded = True

    updates.append("last_accessed_at = NOW()")
    params.append(memory_id)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Verify memory exists
        cur.execute("SELECT title, COALESCE(status, 'active') as status FROM claude.knowledge WHERE knowledge_id = %s::uuid", (memory_id,))
        existing = cur.fetchone()
        if not existing:
            return {"error": f"Memory {memory_id} not found"}

        # Update
        set_clause = ", ".join(updates)
        cur.execute(f"""
            UPDATE claude.knowledge SET {set_clause}
            WHERE knowledge_id = %s::uuid
            RETURNING knowledge_id::text, title
        """, params)

        result = cur.fetchone()

        # Audit log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, from_status, to_status, changed_by, change_source, metadata)
            VALUES ('knowledge', %s::uuid, %s, %s, 'update_memory', 'mcp_tool', %s::jsonb)
        """, (memory_id, existing['status'], existing['status'],
              json.dumps({"updated_fields": updated_fields, "re_embedded": re_embedded})))

        conn.commit()
        cur.close()

        return {
            "success": True,
            "memory_id": memory_id,
            "title": result['title'] if result else existing['title'],
            "updated_fields": updated_fields,
            "re_embedded": re_embedded,
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"update_memory failed: {str(e)}"}
    finally:
        conn.close()


async def tool_archive_memory(
    memory_id: str,
    reason: str = "",
) -> Dict:
    if not memory_id:
        return {"error": "memory_id is required"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get current state
        cur.execute("""
            SELECT title, COALESCE(status, 'active') as status, tier
            FROM claude.knowledge WHERE knowledge_id = %s::uuid
        """, (memory_id,))
        existing = cur.fetchone()
        if not existing:
            return {"error": f"Memory {memory_id} not found"}

        if existing['status'] == 'archived':
            return {"success": True, "memory_id": memory_id, "title": existing['title'],
                    "message": "Already archived", "previous_status": "archived"}

        # Archive it
        cur.execute("""
            UPDATE claude.knowledge
            SET status = 'archived',
                archived_at = NOW(),
                archived_reason = %s,
                archived_by = 'archive_memory'
            WHERE knowledge_id = %s::uuid
        """, (reason or 'Manual archive via tool', memory_id))

        # Audit log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, from_status, to_status, changed_by, change_source, metadata)
            VALUES ('knowledge', %s::uuid, 'active', 'archived', 'archive_memory', 'mcp_tool', %s::jsonb)
        """, (memory_id, json.dumps({"reason": reason, "title": existing['title'], "tier": existing['tier']})))

        conn.commit()
        cur.close()

        return {
            "success": True,
            "memory_id": memory_id,
            "title": existing['title'],
            "previous_status": "active",
            "reason": reason or 'Manual archive via tool',
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"archive_memory failed: {str(e)}"}
    finally:
        conn.close()


async def tool_merge_memories(
    keep_id: str,
    archive_id: str,
    reason: str = "",
) -> Dict:
    if not keep_id or not archive_id:
        return {"error": "Both keep_id and archive_id are required"}
    if keep_id == archive_id:
        return {"error": "keep_id and archive_id must be different"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Verify both exist
        cur.execute("""
            SELECT knowledge_id::text, title, COALESCE(status, 'active') as status
            FROM claude.knowledge
            WHERE knowledge_id IN (%s::uuid, %s::uuid)
        """, (keep_id, archive_id))
        rows = {r['knowledge_id']: r for r in cur.fetchall()}

        if keep_id not in rows:
            return {"error": f"Keep memory {keep_id} not found"}
        if archive_id not in rows:
            return {"error": f"Archive memory {archive_id} not found"}

        # Transfer relations from archive_id to keep_id
        # Relations where archive_id is the source
        cur.execute("""
            UPDATE claude.knowledge_relations
            SET from_knowledge_id = %s::uuid
            WHERE from_knowledge_id = %s::uuid
              AND to_knowledge_id != %s::uuid
        """, (keep_id, archive_id, keep_id))
        transferred_from = cur.rowcount

        # Relations where archive_id is the target
        cur.execute("""
            UPDATE claude.knowledge_relations
            SET to_knowledge_id = %s::uuid
            WHERE to_knowledge_id = %s::uuid
              AND from_knowledge_id != %s::uuid
        """, (keep_id, archive_id, keep_id))
        transferred_to = cur.rowcount

        # Delete any self-referencing relations that may have been created
        cur.execute("""
            DELETE FROM claude.knowledge_relations
            WHERE from_knowledge_id = %s::uuid AND to_knowledge_id = %s::uuid
        """, (keep_id, keep_id))

        # Archive the duplicate
        merge_reason = reason or f"Merged into {keep_id} ({rows[keep_id]['title']})"
        cur.execute("""
            UPDATE claude.knowledge
            SET status = 'archived',
                archived_at = NOW(),
                archived_reason = %s,
                archived_by = 'merge_memories'
            WHERE knowledge_id = %s::uuid
        """, (merge_reason, archive_id))

        # Boost confidence on the kept entry
        cur.execute("""
            UPDATE claude.knowledge
            SET confidence_level = LEAST(confidence_level + 5, 100),
                last_accessed_at = NOW()
            WHERE knowledge_id = %s::uuid
        """, (keep_id,))

        # Audit log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, from_status, to_status, changed_by, change_source, metadata)
            VALUES ('knowledge', %s::uuid, 'active', 'merged', 'merge_memories', 'mcp_tool', %s::jsonb)
        """, (archive_id, json.dumps({
            "kept_id": keep_id,
            "kept_title": rows[keep_id]['title'],
            "archived_title": rows[archive_id]['title'],
            "relations_transferred": transferred_from + transferred_to,
            "reason": reason,
        })))

        conn.commit()
        cur.close()

        return {
            "success": True,
            "kept_id": keep_id,
            "kept_title": rows[keep_id]['title'],
            "archived_id": archive_id,
            "archived_title": rows[archive_id]['title'],
            "relations_transferred": transferred_from + transferred_to,
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"merge_memories failed: {str(e)}"}
    finally:
        conn.close()


async def tool_archive_workfile(
    component: str,
    title: str,
    project_name: Optional[str] = None,
) -> Dict:
    """Mark a workfile as inactive (soft-delete)."""
    if not component or not title:
        return {"error": "component and title are required"}

    project_name = project_name or os.path.basename(os.getcwd())
    project_id = get_project_id(project_name)
    if not project_id:
        return {"error": f"Project '{project_name}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            UPDATE claude.project_workfiles
            SET is_active = FALSE, updated_at = NOW()
            WHERE project_id = %s::uuid AND component = %s AND title = %s AND is_active = TRUE
            RETURNING workfile_id::text
        """, (project_id, component, title))

        result = cur.fetchone()
        if not result:
            return {"error": f"Active workfile '{component}/{title}' not found"}

        # Audit log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, from_status, to_status, changed_by, change_source, metadata)
            VALUES ('workfile', %s::uuid, 'active', 'archived', 'archive_workfile', 'mcp_tool', %s::jsonb)
        """, (result['workfile_id'], json.dumps({"component": component, "title": title, "project": project_name})))

        conn.commit()
        cur.close()

        return {
            "success": True,
            "component": component,
            "title": title,
            "previous_state": "active",
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"archive_workfile failed: {str(e)}"}
    finally:
        conn.close()


async def tool_delete_workfile(
    component: str,
    title: str,
    project_name: Optional[str] = None,
) -> Dict:
    """Permanently delete a workfile."""
    if not component or not title:
        return {"error": "component and title are required"}

    project_name = project_name or os.path.basename(os.getcwd())
    project_id = get_project_id(project_name)
    if not project_id:
        return {"error": f"Project '{project_name}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            DELETE FROM claude.project_workfiles
            WHERE project_id = %s::uuid AND component = %s AND title = %s
            RETURNING workfile_id::text, is_active
        """, (project_id, component, title))

        result = cur.fetchone()
        if not result:
            return {"error": f"Workfile '{component}/{title}' not found"}

        # Audit log
        cur.execute("""
            INSERT INTO claude.audit_log
            (entity_type, entity_id, to_status, changed_by, change_source, metadata)
            VALUES ('workfile', %s::uuid, 'deleted', 'delete_workfile', 'mcp_tool', %s::jsonb)
        """, (result['workfile_id'], json.dumps({"component": component, "title": title, "project": project_name, "was_active": result['is_active']})))

        conn.commit()
        cur.close()

        return {
            "success": True,
            "component": component,
            "title": title,
            "deleted": True,
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"delete_workfile failed: {str(e)}"}
    finally:
        conn.close()


async def tool_link_knowledge(
    from_knowledge_id: str,
    to_knowledge_id: str,
    relation_type: str,
    strength: float = 1.0,
    notes: Optional[str] = None
) -> Dict:
    """Create a typed relation between knowledge entries."""
    valid_relation_types = [
        'extends', 'contradicts', 'supports', 'supersedes',
        'depends_on', 'relates_to', 'part_of', 'caused_by'
    ]

    if relation_type not in valid_relation_types:
        return {
            "error": f"Invalid relation_type: {relation_type}. Valid types: {valid_relation_types}"
        }

    if strength < 0 or strength > 1:
        return {"error": "strength must be between 0 and 1"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Verify both knowledge entries exist
        cur.execute("""
            SELECT knowledge_id::text, title
            FROM claude.knowledge
            WHERE knowledge_id IN (%s::uuid, %s::uuid)
        """, (from_knowledge_id, to_knowledge_id))

        found = {str(r['knowledge_id']): r['title'] for r in cur.fetchall()}

        if from_knowledge_id not in found:
            return {"error": f"From knowledge not found: {from_knowledge_id}"}
        if to_knowledge_id not in found:
            return {"error": f"To knowledge not found: {to_knowledge_id}"}

        # Create relation
        cur.execute("""
            INSERT INTO claude.knowledge_relations
                (from_knowledge_id, to_knowledge_id, relation_type, strength, notes)
            VALUES
                (%s::uuid, %s::uuid, %s, %s, %s)
            ON CONFLICT (from_knowledge_id, to_knowledge_id, relation_type) DO UPDATE
            SET strength = EXCLUDED.strength, notes = EXCLUDED.notes
            RETURNING relation_id::text
        """, (from_knowledge_id, to_knowledge_id, relation_type, strength, notes))

        result = cur.fetchone()
        conn.commit()
        cur.close()

        return {
            "success": True,
            "relation_id": result['relation_id'],
            "from": found[from_knowledge_id],
            "to": found[to_knowledge_id],
            "relation_type": relation_type,
            "strength": strength
        }

    except Exception as e:
        return {"error": f"Failed to link knowledge: {str(e)}"}
    finally:
        conn.close()


async def tool_get_related_knowledge(
    knowledge_id: str,
    relation_types: Optional[List[str]] = None,
    include_reverse: bool = True
) -> Dict:
    """Get related knowledge entries via knowledge_relations."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get the source knowledge
        cur.execute("""
            SELECT knowledge_id::text, title, description
            FROM claude.knowledge
            WHERE knowledge_id = %s::uuid
        """, (knowledge_id,))
        source = cur.fetchone()

        if not source:
            return {"error": f"Knowledge not found: {knowledge_id}"}

        # Build relation type filter
        type_filter = ""
        type_params = []
        if relation_types:
            type_filter = "AND r.relation_type = ANY(%s)"
            type_params = [relation_types]

        # Get outgoing relations
        cur.execute(f"""
            SELECT
                r.relation_id::text,
                r.relation_type,
                r.strength,
                r.notes,
                'outgoing' as direction,
                k.knowledge_id::text as related_id,
                k.title as related_title,
                k.description as related_description,
                k.knowledge_type
            FROM claude.knowledge_relations r
            JOIN claude.knowledge k ON r.to_knowledge_id = k.knowledge_id
            WHERE r.from_knowledge_id = %s::uuid
            {type_filter}
            ORDER BY r.strength DESC
        """, [knowledge_id] + type_params)

        outgoing = [dict(r) for r in cur.fetchall()]

        incoming = []
        if include_reverse:
            cur.execute(f"""
                SELECT
                    r.relation_id::text,
                    r.relation_type,
                    r.strength,
                    r.notes,
                    'incoming' as direction,
                    k.knowledge_id::text as related_id,
                    k.title as related_title,
                    k.description as related_description,
                    k.knowledge_type
                FROM claude.knowledge_relations r
                JOIN claude.knowledge k ON r.from_knowledge_id = k.knowledge_id
                WHERE r.to_knowledge_id = %s::uuid
                {type_filter}
                ORDER BY r.strength DESC
            """, [knowledge_id] + type_params)

            incoming = [dict(r) for r in cur.fetchall()]

        cur.close()

        return {
            "source": {
                "knowledge_id": source['knowledge_id'],
                "title": source['title'],
                "description": source['description']
            },
            "relations_count": len(outgoing) + len(incoming),
            "outgoing": outgoing,
            "incoming": incoming
        }

    except Exception as e:
        return {"error": f"Failed to get related knowledge: {str(e)}"}
    finally:
        conn.close()


# ============================================================================
# Session Facts Tool Implementations
# ============================================================================

def _resolve_session_id(project_name: Optional[str] = None) -> Optional[str]:
    """Resolve session_id from env var, falling back to most recent active session."""
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    if session_id:
        return session_id

    # Fallback: find most recent session for this project (< 24h old, no end time)
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT session_id::text FROM claude.sessions
            WHERE project_name = %s
              AND session_end IS NULL
              AND session_start > NOW() - INTERVAL '24 hours'
            ORDER BY session_start DESC
            LIMIT 1
        """, (project_name or os.path.basename(os.getcwd()),))
        row = cur.fetchone()
        cur.close()
        return row['session_id'] if row else None
    except Exception:
        return None
    finally:
        conn.close()


async def tool_store_session_fact(
    fact_key: str,
    fact_value: str,
    fact_type: str = "note",
    is_sensitive: bool = False,
    project_name: Optional[str] = None
) -> Dict:
    """Store a fact in the session notepad (auto-injected into context)."""
    if not project_name:
        project_name = os.path.basename(os.getcwd())
    session_id = _resolve_session_id(project_name)

    # Validate fact_type
    valid, msg = validate_value('session_facts', 'fact_type', fact_type)
    if not valid:
        return {"error": msg}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Upsert the fact (update if key exists for this session)
        cur.execute("""
            INSERT INTO claude.session_facts
                (fact_id, session_id, project_name, fact_type, fact_key, fact_value, is_sensitive, created_at)
            VALUES
                (gen_random_uuid(), %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (session_id, fact_key) DO UPDATE SET
                fact_value = EXCLUDED.fact_value,
                fact_type = EXCLUDED.fact_type,
                is_sensitive = EXCLUDED.is_sensitive,
                created_at = NOW()
            RETURNING fact_id::text
        """, (session_id if session_id else None, project_name, fact_type, fact_key, fact_value, is_sensitive))

        result = cur.fetchone()
        conn.commit()
        cur.close()

        log_msg = f"Stored fact: {fact_key}" if not is_sensitive else f"Stored sensitive fact: {fact_key}"
        return {
            "success": True,
            "fact_id": result['fact_id'],
            "fact_key": fact_key,
            "fact_type": fact_type,
            "is_sensitive": is_sensitive,
            "message": log_msg
        }

    except Exception as e:
        return {"error": f"Failed to store fact: {str(e)}"}
    finally:
        conn.close()


async def tool_recall_session_fact(
    fact_key: str,
    project_name: Optional[str] = None
) -> Dict:
    """Recall a specific fact by key from current session."""
    if not project_name:
        project_name = os.path.basename(os.getcwd())
    session_id = _resolve_session_id(project_name)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Try current session first, then fall back to recent sessions
        cur.execute("""
            SELECT fact_id::text, fact_key, fact_value, fact_type, is_sensitive, created_at, session_id::text
            FROM claude.session_facts
            WHERE fact_key = %s
              AND project_name = %s
              AND (session_id = %s::uuid OR session_id IS NULL OR %s::text IS NULL)
            ORDER BY
                CASE WHEN session_id = %s::uuid THEN 0 ELSE 1 END,
                created_at DESC
            LIMIT 1
        """, (fact_key, project_name, session_id, session_id, session_id))

        result = cur.fetchone()
        cur.close()

        if not result:
            return {"found": False, "fact_key": fact_key, "message": f"No fact found for key: {fact_key}"}

        return {
            "found": True,
            "fact_id": result['fact_id'],
            "fact_key": result['fact_key'],
            "fact_value": result['fact_value'],
            "fact_type": result['fact_type'],
            "is_sensitive": result['is_sensitive'],
            "created_at": result['created_at'].isoformat() if result['created_at'] else None,
            "from_session": result['session_id']
        }

    except Exception as e:
        return {"error": f"Failed to recall fact: {str(e)}"}
    finally:
        conn.close()


async def tool_list_session_facts(
    project_name: Optional[str] = None,
    include_sensitive: bool = False
) -> Dict:
    """List all facts for the current session."""
    if not project_name:
        project_name = os.path.basename(os.getcwd())
    session_id = _resolve_session_id(project_name)

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Include facts from current session AND recent sessions in same project
        # (handles compaction creating a new session_id mid-CLI-invocation)
        cur.execute("""
            SELECT fact_id::text, fact_key, fact_value, fact_type, is_sensitive, created_at
            FROM claude.session_facts
            WHERE project_name = %s
              AND (
                session_id = %s::uuid
                OR session_id IS NULL
                OR session_id IN (
                    SELECT session_id FROM claude.sessions
                    WHERE project_name = %s
                      AND session_start > NOW() - INTERVAL '4 hours'
                      AND session_end IS NULL
                )
              )
            ORDER BY created_at DESC
        """, (project_name, session_id, project_name))

        facts = []
        for row in cur.fetchall():
            fact = {
                "fact_id": row['fact_id'],
                "fact_key": row['fact_key'],
                "fact_type": row['fact_type'],
                "is_sensitive": row['is_sensitive'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None
            }
            # Only include value if not sensitive or explicitly requested
            if not row['is_sensitive'] or include_sensitive:
                fact["fact_value"] = row['fact_value']
            else:
                fact["fact_value"] = "[REDACTED - use include_sensitive=true]"
            facts.append(fact)

        cur.close()

        return {
            "project_name": project_name,
            "session_id": session_id,
            "facts_count": len(facts),
            "facts": facts
        }

    except Exception as e:
        return {"error": f"Failed to list facts: {str(e)}"}
    finally:
        conn.close()


async def tool_recall_previous_session_facts(
    project_name: Optional[str] = None,
    n_sessions: int = 3,
    fact_types: Optional[List[str]] = None
) -> Dict:
    """Recall facts from previous sessions (after context compaction)."""
    if not project_name:
        project_name = os.path.basename(os.getcwd())

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get recent sessions for this project
        cur.execute("""
            SELECT session_id, MAX(created_at) as latest_fact
            FROM claude.session_facts
            WHERE project_name = %s
              AND session_id IS NOT NULL
            GROUP BY session_id
            ORDER BY latest_fact DESC
            LIMIT %s
        """, (project_name, n_sessions))

        session_ids = [row['session_id'] for row in cur.fetchall()]

        if not session_ids:
            return {"message": "No previous session facts found", "facts": []}

        # Build query with optional type filter
        type_filter = ""
        params = [project_name, [str(sid) for sid in session_ids]]
        if fact_types:
            type_filter = "AND fact_type = ANY(%s)"
            params.append(fact_types)

        cur.execute(f"""
            SELECT
                fact_id::text,
                fact_key,
                fact_value,
                fact_type,
                is_sensitive,
                created_at,
                session_id::text
            FROM claude.session_facts
            WHERE project_name = %s
              AND session_id = ANY(%s::uuid[])
              {type_filter}
            ORDER BY created_at DESC
        """, params)

        facts = []
        for row in cur.fetchall():
            facts.append({
                "fact_id": row['fact_id'],
                "fact_key": row['fact_key'],
                "fact_value": row['fact_value'] if not row['is_sensitive'] else "[REDACTED]",
                "fact_type": row['fact_type'],
                "is_sensitive": row['is_sensitive'],
                "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                "session_id": row['session_id']
            })

        cur.close()

        return {
            "project_name": project_name,
            "sessions_checked": len(session_ids),
            "facts_count": len(facts),
            "facts": facts
        }

    except Exception as e:
        return {"error": f"Failed to recall previous facts: {str(e)}"}
    finally:
        conn.close()


async def tool_mark_knowledge_applied(
    knowledge_id: str,
    success: bool = True
) -> Dict:
    """Track when knowledge is applied (success or failure)."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if success:
            cur.execute("""
                UPDATE claude.knowledge
                SET times_applied = COALESCE(times_applied, 0) + 1,
                    last_applied_at = NOW(),
                    confidence_level = LEAST(100, COALESCE(confidence_level, 80) + 1)
                WHERE knowledge_id = %s::uuid
                RETURNING knowledge_id::text, title, times_applied, confidence_level
            """, (knowledge_id,))
        else:
            cur.execute("""
                UPDATE claude.knowledge
                SET times_failed = COALESCE(times_failed, 0) + 1,
                    confidence_level = GREATEST(0, COALESCE(confidence_level, 80) - 5)
                WHERE knowledge_id = %s::uuid
                RETURNING knowledge_id::text, title, times_failed, confidence_level
            """, (knowledge_id,))

        result = cur.fetchone()
        if not result:
            return {"error": f"Knowledge not found: {knowledge_id}"}

        conn.commit()
        cur.close()

        return {
            "success": True,
            "knowledge_id": result['knowledge_id'],
            "title": result['title'],
            "applied_success": success,
            "new_confidence": result['confidence_level'],
            "times_applied": result.get('times_applied'),
            "times_failed": result.get('times_failed')
        }

    except Exception as e:
        return {"error": f"Failed to mark knowledge: {str(e)}"}
    finally:
        conn.close()


async def tool_store_session_notes(
    content: str,
    section: str = "general",
    append: bool = True
) -> Dict:
    """
    Store structured notes during a session.

    Notes persist to a markdown file for cross-session reference.
    Use for: progress tracking, key decisions, architectural notes, important findings.

    Args:
        content: Note content to store
        section: Section header (e.g., "decisions", "progress", "blockers", "findings")
        append: If True, append to section. If False, replace section.
    """
    session_id = os.environ.get('CLAUDE_SESSION_ID', 'unknown')
    project_name = os.path.basename(os.getcwd())

    # Notes directory: ~/.claude/session_notes/
    notes_dir = Path.home() / ".claude" / "session_notes"
    notes_dir.mkdir(parents=True, exist_ok=True)

    # File per project (not session) so notes persist
    notes_file = notes_dir / f"{project_name}.md"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        # Read existing content or create new
        if notes_file.exists():
            existing = notes_file.read_text(encoding='utf-8')
        else:
            existing = f"# Session Notes: {project_name}\n\n"

        # Format the new note
        note_entry = f"- [{timestamp}] {content}\n"

        # Find or create section
        section_header = f"## {section.title()}\n"

        if section_header in existing:
            if append:
                # Insert note after section header
                parts = existing.split(section_header)
                parts[1] = note_entry + parts[1]
                new_content = section_header.join(parts)
            else:
                # Replace section content until next ## or end
                import re
                pattern = rf"(## {re.escape(section.title())}\n)(.*?)(?=\n## |\Z)"
                new_content = re.sub(pattern, rf"\1{note_entry}", existing, flags=re.DOTALL)
        else:
            # Add new section at end
            new_content = existing.rstrip() + f"\n\n{section_header}{note_entry}"

        # Write back
        notes_file.write_text(new_content, encoding='utf-8')

        return {
            "success": True,
            "notes_file": str(notes_file),
            "section": section,
            "content_added": content[:100] + "..." if len(content) > 100 else content,
            "project": project_name,
            "session_id": session_id
        }

    except Exception as e:
        return {"error": f"Failed to store notes: {str(e)}"}


async def tool_get_session_notes(
    section: Optional[str] = None
) -> Dict:
    """
    Retrieve session notes for the current project.

    Args:
        section: Optional section to retrieve (e.g., "decisions"). If None, returns all.
    """
    project_name = os.path.basename(os.getcwd())
    notes_file = Path.home() / ".claude" / "session_notes" / f"{project_name}.md"

    try:
        if not notes_file.exists():
            return {
                "found": False,
                "message": f"No notes found for project: {project_name}",
                "notes_file": str(notes_file)
            }

        content = notes_file.read_text(encoding='utf-8')

        if section:
            # Extract specific section
            import re
            pattern = rf"## {re.escape(section.title())}\n(.*?)(?=\n## |\Z)"
            match = re.search(pattern, content, flags=re.DOTALL)
            if match:
                return {
                    "found": True,
                    "section": section,
                    "content": match.group(1).strip(),
                    "notes_file": str(notes_file)
                }
            else:
                return {
                    "found": False,
                    "message": f"Section '{section}' not found",
                    "available_sections": re.findall(r"## (\w+)", content)
                }

        return {
            "found": True,
            "content": content,
            "notes_file": str(notes_file),
            "project": project_name
        }

    except Exception as e:
        return {"error": f"Failed to get notes: {str(e)}"}


async def tool_get_session_resume(project: str) -> Dict:
    """
    Get all session resume context in a single call.

    Returns consolidated session context:
    - Last session summary and tasks completed
    - Session state (current_focus, next_steps)
    - Active todos (full content)
    - Pending messages count

    This is designed to replace multiple individual queries for /session-resume.
    """
    project_id = get_project_id(project)
    project_name = project.split('/')[-1].split('\\')[-1]  # Extract basename

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        result = {
            "project_name": project_name,
            "last_session": None,
            "session_state": None,
            "active_todos": {
                "in_progress": [],
                "pending": []
            },
            "pending_messages": 0
        }

        # 1. Get last completed session
        cur.execute("""
            SELECT session_summary, session_end, tasks_completed
            FROM claude.sessions
            WHERE project_name = %s AND session_end IS NOT NULL
            ORDER BY session_end DESC LIMIT 1
        """, (project_name,))
        last_session = cur.fetchone()
        if last_session:
            result["last_session"] = {
                "summary": last_session['session_summary'],
                "ended": last_session['session_end'].isoformat() if last_session['session_end'] else None,
                "tasks_completed": last_session['tasks_completed'] or []
            }

        # 2. Get session state
        cur.execute("""
            SELECT current_focus, next_steps
            FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))
        session_state = cur.fetchone()
        if session_state:
            result["session_state"] = {
                "current_focus": session_state['current_focus'],
                "next_steps": session_state['next_steps'] or []
            }

        # 3. Get active todos
        if project_id:
            cur.execute("""
                SELECT t.content, t.status, t.priority
                FROM claude.todos t
                WHERE t.project_id = %s::uuid
                  AND t.is_deleted = false
                  AND t.status IN ('pending', 'in_progress')
                ORDER BY
                  CASE t.status WHEN 'in_progress' THEN 1 ELSE 2 END,
                  t.priority ASC
                LIMIT 15
            """, (project_id,))

            for row in cur.fetchall():
                todo = {
                    "content": row['content'],
                    "priority": row['priority']
                }
                if row['status'] == 'in_progress':
                    result["active_todos"]["in_progress"].append(todo)
                else:
                    result["active_todos"]["pending"].append(todo)

        # 4. Get pending messages count
        cur.execute("""
            SELECT COUNT(*) as count
            FROM claude.messages
            WHERE status = 'pending'
              AND (to_project = %s OR to_project IS NULL)
        """, (project_name,))
        result["pending_messages"] = cur.fetchone()['count']

        cur.close()
        return result

    finally:
        conn.close()


# ============================================================================
# Activity / WCC Tools
# ============================================================================


async def tool_create_activity(
    name: str,
    aliases: Optional[List[str]] = None,
    description: str = "",
    project: str = "",
) -> Dict:
    """Create a named activity for WCC context assembly."""
    project = project or os.path.basename(os.getcwd())
    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    # Generate embedding for the activity
    embed_text = f"{name} {description}" if description else name
    embedding = generate_embedding(embed_text)

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.activities
                (project_id, name, aliases, description, embedding)
            VALUES (%s::uuid, %s, %s, %s, %s::vector)
            ON CONFLICT (project_id, name)
            DO UPDATE SET
                aliases = COALESCE(EXCLUDED.aliases, activities.aliases),
                description = COALESCE(NULLIF(EXCLUDED.description, ''), activities.description),
                embedding = COALESCE(EXCLUDED.embedding, activities.embedding),
                last_accessed_at = NOW()
            RETURNING activity_id::text, (xmax = 0) AS is_insert
        """, (project_id, name, aliases or [], description, embedding))
        row = cur.fetchone()
        conn.commit()
        cur.close()

        is_insert = row['is_insert'] if row else True
        return {
            "success": True,
            "activity_id": row['activity_id'] if row else None,
            "action": "created" if is_insert else "updated",
            "name": name,
            "project": project,
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"Create activity failed: {str(e)}"}
    finally:
        conn.close()


async def tool_list_activities(
    project: str = "",
) -> Dict:
    """List activities with access stats for a project."""
    project = project or os.path.basename(os.getcwd())
    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT activity_id::text, name, aliases, description,
                   last_accessed_at, access_count, is_active
            FROM claude.activities
            WHERE project_id = %s::uuid
            ORDER BY access_count DESC, last_accessed_at DESC
        """, (project_id,))
        rows = cur.fetchall()
        cur.close()

        activities = []
        for r in rows:
            activities.append({
                "activity_id": r['activity_id'],
                "name": r['name'],
                "aliases": r['aliases'] or [],
                "description": r['description'] or "",
                "last_accessed_at": str(r['last_accessed_at']) if r['last_accessed_at'] else None,
                "access_count": r['access_count'],
                "is_active": r['is_active'],
            })

        return {
            "success": True,
            "project": project,
            "count": len(activities),
            "activities": activities,
        }
    except Exception as e:
        return {"error": f"List activities failed: {str(e)}"}
    finally:
        conn.close()


async def tool_update_activity(
    activity_id: str,
    aliases: Optional[List[str]] = None,
    description: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> Dict:
    """Update an existing activity's aliases, description, or active status."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Build dynamic SET clause
        sets = []
        params = []
        if aliases is not None:
            sets.append("aliases = %s")
            params.append(aliases)
        if description is not None:
            sets.append("description = %s")
            params.append(description)
            # Re-embed with new description
            embedding = generate_embedding(description)
            if embedding:
                sets.append("embedding = %s::vector")
                params.append(embedding)
        if is_active is not None:
            sets.append("is_active = %s")
            params.append(is_active)

        if not sets:
            return {"error": "No fields to update"}

        params.append(activity_id)
        cur.execute(f"""
            UPDATE claude.activities
            SET {', '.join(sets)}
            WHERE activity_id = %s::uuid
            RETURNING activity_id::text, name
        """, tuple(params))
        row = cur.fetchone()
        conn.commit()
        cur.close()

        if not row:
            return {"error": f"Activity '{activity_id}' not found"}

        return {
            "success": True,
            "activity_id": row['activity_id'],
            "name": row['name'],
            "updated_fields": [s.split(" = ")[0] for s in sets],
        }
    except Exception as e:
        conn.rollback()
        return {"error": f"Update activity failed: {str(e)}"}
    finally:
        conn.close()


async def tool_assemble_context(
    activity_name: str,
    project: str = "",
    budget: int = 1000,
) -> Dict:
    """Manually assemble WCC context for a named activity."""
    project = project or os.path.basename(os.getcwd())
    project_id = get_project_id(project)
    if not project_id:
        return {"error": f"Project '{project}' not found"}

    # Import wcc_assembly
    import sys as _sys
    scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
    if scripts_dir not in _sys.path:
        _sys.path.insert(0, scripts_dir)

    try:
        from wcc_assembly import assemble_wcc, _lookup_activity_id
    except ImportError:
        return {"error": "wcc_assembly module not found"}

    conn = get_db_connection()
    try:
        activity_id = _lookup_activity_id(conn, project, activity_name)

        wcc_text = assemble_wcc(
            activity_name=activity_name,
            activity_id=activity_id,
            project_name=project,
            conn=conn,
            session_id=None,
            total_budget=budget,
            generate_embedding_fn=generate_embedding,
        )

        return {
            "success": True,
            "activity_name": activity_name,
            "project": project,
            "context": wcc_text or "(no context assembled — activity may not have associated data)",
            "token_estimate": len(wcc_text) // 4 if wcc_text else 0,
        }
    except Exception as e:
        return {"error": f"Context assembly failed: {str(e)}"}
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
            name="get_session_resume",
            description="Get all session resume context in ONE call. Returns: last session summary, session state (focus/next_steps), active todos, pending messages. Use for /session-resume to avoid multiple SQL queries.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project": {
                        "type": "string",
                        "description": "Project name (defaults to current directory basename)"
                    }
                },
                "required": ["project"]
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
        ),
        # Knowledge Tools
        Tool(
            name="store_knowledge",
            description="Store new knowledge with automatic embedding for semantic search. Use for learnings, patterns, gotchas, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short descriptive title"},
                    "description": {"type": "string", "description": "Detailed knowledge content"},
                    "knowledge_type": {
                        "type": "string",
                        "description": "Type: learned, pattern, gotcha, preference, fact, procedure (default: learned)"
                    },
                    "knowledge_category": {"type": "string", "description": "Category (e.g., 'database', 'react', 'testing')"},
                    "code_example": {"type": "string", "description": "Optional code example"},
                    "applies_to_projects": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Projects this knowledge applies to (null = all)"
                    },
                    "applies_to_platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Platforms (windows, mac, linux)"
                    },
                    "confidence_level": {"type": "integer", "description": "Confidence 0-100 (default: 80)"},
                    "source": {"type": "string", "description": "Source of knowledge (e.g., 'session', 'documentation')"}
                },
                "required": ["title", "description"]
            }
        ),
        Tool(
            name="recall_knowledge",
            description="Semantic search over knowledge entries. Use to find relevant learnings, patterns, or facts.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language query"},
                    "limit": {"type": "integer", "description": "Max results (default: 5)"},
                    "knowledge_type": {"type": "string", "description": "Filter by type (optional)"},
                    "project": {"type": "string", "description": "Filter by project (optional)"},
                    "min_similarity": {"type": "number", "description": "Minimum similarity 0-1 (default: 0.5)"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="link_knowledge",
            description="Create a typed relation between knowledge entries (extends, contradicts, supports, etc.).",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_knowledge_id": {"type": "string", "description": "Source knowledge UUID"},
                    "to_knowledge_id": {"type": "string", "description": "Target knowledge UUID"},
                    "relation_type": {
                        "type": "string",
                        "description": "Type: extends, contradicts, supports, supersedes, depends_on, relates_to, part_of, caused_by"
                    },
                    "strength": {"type": "number", "description": "Relation strength 0-1 (default: 1.0)"},
                    "notes": {"type": "string", "description": "Optional notes about the relation"}
                },
                "required": ["from_knowledge_id", "to_knowledge_id", "relation_type"]
            }
        ),
        Tool(
            name="get_related_knowledge",
            description="Get knowledge entries related to a given entry via knowledge_relations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "knowledge_id": {"type": "string", "description": "Knowledge UUID to find relations for"},
                    "relation_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by relation types (optional)"
                    },
                    "include_reverse": {"type": "boolean", "description": "Include incoming relations (default: true)"}
                },
                "required": ["knowledge_id"]
            }
        ),
        Tool(
            name="mark_knowledge_applied",
            description="Track when knowledge is applied successfully or fails. Updates confidence level.",
            inputSchema={
                "type": "object",
                "properties": {
                    "knowledge_id": {"type": "string", "description": "Knowledge UUID that was applied"},
                    "success": {"type": "boolean", "description": "Whether application was successful (default: true)"}
                },
                "required": ["knowledge_id"]
            }
        ),
        # Session Facts Tools
        Tool(
            name="store_session_fact",
            description="Store a fact in your session notepad. Use for: credentials, configs, endpoints, decisions, findings. These facts auto-inject into context so you don't forget them.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fact_key": {"type": "string", "description": "Unique key for the fact (e.g., 'api_endpoint', 'nimbus_creds')"},
                    "fact_value": {"type": "string", "description": "The fact value to store"},
                    "fact_type": {
                        "type": "string",
                        "description": "Type: credential, config, endpoint, decision, note, data, reference (default: note)"
                    },
                    "is_sensitive": {"type": "boolean", "description": "If true, value won't appear in logs (default: false)"},
                    "project_name": {"type": "string", "description": "Project name (default: current directory)"}
                },
                "required": ["fact_key", "fact_value"]
            }
        ),
        Tool(
            name="recall_session_fact",
            description="Recall a specific fact by key. Looks in current session first, falls back to recent sessions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "fact_key": {"type": "string", "description": "The key of the fact to recall"},
                    "project_name": {"type": "string", "description": "Project name (default: current directory)"}
                },
                "required": ["fact_key"]
            }
        ),
        Tool(
            name="list_session_facts",
            description="List all facts stored in the current session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Project name (default: current directory)"},
                    "include_sensitive": {"type": "boolean", "description": "Include sensitive fact values (default: false)"}
                },
                "required": []
            }
        ),
        Tool(
            name="recall_previous_session_facts",
            description="Recall facts from previous sessions. Use when resuming work or context got compacted and you need to recover important info from your old notepad.",
            inputSchema={
                "type": "object",
                "properties": {
                    "project_name": {"type": "string", "description": "Project name (default: current directory)"},
                    "n_sessions": {"type": "integer", "description": "Number of previous sessions to check (default: 3)"},
                    "fact_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter by fact types (optional)"
                    }
                },
                "required": []
            }
        ),
        # Session Notes Tools
        Tool(
            name="store_session_notes",
            description="Store structured notes during a session. Use for: progress tracking, decisions, blockers, findings. Notes persist to markdown file.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Note content to store"},
                    "section": {
                        "type": "string",
                        "description": "Section header: decisions, progress, blockers, findings, general (default: general)"
                    },
                    "append": {"type": "boolean", "description": "Append to section (default: true). False replaces section."}
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="get_session_notes",
            description="Retrieve session notes for the current project. Useful after context compaction to review what was done.",
            inputSchema={
                "type": "object",
                "properties": {
                    "section": {"type": "string", "description": "Section to retrieve (optional). If omitted, returns all notes."}
                },
                "required": []
            }
        ),
        Tool(
            name="update_config",
            description="Create or update a deployable config component (skill, rule, instruction, or CLAUDE.md section) with versioning and filesystem deployment. If the component exists, updates it with version snapshot. If it doesn't exist, creates it. Use this instead of raw SQL for managing skills, rules, and instructions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_type": {
                        "type": "string",
                        "enum": ["skill", "rule", "instruction", "claude_md"],
                        "description": "What to create or update."
                    },
                    "project": {
                        "type": "string",
                        "description": "Project name (for scoping and file deployment)."
                    },
                    "component_name": {
                        "type": "string",
                        "description": "Name of the skill/rule/instruction. Not needed for claude_md."
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write."
                    },
                    "change_reason": {
                        "type": "string",
                        "description": "Why this change was made (stored in version history)."
                    },
                    "section": {
                        "type": "string",
                        "description": "For claude_md only — which section to update."
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["replace", "append"],
                        "description": "Replace content (default) or append to existing.",
                        "default": "replace"
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["global", "project_type", "project", "command", "agent"],
                        "description": "For creating new components — scope level. Defaults to 'project' for skills, 'global' for rules/instructions. Ignored when updating existing components."
                    },
                    "description": {
                        "type": "string",
                        "description": "For creating new components — optional description text."
                    }
                },
                "required": ["component_type", "project"]
            }
        ),
        # WCC activity tools removed from MCP surface (2026-03-14)
        # Internal plumbing — 0-1 calls ever. Functions remain in code for internal use.
        # Removed: create_activity, list_activities, update_activity, assemble_context
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_project_context":
            result = await tool_get_project_context(arguments['project_path'])
        elif name == "get_session_resume":
            result = await tool_get_session_resume(arguments['project'])
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
        # Knowledge tools
        elif name == "store_knowledge":
            result = await tool_store_knowledge(
                arguments['title'],
                arguments['description'],
                arguments.get('knowledge_type', 'learned'),
                arguments.get('knowledge_category'),
                arguments.get('code_example'),
                arguments.get('applies_to_projects'),
                arguments.get('applies_to_platforms'),
                arguments.get('confidence_level', 80),
                arguments.get('source')
            )
        elif name == "recall_knowledge":
            result = await tool_recall_knowledge(
                arguments['query'],
                arguments.get('limit', 5),
                arguments.get('knowledge_type'),
                arguments.get('project'),
                arguments.get('min_similarity', 0.5)
            )
        elif name == "link_knowledge":
            result = await tool_link_knowledge(
                arguments['from_knowledge_id'],
                arguments['to_knowledge_id'],
                arguments['relation_type'],
                arguments.get('strength', 1.0),
                arguments.get('notes')
            )
        elif name == "get_related_knowledge":
            result = await tool_get_related_knowledge(
                arguments['knowledge_id'],
                arguments.get('relation_types'),
                arguments.get('include_reverse', True)
            )
        elif name == "mark_knowledge_applied":
            result = await tool_mark_knowledge_applied(
                arguments['knowledge_id'],
                arguments.get('success', True)
            )
        # Session Facts tools
        elif name == "store_session_fact":
            result = await tool_store_session_fact(
                arguments['fact_key'],
                arguments['fact_value'],
                arguments.get('fact_type', 'note'),
                arguments.get('is_sensitive', False),
                arguments.get('project_name')
            )
        elif name == "recall_session_fact":
            result = await tool_recall_session_fact(
                arguments['fact_key'],
                arguments.get('project_name')
            )
        elif name == "list_session_facts":
            result = await tool_list_session_facts(
                arguments.get('project_name'),
                arguments.get('include_sensitive', False)
            )
        elif name == "recall_previous_session_facts":
            result = await tool_recall_previous_session_facts(
                arguments.get('project_name'),
                arguments.get('n_sessions', 3),
                arguments.get('fact_types')
            )
        # Session Notes tools
        elif name == "store_session_notes":
            result = await tool_store_session_notes(
                arguments['content'],
                arguments.get('section', 'general'),
                arguments.get('append', True)
            )
        elif name == "get_session_notes":
            result = await tool_get_session_notes(
                arguments.get('section')
            )
        elif name == "update_config":
            from server_v2 import update_config
            result = update_config(
                component_type=arguments['component_type'],
                project=arguments['project'],
                component_name=arguments.get('component_name', ''),
                content=arguments.get('content', ''),
                change_reason=arguments.get('change_reason', ''),
                section=arguments.get('section', ''),
                mode=arguments.get('mode', 'replace'),
                scope=arguments.get('scope', ''),
                description=arguments.get('description', ''),
            )
        # WCC tools removed from MCP surface (2026-03-14) — functions still available internally
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
