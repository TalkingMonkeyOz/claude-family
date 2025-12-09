#!/usr/bin/env python3
"""
Process Router - UserPromptSubmit Hook

This script runs when a user submits a prompt. It:
1. Checks the prompt against registered process trigger patterns (TIER 1: regex/keywords)
2. If no match, uses LLM classification fallback (TIER 2: Haiku)
3. If a process matches, injects guidance into the response
4. Detects task type and injects relevant standards
5. For high-enforcement processes, may require user confirmation to bypass

Architecture:
    TIER 1: Fast regex/keywords (0-1ms, $0)
    TIER 2: LLM Classification (200-500ms, ~$0.0002 per call)

Usage:
    Called by Claude Code hooks system with user prompt on stdin
    Returns JSON with systemPrompt or block message

Author: claude-code-unified
Date: 2025-12-07
Updated: 2025-12-07 - Added standards injection by task type
Updated: 2025-12-08 - Added LLM classification fallback (TIER 2)
Updated: 2025-12-08 - Added auto-TodoWrite injection for workflow steps
"""

import sys
import os
import io
import json
import re
import time
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

# LLM Classifier imports (optional - graceful fallback if not available)
try:
    from process_router_config import LLM_CONFIG, ANTHROPIC_API_KEY, FEATURES
    from llm_classifier import ProcessClassifier, get_classifier
    HAS_LLM = FEATURES.get("llm_fallback", False) and bool(ANTHROPIC_API_KEY)
except ImportError:
    HAS_LLM = False
    LLM_CONFIG = {}
    ANTHROPIC_API_KEY = ""
    FEATURES = {"llm_fallback": False}


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
    },
    "testing": {
        "file": None,  # No file - inline guidance
        "keywords": [
            "implement", "fix", "bug", "feature", "refactor", "add",
            "create", "build", "write", "code", "function", "component",
            "change", "modify", "update"
        ],
        "description": "Testing Requirements (SOP-006)"
    }
}


# Code change indicators that should trigger testing reminders
CODE_CHANGE_KEYWORDS = [
    "implement", "fix", "bug", "feature", "refactor", "add", "create",
    "build", "write", "modify", "update", "change", "delete", "remove",
    "function", "class", "component", "endpoint", "api", "page"
]


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

    # Special handling for testing - inline guidance, no file
    if standard_key == "testing":
        return """**Testing Requirements (SOP-006)**

BEFORE COMMITTING code changes:
- [ ] PreCommit hook will run Level 1 tests automatically
- [ ] Run `pnpm build` / `dotnet build` to check types
- [ ] Run `pnpm lint` / `ruff check` for code style

BEFORE PUSHING significant changes:
- [ ] Run unit tests: `pnpm test` / `pytest`
- [ ] Run API smoke test if endpoints changed

FOR MAJOR FEATURES consider spawning:
- `test-coordinator-sonnet` - orchestrates full test suite
- `nextjs-tester-haiku` - E2E testing for Next.js
- `debugger-haiku` - analyze any test failures

Full process: docs/sops/SOP-006-TESTING-PROCESS.md"""

    # Normal file-based standards
    if not config.get("file"):
        return f"**{config['description']}**"

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


def is_code_change_task(user_prompt: str) -> bool:
    """Check if the prompt indicates code changes that need testing."""
    prompt_lower = user_prompt.lower()
    return any(kw in prompt_lower for kw in CODE_CHANGE_KEYWORDS)


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


def classify_with_llm_fallback(conn, user_prompt: str) -> List[Dict[str, Any]]:
    """
    Use LLM to classify user intent when regex/keywords fail.

    This is TIER 2 classification - only called when TIER 1 (regex/keywords)
    returns no matches.

    Args:
        conn: Database connection
        user_prompt: The user's input text

    Returns:
        List of matched process dicts (same format as get_matching_processes)
    """
    if not HAS_LLM:
        return []

    classifier = get_classifier(ANTHROPIC_API_KEY, LLM_CONFIG)
    if not classifier:
        return []

    # Get all active processes for classification
    cur = conn.cursor()
    cur.execute("""
        SELECT
            pr.process_id,
            pr.process_name,
            pr.description,
            pr.category,
            pr.enforcement,
            pr.sop_ref,
            pr.command_ref,
            COALESCE(
                json_agg(pt.pattern) FILTER (WHERE pt.trigger_type = 'keywords'),
                '[]'
            ) as keywords
        FROM claude.process_registry pr
        LEFT JOIN claude.process_triggers pt ON pr.process_id = pt.process_id
        WHERE pr.is_active = true
        GROUP BY pr.process_id, pr.process_name, pr.description, pr.category,
                 pr.enforcement, pr.sop_ref, pr.command_ref
        ORDER BY pr.process_id
    """)

    processes = []
    for row in cur.fetchall():
        # Extract keywords from JSON arrays
        keywords = []
        if row['keywords']:
            for kw_json in row['keywords']:
                try:
                    keywords.extend(json.loads(kw_json))
                except (json.JSONDecodeError, TypeError):
                    pass

        processes.append({
            "process_id": row['process_id'],
            "name": row['process_name'],
            "description": row['description'],
            "category": row['category'],
            "keywords": keywords
        })

    # Classify with LLM
    llm_matches = classifier.classify(user_prompt, processes)

    if not llm_matches:
        return []

    # Convert LLM matches back to full process dicts
    matched_process_ids = [m['process_id'] for m in llm_matches]

    # Fetch full process details
    placeholders = ','.join(['%s'] * len(matched_process_ids))
    cur.execute(f"""
        SELECT DISTINCT
            pr.process_id,
            pr.process_name,
            pr.category,
            pr.description,
            pr.enforcement,
            pr.sop_ref,
            pr.command_ref
        FROM claude.process_registry pr
        WHERE pr.process_id IN ({placeholders})
    """, matched_process_ids)

    matches = [dict(row) for row in cur.fetchall()]

    # Add LLM metadata to matches
    for match in matches:
        llm_match = next((m for m in llm_matches if m['process_id'] == match['process_id']), None)
        if llm_match:
            match['llm_confidence'] = llm_match.get('confidence', 0)
            match['llm_reasoning'] = llm_match.get('reasoning', '')
            match['classification_method'] = 'llm'

    return matches


def log_classification(conn, user_prompt: str, method: str, matches: List[Dict],
                       latency_ms: int = 0, cost_usd: float = 0):
    """Log classification result for analytics."""
    if not FEATURES.get("classification_logging", True):
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.process_classification_log
            (user_prompt, classification_method, matched_process_ids,
             llm_confidence, llm_reasoning, latency_ms, cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_prompt[:500],  # Truncate for storage
            method,
            [m.get('process_id') for m in matches] if matches else [],
            matches[0].get('llm_confidence') if matches and 'llm_confidence' in matches[0] else None,
            matches[0].get('llm_reasoning', '')[:500] if matches and 'llm_reasoning' in matches[0] else None,
            latency_ms,
            cost_usd
        ))
        conn.commit()
    except Exception as e:
        # Best effort logging - don't fail the main flow
        pass


def get_matching_processes(conn, user_prompt: str) -> List[Dict[str, Any]]:
    """
    Find all processes that match the user prompt.

    Uses a two-tier approach:
    - TIER 1: Fast regex/keyword matching (0-1ms, $0)
    - TIER 2: LLM classification fallback (200-500ms, ~$0.0002) when TIER 1 fails

    Args:
        conn: Database connection
        user_prompt: The user's input text

    Returns:
        List of matched process dicts with process details
    """
    if not conn:
        return []

    start_time = time.time()
    cur = conn.cursor()

    # TIER 1: Get all active triggers ordered by priority
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
    classification_method = 'none'

    # TIER 1: Try regex/keyword matching
    for trigger in triggers:
        matched = False

        if trigger['trigger_type'] == 'regex':
            try:
                if re.search(trigger['pattern'], user_prompt, re.IGNORECASE):
                    matched = True
                    classification_method = 'regex'
            except re.error:
                pass  # Invalid regex, skip

        elif trigger['trigger_type'] == 'keywords':
            try:
                keywords = json.loads(trigger['pattern'])
                prompt_lower = user_prompt.lower()
                if any(kw.lower() in prompt_lower for kw in keywords):
                    matched = True
                    classification_method = 'keywords'
            except json.JSONDecodeError:
                pass

        # Events are handled separately (not from user prompt text)
        # Tool calls are handled by PreToolUse hooks

        if matched:
            # Avoid duplicates (same process from different triggers)
            if not any(m['process_id'] == trigger['process_id'] for m in matches):
                match_dict = dict(trigger)
                match_dict['classification_method'] = classification_method
                matches.append(match_dict)

    # TIER 2: If no matches and LLM enabled, try LLM classification
    if not matches and HAS_LLM:
        try:
            llm_matches = classify_with_llm_fallback(conn, user_prompt)
            if llm_matches:
                matches = llm_matches
                classification_method = 'llm'
        except Exception as e:
            # Don't let LLM failures break the system
            print(f"LLM fallback error: {e}", file=sys.stderr)

    # Log classification for analytics
    latency_ms = int((time.time() - start_time) * 1000)
    if matches:
        log_classification(conn, user_prompt, classification_method, matches, latency_ms)

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


def build_process_guidance(matches: List[Dict], conn) -> Dict[str, Any]:
    """Build guidance message and todos for matched processes.

    Returns:
        Dict with 'guidance_text' and 'suggested_todos' keys
    """
    if not matches:
        return {"guidance_text": "", "suggested_todos": []}

    guidance_parts = []
    all_todos = []

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

                # Build todo item for this step
                # Convert step name to active form (e.g., "Create Entry" -> "Creating Entry")
                step_name = step['step_name']
                active_form = step_name
                if step_name.startswith("Create"):
                    active_form = "Creating" + step_name[6:]
                elif step_name.startswith("Add"):
                    active_form = "Adding" + step_name[3:]
                elif step_name.startswith("Update"):
                    active_form = "Updating" + step_name[6:]
                elif step_name.startswith("Check"):
                    active_form = "Checking" + step_name[5:]
                elif step_name.startswith("Run"):
                    active_form = "Running" + step_name[3:]
                elif step_name.startswith("Verify"):
                    active_form = "Verifying" + step_name[6:]
                elif step_name.startswith("Review"):
                    active_form = "Reviewing" + step_name[6:]
                elif step_name.startswith("Implement"):
                    active_form = "Implementing" + step_name[9:]
                elif step_name.startswith("Investigate"):
                    active_form = "Investigating" + step_name[11:]
                elif step_name.startswith("Mark"):
                    active_form = "Marking" + step_name[4:]
                elif step_name.startswith("Consider"):
                    active_form = "Considering" + step_name[8:]
                else:
                    # Default: add "ing" if ends with consonant, or just use as-is
                    active_form = step_name + "..."

                all_todos.append({
                    "content": f"[{process_id}] {step['step_number']}. {step_name}",
                    "status": "pending",
                    "activeForm": active_form
                })

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

    return {
        "guidance_text": "\n\n---\n\n".join(guidance_parts),
        "suggested_todos": all_todos
    }


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
    process_guidance_result = {"guidance_text": "", "suggested_todos": []}
    if matches:
        process_guidance_result = build_process_guidance(matches, conn)
        # Log the trigger (first match only for now)
        trigger_info = f"Pattern matched: {matches[0].get('pattern', 'N/A')[:50]}"
        log_process_trigger(conn, matches[0]['process_id'], trigger_info)

    if conn:
        conn.close()

    # If no process matched AND no standards detected, allow normal flow
    if not matches and not detected_standards:
        print(json.dumps({}))
        return 0

    # Build combined guidance
    guidance_parts = []
    suggested_todos = process_guidance_result.get("suggested_todos", [])

    if process_guidance_result["guidance_text"]:
        # Include suggested todos in the guidance
        todos_instruction = ""
        if suggested_todos:
            todos_json = json.dumps(suggested_todos, indent=2)
            todos_instruction = f"""

SUGGESTED TODOS (use TodoWrite to add these):
```json
{todos_json}
```

INSTRUCTION: Use TodoWrite tool immediately to add the above todos, then work through each step in order."""

        guidance_parts.append(f"""<process-guidance>
{process_guidance_result["guidance_text"]}
{todos_instruction}

IMPORTANT: The above process(es) were detected for this user request.
You MUST:
1. Use TodoWrite to add the workflow steps as todos
2. Follow each step in order, marking todos as you complete them
3. If you need to deviate, explain WHY and ask user for approval
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
