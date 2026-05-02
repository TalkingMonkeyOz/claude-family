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
    """Get project name from CWD, walking up to find a directory that contains .claude/ or .git."""
    cwd = Path.cwd()
    # Walk up to find the project root (contains .claude/ or .git)
    for p in [cwd, *cwd.parents]:
        if (p / '.claude').is_dir() or (p / '.git').is_dir():
            return p.name
        if p == p.parent:
            break
    # Fallback to CWD name
    return cwd.name


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


# Tables with dedicated MCP tools — raw SQL writes should use these instead.
# Applies to ALL projects including claude-family.
# Warn (not block) because sometimes raw SQL is legitimately needed.
TOOL_GOVERNED_TABLES = {
    'features': {
        'tools': 'work_create(), work_status(), work_board()',
        'reason': 'Features have workflow state machines, audit logging, and side effects',
    },
    'build_tasks': {
        'tools': 'work_create(), work_status()',
        'reason': 'Build tasks have dependency checks, feature completion cascades, and audit logging',
    },
    'feedback': {
        'tools': 'work_create(), work_status()',
        'reason': 'Feedback has multi-step state transitions and audit logging',
    },
    'knowledge': {
        'tools': 'remember(), memory_manage()',
        'reason': 'Knowledge entries need embedding generation, dedup checks, and relation linking',
    },
    'entities': {
        'tools': 'entity_store(), entity_read()',
        'reason': 'Entities need schema validation, embedding generation, and dedup by key properties',
    },
    'sessions': {
        'tools': 'start_session(), end_session(), session_manage()',
        'reason': 'Sessions need proper lifecycle management and state persistence',
    },
    'todos': {
        'tools': 'TaskCreate (native), store_session_fact() for notes',
        'reason': 'Todos sync with Claude Code task system via hooks',
    },
    'messages': {
        'tools': 'send_msg(), inbox()',
        'reason': 'Messages need recipient validation, threading, and pg_notify triggers',
    },
    'workfiles': {
        'tools': 'workfile_store(), workfile_read()',
        'reason': 'Workfiles need embedding generation and access tracking',
    },
    'knowledge_relations': {
        'tools': 'link()',
        'reason': 'Knowledge relations need bidirectional consistency and strength management',
    },
    'resource_links': {
        'tools': 'link()',
        'reason': 'Resource links have unique constraints and bidirectional queries',
    },
    'secret_registry': {
        'tools': 'secret()',
        'reason': 'Secrets need Windows Credential Manager sync and session fact caching',
    },
    'task_queue': {
        'tools': 'job_enqueue(), job_cancel(), job_status()',
        'reason': 'Task queue needs lease management, concurrency controls, and worker daemon coordination',
    },
    'job_templates': {
        'tools': 'job_template()',
        'reason': 'Job templates need parameter validation, kind registration, and version history tracking',
    },
    'job_template_versions': {
        'tools': 'job_template(action="publish_version")',
        'reason': 'Template versions need semantic versioning, immutability, and rollback coordination',
    },
    'job_template_origins': {
        'tools': 'job_template(action="add_origin")',
        'reason': 'Origins need one-way traceability and audit trail for template sourcing',
    },
    'job_run_history': {
        'tools': 'job_status(view="runs") for reads; worker_daemon writes need -- OVERRIDE: worker_daemon',
        'reason': 'Run history is read-mostly and append-only; worker daemon has exclusive write access',
    },
}


# FB341: read-side telemetry for bypass detection. ALL projects.
# Reads against these tables almost always have a better MCP tool — when a
# raw SELECT shows up, log it so we can measure how often the discovery
# surface fails. We DO NOT block (reads can be legitimately ad-hoc), but
# logging gives us the FB341 signal to drive tool design.
READ_NUDGE_TABLES = {
    'features': "Try work_board(view='board') / get_ready_tasks() / get_work_context() before raw SELECT.",
    'build_tasks': "Try work_board(view='board') / get_ready_tasks() before raw SELECT.",
    'feedback': "Try work_board(view='board') for open items; work_status() for state changes.",
    'knowledge': "Try recall_memories(query=...) — it covers all 4 atomic stores via kg_nodes_view.",
    'entities': "Try entity_read(query=..., entity_type=...) before raw SELECT.",
    'workfiles': "Try workfile_read(component=...) / search_workfiles(query=...).",
    'project_workfiles': "Try workfile_read(component=...) / search_workfiles(query=...).",
    'session_facts': "Try session_facts(fact_key=...) / recall_session_fact(key=...).",
}

# Identify SELECT statements (read-only).
SELECT_RE = re.compile(r'^\s*(WITH\s+.*?\s+)?SELECT\b', re.IGNORECASE | re.DOTALL)


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
try:
    from config import DATABASE_URI as _db_uri
    DB_URI = _db_uri or ""
except Exception:
    DB_URI = os.environ.get("DATABASE_URI", "")


def log_governance_event(action: str, project: str, tables: set, reason: str = "", sql_snippet: str = ""):
    """Log governance block or override to claude.enforcement_log for gap analysis."""
    try:
        if not DB_URI:
            return
        try:
            import psycopg2
            conn = psycopg2.connect(DB_URI, connect_timeout=2)
        except ImportError:
            import psycopg
            conn = psycopg.connect(DB_URI, connect_timeout=2)
        message = json.dumps({
            "event": "sql_governance",
            "project": project,
            "tables": sorted(tables),
            "override_reason": reason,
            "sql_preview": sql_snippet[:200],
        })
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO claude.enforcement_log "
                    "(reminder_type, reminder_message, action_taken) "
                    "VALUES (%s, %s, %s)",
                    (f"sql_governance_{action}", message, action)
                )
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log governance event: {e}")


def allow():
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow"
        }
    }))
    sys.exit(0)


def deny_with_guidance(reason: str):
    """Deny with helpful message pointing to the correct tool."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason
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

        table_refs = extract_table_refs(sql)
        is_write = is_write_operation(sql)

        # Infrastructure projects skip protection checks (1 & 2) but still get governance warnings (3)
        is_infra = project in INFRA_PROJECTS

        # Check 1: Block writes to protected tables (non-infra only)
        if is_write and not is_infra:
            protected_hits = table_refs & PROTECTED_TABLES
            if protected_hits:
                tables_str = ', '.join(f'claude.{t}' for t in protected_hits)
                logger.warning(
                    f"BLOCKED: Project '{project}' attempted write to protected tables: {tables_str}"
                )
                deny(
                    f"BLOCKED: Project '{project}' cannot modify infrastructure tables ({tables_str}). "
                    f"Config changes must go through claude-family:\n"
                    f"  send_msg(message_type='task_request', to_project='claude-family', "
                    f"body='Requesting config change: ...')\n"
                    f"Only claude-family can modify config_templates, workspaces, and other infrastructure tables."
                )

        # Check 2: Block reads on sensitive tables (non-infra only)
        if not is_infra:
            sensitive_hits = table_refs & SENSITIVE_TABLES
        else:
            sensitive_hits = set()
        if sensitive_hits:
            tables_str = ', '.join(f'claude.{t}' for t in sensitive_hits)
            logger.warning(
                f"BLOCKED: Project '{project}' attempted read on sensitive table: {tables_str}"
            )
            deny(
                f"BLOCKED: Project '{project}' cannot query sensitive tables ({tables_str}). "
                f"These tables contain credentials and infrastructure config.\n"
                f"To request config changes, send a message to claude-family:\n"
                f"  send_msg(message_type='task_request', to_project='claude-family', "
                f"body='Need config change: ...')"
            )

        # Check 3: Block writes to tool-governed tables (ALL projects including infra)
        # Override: include "-- OVERRIDE: reason" as a SQL comment to bypass
        if is_write:
            governed_hits = table_refs & set(TOOL_GOVERNED_TABLES.keys())
            if governed_hits:
                # Check for override comment
                override_match = re.search(r'--\s*OVERRIDE:\s*(.+)', sql, re.IGNORECASE)
                if override_match:
                    override_reason = override_match.group(1).strip()
                    logger.info(
                        f"SQL governance OVERRIDE: project '{project}' raw write on "
                        f"{', '.join(f'claude.{t}' for t in governed_hits)} "
                        f"reason: {override_reason}"
                    )
                    log_governance_event("override", project, governed_hits, override_reason, sql)
                    allow()

                # No override - deny with guidance
                guidance_lines = []
                for table in sorted(governed_hits):
                    info = TOOL_GOVERNED_TABLES[table]
                    guidance_lines.append(
                        f"  claude.{table}:\n"
                        f"    Use: {info['tools']}\n"
                        f"    Why: {info['reason']}"
                    )
                deny_text = (
                    f"BLOCKED: Raw SQL write on tool-governed table(s).\n\n"
                    f"Use the dedicated MCP tools instead:\n"
                    + "\n".join(guidance_lines)
                    + "\n\n"
                    "Raw SQL bypasses workflow validation, audit logging, embedding generation, "
                    "and side effects (dependency checks, cascades, dedup).\n\n"
                    "If you MUST use raw SQL (migration, bulk fix, data repair), add a comment:\n"
                    "  -- OVERRIDE: reason for raw SQL\n"
                    "Example: UPDATE claude.features SET status = 'cancelled' "
                    "WHERE ... -- OVERRIDE: bulk cleanup of abandoned features"
                )
                logger.warning(
                    f"SQL governance BLOCKED: project '{project}' raw write on governed tables: "
                    f"{', '.join(f'claude.{t}' for t in governed_hits)}"
                )
                log_governance_event("blocked", project, governed_hits, "", sql)
                deny_with_guidance(deny_text)

        # FB341: read-side bypass telemetry. SELECT-only against tables with a
        # better MCP tool — log to enforcement_log so we can measure failure
        # of the discovery surface. Never blocks, never denies.
        if not is_write and SELECT_RE.match(sql):
            nudge_hits = table_refs & set(READ_NUDGE_TABLES.keys())
            if nudge_hits:
                hint_parts = []
                for t in sorted(nudge_hits):
                    hint_parts.append(f"claude.{t}: {READ_NUDGE_TABLES[t]}")
                hint = " | ".join(hint_parts)
                # Override comment also suppresses the nudge log (deliberate raw SQL).
                if not re.search(r'--\s*OVERRIDE:', sql, re.IGNORECASE):
                    log_governance_event("read_nudge", project, nudge_hits, hint, sql)
                    logger.info(
                        f"SQL governance read_nudge: project '{project}' SELECT on "
                        f"{', '.join(f'claude.{t}' for t in nudge_hits)} — {hint}"
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
