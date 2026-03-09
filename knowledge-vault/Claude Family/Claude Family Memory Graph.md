---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.750037'
tags:
- quick-reference
- claude-family
---

# Claude Family Memory Graph

> **RETIRED — January 2026**
>
> The `memory` MCP server and its JSONL backing file at `C:\claude\shared\memory\claude-family-memory.json` have been decommissioned.
>
> **Replacement**: Use `project-tools` cognitive memory tools:
> - `remember(content, memory_type)` — store knowledge (auto-routes to short/mid/long tier)
> - `recall_memories(query, budget)` — retrieve context before tasks
> - `consolidate_memories(trigger)` — lifecycle management
>
> This document is preserved as a historical reference only.

---

MCP memory server for persistent entity storage (RETIRED).

## Former Location

`C:\claude\shared\memory\claude-family-memory.json` (no longer maintained)

## Former Usage

- Create entities with observations
- Create relations between entities
- Search/query the graph
- Persists across sessions

See also: [[MCP configuration]], [[Claude Family Postgres]]
---

**Version**: 2.0 (Added RETIRED notice; preserved content as historical reference)
**Created**: 2025-12-26
**Updated**: 2026-03-09
**Location**: Claude Family/Claude Family Memory Graph.md