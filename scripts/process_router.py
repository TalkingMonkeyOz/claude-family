#!/usr/bin/env python3
"""
Process Router - UserPromptSubmit Hook

This script runs when a user submits a prompt. It:
1. Checks the prompt against registered process trigger patterns
2. If a process matches, injects guidance into the response
3. Detects task type and injects relevant standards
4. For high-enforcement processes, may require user confirmation to bypass

Usage:
    Called by Claude Code hooks system with user prompt on stdin
    Returns JSON with systemPrompt or block message

Author: claude-code-unified
Date: 2025-12-07
Updated: 2025-12-07 - Added standards injection by task type
"""

import sys
import os
import io
import json
import re
from typing import Optional, Dict, List, Any, Set

# Fix Windows encoding - only if not already wrapped
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add ai-workspace to path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')

try:
    from config import POSTGRES_CONFIG
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_DB = True
except ImportError:
    HAS_DB = False


# Standards configuration
STANDARDS_BASE_PATH = r"C:\Projects\claude-family\docs\standards"

STANDARDS_CONFIG = {
    "ui": {
        "file": "UI_COMPONENT_STANDARDS.md",
        "keywords": [
            "ui", "component", "page", "form", "table", "button", "modal",
            "dialog", "input", "dropdown", "sidebar", "navigation", "menu",
            "card", "list", "grid", "layout", "responsive", "mobile",
            "pagination", "filter", "sort", "empty state", "loading",
            "skeleton", "toast", "notification", "accessibility", "a11y"
        ],
        "description": "UI Component Standards - Tables, Forms, States, Accessibility"
    },
    "api": {
        "file": "API_STANDARDS.md",
        "keywords": [
            "api", "endpoint", "route", "rest", "http", "request", "response",
            "json", "get", "post", "put", "patch", "delete", "authentication",
            "authorization", "bearer", "token", "jwt", "cors", "rate limit",
            "pagination", "status code", "error handling"
        ],
        "description": "API Standards - REST patterns, Error handling, Authentication"
    },
    "database": {
        "file": "DATABASE_STANDARDS.md",
        "keywords": [
            "database", "db", "sql", "query", "schema", "table", "column",
            "migration", "index", "constraint", "foreign key", "primary key",
            "postgres", "postgresql", "select", "insert", "update", "delete",
            "join", "transaction", "performance", "n+1"
        ],
        "description": "Database Standards - Schema design, Queries, Migrations"
    },
    "development": {
        "file": "DEVELOPMENT_STANDARDS.md",
        "keywords": [
            "code", "implement", "refactor", "fix", "bug", "feature",
            "function", "class", "module", "naming", "convention", "style",
            "typescript", "python", "javascript", "react", "import", "export",
            "error handling", "logging", "test"
        ],
        "description": "Development Standards - Naming, Structure, Error handling"
    },
    "workflow": {
        "file": "WORKFLOW_STANDARDS.md",
        "keywords": [
            "workflow", "process", "deploy", "deployment", "review",
            "commit", "branch", "merge", "pr", "pull request", "git",
            "session", "documentation", "docs"
        ],
        "description": "Workflow Standards - Development lifecycle, Reviews, Deployment"
    }
}


def detect_task_standards(user_prompt: str) -> Set[str]:
    """Detect which standards are relevant to the user's prompt."""
    prompt_lower = user_prompt.lower()
    detected = set()

    for standard_key, config in STANDARDS_CONFIG.items():
        for keyword in config["keywords"]:
            if keyword in prompt_lower:
                detected.add(standard_key)
                break  # One keyword match is enough

    return detected


def load_standard_summary(standard_key: str) -> Optional[str]:
    """Load a condensed version of the standard (just key sections)."""
    config = STANDARDS_CONFIG.get(standard_key)
    if not config:
        return None

    file_path = os.path.join(STANDARDS_BASE_PATH, config["file"])

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract just the Quick Reference Checklist section for brevity
        checklist_match = re.search(
            r'## Quick Reference Checklist\s*\n(.*?)(?=\n## |\n---|\Z)',
            content,
            re.DOTALL
        )

        if checklist_match:
            checklist = checklist_match.group(1).strip()
            return f"**{config['description']}**\n\nQuick Checklist:\n{checklist}"

        # Fallback: return description and file reference
        return f"**{config['description']}**\nFull standard: {config['file']}"

    except (IOError, OSError):
        return f"**{config['description']}**\nFile: {config['file']}"


def build_standards_guidance(detected_standards: Set[str]) -> str:
    """Build guidance text for detected standards."""
    if not detected_standards:
        return ""

    parts = []
    parts.append("[RELEVANT STANDARDS DETECTED]")
    parts.append("Based on your task, the following standards apply:\n")

    for standard_key in sorted(detected_standards):
        summary = load_standard_summary(standard_key)
        if summary:
            parts.append(f"### {standard_key.upper()}\n{summary}\n")

    parts.append("---")
    parts.append("**Important**: Follow the checklist items above. For full details, reference the standard files in docs/standards/")

    return "\n".join(parts)


def get_db_connection():
    """Get database connection."""
    if not HAS_DB:
        return None
    try:
        return psycopg2.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)
    except Exception:
        return None


def get_matching_processes(conn, user_prompt: str) -> List[Dict[str, Any]]:
    """Find all processes that match the user prompt."""
    if not conn:
        return []

    cur = conn.cursor()

    # Get all active triggers ordered by priority
    cur.execute("""
        SELECT
            pt.trigger_id,
            pt.process_id,
            pt.trigger_type,
            pt.pattern,
            pt.priority,
            pr.process_name,
            pr.category,
            pr.description,
            pr.enforcement,
            pr.sop_ref,
            pr.command_ref
        FROM claude.process_triggers pt
        JOIN claude.process_registry pr ON pt.process_id = pr.process_id
        WHERE pt.is_active = true AND pr.is_active = true
        ORDER BY pt.priority ASC
    """)

    triggers = cur.fetchall()
    matches = []

    for trigger in triggers:
        matched = False

        if trigger['trigger_type'] == 'regex':
            try:
                if re.search(trigger['pattern'], user_prompt, re.IGNORECASE):
                    matched = True
            except re.error:
                pass  # Invalid regex, skip

        elif trigger['trigger_type'] == 'keywords':
            try:
                keywords = json.loads(trigger['pattern'])
                prompt_lower = user_prompt.lower()
                if any(kw.lower() in prompt_lower for kw in keywords):
                    matched = True
            except json.JSONDecodeError:
                pass

        # Events are handled separately (not from user prompt text)
        # Tool calls are handled by PreToolUse hooks

        if matched:
            # Avoid duplicates (same process from different triggers)
            if not any(m['process_id'] == trigger['process_id'] for m in matches):
                matches.append(dict(trigger))

    return matches


def get_process_steps(conn, process_id: str) -> List[Dict[str, Any]]:
    """Get steps for a process."""
    if not conn:
        return []

    cur = conn.cursor()
    cur.execute("""
        SELECT step_number, step_name, step_description, is_blocking, is_user_approval
        FROM claude.process_steps
        WHERE process_id = %s
        ORDER BY step_number
    """, (process_id,))

    return [dict(row) for row in cur.fetchall()]


def build_process_guidance(matches: List[Dict], conn) -> str:
    """Build guidance message for matched processes."""
    if not matches:
        return ""

    guidance_parts = []

    for match in matches:
        process_name = match['process_name']
        process_id = match['process_id']
        enforcement = match['enforcement']
        command_ref = match.get('command_ref')
        sop_ref = match.get('sop_ref')
        description = match.get('description', '')

        # Build header based on enforcement level
        if enforcement == 'automated':
            header = f"[PROCESS DETECTED - AUTOMATED] {process_name}"
        elif enforcement == 'semi-automated':
            header = f"[PROCESS DETECTED - FOLLOW STEPS] {process_name}"
        else:
            header = f"[PROCESS AVAILABLE] {process_name}"

        guidance = [header, description]

        # Add steps if available
        steps = get_process_steps(conn, process_id)
        if steps:
            guidance.append("\nRequired Steps:")
            for step in steps:
                step_marker = "[BLOCKING] " if step['is_blocking'] else ""
                approval_marker = "[USER APPROVAL] " if step['is_user_approval'] else ""
                guidance.append(f"  {step['step_number']}. {step_marker}{approval_marker}{step['step_name']}")
                if step['step_description']:
                    guidance.append(f"      {step['step_description']}")

        # Add references
        refs = []
        if command_ref:
            refs.append(f"Command: {command_ref}")
        if sop_ref:
            refs.append(f"SOP: {sop_ref}")
        if refs:
            guidance.append("\nReferences: " + ", ".join(refs))

        # Add enforcement note
        if enforcement in ('automated', 'semi-automated'):
            guidance.append(f"\n** This process has {enforcement} enforcement. Follow the steps above. **")
            guidance.append("** To bypass, explain your reasoning and ask user for explicit approval. **")

        guidance_parts.append("\n".join(guidance))

    return "\n\n---\n\n".join(guidance_parts)


def log_process_trigger(conn, process_id: str, triggered_by: str, session_id: str = None):
    """Log that a process was triggered."""
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.process_runs (process_id, session_id, triggered_by, status)
            VALUES (%s, %s, %s, 'running')
            RETURNING run_id
        """, (process_id, session_id, triggered_by))
        conn.commit()
    except Exception:
        pass  # Logging is best-effort


def main():
    """Main entry point for the hook."""
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        # No input or invalid JSON
        print(json.dumps({}))
        return 0

    # Get user prompt
    user_prompt = hook_input.get('prompt', '')
    if not user_prompt:
        print(json.dumps({}))
        return 0

    # Connect to database
    conn = get_db_connection()

    # Find matching processes
    matches = get_matching_processes(conn, user_prompt)

    # Detect relevant standards based on task type
    detected_standards = detect_task_standards(user_prompt)
    standards_guidance = build_standards_guidance(detected_standards)

    # Build process guidance (if any processes matched)
    process_guidance = ""
    if matches:
        process_guidance = build_process_guidance(matches, conn)
        # Log the trigger (first match only for now)
        trigger_info = f"Pattern matched: {matches[0]['pattern'][:50]}"
        log_process_trigger(conn, matches[0]['process_id'], trigger_info)

    if conn:
        conn.close()

    # If no process matched AND no standards detected, allow normal flow
    if not matches and not detected_standards:
        print(json.dumps({}))
        return 0

    # Build combined guidance
    guidance_parts = []

    if process_guidance:
        guidance_parts.append(f"""<process-guidance>
{process_guidance}

IMPORTANT: The above process(es) were detected for this user request.
You MUST acknowledge the detected process and follow its steps.
If you need to deviate from the process, you MUST:
1. Explain WHY you're deviating
2. Ask the user for explicit approval to proceed differently
</process-guidance>""")

    if standards_guidance:
        guidance_parts.append(f"""<standards-guidance>
{standards_guidance}
</standards-guidance>""")

    response = {
        "systemPrompt": "\n\n".join(guidance_parts)
    }

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
