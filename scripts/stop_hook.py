#!/usr/bin/env python3
"""
Stop Hook (type: command) - Enforces task completion.

Reads the user's last prompt from the transcript JSONL, compares against
Claude's response, and uses Haiku to check if all requests were addressed.
If requests were missed, blocks with a reason forcing Claude to continue.

Receives on stdin: {session_id, transcript_path, last_assistant_message, ...}
Output: {"decision": "approve"} or {"decision": "block", "reason": "..."}

IMPORTANT: Uses stop_hook_active flag to prevent infinite loops.
"""
import json
import sys
import os
import logging

# Suppress all logging to avoid polluting Claude's output
logging.disable(logging.CRITICAL)

# Minimum prompt length to bother checking (skip "yes", "ok", etc.)
MIN_PROMPT_LENGTH = 30

# Skip prompts that start with these (commands, confirmations)
SKIP_PREFIXES = [
    "/", "yes", "no", "ok", "sure", "thanks", "thank you",
    "got it", "cool", "great", "fine", "yep", "nope",
    "<command", "quit", "exit"
]


def get_last_user_prompt(transcript_path):
    """Extract the last user prompt from the JSONL transcript."""
    last_prompt = None
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    obj = json.loads(line.strip())
                    if obj.get("type") == "user":
                        msg = obj.get("message", {}).get("content", "")
                        if isinstance(msg, str) and msg.strip():
                            last_prompt = msg.strip()
                except (json.JSONDecodeError, KeyError):
                    continue
    except (FileNotFoundError, IOError):
        return None
    return last_prompt


def should_skip(prompt):
    """Check if this prompt should skip enforcement."""
    if not prompt:
        return True
    if len(prompt) < MIN_PROMPT_LENGTH:
        return True
    lower = prompt.lower().strip()
    for prefix in SKIP_PREFIXES:
        if lower.startswith(prefix):
            return True
    return False


def check_with_haiku(user_prompt, assistant_response):
    """Use Haiku to check if all user requests were addressed."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        
        check_prompt = f"""You are a completeness checker. Compare the user's request against the assistant's response.

USER REQUEST:
{user_prompt[:2000]}

ASSISTANT RESPONSE (last message):
{assistant_response[:3000]}

Count every distinct request, question, and directive in the user's message. Then check if EACH ONE was addressed in the assistant's response.

If ALL were addressed: respond with exactly: {{"ok": true}}
If ANY were missed or only partially addressed: respond with exactly: {{"ok": false, "missed": "numbered list of what was missed or incomplete"}}

Be strict. If the user asked 5 things and only 4 were answered, that's a miss.
Return ONLY the JSON, nothing else."""

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": check_prompt}]
        )
        
        result_text = response.content[0].text.strip()
        # Try to parse JSON from response
        result = json.loads(result_text)
        return result
        
    except ImportError:
        # anthropic not installed - allow through
        return {"ok": True}
    except json.JSONDecodeError:
        # Haiku didn't return valid JSON - allow through
        return {"ok": True}
    except Exception:
        # Any other error - fail open
        return {"ok": True}


def main():
    try:
        input_data = json.load(sys.stdin)
    except:
        # Can't read input - allow through
        print(json.dumps({"decision": "approve"}))
        return

    # Prevent infinite loops - if stop_hook_active, we're already in a retry
    if input_data.get("stop_hook_active", False):
        print(json.dumps({"decision": "approve"}))
        return

    transcript_path = input_data.get("transcript_path", "")
    assistant_message = input_data.get("last_assistant_message", "")

    # Get the user's last prompt
    user_prompt = get_last_user_prompt(transcript_path)

    # Skip enforcement for short/simple prompts
    if should_skip(user_prompt):
        print(json.dumps({"decision": "approve"}))
        return

    # Check with Haiku
    result = check_with_haiku(user_prompt, assistant_message)

    # Log the decision for debugging
    log_path = os.path.join(os.path.dirname(__file__), "stop_hook_debug.log")
    try:
        from datetime import datetime
        with open(log_path, "a", encoding="utf-8") as log:
            log.write(f"\n--- {datetime.now().isoformat()} ---\n")
            log.write(f"User prompt ({len(user_prompt or '')} chars): {(user_prompt or '')[:200]}\n")
            log.write(f"Assistant msg ({len(assistant_message)} chars): {assistant_message[:200]}\n")
            log.write(f"Haiku result: {json.dumps(result)}\n")
    except:
        pass

    if result.get("ok", True):
        print(json.dumps({"decision": "approve"}))
    else:
        missed = result.get("missed", "some requests were not addressed")
        reason = f"INCOMPLETE: You missed the following from the user's request: {missed}. Create a task (TaskCreate) for EACH missed item, then address them all before stopping."
        print(json.dumps({"decision": "block", "reason": reason}))


if __name__ == "__main__":
    main()
