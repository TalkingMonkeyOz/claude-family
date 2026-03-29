#!/usr/bin/env python3
"""
rag_context.py — Periodic reminders, context health monitoring, keyword detection.

Extracted from rag_query_hook.py. This is a LEAF module — no cross-module deps
except config.py for DB access in _check_recent_checkpoint().
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from config import get_db_connection, detect_psycopg

psycopg_mod, _PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None

logger = logging.getLogger('rag_query.context')

# =============================================================================
# PERIODIC REMINDERS - Interval-based context injection
# =============================================================================
# Merged from stop_hook_enforcer.py - single injection point for all context.
# Reminders are injected at intervals to prevent context drift.

REMINDER_INTERVALS = {
    "inbox_check": 15,       # Every 15 interactions - check for messages
    "vault_refresh": 25,     # Every 25 interactions - refresh vault understanding
    "git_check": 10,         # Every 10 interactions - check uncommitted changes
    "tool_awareness": 8,     # Every 8 interactions - remind about MCP tools
    "budget_check": 12,      # Every 12 interactions - context budget awareness
    "storage_nudge": 25,     # Every 25 interactions - rotate storage system reminders
}

# Rotating storage nudges — cycle through these to reinforce filing habits
STORAGE_NUDGES = [
    "📁 **Filing Cabinet**: Working on a component? `stash()` your notes. `unstash()` to reload next session.",
    "🧠 **Memory**: Learned a pattern or gotcha? `remember()` it for future sessions (min 80 chars).",
    "📋 **Notepad**: Important finding or decision? `store_session_fact()` — survives compaction.",
    "📚 **Reference Library**: Found structured data (API, schema, entity)? `catalog()` it.",
    "📂 **Filing Check**: `list_workfiles()` before starting work — check if a dossier already exists.",
]

# State file for tracking interaction count
STATE_DIR = Path.home() / ".claude" / "state"
STATE_FILE = STATE_DIR / "rag_hook_state.json"

# =============================================================================
# CONTEXT HEALTH - Graduated urgency based on context window fullness
# =============================================================================
# Reads context_health.json written by StatusLine sensor script.
# Falls back to prompt count heuristic when StatusLine data is stale/missing.
# Returns (level, remaining_pct, message) for injection into context.

CONTEXT_HEALTH_FILE = STATE_DIR / "context_health.json"
CONTEXT_HEALTH_FRESHNESS_SECONDS = 3600  # 1 hour — trust last StatusLine reading unless truly ancient

# Prompt count fallback thresholds (LAST RESORT — only when StatusLine file doesn't exist at all)
# These are intentionally very conservative. The StatusLine sensor provides actual
# remaining_percentage from Claude Code, which knows the real context window size.
# The fallback is just prompt counting — it cannot know if we're on 200K or 1M.
FALLBACK_THRESHOLDS = {
    "red": 800,    # Only trigger at extreme prompt counts
    "orange": 600, # These are deliberately high to avoid false alarms
    "yellow": 400, # Real data from StatusLine is always preferred
}

CONTEXT_HEALTH_MESSAGES = {
    "yellow": (
        "**CONTEXT ADVISORY ({remaining}% remaining).** Consider saving cognitive state:\n"
        "  - save_checkpoint(\"<current focus>\", \"<progress notes>\")\n"
        "  - store_session_fact(\"current_task\", \"<what you're working on>\")"
    ),
    "orange": (
        "**CONTEXT LOW ({remaining}% remaining).** Save cognitive state NOW:\n"
        "1. store_session_fact(\"current_task\", \"<what you're working on>\")\n"
        "2. store_session_fact(\"approach\", \"<strategy being used>\")\n"
        "3. store_session_fact(\"progress\", \"<what's done, what remains>\")\n"
        "4. save_checkpoint(\"<current focus>\", \"<progress summary>\")\n"
        "Then continue your work."
    ),
    "red_ok": (
        "**COMPACTION IMMINENT ({remaining}% remaining).** Checkpoint was recently saved (good).\n"
        "Continue working but avoid starting large new tasks. Compaction may occur soon."
    ),
    "red_blocked": (
        "**COMPACTION IMMINENT ({remaining}% remaining).** You MUST save state NOW:\n"
        "1. store_session_fact(\"current_task\", \"<what you're working on>\")\n"
        "2. store_session_fact(\"approach\", \"<strategy being used>\")\n"
        "3. store_session_fact(\"progress\", \"<what's done, what remains>\")\n"
        "4. store_session_notes(\"<progress narrative>\", section=\"progress\")\n"
        "5. save_checkpoint(\"<current focus>\", \"<progress notes>\")\n"
        "6. remember() any patterns or decisions from this session\n"
        "Gated tools (Write/Edit/Bash/Task) are BLOCKED until checkpoint is saved."
    ),
}

# Session context keywords - trigger session handoff context injection
SESSION_KEYWORDS = [
    "where was i",
    "where were we",
    "what was i working on",
    "what were we working on",
    "what's next",
    "whats next",
    "next steps",
    "resume",
    "continue from",
    "last session",
    "previous session",
    "pick up where",
    "what todos",
    "my todos",
    "active todos",
    "pending tasks",
    "what should i do",
    "what should we do",
    "session context",
    "session resume",
    "/session-resume",
]

# Keywords that should trigger config management warning
# These patterns indicate Claude might be about to edit config files
CONFIG_KEYWORDS = [
    "settings.local.json",
    "settings.json",
    ".claude/settings",
    "hooks.json",
    "edit config",
    "change config",
    "modify config",
    "update config",
    "fix hooks",
    "change hooks",
    "add hook",
    "remove hook",
]

CONFIG_WARNING = """
⚠️ **CONFIG WARNING**: `.claude/settings.local.json` is **database-generated**.

**DO NOT manually edit** - changes will be overwritten on next SessionStart.

**To change permanently:**
1. Update database: `config_templates` (all projects) or `workspaces.startup_config` (one project)
2. Regenerate: `python scripts/generate_project_settings.py <project>` (from project dir)
3. Restart Claude Code

See: `knowledge-vault/40-Procedures/Config Management SOP.md`
"""


def load_reminder_state() -> Dict[str, Any]:
    """Load reminder state from file."""
    default_state = {
        "interaction_count": 0,
        "last_inbox_check": 0,
        "last_vault_refresh": 0,
        "last_git_check": 0,
        "last_tool_awareness": 0,
        "session_start": datetime.now(timezone.utc).isoformat(),
    }
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                state = json.load(f)
                return {**default_state, **state}
    except (json.JSONDecodeError, IOError):
        pass
    return default_state


def save_reminder_state(state: Dict[str, Any]):
    """Save reminder state to file."""
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state["last_interaction"] = datetime.now(timezone.utc).isoformat()
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass  # Silent fail - don't break the hook


def get_periodic_reminders(state: Dict[str, Any]) -> Optional[str]:
    """Generate periodic reminders based on interaction count.

    Returns formatted reminder string or None if no reminders due.
    """
    count = state.get("interaction_count", 0)
    reminders = []

    # Check each interval
    if count > 0 and count % REMINDER_INTERVALS["inbox_check"] == 0:
        if count != state.get("last_inbox_check", 0):
            reminders.append("📬 **Inbox Check**: Use `mcp__project-tools__check_inbox` to see pending messages")
            state["last_inbox_check"] = count

    if count > 0 and count % REMINDER_INTERVALS["vault_refresh"] == 0:
        if count != state.get("last_vault_refresh", 0):
            reminders.append("📚 **Vault Refresh**: Re-read CLAUDE.md if unsure about project conventions")
            state["last_vault_refresh"] = count

    if count > 0 and count % REMINDER_INTERVALS["git_check"] == 0:
        if count != state.get("last_git_check", 0):
            reminders.append("🔀 **Git Check**: Run `git status` to check for uncommitted changes")
            state["last_git_check"] = count

    if count > 0 and count % REMINDER_INTERVALS["tool_awareness"] == 0:
        if count != state.get("last_tool_awareness", 0):
            reminders.append("""🔧 **When to use MCP tools**:
  - **User reports bug/idea?** → `create_feedback` (NOT raw SQL)
  - **Planning 3+ file feature?** → `create_feature` + `add_build_task`
  - **Task too complex?** → Native `Task` tool (delegate to agents)
  - **Need deep reasoning?** → `sequential-thinking`
  - **Processing data?** → `python-repl` (keep out of context)""")
            state["last_tool_awareness"] = count

    if count > 0 and count % REMINDER_INTERVALS["storage_nudge"] == 0:
        if count != state.get("last_storage_nudge", 0):
            nudge_index = (count // REMINDER_INTERVALS["storage_nudge"]) % len(STORAGE_NUDGES)
            reminders.append(STORAGE_NUDGES[nudge_index])
            state["last_storage_nudge"] = count

    if count > 0 and count % REMINDER_INTERVALS["budget_check"] == 0:
        if count != state.get("last_budget_check", 0):
            reminders.append("""**CONTEXT BUDGET CHECK** (interaction #{count}):
  - Heavy tasks (BPMN, large files, multi-file refactor): ~800 tokens each
  - Medium tasks (single edit, test writing): ~400 tokens each
  - Light tasks (query, status, git): ~100 tokens each
  - **3+ heavy tasks remaining?** DELEGATE to agents (native Task tool)
  - **Run save_checkpoint()** after each completed task to preserve progress
  - **Over budget?** Stop, save state, let next session continue""".format(count=count))
            state["last_budget_check"] = count

    if reminders:
        return "\n## Periodic Reminders (Interaction #{})\n{}".format(
            count,
            "\n".join(f"- {r}" for r in reminders)
        )
    return None


def _check_context_health(interaction_count: int = 0) -> tuple:
    """Check context window health and return graduated urgency info.

    Reads context_health.json from StatusLine sensor. Falls back to prompt
    count heuristic when data is stale (>120s) or missing.

    Args:
        interaction_count: Current prompt count for fallback heuristic.

    Returns:
        (level, remaining_pct, message) where:
        - level: "green", "yellow", "orange", "red"
        - remaining_pct: Estimated remaining context percentage
        - message: Formatted directive string, or None for green
    """
    remaining_pct = -1
    used_fallback = False

    # Try to read StatusLine sensor data
    try:
        if CONTEXT_HEALTH_FILE.exists():
            import time as _time
            file_age = _time.time() - CONTEXT_HEALTH_FILE.stat().st_mtime
            if file_age < CONTEXT_HEALTH_FRESHNESS_SECONDS:
                # Fresh data from StatusLine
                with open(CONTEXT_HEALTH_FILE, 'r', encoding='utf-8') as f:
                    health_data = json.load(f)
                    remaining_pct = health_data.get('remaining_pct', -1)
            else:
                # Stale StatusLine data — but still trust it.
                # The StatusLine sensor provides ACTUAL remaining_percentage from
                # Claude Code. Even stale data is better than prompt-count guessing,
                # which can't distinguish 200K from 1M context windows.
                with open(CONTEXT_HEALTH_FILE, 'r', encoding='utf-8') as f:
                    health_data = json.load(f)
                    remaining_pct = health_data.get('remaining_pct', -1)
    except (json.JSONDecodeError, IOError, OSError):
        pass

    # Fallback to prompt count heuristic
    if remaining_pct < 0:
        used_fallback = True
        if interaction_count >= FALLBACK_THRESHOLDS["red"]:
            remaining_pct = 5
        elif interaction_count >= FALLBACK_THRESHOLDS["orange"]:
            remaining_pct = 15
        elif interaction_count >= FALLBACK_THRESHOLDS["yellow"]:
            remaining_pct = 25
        else:
            remaining_pct = 50

    # Compute urgency level
    if remaining_pct > 30:
        return ("green", remaining_pct, None)
    elif remaining_pct > 20:
        level = "yellow"
    elif remaining_pct > 10:
        level = "orange"
    else:
        level = "red"

    # For red level, check if checkpoint is recent
    if level == "red":
        checkpoint_recent = _check_recent_checkpoint()
        if checkpoint_recent:
            msg = CONTEXT_HEALTH_MESSAGES["red_ok"].format(remaining=remaining_pct)
        else:
            msg = CONTEXT_HEALTH_MESSAGES["red_blocked"].format(remaining=remaining_pct)
    else:
        msg = CONTEXT_HEALTH_MESSAGES[level].format(remaining=remaining_pct)

    source = "fallback" if used_fallback else "statusline"
    return (level, remaining_pct, msg)


def _check_recent_checkpoint(max_age_seconds: int = 120) -> bool:
    """Check if a checkpoint was saved recently (within max_age_seconds).

    Queries claude.session_state for the current project's updated_at timestamp.
    Returns True if updated within the threshold.
    """
    try:
        conn = get_db_connection()
        if not conn:
            return False

        project_name = os.path.basename(os.getcwd())
        cur = conn.cursor()
        cur.execute("""
            SELECT updated_at FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return False

        updated_at = row['updated_at'] if isinstance(row, dict) else row[0]
        if updated_at is None:
            return False

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if hasattr(updated_at, 'tzinfo') and updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        age = (now - updated_at).total_seconds()
        return age < max_age_seconds
    except Exception:
        return False


def detect_session_keywords(user_prompt: str) -> bool:
    """Detect if user prompt contains session-related keywords.

    Returns True if prompt is asking about session context, todos, or resumption.
    """
    prompt_lower = user_prompt.lower()
    for keyword in SESSION_KEYWORDS:
        if keyword in prompt_lower:
            logger.info(f"Detected session keyword: '{keyword}'")
            return True
    return False


def detect_config_keywords(user_prompt: str) -> bool:
    """Detect if user prompt mentions config files that are database-generated.

    Returns True if prompt mentions settings.local.json, hooks, or config editing.
    This triggers a warning that these files should not be manually edited.
    """
    prompt_lower = user_prompt.lower()
    for keyword in CONFIG_KEYWORDS:
        if keyword in prompt_lower:
            logger.info(f"Detected config keyword: '{keyword}'")
            return True
    return False


def get_session_context(project_name: str) -> Optional[str]:
    """Deprecated: Session context now served by project-tools get_work_context MCP tool.

    Returns None - callers should use get_work_context(scope='project') instead.
    """
    logger.info("get_session_context called but deprecated - use get_work_context MCP tool")
    return None
