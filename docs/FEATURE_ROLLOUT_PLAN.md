# Feature Rollout Plan

**Version**: 1.0
**Created**: 2025-12-06
**Status**: Active

---

## Overview

Plan for rolling out advanced Claude capabilities across all projects in the Claude Family ecosystem.

---

## Active Projects

| Project | Phase | Priority |
|---------|-------|----------|
| claude-family | Implementation | 1 (Infrastructure) |
| mission-control-web | Implementation | 2 (UI) |
| ATO-Tax-Agent | Implementation | 3 (Business Logic) |
| nimbus-user-loader | Implementation | 4 (ETL) |

---

## Features to Roll Out

### Tier 1: Immediate (Infrastructure Complete)

| Feature | Status | Projects Enabled |
|---------|--------|------------------|
| 1M Token Context Window | Ready | All via desktop shortcut |
| Token-Efficient Tool Use | Ready | Native in Claude 4 (auto) |
| Interleaved Thinking | Ready | Opus agents, coordinators |
| Tool Use Examples | Ready | 5 agents updated |
| Git Worktrees | Ready | SOP created |

### Tier 2: In Progress

| Feature | Status | Next Steps |
|---------|--------|------------|
| Tool Search for Deferred Loading | Built | Integrate into orchestrator |
| Programmatic Tool Calling | In Progress | Add to coordinator prompts |
| LLM-as-Judge | Ready | Built into reviewer-sonnet |

### Tier 3: Planned

| Feature | Status | Prerequisites |
|---------|--------|---------------|
| Computer Use Tool | Planned | Docker/sandbox setup |
| Visual Feedback Loop | Planned | Computer Use working |
| Sandboxed Autonomous Operation | Planned | Docker environment |

---

## Rollout Strategy

### Phase 1: claude-family (This Week)

1. **Enable 1M context** for long planning sessions
2. **Deploy Tool Search MCP** to reduce agent context usage
3. **Update all agent specs** with tool examples
4. **Test interleaved thinking** on complex tasks

### Phase 2: mission-control-web (Next Sprint)

1. **Add MCW-specific agents** with UI tool examples
2. **Enable LLM-as-Judge** for code review before merge
3. **Configure worktrees** for parallel UI work

### Phase 3: ATO-Tax-Agent (Following Sprint)

1. **Enable 1M context** for complex tax scenarios
2. **Add domain-specific tool examples** (tax rules, calculations)
3. **Configure security-opus** for tax data handling

### Phase 4: nimbus-user-loader (As Needed)

1. **Add ETL-specific examples** (data transformations)
2. **Enable postgres tool examples** for batch operations

---

## Monitoring & Metrics

### Feature Usage Tracking

```sql
-- Track feature usage
INSERT INTO claude.feature_usage (feature_id, project_id, session_id, agent_type)
VALUES (:feature_id, :project_id, :session_id, :agent_type);

-- Query feature adoption
SELECT 
    f.feature_name,
    p.project_name,
    COUNT(*) as usage_count,
    COUNT(DISTINCT session_id) as unique_sessions
FROM claude.feature_usage fu
JOIN claude.features f ON fu.feature_id = f.feature_id
JOIN claude.projects p ON fu.project_id = p.project_id
GROUP BY f.feature_name, p.project_name
ORDER BY usage_count DESC;
```

### Key Metrics to Track

| Metric | How to Measure | Target |
|--------|----------------|--------|
| Context Token Savings | Compare before/after with Tool Search | 50%+ reduction |
| Agent Success Rate | Track success in feature_usage | 90%+ |
| Feature Adoption | Usage count per project | All projects using within 2 weeks |
| Session Length | Compare with 1M context enabled | 2x longer sessions possible |

---

## Integration Points

### 1. Session Start Hook

Update `/session-start` to log feature availability:

```python
# Check which features are enabled for this project
enabled_features = check_project_features(project_id)
log_feature_availability(session_id, enabled_features)
```

### 2. Agent Spawn Logging

Update orchestrator to log feature usage:

```python
# In orchestrator spawn_agent
if spec.get('betas'):
    log_feature_usage('1m_context' if 'context-1m' in spec['betas'] else None)
```

### 3. Tool Search Integration

Update agent configs to use Tool Search:

```json
{
  "deferred_mcp_servers": ["postgres", "memory"],
  "tool_search_enabled": true
}
```

---

## Success Criteria

1. **All 4 projects** have access to 1M context via shortcut
2. **Tool Search** reduces agent startup tokens by 50%+
3. **Feature usage** tracked in database
4. **No regressions** in agent task completion rates

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Beta features unstable | Test in claude-family first |
| Tool Search index incomplete | Start with 13 core tools, expand |
| Monitoring overhead | Async logging, minimal impact |

---

## Next Actions

1. [x] Desktop shortcut updated with 1M option
2. [x] Feature usage table created
3. [ ] Integrate Tool Search MCP into orchestrator
4. [ ] Add feature logging to session hooks
5. [ ] Test 1M context on complex planning task
6. [ ] Document feature adoption in project CLAUDE.md files

---

**Maintained by**: Claude Family Infrastructure
