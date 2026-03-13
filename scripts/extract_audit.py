#!/usr/bin/env python3
"""
Extract relevant conversation segments from the tool-results JSON file.
The file is a JSON array of conversation messages.
Search for segments related to:
1. Task management between sessions
2. User flows / user stories for task system
3. Built-in Claude Code task system vs custom DB approach
4. Zombie tasks, stale tasks, task restoration problems
5. User's vision for task lifecycle
"""

import json
import re

FILEPATH = r"C:\Users\johnd\.claude\projects\C--Projects-claude-family\4c1d9f34-c6e3-42c9-8b6e-49c0d05b7ea9\tool-results\mcp-project-tools-extract_conversation-1772563754421.txt"

KEYWORDS = [
    "zombie",
    "stale task",
    "stale todo",
    "task restor",
    "restore.*task",
    "task.*session",
    "session.*task",
    "built-in.*task",
    "native.*task",
    "task system",
    "task lifecycle",
    "task flow",
    "between session",
    "next session",
    "user flow",
    "user stor",
    "trial",
    "todo.*session",
    "session.*todo",
    "task.*persist",
    "persist.*task",
    "task.*carry",
    "carry.*task",
    "~/.claude/tasks",
    "CLAUDE_CODE_TASK",
    "TodoWrite.*session",
    "task.*duplicate",
    "duplicate.*task",
    "redundant",
    "task.*vision",
    "how task",
    "task should",
]

def extract_text_from_content(content):
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_result":
                    # Skip tool results
                    pass
        return "".join(parts)
    return ""


def matches_keywords(text):
    text_lower = text.lower()
    for kw in KEYWORDS:
        if re.search(kw, text_lower):
            return kw
    return None


def main():
    print(f"Loading file...")
    with open(FILEPATH, "r", encoding="utf-8") as f:
        raw = f.read()

    print(f"File size: {len(raw):,} chars")

    # The file is a JSON array
    data = json.loads(raw)
    print(f"Total entries: {len(data)}")

    # Build a list of (index, role, text) tuples
    messages = []
    for i, entry in enumerate(data):
        role = entry.get("role", "")
        content = entry.get("content", "")
        text = extract_text_from_content(content)
        if text.strip():
            messages.append((i, role, text))

    print(f"Messages with text: {len(messages)}")

    # Find messages matching keywords, include context (prev + next message)
    output = []
    matched_indices = set()

    for pos, (idx, role, text) in enumerate(messages):
        kw = matches_keywords(text)
        if kw:
            # Include surrounding context: 1 message before, 1 after
            start = max(0, pos - 1)
            end = min(len(messages) - 1, pos + 2)
            for ctx_pos in range(start, end + 1):
                matched_indices.add(ctx_pos)

    # Sort and deduplicate, output contiguous blocks
    sorted_positions = sorted(matched_indices)

    # Group into contiguous runs
    runs = []
    if sorted_positions:
        run_start = sorted_positions[0]
        run_end = sorted_positions[0]
        for p in sorted_positions[1:]:
            if p <= run_end + 3:  # merge if gap <= 3
                run_end = p
            else:
                runs.append((run_start, run_end))
                run_start = p
                run_end = p
        runs.append((run_start, run_end))

    print(f"Found {len(runs)} relevant conversation blocks")

    output_lines = []
    output_lines.append("# Extracted Conversation Segments - Task System Discussion\n")
    output_lines.append(f"**Source**: {FILEPATH}\n")
    output_lines.append(f"**Total entries**: {len(data)}\n")
    output_lines.append(f"**Relevant blocks found**: {len(runs)}\n\n")
    output_lines.append("---\n\n")

    for block_num, (run_start, run_end) in enumerate(runs, 1):
        output_lines.append(f"## Block {block_num} (messages {run_start}-{run_end})\n\n")
        for pos in range(run_start, min(run_end + 1, len(messages))):
            idx, role, text = messages[pos]
            output_lines.append(f"**[{role.upper()} - entry {idx}]**\n\n")
            output_lines.append(text.strip())
            output_lines.append("\n\n---\n\n")

    result = "\n".join(output_lines)

    out_path = r"C:\Projects\claude-family\docs\task_system_excerpts.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(result)

    print(f"Written to: {out_path}")
    print(f"Output size: {len(result):,} chars")

    # Also print to stdout for immediate review
    print("\n" + "="*80)
    print(result[:20000])
    if len(result) > 20000:
        print(f"\n... [truncated, see {out_path} for full output] ...")


if __name__ == "__main__":
    main()
