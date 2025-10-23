# Claude Family - Infrastructure Project

**Type**: Infrastructure
**Purpose**: Shared configuration, scripts, and documentation for Claude instances

---

## What Is This?

The **Claude Family** project provides shared infrastructure for multiple Claude instances working across different projects with persistent knowledge storage in PostgreSQL.

**Key Features:**
- PostgreSQL database (`ai_company_foundation`) for persistent knowledge
- MCP servers (postgres, memory, filesystem, tree-sitter, github)
- Shared documentation and scripts
- Session history tracking
- Knowledge management system

---

## Current Architecture (Oct 21, 2025)

**Two Active Identities:**
1. **claude-desktop** - GUI interface (Claude Desktop app)
2. **claude-code-unified** - CLI interface (Claude Code Console)

**Project-Aware Context:**
- Each project has its own `CLAUDE.md` file that auto-loads
- Shared scripts and documentation in `claude-family` repository
- Universal knowledge stored in PostgreSQL
- MCP servers available to all instances

---

## Directory Structure

```
claude-family/
├── docs/                     # Documentation and session notes
├── .claude/                  # Shared slash commands
│   └── commands/
│       ├── session-start.md  # Startup checklist
│       └── session-end.md    # End-of-session logging
├── scripts/
│   ├── audit_docs.py                 # Documentation audit
│   ├── install_git_hooks.py          # Install git hooks
│   ├── pre-commit-hook.sh            # Enforce CLAUDE.md limits
│   ├── auto_sync_startup.py          # PostgreSQL → MCP sync
│   ├── load_claude_startup_context.py
│   └── sync_postgres_to_mcp.py
├── .docs-manifest.json       # Documentation registry
├── CLAUDE.md                 # Project context (auto-loaded)
└── README.md                 # You are here
```

---

## Quick Start

### Every Session (Optional)

Run `/session-start` to:
- Check documentation health (monthly)
- Query for existing solutions before proposing new ones
- Search memory graph for relevant context

### End of Session (Optional)

Run `/session-end` to:
- Log session to PostgreSQL
- Store reusable knowledge
- Update memory graph

---

## PostgreSQL Database

**Database**: `ai_company_foundation`

**Schemas:**
- `claude_family` - Identities, session history, shared knowledge
- `nimbus_context` - Nimbus project context
- `public` - Work packages, projects, SOPs

**Key Tables:**
- `claude_family.identities` - Claude instances
- `claude_family.session_history` - Session logs
- `claude_family.shared_knowledge` - Reusable patterns/learnings
- `claude_family.project_workspaces` - Project locations

---

## MCP Servers (Always Available)

- **postgres** - Database access, session logging
- **memory** - Persistent memory graph
- **filesystem** - File operations
- **tree-sitter** - Code structure analysis
- **github** - GitHub operations
- **sequential-thinking** - Complex problem solving

---

## Documentation Management

**System**: Simple 3-component system

1. **`.docs-manifest.json`** - Single source of truth for all markdown files
2. **`scripts/audit_docs.py`** - Monthly audit script
3. **Git pre-commit hook** - Enforces CLAUDE.md ≤250 lines

**Install hook:**
```bash
python scripts/install_git_hooks.py
```

**Run audit:**
```bash
python scripts/audit_docs.py
```

**Rules:**
- CLAUDE.md must stay ≤250 lines (enforced automatically)
- Deprecated docs kept for 90 days, then archived
- Audit monthly to prevent bloat

---

## Benefits

| Before | After |
|--------|-------|
| 30-60 min context reload | Auto-loads from CLAUDE.md |
| No memory across reboots | Permanent PostgreSQL storage |
| Repeated explanations | Persistent knowledge & patterns |
| Mixed work/personal projects | Clean schema separation |

---

## Troubleshooting

**Problem:** "Graph is empty" after reboot
**Solution:** Use MCP postgres tool to query shared_knowledge directly

**Problem:** Python script errors
**Solution:** Check PostgreSQL is running

**Problem:** Can't commit CLAUDE.md changes
**Solution:** CLAUDE.md exceeds 250 lines - move content to docs/ subdirectory

---

## Architecture History

- **Oct 10, 2025**: Initial 9-identity architecture with isolated workspaces
- **Oct 21, 2025**: Simplified to 2 identities with project-aware context
- **Oct 23, 2025**: Added documentation management system

See `docs/DEPRECATED_OCT10_ARCHITECTURE.md` for historical architecture.

---

## Future Enhancements

- Automatic session history recording
- Semantic search with vector embeddings
- ClaudePM integration for centralized documentation
- PostgreSQL automated backups
- Cross-Claude task handoff workflows

---

**Created:** 2025-10-10
**Last Updated:** 2025-10-23
**Location:** `C:\Projects\claude-family\`
