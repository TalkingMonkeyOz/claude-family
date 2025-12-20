---
category: hooks
confidence: 95
created: 2025-12-19
projects:
- claude-family
synced: true
synced_at: '2025-12-20T11:08:45.244942'
tags:
- claude-code
- hooks
- python
title: Claude Code Hook Response Format
type: gotcha
---

# Claude Code Hook Response Format

## Summary
UserPromptSubmit hooks returning `{"systemPrompt": "..."}` do NOT inject content into Claude's context. Use `hookSpecificOutput.additionalContext` instead.

## Details
When writing hooks for Claude Code (the CLI tool), the output format is critical for content injection.

### WRONG Approach
```python
# This does NOT inject content into Claude's context
result = {
    "systemPrompt": "Follow these instructions..."
}
print(json.dumps(result))
sys.exit(0)
```

### CORRECT Approach
```python
# Use hookSpecificOutput.additionalContext for UserPromptSubmit
result = {
    "hookSpecificOutput": {
        "additionalContext": "<process-guidance>\nFollow these instructions...\n</process-guidance>"
    }
}
print(json.dumps(result))
sys.exit(0)
```

### Alternative: Plain Text
```python
# Plain text output also works
print("Follow these instructions...")
sys.exit(0)
```

## Exit Codes

| Exit Code | Meaning |
|-----------|---------|
| 0 | Success - proceed with prompt |
| 1 | Error - show error, may block |
| Non-zero | Hook failed |

## Code Example
```python
#!/usr/bin/env python3
import json
import sys

def main():
    # Read stdin for prompt context
    input_data = json.load(sys.stdin)
    prompt = input_data.get("prompt", "")
    
    # Generate additional context
    context = process_prompt(prompt)
    
    # Return in correct format
    if context:
        result = {
            "hookSpecificOutput": {
                "additionalContext": context
            }
        }
        print(json.dumps(result))
    
    sys.exit(0)

if __name__ == "__main__":
    main()
```

## Related
- [[claude-code-hooks-overview]]
- [[process-router-implementation]]