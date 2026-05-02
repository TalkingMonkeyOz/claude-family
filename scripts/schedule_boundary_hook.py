#!/usr/bin/env python3
"""
Schedule Boundary Hook — PreToolUse on RemoteTrigger (the underlying tool of `/schedule`).

Hard enforcement of the FB416/#1033 + FB417 storage-rules boundary:
  /schedule (cloud sandbox, BILLABLE) is reserved for work that genuinely
  needs an isolated environment (open a PR, run in a sandbox).

  Local work — anything touching ~/.claude/, claude.* schema, scripts/,
  mcp-servers/, local DB, recurring system maintenance — MUST use one of:
    create_reminder()   — judgment call to surface in N days
    job_enqueue()       — one-off async work
    job_schedule()      — recurring local cron

This hook intercepts every RemoteTrigger call, scores the prompt for
local-vs-cloud signals, and:
  - DENY  if the work is clearly local (high local score, no cloud signals)
  - ALLOW with warning if signals are mixed (logged for review)
  - ALLOW silently if cloud signals dominate

Every decision is recorded in claude.enforcement_log for audit.

Hook event: PreToolUse | Matcher: RemoteTrigger
"""
import io
import json
import logging
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LOG_FILE = Path.home() / ".claude" / "hooks.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger('schedule_boundary')

DB_URI = (
    os.environ.get('DATABASE_URI')
    or os.environ.get('DATABASE_URL')
    or os.environ.get('POSTGRES_CONNECTION_STRING')
    or ''
)

# --- Signal patterns --------------------------------------------------------

# Strong cloud signals — work that genuinely needs the cloud sandbox
CLOUD_SIGNALS = [
    re.compile(r'\bopen\s+(a\s+)?pr\b', re.I),
    re.compile(r'\bgh\s+pr\s+create\b', re.I),
    re.compile(r'\bgithub\.com/', re.I),
    re.compile(r'\bcreate\s+(a\s+)?pull\s+request\b', re.I),
    re.compile(r'\bisolated\s+(env|environment|sandbox)\b', re.I),
    re.compile(r'\bclean(\s+|-)?room\b', re.I),
    re.compile(r'\bramp\s+(up|down)\s+(the\s+)?flag\b', re.I),
    re.compile(r'\bevaluat(e|ing)\s+(the\s+)?(rollout|experiment)\b', re.I),
]

# Strong local signals — work that should run on this machine, not in cloud
LOCAL_SIGNALS = [
    re.compile(r'~?[/\\]\.claude[/\\]', re.I),
    re.compile(r'\bclaude\.\w+\s', re.I),                      # claude.* schema
    re.compile(r'\bclaude\.(feedback|features|task_queue|messages|knowledge|sessions|scheduled_jobs|job_templates|memories)\b', re.I),
    re.compile(r'\bscripts[/\\]\w+\.py\b', re.I),
    re.compile(r'\bmcp-servers[/\\]', re.I),
    re.compile(r'\bC:[/\\]Projects[/\\]', re.I),
    re.compile(r'\blocalhost\b', re.I),
    re.compile(r'\bpostgres(ql)?:\s*//\s*localhost\b', re.I),
    re.compile(r'\b(hooks?|drift|embedding|reindex|consolidat\w*)\.log\b', re.I),
    re.compile(r'\bqueue\s+health\b', re.I),
    re.compile(r'\bmemory\s+consolidation\b', re.I),
    re.compile(r'\bdrift\s+detect\w*\b', re.I),
    re.compile(r'\bvault\s+embed\w*\b', re.I),
    re.compile(r'\bckg\s+(reindex|drift|crawl)\b', re.I),
    re.compile(r'\bdead[_\s-]letter\b', re.I),
    re.compile(r'\barchive\s+sweep\b', re.I),
    re.compile(r'\bhost\s*-?\s*level\b', re.I),
    re.compile(r'\b(?:my|local)\s+(database|machine|filesystem)\b', re.I),
]


def score_signals(text: str) -> tuple[int, int, list[str], list[str]]:
    """Return (local_count, cloud_count, local_hits, cloud_hits)."""
    local_hits, cloud_hits = [], []
    for pat in LOCAL_SIGNALS:
        m = pat.search(text)
        if m:
            local_hits.append(m.group(0))
    for pat in CLOUD_SIGNALS:
        m = pat.search(text)
        if m:
            cloud_hits.append(m.group(0))
    return len(local_hits), len(cloud_hits), local_hits, cloud_hits


def log_decision(action: str, prompt: str, local_hits: list[str], cloud_hits: list[str]) -> None:
    """Persist the decision to claude.enforcement_log (best-effort)."""
    if not DB_URI:
        return
    try:
        try:
            import psycopg
            conn = psycopg.connect(DB_URI, connect_timeout=2)
        except ImportError:
            import psycopg2 as psycopg
            conn = psycopg.connect(DB_URI, connect_timeout=2)
        message = json.dumps({
            "event": "schedule_boundary",
            "prompt_preview": prompt[:300],
            "local_hits": local_hits,
            "cloud_hits": cloud_hits,
        })
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO claude.enforcement_log "
                    "(reminder_type, reminder_message, action_taken) "
                    "VALUES (%s, %s, %s)",
                    (f"schedule_boundary_{action}", message, action),
                )
        conn.close()
    except Exception as e:
        logger.error(f"enforcement_log write failed: {e}")


def allow(reason: str = "") -> None:
    out = {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                   "permissionDecision": "allow"}}
    if reason:
        out["hookSpecificOutput"]["permissionDecisionReason"] = reason
    print(json.dumps(out))
    sys.exit(0)


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))
    sys.exit(0)


def main() -> None:
    try:
        stdin_data = sys.stdin.read()
        if not stdin_data:
            allow("no stdin")
        hook_input = json.loads(stdin_data)
    except Exception as e:
        # Fail-open — never break a tool call due to a hook crash
        logger.error(f"hook input parse error: {e}")
        allow("parse error")

    tool_input = hook_input.get('tool_input') or hook_input.get('toolInput') or {}

    # RemoteTrigger payload shape varies; collect every text field we can find
    candidate_fields = ['prompt', 'message', 'instructions', 'task',
                        'description', 'name', 'goal', 'body']
    parts = []
    for f in candidate_fields:
        v = tool_input.get(f)
        if isinstance(v, str) and v:
            parts.append(v)
    text = "\n".join(parts) or json.dumps(tool_input, default=str)

    local, cloud, local_hits, cloud_hits = score_signals(text)

    # Decision matrix
    if cloud >= 1 and local <= cloud:
        log_decision("allow_cloud", text, local_hits, cloud_hits)
        allow(f"cloud signals present ({cloud_hits})")

    if local >= 2 and cloud == 0:
        # Clear local — block hard
        msg = (
            "BLOCKED: this work appears to be local — use local schedulers instead "
            "of /schedule (cloud, billable).\n\n"
            f"Local signals detected: {local_hits}\n\n"
            "Use one of (all free, all local):\n"
            "  - create_reminder(due_at, body, rationale)  — judgment-call surface in N days\n"
            "  - job_enqueue(template_name, payload_override)  — one-shot async, drains via task_worker\n"
            "  - job_schedule(action='create', template_id, schedule)  — recurring cron\n\n"
            "If this work GENUINELY needs the cloud sandbox (opens a PR, "
            "runs in an isolated env), rephrase the prompt to make the cloud "
            "signal explicit (mention 'open a PR' / 'sandbox' / 'isolated env')."
        )
        log_decision("deny", text, local_hits, cloud_hits)
        deny(msg)

    if local >= 1 and cloud == 0:
        # Mixed/weak — allow but warn
        log_decision("allow_with_warning", text, local_hits, cloud_hits)
        allow(
            f"WARN: local signals detected {local_hits}; consider job_enqueue/job_schedule. "
            "Allowing because no strong block-criteria met."
        )

    # Fully neutral — allow without comment
    log_decision("allow_neutral", text, local_hits, cloud_hits)
    allow("no boundary signals")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        logger.error(f"unexpected hook error: {e}", exc_info=True)
        # Fail-open
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
        }}))
        sys.exit(0)
