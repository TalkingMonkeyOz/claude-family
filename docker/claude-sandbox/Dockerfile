# Claude Code Sandboxed Agent
# Isolated environment for autonomous agent execution
#
# Features:
# - Claude Code CLI pre-installed
# - Workspace mounted at /workspace (read-write)
# - No access to host system
# - Full permissions within container (--dangerously-skip-permissions safe)
#
# Usage:
#   docker build -t claude-sandbox .
#   docker run -v C:\Projects\myproject:/workspace claude-sandbox "task here"

FROM node:20-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI globally
RUN npm install -g @anthropic-ai/claude-code

# Create non-root user (Claude Code blocks --dangerously-skip-permissions with root)
RUN useradd -m -s /bin/bash claude && \
    mkdir -p /workspace /home/claude/.claude && \
    chown -R claude:claude /workspace /home/claude

# Set working directory
WORKDIR /workspace

# Create entrypoint script
# Supports both API key and OAuth credentials (mounted from host)
RUN echo '#!/bin/bash\n\
# Claude Sandbox Entrypoint\n\
# Runs Claude Code with full permissions (safe in container)\n\
\n\
# Check for credentials - either API key OR mounted OAuth credentials\n\
if [ -z "$ANTHROPIC_API_KEY" ] && [ ! -f "/home/claude/.claude/.credentials.json" ]; then\n\
    echo "ERROR: No credentials found"\n\
    echo "Either set ANTHROPIC_API_KEY or mount credentials:"\n\
    echo "  -v ~/.claude/.credentials.json:/home/claude/.claude/.credentials.json:ro"\n\
    exit 1\n\
fi\n\
\n\
# Run Claude with task from argument or stdin\n\
if [ -n "$1" ]; then\n\
    echo "$@" | claude --dangerously-skip-permissions --print\n\
else\n\
    claude --dangerously-skip-permissions --print\n\
fi\n\
' > /entrypoint.sh && chmod +x /entrypoint.sh

# Environment
ENV NODE_ENV=production

# Switch to non-root user
USER claude

# Entrypoint
ENTRYPOINT ["/entrypoint.sh"]
