# Windows Startup Integration - How It Works

## What Happens at Boot

When Windows starts, the Claude Family system automatically:

1. ✅ **Runs silently** in the background (minimized, no console window)
2. ✅ **Syncs PostgreSQL → JSON** files (mcp_sync_entities.json + mcp_sync_relations.json)
3. ✅ **Shows balloon notification** when ready (auto-disappears after 10 seconds)
4. ✅ **Auto-closes** (no user interaction needed)

---

## The Scripts

### Windows Startup Script
**Location:** `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Claude-Family-Startup.bat`

```batch
@echo off
REM Runs minimized, shows balloon notification, auto-closes
start /min cmd /c "C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\STARTUP_SILENT.bat"
```

### Silent Startup Script
**Location:** `claude-family/STARTUP_SILENT.bat`

```batch
@echo off
cd /d "%~dp0scripts"

REM Run the sync (silent)
python auto_sync_startup.py > NUL 2>&1

REM Show balloon notification
powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\show_startup_balloon.ps1"

REM Auto-close
exit
```

### Balloon Notification Script
**Location:** `claude-family/scripts/show_startup_balloon.ps1`

Shows a Windows balloon notification with:
- 🤖 Identity: claude-desktop-001
- 📚 Knowledge: Loaded
- 📋 Sessions: Ready
- ✅ Context restored successfully!

---

## What You Still Need To Do

**After Windows boots and you open Claude Desktop:**

The JSON sync files are ready, but you must manually tell Claude Desktop to import them into MCP memory:

```
Hi! I just rebooted and need to restore my Claude Family memory.

Please read these two files:
1. C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data\mcp_sync_entities.json
2. C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data\mcp_sync_relations.json

Then use the create_entities MCP memory tool to add all the entities from file 1,
and use the create_relations MCP memory tool to add all the relations from file 2.

After you're done, use read_graph to verify everything was imported.
```

---

## Why Not Fully Automatic?

**MCP memory tools can only be called BY Claude, not BY external scripts.**

So the workflow is:
1. **Windows boots** → STARTUP_SILENT.bat runs automatically ✅
2. **Sync completes** → Balloon notification shows ✅
3. **You open Claude Desktop** → Graph is empty (expected)
4. **You tell Claude** → "Import the sync files" (manual step) ⚠️
5. **Claude imports** → Graph is now populated ✅

This is a limitation of the MCP architecture.

---

## Verification

### Check the startup script ran:
```bash
dir C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\logs
```

You should see a recent `startup_context_claude-desktop-001_*.txt` file.

### Check the JSON files exist:
```bash
dir C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data
```

You should see:
- `mcp_sync_entities.json` (updated today)
- `mcp_sync_relations.json` (updated today)

---

## Disable Auto-Startup

If you want to disable the automatic startup:

**Option 1: Delete the startup script**
```bash
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Claude-Family-Startup.bat"
```

**Option 2: Disable in Task Manager**
1. Press `Ctrl+Shift+Esc`
2. Go to "Startup" tab
3. Find "Claude-Family-Startup"
4. Right-click → Disable

---

## Manual Run (Alternative)

If you prefer to run it manually:

**Option 1: With pause (see output)**
```
C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\STARTUP.bat
```

**Option 2: Silent (balloon notification only)**
```
C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\STARTUP_SILENT.bat
```

---

## Troubleshooting

**Problem:** No balloon notification appears
**Solution:** Check if the script ran by looking for today's log file in `logs/`

**Problem:** Balloon says "file not found"
**Solution:** Run STARTUP.bat manually to see the full error

**Problem:** OneDrive caching issues
**Solution:** Unpin the data directory:
```bash
attrib -P "C:\Users\johnd\OneDrive\Documents\AI_projects\claude-family\postgres\data" /S /D
```

---

**Summary:** The startup integration works perfectly - it just can't automatically import into Claude Desktop's MCP memory. That one step requires you to ask Claude to do it.
