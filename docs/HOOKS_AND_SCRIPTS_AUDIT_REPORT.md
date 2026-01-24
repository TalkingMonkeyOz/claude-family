# Comprehensive Hooks and Scripts Audit Report

**Date**: 2026-01-19
**Auditor**: Claude Sonnet 4.5 (analyst-sonnet)
**Scope**: All hook scripts and related Python utilities in claude-family project

---

## Executive Summary

**Status**: ✅ MOSTLY CURRENT with minor issues

- **Total Scripts Audited**: 89 Python files
- **Hook Scripts**: 11 active hooks configured
- **Current**: 9 hooks using modern `claude.*` schema
- **Outdated**: 2 hooks with hardcoded credentials (security issue)
- **Deprecated**: 1 script in `_deprecated/` folder
- **Critical Issues**: 1 (hardcoded database credentials in 2 scripts)

---

## Hook Configuration Analysis

### Configured Hooks (from `.claude/settings.local.json`)

| Hook Type | Matcher | Script | Status |
|-----------|---------|--------|--------|
| **SessionStart** | once | `session_startup_hook.py` (plugin) | ✅ CURRENT |
| **SessionEnd** | - | Prompt-only (no script) | ✅ CURRENT |
| **UserPromptSubmit** | - | `rag_query_hook.py` | ✅ CURRENT |
| **SubagentStart** | - | `subagent_start_hook.py` | ⚠️ HARDCODED CREDS |
| **Stop** | - | `stop_hook_enforcer.py` | ⚠️ HARDCODED CREDS |
| **PreCompact** | manual/auto | `precompact_hook.py` | ✅ CURRENT |
| **PreToolUse** | Write/Edit | `context_injector_hook.py` | ✅ CURRENT |
| **PreToolUse** | Write/Edit | `standards_validator.py` | ✅ CURRENT |
| **PreToolUse** | mcp__postgres__execute_sql | `context_injector_hook.py` | ✅ CURRENT |
| **PostToolUse** | TodoWrite | `todo_sync_hook.py` | ✅ CURRENT |
| **PostToolUse** | 30+ MCP tools | `mcp_usage_logger.py` | ✅ CURRENT |

### Hook Configuration Location

**Discovery**: No `claude.hooks` table exists in database. All hook configuration is file-based via:
- Global: `~/.claude/settings.json`
- Project: `.claude/settings.local.json` (generated from database via `generate_project_settings.py`)

---

## Detailed Script Audit

### 1. Session Lifecycle Hooks

#### ✅ `session_startup_hook.py` (Plugin - 1,146 lines)
**Hook**: SessionStart (once)
**Location**: `.claude-plugins/claude-family-core/scripts/`
**Schema**: ✅ Uses `claude.*` throughout
**Database**: ✅ Uses environment var or secure config
**Error Handling**: ✅ Comprehensive try/catch, returns valid JSON on error

**Features**:
- Auto-logs session to `claude.sessions` (uses Claude Code's session_id)
- Syncs config from database (calls `generate_project_settings.py`)
- Deploys components from database (CLAUDE.md, skills, rules via `deploy_components.py`)
- Loads todos with smart auto-completion ("restart" todos auto-complete)
- Checks pending messages from orchestrator
- Loads active work items (features, feedback, build_tasks)
- RAG pre-load: semantic search for relevant vault docs
- Fixes Windows npx commands automatically
- Sets environment variables (SESSION_ID, PROJECT_ID, CLAUDE_PROJECT_NAME)

**Issues**: None - this is the gold standard

---

#### ✅ `session_end_hook.py` (Plugin - 142 lines)
**Hook**: SessionEnd (prompt-based, no actual hook execution)
**Location**: `.claude-plugins/claude-family-core/scripts/`
**Schema**: ✅ Uses `claude.session_state`
**Database**: ✅ Uses environment var `DATABASE_URL`
**Error Handling**: ✅ Returns valid JSON on error

**Features**:
- Saves session state (todos, focus, next_steps, files_modified)
- Upserts to `claude.session_state` table
- Called via `/session-end` command, not as active hook

**Issues**: None

---

#### ⚠️ `session_startup_hook_enhanced.py` (scripts/ - 100+ lines partial read)
**Hook**: NOT CONFIGURED (orphan script)
**Location**: `scripts/`
**Status**: ⚠️ ORPHANED - not referenced in any hook config

**Discovery**: This appears to be an enhanced version but is NOT configured. The plugin version is what's actually used.

**Recommendation**: Delete or document why it exists

---

### 2. RAG and Context Hooks

#### ✅ `rag_query_hook.py` (1,037 lines)
**Hook**: UserPromptSubmit
**Schema**: ✅ Uses `claude.vault_embeddings`, `claude.rag_usage_log`, `claude.vocabulary_mappings`
**Database**: ✅ Uses environment var or secure config
**Error Handling**: ✅ Silent failure (returns empty context if RAG unavailable)

**Features**:
- Automatic semantic search on EVERY user prompt
- Uses Voyage AI embeddings (voyage-3 model)
- Queries both vault docs and knowledge table
- Vocabulary expansion (learns user phrases → canonical concepts)
- Self-learning: implicit feedback detection
- Logs usage to `claude.rag_usage_log`

**Dependencies**:
- `VOYAGE_API_KEY` environment variable
- `voyageai` Python package
- `claude.vault_embeddings` table populated

**Issues**: None - critical infrastructure, working as designed

---

#### ✅ `context_injector_hook.py` (468 lines)
**Hook**: PreToolUse (Write, Edit, mcp__postgres__execute_sql)
**Schema**: ✅ Uses `claude.context_rules`, `claude.skill_content`, `claude.coding_standards`
**Database**: ✅ Uses environment var or secure config
**Error Handling**: ✅ Returns "allow" decision on error

**Features**:
- Database-driven context injection via `claude.context_rules`
- Matches tool_patterns and file_patterns
- Injects coding standards before Write/Edit
- Injects Data Gateway standards before SQL execution
- Loads comprehensive skills from `claude.skill_content`
- Fast (<50ms) - immediate static context, optional vault RAG

**Issues**: None

---

### 3. Validation Hooks

#### ✅ `standards_validator.py` (520 lines)
**Hook**: PreToolUse (Write, Edit)
**Schema**: ✅ Uses `claude.coding_standards`, `claude.column_registry`
**Database**: ✅ Uses environment var or secure config
**Error Handling**: ✅ Returns "allow" on error

**Features**:
- Validates files against `claude.coding_standards`
- Supports ask+updatedInput middleware pattern (v2.1.0)
- Can block violations or suggest corrections
- Checks file patterns, validation rules, max lines

**Issues**: None

---

#### ✅ `validate_db_write.py` (Plugin - 238 lines)
**Hook**: NOT CURRENTLY CONFIGURED (but available)
**Schema**: ✅ Uses `claude.column_registry`
**Database**: ✅ Uses environment var `DATABASE_URL`

**Features**:
- Validates INSERT/UPDATE against `claude.column_registry`
- Blocks operations with invalid column values
- Provides valid options in error message

**Status**: ⚠️ NOT ACTIVE - should this be enabled?

**Recommendation**: Consider enabling as PreToolUse hook for postgres tools

---

#### ✅ `validate_claude_md.py` (Plugin - 139 lines)
**Hook**: NOT CURRENTLY CONFIGURED (but available)
**Features**:
- Validates CLAUDE.md files (max 250 lines, required sections, project ID format)
- Returns warnings, not blocking errors

**Status**: ⚠️ NOT ACTIVE

**Recommendation**: Consider enabling as PreToolUse hook for CLAUDE.md edits

---

### 4. Persistence Hooks

#### ✅ `todo_sync_hook.py` (517 lines)
**Hook**: PostToolUse (TodoWrite)
**Schema**: ✅ Uses `claude.todos`
**Database**: ✅ Uses environment var or secure config
**Error Handling**: ✅ Silent failure (logs error, doesn't block TodoWrite)

**Features**:
- Syncs TodoWrite calls to `claude.todos` database
- Fuzzy matching to identify same todo across calls (75% similarity)
- Tracks created_session_id and completed_session_id
- Handles INSERT new and UPDATE existing todos
- Soft deletes todos removed from list

**Critical Fix** (2025-12-31): Solves architectural flaw where TodoWrite only saves to in-memory state

**Issues**: None - critical infrastructure

---

#### ✅ `mcp_usage_logger.py` (250+ lines)
**Hook**: PostToolUse (30+ MCP tool matchers)
**Schema**: ✅ Uses `claude.mcp_usage`, `claude.sessions`
**Database**: ⚠️ **HARDCODED CREDENTIALS** in line 41-44
**Error Handling**: ✅ Best-effort logging, doesn't block tool execution

**Features**:
- Logs all MCP tool calls to `claude.mcp_usage`
- Tracks: tool name, execution time, success/failure, input/output sizes
- Lazy session creation (for continuations without SessionStart)
- Extracts MCP server name from tool name

**🔴 CRITICAL ISSUE**:
```python
DATABASE_URI = os.environ.get(
    'DATABASE_URI',
    'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost:5432/ai_company_foundation'
)
```

**Recommendation**: Remove hardcoded credentials IMMEDIATELY. Use secure config loading pattern like `rag_query_hook.py`

---

### 5. Enforcement and Reminder Hooks

#### ⚠️ `stop_hook_enforcer.py` (350+ lines)
**Hook**: Stop
**Schema**: ✅ Uses `claude.enforcement_log` (if available)
**Database**: ⚠️ **HARDCODED CREDENTIALS** in lines 40-45
**Error Handling**: ✅ Graceful degradation

**Features**:
- Self-enforcing periodic checks (every 5/10/20 interactions)
- Git status reminder (every 5)
- Inbox check reminder (every 10)
- CLAUDE.md refresh reminder (every 5)
- Work tracking reminder (every 15)
- Tracks code changes to remind about tests

**🔴 CRITICAL ISSUE**: Same hardcoded credentials as mcp_usage_logger.py

**Recommendation**: Fix immediately

---

#### ✅ `precompact_hook.py` (123 lines)
**Hook**: PreCompact (manual, auto)
**Schema**: N/A (no database access)
**Features**:
- Reminds to re-examine CLAUDE.md and vault before compaction
- Lists vault folder structure (40-Procedures, 20-Domains, etc.)

**Issues**: None

---

#### ⚠️ `subagent_start_hook.py` (159 lines)
**Hook**: SubagentStart
**Schema**: ✅ Uses `claude.agent_sessions`
**Database**: ⚠️ **HARDCODED CREDENTIALS** in lines 44-47
**Error Handling**: ✅ Silent failure

**Features**:
- Logs agent spawns to `claude.agent_sessions`
- Tracks: agent_type, task_prompt, parent_session_id, workspace_dir

**🔴 CRITICAL ISSUE**: Same hardcoded credentials

**Recommendation**: Fix immediately

---

### 6. Utility and Support Scripts

#### ✅ `generate_project_settings.py` (23,901 bytes)
**Purpose**: Generates `.claude/settings.local.json` from database
**Schema**: ✅ Uses `claude.workspaces`, `claude.project_type_configs`, `claude.config_templates`
**Called by**: `session_startup_hook.py`
**Status**: ✅ CURRENT - critical self-healing infrastructure

---

#### ✅ `deploy_components.py` (23,262 bytes)
**Purpose**: Deploys CLAUDE.md, skills, rules from database to filesystem
**Schema**: ✅ Uses `claude.managed_components`, `claude.skill_content`, etc.
**Called by**: `session_startup_hook.py`
**Status**: ✅ CURRENT - implements ADR-006 (database as source of truth)

---

#### ✅ `embed_vault_documents.py` (17,966 bytes)
**Purpose**: Embeds vault docs using Voyage AI, stores in `claude.vault_embeddings`
**Schema**: ✅ Uses `claude.vault_embeddings`
**Status**: ✅ CURRENT - critical for RAG system

---

#### ✅ `embed_knowledge.py` (6,865 bytes)
**Purpose**: Embeds knowledge entries, stores in `claude.knowledge`
**Schema**: ✅ Uses `claude.knowledge`
**Status**: ✅ CURRENT

---

#### ✅ `embed_features.py` (10,812 bytes)
**Purpose**: Embeds feature plan_data for semantic search
**Schema**: ✅ Uses `claude.features`, `claude.feature_embeddings`
**Status**: ✅ CURRENT

---

#### `process_router.py` (35,071 bytes)
**Purpose**: Routes slash commands to process handlers
**Status**: ⚠️ DEPRECATED (ADR-005: replaced by skills-first architecture)
**Note**: `.deprecated` backup exists (Dec 20, 2025)

---

### 7. Validator Module Scripts

#### `scripts/validators/` (6 files)
- `__init__.py`
- `claude_md.py` - Validates CLAUDE.md structure
- `data_gateway.py` - Validates column_registry usage
- `rules.py` - Validates rules files
- `skills.py` - Validates skills files
- `runner.py` - Orchestrates validation

**Status**: ✅ CURRENT - used by validation tooling

---

## Schema Compliance Summary

### ✅ Scripts Using Current `claude.*` Schema (9/11 hooks)

All scripts use the unified `claude.*` schema correctly:
- `claude.sessions`, `claude.todos`, `claude.feedback`
- `claude.features`, `claude.build_tasks`
- `claude.mcp_usage`, `claude.rag_usage_log`
- `claude.vault_embeddings`, `claude.knowledge`
- `claude.context_rules`, `claude.coding_standards`
- `claude.column_registry`, `claude.session_state`

### ❌ No Legacy Schema Usage Found

Good! No scripts reference deprecated schemas:
- ❌ `claude_family.*` - NONE FOUND
- ❌ `claude_pm.*` - NONE FOUND

---

## Security Audit

### 🔴 CRITICAL: Hardcoded Database Credentials (3 scripts)

**Affected Files**:
1. `scripts/mcp_usage_logger.py` (line 41-44)
2. `scripts/stop_hook_enforcer.py` (line 40-45)
3. `scripts/subagent_start_hook.py` (line 44-47)

**Exposure**:
```python
DATABASE_URI = os.environ.get(
    'DATABASE_URI',
    'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost:5432/ai_company_foundation'
)
```

**Risk**: HIGH - credentials in plain text, committed to git

**Remediation**: Replace with secure config pattern used in other scripts:
```python
# Load from ai-workspace config
try:
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    DEFAULT_CONN_STR = None
```

---

## Error Handling Assessment

### ✅ Robust Error Handling (All Hooks)

All hooks implement proper error handling:
- Return valid JSON on all code paths
- Silent failures where appropriate (RAG, logging)
- Graceful degradation when database unavailable
- Logging to `~/.claude/hooks.log` for debugging

**Example** (rag_query_hook.py):
```python
except Exception as e:
    logger.error(f"RAG query failed: {e}", exc_info=True)
    print(json.dumps({"additionalContext": "", "systemMessage": ""}))
    return 0  # Allow execution to continue
```

---

## Configuration Drift Analysis

### Settings File vs Database

**Discovery**: No `claude.hooks` table exists. Hook configuration is file-only:
- Global hooks: `~/.claude/settings.json`
- Project hooks: `.claude/settings.local.json` (generated from `claude.workspaces.startup_config`)

**Self-Healing**: Project settings regenerate from database on EVERY SessionStart via `generate_project_settings.py`

**Configuration Source of Truth**:
- Hook scripts: Database (`claude.workspaces.startup_config` JSONB)
- Hook triggers: File-based (`settings.local.json`)

---

## Orphaned/Unused Scripts

### ⚠️ Scripts Not Referenced in Hook Config

1. **`session_startup_hook_enhanced.py`** - Duplicate/orphaned, plugin version is used
2. **`validate_db_write.py`** - Available but not configured
3. **`validate_claude_md.py`** - Available but not configured
4. **`validate_parent_links.py`** - Plugin script, purpose unclear
5. **`validate_phase.py`** - Plugin script, purpose unclear
6. **`check_doc_updates.py`** - Plugin script, purpose unclear
7. **`cleanup_mcp_processes.py`** - Plugin script, utility not hook

### Recommendation

- **DELETE** `session_startup_hook_enhanced.py` (duplicate)
- **DOCUMENT** why validate_db_write and validate_claude_md aren't active
- **AUDIT** plugin validator scripts to determine if still needed

---

## MCP Tool Coverage

### PostToolUse Hook Coverage (mcp_usage_logger.py)

**Matchers configured**: 30+ MCP tools

**Postgres MCP** (5 tools):
- `execute_sql`, `list_schemas`, `list_objects`, `get_object_details`, `explain_query`, `analyze_db_health`

**Orchestrator MCP** (8 tools):
- `spawn_agent`, `spawn_agent_async`, `check_inbox`, `send_message`, `broadcast`, `acknowledge`, `get_agent_stats`, `get_mcp_stats`

**Memory MCP** (3 tools):
- `create_entities`, `search_nodes`, `read_graph`

**Vault-RAG MCP** (2 tools):
- `semantic_search`, `get_document`

**Project-Tools MCP** (12 tools):
- `get_project_context`, `get_incomplete_todos`, `restore_session_todos`, `create_feedback`, `create_feature`, `add_build_task`, `get_ready_tasks`, `update_work_status`, `find_skill`, `todos_to_build_tasks`, `store_knowledge`, `recall_knowledge`, `link_knowledge`, `get_related_knowledge`, `mark_knowledge_applied`

**Sequential-Thinking MCP** (1 tool):
- `sequentialthinking`

**Coverage**: ✅ Excellent - all major MCP tools logged

---

## Recommendations

### 🔴 URGENT (Security)

1. **Fix hardcoded credentials** in 3 scripts:
   - `mcp_usage_logger.py`
   - `stop_hook_enforcer.py`
   - `subagent_start_hook.py`

   **Action**: Replace with secure config pattern, commit fix immediately

---

### 🟡 HIGH PRIORITY

2. **Enable Data Gateway validation**:
   - Activate `validate_db_write.py` as PreToolUse hook for postgres tools
   - This prevents invalid column values BEFORE execution

3. **Audit orphaned scripts**:
   - Delete `session_startup_hook_enhanced.py` (duplicate)
   - Document why validate_claude_md.py isn't active
   - Audit plugin validator scripts (validate_parent_links, validate_phase, check_doc_updates)

4. **Document hook configuration process**:
   - Create SOP: "Adding a New Hook to Claude Family"
   - Explain file-based config vs database config
   - Show how to test hooks locally

---

### 🟢 MEDIUM PRIORITY

5. **Improve logging**:
   - Implement log rotation in more scripts (only session_startup_hook does this)
   - Consider structured logging (JSON) for easier parsing
   - Add log levels (DEBUG, INFO, WARNING, ERROR)

6. **Add hook health monitoring**:
   - Track hook execution times in database
   - Alert on hooks taking >5s
   - Dashboard for hook performance

7. **Test coverage**:
   - Unit tests for hook scripts
   - Integration tests for full hook chain
   - Regression tests for hook failures

---

### 🔵 LOW PRIORITY

8. **Documentation**:
   - Create `docs/HOOKS_ARCHITECTURE.md` explaining hook system
   - Document each hook's purpose, inputs, outputs
   - Add troubleshooting guide

9. **Code quality**:
   - Standardize error handling patterns across all hooks
   - Extract common DB connection logic to shared module
   - Add type hints to all functions

---

## Hook Dependency Graph

```
SessionStart (once)
├─→ generate_project_settings.py (sync config from DB)
├─→ deploy_components.py (sync CLAUDE.md, skills from DB)
├─→ Log session to claude.sessions
├─→ Load todos from claude.todos (with auto-completion)
├─→ Check messages from claude.messages
├─→ Load work items (features, feedback, build_tasks)
└─→ RAG pre-load (semantic search for relevant vault docs)

UserPromptSubmit
└─→ rag_query_hook.py (inject vault knowledge via RAG)

PreToolUse (Write/Edit)
├─→ context_injector_hook.py (inject standards/context)
└─→ standards_validator.py (validate against standards)

PreToolUse (mcp__postgres__execute_sql)
└─→ context_injector_hook.py (inject Data Gateway standards)

PostToolUse (TodoWrite)
└─→ todo_sync_hook.py (sync to claude.todos)

PostToolUse (30+ MCP tools)
└─→ mcp_usage_logger.py (log to claude.mcp_usage)

SubagentStart
└─→ subagent_start_hook.py (log to claude.agent_sessions)

Stop
└─→ stop_hook_enforcer.py (periodic reminders)

PreCompact (manual/auto)
└─→ precompact_hook.py (remind to re-examine CLAUDE.md/vault)

SessionEnd (prompt-only, no script execution)
```

---

## Files Requiring Immediate Attention

### 🔴 Fix Now (Security)
1. `scripts/mcp_usage_logger.py` - Remove hardcoded credentials
2. `scripts/stop_hook_enforcer.py` - Remove hardcoded credentials
3. `scripts/subagent_start_hook.py` - Remove hardcoded credentials

### 🟡 Review Soon
4. `scripts/session_startup_hook_enhanced.py` - Delete or document
5. `.claude-plugins/claude-family-core/scripts/validate_db_write.py` - Consider enabling
6. `.claude-plugins/claude-family-core/scripts/validate_claude_md.py` - Consider enabling
7. `.claude-plugins/claude-family-core/scripts/validate_parent_links.py` - Audit purpose
8. `.claude-plugins/claude-family-core/scripts/validate_phase.py` - Audit purpose
9. `.claude-plugins/claude-family-core/scripts/check_doc_updates.py` - Audit purpose

---

## Conclusion

The Claude Family hook system is **well-architected** with:
- ✅ Modern `claude.*` schema usage throughout
- ✅ Comprehensive error handling
- ✅ Self-healing configuration (database → files)
- ✅ RAG integration for knowledge injection
- ✅ Persistent todo tracking
- ✅ MCP usage analytics

**Critical Issue**: 3 scripts have hardcoded database credentials that must be fixed immediately.

**Overall Grade**: B+ (would be A if credentials fixed)

---

**Version**: 1.0
**Created**: 2026-01-19
**Updated**: 2026-01-19
**Location**: C:\Projects\claude-family\docs\HOOKS_AND_SCRIPTS_AUDIT_REPORT.md
