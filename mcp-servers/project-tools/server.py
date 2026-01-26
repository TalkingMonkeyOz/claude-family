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
from typing import Any, Dict, List, Optional
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
# Embedding Helper
# ============================================================================

VOYAGE_API_KEY = os.environ.get('VOYAGE_API_KEY')
EMBEDDING_MODEL = "voyage-3"


def generate_embedding(text: str) -> Optional[List[float]]:
    """Generate embedding for a single text using Voyage AI."""
    if not REQUESTS_AVAILABLE:
        return None
    if not VOYAGE_API_KEY:
        return None

    try:
        response = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "input": [text],
                "model": EMBEDDING_MODEL,
                "input_type": "document"
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as e:
        print(f"Embedding generation failed: {e}", file=sys.stderr)
        return None


def generate_query_embedding(query: str) -> Optional[List[float]]:
    """Generate embedding for a query (uses query input_type for better retrieval)."""
    if not REQUESTS_AVAILABLE:
        return None
    if not VOYAGE_API_KEY:
        return None

    try:
        response = requests.post(
            "https://api.voyageai.com/v1/embeddings",
            headers={
                "Authorization": f"Bearer {VOYAGE_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "input": [query],
                "model": EMBEDDING_MODEL,
                "input_type": "query"
            },
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result["data"][0]["embedding"]
    except Exception as e:
        print(f"Query embedding generation failed: {e}", file=sys.stderr)
        return None


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
                     confidence_level, source, embedding, created_at)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, NOW())
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
                     confidence_level, source, created_at)
                VALUES
                    (gen_random_uuid(), %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
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
    min_similarity: float = 0.5
) -> Dict:
    """Semantic search over knowledge entries."""
    if not VOYAGE_API_KEY:
        return {"error": "VOYAGE_API_KEY not set - cannot perform semantic search"}

    # Generate query embedding
    query_embedding = generate_query_embedding(query)
    if not query_embedding:
        return {"error": "Failed to generate query embedding"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Build query with optional filters
        filters = []
        params = [query_embedding, min_similarity]

        if knowledge_type:
            filters.append("AND knowledge_type = %s")
            params.append(knowledge_type)

        if project:
            filters.append("AND (%s = ANY(applies_to_projects) OR applies_to_projects IS NULL)")
            params.append(project)

        params.append(limit)
        filter_clause = " ".join(filters)

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
              AND 1 - (embedding <=> %s::vector) >= %s
              {filter_clause}
            ORDER BY similarity DESC
            LIMIT %s
        """, [query_embedding] + params)

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

async def tool_store_session_fact(
    fact_key: str,
    fact_value: str,
    fact_type: str = "note",
    is_sensitive: bool = False,
    project_name: Optional[str] = None
) -> Dict:
    """Store a fact in the session notepad (auto-injected into context)."""
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    if not project_name:
        project_name = os.path.basename(os.getcwd())

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
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    if not project_name:
        project_name = os.path.basename(os.getcwd())

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
    session_id = os.environ.get('CLAUDE_SESSION_ID')
    if not project_name:
        project_name = os.path.basename(os.getcwd())

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT fact_id::text, fact_key, fact_value, fact_type, is_sensitive, created_at
            FROM claude.session_facts
            WHERE project_name = %s
              AND (session_id = %s OR session_id IS NULL)
            ORDER BY created_at DESC
        """, (project_name, session_id))

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
            SELECT DISTINCT session_id
            FROM claude.session_facts
            WHERE project_name = %s
              AND session_id IS NOT NULL
            ORDER BY (SELECT MAX(created_at) FROM claude.session_facts sf2 WHERE sf2.session_id = session_facts.session_id) DESC
            LIMIT %s
        """, (project_name, n_sessions))

        session_ids = [row['session_id'] for row in cur.fetchall()]

        if not session_ids:
            return {"message": "No previous session facts found", "facts": []}

        # Build query with optional type filter
        type_filter = ""
        params = [project_name, tuple(session_ids)]
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
              AND session_id IN %s
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
        )
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
