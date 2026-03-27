---
projects:
- claude-family
- nimbus-mui
tags:
- context-management
- progressive-disclosure
- entity-catalog
- F137
---

# Progressive Disclosure for AI Agent Context

## Problem
AI agents working on data-heavy projects (e.g., 366 OData entities) fill context windows quickly when retrieval tools return full detail on every call. `recall_entities` in the Claude Family entity catalog returns full JSONB properties (avg 1.5KB, max 8.7KB per entity, up to 65KB per search call).

## Industry Research (2026-03)

### Proven Approaches
- **Strata (YC X25)**: 4-step progressive discovery for 400+ tools. 405K→6K tokens (67x reduction). Steps: discover categories → get actions → get details → execute.
- **Anthropic Context Engineering Guide**: "Maintain lightweight identifiers and dynamically load data at runtime via tools." Claude Code Skills system is itself progressive disclosure.
- **Speakeasy Comparison**: Progressive discovery vs semantic search at 400-tool scale. Progressive more reliable for complex tasks. Hybrid performs best.
- **Claude Code Issue #27208**: Hierarchical deferred tool discovery requested. Closed as duplicate of #23508 (lazy MCP tool loading). Anthropic tracking this.
- **Letta/MemGPT**: OS-inspired memory hierarchy — core memory (RAM) + archival (disk) + recall (history).
- **Hierarchical RAG**: Multi-level retrieval with context condensation. Key finding: 2-3 levels max, deeper causes fragmentation.

### Key Principles
1. **Quality of metadata determines quality of routing** (Honra.io) — write summaries for machine consumption, not humans
2. **2-3 levels maximum** — deeper hierarchies cause context fragmentation
3. **Hybrid search + progressive disclosure performs best** — semantic search for finding, progressive disclosure for payload control
4. **Make the default right** — return summaries by default, full detail on opt-in

## Our Design: Computed Summary with Progressive Detail (F137)

### Architecture
- Add `summary` TEXT column to `claude.entities` — auto-computed from properties at `catalog()` write time
- `recall_entities(query)` returns summaries by default (~200 bytes/result vs 1,500)
- `recall_entities(query, detail="full")` returns full properties (current behavior)
- `recall_entities(entity_id="xxx")` returns single entity full detail

### Smart Summary Format (OData)
```
Staff (Key: StaffId Int32). Nav: User, Contract, ShiftAssignment, StaffRole. Props [12]: StaffCode, FirstName, LastName, Email, StartDate, IsActive, ...
```

### Why This Pattern
- Zero sync complexity (summary is derived from properties, not separately maintained)
- 87% context reduction per call (28KB→2KB average)
- Backward compatible (existing calls unchanged, detail available on opt-in)
- Self-documenting (summaries include hint: "use detail='full' for all properties")
- Matches Anthropic's own Skills architecture pattern

### Discoverability
1. **Primary**: Updated MCP tool schema description (automatic — Claude reads tool schemas every turn)
2. **Secondary**: Updated storage-rules.md with retrieval guidance
3. **Tertiary**: Memory entry for cross-session awareness
4. **Default behavior** is the most powerful mechanism — summaries returned without any parameter change

## Trade-offs Considered

| Approach | Reduction | Effort | Sync Risk | Verdict |
|----------|-----------|--------|-----------|---------|
| Smart Summary (chosen) | 87% | Half day | Zero | Best ROI for our scale |
| Strata 4-step discovery | 95%+ | 1-2 days | Medium (groups) | Over-engineered — our problem is payload, not discovery |
| Hybrid (summary + browse) | 87-95% | 1 day | Low | Nice-to-have later via tags |
| Capping results | Variable | Trivial | None | Rejected — hides information, makes things worse |

## What This Does NOT Solve
- SQL result bloat (524 calls/month, separate pagination solution needed)
- Session handoff accumulation (needs archival lifecycle)
- System prompt overhead (addressed by F158)
- MCP tool schema overhead at 60+ tools (future: Strata-style tool discovery)

## Sources
- Anthropic: Effective Context Engineering for AI Agents
- Klavis/Strata: Less is More - 4 MCP Design Patterns
- Speakeasy: 100x Token Reduction - Progressive Discovery vs Semantic Search
- Claude Code Issue #27208: Hierarchical Deferred Tool Discovery
- Honra: Progressive Disclosure for AI Agents
- Letta/MemGPT: Virtual Context Management

---
**Version**: 1.0
**Created**: 2026-03-27
**Updated**: 2026-03-27
**Location**: knowledge-vault/30-Patterns/progressive-disclosure-ai-context.md
