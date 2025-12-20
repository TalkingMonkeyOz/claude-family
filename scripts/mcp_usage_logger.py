#!/usr/bin/env python3
"""
MCP Usage Logger - PostToolUse Hook

Logs all MCP tool calls to claude.mcp_usage for analytics.
Tracks: tool name, execution time, success/failure, input/output sizes.

Usage:
    Called by Claude Code hooks system after each tool use.
    Receives tool execution result on stdin as JSON.

Author: claude-code-unified
Date: 2025-12-12
"""

import sys
import os
import io
import json
import time
import uuid
from datetime import datetime
from typing import Optional


def is_valid_uuid(val: str) -> bool:
    """Check if string is a valid UUID."""
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Database connection
DATABASE_URI = os.environ.get(
    'DATABASE_URI',
    'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost:5432/ai_company_foundation'
)

try:
    import psycopg2
    HAS_DB = True
except ImportError:
    HAS_DB = False


def get_db_connection():
    """Get database connection."""
    if not HAS_DB:
        return None
    try:
        return psycopg2.connect(DATABASE_URI)
    except Exception as e:
        print(f"DB connection failed: {e}", file=sys.stderr)
        return None


def log_mcp_usage(
    tool_name: str,
    mcp_server: str,
    execution_time_ms: int,
    success: bool,
    error_message: Optional[str] = None,
    input_size_bytes: int = 0,
    output_size_bytes: int = 0,
    session_id: Optional[str] = None,
    project_name: Optional[str] = None
):
    """Log MCP tool usage to database."""
    debug_mode = os.environ.get('MCP_LOGGER_DEBUG', '0') == '1'
    if debug_mode:
        print(f"DEBUG: log_mcp_usage() entered", file=sys.stderr)
    conn = get_db_connection()
    if not conn:
        if debug_mode:
            print(f"DEBUG: no DB connection", file=sys.stderr)
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.mcp_usage
            (mcp_server, tool_name, execution_time_ms, success,
             error_message, input_size_bytes, output_size_bytes,
             session_id, project_name, called_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            mcp_server,
            tool_name,
            execution_time_ms,
            success,
            error_message[:500] if error_message else None,
            input_size_bytes,
            output_size_bytes,
            session_id,
            project_name
        ))
        conn.commit()
    except Exception as e:
        # Best effort - don't fail the tool call
        print(f"MCP usage logging failed: {e}", file=sys.stderr)
    finally:
        conn.close()


def extract_mcp_server(tool_name: str) -> str:
    """Extract MCP server name from tool name.

    Examples:
        mcp__postgres__execute_sql -> postgres
        mcp__filesystem__read_file -> filesystem
        Read -> builtin
    """
    if tool_name.startswith('mcp__'):
        parts = tool_name.split('__')
        if len(parts) >= 2:
            return parts[1]
    return 'builtin'


def main():
    """Main entry point for the hook."""
    start_time = time.time()

    # Debug: Log that hook was called
    debug_mode = os.environ.get('MCP_LOGGER_DEBUG', '0') == '1'
    if debug_mode:
        print(f"DEBUG: mcp_usage_logger called", file=sys.stderr)

    # Read hook input from stdin
    try:
        raw_input = sys.stdin.read()
        if debug_mode:
            print(f"DEBUG: raw input: {raw_input[:200]}", file=sys.stderr)
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError as e:
        # No input or invalid JSON - pass through
        if debug_mode:
            print(f"DEBUG: JSON decode error: {e}", file=sys.stderr)
        print(json.dumps({}))
        return 0

    # Extract tool info from PostToolUse format (per Claude Code docs)
    tool_name = hook_input.get('tool_name', '')
    tool_input = hook_input.get('tool_input', {})
    tool_response = hook_input.get('tool_response', {})  # Correct field name per docs
    # Check for error in response
    tool_error = tool_response.get('error') if isinstance(tool_response, dict) else None

    if debug_mode:
        print(f"DEBUG: tool_name={tool_name}", file=sys.stderr)
        print(f"DEBUG: HAS_DB={HAS_DB}", file=sys.stderr)

    # Only log MCP tools (start with mcp__) - skip built-in tools to reduce noise
    if not tool_name.startswith('mcp__'):
        if debug_mode:
            print(f"DEBUG: skipping non-MCP tool", file=sys.stderr)
        print(json.dumps({}))
        return 0

    # Also skip certain MCP tools that are too noisy
    skip_tools = ['mcp__memory__search_nodes']  # Add noisy tools here if needed
    if tool_name in skip_tools:
        print(json.dumps({}))
        return 0

    # Calculate sizes
    input_size = len(json.dumps(tool_input)) if tool_input else 0
    output_size = len(json.dumps(tool_response)) if tool_response else 0

    # Determine success (no error in response)
    success = tool_error is None

    # Extract MCP server
    mcp_server = extract_mcp_server(tool_name)

    # Get session info - prefer hook input (per docs: session_id is passed directly)
    raw_session_id = hook_input.get('session_id') or os.environ.get('CLAUDE_SESSION_ID')
    # Validate UUID - column has FK constraint, so invalid UUIDs will fail
    session_id = raw_session_id if is_valid_uuid(raw_session_id) else None
    project_name = os.environ.get('CLAUDE_PROJECT_NAME')

    # Extract project from cwd if not in env
    if not project_name:
        cwd = hook_input.get('cwd', '')
        # Try to extract project name from path like C:\Projects\project-name
        if 'Projects' in cwd:
            parts = cwd.split('Projects')
            if len(parts) > 1:
                project_name = parts[1].strip('\\/ ').split('\\')[0].split('/')[0]

    # Calculate execution time (approximate - from hook call, not actual tool)
    execution_time_ms = int((time.time() - start_time) * 1000)

    # Log to database
    if debug_mode:
        print(f"DEBUG: calling log_mcp_usage({tool_name}, {mcp_server})", file=sys.stderr)
    log_mcp_usage(
        tool_name=tool_name,
        mcp_server=mcp_server,
        execution_time_ms=execution_time_ms,
        success=success,
        error_message=str(tool_error) if tool_error else None,
        input_size_bytes=input_size,
        output_size_bytes=output_size,
        session_id=session_id,
        project_name=project_name
    )
    if debug_mode:
        print(f"DEBUG: log_mcp_usage completed", file=sys.stderr)

    # Return empty response (don't modify tool output)
    print(json.dumps({}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
