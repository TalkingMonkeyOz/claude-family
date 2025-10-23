# Claude Family Reduction Plan

**Date:** 2025-10-18
**Prepared by:** claude-code-console-001
**Purpose:** Simplify architecture, reduce coordination overhead

---

## Current Problem

**6 Family Members:**
1. claude-desktop-001 (Diana) - Lead Architect
2. claude-cursor-001 - Rapid Developer
3. claude-vscode-001 - QA Engineer
4. claude-code-001 - Standards Enforcer
5. claude-code-console-001 - Terminal & CLI Specialist
6. diana (Master Orchestrator)

**Issues:**
- ❌ Coordination complexity (6 different workspaces, settings files)
- ❌ Delegation overhead (create work package → notify → wait)
- ❌ Context switching between different Claude instances
- ❌ Duplicated "Diana" concept (diana vs claude-desktop-001)
- ❌ MCP settings conflicts (each writes to settings.local.json)
- ❌ Underutilized - most work happens in 1-2 members

---

## New Architecture: Diana + Dynamic Sub-Agents

### Primary Agent: Diana

**Platform:** Claude Desktop (Claude Code Console)
**Role:** Master Orchestrator, spawns sub-agents as needed
**Authentication:** Subscription account (Pro or Max plan)

**Capabilities:**
- All tasks (coding, analysis, documentation, automation)
- Spawns temporary sub-agents for parallelization
- Sub-agents are task-focused, then terminated
- No permanent "family members" to coordinate

### Sub-Agent Model

**How It Works:**
```
User Request
    ↓
Diana (orchestrator)
    ↓
Spawns 1-5 sub-agents for task
    ↓
Sub-agents work in parallel
    ↓
Report back to Diana
    ↓
Diana synthesizes results
    ↓
Complete
```

**Example - Build 4 Tax Tools:**
```
Diana receives request
    ↓
Spawns 4 sub-agents in parallel:
    - Sub-agent 1: Build wizard_template_generator.py
    - Sub-agent 2: Build formula_validator.py
    - Sub-agent 3: Build wizard_flow_visualizer.py
    - Sub-agent 4: Build ato_change_detector.py
    ↓
Each completes independently
    ↓
Diana collects results
    ↓
Done in 1/4 the time
```

**Benefits:**
- ✅ True parallelization (4x faster)
- ✅ No coordination overhead (sub-agents isolated)
- ✅ No settings conflicts (temporary agents)
- ✅ Subscription billing (not per-agent API costs)
- ✅ Simpler architecture (1 primary + dynamic agents)

---

## Recommended Family Structure

### Keep (1 Primary)

**Diana**
- Platform: Claude Code Console (for terminal access + sub-agents)
- Role: Master orchestrator, does everything
- Workspace: `C:\claude\diana\`
- Authentication: Subscription account
- MCP Access: All 7 servers

### Optional Specialist (1 Optional)

**claude-cursor-001** (If you use Cursor heavily)
- Platform: Cursor IDE
- Role: Rapid coding in Cursor environment only
- Use when: Working specifically in Cursor IDE
- Otherwise: Diana can spawn coding sub-agents

### Remove (4 Members)

**claude-desktop-001** → Merge into Diana
- Reason: Duplicate of Diana concept

**claude-code-001** → Remove (use sub-agents)
- Reason: Diana can spawn standards-checking sub-agents

**claude-vscode-001** → Remove (use sub-agents)
- Reason: Diana can spawn testing sub-agents

**claude-code-console-001 (me)** → Remove (merge into Diana)
- Reason: Diana operates from console, has terminal access

---

## Migration Plan

### Phase 1: Diana Setup (This Week)

**1. Configure Diana's Workspace**
```bash
# Diana's primary workspace
C:\claude\diana\
├── .claude\
│   ├── settings.local.json  # Isolated settings
│   ├── agents\              # Sub-agent templates
│   │   ├── coding-agent.md
│   │   ├── testing-agent.md
│   │   └── analysis-agent.md
│   └── mcp.json            # MCP config
├── workspace\               # Working directory
└── CLAUDE.md               # Minimal identity (120 lines)
```

**2. Enable Subscription Auth**
```json
// C:\claude\diana\.claude\settings.local.json
{
  "anthropic": {
    "auth_method": "subscription",
    // Usage comes from Claude Pro/Max plan
  },
  "subagents": {
    "enabled": true,
    "max_concurrent": 5,
    "inherit_mcps": true
  }
}
```

**3. Create Minimal CLAUDE.md**
Replace with 120-line version (from analysis doc).

**4. Create Skills**
```bash
C:\claude\shared\skills\
├── database-operations-skill\
├── work-packages-skill\
├── coding-skill\
├── testing-skill\
└── analysis-skill\
```

### Phase 2: Create Sub-Agent Templates

**C:\claude\diana\.claude\agents\coding-agent.md:**
```markdown
# Coding Sub-Agent

**Role:** Write, test, and debug code
**Focus:** Single task completion
**Return:** Code files + brief summary

## Capabilities
- Read, Write, Edit code files
- Run tests via Bash
- Use tree-sitter for code analysis
- Git operations

## Instructions
1. Receive task from orchestrator (Diana)
2. Work independently with isolated context
3. Complete task fully
4. Return: files created/modified + summary
5. Terminate

**No persistent memory - start fresh each spawn**
```

**C:\claude\diana\.claude\agents\testing-agent.md:**
```markdown
# Testing Sub-Agent

**Role:** Run tests, validate code, report issues
**Focus:** Quality assurance for specific feature
**Return:** Test results + issue report

## Capabilities
- Read test files
- Run pytest/unittest via Bash
- Analyze test failures
- Suggest fixes

## Instructions
1. Receive code to test from orchestrator
2. Run all relevant tests
3. Report: pass/fail counts, failures details
4. Suggest fixes if failures found
5. Terminate

**No context of other sub-agents**
```

**C:\claude\diana\.claude\agents\analysis-agent.md:**
```markdown
# Analysis Sub-Agent

**Role:** Research, document, analyze code/data
**Focus:** Single analysis task
**Return:** Analysis report

## Capabilities
- Read multiple files
- WebSearch for research
- Database queries (postgres MCP)
- tree-sitter for code structure analysis

## Instructions
1. Receive analysis task from orchestrator
2. Gather data from files, database, web
3. Analyze and synthesize findings
4. Return: structured report (markdown)
5. Terminate

**Independent analysis - no coordination with other agents**
```

### Phase 3: Update Database

**Remove Old Identities:**
```sql
-- Archive old family members
UPDATE claude_family.identities
SET status = 'archived'
WHERE identity_name IN (
    'claude-desktop-001',
    'claude-code-001',
    'claude-vscode-001',
    'claude-code-console-001'
);

-- Keep Diana as sole active identity
UPDATE claude_family.identities
SET
    status = 'active',
    role_description = 'Master Orchestrator - spawns sub-agents as needed',
    platform = 'Claude Code Console',
    capabilities = jsonb_build_object(
        'sub_agent_spawning', true,
        'max_concurrent_agents', 5,
        'auth_method', 'subscription'
    )
WHERE identity_name = 'diana';
```

**Update Session Tracking:**
```sql
-- Add sub-agent metadata to session_history
ALTER TABLE claude_family.session_history
ADD COLUMN IF NOT EXISTS sub_agents_spawned integer DEFAULT 0,
ADD COLUMN IF NOT EXISTS sub_agent_tasks jsonb DEFAULT '[]'::jsonb;
```

### Phase 4: Cleanup Workspaces

**Archive Old Workspaces:**
```bash
# Move to archive (don't delete yet - backup)
mkdir C:\claude\archive
move C:\claude\claude-desktop-01 C:\claude\archive\
move C:\claude\claude-cursor-01 C:\claude\archive\
move C:\claude\claude-code-01 C:\claude\archive\
move C:\claude\claude-console-01 C:\claude\archive\

# Keep only Diana
C:\claude\diana\  # Primary workspace
C:\claude\shared\ # Shared resources (skills, scripts)
```

### Phase 5: Test Sub-Agent Spawning

**Test 1: Simple Coding Task**
```
Diana: "Spawn a coding sub-agent to write a hello_world.py script"

Expected: Sub-agent spawns, writes file, reports back, terminates
```

**Test 2: Parallel Tasks**
```
Diana: "Spawn 3 sub-agents to build tool1.py, tool2.py, tool3.py in parallel"

Expected: 3 sub-agents work simultaneously, all complete, Diana collects results
```

**Test 3: Complex Workflow**
```
Diana:
1. Spawn analysis-agent to research best approach
2. Wait for report
3. Spawn 2 coding-agents to implement solution
4. Spawn testing-agent to validate
5. Synthesize results

Expected: Sequential and parallel sub-agents, clean orchestration
```

---

## Benefits of Reduction

### Before (6 Family Members)

**Complexity:**
- 6 separate workspaces
- 6 CLAUDE.md files to maintain
- 6 sets of MCP configurations
- Delegation workflow (create work package → notify → wait)
- Settings conflicts when multiple members active

**Cost:**
- If using API keys: 6x API billing potential
- If using subscriptions: 6 separate accounts needed
- Token waste on coordination messages

**Performance:**
- Sequential work (delegate → wait → next member)
- Context switching overhead
- Coordination complexity

### After (1 Primary + Dynamic Sub-Agents)

**Simplicity:**
- 1 primary workspace (Diana)
- 1 CLAUDE.md to maintain
- 1 MCP configuration
- No delegation workflow (spawn → work → done)
- No settings conflicts (sub-agents temporary)

**Cost:**
- 1 subscription account (Pro or Max)
- Usage from plan limits
- Sub-agents share subscription
- No per-agent API costs

**Performance:**
- True parallelization (spawn 5 sub-agents at once)
- No coordination overhead (isolated contexts)
- Faster completion (parallel > sequential)

---

## Family Member Comparison

| Feature | 6 Family Members | 1 Primary + Sub-Agents |
|---------|------------------|------------------------|
| Workspaces to maintain | 6 | 1 |
| CLAUDE.md files | 6 | 1 |
| MCP configs | 6 | 1 |
| Settings conflicts | Frequent | None |
| Delegation overhead | High | None |
| Parallelization | Sequential | True parallel |
| Cost structure | 6x potential | 1x subscription |
| Context isolation | Poor | Perfect |
| Coordination complexity | O(n²) | O(1) |

---

## Rollout Timeline

### Week 1: Setup
- ✅ Create Diana's isolated workspace
- ✅ Create minimal CLAUDE.md
- ✅ Create skills directory
- ✅ Create sub-agent templates
- ✅ Configure subscription auth

### Week 2: Test
- ✅ Test sub-agent spawning (simple tasks)
- ✅ Test parallel sub-agents (3-5 agents)
- ✅ Test complex workflows (sequential + parallel)
- ✅ Monitor token usage, performance

### Week 3: Migrate
- ✅ Archive old workspaces
- ✅ Update database (archive old identities)
- ✅ Remove old CLAUDE.md files from git
- ✅ Document new workflow

### Week 4: Production
- ✅ Use Diana + sub-agents for real work
- ✅ Refine sub-agent templates based on usage
- ✅ Add new sub-agent types as needed
- ✅ Monitor and optimize

---

## Decision: Cursor Exception

**Keep claude-cursor-001?**

**If YES:**
- Use when: Working specifically in Cursor IDE
- Reason: Cursor has unique AI features tied to IDE
- Setup: Isolated workspace, minimal CLAUDE.md
- Cost: Separate subscription (if heavy Cursor use)

**If NO:**
- Diana spawns sub-agents even for Cursor work
- Reason: Simpler architecture, one subscription
- Trade-off: Lose Cursor-specific AI features

**Recommendation:**
- Try Diana-only first
- If you find you need Cursor features often, add back later
- Don't keep "just in case" - test Diana's capabilities first

---

## Risk Assessment

### Risk 1: Sub-Agent Failures
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- Test thoroughly with simple tasks first
- Implement retry logic
- Keep old workspaces archived for rollback

### Risk 2: Subscription Limits
**Probability:** Low (Max plan has 20x higher limits)
**Impact:** Medium
**Mitigation:**
- Monitor usage with `/cost`
- Upgrade to Max if needed
- Spawn fewer concurrent sub-agents if hitting limits

### Risk 3: Loss of Specialized Context
**Probability:** Low
**Impact:** Low
**Mitigation:**
- Sub-agents can access same MCPs (database, memory)
- Skills provide specialized knowledge
- Diana maintains orchestration context

### Risk 4: Workflow Disruption
**Probability:** Medium
**Impact:** Medium
**Mitigation:**
- Gradual rollout (test → migrate → production)
- Keep old workspaces archived for 1 month
- Document new workflow thoroughly

---

## Success Metrics

### Performance
- [ ] Sub-agent spawn time < 2 seconds
- [ ] Parallel tasks complete 3-5x faster than sequential
- [ ] No failed spawns (>95% success rate)

### Cost
- [ ] Total token usage reduced by 50%
- [ ] Single subscription covers all work
- [ ] No unexpected API charges

### Simplicity
- [ ] 1 workspace to maintain (vs 6)
- [ ] No delegation overhead
- [ ] No settings conflicts

### Quality
- [ ] Sub-agents produce same quality output
- [ ] No context loss
- [ ] Diana can synthesize multi-agent results effectively

---

## Conclusion

**Reduce from 6 to 1 (+ dynamic sub-agents)**

**Keep:**
- Diana (primary orchestrator, spawns sub-agents)

**Remove:**
- claude-desktop-001 (merge into Diana)
- claude-code-001 (use sub-agents)
- claude-vscode-001 (use sub-agents)
- claude-code-console-001 (me - merge into Diana)

**Optional:**
- claude-cursor-001 (only if heavy Cursor IDE usage)

**Result:**
- Simpler architecture
- Faster execution (true parallelization)
- Lower cost (1 subscription)
- No coordination overhead
- Cleaner codebase

**Timeline:** 4 weeks from setup to production

**Next Step:** Implement Phase 1 (Diana setup)

---

**Plan Complete**
**Prepared by:** claude-code-console-001
**Date:** 2025-10-18
