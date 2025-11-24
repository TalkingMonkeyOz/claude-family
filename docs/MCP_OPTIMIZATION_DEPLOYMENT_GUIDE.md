# MCP Optimization Deployment Guide - Option A

**Date**: 2025-11-04
**Status**: Ready to Deploy
**Option**: Conservative (keep tree-sitter for testing)

---

## What Was Created

### Configuration Files (in `configs/`)

1. **global-mcp-optimized.json** → Deploy to `~/.claude/mcp.json`
   - Core MCPs: postgres, memory, filesystem, sequential-thinking
   - Token cost: ~22,609 tokens
   - Used by: ALL Claude instances

2. **nimbus-mcp-optimized.json** → Deploy to `C:/Projects/nimbus-user-loader/.mcp.json`
   - Adds: roslyn, flaui-testing, tree-sitter
   - Additional tokens: ~23,357
   - Total: ~45,966 tokens (was 70k = **34% savings**)

3. **claudepm-mcp-optimized.json** → Deploy to `C:/Projects/claude-pm/.mcp.json`
   - Adds: roslyn, flaui-testing, tree-sitter
   - Additional tokens: ~23,357
   - Total: ~45,966 tokens (was 70k = **34% savings**)

4. **ato-mcp-optimized.json** → Deploy to `C:/Projects/ATO-Tax-Agent/.mcp.json`
   - Adds: playwright, tree-sitter
   - Additional tokens: ~23,627
   - Total: ~46,236 tokens (was 70k = **34% savings**)

5. **claude-family-mcp-optimized.json** → Deploy to `C:/Projects/claude-family/.mcp.json`
   - Adds: github, tree-sitter
   - Additional tokens: ~36,050
   - Total: ~58,659 tokens (was 70k = **16% savings**)

---

## What Was Removed (Per Project)

### Nimbus & Claude PM (C# Projects)
- ❌ **github** (18,123 tokens) - Use `gh` CLI instead
- ❌ **py-notes-server** (4,251 tokens) - Not actively used
- ❌ **context7** (1,709 tokens) - Use WebSearch instead
- **Total removed**: 24,083 tokens

### ATO (Web Research)
- ❌ **github** (18,123 tokens)
- ❌ **py-notes-server** (4,251 tokens)
- ❌ **context7** (1,709 tokens)
- ❌ **roslyn** (1,902 tokens) - No C# in this project
- ❌ **flaui-testing** (3,528 tokens) - No UI testing
- **Total removed**: 29,513 tokens

### Claude-Family (Infrastructure)
- ❌ **py-notes-server** (4,251 tokens)
- ❌ **context7** (1,709 tokens)
- ❌ **roslyn** (1,902 tokens)
- ❌ **flaui-testing** (3,528 tokens)
- ❌ **playwright** (5,700 tokens)
- **Total removed**: 17,090 tokens

---

## What Was KEPT for Testing (Option A)

**tree-sitter** (17,927 tokens) - kept in ALL projects to test if actually needed

**Reason**: You mentioned "you do all the coding" - need to verify I actually use tree-sitter's 26 tools for C# projects where Roslyn provides semantic analysis.

**Next Step**: After 1 week, if tree-sitter unused → Option B (remove it, save another 18k tokens)

---

## Expected Results

### Token Savings (Option A)

| Instance | Current | Optimized | Savings | % Reduction |
|----------|---------|-----------|---------|-------------|
| Nimbus | 70,000 | 45,966 | 24,034 | 34% |
| Claude PM | 70,000 | 45,966 | 24,034 | 34% |
| ATO | 70,000 | 46,236 | 23,764 | 34% |
| claude-family | 70,000 | 58,659 | 11,341 | 16% |
| **Average** | **70,000** | **49,207** | **20,793** | **30%** |

### Context Window Impact (Nimbus Example)

**Before**:
```
Total context: 247k/200k (123% - OVER LIMIT)
MCP tools: 70k tokens (35%)
Autocompact buffer: 45k tokens (fighting to stay under)
```

**After**:
```
Total context: ~202k/200k (101% - still over but closer)
MCP tools: 46k tokens (23%)
Autocompact buffer: ~21k tokens (reduced pressure)
```

**Need further reduction**: Even with Option A, you're still slightly over. Option B (remove tree-sitter) will get you under the limit.

---

## Deployment Instructions

### Pre-Deployment Checklist

- [ ] **Close ALL Claude instances** (Nimbus, Claude PM, ATO, Claude Desktop, console)
- [ ] Verify backups directory exists: `C:/Projects/claude-family/backups/mcp-configs/`
- [ ] Read this guide completely

### Option 1: Automated Deployment (Recommended)

```bash
cd C:/Projects/claude-family

# Dry run first (validates without deploying)
python scripts/deploy_optimized_mcps.py --dry-run

# If validation passes, deploy for real
python scripts/deploy_optimized_mcps.py
```

Script will:
1. Backup existing configs to `backups/mcp-configs/`
2. Validate JSON syntax
3. Deploy optimized configs
4. Log deployment to PostgreSQL

### Option 2: Manual Deployment

```bash
# Backup existing
cp ~/.claude/mcp.json ~/.claude/mcp.json.backup.20251104

# Deploy global config (remove comments manually)
# Copy mcpServers section from configs/global-mcp-optimized.json to ~/.claude/mcp.json

# Deploy project configs
cp configs/nimbus-mcp-optimized.json C:/Projects/nimbus-user-loader/.mcp.json
cp configs/claudepm-mcp-optimized.json C:/Projects/claude-pm/.mcp.json
cp configs/ato-mcp-optimized.json C:/Projects/ATO-Tax-Agent/.mcp.json
cp configs/claude-family-mcp-optimized.json C:/Projects/claude-family/.mcp.json

# Remove _comment fields from JSON files (they're invalid JSON)
```

---

## Post-Deployment Verification

### Step 1: Restart Claude Instances

Start ONE instance at a time to verify:

```bash
# Start Nimbus
cd C:/Projects/nimbus-user-loader
claude
```

### Step 2: Verify MCPs Loaded

```
/mcp list
```

**Expected for Nimbus**:
- ✅ postgres (from global)
- ✅ memory (from global)
- ✅ filesystem (from global)
- ✅ sequential-thinking (from global)
- ✅ roslyn (from project)
- ✅ flaui-testing (from project)
- ✅ tree-sitter (from project)
- ❌ github (removed)
- ❌ py-notes-server (removed)
- ❌ context7 (removed)

### Step 3: Check Token Usage

```
/context
```

**Expected for Nimbus**:
- MCP tools: ~46k tokens (down from 70k)
- Total context: ~202k/200k (down from 247k)

### Step 4: Test Functionality

**Coding workflow**:
1. Ask me to write C# code → should work (roslyn available)
2. Ask me to test UI → should work (flaui available)
3. Ask me to analyze project structure → should work (tree-sitter available)

**Removed functionality**:
4. Ask me to create GitHub PR → I should use `gh` CLI via Bash
5. Ask me to look up library docs → I should use WebSearch
6. Ask me to read Obsidian notes → I should use Read tool for local files

---

## Rollback Procedure

If something breaks:

```bash
# Restore from backup (automated deployment)
cp C:/Projects/claude-family/backups/mcp-configs/mcp_20251104_*.json ~/.claude/mcp.json

# Or restore manual backup
cp ~/.claude/mcp.json.backup.20251104 ~/.claude/mcp.json

# Restart Claude instances
```

---

## Monitoring Plan (Week 1)

### Daily Check

Each day for 1 week, note if I:
- ✅ Struggled to do something I normally do easily
- ✅ Asked for a tool that wasn't available
- ✅ Complained about missing MCPs

### End of Week Questions

1. Did I use tree-sitter at all? (Check /context for usage)
2. Did I miss github, py-notes, or context7?
3. Did context window pressure improve?

### If All Good → Proceed to Option B

Remove tree-sitter from C# projects (save another 18k tokens):
- Nimbus: 46k → 28k tokens
- Claude PM: 46k → 28k tokens
- Total with Option B: ~28k average (60% total reduction)

---

## Cost Savings Projection

### Option A (Current)

**Token savings**: ~21k tokens/session average
**Sessions/day**: 10 (estimated)
**Monthly tokens saved**: 6.3M
**Cost savings**: ~$378/month @ $0.06 per 1k output tokens

### Option B (If tree-sitter removed)

**Token savings**: ~38k tokens/session average
**Sessions/day**: 10
**Monthly tokens saved**: 11.4M
**Cost savings**: ~$684/month

---

## Next Steps

1. **Deploy Option A** using deployment script
2. **Verify** all instances load correctly
3. **Monitor** for 1 week (note any missing tools)
4. **Analyze** tree-sitter usage in /context output
5. **Decide**: Proceed to Option B or keep tree-sitter

---

## Questions & Troubleshooting

### Q: What if I need GitHub during coding?

Use `gh` CLI via Bash:
```bash
gh pr create --title "Feature" --body "Description"
gh issue create --title "Bug" --body "Details"
```

### Q: What if I need library docs?

Use WebSearch:
```bash
WebSearch("C# HttpClient best practices 2025")
```

Or WebFetch specific docs:
```bash
WebFetch("https://learn.microsoft.com/en-us/dotnet/api/...")
```

### Q: What if context still over limit after Option A?

Proceed immediately to Option B (remove tree-sitter). You need to get under 200k urgently.

### Q: How do I know if tree-sitter is being used?

Run `/context` and check if any `mcp__tree-sitter__*` tools appear in the usage list. If none listed after 1 week of coding → safe to remove.

---

**Ready to deploy?** Run `python scripts/deploy_optimized_mcps.py --dry-run` to test first.
