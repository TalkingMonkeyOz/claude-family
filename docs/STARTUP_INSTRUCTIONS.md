# Claude Family Startup Instructions

## The Problem

After a reboot or new Claude Desktop session, the MCP memory graph is empty (it doesn't persist to disk). However, your **PostgreSQL database is permanent** and contains all your identities, knowledge, and session history.

## The Solution

**Two-step startup process** to sync PostgreSQL → MCP memory every session:

---

## Quick Start (Every Session)

### Option 1: Automated (Recommended)

1. **Run the startup batch file:**
   ```
   C:\Users\johnd\OneDrive\Documents\AI_projects\ZZZ_Work_nimbus\nimbus-user-loader\postgres\STARTUP.bat
   ```

2. **Tell Claude Desktop:**
   ```
   Read the MCP sync files and populate the memory graph
   ```

   Claude will read `mcp_sync_entities.json` and `mcp_sync_relations.json` and use the MCP memory tools to restore your persistent memory.

### Option 2: Manual

1. **Run Python script directly:**
   ```bash
   cd C:\Users\johnd\OneDrive\Documents\AI_projects\ZZZ_Work_nimbus\nimbus-user-loader\postgres
   python auto_sync_startup.py
   ```

2. **Tell Claude Desktop:**
   ```
   Read mcp_sync_entities.json and mcp_sync_relations.json, then use create_entities and create_relations to populate the MCP memory graph
   ```

---

## What Happens Behind the Scenes

1. **`auto_sync_startup.py`** runs two sub-scripts:
   - **`load_claude_startup_context.py`**: Loads your identity, knowledge, and recent sessions from PostgreSQL and prints a startup brief
   - **`sync_postgres_to_mcp.py`**: Exports PostgreSQL data to JSON files for MCP import

2. **JSON files created:**
   - `mcp_sync_entities.json`: All Claude identities and knowledge items
   - `mcp_sync_relations.json`: Relationships between Claudes (who collaborates with whom)

3. **Claude Desktop reads the JSON** and calls MCP memory tools:
   - `create_entities`: Adds 17 entities (5 identities + 12 knowledge items)
   - `create_relations`: Links them together (10 collaboration relationships)

4. **Result:** Your MCP memory graph is now populated from PostgreSQL!

---

## Files Explained

| File | Purpose |
|------|---------|
| **STARTUP.bat** | Batch file to run at session start (calls Python script) |
| **auto_sync_startup.py** | Master script - runs both context loader and MCP sync |
| **load_claude_startup_context.py** | Loads and prints your identity, knowledge, sessions from PostgreSQL |
| **sync_postgres_to_mcp.py** | Exports PostgreSQL data to JSON files for MCP import |
| **mcp_sync_entities.json** | Generated: All entities for MCP memory graph |
| **mcp_sync_relations.json** | Generated: All relationships for MCP memory graph |
| **startup_context_{identity}_{timestamp}.txt** | Generated: Saved copy of your startup brief |

---

## Future Enhancement: True Auto-Sync

Unfortunately, Claude Desktop doesn't support running scripts automatically at startup yet.

**Possible future solutions:**
1. **MCP memory server with persistent storage** - Configure it to save to disk (if supported in future versions)
2. **Windows scheduled task** - Run the sync script when Claude Desktop process starts
3. **Wrapper application** - Launch Claude Desktop via a wrapper that runs sync first
4. **Claude Desktop feature request** - Ask Anthropic to add startup script support

For now, **manually running STARTUP.bat** at the beginning of each session is the best approach.

---

## Testing

Test the sync right now:

```bash
cd C:\Users\johnd\OneDrive\Documents\AI_projects\ZZZ_Work_nimbus\nimbus-user-loader\postgres
python auto_sync_startup.py
```

Then tell Claude Desktop:
```
Read mcp_sync_entities.json and create all entities in the memory graph
```

Verify with:
```
Use the read_graph tool to show me what's in the memory graph now
```

You should see all 5 Claude identities and 12 knowledge items!

---

## Benefits

✅ **5-second context restore** vs 30-60 minutes of re-explaining
✅ **PostgreSQL is permanent** - survives reboots, crashes, everything
✅ **MCP memory is session cache** - fast access during conversation
✅ **Best of both worlds** - persistent storage + fast retrieval

---

## Troubleshooting

**Problem:** "Graph is empty" after reboot
**Solution:** You forgot to run STARTUP.bat - run it now!

**Problem:** Python script errors
**Solution:** Check PostgreSQL is running: `psql -U postgres -d ai_company_foundation -c "SELECT 1"`

**Problem:** JSON files not created
**Solution:** Check script output for errors, verify database connection in config.py

**Problem:** MCP memory tools not working
**Solution:** Check `%APPDATA%\Claude\logs\mcp-server-memory.log` for errors

---

## Questions?

- **"Do I have to do this every time?"** - Yes, until we have true auto-sync
- **"What if I forget?"** - Claude will have empty memory, but PostgreSQL is safe
- **"Can I automate this?"** - Not easily with current Claude Desktop limitations
- **"Is my data safe?"** - YES! PostgreSQL is permanent, this just restores the cache

---

**Created:** 2025-10-10
**Author:** Claude Desktop & John
**Last Updated:** 2025-10-10
