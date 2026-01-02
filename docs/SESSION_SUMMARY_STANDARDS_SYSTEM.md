# Session Summary: Database-Driven Coding Standards System

**Date**: 2026-01-02
**Session ID**: 9c82ae44-2b48-4bbc-9c47-6aeb8215e160
**Status**: Phase 1-2 Complete, Testing Shows Migration Needed

---

## Executive Summary

Successfully implemented a complete, centralized coding standards system using:
- Database-driven standards (`claude.coding_standards` table)
- Auto-generation to `~/.claude/standards/`
- CLAUDE.md @import integration for awareness
- Block-and-correct PreToolUse validation (replaces broken additionalContext injection)

**Test Result**: Created 504-line file successfully, proving OLD hook still active. New validation requires session restart.

---

## What Was Built

### 1. Database Infrastructure ✅

**Table**: `claude.coding_standards`
- Categories: core, language, framework, pattern
- Pattern matching: `applies_to_patterns` (glob patterns)
- Validation rules: JSONB for max_lines, forbidden_patterns, etc.
- 7 standards total (1 core + 3 language + 2 framework + README)

**Script**: `scripts/generate_standards.py`
- Reads from database
- Generates `~/.claude/standards/` directory structure
- Self-healing (regenerates on SessionStart)

### 2. Standards Added (from GitHub Copilot Awesome) ✅

| Standard | File | Patterns | Key Rules |
|----------|------|----------|-----------|
| Markdown Docs | core/markdown-documentation.md | **/*.md | Max 300 lines (detailed), 150 (quick-ref), 100 (working) |
| C# | language/csharp.md | **/*.cs | PascalCase, async patterns, XML comments |
| TypeScript | language/typescript.md | **/*.ts, **/*.tsx | No `any`, async/await, security |
| Rust | language/rust.md | **/*.rs | Ownership, Result<T,E>, rustfmt/clippy |
| React | framework/react.md | **/*.tsx, **/*.jsx | Hooks, dependency arrays, memoization |
| MUI | framework/mui.md | **/*.tsx, **/*.jsx | Theming, sx prop, responsive design |

**Sources**:
- [GitHub Copilot Awesome](https://github.com/github/awesome-copilot)
- [C# Instructions](https://github.com/github/awesome-copilot/blob/main/instructions/csharp.instructions.md)
- [TypeScript 5/ES2022](https://github.com/github/awesome-copilot/blob/main/instructions/typescript-5-es2022.instructions.md)
- [React](https://github.com/github/awesome-copilot/blob/main/instructions/reactjs.instructions.md)
- [Rust](https://github.com/github/awesome-copilot/blob/main/instructions/rust.instructions.md)

### 3. Enforcement System (Block-and-Correct) ✅

**New**: `scripts/standards_validator.py`
- PreToolUse hook for Write/Edit operations
- Validates BEFORE file creation
- Exit code 2 + stderr = Claude sees error, adjusts, retries
- Database-driven validation rules

**Replaced**: `scripts/instruction_matcher.py` (tried additionalContext injection - didn't work)

**Hook Configuration Updated** in `claude.config_templates`:
```json
{
  "PreToolUse": [
    {
      "matcher": "Write",
      "hooks": [{
        "type": "command",
        "command": "python \"C:/Projects/claude-family/scripts/standards_validator.py\"",
        "timeout": 10
      }]
    }
  ]
}
```

### 4. CLAUDE.md @import Integration ✅

Updated files:
- `~/.claude/CLAUDE.md` (global - ALL projects)
- `claude-family/CLAUDE.md`
- `claude-manager-mui/CLAUDE.md`
- `nimbus-mui/CLAUDE.md`

Example:
```markdown
## Coding Standards (Auto-Loaded)

@~/.claude/standards/core/markdown-documentation.md
@~/.claude/standards/language/typescript.md
@~/.claude/standards/language/rust.md
@~/.claude/standards/framework/react.md
@~/.claude/standards/framework/mui.md
```

---

## Critical Findings

### Test: 504-Line File Creation

**Action**: Created `TEST_VALIDATION_500_LINES.md` (504 lines)
**Expected**: File creation BLOCKED with helpful error
**Actual**: File created successfully
**Reason**: OLD `instruction_matcher.py` hook still running in current session

**Evidence from hooks.log**:
```
2026-01-02 11:00:59 - instruction_matcher - INFO - SUCCESS: Applied 1 instructions (markdown)
```

### Conflict Identified

**Problem**: Two hooks for same event
- OLD: `instruction_matcher.py` (tries additionalContext injection - doesn't work)
- NEW: `standards_validator.py` (block-and-correct pattern - correct approach)

**Resolution Required**:
1. Archive `instruction_matcher.py`
2. Restart Claude Code (new session loads new hook config)
3. Test validation in new session

---

## Answers to User Questions

### Q: "is this not going to conflict with other things?"

**A: YES - Conflict Found**

Conflicts:
1. ✅ **FOUND**: Old `instruction_matcher.py` vs new `standards_validator.py`
2. ✅ **FOUND**: ~/.claude/instructions/*.instructions.md (7 files) vs database standards
3. ❌ **NO CONFLICT**: Multiple CLAUDE.md @imports (correct - merge priority works)
4. ❌ **NO CONFLICT**: .claude/rules/ (not implemented yet, deferred)

### Q: "have you updated the vault documentation?"

**A: NOT YET - On todo list**

Need to create:
1. `Coding Standards System.md` (40-Procedures/) - Main doc
2. `Azure Deployment Standards.md` (for ATO) - Production deployment
3. Update `Auto-Apply Instructions.md` - Archive old system
4. Update cross-references

### Q: "do we need some more skills... Like azue, security....."

**A: YES - Critical for ATO Azure Deployment**

Needed from Copilot Awesome:
1. Azure standards (Bicep, Functions, Logic Apps, Terraform)
2. Security/OWASP standards (production deployment)
3. Docker/containerization standards
4. CI/CD (GitHub Actions) standards

**Status**: On todo list, HIGH PRIORITY

### Q: "what the outcome of orchestrator review was, are there outstanidng jobs"

**A: YES - Critical Bug Found, NOT FIXED YET**

**From ORCHESTRATOR_MCP_AUDIT.md (632 lines - violated limit)**:

CRITICAL BUG (P0):
- `recommend_agent()` references 2 deleted agents
- Causes crashes when recommendation runs
- **Status**: ❌ NOT FIXED
- **Action**: On todo list

**Other findings**:
- Progressive discovery opportunity (P1)
- Validation layer needed (P2)
- Enhanced monitoring (P3)

---

## Outstanding Work (TODO)

### IMMEDIATE (Next Session)
1. ✅ Document hook migration (this doc)
2. ⏳ Archive `instruction_matcher.py` and `.instructions.md` files
3. ⏳ Restart Claude Code to load new hooks
4. ⏳ Test validation in NEW session

### HIGH PRIORITY (Before ATO Azure)
5. ⏳ Add Azure standards (Bicep, Functions, Logic Apps)
6. ⏳ Add Security/OWASP standards
7. ⏳ Add Docker standards
8. ⏳ Add CI/CD (GitHub Actions) standards
9. ⏳ Update remaining CLAUDE.md files (ATO-tax-agent)
10. ⏳ Regenerate all standards files

### CRITICAL BUGS (Orchestrator)
11. ⏳ Fix `recommend_agent()` stale agent references (P0)
12. ⏳ Test orchestrator after fix
13. ⏳ Update ORCHESTRATOR_MCP_AUDIT.md with resolution

### DOCUMENTATION (Vault)
14. ⏳ Create `Coding Standards System.md` in vault
15. ⏳ Create `Azure Deployment Standards.md` for ATO
16. ⏳ Update vault cross-references
17. ⏳ Archive old Auto-Apply Instructions.md

### FINAL
18. ⏳ Commit all changes with comprehensive message

---

## Migration Instructions (Next Session)

### Step 1: Verify Hook Configuration
```bash
# Check that new hook is in settings
cat .claude/settings.local.json | grep "standards_validator"
```

### Step 2: Archive Old System
```bash
# Move old files
mv scripts/instruction_matcher.py scripts/_archived/
mv ~/.claude/instructions/ ~/.claude/_archived_instructions/
```

### Step 3: Test Validation
Try to create a 500-line markdown file:
- **Expected**: Operation BLOCKED with error message
- **Error should say**: "VIOLATION: File exceeds maximum line limit"
- **Error should recommend**: Split into smaller files

### Step 4: Add Azure/Security Standards
Fetch from Copilot Awesome and add to database:
- azure-functions.instructions.md
- security-owasp.instructions.md
- docker.instructions.md
- github-actions.instructions.md

### Step 5: Fix Orchestrator Bug
Edit `mcp-servers/orchestrator/server.py`:
- Find `recommend_agent()` function
- Remove references to deleted agents
- Test with `orchestrator.recommend_agent(task="test")`

---

## File Structure

```
~/.claude/standards/          # Generated from database
├── README.md                 # Auto-generated index
├── core/
│   └── markdown-documentation.md
├── language/
│   ├── csharp.md
│   ├── typescript.md
│   └── rust.md
└── framework/
    ├── react.md
    └── mui.md

scripts/
├── generate_standards.py     # NEW: Database → files
├── standards_validator.py    # NEW: Block-and-correct enforcement
└── instruction_matcher.py    # OLD: TO BE ARCHIVED

Database:
└── claude.coding_standards   # Source of truth (7 records)
```

---

## Key Decisions

1. **Defer .claude/rules/**: Not implementing now - focus on testing current system
2. **Database-driven**: Standards in DB, not files (self-healing)
3. **Block-and-correct**: Exit code 2 pattern works better than additionalContext
4. **Three layers**: Awareness (@imports) + Enforcement (PreToolUse) + Reference (future)
5. **Copilot Awesome**: Use community standards instead of creating from scratch

---

## Next Session Priority

1. Archive old system
2. Add Azure/security standards (CRITICAL for ATO)
3. Fix orchestrator bug (P0)
4. Test validation works
5. Create vault documentation

---

**Handoff Status**: Ready for migration testing and Azure standards addition
**Blocker**: Needs session restart to activate new hooks
**Risk**: ATO Azure deployment needs security standards BEFORE production
