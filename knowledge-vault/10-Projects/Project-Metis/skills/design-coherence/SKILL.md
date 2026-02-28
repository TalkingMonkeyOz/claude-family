---
name: design-coherence
description: "Cross-reference and validate large multi-area design projects for contradictions, gaps, terminology drift, and assumption conflicts. Use this skill whenever working on a project with 5+ interconnected design documents, multiple areas/workstreams with overlapping concerns, or when the user says 'run coherence check', 'check for contradictions', 'cross-reference the design', 'consolidation review', 'are the areas consistent?', or 'what conflicts exist?'. Also trigger when resuming Phase 6 consolidation work on Project METIS, or when any large design project needs systematic cross-area validation. This skill is the AI-native replacement for manual design reviews — it decomposes what no single context window can hold into structured, pairwise comparisons against an indexed knowledge base."
---

# Design Coherence Checker

## Why This Skill Exists

Large design projects — like METIS with 9 interconnected areas, 68+ decisions, and 35+ vault files — exceed what any single Claude session can hold in context. The design lives across many documents, each written in separate sessions. Nobody has read all of them together. Contradictions, gaps, and terminology drift accumulate silently.

The traditional approach (load everything, review) doesn't work with AI context limits. This skill provides an incremental, repeatable process that any Claude instance can follow to cross-reference a multi-area design without needing to hold it all in memory at once.

**Core insight:** Don't try to hold the whole design in context. Build an index of concepts in the database, then pull specific pairs of files to compare when the index shows overlap. The database IS the cross-referencing engine. Claude's job is extraction, comparison, and reporting — not memorisation.

## When To Use This Skill

- Phase 6 (Consolidation) of any METIS-style design project
- Any time you have 5+ design documents with overlapping topics
- When the user asks "are the areas consistent?" or "run a coherence check"
- After completing a multi-session design phase and wanting to verify internal consistency
- Periodically as design evolves to catch drift between areas

## Prerequisites

**Required MCP tools** (project-tools):
- `store_knowledge()` — store extracted concepts
- `recall_knowledge()` — semantic search across concepts
- `link_knowledge()` — create relations (contradicts, supports, extends, etc.)
- `get_related_knowledge()` — traverse knowledge graph
- `create_feedback()` — log findings as design feedback items
- `resolve_feedback()` — close resolved findings
- `store_session_fact()` — persist progress between sessions

**Required MCP tools** (filesystem):
- `read_file()` — read vault markdown files
- `list_directory()` — discover vault structure
- `edit_file()` — update vault files during resolution

**Database tables used** (all existing, no new tables needed):
- `claude.knowledge` — stores extracted design concepts (use `knowledge_category = 'design_concept'`)
- `claude.knowledge_relations` — cross-references between concepts (contradicts, supports, extends, etc.)
- `claude.feedback` — stores findings (type: 'design' for contradictions/gaps, 'improvement' for terminology issues)

## The Five Phases

### Overview

| Phase | Name | What Happens | Who Acts | Output |
|-------|------|-------------|----------|--------|
| 1 | EXTRACT | Read vault files, pull out concepts/decisions/assumptions | Agent | Knowledge entries in DB |
| 2 | MAP | Query concepts, identify cross-area overlaps and gaps | Agent | Cross-reference report |
| 3 | CHECK | Load relevant file pairs, compare for conflicts | Agent | Findings list |
| 4 | REPORT | Present findings grouped by severity | Agent → **HUMAN** | Prioritised findings |
| 5 | RESOLVE | Human decides, agent updates files and index | **HUMAN** → Agent | Updated vault + index |

**The loop:** Phases 3→4→5 repeat. After resolving findings and updating vault files, re-run CHECK to verify fixes and catch any new issues. The loop ALWAYS breaks at Phase 4 (REPORT) — the agent never auto-resolves.

```
Extract → Map → Check → Report → [HUMAN DECIDES] → Resolve → re-Check → Report → [HUMAN DECIDES] → ... until clean
```

**CRITICAL ANTI-DRIFT RULE:** The agent must NEVER auto-resolve findings. Contradictions may be intentional distinctions between areas. Terminology differences may be deliberate. The agent does the tedious cross-referencing work; the human makes judgment calls on what's a real problem vs intentional variation.

---

### Phase 1: EXTRACT

**Goal:** Turn prose vault files into queryable knowledge entries in the database.

**Process per vault file:**

1. Read the vault file
2. For each substantive concept, decision, assumption, or dependency found, extract:
   - **concept_name**: Short label (e.g., "Haiku classifier gatekeeper", "Tiered knowledge validation")
   - **area**: Which METIS area this belongs to (e.g., "Knowledge Engine", "Integration Hub")
   - **source_file**: Vault file path
   - **concept_type**: One of: `decision`, `assumption`, `requirement`, `dependency`, `principle`, `constraint`
   - **description**: 2-3 sentence summary of what this concept says
   - **related_concepts**: Names of other concepts this references or depends on
3. Store each concept using:

```
store_knowledge(
    title='[concept_name]',
    description='[description]. Source: [source_file]. Area: [area]. Type: [concept_type].',
    knowledge_type='fact',
    knowledge_category='design_concept',
    applies_to_projects=['Project-Metis'],
    source='design-coherence-extraction',
    confidence_level=80
)
```

**What to extract (and what to skip):**

EXTRACT:
- Architectural decisions (e.g., "PostgreSQL + pgvector as primary data store")
- Technology choices (e.g., "Voyage AI for embeddings")
- Assumptions about how areas interact (e.g., "Knowledge Engine provides retrieval for all other areas")
- Constraints (e.g., "Australian data residency", "No core code modification")
- Principles (e.g., "Build for nimbus first, generalise second")
- Dependencies between areas (e.g., "PS Accelerator depends on Knowledge Engine API")
- Numbered/named decisions from decision trackers

SKIP:
- Background context and motivation paragraphs
- Examples and illustrations (unless they contain implicit decisions)
- Future/aspirational features marked as Phase 3+ or "later"
- Meeting logistics and session management notes

**Pacing:** Do NOT attempt all vault files in one session. Process 3-5 files per session. Use `store_session_fact()` to track which files have been extracted:

```
store_session_fact(
    fact_key='coherence_extract_progress',
    fact_value='Extracted: [file1, file2, file3]. Remaining: [file4, file5, ...]',
    fact_type='data'
)
```

**Quality check after each file:** Count concepts extracted. If fewer than 3 from a substantive file, you may be skipping too much. If more than 20, you may be too granular — consolidate related items.

---

### Phase 2: MAP

**Goal:** Build a cross-reference picture from the extracted concepts.

**Process:**

1. Query all design_concept knowledge entries:
```
recall_knowledge(
    query='design concept METIS',
    project='Project-Metis',
    limit=50
)
```

2. For each concept that appears in 2+ areas, note the overlap. These are the candidates for Phase 3 checking.

3. Look for gaps: concepts referenced by one area but never defined. For example, if PS Accelerator references "Knowledge Engine API contract" but no knowledge entry defines what that API looks like.

4. Look for terminology drift: same concept called different things in different areas (e.g., "Implementation Accelerator" vs "PS Accelerator" vs "Delivery Accelerator").

5. Create knowledge relations for clear connections:
```
link_knowledge(
    from_knowledge_id='[concept_A_id]',
    to_knowledge_id='[concept_B_id]',
    relation_type='relates_to',  # or 'contradicts', 'supports', 'extends', 'depends_on'
    notes='Both discuss authentication model. Area 1 says JWT, Area 7 says API key.'
)
```

6. Produce a MAP SUMMARY — a structured list of:
   - **Overlap hotspots**: concepts appearing in 3+ areas (highest priority for checking)
   - **Potential contradictions**: same topic, different statements
   - **Undefined references**: concept referenced but never specified
   - **Terminology variants**: same thing, different names

Store the map summary as a session fact for continuity:
```
store_session_fact(
    fact_key='coherence_map_summary',
    fact_value='[JSON or structured text of hotspots, contradictions, gaps, terminology]',
    fact_type='data'
)
```

---

### Phase 3: CHECK

**Goal:** For each flagged overlap or potential contradiction, load the relevant vault file sections and compare.

**Process:**

1. For each item from the MAP summary, identify the 2-3 vault files involved.
2. Read only the relevant sections from each file (not the entire file — manage context).
3. Compare directly:
   - Do they agree on facts?
   - Are assumptions aligned?
   - Is terminology consistent?
   - Do they make contradictory claims about the same topic?
   - Does one assume a dependency the other doesn't mention?
4. Classify each finding:

| Severity | Description | Example |
|----------|-------------|---------|
| **CONTRADICTION** | Two areas make incompatible claims | Area 1 says "JWT auth", Area 7 says "API key only" |
| **GAP** | Concept referenced but never defined | PS Accelerator references "config generation API" — no spec exists |
| **ASSUMPTION CONFLICT** | Different areas assume different things about the same topic | Area 3 assumes Jira is primary tracker, Area 6 assumes Git-native |
| **TERMINOLOGY DRIFT** | Same concept, different names | "PS Accelerator" / "Implementation Accelerator" / "Delivery Accelerator" |
| **DUPLICATION** | Same decision/spec written in 2+ places (maintenance risk) | Auth model described in both Orchestration and Constrained Deployment docs |
| **STALENESS** | One area's version of a concept is clearly outdated | Area 2 still references "9 workstreams" when there are now "9 areas + constrained deployment" |

5. For each finding, log it:
```
create_feedback(
    project='Project-Metis',
    feedback_type='design',       # for contradictions, gaps, assumption conflicts
    title='[SHORT_LABEL]: [area1] vs [area2]',
    description='[Detailed description of the conflict, with quotes from each source file. Include file paths.]',
    priority='high'               # high for contradictions, medium for gaps, low for terminology
)
```

**STOP HERE.** Do not proceed to resolution. Present findings to the human.

---

### Phase 4: REPORT

**Goal:** Present findings clearly for human decision-making.

**Format the report as:**

```
## Design Coherence Report — [Date]

### Summary
- X contradictions found
- Y gaps identified  
- Z terminology issues
- Files checked: [list]
- Files remaining: [list]

### Contradictions (Action Required)
1. **[SHORT_LABEL]** — [Area A] vs [Area B]
   - Area A says: "[quote/summary]" (source: [file])
   - Area B says: "[quote/summary]" (source: [file])
   - **Suggested resolution:** [agent's recommendation — human decides]
   - FB code: [FBxxx]

### Gaps (Missing Specifications)
1. **[CONCEPT]** — referenced in [Area A] but not defined
   - Where it's referenced: [file, context]
   - What's missing: [description]
   - FB code: [FBxxx]

### Terminology & Duplication (Cleanup)
1. **[TERM1] vs [TERM2]** — same concept, different names
   - Used in: [areas/files]
   - Suggested canonical term: [recommendation]
   - FB code: [FBxxx]
```

**After presenting:** Ask the human which findings to resolve, which to accept as intentional, and which need discussion. Mark accepted-as-intentional findings as `wont_fix` in the feedback table. Mark items for resolution as `in_progress`.

---

### Phase 5: RESOLVE

**Goal:** Implement the human's decisions.

For each finding the human wants resolved:

1. **Update vault files** — edit the source files to resolve the contradiction, fill the gap, or standardise terminology. Use `edit_file()`.
2. **Update knowledge entries** — if a concept's description changed, update the corresponding knowledge entry.
3. **Update relations** — if a contradiction was resolved, change the `contradicts` relation to `supports` or remove it.
4. **Close the feedback item** — `resolve_feedback(feedback_id='FBxxx', resolution_note='[what was changed]')`
5. **Track progress** — update session fact with resolution count.

After resolving, return to Phase 3 (CHECK) to verify fixes didn't introduce new issues.

---

## Session Management

This skill spans multiple sessions. Use these patterns for continuity:

**At session start:**
```
recall_session_fact(fact_key='coherence_extract_progress')
recall_session_fact(fact_key='coherence_map_summary')
recall_session_fact(fact_key='coherence_check_progress')
```

**At session end:**
```
save_checkpoint(focus='Design coherence [phase X]', progress_notes='[what was done]')
store_session_fact(fact_key='coherence_[phase]_progress', fact_value='[status]', fact_type='data')
```

**Between sessions:** The database IS the continuity mechanism. Knowledge entries, relations, and feedback items persist. The session facts track which phase you're in and what's been processed.

## Capture Conventions

When using Phase 1 (EXTRACT) or capturing concepts during brainstorms, follow the [[Design Capture Conventions]] in the vault procedures folder. Key points:

- Use structured prefixes: `DECIDED:`, `ASSUMED:`, `DEPENDS:`, `CONSTRAINT:`, `PRINCIPLE:`, `REQUIRED:`
- Always include `Area:` and `Type:` tags in the content
- Target 3-8 concepts per session
- Track progress with `store_session_fact("design_capture_count", ...)`

---

## Scope and Limitations

**What this skill does:**
- Systematic cross-referencing of design documents
- Detection of contradictions, gaps, and terminology drift
- Structured reporting for human decision-making
- Tracking of resolution progress

**What this skill does NOT do:**
- Replace human judgment on what's a real contradiction vs intentional variation
- Guarantee completeness (extraction quality depends on the agent following instructions)
- Work in a single session for large projects (multi-session by design)
- Auto-resolve findings (the human always decides)

**Semantic drift risk:** The biggest risk is the agent "tidying up" intentional distinctions during resolution. Different areas MAY use different terminology deliberately. The agent must present findings, not assume they're errors. This is why the loop breaks at REPORT, not at RESOLVE.

---

*Skill version: 1.0 | Created: 2026-03-01 | For use with: project-tools MCP + filesystem MCP*
*Companion: FB164 (large-scale design tracking skill)*
