#!/bin/bash
# Pre-commit hook to enforce CLAUDE.md line limit
# Install: cp scripts/pre-commit-hook.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

MAX_LINES=250

# Check if CLAUDE.md (case-insensitive) is being committed
if git diff --cached --name-only | grep -iq "^claude\.md$"; then
    # Find the actual filename (CLAUDE.md or claude.md)
    CLAUDE_MD=$(git diff --cached --name-only | grep -i "^claude\.md$")

    # Count lines in CLAUDE.md
    LINE_COUNT=$(wc -l < "$CLAUDE_MD" | tr -d ' ')

    if [ "$LINE_COUNT" -gt "$MAX_LINES" ]; then
        echo ""
        echo "❌ COMMIT BLOCKED: CLAUDE.md exceeds line limit"
        echo ""
        echo "   Current lines: $LINE_COUNT"
        echo "   Maximum lines: $MAX_LINES"
        echo "   Excess lines:  $((LINE_COUNT - MAX_LINES))"
        echo ""
        echo "CLAUDE.md must stay concise and focused."
        echo ""
        echo "To fix:"
        echo "  1. Move detailed content to docs/ subdirectory"
        echo "  2. Keep only essential project context in CLAUDE.md"
        echo "  3. Run: python scripts/audit_docs.py (for guidance)"
        echo ""
        exit 1
    else
        echo "✓ CLAUDE.md line count OK ($LINE_COUNT/$MAX_LINES lines)"
    fi
fi

exit 0
