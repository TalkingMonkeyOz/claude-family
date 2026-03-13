#!/usr/bin/env python3
"""Parse JSONL session file and extract human messages."""

import json

def extract_text_from_content(content):
    """Extract text from content field which can be string or list."""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        text_parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
        return "".join(text_parts)
    return ""

jsonl_path = r"C:\Users\johnd\.claude\projects\C--Projects-claude-family\0b358a38-8785-4acb-a4ab-a0c8e97d99ab.jsonl"
output_path = r"C:\Projects\claude-family\docs\morning_session_audit.md"

messages = []
turn = 0

# Parse JSONL file
with open(jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Look for user messages
        if entry.get("type") == "user":
            message = entry.get("message", {})
            if message.get("role") == "user":
                turn += 1

                # Extract content
                content = message.get("content", "")
                text = extract_text_from_content(content)

                # Skip command messages
                if "<command-message>" in text:
                    turn -= 1  # Don't count command invocations
                    continue

                # Skip empty
                if not text.strip():
                    turn -= 1
                    continue

                # Get first 300 chars
                text_preview = text.strip()[:300]

                messages.append({
                    "turn": turn,
                    "timestamp": entry.get("timestamp", ""),
                    "text": text_preview,
                })

# Write output
import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    f.write("# Morning Session Audit - Human Messages\n\n")
    f.write(f"**Generated**: 2026-02-22\n")
    f.write(f"**Total Messages**: {len(messages)}\n")
    f.write(f"**Session ID**: 0b358a38-8785-4acb-a4ab-a0c8e97d99ab\n\n")
    f.write("---\n\n")

    for msg in messages:
        f.write(f"## Turn {msg['turn']}\n\n")
        f.write(f"**Timestamp**: {msg['timestamp']}\n\n")
        f.write("```\n")
        f.write(msg["text"])
        f.write("\n```\n\n")

print(f"Extracted {len(messages)} human messages to {output_path}")
