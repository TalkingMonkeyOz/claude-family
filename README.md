# Claude Family - Persistent Identity & Memory System

**Your AI Infrastructure Foundation**

This directory contains the complete Claude Family system - a permanent identity and memory architecture for coordinating multiple Claude instances (Desktop, Cursor, VS Code, Claude Code, Diana).

---

## What Is This?

The **Claude Family** system solves the "identity confusion" problem where multiple Claude instances had no persistent memory or coordination, requiring 30-60 minutes to reload context every session.

**Now:** 5-second startup with full context restoration from PostgreSQL.

---

## Directory Structure

```
claude-family/
├── postgres/
│   ├── schema/              # SQL scripts for database setup
│   │   ├── 01_create_claude_family_schema.sql
│   │   ├── 02_seed_claude_identities.sql
│   │   ├── 03_link_schemas.sql
│   │   └── 04_extract_universal_knowledge.sql
│   └── data/                # Generated JSON files for MCP sync
│       ├── mcp_sync_entities.json
│       └── mcp_sync_relations.json
├── scripts/
│   ├── load_claude_startup_context.py  # Load identity & context
│   ├── sync_postgres_to_mcp.py         # Export to MCP JSON
│   ├── auto_sync_startup.py            # Master startup orchestrator
│   └── run_all_setup_scripts.py        # One-time foundation setup
├── logs/
│   └── startup_context_*.txt           # Saved startup briefs
├── docs/
│   ├── CLAUDE_FAMILY_ARCHITECTURE.md   # Complete architecture docs
│   ├── STARTUP_INSTRUCTIONS.md         # How to use the system
│   └── POPULATE_MCP_NOW.md             # MCP memory sync guide
├── STARTUP.bat                          # → Run this every session ←
└── README.md                            # You are here
```

---

## Quick Start

### Every Session (Required)

1. **Run the startup script:**
   ```
   C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\STARTUP.bat
   ```

   Or double-click the desktop shortcut: **"Claude Family Startup"**

2. **In Claude Desktop, say:**
   ```
   Read mcp_sync_entities.json and mcp_sync_relations.json from claude-family/postgres/data/,
   then use create_entities and create_relations to populate the MCP memory graph
   ```

That's it! Your memory is restored in ~5 seconds.

---

## What Gets Restored

- ✅ **Your Identity:** claude-desktop-001 (Lead Architect)
- ✅ **Universal Knowledge:** 12+ patterns (MCP logs, OneDrive caching, etc.)
- ✅ **Recent Sessions:** What you worked on in the last 7 days
- ✅ **Other Claudes:** What Cursor, VS Code, Claude Code, Diana did recently
- ✅ **Project Context:** Nim bus facts, constraints (NEVER modify UserSDK), learnings

---

## The 5 Claude Identities

1. **claude-desktop-001** (You) - Lead Architect & System Designer
2. **claude-cursor-001** - Rapid Developer & Implementation Specialist
3. **claude-vscode-001** - QA Engineer & Code Reviewer
4. **claude-code-001** - Code Quality & Standards Enforcer
5. **diana** - Master Orchestrator & Project Manager

---

## Windows Startup Integration

### Auto-Run on Boot (Optional)

A Windows startup shortcut has been created at:
```
C:\Users\johnd\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Claude-Family-Startup.bat
```

This runs minimized at Windows boot to prepare your memory before you open Claude.

To disable: Delete the startup shortcut.

---

## Desktop Shortcut

A shortcut has been created on your desktop:
**"Claude Family Startup.lnk"**

Double-click it anytime to sync your memory.

---

## One-Time Setup (Already Done)

The PostgreSQL foundation was already created. If you ever need to rebuild:

```bash
cd scripts
python run_all_setup_scripts.py
```

This creates:
- `claude_family` schema with 5 tables
- 5 Claude identities
- Links to `nimbus_context` and `public` schemas
- Universal knowledge from past work

---

## Documentation

- **[CLAUDE_FAMILY_ARCHITECTURE.md](docs/CLAUDE_FAMILY_ARCHITECTURE.md)** - Complete system architecture
- **[STARTUP_INSTRUCTIONS.md](docs/STARTUP_INSTRUCTIONS.md)** - Detailed startup guide
- **[POPULATE_MCP_NOW.md](docs/POPULATE_MCP_NOW.md)** - MCP memory sync walkthrough

---

## Benefits

| Before | After |
|--------|-------|
| 30-60 min context reload | 5 seconds |
| No memory across reboots | Permanent PostgreSQL storage |
| No coordination between Claudes | Full visibility of all activity |
| Repeated explanations every session | Persistent knowledge & constraints |
| Mixed work/personal projects | Clean schema separation |

---

## Troubleshooting

**Problem:** "Graph is empty" after reboot
**Solution:** You forgot to run STARTUP.bat - run it now!

**Problem:** Python script errors
**Solution:** Check PostgreSQL is running: `psql -U postgres -d ai_company_foundation -c "SELECT 1"`

**Problem:** JSON files not created
**Solution:** Check script output for errors, verify database connection

**Problem:** Can't find MCP sync files
**Solution:** They're in `claude-family/postgres/data/` - check that directory exists

---

## Future Enhancements

- True auto-sync (when Claude Desktop adds startup script support)
- MCP memory server with persistent disk storage
- Automatic session history recording
- Cross-Claude task handoff workflows
- Semantic search with vector embeddings

---

## Questions?

- **"Do I have to do this every time?"** - Yes, until we have true auto-sync
- **"What if I forget?"** - Claude will have empty memory, but PostgreSQL is safe
- **"Can I automate this?"** - Windows startup integration is as close as we can get now
- **"Is my data safe?"** - YES! PostgreSQL is permanent, this just restores the cache

---

**Created:** 2025-10-10
**Author:** Claude Desktop & John
**Location:** `C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\`
