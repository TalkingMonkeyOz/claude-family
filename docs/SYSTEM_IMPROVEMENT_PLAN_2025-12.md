# Claude Family System Improvement Plan

**Created**: 2025-12-16
**Status**: PROPOSED
**Author**: Claude Opus 4.5 + John

---

## Executive Summary

The Claude Family system has evolved into a sophisticated multi-layered platform but suffers from **complexity debt**. Analysis shows:
- 50 database tables, but only ~15 have meaningful data
- 32 workflows defined, but limited actual usage
- 80% of infrastructure is underutilized
- Testing infrastructure exists but is empty (0 test runs)

This plan proposes a **5-phase improvement** to right-size the system while retaining proven capabilities.

---

## Current State Analysis

### Database Utilization

| Category | Tables | With Data (>10 rows) | Utilization |
|----------|--------|---------------------|-------------|
| Core | 50 | 15 | 30% |
| Empty | - | 4 (test_runs, feature_usage, capability_usage, workflow_state) | 0% |
| Near-empty | - | 8 (1-5 rows) | <10% |

**Top Used Tables:**
1. document_projects: 2,163 rows
2. documents: 1,885 rows
3. process_runs: 370 rows
4. build_tasks: 212 rows
5. sessions: 196 rows
6. knowledge: 161 rows

### Directory Structure

| Location | Purpose | Status |
|----------|---------|--------|
| C:\Projects | Active code repos | KEEP - primary |
| C:\claude | Infrastructure/shared | KEEP - clean up |
| C:\Users\johnd\OneDrive\Documents\AI_projects | Legacy location | ARCHIVE |
| C:\venvs | Python environments | CONSOLIDATE |

### Active Resources

**Projects (5 active of 23):**
- claude-family (infrastructure)
- mission-control-web (UI dashboard)
- nimbus-user-loader (work)
- nimbus-import (work)
- ATO-Tax-Agent (work)

**Identities (2 active of 12):**
- claude-desktop
- claude-code-unified

**Claude Instances (operational):**
- Claude 1, 3, 4, 5, 6, 7, 8 generic
- Claude Desktop (integrated console)

---

## Reference Sources

### PID Development Process (pid-process.jsx)
A 5-phase systematic approach:
1. Initial Document Review (gap analysis)
2. Question Resolution (real data validation)
3. Technical Validation (data flow, API, DB)
4. Application Design (UI, data, logging)
5. Final Review (E2E walkthrough, checklist)

**Key Anti-Patterns Identified:**
- Don't assume - verify against real data
- Don't batch questions endlessly - iterate
- Don't skip edge cases - nulls, duplicates
- Don't forget logging - needed for debugging
- Don't hardcode - use lookups/caches
- Don't trust field names - verify schema

### Research Document Recommendations
- Adopt **Explore -> Plan -> Code -> Commit** pattern
- Embrace **Test-Driven Development (TDD)**
- Keep **CLAUDE.md lean** - only enforced rules
- Use **structured workflows** with clear phases
- **Archive unused** tables and workflows
- Focus on **90% guideline adherence**

### Anthropic Best Practices (2025)

From [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices):
- **Feedback loop**: gather context -> take action -> verify work -> repeat
- **Extended thinking**: "think" < "think hard" < "think harder" < "ultrathink"
- **TDD workflow**: tests first, verify failures, implement to pass
- **Headless mode**: `--dangerously-skip-permissions` for automation
- **Custom slash commands**: store templates in `.claude/commands/`

From [Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system):
- **Orchestrator-worker pattern**: lead agent coordinates specialists
- **One agent, one job**: keep responsibilities focused
- **Full production tracing**: monitor agent decisions
- **Compress global state**: plan + decisions + artifacts only

---

## Improvement Plan

### Phase A: Cleanup (Week 1)

#### A1. Directory Consolidation

**ARCHIVE** (move to backup):
```
C:\Users\johnd\OneDrive\Documents\AI_projects\
  -> C:\Users\johnd\OneDrive\Documents\AI_projects_ARCHIVE_2025-12\
```

**C:\Projects Cleanup:**
| Directory | Action | Reason |
|-----------|--------|--------|
| claude-family | KEEP | Active infrastructure |
| mission-control-web | KEEP | Active UI project |
| nimbus-user-loader | KEEP | Active work |
| nimbus-import | KEEP | Active work |
| ATO-Tax-Agent | KEEP | Active work |
| claude-pm | REVIEW | May merge into claude-family |
| claude-pm-v1 | ARCHIVE | Old version |
| claude-mission-control | ARCHIVE | Superseded by MCW |
| roslyn-mcp | ARCHIVE | Duplicate |
| RoslynMCP | ARCHIVE | Duplicate |
| test-diana-project | ARCHIVE | Test artifact |
| test | ARCHIVE | Test artifact |
| llama-ato-assistant | ARCHIVE | Inactive |
| ai-workspace | REVIEW | Check if active |
| tax-calculator | REVIEW | Check if active |

**C:\claude Cleanup:**
| File/Directory | Action | Reason |
|----------------|--------|--------|
| start-claude.bat | KEEP | Main launcher |
| shared/ | KEEP | Shared resources |
| plugins/ | KEEP | Active plugins |
| agent-workspaces/ | KEEP | Agent isolation |
| archive/ | REVIEW | Check contents |
| CORRECT_ARCHITECTURE.md | ARCHIVE | Historical |
| GLOBAL_MCP_FIX.md | ARCHIVE | Historical |
| MCP_LOADING_FIX.md | ARCHIVE | Historical |
| LAUNCHER_GUIDE.md | ARCHIVE | Historical |

**C:\venvs Consolidation:**
Keep only essential environments:
- mcp (MCP development)
- mission-control (MCW project)
- testing (general testing)
Archive the rest.

#### A2. Database Cleanup

**DROP/ARCHIVE Empty Tables:**
```sql
-- Tables with 0 rows - safe to drop
DROP TABLE IF EXISTS claude.test_runs;
DROP TABLE IF EXISTS claude.feature_usage;
DROP TABLE IF EXISTS claude.capability_usage;
DROP TABLE IF EXISTS claude.workflow_state;
```

**CONSOLIDATE Near-Empty:**
- `ideas` (1 row) -> merge concept into `feedback` (type='idea')
- `reminders` (1 row) -> replace with slash command

**ARCHIVE Stale Data:**
```sql
-- Archive sessions older than 90 days
UPDATE claude.sessions
SET status = 'archived'
WHERE session_start < NOW() - INTERVAL '90 days'
  AND status != 'archived';

-- Archive inactive projects
UPDATE claude.projects
SET status = 'archived'
WHERE project_name NOT IN (
  'claude-family', 'mission-control-web',
  'nimbus-user-loader', 'nimbus-import', 'ATO-Tax-Agent'
);
```

---

### Phase B: Simplification (Week 2)

#### B1. Process Workflow Reduction

**FROM**: 32 workflows
**TO**: 8 core workflows

| Workflow | Keep/Archive | Reason |
|----------|--------------|--------|
| Session Start/End | KEEP | Working, essential |
| Bug Fix | KEEP | High value |
| Feature Development | KEEP | Core workflow |
| Code Review | KEEP | Quality gate |
| Documentation Update | KEEP | Staleness prevention |
| Database Change | KEEP | Migration safety |
| Test Suite | NEW | Enforce TDD |
| Deployment | KEEP | Release safety |
| Other 24 workflows | ARCHIVE | Until proven needed |

#### B2. Standards Simplification

Create **Quick Reference Cards** (single page each):

**DEVELOPMENT_QUICKREF.md:**
```markdown
# Development Quick Reference

## Naming
- Functions: camelCase (JS/TS), snake_case (Python)
- Components: PascalCase
- Files: kebab-case

## Required
- [ ] Error handling on all async
- [ ] No console.log (use logger)
- [ ] Type hints (TS/Python)

## Forbidden
- No hardcoded IDs/secrets
- No console.log in production
- No TODO comments without ticket
```

#### B3. Agent Consolidation

**KEEP** (proven performers):
| Agent | Use Case | Model |
|-------|----------|-------|
| coder-haiku | General coding | Haiku |
| python-coder-haiku | Python specific | Haiku |
| reviewer-sonnet | Code review | Sonnet |
| web-tester-haiku | E2E testing | Haiku |
| architect-opus | Planning | Opus |
| researcher-opus | Research | Opus |

**KEEP** (ATO specialist):
| ux-tax-screen-analyzer | ATO screen analysis | Haiku |

**ARCHIVE** (until needed):
- security-sonnet, analyst-sonnet, planner-sonnet
- lightweight-haiku, nextjs-tester-haiku

---

### Phase C: Enhanced Workflows (Week 3-4)

#### C1. Feature Development Workflow (BPMN)

```
┌─────────────────────────────────────────────────────────────────┐
│                  FEATURE DEVELOPMENT WORKFLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌─────────────────────────────────────────┐     │
│  │  START  │───>│ 1. EXPLORATION                          │     │
│  └─────────┘    │    - Load existing code                 │     │
│                 │    - Gap analysis                       │     │
│                 │    - Compile questions                  │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                 ┌─────────────────────────────────────────┐     │
│                 │ 2. RESOLUTION                           │     │
│                 │    - Answer with real data              │     │
│                 │    - Validate assumptions               │     │
│                 │    - Iterate until gaps resolved        │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                 ┌─────────────────────────────────────────┐     │
│                 │ 3. VALIDATION                           │     │
│                 │    - Data flow verification             │     │
│                 │    - API/DB confirmation                │     │
│                 │    - Insert/Update patterns             │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                 ┌─────────────────────────────────────────┐     │
│                 │ 4. DESIGN                               │     │
│                 │    - UI specification                   │     │
│                 │    - Data management                    │     │
│                 │    - Logging/debugging                  │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                 ┌─────────────────────────────────────────┐     │
│                 │ 5. IMPLEMENTATION (TDD)                 │     │
│                 │    - Write tests FIRST                  │     │
│                 │    - Verify tests fail                  │     │
│                 │    - Code to pass tests                 │     │
│                 │    - Refactor                           │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                 ┌─────────────────────────────────────────┐     │
│                 │ 6. REVIEW                               │     │
│                 │    - E2E walkthrough                    │     │
│                 │    - Code review agent                  │     │
│                 │    - Checklist validation               │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                 ┌─────────────────────────────────────────┐     │
│                 │ 7. COMMIT                               │     │
│                 │    - Run full test suite                │     │
│                 │    - Create PR                          │     │
│                 │    - Merge                              │     │
│                 └──────────────┬──────────────────────────┘     │
│                                │                                 │
│                                v                                 │
│                          ┌─────────┐                            │
│                          │   END   │                            │
│                          └─────────┘                            │
└─────────────────────────────────────────────────────────────────┘
```

#### C2. TDD Enforcement

**New Slash Command: /test-first**
```markdown
# Test-First Development

You are now in TDD mode. Follow these steps:

1. **Write Tests First**
   - Generate comprehensive tests for the feature
   - Cover valid AND invalid scenarios
   - Include edge cases (nulls, duplicates, boundaries)

2. **Run Tests - Confirm Failure**
   - Execute the test suite
   - Verify tests fail for the RIGHT reasons
   - Do NOT write implementation yet

3. **Implement to Pass**
   - Write MINIMAL code to pass tests
   - No extra features
   - No premature optimization

4. **Refactor**
   - Clean up code while keeping tests green
   - Extract common patterns
   - Improve readability

$ARGUMENTS
```

**PreCommit Hook Enhancement:**
```python
# Check for test presence
def check_test_coverage(files_changed):
    code_files = [f for f in files_changed if f.endswith(('.py', '.ts', '.tsx'))]
    test_files = [f for f in files_changed if 'test' in f.lower()]

    if code_files and not test_files:
        return False, "No tests included with code changes. Use /test-first"
    return True, "Tests present"
```

#### C3. Context Management Enhancement

**Session Context File Structure:**
```markdown
# Session Context - {date}

## Session ID: {uuid}
## Project: {project_name}
## Duration: {start} - {end}

## What Was Done
- [Bullet points of completed work]

## Key Decisions
- [Important choices made and why]

## Artifacts Created/Modified
- [List of files with brief descriptions]

## Blockers/Issues
- [Any problems encountered]

## Next Steps
1. [Priority 1]
2. [Priority 2]
3. [Priority 3]

## Context for Next Session
[Key information the next session needs to know]
```

#### C4. Self-Enforcing Hooks System

**Problem**: "I'LL FORGET TO USE IT SO WILL YOU" - Manual slash commands get forgotten.

**Solution**: Stop hook with counters that trigger periodic reminders automatically.

**Implementation**: `scripts/stop_hook_enforcer.py`

**Enforcement Schedule**:
| Interval | Action | Reminder |
|----------|--------|----------|
| Every 5 responses | Git check | "Consider committing if you have changes" |
| Every 10 responses | Inbox check | "Run /inbox-check for messages" |
| Every 20 responses | CLAUDE.md refresh | "Re-read CLAUDE.md to refresh context" |
| On code change | Test tracking | "X code files changed without test updates" |

**State Storage**: `~/.claude/state/enforcement_state.json`
```json
{
  "interaction_count": 47,
  "last_git_check": 45,
  "last_inbox_check": 40,
  "last_claude_md_check": 40,
  "code_changes_since_test": 3,
  "files_changed_this_session": ["src/api.ts", "src/utils.ts"]
}
```

**Hook Configuration** (`.claude/hooks.json`):
```json
{
  "Stop": [{
    "hooks": [{
      "type": "command",
      "command": "python \"scripts/stop_hook_enforcer.py\"",
      "timeout": 5
    }]
  }]
}
```

**Status**: PLANNED - Script created, needs testing

#### C5. Knowledge Retrieval System

**Problem**: 161 knowledge entries exist but aren't used. User said: "I need to write a new importer for Nimbus... let me check what knowledge I have on API shifts..."

**Solution**: Auto-query `claude.knowledge` on UserPromptSubmit based on detected topics.

**Implementation**: Enhanced `scripts/process_router.py`

**Topic Detection**:
| Topic | Keywords |
|-------|----------|
| nimbus | nimbus, shift, schedule, employment, employee, roster |
| api | api, odata, rest, endpoint, request, response |
| import | import, importer, loader, sync, migration |
| tax | tax, ato, tfn, abn, bas, payg, super |
| database | database, postgres, sql, query, schema, table |
| react | react, component, hook, state, props, jsx, tsx |

**Injection Format**:
```xml
<relevant-knowledge>
[RELEVANT KNOWLEDGE RETRIEVED]
Found 3 relevant knowledge entries:

### Nimbus API - Shifts Endpoint
**Category**: api
**Tags**: nimbus, shifts, odata
**Source**: API documentation

GET /odata/Shifts returns shift records with EmployeeId, StartTime...
---
</relevant-knowledge>
```

**Query Logic**:
1. Extract keywords from user prompt
2. Map keywords to topics
3. Query `claude.knowledge` with relevance ranking
4. Inject top 5 results as `<relevant-knowledge>`

**Status**: PLANNED - Code added to process_router.py, needs testing

#### C6. LLM Guide MCP (Future)

**Problem**: Sometimes need LLM guidance for lookups and decisions.

**Solution**: MCP server that provides LLM-assisted guidance.

**Proposed Tools**:
| Tool | Purpose |
|------|---------|
| `guide_lookup` | "How do I find X in this codebase?" |
| `guide_decide` | "Which approach should I use for X?" |
| `guide_explain` | "What does X mean in this context?" |

**Status**: NOT STARTED - Needs design approval

---

### Phase D: Documentation & Diagrams (Week 4-5)

#### D1. System Architecture Document

Create `docs/ARCHITECTURE_VISUAL.md` with:

1. **System Overview Diagram**
2. **Data Flow Diagram**
3. **Workflow State Diagrams**
4. **Agent Orchestration Diagram**
5. **Decision Trees**

#### D2. Quick Reference Cards

| Card | Audience | Content |
|------|----------|---------|
| Claude Family Quick Start | New user | 5-minute setup |
| Daily Workflow | Regular user | Session flow |
| Agent Selection | Developer | When to use which agent |
| Emergency Reference | All | Common issues + fixes |

---

### Phase E: Validation & Metrics (Ongoing)

#### E1. Success Metrics

| Metric | Current | Target | How to Measure |
|--------|---------|--------|----------------|
| Table utilization | 30% | 80% | rows > 0 / total tables |
| Workflow completion | Unknown | 90% | completed / started runs |
| Test coverage | 0% | 70% | test_runs / commits |
| Session closure | Unknown | 95% | closed / opened |
| Agent success | ~46% | 80% | success / total spawns |
| Context carryover | Manual | Auto | summaries present |

#### E2. Weekly Review Checklist

- [ ] Check session closure rate
- [ ] Review failed agent runs
- [ ] Identify unused tables/workflows
- [ ] Update documentation if needed
- [ ] Archive stale data

---

## Implementation Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | A: Cleanup | Directories consolidated, DB cleaned |
| 2 | B: Simplification | 8 core workflows, quick refs |
| 3 | C: Workflows (Part 1) | Feature dev workflow, TDD command |
| 4 | C: Workflows (Part 2) | Context management, hooks |
| 5 | D: Documentation | Architecture doc, diagrams |
| 6+ | E: Validation | Metrics tracking, iteration |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Breaking existing work | Archive, don't delete; test before removing |
| Losing valuable data | Full backup before each phase |
| User confusion | Document changes, provide migration guide |
| Over-simplification | Keep archived items recoverable |

---

## Appendix: Files to Create/Modify

### Already Created (Needs Testing)
| File | Status | Description |
|------|--------|-------------|
| `scripts/stop_hook_enforcer.py` | CREATED | Counter-based enforcement |
| `scripts/config.py` | CREATED | Centralized database config |
| `scripts/process_router.py` | MODIFIED | Added knowledge retrieval |
| `.claude/hooks.json` | MODIFIED | Added Stop hook |

### To Create
1. `docs/ARCHITECTURE_VISUAL.md` - System diagrams (DONE - created last session)
2. `docs/standards/DEVELOPMENT_QUICKREF.md` - Dev quick reference
3. `docs/standards/UI_QUICKREF.md` - UI quick reference
4. `docs/standards/API_QUICKREF.md` - API quick reference
5. `.claude/commands/test-first.md` - TDD slash command
6. `.claude/commands/knowledge-add.md` - Add knowledge entry
7. `scripts/cleanup_directories.py` - Automated cleanup script
8. `scripts/archive_database.sql` - Database archive script
9. `mcp-servers/llm-guide/server.py` - LLM guide MCP (future)

---

## Sources

- [Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system)
- [How Anthropic teams use Claude Code](https://www.anthropic.com/news/how-anthropic-teams-use-claude-code)
- [Claude Agent SDK Best Practices](https://skywork.ai/blog/claude-agent-sdk-best-practices-ai-agents-2025/)
- [Multi-Agent Orchestration Patterns](https://dev.to/bredmond1019/multi-agent-orchestration-running-10-claude-instances-in-parallel-part-3-29da)
- [Context Management Best Practices](https://docs.digitalocean.com/products/gradient-ai-platform/concepts/context-management/)

---

**Version**: 1.1
**Status**: IN PROGRESS - Phase C partially implemented
**Last Updated**: 2025-12-16
**Next Steps**:
1. Test C4 (stop_hook_enforcer.py) and C5 (knowledge retrieval)
2. Get user approval before continuing
3. Proceed with Phase A cleanup once testing complete
