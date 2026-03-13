#!/usr/bin/env python3
"""Extract human messages from session JSONL."""
import json
import sys
from pathlib import Path

def main():
    jsonl_path = r"C:\Users\johnd\.claude\projects\C--Projects-claude-family\0b358a38-8785-4acb-a4ab-a0c8e97d99ab.jsonl"
    output_path = r"C:\Projects\claude-family\docs\morning_session_audit.md"

    messages = []
    turn = 0

    print(f"Parsing {jsonl_path}...")

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"JSON error on line {line_no}: {e}")
                continue

            if entry.get("type") != "user":
                continue

            message = entry.get("message", {})
            if message.get("role") != "user":
                continue

            turn += 1
            content = message.get("content", "")

            # Extract text
            text = ""
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text += block.get("text", "")
                        elif block.get("type") == "tool_result":
                            # Skip tool results
                            pass

            # Skip command messages
            if "<command-message>" in text:
                turn -= 1
                continue

            if not text.strip():
                turn -= 1
                continue

            # Truncate to 300 chars
            text_preview = text.strip()[:300]

            messages.append({
                "turn": turn,
                "timestamp": entry.get("timestamp", ""),
                "text": text_preview,
            })

            if turn % 10 == 0:
                print(f"  Processed {turn} human messages...")

    print(f"Total: {len(messages)} human messages extracted")

    # Write output
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

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

    print(f"Results written to {output_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
