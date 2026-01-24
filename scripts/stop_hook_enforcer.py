#!/usr/bin/env python3
"""
Stop Hook Enforcer - Self-Enforcing Periodic Checks

This script runs as a Claude Code Stop hook (after each response).
It maintains counters to trigger periodic reminders without user action.

Enforcement Schedule:
- Every 5 interactions: Git status check reminder
- Every 10 interactions: Inbox check reminder
- Every 20 interactions: CLAUDE.md refresh reminder
- On code changes: Track if tests were touched

The user's insight: "I'LL FORGET TO USE IT SO WILL YOU" - so we automate it.

Usage:
    Called by Claude Code hooks system after each response
    Returns JSON with systemMessage for reminders

Author: claude-code-unified
Date: 2025-12-16
"""

import sys
import os
import io
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

# Try to import database connection
try:
    import psycopg2
    HAS_DB = True
except ImportError:
    HAS_DB = False

# Database connection settings - secure config loading
DB_CONFIG = None
if os.environ.get("CLAUDE_DB_PASSWORD"):
    # Use environment variables if available
    DB_CONFIG = {
        "host": os.environ.get("CLAUDE_DB_HOST", "localhost"),
        "database": os.environ.get("CLAUDE_DB_NAME", "ai_company_foundation"),
        "user": os.environ.get("CLAUDE_DB_USER", "postgres"),
        "password": os.environ.get("CLAUDE_DB_PASSWORD"),
    }
else:
    # Try to load from secure config file
    try:
        sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
        from config import POSTGRES_CONFIG
        DB_CONFIG = POSTGRES_CONFIG
    except ImportError:
        DB_CONFIG = None  # No fallback - will gracefully fail

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# State file location
STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "enforcement_state.json"

# Enforcement intervals
INTERVALS = {
    "git_check": 5,          # Every 5 interactions
    "inbox_check": 10,       # Every 10 interactions
    "claude_md_refresh": 5,  # Every 5 interactions - check vault for answers
    "work_tracking": 15,     # Every 15 interactions - check work item tracking
}

# Code file extensions that trigger test tracking
CODE_EXTENSIONS = {
    '.py', '.ts', '.tsx', '.js', '.jsx', '.cs', '.rs', '.go',
    '.java', '.kt', '.swift', '.rb', '.php', '.vue', '.svelte'
}

# Test file patterns
TEST_PATTERNS = ['test', 'spec', '__tests__', '.test.', '.spec.']


def load_state() -> Dict[str, Any]:
    """Load enforcement state from file."""
    default_state = {
        "interaction_count": 0,
        "last_git_check": 0,
        "last_inbox_check": 0,
        "last_claude_md_check": 0,
        "last_work_tracking_check": 0,
        "code_changes_since_test": 0,
        "files_changed_this_session": [],
        "session_start": datetime.now(timezone.utc).isoformat(),
        "last_interaction": None
    }

    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                # Merge with defaults in case of missing keys
                return {**default_state, **state}
    except (json.JSONDecodeError, IOError):
        pass

    return default_state


def save_state(state: Dict[str, Any]):
    """Save enforcement state to file."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state["last_interaction"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        print(f"Warning: Could not save state: {e}", file=sys.stderr)


def get_db_connection():
    """Get database connection for logging."""
    if not HAS_DB:
        return None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception:
        return None


def log_enforcement(reminder_type: str, reminder_message: str,
                    session_id: str = None, interaction_count: int = 0):
    """
    Log enforcement reminder to database for observability.

    Writes to claude.enforcement_log table.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.enforcement_log
            (session_id, interaction_count, reminder_type,
             reminder_message, action_taken)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session_id,
            interaction_count,
            reminder_type,
            reminder_message[:500] if reminder_message else '',
            'reminded'
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        # Best effort logging - don't break the main flow
        print(f"Enforcement logging error: {e}", file=sys.stderr)
        if conn:
            try:
                conn.close()
            except:
                pass


def is_code_file(filepath: str) -> bool:
    """Check if a file is a code file."""
    if not filepath:
        return False
    ext = Path(filepath).suffix.lower()
    return ext in CODE_EXTENSIONS


def is_test_file(filepath: str) -> bool:
    """Check if a file is a test file."""
    if not filepath:
        return False
    filepath_lower = filepath.lower()
    return any(pattern in filepath_lower for pattern in TEST_PATTERNS)


def analyze_tool_output(hook_input: Dict) -> Dict[str, Any]:
    """Analyze what the response did (files changed, tools used)."""
    result = {
        "code_files_changed": [],
        "test_files_changed": [],
        "tools_used": []
    }

    # Get tool results from hook input
    tool_results = hook_input.get('toolResults', [])

    for tool_result in tool_results:
        tool_name = tool_result.get('toolName', '')
        result["tools_used"].append(tool_name)

        # Check for file operations
        if tool_name in ('Write', 'Edit'):
            file_path = tool_result.get('params', {}).get('file_path', '')
            if file_path:
                if is_test_file(file_path):
                    result["test_files_changed"].append(file_path)
                elif is_code_file(file_path):
                    result["code_files_changed"].append(file_path)

    return result


def build_reminders(state: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
    """Build list of reminder messages based on state and analysis."""
    reminders = []
    count = state["interaction_count"]

    # Git status check (every 5 interactions)
    if count - state["last_git_check"] >= INTERVALS["git_check"]:
        reminders.append(
            "GIT CHECK: Consider running `git status` to review changes. "
            "Commit frequently to preserve your work."
        )
        state["last_git_check"] = count

    # Inbox check (every 10 interactions)
    if count - state["last_inbox_check"] >= INTERVALS["inbox_check"]:
        reminders.append(
            "INBOX CHECK: Run `/inbox-check` to see if other Claude instances "
            "have sent you messages."
        )
        state["last_inbox_check"] = count

    # CLAUDE.md refresh (every 5 interactions)
    if count - state["last_claude_md_check"] >= INTERVALS["claude_md_refresh"]:
        reminders.append(
            "VAULT CHECK: Re-read CLAUDE.md and check knowledge-vault/ for answers. "
            "Almost any question (configuration, procedures, patterns) likely has an answer in the vault. "
            "Context can drift - refresh your understanding."
        )
        state["last_claude_md_check"] = count

    # Work tracking reminder (every 15 interactions)
    if count - state.get("last_work_tracking_check", 0) >= INTERVALS["work_tracking"]:
        reminders.append(
            "WORK TRACKING: Are you tracking this work? "
            "Significant work should be logged as features (claude.features) or build_tasks. "
            "Link commits using branch naming: feature/F1-desc, fix/FB1-desc. "
            "See [[Work Tracking Schema]] in vault."
        )
        state["last_work_tracking_check"] = count

    # Test tracking - warn if code changed without tests
    if analysis["code_files_changed"] and not analysis["test_files_changed"]:
        state["code_changes_since_test"] += len(analysis["code_files_changed"])
        state["files_changed_this_session"].extend(analysis["code_files_changed"])
    elif analysis["test_files_changed"]:
        state["code_changes_since_test"] = 0  # Reset counter

    # Warn after 3+ code files changed without tests
    if state["code_changes_since_test"] >= 3:
        changed_files = state.get("files_changed_this_session", [])[-5:]
        files_preview = ", ".join(Path(f).name for f in changed_files)
        reminders.append(
            f"TEST REMINDER: {state['code_changes_since_test']} code files changed "
            f"without test updates. Recent: {files_preview}. "
            "Consider writing tests before committing (SOP-006)."
        )

    return reminders


def main():
    """Main entry point for the hook."""
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Load current state
    state = load_state()

    # Increment interaction counter
    state["interaction_count"] += 1

    # Analyze what happened in this response
    analysis = analyze_tool_output(hook_input)

    # Build reminders based on counters and analysis
    reminders = build_reminders(state, analysis)

    # Save updated state
    save_state(state)

    # If no reminders, return empty response
    if not reminders:
        print(json.dumps({}))
        return 0

    # Format reminders as system message
    reminder_text = "\n".join(f"- {r}" for r in reminders)

    # Log each reminder to database
    session_id = hook_input.get('session_id')
    for reminder in reminders:
        # Determine reminder type from content
        if "GIT CHECK" in reminder:
            reminder_type = "git_check"
        elif "INBOX CHECK" in reminder:
            reminder_type = "inbox_check"
        elif "VAULT CHECK" in reminder:
            reminder_type = "claude_md_refresh"
        elif "WORK TRACKING" in reminder:
            reminder_type = "work_tracking"
        elif "TEST REMINDER" in reminder:
            reminder_type = "test_reminder"
        else:
            reminder_type = "other"

        log_enforcement(
            reminder_type=reminder_type,
            reminder_message=reminder,
            session_id=session_id,
            interaction_count=state["interaction_count"]
        )

    response = {
        "systemMessage": f"""<enforcement-reminders>
PERIODIC ENFORCEMENT CHECK (Interaction #{state['interaction_count']}):
{reminder_text}
</enforcement-reminders>"""
    }

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
