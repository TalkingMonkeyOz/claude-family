#!/usr/bin/env python3
"""Create git hooks in .githooks directory."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
HOOKS_DIR = PROJECT_ROOT / '.githooks'

PREPARE_COMMIT_MSG = '''#!/bin/bash
COMMIT_MSG_FILE=$1
COMMIT_SOURCE=$2
if [ "$COMMIT_SOURCE" != "" ]; then exit 0; fi
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
if [ -z "$BRANCH" ]; then exit 0; fi
WORK_ITEM=""
if [[ $BRANCH =~ ^feature/(F[0-9]+) ]]; then WORK_ITEM="${BASH_REMATCH[1]}"; fi
if [[ $BRANCH =~ ^fix/(FB[0-9]+) ]]; then WORK_ITEM="${BASH_REMATCH[1]}"; fi
if [[ $BRANCH =~ ^task/(BT[0-9]+) ]]; then WORK_ITEM="${BASH_REMATCH[1]}"; fi
if [ -n "$WORK_ITEM" ]; then
    FIRST_LINE=$(head -n 1 "$COMMIT_MSG_FILE")
    if ! echo "$FIRST_LINE" | grep -qE "^\\[$WORK_ITEM\\]"; then
        TEMP_FILE=$(mktemp)
        echo "[$WORK_ITEM] $FIRST_LINE" > "$TEMP_FILE"
        tail -n +2 "$COMMIT_MSG_FILE" >> "$TEMP_FILE"
        mv "$TEMP_FILE" "$COMMIT_MSG_FILE"
    fi
fi
exit 0
'''

COMMIT_MSG = '''#!/bin/bash
COMMIT_MSG_FILE=$1
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")
if ! echo "$COMMIT_MSG" | grep -qE '\\[(F|FB|BT)[0-9]+\\]'; then
    echo ""
    echo "=============================================="
    echo "NOTE: No work item reference in commit message"
    echo "=============================================="
    echo "Consider using: feature/F1-desc, fix/FB1-desc"
    echo "=============================================="
fi
exit 0
'''

def main():
    print(f"Creating hooks in: {HOOKS_DIR}")
    HOOKS_DIR.mkdir(exist_ok=True)

    prepare = HOOKS_DIR / 'prepare-commit-msg'
    prepare.write_text(PREPARE_COMMIT_MSG, encoding='utf-8')
    print(f"Created: {prepare}")

    commit = HOOKS_DIR / 'commit-msg'
    commit.write_text(COMMIT_MSG, encoding='utf-8')
    print(f"Created: {commit}")

    print(f"Contents: {list(HOOKS_DIR.iterdir())}")
    print(f"Exists check: {HOOKS_DIR.exists()}")

if __name__ == '__main__':
    main()
