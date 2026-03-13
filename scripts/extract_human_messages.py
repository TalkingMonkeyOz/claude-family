#!/usr/bin/env python3
"""Extract human messages from JSONL conversation transcript."""

import json
import sys
from pathlib import Path


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
                elif block.get("type") == "tool_result":
                    # Skip tool results
                    continue
        return "".join(text_parts)
    return ""


def extract_human_messages(jsonl_file):
    """Parse JSONL and extract all human messages."""
    messages = []
    turn = 0

    with open(jsonl_file, "r", encoding="utf-8") as f:
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

                    # Skip command messages and metadata
                    if "<command-message>" in text or "<command-name>" in text:
                        # This is a command invocation, skip or mark differently
                        continue

                    # Skip empty or system content
                    if not text.strip():
                        continue

                    # Truncate to 300 characters
                    text_preview = text.strip()[:300]

                    messages.append(
                        {
                            "turn": turn,
                            "timestamp": entry.get("timestamp", ""),
                            "text": text_preview,
                        }
                    )

    return messages


def main():
    jsonl_file = Path(
        r"C:\Users\johnd\.claude\projects\C--Projects-claude-family\0b358a38-8785-4acb-a4ab-a0c8e97d99ab.jsonl"
    )

    if not jsonl_file.exists():
        print(f"Error: File not found: {jsonl_file}")
        sys.exit(1)

    print(f"Parsing {jsonl_file}...")
    messages = extract_human_messages(jsonl_file)

    print(f"Found {len(messages)} human messages")

    # Write to output file
    output_file = Path(r"C:\Projects\claude-family\docs\morning_session_audit.md")
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Morning Session Audit - Human Messages\n\n")
        f.write(
            f"**Generated**: 2026-02-22\n"
            f"**Total Messages**: {len(messages)}\n"
            f"**Session ID**: 0b358a38-8785-4acb-a4ab-a0c8e97d99ab\n\n"
        )
        f.write("---\n\n")

        for msg in messages:
            f.write(f"## Turn {msg['turn']}\n\n")
            f.write(f"**Timestamp**: {msg['timestamp']}\n\n")
            f.write("```\n")
            f.write(msg["text"])
            f.write("\n```\n\n")

    print(f"Results written to {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
