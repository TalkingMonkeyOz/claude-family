# CLAUDE.md Breadcrumb Quality Audit

**Date**: 2026-04-11
**Scope**: All 19 active profiles in `claude.profiles` with `config->'behavior'`

## Summary

Most project CLAUDE.md files use a **template-generated boilerplate** pattern for Information Discovery that provides generic tool references (`recall_memories("topic keyword")`, `recall_entities("search term")`) without project-specific search terms. Only 4 of 16 real projects have any specific breadcrumbs beyond the template defaults.

**Template problem**: The `claude-md-standard v1.0` template produces identical Information Discovery and Work Tracking sections across all projects. These sections consume ~40% of each CLAUDE.md but provide zero project-specific guidance.

## Audit Results

| Project | Size | Specific | Vague | Dead Links | Gaps |
|---------|------|----------|-------|------------|------|
| ATO-Infrastructure | 2846 | 2 | 5 | 0 | - No `recall_memories("Azure Bicep")` or `recall_memories("IaC patterns")` pointers; - No link to related ATO-Tax-Agent project's entities; - References `knowledge-vault/20-Domains/awesome-copilot-reference/agents/` (file path, not DB) |
| ATO-tax-agent | 3512 | 2 | 4 | 0 | - `recall_memories("ATO tax rules")` is good but needs more: deduction categories, compliance rules, two-layer system; - No pointer to tax table entities; - No `recall_entities("tax threshold")` or similar |
| ATO-Tax-Agent (dupe) | 3512 | 2 | 4 | 0 | - Exact duplicate of ATO-tax-agent -- should be deduplicated |
| claude-desktop-config | 3064 | 0 | 6 | 0 | - Zero project-specific breadcrumbs; - Should reference `recall_memories("MCP config")`, `recall_memories("Claude Desktop")` |
| claude-family | 4976 | 5 | 4 | 0 | - Best of the bunch: has `PROBLEM_STATEMENT.md`, `ARCHITECTURE.md`, `get_schema()`, `search_processes("keyword")`; - Missing specific memory queries for hooks, embedding pipeline, protocol injection |
| claude-family-manager-v2 | 3307 | 1 | 5 | 0 | - Only specific ref is `docs/COMPONENT_MAPPING.md`; - Notes it's superseded by claude-manager-mui but no link to migration knowledge; - Should have `recall_memories("WPF UI patterns")` |
| claude-manager-mui | 3534 | 0 | 6 | 0 | - Zero specific breadcrumbs despite being an active project; - Should reference finance-mui theme, Tauri patterns, build phases; - No `recall_memories("MUI theme")` or `recall_entities("claude manager feature")` |
| coder-haiku | 126 | 0 | 0 | 0 | - Role profile, not a project -- N/A for breadcrumbs |
| coder-sonnet | 202 | 0 | 0 | 0 | - Role profile, not a project -- N/A for breadcrumbs |
| reviewer-sonnet | 131 | 0 | 0 | 0 | - Role profile, not a project -- N/A for breadcrumbs |
| finance-mui | 3544 | 1 | 5 | 1 | - One specific: `recall_memories("finance MUI")`; - Dead wiki-link: `[[prd-personal-finance-system]]` (vault wiki-links don't work in DB-first model); - Missing SMSF entity pointers, Tauri patterns |
| global | 7468 | 3 | 4 | 0 | - Has `recall_memories("agent selection")`, `recall_memories("new project SOP")`, `recall_memories("add MCP server")`; - Still says "RAG auto-searches" in SOPs table (stale claim removed from main but lingers here); - Large but mostly tool index, not knowledge pointers |
| Global Configuration | 12539 | 0 | 8 | 5 | - STALE: v3.1 from 2026-01-10, heavily outdated; - Dead wiki-links: `[[Work Tracking Schema]]`; - Dead vault paths: `40-Procedures/New Project SOP.md`, `40-Procedures/Add MCP Server SOP.md`, `40-Procedures/Config Management SOP.md`, `40-Procedures/Session Lifecycle - Overview.md`, `knowledge-vault/30-Patterns/Agent Selection Decision Tree.md`, `knowledge-vault/30-Patterns/Structured Autonomy Workflow.md`; - References `mcp__orchestrator__spawn_agent`, `mcp__orchestrator__check_inbox` (dead MCP); - References `mcp__python-repl__execute_python` (dead MCP); - References `ToolSearch select:` pattern (dead feature); - Still uses emoji anti-patterns; - Should be deactivated or merged into `global` |
| monash-engagement | 3569 | 1 | 5 | 0 | - One specific: `recall_entities(query, entity_type="odata_entity")` with "366 entities available"; - Missing pointers to Nimbus domain concepts, Confluence/Jira knowledge, deliverable structure |
| nimbus-import | 3755 | 4 | 3 | 0 | - Good: lists OData entities, specific API endpoints, entity creation URLs, SQL insert targets; - Could add `recall_memories("nimbus auth")`, `recall_memories("import validation")` |
| nimbus-mui | 3774 | 6 | 2 | 0 | - Best project-specific breadcrumbs: OData entities, domain concepts, `get_secret()` for credentials, entity dependency order, reference files to port, two-tier caching; - Has "RECALL FIRST" reminder; - Could still add specific memory queries for known gotchas |
| nimbus-user-loader | 3958 | 5 | 4 | 0 | - Good domain-specific rules: auth endpoint quirk, POST semantics, `GetFlexibleVal()`, batch mode, session affinity; - Roslyn-first workflow is specific; - Missing `recall_memories("nimbus auth quirks")` to surface DB knowledge |
| project-metis | 4399 | 6 | 3 | 0 | - Best overall: specific entity types (`decision`, `gate_deliverable`), `get_build_board("project-metis")`, 13 validated decisions inlined, context discipline rules; - Could add `recall_memories("metis gate")` for gate knowledge |
| trading-intelligence | 3765 | 2 | 5 | 0 | - Has `recall_memories("trading IBKR SMSF")` and detailed safety rules; - Missing pointers to scanner entities, IBKR API patterns, Correction Gauge knowledge |

## Scoring Legend

- **Specific**: References with concrete search terms, file paths, entity types, or inlined domain knowledge (e.g., `recall_memories("nimbus auth")`, `recall_entities("entity", entity_type="odata_entity")`, API endpoint URLs, inlined decision lists)
- **Vague**: Generic tool references from the template (e.g., `recall_memories("topic keyword")`, `recall_entities("search term")`, `unstash("component-name")`)
- **Dead Links**: Wiki-links `[[...]]`, vault file paths, or MCP tool references that no longer resolve in the DB-first model

## Key Findings

1. **Template bloat**: 12 of 16 project profiles use identical boilerplate for Information Discovery and Work Tracking (~1200 chars each). This wastes context window on zero-value instructions.

2. **Duplicate profile**: `ATO-tax-agent` and `ATO-Tax-Agent` are identical (case difference). One should be deactivated.

3. **Stale global profile**: `Global Configuration` (12,539 chars) is heavily outdated (v3.1 from Jan 2026) with 5+ dead references. The current `global` profile (7,468 chars, v5.0) has replaced it. `Global Configuration` should be deactivated.

4. **Best practices** (from nimbus-mui, project-metis): Inline domain-specific rules, list concrete entity types for recall, include "RECALL FIRST" reminders with specific search terms, reference specific files to port/consult.

5. **Worst offenders**: claude-desktop-config, claude-manager-mui, and claude-family-manager-v2 have zero project-specific knowledge pointers despite being active projects.

## Recommendations

1. **Deactivate** `Global Configuration` profile (superseded by `global`)
2. **Deactivate** duplicate `ATO-tax-agent` or `ATO-Tax-Agent`
3. **Strip template boilerplate** from project CLAUDE.md files -- the global profile already provides tool indexes
4. **Add specific breadcrumbs** to each project: concrete `recall_memories()` terms, `recall_entities()` with entity_type filters, and inlined domain rules (follow nimbus-mui and project-metis patterns)
5. **Remove dead vault path references** from any profile still pointing to `40-Procedures/*.md` or `knowledge-vault/30-Patterns/*.md`
6. **Create a "breadcrumb checklist"** for the CLAUDE.md template: every project MUST have at least 3 specific `recall_memories()` terms and 2 specific `recall_entities()` queries

---

**Version**: 1.0
**Created**: 2026-04-11
**Updated**: 2026-04-11
**Location**: docs/claude-md-breadcrumb-audit.md
