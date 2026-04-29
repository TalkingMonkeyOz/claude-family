#!/usr/bin/env python3
"""
Commit FB# Auto-Resolve Hook - PostToolUse on Bash (FB397)

When Claude runs `git commit` and the resulting commit message contains
[FB#] tokens, this hook calls _resolve_feedback_impl for each one so the
feedback rows auto-close. Removes the manual "remember to mark FBs
resolved" step that was repeatedly missed.

Hook Event: PostToolUse
Matcher: Bash
Trigger: command starts with `git commit` AND tool succeeded
Targets: all unique [FB<digits>] tokens in the commit message
Skipped: amend without new message, merge commits, dry-run, --no-verify

Output: {"ok": True} (always; failures are logged + captured, fail-open).

Author: Claude Family
Created: 2026-04-29 (FB397)
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _resolve_log_file() -> Path:
    home_claude = Path.home() / ".claude"
    logs_dir = home_claude / "logs"
    if logs_dir.is_dir():
        return logs_dir / "hooks.log"
    home_claude.mkdir(exist_ok=True)
    return home_claude / "hooks.log"


LOG_FILE = _resolve_log_file()
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("commit_fb_resolve")


# ---------------------------------------------------------------------------
# Detection helpers (cheap — run on every PostToolUse Bash call)
# ---------------------------------------------------------------------------

_GIT_COMMIT_RE = re.compile(r"\bgit\s+(?:-[^\s]+\s+|--[^\s]+\s+|-C\s+\S+\s+)*commit\b")
# Tokens like [FB123], [FB1], [fb45], [Fb 12]. Numbers only after FB prefix.
_FB_TOKEN_RE = re.compile(r"\[\s*FB\s*(\d+)\s*\]", re.IGNORECASE)


def is_git_commit(command: str) -> bool:
    """True if a Bash command looks like a `git commit` invocation."""
    if not command:
        return False
    if not _GIT_COMMIT_RE.search(command):
        return False
    # Skip known no-op variants.
    if "--dry-run" in command:
        return False
    return True


def extract_fb_codes(message: str) -> List[str]:
    """Return unique FB codes (e.g., 'FB123') found in commit message."""
    if not message:
        return []
    seen = set()
    out: List[str] = []
    for match in _FB_TOKEN_RE.finditer(message):
        code = f"FB{int(match.group(1))}"
        if code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def _git_head_message(cwd: Optional[str]) -> Optional[str]:
    """Run `git log -1 --format=%B` to fetch the most recent commit message."""
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%B"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd or None,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _git_head_sha(cwd: Optional[str]) -> Optional[str]:
    creationflags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creationflags = subprocess.CREATE_NO_WINDOW
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=cwd or None,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


# ---------------------------------------------------------------------------
# Resolution (lazy import — only when an actual commit triggered work)
# ---------------------------------------------------------------------------


def _resolve_one(fb_code: str, sha: Optional[str]) -> dict:
    """Call _resolve_feedback_impl for a single FB code. Lazy-imports server_v2."""
    project_tools_path = (
        Path(__file__).resolve().parent.parent
        / "mcp-servers"
        / "project-tools"
    )
    sys.path.insert(0, str(project_tools_path))
    try:
        from server_v2 import _resolve_feedback_impl  # type: ignore
    except Exception as e:
        logger.warning(f"commit_fb_resolve: server_v2 import failed for {fb_code}: {e}")
        return {"success": False, "feedback_code": fb_code, "error": f"import: {e}"}

    note = f"Auto-resolved by commit {sha}" if sha else "Auto-resolved by commit"
    try:
        return _resolve_feedback_impl(fb_code, resolution_note=note)
    except Exception as e:
        logger.error(f"commit_fb_resolve: resolve failed for {fb_code}: {e}")
        return {"success": False, "feedback_code": fb_code, "error": str(e)}


# ---------------------------------------------------------------------------
# Hook entry
# ---------------------------------------------------------------------------


def _ok() -> None:
    print(json.dumps({"ok": True}))
    sys.exit(0)


def main() -> None:
    try:
        try:
            stdin_data = sys.stdin.read()
        except Exception:
            _ok()

        if not stdin_data:
            _ok()

        try:
            hook_input = json.loads(stdin_data)
        except Exception:
            _ok()

        # Cheap gate: only Bash, only git commit, only on success.
        tool_name = hook_input.get("tool_name") or hook_input.get("toolName") or ""
        if tool_name != "Bash":
            _ok()

        tool_input = hook_input.get("tool_input") or hook_input.get("toolInput") or {}
        command = tool_input.get("command") or ""
        if not is_git_commit(command):
            _ok()

        # Best-effort: skip if the bash call clearly failed. tool_response may
        # carry exit info under different keys depending on harness version.
        tool_response = (
            hook_input.get("tool_response")
            or hook_input.get("toolResponse")
            or hook_input.get("tool_output")
            or {}
        )
        if isinstance(tool_response, dict):
            if tool_response.get("interrupted") is True:
                _ok()
            # Newer harnesses surface a non-zero exitCode on Bash failure.
            exit_code = tool_response.get("exit_code", tool_response.get("exitCode"))
            if isinstance(exit_code, int) and exit_code != 0:
                _ok()

        cwd = (
            hook_input.get("cwd")
            or hook_input.get("working_directory")
            or os.getcwd()
        )

        message = _git_head_message(cwd) or ""
        fb_codes = extract_fb_codes(message)
        if not fb_codes:
            _ok()

        sha = _git_head_sha(cwd)

        results = []
        for code in fb_codes:
            res = _resolve_one(code, sha)
            results.append(res)
            if res.get("success"):
                logger.info(
                    f"commit_fb_resolve: {code} -> resolved "
                    f"(transitions={res.get('transitions_made')}, sha={sha})"
                )
            else:
                logger.warning(
                    f"commit_fb_resolve: {code} resolve failed: {res.get('error')}"
                )

        # PostToolUse: just acknowledge success. Per-FB results are in the log.
        _ok()

    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"commit_fb_resolve hook error: {e}", exc_info=True)
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from failure_capture import capture_failure  # type: ignore

            capture_failure(
                "commit_fb_resolve",
                str(e),
                "scripts/commit_fb_resolve_hook.py",
            )
        except Exception:
            pass
        _ok()


if __name__ == "__main__":
    main()
