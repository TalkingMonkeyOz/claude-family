#!/usr/bin/env python3
"""
Lock Enforcement Hook - PreToolUse on Write/Edit/NotebookEdit/Bash

Enforces the FB392 lock doctrine: DB-deployed config files must not be
hand-edited because they regenerate from the database on every session
start. Hand-edits create drift.

Governed paths (block hand-edits):
  - ~/.claude/CLAUDE.md (global profile)
  - <project>/CLAUDE.md, <project>/claude.md
  - <project>/.claude/rules/*.md
  - <project>/.claude/skills/**/*.md
  - <project>/.claude/settings.local.json

Tools intercepted:
  - Write / Edit / NotebookEdit -> tool_input.file_path
  - Bash -> tool_input.command (parses for redirect writes: `>`, `>>`, `tee`)

Bypass (either is sufficient — auditable in both cases):
  1. Env var CLAUDE_LOCK_BYPASS=1 in the hook process env
  2. A comment line containing "LOCK BYPASS:" in the tool input
     (Write content, Edit new_string, or Bash command)

Schema (matches the BPMN model `content_validation` element `deny_governed`
and the modeled gateway `gw_bypass`):

  ALLOW:
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                             "permissionDecision": "allow"}}

  DENY:
    {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                             "permissionDecision": "deny",
                             "permissionDecisionReason": "..."}}

Fail-open: any unexpected error logs to ~/.claude/logs/hooks.log (or
~/.claude/hooks.log) and allows the operation through.

Hook Event: PreToolUse (matcher: Write|Edit|NotebookEdit|Bash)

Author: Claude Family
Created: 2026-04-27 (FB392)
"""

from __future__ import annotations

import io
import json
import logging
import os
import re
import shlex
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# ---------------------------------------------------------------------------
# Console / logging plumbing (mirrors other hooks)
# ---------------------------------------------------------------------------

if hasattr(sys.stdout, "buffer") and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def _resolve_log_file() -> Path:
    """Prefer ~/.claude/logs/hooks.log if logs/ exists, else ~/.claude/hooks.log."""
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
logger = logging.getLogger("lock_enforcement")


# ---------------------------------------------------------------------------
# Governance rules
# ---------------------------------------------------------------------------

# Tool name -> remediation message naming the right MCP tool to use instead.
REMEDIATION = {
    "global_claude_md": (
        "Use profile_update(scope='global', section=..., content=...) "
        "to edit the global ~/.claude/CLAUDE.md."
    ),
    "project_claude_md": (
        "Use config_manage(action='update_section', project=..., section=..., "
        "content=...) to edit a project CLAUDE.md."
    ),
    "rule": (
        "Use rule_update(project=..., rule_name=..., content=..., "
        "change_reason=...) to edit a rule (DB-deployed)."
    ),
    "skill": (
        "Use skill_update(project=..., skill_name=..., content=..., "
        "change_reason=...) to edit a skill (DB-deployed)."
    ),
    "settings_local_json": (
        "Do not hand-edit .claude/settings.local.json — it regenerates from "
        "claude.config_templates and claude.workspaces on session start. "
        "Send a task_request to claude-family for permanent config changes."
    ),
}

LOCK_BYPASS_TOKEN = "LOCK BYPASS:"
LOCK_BYPASS_ENV = "CLAUDE_LOCK_BYPASS"

# Bash redirect / write commands we treat as potential file mutations.
# Matches `>`, `>>`, `tee`, `tee -a`, `cp ... <target>`, `mv ... <target>`.
_BASH_REDIRECT_RE = re.compile(r">>?")
_BASH_WRITE_CMDS = {"tee", "cp", "mv", "install", "rsync"}


# ---------------------------------------------------------------------------
# Path classification
# ---------------------------------------------------------------------------


def _normalize(path: str) -> str:
    if not path:
        return ""
    # Expand ~ and environment vars so we catch ~/.claude/CLAUDE.md.
    expanded = os.path.expandvars(os.path.expanduser(path))
    return expanded.replace("\\", "/")


def _global_claude_md_path() -> str:
    return _normalize(str(Path.home() / ".claude" / "CLAUDE.md")).lower()


def classify_governed(path: str) -> Optional[str]:
    """Classify a file path against governed-path rules.

    Returns a remediation key from REMEDIATION, or None if not governed.
    """
    if not path:
        return None
    norm = _normalize(path).lower()
    base = norm.rsplit("/", 1)[-1]

    # 1. Global CLAUDE.md (~/.claude/CLAUDE.md)
    if norm == _global_claude_md_path():
        return "global_claude_md"

    # 2. Project CLAUDE.md / claude.md (any path with that basename)
    if base in {"claude.md"}:
        # We only govern when this lives inside a project (has a sibling
        # .claude/ tree or is checked-in). The conservative rule: if the
        # path traverses or shares a parent with `.claude/`, treat it as
        # governed. Fixtures outside any workspace pass.
        if _is_project_claude_md(norm):
            return "project_claude_md"
        return None

    # 3. settings.local.json under .claude/
    if base == "settings.local.json" and "/.claude/" in norm:
        return "settings_local_json"

    # 4. Rules: <project>/.claude/rules/*.md
    if "/.claude/rules/" in norm and base.endswith(".md"):
        return "rule"

    # 5. Skills: <project>/.claude/skills/**/*.md (any .md, including SKILL.md)
    if "/.claude/skills/" in norm and base.endswith(".md"):
        return "skill"

    return None


def _is_project_claude_md(norm_path: str) -> bool:
    """True if a CLAUDE.md / claude.md path looks like a project root file.

    Cheap heuristic: a sibling `.claude/` directory exists, OR the path
    sits next to a `.git` directory, OR `.claude/` appears anywhere as
    an ancestor segment.
    """
    if "/.claude/" in norm_path:
        # Inside a .claude tree — uncommon for CLAUDE.md but still governed.
        return True
    parent = os.path.dirname(norm_path)
    if not parent:
        return False
    try:
        if (Path(parent) / ".claude").is_dir():
            return True
        if (Path(parent) / ".git").is_dir():
            return True
    except OSError:
        return False
    return False


# ---------------------------------------------------------------------------
# Bypass detection
# ---------------------------------------------------------------------------


def _env_bypass() -> bool:
    return os.environ.get(LOCK_BYPASS_ENV, "").strip() == "1"


def _comment_bypass(*payloads: Optional[str]) -> bool:
    """Return True if any payload contains a LOCK BYPASS: comment line.

    The token must appear after a comment marker on its line — we accept
    `#`, `//`, `<!--`, or `--` (SQL) preceding it, OR the token at the
    start of a stripped line. We do NOT match the token mid-prose to
    avoid accidental triggers in normal text.
    """
    for payload in payloads:
        if not payload:
            continue
        for raw_line in str(payload).splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if LOCK_BYPASS_TOKEN not in line:
                continue
            # Only honor if line begins with a comment marker or the token.
            if (
                line.startswith("#")
                or line.startswith("//")
                or line.startswith("<!--")
                or line.startswith("--")
                or line.startswith(LOCK_BYPASS_TOKEN)
            ):
                return True
    return False


# ---------------------------------------------------------------------------
# Bash command parsing
# ---------------------------------------------------------------------------


def extract_bash_targets(command: str) -> List[str]:
    """Pull likely write-target file paths out of a Bash command string.

    Best-effort: covers redirects (`>`, `>>`), `tee [-a] file`, and
    `cp/mv/install src... dest`. Conservative — when in doubt we return
    paths so governance applies; the path-classifier is the actual gate.
    """
    if not command:
        return []
    targets: List[str] = []

    # 1. Redirects: split on `>` and `>>` while respecting quoted strings.
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes — fall back to a naive split so we still scan.
        tokens = command.split()

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in (">", ">>"):
            if i + 1 < len(tokens):
                targets.append(tokens[i + 1])
            i += 2
            continue
        # tokens like `>file` or `>>file`
        if tok.startswith(">>"):
            rest = tok[2:]
            if rest:
                targets.append(rest)
            i += 1
            continue
        if tok.startswith(">") and not tok.startswith(">="):
            rest = tok[1:]
            if rest:
                targets.append(rest)
            i += 1
            continue
        i += 1

    # 2. tee / cp / mv / install — last positional arg is typically the dest.
    lower_tokens = [t.lower() for t in tokens]
    for cmd in _BASH_WRITE_CMDS:
        if cmd in lower_tokens:
            idx = lower_tokens.index(cmd)
            args = [t for t in tokens[idx + 1 :] if not t.startswith("-")]
            if cmd == "tee":
                # tee writes to ALL non-flag args.
                targets.extend(args)
            elif args:
                # cp/mv/install: last arg is destination.
                targets.append(args[-1])

    return [t for t in targets if t]


# ---------------------------------------------------------------------------
# Hook output helpers
# ---------------------------------------------------------------------------


def _emit_allow() -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }
        )
    )
    sys.exit(0)


def _emit_deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )
    sys.exit(0)


def _build_deny_reason(file_path: str, kind: str) -> str:
    remedy = REMEDIATION.get(kind, "Use the appropriate MCP tool instead.")
    return (
        f"BLOCKED (FB392 lock doctrine): '{file_path}' is a DB-deployed file "
        f"that regenerates on session start; hand-edits will be overwritten "
        f"and create drift.\n\n"
        f"{remedy}\n\n"
        f"Bypass (auditable, use sparingly):\n"
        f"  - Set env CLAUDE_LOCK_BYPASS=1 for the session, OR\n"
        f"  - Include a comment line containing 'LOCK BYPASS: <reason>' "
        f"in the Write/Edit content or Bash command."
    )


# ---------------------------------------------------------------------------
# Decision core (kept pure for unit-testing)
# ---------------------------------------------------------------------------


def evaluate(hook_input: dict, env_bypass: bool) -> Tuple[str, Optional[str], Optional[str]]:
    """Pure decision function. Returns (decision, file_path, reason_kind).

    decision: 'allow' or 'deny'
    file_path: the path that triggered the deny (or None)
    reason_kind: REMEDIATION key (or None on allow)
    """
    tool_name = hook_input.get("tool_name") or hook_input.get("toolName") or ""
    tool_input = hook_input.get("tool_input") or hook_input.get("toolInput") or {}

    # Only intercept the four mutation tools.
    if tool_name not in ("Write", "Edit", "NotebookEdit", "Bash"):
        return ("allow", None, None)

    # Collect candidate paths and the payload to scan for bypass comments.
    candidate_paths: List[str] = []
    bypass_payloads: List[Optional[str]] = []

    if tool_name in ("Write", "Edit", "NotebookEdit"):
        fp = (
            tool_input.get("file_path")
            or tool_input.get("filePath")
            or tool_input.get("notebook_path")
            or tool_input.get("path")
        )
        if fp:
            candidate_paths.append(fp)
        if tool_name == "Write":
            bypass_payloads.append(tool_input.get("content"))
        elif tool_name == "Edit":
            bypass_payloads.append(tool_input.get("new_string"))
            bypass_payloads.append(tool_input.get("old_string"))
        elif tool_name == "NotebookEdit":
            bypass_payloads.append(tool_input.get("new_source"))

    elif tool_name == "Bash":
        command = tool_input.get("command") or ""
        bypass_payloads.append(command)
        candidate_paths.extend(extract_bash_targets(command))

    # Find the first governed path.
    governed_hits: List[Tuple[str, str]] = []
    for p in candidate_paths:
        kind = classify_governed(p)
        if kind:
            governed_hits.append((p, kind))

    if not governed_hits:
        return ("allow", None, None)

    # Bypass evaluation (env OR comment in payload).
    if env_bypass or _comment_bypass(*bypass_payloads):
        return ("allow", governed_hits[0][0], None)

    path, kind = governed_hits[0]
    return ("deny", path, kind)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        try:
            stdin_data = sys.stdin.read()
        except Exception as e:
            logger.warning(f"Failed to read stdin: {e}")
            _emit_allow()

        if not stdin_data:
            _emit_allow()

        try:
            hook_input = json.loads(stdin_data)
        except Exception as e:
            logger.warning(f"Failed to parse stdin JSON: {e}")
            _emit_allow()

        decision, path, kind = evaluate(hook_input, env_bypass=_env_bypass())
        if decision == "allow":
            if path:
                logger.info(
                    f"lock_enforcement: bypass honored for governed path "
                    f"{path} (kind={kind or 'unknown'})"
                )
            _emit_allow()

        # decision == "deny"
        reason = _build_deny_reason(path or "<unknown>", kind or "")
        logger.warning(
            f"lock_enforcement: BLOCKED tool="
            f"{hook_input.get('tool_name', '?')} path={path} kind={kind}"
        )
        _emit_deny(reason)

    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"lock_enforcement hook error: {e}", exc_info=True)
        try:
            sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
            from failure_capture import capture_failure  # type: ignore

            capture_failure("lock_enforcement", str(e), "scripts/lock_enforcement_hook.py")
        except Exception:
            pass
        # Fail-open
        _emit_allow()


if __name__ == "__main__":
    main()
