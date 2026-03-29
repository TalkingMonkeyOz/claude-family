#!/usr/bin/env python3
"""
PreCompact Hook - Context Preservation Before Compaction

Runs before context compaction (manual /compact or auto-compact).
Injects critical session state that would otherwise be lost:
- Active work items (todos, features, build_tasks)
- Current focus and next steps
- CLAUDE.md refresh reminder
- Available MCP tools reminder

This ensures Claude retains situational awareness after compaction.

Hook Event: PreCompact
Output: systemMessage injected into post-compact context

Author: Claude Family
Date: 2025-12-29
Updated: 2026-03-29 (Fix task duplication, remove unbounded re-injection)
"""

import sys
import os
import io
import json
import logging
from pathlib import Path
from typing import Dict, Optional

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
logger = logging.getLogger('precompact')

# Shared credential loading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg

psycopg_mod, PSYCOPG_VERSION, _, _ = detect_psycopg()
DB_AVAILABLE = psycopg_mod is not None


MAX_PRECOMPACT_TOKENS = 2000  # ~8000 chars budget for preserved state


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: chars / 4."""
    return len(text) // 4 if text else 0


def _apply_precompact_budget(sections: list) -> str:
    """Apply token budget to precompact sections, trimming lowest priority first.

    Each section is a tuple of (priority, label, content_lines).
    Priority 0 = highest (always kept), higher = trim first.
    """
    # Sort by priority (lowest number = highest importance)
    sections.sort(key=lambda s: s[0])

    # Build from highest priority, stop when budget exceeded
    kept = []
    total_tokens = 0
    trimmed_labels = []

    for priority, label, content_lines in sections:
        section_text = "\n".join(content_lines)
        section_tokens = _estimate_tokens(section_text)

        if total_tokens + section_tokens <= MAX_PRECOMPACT_TOKENS:
            kept.extend(content_lines)
            total_tokens += section_tokens
        else:
            # Try to fit partial section
            remaining_budget = MAX_PRECOMPACT_TOKENS - total_tokens
            if remaining_budget > 50:  # At least 200 chars worth
                partial_chars = remaining_budget * 4
                partial_text = section_text[:partial_chars]
                # Cut at last newline to avoid mid-line truncation
                last_nl = partial_text.rfind("\n")
                if last_nl > 0:
                    partial_text = partial_text[:last_nl]
                kept.append(partial_text)
                kept.append(f"  ... ({label} truncated, use list_session_facts() for full)")
                total_tokens += _estimate_tokens(partial_text)
            trimmed_labels.append(label)

    if trimmed_labels:
        logger.info(f"PreCompact budget: {total_tokens} tokens, trimmed: {', '.join(trimmed_labels)}")
    else:
        logger.info(f"PreCompact budget: {total_tokens} tokens, all sections fit")

    return "\n".join(kept)


def get_session_state_for_compact(project_name: str) -> Optional[str]:
    """Query active work items and session state to preserve across compaction.

    Uses priority-based budget capping to keep injection under ~2000 tokens.
    Priority: P0=in_progress todos, P1=focus/next_steps, P2=features, P3=facts, P4=notes
    """
    conn = get_db_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        sections = []  # List of (priority, label, lines)

        # Get project_id
        cur.execute("SELECT project_id::text FROM claude.projects WHERE project_name = %s", (project_name,))
        row = cur.fetchone()
        if not row:
            conn.close()
            return None
        project_id = row['project_id'] if isinstance(row, dict) else row[0]

        # P0: Active todos (in_progress AND pending — both survive compaction)
        cur.execute("""
            SELECT content, status, priority
            FROM claude.todos
            WHERE project_id = %s::uuid AND is_deleted = false
              AND status IN ('in_progress', 'pending')
            ORDER BY
              CASE status WHEN 'in_progress' THEN 0 ELSE 1 END,
              priority ASC
            LIMIT 10
        """, (project_id,))
        todos = cur.fetchall()

        if todos:
            todo_lines = [
                "TASK STATE (READ-ONLY REFERENCE — tasks persist natively, DO NOT re-create):",
                "  NOTE: These tasks already exist in the task list. Use TaskList to verify.",
                "  DO NOT call TaskCreate for any items listed below.",
            ]
            for t in todos:
                content = t['content'] if isinstance(t, dict) else t[0]
                status = t['status'] if isinstance(t, dict) else t[1]
                marker = "[>]" if status == 'in_progress' else "[ ]"
                todo_lines.append(f"  {marker} {content}")
            sections.append((0, "in_progress_todos", todo_lines))

        # P1: Session state (focus, next_steps)
        cur.execute("""
            SELECT current_focus, next_steps
            FROM claude.session_state
            WHERE project_name = %s
        """, (project_name,))
        state = cur.fetchone()

        if state:
            focus_lines = []
            focus = state['current_focus'] if isinstance(state, dict) else state[0]
            next_steps = state['next_steps'] if isinstance(state, dict) else state[1]
            if focus:
                focus_lines.append(f"\nCURRENT FOCUS: {focus}")
            if next_steps and isinstance(next_steps, list):
                focus_lines.append("NEXT STEPS:")
                for step in next_steps[:3]:
                    step_text = step.get('step', str(step)) if isinstance(step, dict) else str(step)
                    focus_lines.append(f"  - {step_text}")
            if focus_lines:
                sections.append((1, "focus", focus_lines))

        # P2: Active features (in_progress only)
        cur.execute("""
            SELECT f.feature_name, f.short_code,
                   (SELECT COUNT(*) FROM claude.build_tasks bt
                    WHERE bt.feature_id = f.feature_id AND bt.status = 'in_progress') as active_tasks
            FROM claude.features f
            WHERE f.project_id = %s::uuid AND f.status = 'in_progress'
            ORDER BY f.updated_at DESC LIMIT 3
        """, (project_id,))
        features = cur.fetchall()

        if features:
            feat_lines = ["\nACTIVE FEATURES:"]
            for f in features:
                name = f['feature_name'] if isinstance(f, dict) else f[0]
                code = f['short_code'] if isinstance(f, dict) else f[1]
                active = f['active_tasks'] if isinstance(f, dict) else f[2]
                feat_lines.append(f"  - [{code}] {name} ({active} active tasks)")
            sections.append((2, "features", feat_lines))

        # P3: Session facts (user intent, decisions)
        cur.execute("""
            SELECT fact_key, fact_value, fact_type
            FROM claude.session_facts
            WHERE session_id = (
                SELECT session_id FROM claude.sessions
                WHERE project_name = %s AND session_end IS NULL
                ORDER BY session_start DESC LIMIT 1
            )
            AND fact_type IN ('decision', 'reference', 'note')
            AND NOT is_sensitive
            ORDER BY created_at DESC LIMIT 5
        """, (project_name,))
        facts = cur.fetchall()

        if facts:
            fact_lines = ["\nSESSION CONTEXT (decisions & intent):"]
            for f in facts:
                key = f['fact_key'] if isinstance(f, dict) else f[0]
                value = f['fact_value'] if isinstance(f, dict) else f[1]
                display = value[:150] + "..." if len(value) > 150 else value
                fact_lines.append(f"  [{key}]: {display}")
            sections.append((3, "facts", fact_lines))

        # P3.5: Pinned workfiles (component context summaries)
        try:
            cur.execute("""
                SELECT component, title, workfile_type
                FROM claude.project_workfiles
                WHERE project_id = %s::uuid AND is_pinned = TRUE AND is_active = TRUE
                ORDER BY component, updated_at DESC
                LIMIT 10
            """, (project_id,))
            pinned = cur.fetchall()

            if pinned:
                wf_lines = ["\nPINNED WORKFILES (component context):"]
                current_component = None
                for p in pinned:
                    comp = p['component'] if isinstance(p, dict) else p[0]
                    title = p['title'] if isinstance(p, dict) else p[1]
                    if comp != current_component:
                        wf_lines.append(f"  [{comp}]")
                        current_component = comp
                    wf_lines.append(f"    - {title}")
                wf_lines.append("  Use unstash(component) to load full content")
                sections.append((3, "pinned_workfiles", wf_lines))
        except Exception:
            pass  # Table might not exist yet in older deployments

        conn.close()

        if not sections:
            return None

        return _apply_precompact_budget(sections)

    except Exception as e:
        logger.error(f"Failed to get session state for compact: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return None


def build_refresh_message(hook_input: Dict) -> str:
    """Build context refresh message with session state."""
    project_root = Path.cwd()
    project_name = project_root.name
    compact_type = hook_input.get('matcher', 'unknown')

    parts = [
        f"CONTEXT COMPACTION ({compact_type.upper()}) - PRESERVED STATE",
        "=" * 60,
    ]

    # Inject session state from database
    session_state = get_session_state_for_compact(project_name)
    if session_state:
        parts.append("")
        parts.append(session_state)

    # Session notes: only inject if state section was small enough
    state_tokens = _estimate_tokens("\n".join(parts))
    remaining_budget = MAX_PRECOMPACT_TOKENS - state_tokens
    if remaining_budget > 100:
        notes_path = Path.home() / ".claude" / "session_notes.md"
        if notes_path.exists():
            try:
                notes_content = notes_path.read_text(encoding='utf-8').strip()
                if notes_content and len(notes_content) > 20:
                    max_chars = min(remaining_budget * 4, 400)
                    if len(notes_content) > max_chars:
                        notes_content = notes_content[:max_chars] + "\n  ... (use get_session_notes() for full)"
                    parts.append("")
                    parts.append("SESSION NOTES:")
                    parts.append(notes_content)
            except Exception:
                pass

    parts.extend([
        "",
        "=" * 40,
        "IMPORTANT: Tasks persist natively — DO NOT re-create tasks listed above.",
        "RECOVERY: list_session_facts() | get_session_notes() | get_work_context('current')",
        "Then recall_memories('<what you were working on>'), unstash(component) for workfiles, and resume.",
        "CLAUDE.md and rules are re-loaded automatically by the system prompt — no manual re-injection needed.",
    ])

    return "\n".join(parts)


def main():
    """Main entry point for the hook."""
    logger.info("PreCompact hook invoked")

    try:
        try:
            hook_input = json.load(sys.stdin)
        except json.JSONDecodeError:
            hook_input = {}

        refresh_message = build_refresh_message(hook_input)

        response = {
            "systemMessage": f"<claude-context-refresh>\n{refresh_message}\n</claude-context-refresh>"
        }

        print(json.dumps(response))
        logger.info("PreCompact hook completed - session state injected")
        return 0

    except Exception as e:
        logger.error(f"PreCompact hook failed: {e}", exc_info=True)
        try:
            from failure_capture import capture_failure
            capture_failure("precompact_hook", str(e), "scripts/precompact_hook.py")
        except Exception:
            pass
        print(json.dumps({"systemMessage": "Context compaction occurred. Re-read CLAUDE.md and check work items."}))
        return 0


if __name__ == "__main__":
    sys.exit(main())
