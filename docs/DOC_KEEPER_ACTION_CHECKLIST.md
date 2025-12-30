---
title: Documentation Keeper Action Checklist
date: 2025-12-23
status: active
priority: high
---

# Documentation Keeper Action Checklist

**Generated**: 2025-12-23
**Report**: See `DOCUMENTATION_KEEPER_REPORT_2025-12-23.md` for details
**Feedback Created**: 3 items in `claude.feedback` table

---

## 🔴 PRIORITY 1: CRITICAL (Blocks Functionality)

**Impact**: Agent spawning will fail without these configs

### Missing Agent Configs

- [ ] **research-coordinator-sonnet.mcp.json**
  - File: `mcp-servers/orchestrator/configs/research-coordinator-sonnet.mcp.json`
  - Template: Use existing agent config (e.g., `analyst-sonnet.mcp.json`)
  - Notes: Referenced in `agent_specs.json` but config doesn't exist
  - Feedback ID: #875091bf-14f6-4aba-9d71-e1702cc8ef44

- [ ] **winforms-coder-haiku.mcp.json**
  - File: `mcp-servers/orchestrator/configs/winforms-coder-haiku.mcp.json`
  - Template: Use existing agent config (e.g., `coder-haiku.mcp.json`)
  - Notes: Referenced in `agent_specs.json` but config doesn't exist
  - Feedback ID: #875091bf-14f6-4aba-9d71-e1702cc8ef44

---

## 🟠 PRIORITY 2: IMPORTANT (Cleanup & Documentation)

### A. Stale Agent Configs (Removed agents with lingering files)

**Action**: Move to `configs/deprecated/` or delete

- [ ] agent-creator-sonnet.mcp.json (removed 2025-12-13)
- [ ] csharp-coder-haiku.mcp.json (removed 2025-12-13)
- [ ] data-reviewer-sonnet.mcp.json (removed 2025-12-13)
- [ ] debugger-haiku.mcp.json (removed 2025-12-13)
- [ ] doc-reviewer-sonnet.mcp.json (removed 2025-12-13)
- [ ] nextjs-tester-haiku.mcp.json (removed 2025-12-13)
- [ ] screenshot-tester-haiku.mcp.json (removed 2025-12-13)
- [ ] security-opus.mcp.json (removed 2025-12-13)

**Feedback ID**: #73f4d98d-54e0-4da3-a63f-a863b282bd2d

---

### B. Ambiguous/Extra Configs (Clarify or Remove)

**Action**: Determine if these should be in `agent_specs.json` or archived

| Config File | Status | Action |
|------------|--------|--------|
| coordinator-sonnet.mcp.json | Extra | Rename to `research-coordinator-sonnet.mcp.json` OR document relationship |
| local-reasoner.mcp.json | Extra | Verify usage; archive if obsolete |
| tool-search.mcp.json | Extra | Verify purpose; document or remove |

---

### C. Missing Skill Documentation Files

**Action**: Create `skill.md` in each `.claude/skills/{skill-name}/` directory

**Template Available**: `.claude/skills/doc-keeper/skill.md`

Skills to document:

- [ ] **database-operations**
  - Directory: `.claude/skills/database-operations/`
  - Purpose: SQL validation, column_registry checks
  - Tools: Read, Write, Edit, mcp__postgres, Bash

- [ ] **work-item-routing**
  - Directory: `.claude/skills/work-item-routing/`
  - Purpose: Route feedback, features, build_tasks to correct tables
  - Tools: mcp__postgres, database-operations

- [ ] **testing-patterns**
  - Directory: `.claude/skills/testing-patterns/`
  - Purpose: Testing patterns and requirements
  - Tools: Read, Bash, testing frameworks

- [ ] **code-review**
  - Directory: `.claude/skills/code-review/`
  - Purpose: Code review patterns following project standards
  - Tools: Read, Grep, LSP

- [ ] **project-ops**
  - Directory: `.claude/skills/project-ops/`
  - Purpose: Project lifecycle operations (init, retrofit, phase advancement)
  - Tools: mcp__postgres, Read, Write

- [ ] **messaging**
  - Directory: `.claude/skills/messaging/`
  - Purpose: Inter-Claude messaging (inbox, broadcast, team status)
  - Tools: mcp__orchestrator

- [ ] **agentic-orchestration**
  - Directory: `.claude/skills/agentic-orchestration/`
  - Purpose: Spawn and coordinate specialized Claude agents
  - Tools: mcp__orchestrator

- [ ] **session-management**
  - Directory: `.claude/skills/session-management/`
  - Purpose: Session start/end workflows for Claude Family
  - Tools: mcp__postgres

**Feedback ID**: #32231e69-419e-46d8-a4c1-27a33e481013

**Steps**:
1. Create directory if doesn't exist: `mkdir -p .claude/skills/{skill-name}`
2. Copy template: `cp .claude/skills/doc-keeper/skill.md .claude/skills/{skill-name}/skill.md`
3. Edit frontmatter (name, description, allowed-tools)
4. Add skill-specific documentation
5. Git commit with message: "Add {skill-name} skill documentation"

---

## 🟡 PRIORITY 3: MAINTENANCE (Recommended)

### A. Automate Verification

- [ ] Set up weekly doc-keeper scheduled job
  - SQL: Insert into `claude.scheduled_jobs` with `job_name='doc-keeper-weekly'`
  - Schedule: Every Sunday 7:00 AM UTC
  - Agent: doc-keeper-haiku

### B. Add Pre-Commit Hook

- [ ] Create `.git/hooks/pre-commit` to validate:
  - `agent_specs.json` agents match `.mcp.json` files
  - No orphaned config files
  - Skip-able with `--no-verify` flag

### C. Documentation

- [ ] Add "Adding New Agents" checklist to `docs/SOP/`
  - Step 1: Add to `agent_specs.json`
  - Step 2: Create `.mcp.json` config
  - Step 3: Test spawn
  - Step 4: Update MCP Registry
  - Step 5: Run doc-keeper verification

- [ ] Archive removed agent documentation
  - Directory: `docs/archived/agents/`
  - Include: Specs, configs, system prompts

---

## ✅ Completion Checklist

Once all items are done, verify with:

```bash
# Run doc-keeper verification
python .claude/skills/doc-keeper/verify.py

# Expected output: All checks pass ✓
```

---

## Reference Information

| Item | Location |
|------|----------|
| Full Report | `docs/DOCUMENTATION_KEEPER_REPORT_2025-12-23.md` |
| Agent Specs | `mcp-servers/orchestrator/agent_specs.json` |
| Configs | `mcp-servers/orchestrator/configs/` |
| Skills | `.claude/skills/*/skill.md` |
| MCP Registry | `knowledge-vault/Claude Family/MCP Registry.md` |
| Feedback Items | `claude.feedback` table (query by project_id) |

---

## Notes

- All timestamps in this document are UTC (2025-12-23)
- Feedback items are marked as `status='new'` and ready for assignment
- Config files use `.mcp.json` extension (not `.json`)
- Skills use `.instructions.md` extension for auto-apply rules

---

**Last Updated**: 2025-12-23
**Status**: Ready for team action
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: docs/DOC_KEEPER_ACTION_CHECKLIST.md
