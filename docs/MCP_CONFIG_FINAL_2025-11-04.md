# Final Corrected MCP Configuration - 2025-11-04

**Status**: ✅ **READY FOR TESTING**
**Action Required**: Restart all Claude sessions to load new config

---

## What Was Fixed (Round 2)

### Problem Discovered
After fixing the missing core MCPs, user discovered:
- **ATO** had roslyn loaded (shouldn't - it's web-based, not C#)
- **claude-family** looked "lean" (needed verification)

### Root Cause
Roslyn and context7 were in the **global config** (`~/.claude.json`), causing them to load for ALL projects regardless of whether they needed them.

### Solution Applied
**Removed from global config:**
- ❌ roslyn (C#-specific, not needed globally)
- ❌ context7 (not needed globally)

**Global config now contains ONLY core MCPs:**
- ✅ postgres
- ✅ memory
- ✅ filesystem
- ✅ sequential-thinking

---

## Final Configuration Per Project

### Global MCPs (`~/.claude.json`)
**Always loaded for all projects:**

| MCP | Purpose | Tokens |
|-----|---------|--------|
| postgres | Database access, session logging | ~6,175 |
| memory | Persistent knowledge graph | ~5,713 |
| filesystem | File operations | ~9,221 |
| sequential-thinking | Complex problem solving | ~1,500 |

**Total Global**: ~22,609 tokens

---

### Nimbus (C# WinForms)

**Working Directory**: `C:/Projects/nimbus-user-loader`

**Project MCPs** (`.mcp.json`):
- roslyn (~1,902 tokens) - C# semantic analysis
- flaui-testing (~3,528 tokens) - WinForms UI testing

**Total MCPs when running in Nimbus**:
- Global: postgres, memory, filesystem, sequential-thinking (~22,609)
- Project: roslyn, flaui-testing (~5,430)
- **Total: ~28,039 tokens** (60% reduction from original 70k)

---

### Claude PM (C# WPF)

**Working Directory**: `C:/Projects/claude-pm`

**Project MCPs** (`.mcp.json`):
- roslyn (~1,902 tokens) - C# semantic analysis
- flaui-testing (~3,528 tokens) - WPF UI testing

**Total MCPs when running in Claude PM**:
- Global: postgres, memory, filesystem, sequential-thinking (~22,609)
- Project: roslyn, flaui-testing (~5,430)
- **Total: ~28,039 tokens** (60% reduction from original 70k)

---

### ATO Tax Agent (Web Research)

**Working Directory**: `C:/Projects/ATO-Tax-Agent`

**Project MCPs** (`.mcp.json`):
- playwright (~5,700 tokens) - Browser automation
- tree-sitter (~17,927 tokens) - Multi-language code analysis

**Total MCPs when running in ATO**:
- Global: postgres, memory, filesystem, sequential-thinking (~22,609)
- Project: playwright, tree-sitter (~23,627)
- **Total: ~46,236 tokens** (34% reduction from original 70k)

**Fixed**: No longer loads roslyn (was loading due to global config bug)

---

### claude-family (Infrastructure)

**Working Directory**: `C:/Projects/claude-family`

**Project MCPs** (`.mcp.json`):
- github (~18,123 tokens) - GitHub operations
- tree-sitter (~17,927 tokens) - Multi-language code analysis

**Total MCPs when running in claude-family**:
- Global: postgres, memory, filesystem, sequential-thinking (~22,609)
- Project: github, tree-sitter (~36,050)
- **Total: ~58,659 tokens** (16% reduction from original 70k)

**Fixed**: No longer loads roslyn (was loading due to global config bug)

---

## Token Savings Summary

| Project | Before | After | Savings | % Reduction |
|---------|--------|-------|---------|-------------|
| **Nimbus** | 70,000 | 28,039 | 41,961 | 60% |
| **Claude PM** | 70,000 | 28,039 | 41,961 | 60% |
| **ATO** | 70,000 | 46,236 | 23,764 | 34% |
| **claude-family** | 70,000 | 58,659 | 11,341 | 16% |
| **Average** | 70,000 | 40,243 | 29,757 | 42.5% |

---

## How MCP Loading Works

**Configuration Hierarchy:**

1. **Global Config** (`~/.claude.json` mcpServers section)
   - Loaded first
   - Available in ALL projects
   - Use for tools needed everywhere (postgres, memory, filesystem, etc.)

2. **Project Config** (`.mcp.json` in current working directory)
   - Loaded second
   - Merged with global
   - Adds project-specific tools
   - If same MCP name exists in both, PROJECT wins (overrides global)

**Example: Starting Claude in Nimbus**
```bash
cd C:/Projects/nimbus-user-loader
claude
```

**MCPs loaded:**
- From global: postgres, memory, filesystem, sequential-thinking
- From project: roslyn, flaui-testing
- Total: 6 MCPs, ~28k tokens

**Example: Starting Claude in ATO**
```bash
cd C:/Projects/ATO-Tax-Agent
claude
```

**MCPs loaded:**
- From global: postgres, memory, filesystem, sequential-thinking
- From project: playwright, tree-sitter
- Total: 6 MCPs, ~46k tokens
- **NO roslyn** (not in global anymore, not in ATO project config)

---

## Testing Instructions

### 1. Restart All Claude Sessions

**CRITICAL**: Configuration changes only take effect on new sessions!

```bash
# If you have any Claude sessions open, exit them
exit

# Then restart in the project you want to work on
cd C:/Projects/nimbus-user-loader  # or ATO, claude-pm, claude-family
claude
```

### 2. Verify MCPs Loaded Correctly

```
/mcp list
```

**Expected Output for Nimbus/Claude PM:**
```
Global MCPs:
✓ postgres
✓ memory
✓ filesystem
✓ sequential-thinking

Project MCPs:
✓ roslyn
✓ flaui-testing
```

**Expected Output for ATO:**
```
Global MCPs:
✓ postgres
✓ memory
✓ filesystem
✓ sequential-thinking

Project MCPs:
✓ playwright
✓ tree-sitter

NOT EXPECTED (should be gone):
✗ roslyn
✗ context7
```

**Expected Output for claude-family:**
```
Global MCPs:
✓ postgres
✓ memory
✓ filesystem
✓ sequential-thinking

Project MCPs:
✓ github
✓ tree-sitter

NOT EXPECTED (should be gone):
✗ roslyn
✗ context7
```

### 3. Check Token Usage

```
/context
```

**Expected:**
- MCP tools should match the "Total" in the summary table above
- Total context should be significantly reduced
- No more autocompact warnings in most projects

### 4. Test Functionality

**All Projects** (core MCPs should work everywhere):
```
"Log this session to the database"
→ Should use postgres MCP

"Remember that we optimized MCPs today"
→ Should use memory MCP

"Read the README.md file"
→ Should use filesystem MCP or Read tool
```

**C# Projects** (Nimbus, Claude PM):
```
"Validate the C# code in this file"
→ Should use roslyn MCP

"Test the login form UI"
→ Should use flaui-testing MCP
```

**ATO Project**:
```
"Navigate to https://ato.gov.au and extract the title"
→ Should use playwright MCP

"Analyze the JavaScript in this HTML file"
→ Should use tree-sitter MCP

"Validate C# code"
→ Should fail or fall back to tree-sitter (NO roslyn)
```

**claude-family Project**:
```
"Create a PR for this branch"
→ Should use github MCP

"Analyze the Python script structure"
→ Should use tree-sitter MCP

"Validate C# code"
→ Should fail or fall back to tree-sitter (NO roslyn)
```

---

## Rollback Procedure

If anything breaks:

```bash
# Restore global config
cp ~/.claude.json.backup.20251104_EMERGENCY ~/.claude.json

# Restart Claude
```

---

## Files Modified

**Global Config:**
- `C:/Users/johnd/.claude.json` - mcpServers section (lines 227-292)
  - Removed: roslyn, context7
  - Kept: postgres, memory, filesystem, sequential-thinking

**Project Configs** (unchanged - already correct):
- `C:/Projects/nimbus-user-loader/.mcp.json`
- `C:/Projects/claude-pm/.mcp.json`
- `C:/Projects/ATO-Tax-Agent/.mcp.json`
- `C:/Projects/claude-family/.mcp.json`

**Backups Created:**
- `~/.claude.json.backup.20251104_EMERGENCY`
- `~/.claude.json.backup.edit`

---

## What About context7?

**Removed from global** because:
- Not used frequently enough to justify loading in all projects
- Saves ~1,709 tokens globally
- Can be added to specific project configs if needed

**If you want context7 back:**

Add to a specific project's `.mcp.json`:
```json
{
  "mcpServers": {
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@upstash/context7-mcp"],
      "env": {}
    }
  }
}
```

Or add back to global if used frequently across all projects.

---

## Next Steps

### Immediate
1. ✅ Restart all Claude sessions
2. ✅ Test with `/mcp list` in each project
3. ✅ Verify with `/context` that tokens are reduced
4. ✅ Test functionality in each project

### This Week (Monitoring)
- Track if any project complains about missing tools
- Track if any project still hits context limits
- Track if ATO/claude-family ever need roslyn (they shouldn't)

### Phase 2 (Next Week - if still needed)
- Hybrid MCP Orchestrator for on-demand agent spawning
- Move specialized work to isolated agents
- Target: ~23k token average across all projects

---

**CONFIGURATION FIXED** ✅

All projects now have correct, optimized MCP configurations.

**Restart required to activate!**
