# ADR-004: Tool Search for Deferred Loading

**Status**: Rejected
**Date**: 2025-12-06
**Rejected**: 2025-12-06
**Context**: Claude Family MCP Context Optimization

---

## Context

Our spawned agents load all MCP tool definitions upfront, consuming significant context tokens. With 6 MCP servers and ~50+ tools, we're using 10K+ tokens just for tool schemas before any actual work begins.

From [Anthropic's Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use):
> "Tool Search Tool discovers tools on-demand rather than loading all definitions upfront... 85% reduction in token usage"

---

## Problem

Current agent spawning:
```
Agent starts → Load ALL tool schemas (10K+ tokens) → Do task → Return
```

This means:
- Agents doing simple file reads still load postgres, memory, orchestrator tools
- Context is wasted on tools that won't be used
- Longer tasks hit context limits faster

---

## Decision

**REJECTED** - Tool Search pattern is not viable with Claude Code CLI.

---

## Why It Doesn't Work

### The Fundamental Issue

Claude Code CLI **automatically loads all tool schemas** when an MCP server connects. There's no way to:
1. Connect an MCP server without loading its schemas
2. Dynamically inject schemas mid-conversation
3. Defer schema loading to on-demand

### What We Built vs What We Needed

```
WHAT WE BUILT:
┌────────────────────────────────────────────────────────┐
│ 1. Agent loads tool-search MCP + postgres MCP          │
│ 2. Both servers' schemas loaded into context (10K+)    │
│ 3. Agent calls find_tool("database")                   │
│ 4. Tool Search returns postgres schema (redundant!)    │
│ 5. Agent uses postgres tool                            │
│                                                        │
│ Result: NO token savings - schemas already loaded      │
└────────────────────────────────────────────────────────┘

WHAT THE PATTERN REQUIRES:
┌────────────────────────────────────────────────────────┐
│ 1. Agent loads ONLY tool-search MCP (~500 tokens)      │
│ 2. Agent calls find_tool("database")                   │
│ 3. Tool Search returns postgres schema                 │
│ 4. Schema dynamically added to context                 │
│ 5. Agent uses postgres tool                            │
│                                                        │
│ Requirement: Dynamic schema injection (not supported)  │
└────────────────────────────────────────────────────────┘
```

### Where Tool Search DOES Work

The pattern works with **direct API calls** where you control:
- Exactly which tool schemas are sent in each request
- Can dynamically add schemas based on tool search results
- Full control over the `tools` array in API requests

---

## Prototype Built (For Reference)

We built a working Tool Search MCP server:

```
mcp-servers/tool-search/
├── server.py           # MCP server with find_tool, list_categories
└── tool_index.json     # 25 indexed tools with keywords
```

**Status**: Code works, but provides no benefit with Claude Code CLI.

**Recommendation**: Keep for potential future use with direct API integration or MCW scheduler.

---

## Alternative Approaches

### What Actually Works for Token Reduction

1. **Per-Agent MCP Configs** (Current approach)
   - Each agent type has its own `.mcp.json` with only needed servers
   - `coder-haiku` gets filesystem only
   - `python-coder-haiku` gets filesystem + postgres + python-repl
   - Manual but effective

2. **Smaller System Prompts**
   - Reduce verbose instructions
   - Move examples to on-demand retrieval

3. **Use Haiku for Simple Tasks**
   - Faster, cheaper, less context needed
   - Reserve Sonnet/Opus for complex work

---

## Lessons Learned

1. **Read the docs carefully**: Anthropic's pattern assumes direct API control
2. **Claude Code CLI has constraints**: MCP servers = schemas loaded, no exceptions
3. **Prototype before planning**: Would have caught this in 30 minutes of testing

---

## Related

- **ADR-003**: Async Agent Workflow (Accepted)
- **MCW Scheduler**: May benefit from Tool Search via direct API

---

**Version**: 2.0 (Rejected)
**Created**: 2025-12-06
**Updated**: 2025-12-06
**Author**: Claude Family Infrastructure
