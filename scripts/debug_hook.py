#!/usr/bin/env python3
"""Minimal debug hook - logs all stdin to see what Claude Code passes"""
import sys
import json
from pathlib import Path
from datetime import datetime

LOG = Path.home() / ".claude" / "hook_debug.log"

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | {msg}\n")

log("=== HOOK INVOKED ===")
log(f"sys.argv: {sys.argv}")

raw_stdin = sys.stdin.read()
log(f"stdin length: {len(raw_stdin)}")
log(f"stdin raw: {repr(raw_stdin[:1000])}")

if raw_stdin:
    try:
        data = json.loads(raw_stdin)
        log(f"tool_name: {data.get('tool_name')}")
        log(f"tool_input keys: {list(data.get('tool_input', {}).keys())}")
    except Exception as e:
        log(f"JSON parse error: {e}")

# Always allow - this is just for debugging
print(json.dumps({"hookSpecificOutput": {"permissionDecision": "allow"}}))
log("=== HOOK COMPLETE ===\n")
sys.exit(0)
