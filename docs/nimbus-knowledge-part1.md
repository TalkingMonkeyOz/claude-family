---
projects:
- claude-family
- nimbus-mui
tags:
- mcp
- nimbus
- shutdown-review
synced: false
---

# nimbus-knowledge: Data and Dependents

Part 1 of 2. See [overview and recommendation](nimbus-knowledge-shutdown-review.md).

---

## Database Schema: nimbus_context

A dedicated schema in `ai_company_foundation`, separate from `claude.*`. Created before the current claude schema and designed to be isolated from it.

### Tables Used by the Server

| Table | Rows | Purpose |
|-------|------|---------|
| `api_entities` | 366 | OData entity definitions (static import from `$metadata`) |
| `api_properties` | 7,357 | Property definitions, one row per entity property |
| `code_patterns` | 6 | Reusable integration patterns |
| `project_learnings` | 6 | Lessons learned (success/failure/pattern types) |
| `project_facts` | 22 | Constraints, architecture decisions, API quirks |

Additional tables in the schema (not exposed by MCP):
- `nimbus_context.projects` — project registry
- `nimbus_context.claude_sessions` — legacy session history (linked to old `claude_family` schema)
- `nimbus_context.project_decisions` — architecture decisions

The entity and property tables are **static reference data** imported once from the Nimbus OData `$metadata` endpoint. They do not change unless the Nimbus API version changes. The three small tables (34 rows combined) are writable by Claude during sessions.

---

## Tools Exposed (10 total)

| Tool | Direction | Purpose |
|------|-----------|---------|
| `get_entity_schema` | Read | Full property definitions, grouped by key/required/optional/navigation |
| `search_entities` | Read | Keyword search across entity names |
| `get_code_pattern` | Read | Find patterns by keyword |
| `get_learnings` | Read | Filter lessons by type or keyword |
| `get_facts` | Read | Filter constraints by category or type |
| `get_dependency_order` | Read | Hardcoded entity creation sequence (no DB query) |
| `get_stats` | Read | Row counts across all tables |
| `add_learning` | Write | Capture new lesson |
| `add_fact` | Write | Record new constraint or architecture note |
| `add_code_pattern` | Write | Store new code pattern |

The write tools use a hardcoded project UUID (`550e8400-e29b-41d4-a716-446655440001`).

---

## Project Dependency Matrix

### Active Dependents (configured + referenced in CLAUDE.md)

| Project | enabledMcpjsonServers | CLAUDE.md guidance |
|---------|-----------------------|--------------------|
| nimbus-odata-configurator | Yes | "Use nimbus-knowledge for ALL entity/property lookups"; 4 explicit pre-coding checks |
| monash-nimbus-reports | Yes | "Use nimbus-knowledge before implementing ANY Nimbus API integration"; 4 checks |
| nimbus-mui | Yes | Listed in MCP servers table; less prominently mandated |

### Configured but Inactive

| Project | mcp_configs block | enabledMcpjsonServers | CLAUDE.md |
|---------|--------------------|----------------------|-----------|
| nimbus-import | Yes | No | Not mentioned |
| nimbus-user-loader | Yes | No | Not mentioned |

Both inactive projects have the configuration block but the server is not in `enabledMcpjsonServers` and not referenced in CLAUDE.md. These are configuration orphans — the server would not load for those projects.

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: C:\Projects\claude-family\docs\nimbus-knowledge-part1.md
