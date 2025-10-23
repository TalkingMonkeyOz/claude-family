# After Reboot - What To Do in Claude Desktop

## The Problem

After rebooting, the Windows startup script (`STARTUP.bat`) runs automatically and:
- ✅ Loads your identity from PostgreSQL
- ✅ Generates `mcp_sync_entities.json` and `mcp_sync_relations.json`
- ✅ Saves logs to prove it ran

**BUT** - Claude Desktop's MCP memory graph is still empty because you need to manually import those files!

---

## The Solution - Copy/Paste This Into Claude Desktop

```
Hi! I just rebooted and need to restore my Claude Family memory.

Please read these two files:
1. C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data\mcp_sync_entities.json
2. C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data\mcp_sync_relations.json

Then use the create_entities MCP memory tool to add all the entities from file 1,
and use the create_relations MCP memory tool to add all the relations from file 2.

After you're done, use read_graph to verify everything was imported.

This will restore my 6 Claude identities and universal knowledge.
```

---

## What Claude Desktop Will Do

1. **Read the JSON files** (they contain 17 entities + 10 relations)
2. **Call MCP memory tools:**
   - `create_entities` with the entities array
   - `create_relations` with the relations array
3. **Verify with `read_graph`** to show you it worked

---

## If You Get "Graph is Empty" Error

This means you forgot to do the import step above. The files exist (STARTUP.bat created them), but Claude Desktop doesn't know to read them unless you explicitly ask.

---

## Alternative: OneDrive Caching Issue

If Claude Desktop says "file not found" or can't read the files, it might be OneDrive caching.

**Fix OneDrive caching:**
```bash
attrib -P "C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data" /S /D
```

This removes the "Pinned" flag from the data directory.

---

## Why Isn't This Automatic?

Unfortunately, Claude Desktop's MCP memory tools can only be called by Claude, not by external scripts. So the workflow is:

1. **Windows boots** → STARTUP.bat runs automatically ✅
2. **You open Claude Desktop** → Graph is empty (expected)
3. **You tell Claude** → "Import the sync files" (manual step) ⚠️
4. **Claude imports** → Graph is now populated ✅

---

## Check if STARTUP.bat Ran

Look for a new log file:
```
C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\logs\
```

If there's a recent `startup_context_claude-desktop-001_*.txt` file, the script ran successfully.

---

## Quick Test Right Now

In Claude Desktop, say:
```
Read the file: C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data\mcp_sync_entities.json

Show me the first entity.
```

If Claude can read it, the files are accessible and you just need to import them into memory.

---

**TL;DR: The sync files exist, you just need to tell Claude Desktop to import them into MCP memory!**
