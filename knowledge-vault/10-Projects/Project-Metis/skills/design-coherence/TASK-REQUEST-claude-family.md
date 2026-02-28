---
tags:
  - project/Project-Metis
  - type/task-request
  - target/claude-family
created: 2026-03-01
from: Claude Desktop (Project METIS Session 9)
---

# Task Request: Design Coherence Skill — Infrastructure Support

## Context

Project METIS (AI Development Lifecycle Platform) has completed Phase 4 of its design lifecycle — 9 areas brainstormed, 68+ decisions captured, 35+ vault files, 10 features registered. We're approaching Phase 6 (Consolidation) where we need to cross-reference all design documents for contradictions, gaps, and terminology drift.

FB164 identified this as a general capability need: how do you track large interconnected designs when using AI with limited context windows?

The solution: a 5-phase repeatable skill (Extract → Map → Check → Report → Resolve) that uses the existing knowledge table as a cross-referencing index. The skill file has been written and is at:

```
C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\skills\design-coherence\SKILL.md
```

## What Claude Desktop Has Done

1. ✅ Designed the 5-phase approach with John (validated conversationally over 2 sessions)
2. ✅ Confirmed existing database infrastructure is sufficient (no new tables needed)
3. ✅ Written the complete SKILL.md with step-by-step instructions for each phase
4. ✅ Identified the anti-drift safeguard: loop always breaks at REPORT phase, agent never auto-resolves

## What Claude Family / Claude Code Console Needs To Do

### Task 1: Register the skill in skill_content table (REQUIRED)

The skill needs to be discoverable by any Claude instance via `find_skill()`. Store it in `claude.skill_content`:

```sql
INSERT INTO claude.skill_content (
    content_id, name, description, category, source, 
    applies_to, task_keywords, content, priority, active
) VALUES (
    gen_random_uuid(),
    'design-coherence',
    'Cross-reference and validate large multi-area design projects for contradictions, gaps, and terminology drift. Use when consolidating designs with 5+ documents.',
    'design',
    'Project-Metis',
    ARRAY['Project-Metis'],
    ARRAY['coherence', 'cross-reference', 'consolidation', 'contradiction', 'design review', 'gap analysis', 'terminology drift'],
    -- content: read from the SKILL.md file --
    '<full skill content>',
    1,
    true
);
```

The content field should be the full text of the SKILL.md file. Also generate the `description_embedding` via Voyage AI so it's semantically searchable.

### Task 2: Verify knowledge_category conventions (NICE TO HAVE)

The skill uses `knowledge_category = 'design_concept'` for extracted concepts. Check that this doesn't conflict with existing category conventions. No column_registry change needed — knowledge_category is a free-text field — but document the convention.

### Task 3: Verify feedback conventions (NICE TO HAVE)

The skill logs findings as `feedback_type = 'design'`. Verify this is appropriate. The column_registry shows 'design' as "visual/UX issue" — our usage is broader (design contradictions/gaps). If this is a problem, we could use 'change' or 'improvement' instead. Or update the column_registry description to include architectural design issues.

## What Is NOT Needed

- ❌ No new database tables
- ❌ No new MCP server or tools
- ❌ No new MCP endpoints
- ❌ No code changes to project-tools

The existing `store_knowledge()`, `recall_knowledge()`, `link_knowledge()`, `create_feedback()`, and `resolve_feedback()` tools already do everything the skill needs. The skill is purely instructional — it tells the agent what sequence to call existing tools in.

## Decision Log

| Decision | Outcome | Rationale |
|----------|---------|-----------|
| Skill file vs MCP server | Skill file | MCP server adds no value at this stage. Skill + existing project-tools is sufficient. MCP is future upgrade path for automated triggers. |
| New tables vs reuse existing | Reuse existing | knowledge + knowledge_relations + feedback tables handle all storage needs. Adding tables would be premature. |
| Looping strategy | Loop breaks at REPORT phase | Agent never auto-resolves. Prevents semantic drift where agent "tidies" intentional distinctions. Human judgment at every resolution. |
| Delivery mechanism | Vault file + skill_content registration | Vault for version control and human readability. skill_content for agent discoverability. |

## File Location

```
C:\Projects\claude-family\knowledge-vault\10-Projects\Project-Metis\skills\design-coherence\SKILL.md
```

## Priority

Medium. This supports Phase 6 consolidation work which is next on the METIS design lifecycle after Phase 5 second-pass iteration. Not blocking anything immediately, but needed before we can do systematic cross-area validation.

---
*From: Claude Desktop | Project METIS Session 9 | 2026-03-01*
