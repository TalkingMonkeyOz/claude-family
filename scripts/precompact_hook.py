#!/usr/bin/env python3
"""
PreCompact Hook - CLAUDE.md and Vault Refresh Reminder

This script runs as a Claude Code PreCompact hook (before context compaction).
It injects a strong reminder to re-examine CLAUDE.md files and the knowledge vault.

Purpose:
    Context compaction is a critical moment to refresh understanding of:
    - Project guidelines (CLAUDE.md)
    - Vault knowledge (SOPs, patterns, domain knowledge)
    - Configuration sources (database, not files)

The user's insight: Almost any question has an answer in the vault.
Before continuing after compaction, Claude should re-examine these sources.

Usage:
    Called by Claude Code hooks system before compaction (manual or auto)
    Returns JSON with systemMessage to inject into post-compact context

Author: claude-code-unified
Date: 2025-12-29
"""

import sys
import os
import io
import json
from pathlib import Path
from typing import Dict

# Fix Windows encoding
if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def get_project_root() -> Path:
    """Find the project root (where CLAUDE.md lives)."""
    current = Path.cwd()

    # Walk up looking for CLAUDE.md or .git
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists() or (parent / ".git").exists():
            return parent

    return current


def get_vault_path(project_root: Path) -> Path:
    """Get the knowledge vault path if it exists."""
    vault = project_root / "knowledge-vault"
    return vault if vault.exists() else None


def build_refresh_message(hook_input: Dict) -> str:
    """Build the context refresh reminder message."""
    project_root = get_project_root()
    vault_path = get_vault_path(project_root)

    compact_type = hook_input.get('matcher', 'unknown')  # 'manual' or 'auto'

    message_parts = [
        f"🔄 CONTEXT COMPACTION ({compact_type.upper()}) - RE-EXAMINE CLAUDE FILES",
        "",
        "Before continuing, refresh your understanding from source files:",
        "",
        "1. CLAUDE.md (Global): ~/.claude/CLAUDE.md",
        "   - Global preferences, database connection, MCP servers",
        "   - Data Gateway usage, feedback system, session workflow",
        "",
        f"2. CLAUDE.md (Project): {project_root / 'CLAUDE.md'}",
        "   - Project-specific rules, architecture, work tracking",
        "   - Skills system, auto-apply instructions, recent changes",
        "",
    ]

    if vault_path:
        message_parts.extend([
            f"3. Knowledge Vault: {vault_path}",
            "   - 40-Procedures/: SOPs for common operations (check FIRST for how-to questions)",
            "   - 20-Domains/: Domain expertise (APIs, Database, WinForms, etc.)",
            "   - 30-Patterns/: Reusable patterns and gotchas",
            "   - Claude Family/: Infrastructure docs (hooks, tools, orchestrator)",
            "",
        ])

    message_parts.extend([
        "KEY REMINDER:",
        "⚠️  Almost ANY question (configuration, procedures, patterns, architecture)",
        "    likely has an answer in the vault. CHECK BEFORE implementing or asking user.",
        "",
        "⚠️  Database is source of truth for config (not files).",
        "    Settings regenerate from DB - check claude.config_templates, workspaces.startup_config",
        "",
        "After re-examining these sources, proceed with renewed context."
    ])

    return "\n".join(message_parts)


def main():
    """Main entry point for the hook."""
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except json.JSONDecodeError:
        hook_input = {}

    # Build the refresh reminder
    refresh_message = build_refresh_message(hook_input)

    # Return as systemMessage to inject into context
    response = {
        "systemMessage": f"<claude-context-refresh>\n{refresh_message}\n</claude-context-refresh>"
    }

    print(json.dumps(response))
    return 0


if __name__ == "__main__":
    sys.exit(main())
