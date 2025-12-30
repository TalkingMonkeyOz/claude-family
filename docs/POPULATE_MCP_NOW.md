# Populate MCP Memory Graph - Run This Now in Claude Desktop

The sync scripts have run successfully and generated the JSON files. Now you need to populate the MCP memory graph in **Claude Desktop** (not here in Claude Code).

---

## Step 1: Copy this message to Claude Desktop

```
Hi! I need you to restore my persistent memory from PostgreSQL into the MCP memory graph.

Read these two files:
1. C:\Users\johnd\OneDrive\Documents\AI_projects\ZZZ_Work_nimbus\nimbus-user-loader\postgres\mcp_sync_entities.json
2. C:\Users\johnd\OneDrive\Documents\AI_projects\ZZZ_Work_nimbus\nimbus-user-loader\postgres\mcp_sync_relations.json

Then use the create_entities and create_relations MCP memory tools to populate the graph.

This will restore:
- 5 Claude identities (Desktop, Cursor, VS Code, Claude Code, Diana)
- 12 universal knowledge items (MCP logging, OneDrive caching, etc.)
- 10 collaboration relationships between Claudes

After you're done, use read_graph to verify everything was created successfully.
```

---

## Step 2: Verify it worked

In Claude Desktop, after the sync, run:

```
Use the read_graph tool to show me what's in memory now
```

You should see:
- ✅ 5 entities of type "claude_identity"
- ✅ 12 entities of type "pattern", "gotcha", or "technique"
- ✅ 10 relations of type "collaborates_with"

---

## Why This is Necessary

- **PostgreSQL** = Permanent storage (survives reboots)
- **MCP Memory Graph** = Session cache (fast but temporary)
- **This process** = Restores cache from permanent storage

Every time you reboot or start a fresh Claude Desktop session, you'll need to run:

1. `STARTUP.bat` (or `python auto_sync_startup.py`)
2. Tell Claude Desktop to read the JSON files and populate memory

---

## Automation Status

❌ **Not fully automatic yet** - Claude Desktop doesn't support startup scripts
✅ **Best current solution** - Run STARTUP.bat at session start
🔮 **Future goal** - True auto-sync when Claude Desktop adds support

---

**Current Status:** JSON files are ready, MCP graph needs populating in Claude Desktop
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/POPULATE_MCP_NOW.md
