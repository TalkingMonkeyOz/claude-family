# Migration Guide: Isolated Workspaces v3.0

**Date**: 2025-10-17
**Purpose**: Migrate each Claude Family member to isolated workspace to prevent settings/MCP conflicts

## The Problem

Multiple Claude instances were sharing:
- `.claude\settings.local.json` in `C:\Projects\claude-family\`
- Each instance auto-saved permissions, overwriting others
- `.mcp.json` tracked in git, causing merge conflicts
- **Result**: MCP servers kept disappearing, permissions reset constantly

## The Solution

Each Claude Family member gets their own isolated workspace at `C:\claude\{member-name}\`

## Migration Steps (Per Claude Instance)

### For claude-code-console-001 ✅ COMPLETE
Already migrated to `C:\claude\claude-console-01\`

### For claude-desktop-001

1. **Create workspace**:
   ```bash
   mkdir -p C:\claude\claude-desktop-01\workspace
   mkdir -p C:\claude\claude-desktop-01\.claude
   ```

2. **Copy MCP config**:
   ```bash
   cp C:\Projects\claude-family\.mcp.json C:\claude\claude-desktop-01\.mcp.json
   ```

3. **Create settings**:
   Copy your desired permissions to `C:\claude\claude-desktop-01\.claude\settings.local.json`
   (Use the template from `C:\claude\shared\templates\` if needed)

4. **Open Claude Desktop in new workspace**:
   - Set working directory to `C:\claude\claude-desktop-01`
   - MCP servers will now use local `.mcp.json`
   - Settings will save to isolated `.claude\` directory

### For claude-cursor-001, claude-vscode-001, claude-code-001

Follow same steps as above, replacing the workspace name:
- claude-cursor-001 → `C:\claude\claude-cursor-01\`
- claude-vscode-001 → `C:\claude\claude-vscode-01\`
- claude-code-001 → `C:\claude\claude-code-01\`

## Shared Resources

All members have access to:
- `C:\claude\shared\scripts\` - Shared Python scripts
- `C:\claude\shared\docs\` - CLAUDE.md and documentation
- `C:\claude\shared\templates\` - Configuration templates

These are READ-ONLY - don't modify directly. Update git repo instead:
```bash
# Make changes in git repo
cd C:\Projects\claude-family
# Edit files, commit
git add .
git commit -m "Update shared resources"

# Copy to shared (if needed)
cp updated_file.py C:\claude\shared\scripts/
```

## Git Repository Usage

**C:\Projects\claude-family\** is now for git operations only:
- ✅ Commit changes here
- ✅ Push/pull to GitHub
- ✅ Manage version control
- ❌ Don't work directly in this directory
- ❌ Don't open Claude instances here

## After Migration

Each Claude instance:
1. Opens in their isolated workspace (`C:\claude\{name}\`)
2. Uses local `.mcp.json` (not tracked in git)
3. Saves settings to isolated `.claude\settings.local.json`
4. Works in `workspace\` subdirectory
5. **NO CONFLICTS** with other Claude instances

## Startup Workflow (Updated)

```bash
# Navigate to YOUR workspace
cd C:\claude\{your-workspace-name}

# Load startup context
python C:\claude\shared\scripts\load_claude_startup_context.py

# Check MCP servers
/mcp list

# Start working
cd workspace
```

## Checklist

For each Claude Family member:
- [ ] Create isolated workspace at `C:\claude\{name}\`
- [ ] Copy `.mcp.json` to workspace root
- [ ] Create `.claude\settings.local.json` with permissions
- [ ] Test MCP servers in new workspace
- [ ] Update startup shortcuts/scripts to open in new workspace
- [ ] Verify no conflicts with other instances

## Rollback (If Needed)

If something breaks, you can temporarily revert:
```bash
cd C:\Projects\claude-family
# Your old .mcp.json and .claude settings are still here
# (But you'll have the conflict problem again)
```

## Benefits

✅ **No More Overwrites**: Each Claude has isolated settings
✅ **No More MCP Disappearing**: Local configs, not in git
✅ **Clean Git**: No merge conflicts on config files
✅ **Shared Resources**: Scripts and docs available to all
✅ **Clear Separation**: Work vs. Git operations separate

## Questions?

Check:
- `C:\claude\claude-console-01\README.md` - Example workspace setup
- `C:\claude\shared\SHARED_RESOURCES.md` - Shared resources info
- `C:\Projects\claude-family\CLAUDE.md` - Updated family documentation

---

**Version**: 3.0.0
**Migration Lead**: claude-code-console-001
**Date**: 2025-10-17
