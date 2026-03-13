import json
import os

jsonl_path = r"C:\Users\johnd\.claude\projects\C--Projects-claude-family\0b358a38-8785-4acb-a4ab-a0c8e97d99ab.jsonl"

messages = []
turn = 0
line_count = 0

with open(jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        line_count += 1
        if not line.strip():
            continue

        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
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
                if isinstance(block, dict) and block.get("type") == "text":
                    text += block.get("text", "")

        # Skip command messages
        if "<command-message>" in text:
            turn -= 1
            continue

        if not text.strip():
            turn -= 1
            continue

        text_preview = text.strip()[:300]
        messages.append({
            "turn": turn,
            "timestamp": entry.get("timestamp", ""),
            "text": text_preview,
        })

print(f"Processed {line_count} lines, found {len(messages)} user messages")

# Write output
output_path = r"C:\Projects\claude-family\docs\morning_session_audit.md"
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

print(f"Results written to {output_path}")
