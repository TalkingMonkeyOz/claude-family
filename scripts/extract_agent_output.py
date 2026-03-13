#!/usr/bin/env python3
"""Extract markdown document content from agent JSONL output files."""

import json
import sys
import re


def extract_markdown_from_jsonl(input_path: str, output_path: str, doc_name: str) -> None:
    """Parse JSONL output file and extract the markdown document content."""
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the last assistant message with the document content
    # The document is inside a markdown code block in the text field
    for line in reversed(lines):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Look for assistant messages
        msg = record.get('message', {})
        if not isinstance(msg, dict):
            continue
        if msg.get('role') != 'assistant':
            continue

        content = msg.get('content', [])
        if not isinstance(content, list):
            continue

        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get('type') != 'text':
                continue
            text = item.get('text', '')

            # Look for markdown code block containing the document
            # The document starts with YAML frontmatter inside ```markdown
            match = re.search(r'```markdown\n(---\n.*?)```', text, re.DOTALL)
            if match:
                doc_content = match.group(1)
                with open(output_path, 'w', encoding='utf-8') as out:
                    out.write(doc_content)
                print(f"SUCCESS: Extracted {doc_name}")
                print(f"  Written to: {output_path}")
                line_count = doc_content.count('\n') + 1
                print(f"  Line count: {line_count}")
                return

            # Also try: document starts with --- (frontmatter without code block)
            match2 = re.search(r'(---\nprojects:.*?\*\*Location\*\*:.*?\n)', text, re.DOTALL)
            if match2:
                doc_content = match2.group(1)
                with open(output_path, 'w', encoding='utf-8') as out:
                    out.write(doc_content)
                print(f"SUCCESS: Extracted {doc_name} (no code block)")
                print(f"  Written to: {output_path}")
                line_count = doc_content.count('\n') + 1
                print(f"  Line count: {line_count}")
                return

    print(f"FAILED: Could not find document content for {doc_name} in {input_path}")
    sys.exit(1)


if __name__ == '__main__':
    print("Extracting library-science-research.md...")
    extract_markdown_from_jsonl(
        r'C:\Users\johnd\AppData\Local\Temp\claude\C--Projects-claude-family\tasks\a927d4753f648044c.output',
        r'C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\research\library-science-research.md',
        'library-science-research.md'
    )

    print("\nExtracting filing-records-management-research.md...")
    extract_markdown_from_jsonl(
        r'C:\Users\johnd\AppData\Local\Temp\claude\C--Projects-claude-family\tasks\af175a64bc1659160.output',
        r'C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\research\filing-records-management-research.md',
        'filing-records-management-research.md'
    )

    print("\nDone.")
