#!/usr/bin/env python3
"""
Claude Agent Orchestrator - Full MCP Server

Exposes agent spawning AND messaging capabilities via MCP protocol.

Tools:
- spawn_agent: Spawn an isolated Claude agent
- list_agent_types: List available agent types
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

    conn_string = os.environ.get(
        'DATABASE_URI',
        os.environ.get(
            'POSTGRES_CONNECTION_STRING',
            'postgresql://postgres:postgres@localhost:5432/ai_company_foundation'
        )
    )

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
        if include_broadcasts:
            or_conditions.append("(to_session_id IS NULL AND to_project IS NULL)")
        if project_name:
            or_conditions.append("to_project = %s")
            params.append(project_name)
        if session_id:
            or_conditions.append("to_session_id = %s")
            params.append(session_id)

        # If no recipient filters specified, show all messages to any project/session
        # This prevents returning 0 when user forgets to pass project_name
        if not or_conditions:
            # Show broadcasts + any messages to any project (but not direct session messages)
            or_conditions.append("to_session_id IS NULL")

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


def acknowledge(message_id: str, action: str = "read") -> dict:
    """Mark a message as read or acknowledged."""
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
        else:
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
        from_session_id=from_session_id,
        metadata={"reply_to": original_message_id}
    )


def recommend_agent(task: str) -> dict:
    """Analyze task description and recommend best agent type.
    
    Args:
        task: Task description to analyze
    
    Returns:
        dict with recommended agent type, reason, and cost
    """
    task_lower = task.lower()
    
    # Security tasks
    if any(w in task_lower for w in ['security', 'vulnerability', 'audit', 'owasp', 'penetration']):
        if 'deep' in task_lower or 'comprehensive' in task_lower:
            return {"agent": "security-opus", "reason": "Deep security audit", "cost": "$1.00"}
        return {"agent": "security-sonnet", "reason": "Security analysis", "cost": "$0.24"}
    
    # Testing tasks
    if any(w in task_lower for w in ['playwright', 'e2e', 'browser', 'selenium']):
        if 'next' in task_lower or 'react' in task_lower:
            return {"agent": "nextjs-tester-haiku", "reason": "Next.js E2E testing", "cost": "$0.06"}
        return {"agent": "web-tester-haiku", "reason": "Web E2E testing", "cost": "$0.05"}
    if any(w in task_lower for w in ['test', 'unit test', 'pytest', 'jest']):
        return {"agent": "tester-haiku", "reason": "Unit/integration testing", "cost": "$0.05"}
    
    # Code review
    if any(w in task_lower for w in ['review', 'code review', 'pr review']):
        return {"agent": "reviewer-sonnet", "reason": "Code review", "cost": "$0.11"}
    
    # Python development
    if 'python' in task_lower and any(w in task_lower for w in ['write', 'create', 'build', 'fix', 'implement']):
        return {"agent": "python-coder-haiku", "reason": "Python development", "cost": "$0.045"}
    
    # C# development
    if any(w in task_lower for w in ['c#', 'csharp', '.net', 'wpf', 'winforms']):
        return {"agent": "csharp-coder-haiku", "reason": "C#/.NET development", "cost": "$0.045"}
    
    # Architecture
    if any(w in task_lower for w in ['architect', 'design', 'system design', 'refactor large']):
        return {"agent": "architect-opus", "reason": "Architecture design", "cost": "$0.83"}
    
    # Research/analysis
    if any(w in task_lower for w in ['research', 'analyze', 'investigate', 'understand']):
        return {"agent": "analyst-sonnet", "reason": "Research and analysis", "cost": "$0.30"}
    
    # Planning
    if any(w in task_lower for w in ['plan', 'breakdown', 'sprint', 'roadmap']):
        return {"agent": "planner-sonnet", "reason": "Task planning", "cost": "$0.21"}
    
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

    # Default: general coding
    return {"agent": "coder-haiku", "reason": "General coding task", "cost": "$0.035"}


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
                        "maximum": 600
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
                description="Mark a message as read or acknowledged",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "message_id": {
                            "type": "string",
                            "description": "ID of message to acknowledge"
                        },
                        "action": {
                            "type": "string",
                            "enum": ["read", "acknowledged"],
                            "description": "Mark as read or fully acknowledged"
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
    elif name == "recommend_agent":
        return await handle_recommend_agent(arguments)

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
            "output": result['output']
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


async def handle_recommend_agent(arguments: dict) -> List[TextContent]:
    """Handle recommend_agent tool call."""
    task = arguments['task']
    result = recommend_agent(task)
    return [TextContent(type="text", text=json.dumps(result, indent=2))]


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
        action=arguments.get('action', 'read')
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
            # Convert Decimal to float
            if row_dict.get('avg_execution_ms'):
                row_dict['avg_execution_ms'] = float(row_dict['avg_execution_ms'])
            stats.append(row_dict)

        return [TextContent(type="text", text=json.dumps({
            "filter": {"mcp_server": mcp_server, "days": days},
            "stats": stats,
            "note": "MCP usage tracking requires hooks to be configured to log tool calls"
        }, indent=2))]

    finally:
        conn.close()


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
