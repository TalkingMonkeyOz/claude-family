# Vault Documentation vs Database Reality - Discrepancy Report

**Generated**: 2026-01-21
**Analyst**: analyst-sonnet agent
**Purpose**: Identify gaps between vault documentation claims and actual database state

---

## Executive Summary

**Critical Finding**: The `infrastructure` project type is **missing `project-tools` MCP** in its default configuration, while all other project types have it. This explains why project-tools MCP features (knowledge operations, work tracking, etc.) may not be available in infrastructure projects like claude-family.

**Overall Status**:
- ✅ **7 claims verified** as accurate
- ❌ **5 critical discrepancies** found requiring fixes
- ⚠️ **8 documentation issues** need clarification or updates
- 📊 **4 data quality issues** identified

---

## Critical Discrepancies (Fix Required)

### 1. ❌ infrastructure Projects Missing project-tools MCP

**Documentation Claims** (Config Management SOP, MCP configuration.md):
- "Global MCPs: postgres, orchestrator, sequential-thinking, python-repl"
- project-tools MCP exists and provides knowledge operations, work tracking
- MCP configuration doc mentions project-tools template exists

**Database Reality**:
```sql
SELECT project_type, default_mcp_servers
FROM claude.project_type_configs
WHERE project_type IN ('infrastructure', 'web-app', 'csharp-desktop');
```

| project_type | default_mcp_servers |
|-------------|---------------------|
| infrastructure | ['orchestrator', 'postgres'] |
| web-app | ['postgres', 'project-tools'] |
| csharp-desktop | ['postgres', 'project-tools'] |

**Impact**:
- Infrastructure projects (claude-family) don't have access to:
  - `store_knowledge` / `recall_knowledge` (manual knowledge operations)
  - `get_project_context` (load project settings)
  - `create_feedback` / `create_feature` (work tracking with validation)
  - All other project-tools MCP functionality

**Fix Required**:
```sql
UPDATE claude.project_type_configs
SET default_mcp_servers = ARRAY['orchestrator', 'postgres', 'project-tools']
WHERE project_type = 'infrastructure';
```

---

### 2. ❌ config_templates Table Missing 'active' Column

**Documentation Claims** (Config Management SOP line 149):
```sql
SELECT template_name, config_type, description, active
FROM claude.config_templates
WHERE active = true
```

**Database Reality**:
```
Error: column "active" does not exist
```

**Actual Columns**: template_id, template_name, config_type, description, content, file_path, is_base, extends_template_id, version, created_at, updated_at

**Impact**: Documentation query examples fail. No way to filter active/inactive templates.

**Fix Options**:
1. **Add column**: `ALTER TABLE claude.config_templates ADD COLUMN active boolean DEFAULT true;`
2. **Update docs**: Remove `active` references, use `is_base` or other filters

---

### 3. ❌ column_registry Missing config_templates Constraints

**Documentation Claims** (Config Management SOP line 174):
```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'config_templates' AND column_name = 'config_type';
```

**Database Reality**:
```
[] -- No rows returned
```

**Impact**: No validation enforcement for `config_type` values. Documentation implies data gateway pattern applies but constraints don't exist.

**Fix Required**:
```sql
INSERT INTO claude.column_registry (table_name, column_name, valid_values)
VALUES ('config_templates', 'config_type', ARRAY['hooks', 'mcp', 'skills', 'instructions']);
```

---

### 4. ❌ vault-rag MCP Not in Any Configuration

**Documentation Claims**:
- Global CLAUDE.md: "~~vault-rag~~ ❌ Auto via RAG hook"
- MCP Registry.md: No vault-rag mentioned (good)
- Config Management SOP: No mention (good)

**Database Reality**:
- `config_templates` table: No vault-rag template exists
- `project_type_configs`: No vault-rag in any default_mcp_servers
- `mcp_usage_stats`: Only 1 call to `mcp__vault-rag__semantic_search` ever recorded

**Impact**:
- Documentation correctly states vault-rag is "auto via hook" but unclear how/where configured
- If it's truly automatic via hook, why does it need MCP configuration at all?
- 839 RAG queries logged in `rag_usage_log` but only 1 MCP call logged suggests it's NOT using vault-rag MCP

**Clarification Needed**:
- Is vault-rag MCP actually installed/configured anywhere?
- Or is RAG functionality handled entirely by hooks calling Voyage API directly?
- If hooks handle it, vault-rag MCP can be fully removed from system

---

### 5. ❌ agent_sessions All Orphaned (43/43 with NULL parent)

**Documentation Claims** (Session Architecture.md line 86-87):
- "agent_sessions → sessions (parent link **MISSING**)"
- "Data Quality: 144 agent spawns (all orphaned, no parent_session_id)"

**Database Reality**:
```sql
SELECT COUNT(*) as total, COUNT(parent_session_id) as with_parent
FROM claude.agent_sessions;
-- Result: 43 total, 0 with_parent
```

**FK Exists But Not Used**:
```sql
SELECT constraint_name FROM information_schema.table_constraints
WHERE table_name = 'agent_sessions' AND constraint_type = 'FOREIGN KEY';
-- Result: fk_agent_sessions_parent exists!
```

**Impact**:
- Cannot trace which session spawned which agent
- Cost rollups impossible (can't sum agent costs per session)
- Orphaned agent records accumulate without cleanup

**Fix Required**: Update orchestrator MCP's `spawn_agent` to actually set `parent_session_id` when creating agent_sessions records.

---

## Data Quality Issues

### 6. 📊 Observability Doc Claims Outdated

**Documentation Claims** (Observability.md line 17-32):
- `sessions`: 532 rows
- `rag_usage_log`: 664 rows
- `agent_sessions`: ~130 rows
- `mcp_usage_stats`: 2 rows (⚠️ Barely used)
- `enforcement_log`: 0 rows (❌ NOT USED)

**Database Reality**:
- `sessions`: **550 rows** (18 more than claimed)
- `rag_usage_log`: **839 rows** (175 more than claimed)
- `agent_sessions`: **43 rows** (87 FEWER than claimed - discrepancy!)
- `mcp_usage_stats`: **23 rows** (21 more than claimed)
- `enforcement_log`: **1,178 rows** (NOT empty!)

**Major Discrepancy**: Observability doc says enforcement_log is "NOT USED" with 0 rows, but it actually has 1,178 rows! Table is actively used for reminder logging.

**Fix Required**: Update Observability.md with current counts and correct enforcement_log status.

---

### 7. 📊 Session Identity Stats Wrong

**Documentation Claims** (Session Architecture.md line 104):
- "395 total sessions (39 with NULL identity, 10%)"

**Database Reality**:
```sql
SELECT COUNT(*) as total, COUNT(*) - COUNT(identity_id) as null_count
FROM claude.sessions;
-- Result: 550 total, 6 null (1%, not 10%)
```

**Impact**: Documentation overstates identity resolution problems. System is healthier than docs claim.

**Fix Required**: Update Session Architecture.md with current stats.

---

### 8. 📊 Vault Embedding Counts Don't Match Claims

**Documentation Claims** (various docs):
- "118+ vault documents embedded"
- "290 knowledge entries embedded"

**Database Reality**:
```sql
SELECT COUNT(*) as embeddings, COUNT(DISTINCT doc_path) as docs
FROM claude.vault_embeddings;
-- Result: 8,685 embeddings from 681 unique documents
```

**Knowledge Table**:
```sql
SELECT COUNT(*) FROM claude.knowledge;
-- Result: 313 knowledge entries (close to 290 claim)
```

**Impact**: Vault embeddings claim of "118+ documents" is massively understated. System has embedded **681 documents** across **11 projects**. This is GOOD news - system is more comprehensive than documented.

**Fix Required**: Update documentation with accurate embedding stats.

---

### 9. 📊 mcp_usage_stats Severely Underutilized

**Documentation Claims** (Observability.md):
- "mcp_usage_stats: ⚠️ Barely used"
- "13 MCP usage records (should be thousands)"

**Database Reality**:
```sql
SELECT COUNT(*) FROM claude.mcp_usage_stats;
-- Result: 23 rows total
```

**Tool Calls Logged**:
- Most are test calls: `mcp__postgres__test`, `mcp__postgres__debug_test`, etc.
- Only 1 real usage call per tool (execute_sql, spawn_agent, etc.)

**Impact**: MCP usage tracking is essentially non-functional. With 550 sessions and 839 RAG queries, should have thousands of MCP usage records.

**Root Cause**: Session Architecture doc mentions "MCP usage logging ❌ Broken - CLAUDE_SESSION_ID env var not exported"

**Fix Required**:
1. Implement `CLAUDE_SESSION_ID` export in SessionStart hook
2. Update MCP servers to log usage to `mcp_usage_stats`
3. Add usage logging to orchestrator MCP

---

## Documentation Clarification Needed

### 10. ⚠️ Global MCPs List Inconsistent

**Different Claims Across Docs**:

1. **MCP configuration.md line 26**: "Global MCPs: postgres, orchestrator, sequential-thinking, python-repl"
2. **Global CLAUDE.md**: Lists postgres, orchestrator, sequential-thinking, python-repl as global
3. **MCP Registry.md**: Lists these as "Scope: Global (all projects)"

**Database Reality**:
- These MCPs are NOT in `default_mcp_servers` for most project types
- Only `infrastructure` has orchestrator + postgres
- All others have postgres + project-tools

**Clarification Needed**:
- Define "Global MCP" clearly: Does it mean "in ~/.claude.json" or "available to all projects"?
- If truly global, why aren't they in every project_type_configs.default_mcp_servers?
- Update docs to distinguish between:
  - **System-wide MCPs** (installed in ~/.claude.json)
  - **Default MCPs by type** (in project_type_configs)
  - **Project overrides** (in workspaces.startup_config)

---

### 11. ⚠️ memory MCP Status Unclear

**Documentation Claims**:
- Global CLAUDE.md: "~~memory~~ ❌ **Removed** (replaced by project-tools knowledge)"
- MCP Registry.md: "memory: Scope: Project-specific (claude-family only)"
- config_templates: "mcp-project-tools: Replaces memory MCP"

**Database Reality**:
- `mcp_usage_stats` shows 1 call to `mcp__memory__create_entities`
- No memory template in config_templates
- mcp_usage_stats records it as active MCP

**Inconsistency**: Some docs say removed, others say active. If removed, why are there recent usage logs?

**Clarification Needed**:
- Is memory MCP still installed anywhere?
- If deprecated, update MCP Registry.md to reflect removal
- If still used for specific purposes, document where/why

---

### 12. ⚠️ filesystem MCP Status Unclear

**Documentation Claims**:
- MCP Registry.md: "filesystem: Scope: Project-specific (claude-family only)"
- Agent coordination protocol (this session): "Use the filesystem MCP tools (mcp__filesystem__*)"

**Database Reality**:
- No filesystem in any project_type_configs.default_mcp_servers
- `mcp_usage_stats` shows 1 call to `mcp__filesystem__list_directory`
- No filesystem template in config_templates

**Clarification Needed**:
- Is filesystem MCP actually configured for claude-family project?
- If so, where? (Should be in workspaces.startup_config)
- If not, remove references from agent protocols and docs

---

### 13. ⚠️ Settings File Location Inconsistent

**Documentation Claims**:
- Config Management SOP: "Generated Files: `.claude/settings.local.json`"
- Session Architecture: "Config sync regenerates `.claude/settings.local.json`"

**Reality Check**:
- This agent session (spawned in claude-family workspace) has NO `.claude/settings.local.json`
- Agent was given "WORKSPACE: C:\Projects\claude-family"
- Agent instructions say "Use the filesystem MCP tools (mcp__filesystem__*)"

**Possible Explanations**:
1. Spawned agents don't get settings.local.json (run with parent's config)
2. Settings file only generated for main Claude Code sessions, not agent sessions
3. Config sync hasn't run yet in this session

**Clarification Needed**:
- Document that agent sessions inherit parent config, don't get own settings file
- Or confirm settings file should exist for agents and investigate why missing

---

### 14. ⚠️ Hook Configuration Location Confusion

**Documentation Claims**:
- Config Management SOP (older sections): "Writes `.claude/hooks.json` (hooks only)"
- Config Management SOP line 39: "Claude Code reads hooks from settings files only (`settings.json` or `settings.local.json`), NOT from a separate `hooks.json` file"

**Inconsistency**: Documentation contradicts itself about whether hooks.json is written.

**Clarification Needed**:
- If hooks.json is NOT used, remove all references to it being written
- If it IS written for backward compatibility, document why
- Update line 69 which mentions writing both hooks.json AND settings.local.json

---

### 15. ⚠️ mcp_configs Table Purpose Unclear

**Documentation Claims**:
- Config Management SOP line 78: "mcp_configs - Audit tracking"
- MCP configuration.md line 78: "mcp_configs - Audit tracking"

**Database Reality**:
```sql
SELECT * FROM claude.mcp_configs LIMIT 5;
-- Columns: config_id, project_name, mcp_server_name, mcp_package,
--          install_date, removal_date, is_active, reason, installed_by_identity_id
```

**Confusion**:
- Table appears designed for install/removal audit trail
- But documentation doesn't explain when/how it's populated
- No examples of querying it for audit purposes
- Relationship to config_deployment_log unclear (both seem to track changes?)

**Clarification Needed**:
- Document when records are inserted (manual? automatic?)
- Provide examples of audit queries
- Explain difference between mcp_configs and config_deployment_log
- If unused/deprecated, mark as such

---

### 16. ⚠️ project_config_assignments Table Undocumented

**Documentation Claims**:
- Config Management SOP line 152: Lists `project_config_assignments` table

**Database Reality**:
- Table exists ✅
- NO documentation about:
  - What it does
  - When to use it vs workspaces.startup_config
  - How override_content works
  - Examples of usage

**Clarification Needed**: Add section to Config Management SOP explaining:
- Purpose: Link projects to reusable config templates
- When to use: For projects sharing complex configs
- Schema: project_id, template_id, override_content (JSONB)
- Examples: Assigning hooks-with-db-validation template to multiple projects

---

### 17. ⚠️ RAG System Architecture Needs Clarification

**Documentation Claims**:
- Global CLAUDE.md: "RAG (FULLY OPERATIONAL) - ✅ AUTOMATIC via UserPromptSubmit hook"
- Says 664 RAG queries (actually 839)
- Says vault-rag MCP exists but is "auto via hook"

**Database Reality**:
- `rag_usage_log`: 839 queries logged ✅
- `vault_embeddings`: 8,685 embeddings from 681 docs ✅
- `mcp_usage_stats`: Only 1 call to vault-rag MCP ever

**Confusion**:
- If RAG is "auto via hook", does it use vault-rag MCP or not?
- If hook calls Voyage API directly, why have vault-rag MCP?
- Documentation doesn't explain the architecture clearly

**Clarification Needed**: Create RAG architecture diagram showing:
```
Option A: Hook → Voyage API → PostgreSQL → Context injection
Option B: Hook → vault-rag MCP → Voyage API → PostgreSQL → Context injection
```

Document which is actually implemented and why.

---

## Verified Claims (Documentation Accurate) ✅

### 18. ✅ Infrastructure Project Type Correctly Configured (Except project-tools)

**Claim**: infrastructure projects have specific default skills and MCPs

**Verified**:
```sql
SELECT default_skills FROM claude.project_type_configs
WHERE project_type = 'infrastructure';
-- Result: ['database-operations', 'work-item-routing', 'session-management',
--          'code-review', 'project-ops', 'messaging', 'agentic-orchestration']
```

Matches documentation expectations (7 skills vs 2-3 for other types).

---

### 19. ✅ Foreign Key Constraints Actually Exist

**Claim** (Session Architecture.md): "sessions.identity_id → identities.identity_id (FK **MISSING**)"

**Verified**: FK DOES exist!
```sql
-- Result: fk_sessions_identity constraint exists
```

**Documentation Issue**: Doc claims FK is missing, but it exists. Status marker is wrong, not the database.

---

### 20. ✅ session_state Table Structure Correct

**Claim**: session_state has todo_list, current_focus, next_steps

**Verified**: All expected columns present:
- project_name (PK)
- todo_list (jsonb)
- current_focus (text)
- files_modified (array)
- pending_actions (array)
- next_steps (jsonb)
- updated_at (timestamp)

---

### 21. ✅ config_templates Table Has Expected Structure

**Claim**: Stores reusable config templates with JSONB content

**Verified**: 6 templates exist:
- hooks-base (hooks config)
- hooks-with-db-validation (extended hooks)
- mcp-orchestrator (orchestrator MCP config)
- mcp-postgres (postgres MCP config)
- mcp-project-tools (project-tools MCP config)
- mcp-sequential-thinking (sequential-thinking MCP config)

All have proper structure: template_name, config_type, description, content (JSONB).

---

### 22. ✅ Self-Healing Config System Architecture Sound

**Claim**: Database → script → settings.local.json regenerates every session

**Verified by Design**:
- `project_type_configs` table exists with default_mcp_servers[] ✅
- `workspaces` table has startup_config JSONB for overrides ✅
- `config_templates` provides reusable configs ✅
- Documentation correctly describes merge order: base → type → project

System architecture is solid, just needs project-tools added to infrastructure type.

---

### 23. ✅ Knowledge System Active and Larger Than Claimed

**Claim**: Knowledge embeddings system operational

**Verified**:
- `knowledge` table: 313 entries (close to claimed 290) ✅
- `vault_embeddings`: 8,685 embeddings from 681 documents (MUCH larger than claimed 118) ✅
- `rag_usage_log`: 839 queries (more than claimed 664) ✅

System is MORE comprehensive than documented - good problem to have!

---

### 24. ✅ Column Registry Exists and Used for Validation

**Claim**: column_registry stores valid values for constrained columns

**Verified**:
- Table exists ✅
- Used for data gateway pattern ✅
- Missing some entries (see issue #3) but functional

---

## Recommendations

### Immediate Actions (High Priority)

1. **Add project-tools to infrastructure projects**:
   ```sql
   UPDATE claude.project_type_configs
   SET default_mcp_servers = ARRAY['orchestrator', 'postgres', 'project-tools']
   WHERE project_type = 'infrastructure';
   ```

2. **Fix orchestrator MCP to populate parent_session_id** when spawning agents

3. **Update Observability.md** with current row counts:
   - sessions: 550
   - rag_usage_log: 839
   - agent_sessions: 43
   - enforcement_log: 1,178 (NOT empty!)
   - mcp_usage_stats: 23

4. **Clarify vault-rag MCP architecture** - is it used or not?

### Medium Priority

5. **Add column_registry entries** for config_templates.config_type

6. **Document mcp_configs table usage** or mark as deprecated

7. **Add active column** to config_templates OR update all doc examples to remove it

8. **Update Session Architecture.md**:
   - FK for sessions→identities DOES exist
   - Current NULL identity rate is 1%, not 10%

### Low Priority

9. **Document project_config_assignments** table with examples

10. **Clarify "Global MCP"** terminology across docs

11. **Update vault embedding stats** (681 docs, not 118)

12. **Resolve hooks.json vs settings.local.json** contradiction

13. **Document agent session config inheritance** (no own settings file)

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Critical discrepancies requiring database fixes | 3 |
| Critical discrepancies requiring code fixes | 2 |
| Data quality issues (outdated stats) | 4 |
| Documentation clarifications needed | 8 |
| Claims verified as accurate | 7 |
| **Total issues identified** | **17** |

---

**Next Steps**:
1. Review this report with primary maintainer
2. Create feedback items for each critical issue
3. Update vault documentation for data quality issues
4. Schedule fix implementation for critical discrepancies

---

**Version**: 1.0
**Created**: 2026-01-21
**Analyst**: analyst-sonnet (session 45f8b986-73df-4b9e-ac9c-2e66e4985fe7)
**Location**: claude-family/docs/VAULT_DATABASE_DISCREPANCY_REPORT.md
