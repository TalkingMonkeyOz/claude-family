#!/usr/bin/env python3
"""
Stop Hook Enforcer - Counter-based automatic reminders

Runs after every Claude response. Tracks interaction count and triggers
reminders at specified intervals.

State persisted to: ~/.claude/state/enforcement_state.json
"""

import sys
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
STATE_FILE = Path.home() / ".claude" / "state" / "enforcement_state.json"
INTERVALS = {
    "git_check": 5,          # Every 5 responses
    "inbox_check": 10,       # Every 10 responses
    "claude_md_refresh": 20, # Every 20 responses
}

def load_state() -> dict:
    """Load state from file or return defaults."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass

    return {
        "interaction_count": 0,
        "last_git_check": 0,
        "last_inbox_check": 0,
        "last_claude_md_check": 0,
        "code_changes_since_test": 0,
        "files_changed_this_session": [],
        "session_start": datetime.now().isoformat()
    }

def save_state(state: dict):
    """Persist state to file."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))

def check_git_status() -> tuple:
    """Check if there are uncommitted changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split('\n')
            return True, f"{len(lines)} uncommitted changes"
        return False, ""
    except Exception:
        return False, ""

def get_reminders(state: dict) -> list:
    """Generate reminders based on current state."""
    reminders = []
    count = state["interaction_count"]

    # Git check reminder
    if count - state["last_git_check"] >= INTERVALS["git_check"]:
        has_changes, msg = check_git_status()
        if has_changes:
            reminders.append(f"Git: {msg}. Consider committing.")
        state["last_git_check"] = count

    # Inbox check reminder
    if count - state["last_inbox_check"] >= INTERVALS["inbox_check"]:
        reminders.append("Run /inbox-check for messages from other Claude instances.")
        state["last_inbox_check"] = count

    # CLAUDE.md refresh reminder
    if count - state["last_claude_md_check"] >= INTERVALS["claude_md_refresh"]:
        reminders.append("Consider re-reading CLAUDE.md to refresh context.")
        state["last_claude_md_check"] = count

    # Test tracking reminder
    if state.get("code_changes_since_test", 0) >= 3:
        reminders.append(f"{state['code_changes_since_test']} code changes without tests.")

    return reminders

def main():
    """Main entry point."""
    # Load state
    state = load_state()

    # Increment counter
    state["interaction_count"] += 1

    # Get reminders
    reminders = get_reminders(state)

    # Save state
    save_state(state)

    # Output reminders if any
    if reminders:
        output = {
            "systemPrompt": "\n".join([
                "<stop-hook-reminder>",
                "PERIODIC REMINDERS:",
                *reminders,
                "</stop-hook-reminder>"
            ])
        }
        print(json.dumps(output))
    else:
        print(json.dumps({}))

    return 0

if __name__ == "__main__":
    sys.exit(main())
