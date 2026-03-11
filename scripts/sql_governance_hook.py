#!/usr/bin/env python3
"""
SQL Governance Hook - PreToolUse on mcp__postgres__execute_sql

Prevents non-infrastructure projects from modifying infrastructure tables
or reading sensitive config tables via raw SQL.

Protected tables (no writes from non-infra projects):
  config_templates, workspaces, project_type_configs,
  protocol_versions, coding_standards, workflow_transitions,
  agent_definitions, context_rules

Sensitive tables (no reads from non-infra projects):
  config_templates (contains DB credentials in content JSONB)

Infrastructure projects (exempt from restrictions):
  claude-family, claude-desktop-config

Hook Event: PreToolUse (matcher: mcp__postgres__execute_sql)
Response: allow | deny

Author: Claude Family
Created: 2026-03-09
"""

import sys
import os
import io
import json
import logging
import re
from pathlib import Path

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup logging
LOG_FILE = Path.home() / ".claude" / "hooks.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('sql_governance')

# Infrastructure projects that are exempt from restrictions
INFRA_PROJECTS = {'claude-family', 'claude-desktop-config'}

# Tables that non-infra projects cannot write to (INSERT/UPDATE/DELETE/ALTER/DROP)
PROTECTED_TABLES = {
    'config_templates', 'workspaces', 'project_type_configs',
    'protocol_versions', 'coding_standards', 'workflow_transitions',
    'agent_definitions', 'context_rules', 'mcp_configs',
}

# Tables that non-infra projects cannot read (contain credentials/sensitive config)
SENSITIVE_TABLES = {
    'config_templates',  # Contains DB credentials in content JSONB
}

# SQL keywords that indicate write operations
WRITE_KEYWORDS = re.compile(
    r'\b(INSERT\s+INTO|UPDATE\s+|DELETE\s+FROM|ALTER\s+TABLE|DROP\s+TABLE|TRUNCATE|CREATE\s+TABLE)\b',
    re.IGNORECASE
)


def get_project_name() -> str:
    """Get project name from CWD."""
    return Path.cwd().name


def extract_table_refs(sql: str) -> set:
    """Extract claude.* table references from SQL."""
    tables = set()
    # Match claude.table_name patterns
    for match in re.finditer(r'claude\.(\w+)', sql, re.IGNORECASE):
        tables.add(match.group(1).lower())
    return tables


def is_write_operation(sql: str) -> bool:
    """Check if SQL contains write operations."""
    return bool(WRITE_KEYWORDS.search(sql))


def allow():
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)


def deny(reason: str):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
        }
    }))
    sys.exit(0)


def main():
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data:
            allow()

        hook_input = json.loads(stdin_data)
        tool_input = hook_input.get('tool_input') or hook_input.get('toolInput', {})
        sql = tool_input.get('sql', '')

        if not sql:
            allow()

        project = get_project_name()

        # Infrastructure projects are exempt
        if project in INFRA_PROJECTS:
            logger.info(f"SQL governance: infra project '{project}' - allowed")
            allow()

        table_refs = extract_table_refs(sql)
        is_write = is_write_operation(sql)

        # Check 1: Block writes to protected tables
        if is_write:
            protected_hits = table_refs & PROTECTED_TABLES
            if protected_hits:
                tables_str = ', '.join(f'claude.{t}' for t in protected_hits)
                logger.warning(
                    f"BLOCKED: Project '{project}' attempted write to protected tables: {tables_str}"
                )
                deny(
                    f"BLOCKED: Project '{project}' cannot modify infrastructure tables ({tables_str}). "
                    f"Config changes must go through claude-family:\n"
                    f"  send_message(message_type='task_request', to_project='claude-family', "
                    f"body='Requesting config change: ...')\n"
                    f"Only claude-family can modify config_templates, workspaces, and other infrastructure tables."
                )

        # Check 2: Block reads on sensitive tables
        sensitive_hits = table_refs & SENSITIVE_TABLES
        if sensitive_hits:
            tables_str = ', '.join(f'claude.{t}' for t in sensitive_hits)
            logger.warning(
                f"BLOCKED: Project '{project}' attempted read on sensitive table: {tables_str}"
            )
            deny(
                f"BLOCKED: Project '{project}' cannot query sensitive tables ({tables_str}). "
                f"These tables contain credentials and infrastructure config.\n"
                f"To request config changes, send a message to claude-family:\n"
                f"  send_message(message_type='task_request', to_project='claude-family', "
                f"body='Need config change: ...')"
            )

        # All checks passed
        logger.info(f"SQL governance: project '{project}' - allowed (tables: {table_refs or 'none detected'})")
        allow()

    except Exception as e:
        logger.error(f"SQL governance hook error: {e}", exc_info=True)
        try:
            from failure_capture import capture_failure
            capture_failure("sql_governance", str(e), "scripts/sql_governance_hook.py")
        except Exception:
            pass
        # Fail-open
        allow()


if __name__ == "__main__":
    main()
