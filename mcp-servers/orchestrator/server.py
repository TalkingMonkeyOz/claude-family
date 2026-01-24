#!/usr/bin/env python3
"""
Claude Agent Orchestrator - Full MCP Server

Exposes agent spawning AND messaging capabilities via MCP protocol.

Tools:
- spawn_agent: Spawn an isolated Claude agent
- list_agent_types: List available agent types
- search_agents: Search for agents by capability/use case (progressive discovery)
- recommend_agent: Get agent recommendation for a task
- check_inbox: Check for pending messages
- send_message: Send message to another Claude/project
- broadcast: Send to all active Claudes
- acknowledge: Mark message as read
- get_active_sessions: See who's online
- reply_to: Reply to a specific message
"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

# Ensure we're running from the orchestrator directory so relative paths work
SCRIPT_DIR = Path(__file__).parent.resolve()
os.chdir(SCRIPT_DIR)

# MCP SDK imports
try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import Tool, TextContent
except ImportError:
    print("ERROR: MCP SDK not installed. Install with: pip install mcp", file=sys.stderr)
    sys.exit(1)

# PostgreSQL for messaging (supports both psycopg2 and psycopg3)
POSTGRES_AVAILABLE = False
psycopg = None
RealDictCursor = None

try:
    # Try psycopg3 first (newer)
    import psycopg
    from psycopg.rows import dict_row
    POSTGRES_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        # Fall back to psycopg2
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        POSTGRES_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        POSTGRES_AVAILABLE = False
        PSYCOPG_VERSION = 0
        print("WARNING: Neither psycopg nor psycopg2 installed. Messaging features disabled.", file=sys.stderr)

# Import our orchestrator
from orchestrator_prototype import AgentOrchestrator


# Initialize MCP server
app = Server("claude-orchestrator")

# Initialize orchestrator
orchestrator = AgentOrchestrator()


# ============================================================================
# Database Connection Helper
# ============================================================================

def get_db_connection():
    """Get PostgreSQL connection for messaging."""
    if not POSTGRES_AVAILABLE:
        raise RuntimeError("PostgreSQL not available - neither psycopg nor psycopg2 installed")

    # Try environment variables first, fall back to correct local dev connection
    conn_string = os.environ.get('DATABASE_URI') or os.environ.get('POSTGRES_CONNECTION_STRING')
    if not conn_string:
        # Local development fallback - use correct password
        conn_string = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost:5432/ai_company_foundation'

    if PSYCOPG_VERSION == 3:
        # psycopg3 syntax
        return psycopg.connect(conn_string, row_factory=dict_row)
    else:
        # psycopg2 syntax
        return psycopg.connect(conn_string, cursor_factory=RealDictCursor)


# ============================================================================
# Messaging Functions
# ============================================================================

def check_inbox(
    project_name: Optional[str] = None,
    session_id: Optional[str] = None,
    include_broadcasts: bool = True,
    include_read: bool = False
) -> dict:
    """Check for pending messages.

    Args:
        project_name: Filter to messages sent to this project
        session_id: Filter to messages sent to this session
        include_broadcasts: Include messages with no specific recipient
        include_read: Also include already-read messages (default: pending only)
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Status filter
        if include_read:
            status_condition = "status IN ('pending', 'read')"
        else:
            status_condition = "status = 'pending'"

        conditions = [status_condition]
        params = []

        # Build WHERE clause for recipients
        or_conditions = []
        has_specific_recipient = False

        if project_name:
            or_conditions.append("to_project = %s")
            params.append(project_name)
            has_specific_recipient = True
        if session_id:
            or_conditions.append("to_session_id = %s")
            params.append(session_id)
            has_specific_recipient = True

        # If no specific recipient filter, show ONLY true broadcasts
        # (not all project-targeted messages across all projects)
        if not has_specific_recipient:
            # Show ONLY true broadcasts (both to_session_id and to_project are NULL)
            or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")
        elif include_broadcasts:
            # Also include true broadcasts when specific recipient is provided
            or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")

        conditions.append(f"({' OR '.join(or_conditions)})")

        query = f"""
            SELECT
                message_id::text,
                from_session_id::text,
                to_project,
                message_type,
                priority,
                subject,
                body,
                metadata,
                status,
                created_at
            FROM claude.messages
            WHERE {' AND '.join(conditions)}
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'normal' THEN 2
                    ELSE 3
                END,
                created_at DESC
            LIMIT 20
        """

        cur.execute(query, params)
        messages = cur.fetchall()
        cur.close()

        # Convert to list of dicts and handle datetime
        result_messages = []
        for msg in messages:
            msg_dict = dict(msg) if not isinstance(msg, dict) else msg
            if msg_dict.get('created_at'):
                msg_dict['created_at'] = msg_dict['created_at'].isoformat()
            result_messages.append(msg_dict)

        return {
            "count": len(result_messages),
            "messages": result_messages
        }
    finally:
        conn.close()


def send_message(
    message_type: str,
    body: str,
    subject: Optional[str] = None,
    to_project: Optional[str] = None,
    to_session_id: Optional[str] = None,
    priority: str = "normal",
    from_session_id: Optional[str] = None,
    metadata: Optional[dict] = None
) -> dict:
    """Send a message to another Claude instance or project."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.messages
            (from_session_id, to_session_id, to_project, message_type, priority, subject, body, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING message_id::text, created_at
        """, (
            from_session_id,
            to_session_id,
            to_project,
            message_type,
            priority,
            subject,
            body,
            json.dumps(metadata or {})
        ))
        result = cur.fetchone()
        cur.close()
        conn.commit()

        result_dict = dict(result) if not isinstance(result, dict) else result
        return {
            "success": True,
            "message_id": result_dict['message_id'],
            "created_at": result_dict['created_at'].isoformat()
        }
    finally:
        conn.close()


def broadcast(body: str, subject: Optional[str] = None, from_session_id: Optional[str] = None, priority: str = "normal") -> dict:
    """Broadcast message to all active Claude instances."""
    return send_message(
        message_type="broadcast",
        body=body,
        subject=subject,
        priority=priority,
        from_session_id=from_session_id,
        to_project=None,
        to_session_id=None
    )


def acknowledge(message_id: str, action: str = "read", project_id: str = None, defer_reason: str = None, priority: int = 3) -> dict:
    """Mark a message as read, acknowledged, actioned, or deferred.

    Args:
        message_id: UUID of the message
        action: One of 'read', 'acknowledged', 'actioned', 'deferred'
        project_id: Required for 'actioned' - project to create todo in
        defer_reason: Required for 'deferred' - reason for deferral
        priority: Optional priority for created todo (default 3)

    Returns:
        dict with success status and optional todo_id
    """
    # For 'actioned' and 'deferred', delegate to the specific functions
    if action == "actioned":
        if not project_id:
            return {"success": False, "error": "project_id required for actioned messages"}
        return action_message(message_id, project_id, priority)

    if action == "deferred":
        if not defer_reason:
            return {"success": False, "error": "defer_reason required for deferred messages"}
        return defer_message(message_id, defer_reason)

    # Handle 'read' and 'acknowledged' as before
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if action == "read":
            cur.execute("""
                UPDATE claude.messages
                SET status = 'read', read_at = NOW()
                WHERE message_id = %s
                RETURNING message_id::text
            """, (message_id,))
        else:  # acknowledged
            cur.execute("""
                UPDATE claude.messages
                SET status = 'acknowledged', acknowledged_at = NOW()
                WHERE message_id = %s
                RETURNING message_id::text
            """, (message_id,))

        result = cur.fetchone()
        cur.close()
        conn.commit()

        return {
            "success": result is not None,
            "message_id": message_id,
            "new_status": action
        }
    finally:
        conn.close()


def get_active_sessions() -> dict:
    """Get all currently active Claude sessions."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT
                sh.session_id::text,
                i.identity_name,
                sh.project_name,
                sh.session_start,
                EXTRACT(EPOCH FROM (NOW() - sh.session_start))/60 as minutes_active
            FROM claude.sessions sh
            JOIN claude.identities i ON sh.identity_id = i.identity_id
            WHERE sh.session_end IS NULL
            ORDER BY sh.session_start DESC
        """)
        sessions = cur.fetchall()
        cur.close()

        result_sessions = []
        for s in sessions:
            s_dict = dict(s) if not isinstance(s, dict) else s
            if s_dict.get('session_start'):
                s_dict['session_start'] = s_dict['session_start'].isoformat()
            if s_dict.get('minutes_active'):
                s_dict['minutes_active'] = float(s_dict['minutes_active'])
            result_sessions.append(s_dict)

        return {
            "count": len(result_sessions),
            "sessions": result_sessions
        }
    finally:
        conn.close()


def reply_to(original_message_id: str, body: str, from_session_id: Optional[str] = None) -> dict:
    """Reply to a specific message.

    Thread-safe: Properly manages connection lifecycle.
    """
    # First, fetch the original message details
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT from_session_id::text, to_project, subject
            FROM claude.messages
            WHERE message_id = %s
        """, (original_message_id,))
        original = cur.fetchone()
        cur.close()
    finally:
        conn.close()

    if not original:
        return {"success": False, "error": "Original message not found"}

    original_dict = dict(original) if not isinstance(original, dict) else original

    # Send reply back to original sender (uses its own connection)
    return send_message(
        message_type="notification",
        body=body,
        subject=f"Re: {original_dict['subject']}" if original_dict.get('subject') else "Reply",
        to_session_id=original_dict.get('from_session_id'),
        to_project=original_dict.get('to_project'),
        from_session_id=from_session_id,
        metadata={"reply_to": original_message_id}
    )


def action_message(message_id: str, project_id: str, priority: int = 3) -> dict:
    """Convert a message into an actionable todo.

    Args:
        message_id: UUID of the message to action
        project_id: UUID of the project to create todo for
        priority: Priority level 1-5 (default 3)

    Returns:
        dict with success status and todo_id
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1. Fetch message details
        cur.execute("""
            SELECT subject, body, message_type
            FROM claude.messages
            WHERE message_id = %s
        """, (message_id,))
        message = cur.fetchone()

        if not message:
            cur.close()
            conn.close()
            return {"success": False, "error": "Message not found"}

        message_dict = dict(message) if not isinstance(message, dict) else message

        # 2. Create todo content from message
        content = message_dict.get('subject', 'Unnamed task')
        active_form = f"Working on: {content}"

        # 3. Create todo with message link
        cur.execute("""
            INSERT INTO claude.todos
            (project_id, content, active_form, status, priority, source_message_id)
            VALUES (%s, %s, %s, 'pending', %s, %s)
            RETURNING todo_id::text
        """, (project_id, content, active_form, priority, message_id))

        todo_result = cur.fetchone()
        todo_dict = dict(todo_result) if not isinstance(todo_result, dict) else todo_result
        todo_id = todo_dict['todo_id']

        # 4. Update message status to 'actioned'
        cur.execute("""
            UPDATE claude.messages
            SET status = 'actioned', acknowledged_at = NOW()
            WHERE message_id = %s
        """, (message_id,))

        cur.close()
        conn.commit()

        return {
            "success": True,
            "todo_id": todo_id,
            "message": "Message converted to todo successfully"
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def defer_message(message_id: str, reason: str) -> dict:
    """Explicitly defer a message with a reason.

    Args:
        message_id: UUID of the message to defer
        reason: Explanation for why message is being deferred

    Returns:
        dict with success status
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Update message status and store defer reason in metadata
        cur.execute("""
            UPDATE claude.messages
            SET status = 'deferred',
                acknowledged_at = NOW(),
                metadata = COALESCE(metadata, '{}'::jsonb) || jsonb_build_object('defer_reason', %s, 'deferred_at', NOW()::text)
            WHERE message_id = %s
            RETURNING message_id::text
        """, (reason, message_id))

        result = cur.fetchone()
        cur.close()
        conn.commit()

        if not result:
            return {"success": False, "error": "Message not found"}

        return {
            "success": True,
            "message": "Message deferred successfully",
            "reason": reason
        }
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Context Injection Functions
# ============================================================================

def get_context_for_task(
    task: str,
    file_patterns: Optional[List[str]] = None,
    agent_type: Optional[str] = None
) -> dict:
    """
    Get composed context for a task based on context_rules.

    Queries context_rules matching task keywords, file patterns, or agent type.
    Returns prioritized context from coding_standards and static context.

    Args:
        task: Task description to analyze for keywords
        file_patterns: Optional file patterns to match (e.g., ['**/*.cs'])
        agent_type: Optional agent type to match rules for

    Returns:
        dict with 'context' string, 'rules_matched' list, 'standards_loaded' list
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Extract keywords from task
        task_lower = task.lower()
        task_words = set(task_lower.split())

        # Build query to find matching rules
        cur.execute("""
            SELECT
                rule_id, name, task_keywords, file_patterns, agent_types,
                inject_standards, inject_vault_query, inject_static_context, priority
            FROM claude.context_rules
            WHERE active = true
            ORDER BY priority DESC
        """)

        rules = cur.fetchall()
        matched_rules = []
        standards_to_load = set()
        static_contexts = []
        vault_queries = []

        for rule in rules:
            rule_dict = dict(rule) if not isinstance(rule, dict) else rule
            matched = False

            # Check task_keywords match
            if rule_dict.get('task_keywords'):
                for keyword in rule_dict['task_keywords']:
                    if keyword.lower() in task_lower:
                        matched = True
                        break

            # Check file_patterns match
            if not matched and file_patterns and rule_dict.get('file_patterns'):
                for rule_pattern in rule_dict['file_patterns']:
                    for file_pattern in file_patterns:
                        # Simple pattern matching (could be improved with fnmatch)
                        if rule_pattern.replace('**/', '').replace('*', '') in file_pattern:
                            matched = True
                            break

            # Check agent_type match
            if not matched and agent_type and rule_dict.get('agent_types'):
                if agent_type in rule_dict['agent_types']:
                    matched = True

            if matched:
                matched_rules.append({
                    'name': rule_dict['name'],
                    'priority': rule_dict['priority']
                })

                if rule_dict.get('inject_standards'):
                    standards_to_load.update(rule_dict['inject_standards'])

                if rule_dict.get('inject_static_context'):
                    static_contexts.append(rule_dict['inject_static_context'])

                if rule_dict.get('inject_vault_query'):
                    vault_queries.append(rule_dict['inject_vault_query'])

        # Load coding standards content
        standards_content = []
        if standards_to_load:
            placeholders = ','.join(['%s'] * len(standards_to_load))
            cur.execute(f"""
                SELECT name, content
                FROM claude.coding_standards
                WHERE name IN ({placeholders}) AND active = true
            """, list(standards_to_load))

            for std in cur.fetchall():
                std_dict = dict(std) if not isinstance(std, dict) else std
                if std_dict.get('content'):
                    standards_content.append(f"=== {std_dict['name']} STANDARDS ===\n{std_dict['content']}")

        cur.close()

        # Compose final context
        context_parts = []

        if standards_content:
            context_parts.extend(standards_content)

        if static_contexts:
            context_parts.extend(static_contexts)

        # Note: vault_queries would need RAG integration - store for future use
        final_context = "\n\n".join(context_parts) if context_parts else ""

        return {
            "context": final_context[:10000],  # Limit context size
            "rules_matched": matched_rules,
            "standards_loaded": list(standards_to_load),
            "vault_queries": vault_queries  # For future RAG integration
        }

    except Exception as e:
        return {
            "context": "",
            "rules_matched": [],
            "error": str(e)
        }
    finally:
        conn.close()


# ============================================================================
# Agent Status Functions
# ============================================================================

def update_agent_status(
    session_id: str,
    agent_type: str,
    current_status: str = "working",
    activity: Optional[str] = None,
    progress_pct: Optional[int] = None,
    discoveries: Optional[List[dict]] = None,
    parent_session_id: Optional[str] = None,
    task_summary: Optional[str] = None
) -> dict:
    """
    Update or create agent status record.

    Agents should call this every ~5 tool calls to report progress.

    Args:
        session_id: This agent's session ID
        agent_type: Agent type (e.g., 'coder-haiku')
        current_status: 'starting', 'working', 'waiting', 'completed', 'failed', 'aborted'
        activity: Current activity description
        progress_pct: Estimated progress 0-100
        discoveries: List of discoveries to share with other agents
        parent_session_id: Boss session that spawned this agent
        task_summary: Brief task description

    Returns:
        dict with success status
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Check if status record exists
        cur.execute("""
            SELECT status_id FROM claude.agent_status
            WHERE agent_session_id = %s
        """, (session_id,))

        existing = cur.fetchone()

        if existing:
            # Update existing record
            cur.execute("""
                UPDATE claude.agent_status
                SET current_status = %s,
                    current_activity = COALESCE(%s, current_activity),
                    progress_pct = COALESCE(%s, progress_pct),
                    discoveries = CASE WHEN %s IS NOT NULL THEN %s::jsonb ELSE discoveries END,
                    tool_call_count = tool_call_count + 1,
                    last_heartbeat = NOW()
                WHERE agent_session_id = %s
                RETURNING status_id::text
            """, (
                current_status,
                activity,
                progress_pct,
                json.dumps(discoveries) if discoveries else None,
                json.dumps(discoveries) if discoveries else None,
                session_id
            ))
        else:
            # Create new record
            cur.execute("""
                INSERT INTO claude.agent_status
                (agent_session_id, parent_session_id, agent_type, task_summary,
                 current_status, current_activity, progress_pct, discoveries)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING status_id::text
            """, (
                session_id,
                parent_session_id,
                agent_type,
                task_summary,
                current_status,
                activity,
                progress_pct,
                json.dumps(discoveries or [])
            ))

        result = cur.fetchone()
        result_dict = dict(result) if not isinstance(result, dict) else result

        conn.commit()
        cur.close()

        return {
            "success": True,
            "status_id": result_dict['status_id'],
            "current_status": current_status
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def get_agent_statuses(parent_session_id: Optional[str] = None) -> dict:
    """
    Get status of all agents (optionally filtered by parent).

    Args:
        parent_session_id: Filter to agents spawned by this session

    Returns:
        dict with list of agent statuses
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        if parent_session_id:
            cur.execute("""
                SELECT
                    agent_session_id::text,
                    parent_session_id::text,
                    agent_type,
                    task_summary,
                    current_status,
                    current_activity,
                    progress_pct,
                    tool_call_count,
                    discoveries,
                    last_heartbeat,
                    created_at,
                    EXTRACT(EPOCH FROM (NOW() - last_heartbeat)) as seconds_since_heartbeat
                FROM claude.agent_status
                WHERE parent_session_id = %s
                ORDER BY created_at DESC
            """, (parent_session_id,))
        else:
            cur.execute("""
                SELECT
                    agent_session_id::text,
                    parent_session_id::text,
                    agent_type,
                    task_summary,
                    current_status,
                    current_activity,
                    progress_pct,
                    tool_call_count,
                    discoveries,
                    last_heartbeat,
                    created_at,
                    EXTRACT(EPOCH FROM (NOW() - last_heartbeat)) as seconds_since_heartbeat
                FROM claude.agent_status
                WHERE current_status NOT IN ('completed', 'failed', 'aborted')
                   OR created_at > NOW() - INTERVAL '1 hour'
                ORDER BY last_heartbeat DESC
                LIMIT 20
            """)

        statuses = cur.fetchall()
        cur.close()

        result_statuses = []
        for status in statuses:
            status_dict = dict(status) if not isinstance(status, dict) else status
            # Convert timestamps
            for key in ['last_heartbeat', 'created_at']:
                if status_dict.get(key):
                    status_dict[key] = status_dict[key].isoformat()
            if status_dict.get('seconds_since_heartbeat'):
                status_dict['seconds_since_heartbeat'] = float(status_dict['seconds_since_heartbeat'])
            result_statuses.append(status_dict)

        return {
            "count": len(result_statuses),
            "statuses": result_statuses
        }

    except Exception as e:
        return {"count": 0, "statuses": [], "error": str(e)}
    finally:
        conn.close()


# ============================================================================
# Agent Command Functions
# ============================================================================

def send_agent_command(
    target_session_id: str,
    command: str,
    payload: Optional[dict] = None,
    reason: Optional[str] = None,
    sender_session_id: Optional[str] = None
) -> dict:
    """
    Send a control command to a running agent.

    Args:
        target_session_id: Agent session to receive command
        command: 'ABORT', 'REDIRECT', 'INJECT', 'PAUSE', 'RESUME'
        payload: Command-specific data (e.g., new_task for REDIRECT, context for INJECT)
        reason: Why this command is being sent
        sender_session_id: Session sending the command

    Returns:
        dict with command_id and success status
    """
    valid_commands = ['ABORT', 'REDIRECT', 'INJECT', 'PAUSE', 'RESUME']
    if command not in valid_commands:
        return {"success": False, "error": f"Invalid command. Must be one of: {valid_commands}"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO claude.agent_commands
            (target_session_id, sender_session_id, command, payload, reason)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING command_id::text, created_at
        """, (
            target_session_id,
            sender_session_id,
            command,
            json.dumps(payload) if payload else None,
            reason
        ))

        result = cur.fetchone()
        result_dict = dict(result) if not isinstance(result, dict) else result

        conn.commit()
        cur.close()

        return {
            "success": True,
            "command_id": result_dict['command_id'],
            "command": command,
            "target_session_id": target_session_id,
            "created_at": result_dict['created_at'].isoformat()
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def check_agent_commands(session_id: str) -> dict:
    """
    Check for pending commands for this agent.

    Agents should call this every ~5 tool calls to check for boss commands.

    Args:
        session_id: This agent's session ID

    Returns:
        dict with list of pending commands
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Get pending, non-expired commands
        cur.execute("""
            SELECT
                command_id::text,
                command,
                payload,
                reason,
                created_at
            FROM claude.agent_commands
            WHERE target_session_id = %s
              AND status = 'pending'
              AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY created_at ASC
        """, (session_id,))

        commands = cur.fetchall()

        # Mark commands as acknowledged
        if commands:
            command_ids = [dict(c)['command_id'] if not isinstance(c, dict) else c['command_id'] for c in commands]
            placeholders = ','.join(['%s'] * len(command_ids))
            cur.execute(f"""
                UPDATE claude.agent_commands
                SET status = 'acknowledged', acknowledged_at = NOW()
                WHERE command_id::text IN ({placeholders})
            """, command_ids)
            conn.commit()

        cur.close()

        result_commands = []
        for cmd in commands:
            cmd_dict = dict(cmd) if not isinstance(cmd, dict) else cmd
            if cmd_dict.get('created_at'):
                cmd_dict['created_at'] = cmd_dict['created_at'].isoformat()
            result_commands.append(cmd_dict)

        return {
            "count": len(result_commands),
            "commands": result_commands,
            "has_abort": any(c['command'] == 'ABORT' for c in result_commands),
            "has_redirect": any(c['command'] == 'REDIRECT' for c in result_commands)
        }

    except Exception as e:
        return {"count": 0, "commands": [], "error": str(e)}
    finally:
        conn.close()


def get_unactioned_messages(project_name: str) -> dict:
    """Get actionable messages that haven't been actioned or deferred.

    Args:
        project_name: Name of the project to check

    Returns:
        dict with count and list of unactioned messages
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        cur.execute("""
            SELECT
                message_id::text,
                from_session_id::text,
                message_type,
                priority,
                subject,
                body,
                created_at
            FROM claude.messages
            WHERE to_project = %s
              AND message_type IN ('task_request', 'question', 'handoff')
              AND status NOT IN ('actioned', 'deferred')
            ORDER BY
                CASE priority
                    WHEN 'urgent' THEN 1
                    WHEN 'normal' THEN 2
                    ELSE 3
                END,
                created_at ASC
        """, (project_name,))

        messages = cur.fetchall()
        cur.close()

        # Convert to list of dicts and handle datetime
        result_messages = []
        for msg in messages:
            msg_dict = dict(msg) if not isinstance(msg, dict) else msg
            if msg_dict.get('created_at'):
                msg_dict['created_at'] = msg_dict['created_at'].isoformat()
            result_messages.append(msg_dict)

        return {
            "count": len(result_messages),
            "messages": result_messages
        }
    finally:
        conn.close()


def get_message_history(
    project_name: Optional[str] = None,
    message_type: Optional[str] = None,
    days: int = 7,
    include_sent: bool = True,
    include_received: bool = True,
    limit: int = 50
) -> dict:
    """Get message history with filtering options.

    Args:
        project_name: Filter to messages sent to/from this project
        message_type: Filter by message type (task_request, status_update, etc.)
        days: Number of days to look back (default: 7)
        include_sent: Include messages sent by this project
        include_received: Include messages received by this project
        limit: Maximum messages to return (default: 50)

    Returns:
        dict with sent and received message lists
    """
    conn = get_db_connection()
    try:
        cur = conn.cursor()

        results = {"sent": [], "received": []}

        # Build base conditions
        time_condition = f"created_at > NOW() - INTERVAL '{days} days'"
        type_condition = f"message_type = '{message_type}'" if message_type else "1=1"

        if include_received and project_name:
            cur.execute(f"""
                SELECT
                    message_id::text,
                    from_session_id::text,
                    to_project,
                    message_type,
                    priority,
                    subject,
                    body,
                    status,
                    created_at,
                    read_at,
                    acknowledged_at
                FROM claude.messages
                WHERE (to_project = %s OR (to_session_id IS NULL AND to_project IS NULL))
                  AND {time_condition}
                  AND {type_condition}
                ORDER BY created_at DESC
                LIMIT %s
            """, (project_name, limit))

            for msg in cur.fetchall():
                msg_dict = dict(msg) if not isinstance(msg, dict) else msg
                for key in ['created_at', 'read_at', 'acknowledged_at']:
                    if msg_dict.get(key):
                        msg_dict[key] = msg_dict[key].isoformat()
                results["received"].append(msg_dict)

        if include_sent and project_name:
            # Get session IDs associated with this project
            cur.execute("""
                SELECT DISTINCT session_id::text
                FROM claude.sessions
                WHERE project_name = %s
                ORDER BY session_start DESC
                LIMIT 10
            """, (project_name,))
            session_ids = [row['session_id'] for row in cur.fetchall()]

            if session_ids:
                placeholders = ','.join(['%s'] * len(session_ids))
                cur.execute(f"""
                    SELECT
                        message_id::text,
                        from_session_id::text,
                        to_project,
                        to_session_id::text,
                        message_type,
                        priority,
                        subject,
                        body,
                        status,
                        created_at
                    FROM claude.messages
                    WHERE from_session_id::text IN ({placeholders})
                      AND {time_condition}
                      AND {type_condition}
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (*session_ids, limit))

                for msg in cur.fetchall():
                    msg_dict = dict(msg) if not isinstance(msg, dict) else msg
                    if msg_dict.get('created_at'):
                        msg_dict['created_at'] = msg_dict['created_at'].isoformat()
                    results["sent"].append(msg_dict)

        cur.close()

        return {
            "project": project_name,
            "days": days,
            "message_type_filter": message_type,
            "received_count": len(results["received"]),
            "sent_count": len(results["sent"]),
            "messages": results
        }
    finally:
        conn.close()


def bulk_acknowledge(message_ids: List[str], action: str = "read") -> dict:
    """Acknowledge multiple messages at once.

    Args:
        message_ids: List of message UUIDs
        action: 'read' or 'acknowledged'

    Returns:
        dict with success count and any errors
    """
    if action not in ('read', 'acknowledged'):
        return {"success": False, "error": "action must be 'read' or 'acknowledged'"}

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        success_count = 0
        errors = []

        for msg_id in message_ids:
            try:
                if action == "read":
                    cur.execute("""
                        UPDATE claude.messages
                        SET status = 'read', read_at = NOW()
                        WHERE message_id = %s AND status = 'pending'
                        RETURNING message_id::text
                    """, (msg_id,))
                else:
                    cur.execute("""
                        UPDATE claude.messages
                        SET status = 'acknowledged', acknowledged_at = NOW()
                        WHERE message_id = %s
                        RETURNING message_id::text
                    """, (msg_id,))

                if cur.fetchone():
                    success_count += 1
            except Exception as e:
                errors.append({"message_id": msg_id, "error": str(e)})

        conn.commit()
        cur.close()

        return {
            "success": True,
            "processed": len(message_ids),
            "updated": success_count,
            "errors": errors if errors else None
        }
    finally:
        conn.close()


def get_spec_timeout(agent_type: str) -> int:
    """Get recommended timeout from agent_specs.json.

    Single source of truth for timeouts - no more hardcoding!
    """
    try:
        spec = orchestrator.agent_specs['agent_types'].get(agent_type, {})
        return spec.get('recommended_timeout_seconds', 600)  # Default 600s if not found
    except Exception:
        return 600  # Safe default


def search_agents(query: str, detail_level: str = "summary") -> dict:
    """Search for agents by capability, use case, or name.

    Progressive discovery pattern - load minimal context upfront,
    search for details on-demand. Reduces token usage by ~98%.

    Args:
        query: Search query - agent names, keywords, or use cases
        detail_level: 'name' (just names), 'summary' (name + description),
                      'full' (complete spec)

    Returns:
        dict with matching agents at requested detail level
    """
    query_lower = query.lower()
    keywords = query_lower.split()
    results = []

    for name, spec in orchestrator.agent_specs['agent_types'].items():
        # Build searchable text from name, description, and use_cases
        use_cases = ' '.join(spec.get('use_cases', []))
        searchable = f"{name} {spec.get('description', '')} {use_cases}"
        searchable_lower = searchable.lower()

        # Score by keyword matches
        score = sum(1 for kw in keywords if kw in searchable_lower)

        if score > 0:
            results.append((score, name, spec))

    # Sort by score descending
    results.sort(key=lambda x: -x[0])

    # Format based on detail_level
    if detail_level == "name":
        return {
            "count": len(results),
            "agents": [name for _, name, _ in results],
            "hint": "Use detail_level='summary' or 'full' for more info"
        }

    elif detail_level == "summary":
        agents = []
        for score, name, spec in results:
            agents.append({
                "agent_type": name,
                "description": spec.get('description', ''),
                "model": spec.get('model', ''),
                "cost": spec.get('cost_profile', {}).get('cost_per_task_usd', 'unknown')
            })
        return {
            "count": len(results),
            "agents": agents,
            "hint": "Use detail_level='full' for complete specs including MCP configs"
        }

    else:  # full
        agents = []
        for score, name, spec in results:
            agent_info = {
                "agent_type": name,
                "description": spec.get('description', ''),
                "model": spec.get('model', ''),
                "cost_profile": spec.get('cost_profile', {}),
                "use_cases": spec.get('use_cases', []),
                "read_only": spec.get('read_only', False),
                "recommended_timeout": spec.get('recommended_timeout_seconds', 600),
                "mcp_servers": []
            }
            # Load MCP config to show which MCPs are loaded
            mcp_config_path = orchestrator.base_dir / spec.get('mcp_config', '')
            try:
                with open(mcp_config_path, 'r') as f:
                    mcp_config = json.load(f)
                    agent_info['mcp_servers'] = list(mcp_config.get('mcpServers', {}).keys())
            except:
                pass
            agents.append(agent_info)
        return {
            "count": len(results),
            "agents": agents
        }


def recommend_agent(task: str) -> dict:
    """Analyze task description and recommend best agent type with governance hints.

    Args:
        task: Task description to analyze

    Returns:
        dict with recommended agent type, reason, cost, and governance requirements
    """
    task_lower = task.lower()

    # Estimate task complexity for timeout/agent selection
    complexity = "simple"
    if any(w in task_lower for w in ['service', 'module', 'comprehensive', 'full', 'complete', 'entire']):
        complexity = "complex"
    elif any(w in task_lower for w in ['function', 'method', 'fix', 'update', 'add']):
        complexity = "moderate"

    # Check if task involves database writes (needs governance)
    needs_db_governance = any(w in task_lower for w in [
        'insert', 'update', 'delete', 'database', 'db write', 'create record',
        'feedback', 'session', 'project', 'feature', 'task'
    ])

    # Comprehensive research - use coordinator
    if any(w in task_lower for w in ['comprehensive research', 'thorough research', 'research and compile', 'investigate and document']):
        return {
            "agent": "research-coordinator-sonnet",
            "reason": "Comprehensive research requiring multiple sub-agents",
            "cost": "$0.35+",
            "timeout": get_spec_timeout("research-coordinator-sonnet"),
            "governance": {
                "level": "coordinator",
                "note": "Coordinator spawns child agents, results compiled and returned to caller for review"
            }
        }

    # Security tasks
    if any(w in task_lower for w in ['security', 'vulnerability', 'audit', 'owasp', 'penetration']):
        if 'deep' in task_lower or 'comprehensive' in task_lower:
            return {"agent": "security-opus", "reason": "Deep security audit", "cost": "$1.00", "timeout": get_spec_timeout("security-opus"),
                    "governance": {"level": "read-only", "note": "Cannot modify code, findings returned to caller"}}
        return {"agent": "security-sonnet", "reason": "Security analysis", "cost": "$0.24", "timeout": get_spec_timeout("security-sonnet"),
                "governance": {"level": "read-only", "note": "Cannot modify code, findings returned to caller"}}

    # Testing tasks
    if any(w in task_lower for w in ['playwright', 'e2e', 'browser', 'selenium']):
        return {"agent": "web-tester-haiku", "reason": "Web E2E testing (Playwright)", "cost": "$0.05", "timeout": get_spec_timeout("web-tester-haiku"),
                "governance": {"level": "test-only", "note": "Can run tests, results returned to caller"}}
    if any(w in task_lower for w in ['test', 'unit test', 'pytest', 'jest']):
        return {"agent": "tester-haiku", "reason": "Unit/integration testing", "cost": "$0.05", "timeout": get_spec_timeout("tester-haiku"),
                "governance": {"level": "test-only", "note": "Can write tests, results returned to caller"}}

    # Code review
    if any(w in task_lower for w in ['review', 'code review', 'pr review']):
        return {"agent": "reviewer-sonnet", "reason": "Code review", "cost": "$0.11", "timeout": get_spec_timeout("reviewer-sonnet"),
                "governance": {"level": "read-only", "note": "Cannot modify code, findings returned to caller"}}

    # Python development - check complexity
    if 'python' in task_lower and any(w in task_lower for w in ['write', 'create', 'build', 'fix', 'implement']):
        if complexity == "complex":
            return {
                "agent": "python-coder-haiku",
                "reason": "Python development (complex task - consider breaking down)",
                "cost": "$0.045",
                "timeout": get_spec_timeout("python-coder-haiku"),
                "governance": {
                    "level": "code-write",
                    "note": "Code returned to caller for review before commit",
                    "db_access": needs_db_governance,
                    "warning": "Complex task - consider splitting into smaller sub-tasks"
                }
            }
        return {"agent": "python-coder-haiku", "reason": "Python development", "cost": "$0.045", "timeout": get_spec_timeout("python-coder-haiku"),
                "governance": {"level": "code-write", "note": "Code returned to caller for review before commit"}}

    # C# development
    if any(w in task_lower for w in ['c#', 'csharp', '.net', 'wpf', 'winforms']):
        return {"agent": "winforms-coder-haiku", "reason": "C#/.NET/WinForms development", "cost": "$0.045", "timeout": get_spec_timeout("winforms-coder-haiku"),
                "governance": {"level": "code-write", "note": "Code returned to caller for review before commit"}}

    # Architecture
    if any(w in task_lower for w in ['architect', 'design', 'system design', 'refactor large']):
        return {"agent": "architect-opus", "reason": "Architecture design", "cost": "$0.83", "timeout": get_spec_timeout("architect-opus"),
                "governance": {"level": "advisory", "note": "Recommendations returned to caller for decision"}}

    # Research/analysis
    if any(w in task_lower for w in ['research', 'analyze', 'investigate', 'understand']):
        return {"agent": "analyst-sonnet", "reason": "Research and analysis", "cost": "$0.30", "timeout": get_spec_timeout("analyst-sonnet"),
                "governance": {"level": "read-only", "note": "Analysis returned to caller"}}

    # Planning
    if any(w in task_lower for w in ['plan', 'breakdown', 'sprint', 'roadmap']):
        return {"agent": "planner-sonnet", "reason": "Task planning", "cost": "$0.21", "timeout": get_spec_timeout("planner-sonnet"),
                "governance": {"level": "advisory", "note": "Plan returned to caller for approval"}}

    # Exploration/search tasks - recommend Task tool instead
    if any(w in task_lower for w in ['find', 'search', 'where is', 'locate', 'explore codebase']):
        return {
            "agent": "TASK_TOOL",
            "reason": "Use Task tool with subagent_type='Explore' for codebase exploration",
            "cost": "varies by model",
            "models": ["haiku", "sonnet"],
            "note": "Not an orchestrator agent - use built-in Task tool with model parameter"
        }

    # Complex multi-step research
    if any(w in task_lower for w in ['multi-step', 'complex research', 'gather context']):
        return {
            "agent": "TASK_TOOL",
            "reason": "Use Task tool with subagent_type='general-purpose' for complex research",
            "cost": "varies by model",
            "models": ["haiku", "sonnet", "opus"],
            "note": "Not an orchestrator agent - use built-in Task tool with model parameter"
        }

    # Complex code task - warn about lightweight
    if complexity == "complex":
        return {
            "agent": "coder-haiku",
            "reason": "General coding task (complex - avoid lightweight-haiku)",
            "cost": "$0.035",
            "timeout": get_spec_timeout("coder-haiku"),
            "governance": {
                "level": "code-write",
                "note": "Code returned to caller for review",
                "warning": "Complex task detected. Do NOT use lightweight-haiku. Consider python-coder-haiku for Python or breaking into sub-tasks."
            }
        }

    # Default: general coding
    return {
        "agent": "coder-haiku",
        "reason": "General coding task",
        "cost": "$0.035",
        "timeout": get_spec_timeout("coder-haiku"),
        "governance": {
            "level": "code-write",
            "note": "Code returned to caller for review before commit"
        }
    }


# ============================================================================
# MCP Tool Definitions
# ============================================================================

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available MCP tools."""
    tools = [
        # Agent tools
        Tool(
            name="spawn_agent",
            description=(
                "Spawn an isolated Claude Code agent with specialized MCP configuration. "
                "Returns the agent's output after completion. "
                f"Available agent types: {', '.join(orchestrator.agent_specs['agent_types'].keys())}."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": list(orchestrator.agent_specs['agent_types'].keys()),
                        "description": "Type of agent to spawn"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent"
                    },
                    "workspace_dir": {
                        "type": "string",
                        "description": "Workspace directory (agent will be jailed to this path)"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Optional timeout in seconds (default: from agent spec)",
                        "minimum": 1,
                        "maximum": 1800
                    }
                },
                "required": ["agent_type", "task", "workspace_dir"]
            }
        ),
        Tool(
            name="list_agent_types",
            description="List all available agent types with descriptions, costs, and capabilities.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="recommend_agent",
            description="Analyze a task description and recommend the best agent type to use, based on task keywords and complexity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "task": {
                        "type": "string",
                        "description": "Task description to analyze for agent recommendation"
                    }
                },
                "required": ["task"]
            }
        ),
        Tool(
            name="get_spawn_status",
            description="Get current spawn safeguard status: active spawns, available slots, and configuration.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="reload_agent_specs",
            description="Reload agent specifications from disk. Use after modifying agent_specs.json to pick up changes without restarting.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="spawn_agent_async",
            description=(
                "Spawn an agent asynchronously - returns immediately with task_id. "
                "The agent works in background and reports results via messaging when complete. "
                "Use this when you don't want to block waiting for the agent to finish."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_type": {
                        "type": "string",
                        "enum": list(orchestrator.agent_specs['agent_types'].keys()),
                        "description": "Type of agent to spawn"
                    },
                    "task": {
                        "type": "string",
                        "description": "Task description for the agent"
                    },
                    "workspace_dir": {
                        "type": "string",
                        "description": "Workspace directory for the agent"
                    },
                    "callback_project": {
                        "type": "string",
                        "description": "Project to notify when complete (default: claude-family)"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Optional timeout in seconds (default: from agent spec)",
                        "minimum": 1,
                        "maximum": 1800
                    }
                },
                "required": ["agent_type", "task", "workspace_dir"]
            }
        ),
        Tool(
            name="check_async_task",
            description="Check the status of an async task by its task_id",
            inputSchema={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task ID returned from spawn_agent_async"
                    }
                },
                "required": ["task_id"]
            }
        ),
        Tool(
            name="search_agents",
            description=(
                "Search for available agent types by capability, use case, or name. "
                "Use this BEFORE spawn_agent to discover the right agent for your task. "
                "Returns matching agents with configurable detail level."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - agent names, keywords (e.g. 'python', 'testing', 'security'), or use cases"
                    },
                    "detail_level": {
                        "type": "string",
                        "enum": ["name", "summary", "full"],
                        "default": "summary",
                        "description": "Detail level: 'name' (just names), 'summary' (name + description + cost), 'full' (complete spec including MCP configs)"
                    }
                },
                "required": ["query"]
            }
        ),
    ]

    # Add messaging tools if postgres is available
    if POSTGRES_AVAILABLE:
        tools.extend([
            Tool(
                name="check_inbox",
                description="Check for pending messages from other Claude instances. Returns unread messages addressed to you or broadcast to all. IMPORTANT: Pass project_name to see project-targeted messages!",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Your project name to filter messages (IMPORTANT: required to see project-targeted messages)"
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Your session ID to filter direct messages"
                        },
                        "include_broadcasts": {
                            "type": "boolean",
                            "description": "Include broadcast messages (default: true)"
                        },
                        "include_read": {
                            "type": "boolean",
                            "description": "Include already-read messages (default: false, only pending)"
                        }
                    }
                }
            ),
            Tool(
                name="send_message",
                description="Send a message to another Claude instance or project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_type": {
                            "type": "string",
                            "enum": ["task_request", "status_update", "question", "notification", "handoff", "broadcast"],
                            "description": "Type of message"
                        },
                        "body": {
                            "type": "string",
                            "description": "Message content"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Message subject/title"
                        },
                        "to_project": {
                            "type": "string",
                            "description": "Target project name"
                        },
                        "to_session_id": {
                            "type": "string",
                            "description": "Target session ID (for direct message)"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["urgent", "normal", "low"],
                            "description": "Message priority (default: normal)"
                        },
                        "from_session_id": {
                            "type": "string",
                            "description": "Your session ID"
                        }
                    },
                    "required": ["message_type", "body"]
                }
            ),
            Tool(
                name="broadcast",
                description="Send a message to ALL active Claude instances",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "body": {
                            "type": "string",
                            "description": "Message content"
                        },
                        "subject": {
                            "type": "string",
                            "description": "Message subject"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["urgent", "normal", "low"]
                        },
                        "from_session_id": {
                            "type": "string",
                            "description": "Your session ID"
                        }
                    },
                    "required": ["body"]
                }
            ),
            Tool(
                name="acknowledge",
                description="Mark a message as read, acknowledged, actioned (converted to todo), or deferred (explicitly skipped)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "ID of message to acknowledge"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["read", "acknowledged", "actioned", "deferred"],
                            "description": "Action to take: read, acknowledged, actioned (create todo), or deferred (skip with reason)"
                        },
                        "project_id": {
                            "type": "string",
                            "description": "Required if action='actioned' - UUID of project to create todo in"
                        },
                        "defer_reason": {
                            "type": "string",
                            "description": "Required if action='deferred' - Explanation for why message is being deferred"
                        },
                        "priority": {
                            "type": "integer",
                            "description": "Optional priority for created todo (1-5, default 3). Only used if action='actioned'",
                            "minimum": 1,
                            "maximum": 5
                        }
                    },
                    "required": ["message_id"]
                }
            ),
            Tool(
                name="get_active_sessions",
                description="Get all currently active Claude sessions (who's online)",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="reply_to",
                description="Reply to a specific message",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "original_message_id": {
                            "type": "string",
                            "description": "ID of message to reply to"
                        },
                        "body": {
                            "type": "string",
                            "description": "Reply content"
                        },
                        "from_session_id": {
                            "type": "string",
                            "description": "Your session ID"
                        }
                    },
                    "required": ["original_message_id", "body"]
                }
            ),
            Tool(
                name="get_agent_stats",
                description="Get usage statistics for spawned agents (total sessions, success rate, avg time, cost)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "agent_type": {
                            "type": "string",
                            "description": "Filter by agent type (optional, shows all if not specified)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Limit to last N days (default: all time)",
                            "minimum": 1,
                            "maximum": 365
                        }
                    }
                }
            ),
            Tool(
                name="get_mcp_stats",
                description="Get usage statistics for MCP tool calls (call counts, success rates, avg execution time)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "mcp_server": {
                            "type": "string",
                            "description": "Filter by MCP server name (optional)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Limit to last N days (default: all time)",
                            "minimum": 1,
                            "maximum": 365
                        }
                    }
                }
            ),
            Tool(
                name="get_unactioned_messages",
                description="Get actionable messages (task_request/question/handoff) that haven't been actioned or deferred for a project",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Name of the project to check for unactioned messages"
                        }
                    },
                    "required": ["project_name"]
                }
            ),
            Tool(
                name="get_message_history",
                description="Get message history for a project with filtering options. Shows both sent and received messages with date range and type filters.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_name": {
                            "type": "string",
                            "description": "Project name to get message history for"
                        },
                        "message_type": {
                            "type": "string",
                            "enum": ["task_request", "status_update", "question", "notification", "handoff", "broadcast"],
                            "description": "Filter by message type (optional)"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to look back (default: 7)",
                            "minimum": 1,
                            "maximum": 90
                        },
                        "include_sent": {
                            "type": "boolean",
                            "description": "Include messages sent by this project (default: true)"
                        },
                        "include_received": {
                            "type": "boolean",
                            "description": "Include messages received by this project (default: true)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum messages to return (default: 50)",
                            "minimum": 1,
                            "maximum": 100
                        }
                    }
                }
            ),
            Tool(
                name="bulk_acknowledge",
                description="Acknowledge multiple messages at once. Useful for clearing inbox after reviewing messages.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of message UUIDs to acknowledge"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["read", "acknowledged"],
                            "description": "Action to apply: 'read' or 'acknowledged' (default: read)"
                        }
                    },
                    "required": ["message_ids"]
                }
            ),
            # Context injection tools
            Tool(
                name="get_context_for_task",
                description="Get composed context for a task based on database-driven context_rules. Returns coding standards and relevant documentation matching the task keywords, file patterns, or agent type.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task": {
                            "type": "string",
                            "description": "Task description to analyze for context matching"
                        },
                        "file_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional file patterns to match (e.g., ['**/*.cs', '**/*.sql'])"
                        },
                        "agent_type": {
                            "type": "string",
                            "description": "Optional agent type to match rules for"
                        }
                    },
                    "required": ["task"]
                }
            ),
            # Agent status tools
            Tool(
                name="update_agent_status",
                description="Update this agent's status for visibility by the boss session. Agents should call this every ~5 tool calls to report progress.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "This agent's session ID"
                        },
                        "agent_type": {
                            "type": "string",
                            "description": "Agent type (e.g., 'coder-haiku')"
                        },
                        "current_status": {
                            "type": "string",
                            "enum": ["starting", "working", "waiting", "completed", "failed", "aborted"],
                            "description": "Current status"
                        },
                        "activity": {
                            "type": "string",
                            "description": "Current activity description"
                        },
                        "progress_pct": {
                            "type": "integer",
                            "minimum": 0,
                            "maximum": 100,
                            "description": "Estimated progress 0-100"
                        },
                        "discoveries": {
                            "type": "array",
                            "items": {"type": "object"},
                            "description": "List of discoveries to share"
                        },
                        "parent_session_id": {
                            "type": "string",
                            "description": "Boss session that spawned this agent"
                        },
                        "task_summary": {
                            "type": "string",
                            "description": "Brief task description"
                        }
                    },
                    "required": ["session_id", "agent_type"]
                }
            ),
            Tool(
                name="get_agent_statuses",
                description="Get status of running agents. Boss sessions use this to monitor their spawned agents.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "parent_session_id": {
                            "type": "string",
                            "description": "Filter to agents spawned by this session (optional)"
                        }
                    }
                }
            ),
            # Agent command tools
            Tool(
                name="send_agent_command",
                description="Send a control command to a running agent (ABORT, REDIRECT, INJECT, PAUSE, RESUME)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "target_session_id": {
                            "type": "string",
                            "description": "Agent session to receive command"
                        },
                        "command": {
                            "type": "string",
                            "enum": ["ABORT", "REDIRECT", "INJECT", "PAUSE", "RESUME"],
                            "description": "Command to send"
                        },
                        "payload": {
                            "type": "object",
                            "description": "Command-specific data (e.g., new_task for REDIRECT, context for INJECT)"
                        },
                        "reason": {
                            "type": "string",
                            "description": "Why this command is being sent"
                        },
                        "sender_session_id": {
                            "type": "string",
                            "description": "Your session ID"
                        }
                    },
                    "required": ["target_session_id", "command"]
                }
            ),
            Tool(
                name="check_agent_commands",
                description="Check for pending commands from boss session. Agents should call this every ~5 tool calls.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "This agent's session ID"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
        ])

    return tools


# ============================================================================
# MCP Tool Handlers
# ============================================================================

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls."""

    # Agent tools
    if name == "spawn_agent":
        return await handle_spawn_agent(arguments)
    elif name == "list_agent_types":
        return await handle_list_agent_types()
    elif name == "search_agents":
        return await handle_search_agents(arguments)
    elif name == "recommend_agent":
        return await handle_recommend_agent(arguments)
    elif name == "get_spawn_status":
        return await handle_get_spawn_status()
    elif name == "reload_agent_specs":
        return await handle_reload_agent_specs()
    elif name == "spawn_agent_async":
        return await handle_spawn_agent_async(arguments)
    elif name == "check_async_task":
        return await handle_check_async_task(arguments)

    # Messaging tools
    elif name == "check_inbox":
        return await handle_check_inbox(arguments)
    elif name == "send_message":
        return await handle_send_message(arguments)
    elif name == "broadcast":
        return await handle_broadcast(arguments)
    elif name == "acknowledge":
        return await handle_acknowledge(arguments)
    elif name == "get_active_sessions":
        return await handle_get_active_sessions()
    elif name == "reply_to":
        return await handle_reply_to(arguments)

    # Stats tools
    elif name == "get_agent_stats":
        return await handle_get_agent_stats(arguments)
    elif name == "get_mcp_stats":
        return await handle_get_mcp_stats(arguments)
    elif name == "get_unactioned_messages":
        return await handle_get_unactioned_messages(arguments)
    elif name == "get_message_history":
        return await handle_get_message_history(arguments)
    elif name == "bulk_acknowledge":
        return await handle_bulk_acknowledge(arguments)

    # Context injection tools
    elif name == "get_context_for_task":
        return await handle_get_context_for_task(arguments)

    # Agent status tools
    elif name == "update_agent_status":
        return await handle_update_agent_status(arguments)
    elif name == "get_agent_statuses":
        return await handle_get_agent_statuses(arguments)

    # Agent command tools
    elif name == "send_agent_command":
        return await handle_send_agent_command(arguments)
    elif name == "check_agent_commands":
        return await handle_check_agent_commands(arguments)

    else:
        raise ValueError(f"Unknown tool: {name}")


async def handle_spawn_agent(arguments: dict) -> List[TextContent]:
    """Handle spawn_agent tool call."""
    agent_type = arguments['agent_type']
    task = arguments['task']
    workspace_dir = arguments['workspace_dir']
    timeout = arguments.get('timeout')

    # Spawn the agent
    result = await orchestrator.spawn_agent(
        agent_type=agent_type,
        task=task,
        workspace_dir=workspace_dir,
        timeout=timeout
    )

    # Format response
    if result['success']:
        response = {
            "status": "success",
            "agent_type": result['agent_type'],
            "execution_time_seconds": result['execution_time_seconds'],
            "estimated_cost_usd": result['estimated_cost_usd'],
            "output": result['output'],
            "debug_stderr": result.get('stderr')  # Include stderr for debugging
        }
    else:
        response = {
            "status": "failed",
            "agent_type": result['agent_type'],
            "execution_time_seconds": result['execution_time_seconds'],
            "error": result['error'],
            "stderr": result['stderr']
        }

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_list_agent_types() -> List[TextContent]:
    """Handle list_agent_types tool call."""
    agent_types_info = []

    for agent_type, spec in orchestrator.agent_specs['agent_types'].items():
        info = {
            "agent_type": agent_type,
            "description": spec['description'],
            "model": spec['model'],
            "cost_per_task_usd": spec['cost_profile']['cost_per_task_usd'],
            "read_only": spec.get('read_only', False),
            "use_cases": spec.get('use_cases', []),
            "mcp_servers": []
        }

        # Load MCP config to show which MCPs are loaded
        mcp_config_path = orchestrator.base_dir / spec['mcp_config']
        try:
            with open(mcp_config_path, 'r') as f:
                mcp_config = json.load(f)
                info['mcp_servers'] = list(mcp_config.get('mcpServers', {}).keys())
        except:
            pass

        agent_types_info.append(info)

    return [TextContent(type="text", text=json.dumps(agent_types_info, indent=2))]


async def handle_search_agents(arguments: dict) -> List[TextContent]:
    """Handle search_agents tool call."""
    query = arguments['query']
    detail_level = arguments.get('detail_level', 'summary')
    result = search_agents(query, detail_level)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_recommend_agent(arguments: dict) -> List[TextContent]:
    """Handle recommend_agent tool call."""
    task = arguments['task']
    result = recommend_agent(task)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_spawn_status() -> List[TextContent]:
    """Handle get_spawn_status tool call."""
    status = orchestrator.get_spawn_status()
    return [TextContent(type="text", text=json.dumps(status, indent=2))]


async def handle_reload_agent_specs() -> List[TextContent]:
    """Handle reload_agent_specs tool call."""
    result = orchestrator.reload_specs()
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_spawn_agent_async(arguments: dict) -> List[TextContent]:
    """Handle spawn_agent_async tool call."""
    agent_type = arguments['agent_type']
    task = arguments['task']
    workspace_dir = arguments['workspace_dir']
    callback_project = arguments.get('callback_project')
    timeout = arguments.get('timeout')

    result = await orchestrator.spawn_agent_async(
        agent_type=agent_type,
        task=task,
        workspace_dir=workspace_dir,
        callback_project=callback_project,
        timeout=timeout
    )

    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_check_async_task(arguments: dict) -> List[TextContent]:
    """Handle check_async_task tool call."""
    task_id = arguments['task_id']

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT task_id::text, agent_type, task_description, workspace_dir,
                   callback_project, status, spawned_at, started_at, completed_at,
                   result, error
            FROM claude.async_tasks
            WHERE task_id = %s
        """, (task_id,))

        row = cur.fetchone()
        cur.close()

        if not row:
            return [TextContent(type="text", text=json.dumps({
                "error": f"Task {task_id} not found"
            }, indent=2))]

        row_dict = dict(row) if not isinstance(row, dict) else row
        # Convert datetime to string
        for key in ['spawned_at', 'started_at', 'completed_at']:
            if row_dict.get(key):
                row_dict[key] = row_dict[key].isoformat()

        return [TextContent(type="text", text=json.dumps(row_dict, indent=2))]

    finally:
        conn.close()


async def handle_check_inbox(arguments: dict) -> List[TextContent]:
    """Handle check_inbox tool call."""
    result = check_inbox(
        project_name=arguments.get('project_name'),
        session_id=arguments.get('session_id'),
        include_broadcasts=arguments.get('include_broadcasts', True),
        include_read=arguments.get('include_read', False)
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_send_message(arguments: dict) -> List[TextContent]:
    """Handle send_message tool call."""
    result = send_message(
        message_type=arguments['message_type'],
        body=arguments['body'],
        subject=arguments.get('subject'),
        to_project=arguments.get('to_project'),
        to_session_id=arguments.get('to_session_id'),
        priority=arguments.get('priority', 'normal'),
        from_session_id=arguments.get('from_session_id'),
        metadata=arguments.get('metadata')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_broadcast(arguments: dict) -> List[TextContent]:
    """Handle broadcast tool call."""
    result = broadcast(
        body=arguments['body'],
        subject=arguments.get('subject'),
        from_session_id=arguments.get('from_session_id'),
        priority=arguments.get('priority', 'normal')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_acknowledge(arguments: dict) -> List[TextContent]:
    """Handle acknowledge tool call."""
    result = acknowledge(
        message_id=arguments['message_id'],
        action=arguments.get('action', 'read'),
        project_id=arguments.get('project_id'),
        defer_reason=arguments.get('defer_reason'),
        priority=arguments.get('priority', 3)
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_active_sessions() -> List[TextContent]:
    """Handle get_active_sessions tool call."""
    result = get_active_sessions()
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_reply_to(arguments: dict) -> List[TextContent]:
    """Handle reply_to tool call."""
    result = reply_to(
        original_message_id=arguments['original_message_id'],
        body=arguments['body'],
        from_session_id=arguments.get('from_session_id')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_agent_stats(arguments: dict) -> List[TextContent]:
    """Handle get_agent_stats tool call."""
    agent_type = arguments.get('agent_type')
    days = arguments.get('days')

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Build query with optional filters
        conditions = []
        params = []

        if agent_type:
            conditions.append("agent_type = %s")
            params.append(agent_type)

        if days:
            conditions.append("spawned_at > NOW() - INTERVAL '%s days'")
            params.append(days)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get summary stats
        cur.execute(f"""
            SELECT
                agent_type,
                COUNT(*) as total_sessions,
                COUNT(*) FILTER (WHERE success = true) as successful,
                COUNT(*) FILTER (WHERE success = false) as failed,
                ROUND(AVG(execution_time_seconds)::numeric, 2) as avg_execution_seconds,
                ROUND(SUM(estimated_cost_usd)::numeric, 4) as total_cost_usd,
                MIN(spawned_at) as first_spawn,
                MAX(spawned_at) as last_spawn
            FROM claude.agent_sessions
            {where_clause}
            GROUP BY agent_type
            ORDER BY total_sessions DESC
        """, params)

        rows = cur.fetchall()
        cur.close()

        # Format results
        stats = []
        for row in rows:
            row_dict = dict(row) if not isinstance(row, dict) else row
            # Convert datetime to string
            if row_dict.get('first_spawn'):
                row_dict['first_spawn'] = row_dict['first_spawn'].isoformat()
            if row_dict.get('last_spawn'):
                row_dict['last_spawn'] = row_dict['last_spawn'].isoformat()
            # Convert Decimal to float
            if row_dict.get('avg_execution_seconds'):
                row_dict['avg_execution_seconds'] = float(row_dict['avg_execution_seconds'])
            if row_dict.get('total_cost_usd'):
                row_dict['total_cost_usd'] = float(row_dict['total_cost_usd'])
            stats.append(row_dict)

        return [TextContent(type="text", text=json.dumps({
            "filter": {"agent_type": agent_type, "days": days},
            "stats": stats
        }, indent=2))]

    finally:
        conn.close()


async def handle_get_mcp_stats(arguments: dict) -> List[TextContent]:
    """Handle get_mcp_stats tool call."""
    mcp_server = arguments.get('mcp_server')
    days = arguments.get('days')

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # Build query with optional filters
        conditions = []
        params = []

        if mcp_server:
            conditions.append("mcp_server = %s")
            params.append(mcp_server)

        if days:
            conditions.append("called_at > NOW() - INTERVAL '%s days'")
            params.append(days)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Get summary stats
        cur.execute(f"""
            SELECT
                mcp_server,
                tool_name,
                COUNT(*) as call_count,
                COUNT(*) FILTER (WHERE success = true) as success_count,
                COUNT(*) FILTER (WHERE success = false) as failure_count,
                ROUND(AVG(execution_time_ms)::numeric, 2) as avg_execution_ms,
                MIN(called_at) as first_used,
                MAX(called_at) as last_used
            FROM claude.mcp_usage
            {where_clause}
            GROUP BY mcp_server, tool_name
            ORDER BY call_count DESC
            LIMIT 50
        """, params)

        rows = cur.fetchall()
        cur.close()

        # Format results
        stats = []
        for row in rows:
            row_dict = dict(row) if not isinstance(row, dict) else row
            # Convert datetime to string
            if row_dict.get('first_used'):
                row_dict['first_used'] = row_dict['first_used'].isoformat()
            if row_dict.get('last_used'):
                row_dict['last_used'] = row_dict['last_used'].isoformat()
            # Convert all Decimal/numeric types to float/int for JSON serialization
            for key in ['call_count', 'success_count', 'failure_count']:
                if row_dict.get(key) is not None:
                    row_dict[key] = int(row_dict[key])
            if row_dict.get('avg_execution_ms') is not None:
                row_dict['avg_execution_ms'] = float(row_dict['avg_execution_ms'])
            stats.append(row_dict)

        return [TextContent(type="text", text=json.dumps({
            "filter": {"mcp_server": mcp_server, "days": days},
            "stats": stats,
            "note": "MCP usage tracking requires hooks to be configured to log tool calls"
        }, indent=2))]

    finally:
        conn.close()


async def handle_get_unactioned_messages(arguments: dict) -> List[TextContent]:
    """Handle get_unactioned_messages tool call."""
    project_name = arguments['project_name']
    result = get_unactioned_messages(project_name)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_message_history(arguments: dict) -> List[TextContent]:
    """Handle get_message_history tool call."""
    result = get_message_history(
        project_name=arguments.get('project_name'),
        message_type=arguments.get('message_type'),
        days=arguments.get('days', 7),
        include_sent=arguments.get('include_sent', True),
        include_received=arguments.get('include_received', True),
        limit=arguments.get('limit', 50)
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_bulk_acknowledge(arguments: dict) -> List[TextContent]:
    """Handle bulk_acknowledge tool call."""
    result = bulk_acknowledge(
        message_ids=arguments['message_ids'],
        action=arguments.get('action', 'read')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ============================================================================
# Context Injection Handlers
# ============================================================================

async def handle_get_context_for_task(arguments: dict) -> List[TextContent]:
    """Handle get_context_for_task tool call."""
    result = get_context_for_task(
        task=arguments['task'],
        file_patterns=arguments.get('file_patterns'),
        agent_type=arguments.get('agent_type')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ============================================================================
# Agent Status Handlers
# ============================================================================

async def handle_update_agent_status(arguments: dict) -> List[TextContent]:
    """Handle update_agent_status tool call."""
    result = update_agent_status(
        session_id=arguments['session_id'],
        agent_type=arguments['agent_type'],
        current_status=arguments.get('current_status', 'working'),
        activity=arguments.get('activity'),
        progress_pct=arguments.get('progress_pct'),
        discoveries=arguments.get('discoveries'),
        parent_session_id=arguments.get('parent_session_id'),
        task_summary=arguments.get('task_summary')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_get_agent_statuses(arguments: dict) -> List[TextContent]:
    """Handle get_agent_statuses tool call."""
    result = get_agent_statuses(
        parent_session_id=arguments.get('parent_session_id')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ============================================================================
# Agent Command Handlers
# ============================================================================

async def handle_send_agent_command(arguments: dict) -> List[TextContent]:
    """Handle send_agent_command tool call."""
    result = send_agent_command(
        target_session_id=arguments['target_session_id'],
        command=arguments['command'],
        payload=arguments.get('payload'),
        reason=arguments.get('reason'),
        sender_session_id=arguments.get('sender_session_id')
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


async def handle_check_agent_commands(arguments: dict) -> List[TextContent]:
    """Handle check_agent_commands tool call."""
    result = check_agent_commands(
        session_id=arguments['session_id']
    )
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
