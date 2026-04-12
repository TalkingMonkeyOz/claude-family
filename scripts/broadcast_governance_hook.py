#!/usr/bin/env python3
"""
Broadcast Governance Hook — PreToolUse nudge for targeted messaging.

Fires before mcp__project-tools__broadcast. Injects additionalContext
reminding the Claude instance to prefer send_msg(to_project=X)
for directed communication. Does NOT block — always allows.

Matcher: mcp__project-tools__broadcast

Author: Claude Family (FB221)
Created: 2026-03-29
"""

import sys
import io
import json

# Force UTF-8 stdout for JSON output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    try:
        input_data = json.load(sys.stdin)
        tool_input = input_data.get("tool_input", {})
        subject = tool_input.get("subject", "")
        body = tool_input.get("body", "")

        guidance = (
            "BROADCAST GOVERNANCE: This message will go to ALL 19 projects. "
            "If this is directed at a specific project, CANCEL this broadcast "
            "and use send_msg(to_project='project-name') instead. "
            "Use system_info(view='recipients') to discover valid targets. "
            "Only use send_msg(is_broadcast=True) for genuine all-hands announcements "
            "(maintenance, infrastructure changes affecting everyone, team-wide updates)."
        )

        print(json.dumps({
            "decision": "allow",
            "additionalContext": guidance,
        }))

    except Exception:
        # Fail open
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
