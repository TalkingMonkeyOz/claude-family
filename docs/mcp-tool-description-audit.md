# MCP Tool Description Audit — project-tools

**Date**: 2026-03-13
**Scope**: All 55 tools in `mcp-servers/project-tools/server_v2.py`
**Method**: Reviewer-sonnet analysis against MCP description best practices

---

## Summary

| Rating | Count | % |
|--------|-------|---|
| Good | 19 | 35% |
| Needs Work | 36 | 65% |

## Fixes Applied (This Session)

### Critical (Invisible to Claude)

| Tool | Issue | Fix |
|------|-------|-----|
| `store_knowledge` | `# LEGACY` comment above decorator, not in docstring | Added `LEGACY: Prefer remember()` as first line of docstring |
| `recall_knowledge` | Same — `# LEGACY` invisible to MCP | Added `LEGACY: Prefer recall_memories()` as first line |
| `graph_search` | Same pattern | Added `LEGACY: Prefer recall_memories()` as first line |

### High Priority

| Tool | Issue | Fix |
|------|-------|-----|
| `update_work_status` | Missing deprecation signal in docstring | Added `DEPRECATED: Use advance_status()` as first line |
| `remember` | Docstring said ">85% similar" but threshold is 0.75 | Fixed to ">75% similar", added quality gate note |
| `update_protocol` | No risk warning despite system-wide blast radius | Added WARNING about system-wide injection + cross-ref to `get_protocol_history()` |

### Medium Priority (Cross-references)

| Tool Pair | Issue | Fix |
|-----------|-------|-----|
| `check_inbox` / `get_unactioned_messages` | No cross-reference between siblings | Added "use get_unactioned_messages() for actionable only" to check_inbox, added differentiator to get_unactioned |

## Remaining Work (Future Session)

### Medium — Missing Cross-References

| Tool | Should Reference |
|------|-----------------|
| `stash` / `unstash` | Each other + `search_workfiles` |
| `store_session_fact` / `recall_session_fact` | Each other + `list_session_facts` |
| `create_feature` / `add_build_task` / `create_linked_task` | Prefer `create_linked_task` over `add_build_task` |
| `start_work` / `complete_work` | Each other (workflow pair) |
| `catalog` / `recall_entities` | Each other (new entity pair) |

### Low — Description Improvements

These tools work but have vague or minimal descriptions:

- `get_active_sessions` — add context about when useful
- `bulk_acknowledge` — mention it handles array of message_ids
- `get_message_history` — add filtering tips
- `list_recipients` — clarify what "active workspace" means
- `reply_to` — note auto-threading behavior
- `send_message` — note `to_project` validation against workspaces

### Pattern: Good Descriptions (Reference for Future)

Tools with excellent descriptions follow this pattern:
1. **First line**: What it does (imperative, <80 chars)
2. **Use when**: Clear trigger condition
3. **Returns**: Exact shape of response object
4. **Args**: Each param with type, default, and purpose
5. **Cross-refs**: Related tools mentioned by name

Best examples: `advance_status`, `recall_memories`, `remember`, `create_linked_task`, `assemble_context`

---

**Version**: 1.0
**Created**: 2026-03-13
**Updated**: 2026-03-13
**Location**: docs/mcp-tool-description-audit.md
