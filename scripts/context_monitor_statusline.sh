#!/bin/bash
# Context Monitor StatusLine Script
#
# Reads context_window metrics from Claude Code's StatusLine stdin JSON,
# computes urgency level, writes state to context_health.json, and
# outputs a compact status line display.
#
# StatusLine receives JSON on stdin with context_window.remaining_percentage
# and context_window.used_percentage on each render cycle.
#
# Output: Single line displayed in terminal status bar (e.g., "CTX:45%")
# Side effect: Writes ~/.claude/state/context_health.json for other hooks
#
# Author: Claude Family
# Date: 2026-03-05

input=$(cat)

# Extract context window metrics from stdin JSON
remaining=$(echo "$input" | jq -r '.context_window.remaining_percentage // -1' 2>/dev/null)
used=$(echo "$input" | jq -r '.context_window.used_percentage // -1' 2>/dev/null)

# If jq failed or no data, output minimal status and exit
if [ "$remaining" = "-1" ] || [ -z "$remaining" ]; then
    echo "CTX:?"
    exit 0
fi

# Compute urgency level
if [ "$remaining" -gt 30 ] 2>/dev/null; then
    level="green"
elif [ "$remaining" -gt 20 ] 2>/dev/null; then
    level="yellow"
elif [ "$remaining" -gt 10 ] 2>/dev/null; then
    level="orange"
else
    level="red"
fi

# Write state file for RAG hook and task discipline hook to read
state_dir="$HOME/.claude/state"
mkdir -p "$state_dir"
cat > "$state_dir/context_health.json" << EOF
{"remaining_pct":$remaining,"used_pct":$used,"level":"$level","timestamp":"$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF

# Output status line display
# Format: CTX:<used>% with visual indicator at thresholds
if [ "$level" = "red" ]; then
    echo "CTX:${used}%!!"
elif [ "$level" = "orange" ]; then
    echo "CTX:${used}%!"
elif [ "$level" = "yellow" ]; then
    echo "CTX:${used}%~"
else
    echo "CTX:${used}%"
fi
