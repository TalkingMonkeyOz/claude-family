---
projects:
- claude-family
tags:
- research
- mcp
- mui
- toolsearch
---

# MUI MCP vs ToolSearch Evaluation

## Context

We run 4 MUI-based projects (claude-family, claude-manager-mui, nimbus-mui, monash-nimbus-reports) with 60+ MCP tools across 6-8 servers. This evaluation assesses two mechanisms for MUI coding standards enforcement: the `@mui/mcp` server and Claude Code's built-in ToolSearch.

## 1. MUI MCP Configuration Status

| Project | MUI MCP | Notes |
|---------|---------|-------|
| claude-family | Yes | In `.mcp.json`, global infra project |
| claude-manager-mui | Yes | DB-generated `.mcp.json` |
| nimbus-mui | Yes | Full stack with project-tools, postgres |
| monash-nimbus-reports | Yes | Also has ag-grid MCP |

**Finding**: All 4 projects already have MUI MCP configured. No gaps to fill.

## 2. MUI MCP Capabilities

The `@mui/mcp` server (installed globally via npm at `@mui/mcp`) provides two tools:

| Tool | Purpose |
|------|---------|
| `useMuiDocs` | Fetches llms.txt index files for specific MUI packages and versions |
| `fetchDocs` | Retrieves full documentation pages for specific component URLs |

**How it works**: Two-step retrieval pattern. First call `useMuiDocs` with a package URL (e.g., `@mui/material@5.17.1`) to get a table of contents via llms.txt. Then call `fetchDocs` with specific doc page URLs to get component API details, examples, and usage patterns.

**Supported packages** (from tool definitions in current session):
- `@mui/material` (v5.17.1, v6.4.12, v7.2.0)
- `@mui/x-charts` (v7.29.1, v8.8.0)
- `@mui/x-data-grid` (v7.29.7, v8.8.0)
- `@mui/x-date-pickers` (v7.29.4, v8.8.0)
- `@mui/x-tree-view` (v7.29.1, v8.8.0)
- `@mui/x-common-concepts` (v7.29.7, v8.8.0)

**Coding standards impact**: The MUI MCP does not enforce coding standards directly. It provides on-demand access to official MUI documentation, ensuring Claude uses correct APIs, props, and patterns for the specific version in use. This prevents hallucinated props and outdated API usage.

## 3. Claude Code ToolSearch

ToolSearch is a built-in Claude Code feature that activates automatically when MCP tool definitions exceed ~10K tokens (roughly 10% of context).

**How it works**:
1. Tool definitions are deferred (not loaded into context upfront)
2. A lightweight search index replaces full definitions
3. Claude searches for relevant tools per request using keywords
4. Only 3-5 tools load per query (~3K tokens vs ~55K+ without)

**Impact**: Reduces tool definition overhead by ~85%. A setup with GitHub, Slack, Sentry, etc. drops from ~55K tokens to ~8.7K tokens.

**Key thresholds**:
- Under 10K tokens of tool definitions: loads normally
- Over 10K tokens: ToolSearch activates automatically

**Our situation**: With 60+ tools across 6-8 MCP servers (postgres, project-tools, sequential-thinking, mui, playwright, bpmn-engine, and project-specific servers), we are well above the 10K threshold. ToolSearch is almost certainly active in all our projects.

## 4. Comparison

These are **complementary, not competing** mechanisms:

| Aspect | MUI MCP | ToolSearch |
|--------|---------|------------|
| Purpose | MUI component documentation | Tool definition management |
| Scope | MUI-specific | All MCP tools |
| Activation | On-demand (Claude calls it) | Automatic (>10K tokens) |
| Standards enforcement | Indirect (correct API usage) | None (tool discovery only) |
| Token cost | Per-call (fetches docs when needed) | Reduces upfront overhead |
| Alternative | Manual docs lookup, hallucination | All tools in context (bloated) |

**ToolSearch manages how Claude discovers MUI MCP tools**. Without ToolSearch, the MUI MCP tool definitions sit in context permanently. With ToolSearch, they load only when Claude needs MUI help. They work together.

## 5. Recommendation

**Option C: Both** -- keep MUI MCP on all React/MUI projects, let ToolSearch manage loading.

### Rationale

1. **MUI MCP is already deployed** on all 4 projects. No action needed.
2. **ToolSearch is automatic**. No configuration required. It already manages our 60+ tools.
3. **They solve different problems**: MUI MCP provides accurate component docs; ToolSearch prevents those tool definitions from bloating context.
4. **Version-awareness matters**: Our projects span MUI v5, v6, and v7. The MUI MCP serves version-specific docs, preventing cross-version API confusion.

### No action items required

- All projects already have MUI MCP configured
- ToolSearch activates automatically
- No coding standards gaps identified

### One consideration

The MUI MCP adds 2 tools to the tool count. With ToolSearch active, these 2 tools are deferred until needed, so the overhead is negligible. If a project does not use MUI at all, removing the MUI MCP saves a process spawn but has no context impact (ToolSearch defers it anyway).

## Sources

- [MUI MCP Documentation](https://mui.com/material-ui/getting-started/mcp/)
- [MUI X MCP Documentation](https://mui.com/x/introduction/mcp/)
- [Claude Tool Search API Docs](https://platform.claude.com/docs/en/agents-and-tools/tool-use/tool-search-tool)
- [MCP Tool Search Guide](https://www.atcyrus.com/stories/mcp-tool-search-claude-code-context-pollution-guide)
- [Anthropic Advanced Tool Use](https://www.anthropic.com/engineering/advanced-tool-use)

---
**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: knowledge-vault/10-Projects/claude-family/mui-mcp-toolsearch-evaluation.md
