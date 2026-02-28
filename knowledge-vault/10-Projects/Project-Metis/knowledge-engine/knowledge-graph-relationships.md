---
tags:
  - project/Project-Metis
  - area/knowledge-engine
  - scope/system
  - type/design
  - topic/knowledge-graph
  - phase/1
projects:
  - Project-Metis
created: 2026-02-25
synced: false
---

# Knowledge Graph — Explicit Relationships Design

> **Scope:** system (generic platform concern — relationship types are defaults, extensible per organisation)
>
> **Resolves:** GAP-1 from session prep doc (flagged CRITICAL by John, Feb 24)
>
> **Problem:** Vector similarity alone finds knowledge that "sounds like" the query but misses structural and causal chains. "This API endpoint → requires this entity → configured by this pattern → implements this compliance rule → has this known support issue" — vector similarity would never connect that chain because each item uses different vocabulary.
>
> **Solution:** Explicit typed relationships between knowledge items, queried via graph traversal alongside vector search.

**Parent:** [[knowledge-engine/README|Knowledge Engine]]
**Cross-cuts:** [[support-defect-intel/README|Support & Defect Intelligence]] (resolution linking), [[quality-compliance/README|Quality & Compliance]] (rule-to-test linking)

---

## 1. Key Principle

**Knowledge items ARE the content.** The Jira ticket, the API spec, the compliance rule — they live in `knowledge_items` with full description, embedding, metadata. That's the knowledge.

**Relationships are a layer ON TOP.** They connect knowledge items without duplicating content. Think of it as a web between filing cabinet entries. The relationship says "this ticket resolves this pattern" — it doesn't copy the ticket or the pattern.

---

## 2. Relationship Types (Defaults)

Eight default types. Extensible per organisation.

| Type | Direction | What It Means | Example |
|------|-----------|--------------|---------|
| `depends_on` | A → B | A requires B to exist or work | "Pay rule endpoint depends on employee entity existing first" |
| `implements` | A → B | A is how you achieve B | "Config pattern X implements compliance rule Y" |
| `resolves` | A → B | A fixes or addresses B | "Support resolution R resolves issue pattern P" |
| `supersedes` | A → B | A replaces B | "Knowledge item V2 supersedes V1" |
| `contradicts` | A ↔ B | A conflicts with B under some conditions | "These two rules can't both apply to casual employees" |
| `relates_to` | A ↔ B | Generic association | Catch-all for connections that don't fit above |
| `part_of` | A → B | A is a component of B | "This endpoint is part of the payroll module" |
| `produces` | A → B | Process A creates output B | "Delivery step X produces configuration artifact Y" |

---

## 3. Schema

```sql
CREATE TABLE knowledge_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organisation_id UUID NOT NULL REFERENCES organisations(id),
    from_item_id UUID NOT NULL REFERENCES knowledge_items(id),
    to_item_id UUID NOT NULL REFERENCES knowledge_items(id),
    relation_type VARCHAR(50) NOT NULL,  -- enum of 8 defaults + custom
    strength FLOAT DEFAULT 1.0 CHECK (strength >= 0 AND strength <= 1),
    notes TEXT,
    created_by VARCHAR(50) NOT NULL,  -- ingestion_auto | ai_suggested | human_manual | promotion
    created_by_user_id UUID REFERENCES users(id),
    validated BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT now(),

    CONSTRAINT no_self_reference CHECK (from_item_id != to_item_id)
);

-- Indexes
CREATE INDEX idx_kr_from ON knowledge_relations(from_item_id);
CREATE INDEX idx_kr_to ON knowledge_relations(to_item_id);
CREATE INDEX idx_kr_org ON knowledge_relations(organisation_id);
CREATE INDEX idx_kr_type ON knowledge_relations(relation_type);
```

---

## 4. How Relationships Get Created

Four mechanisms, from most automated to most manual:

### 4.1 Automatic from Ingestion (`ingestion_auto`, validated = true)

When the ingestion pipeline parses structured sources, it creates relationships automatically:
- API spec parser: endpoint X `depends_on` entity Y (from request body references)
- Support resolution: resolution `resolves` issue pattern (from ticket linking)
- Version updates: new item `supersedes` old item (from version chain)

These come from authoritative sources, so validated = true.

### 4.2 AI-Suggested (`ai_suggested`, validated = false)

Background process analyses new knowledge items against existing knowledge:
- "This new config pattern looks like it `implements` compliance rule Y"
- "This support ticket describes an issue that `contradicts` documented behaviour Z"

Created with validated = false. Human reviews and approves/rejects.

**Learning loop:** Track approval rate per relationship type. As accuracy improves:
- Early: all AI suggestions require human validation (Tier 4 equivalent)
- Later: high-confidence suggestions auto-approved with flag (Tier 3 equivalent)
- Criteria for promotion: >90% approval rate over 50+ suggestions for that type

### 4.3 Manual by Consultant (`human_manual`, validated = true)

Consultants link items they discover are connected during delivery work. Always validated = true (human-authored).

### 4.4 Promotion-Derived (`promotion`)

When knowledge is promoted from client to product level, automatically creates `relates_to` or `supersedes` link to the source item. Part of the promotion workflow.

---

## 5. How /ask Uses Relationships

After vector search returns top-N similar items, graph traversal finds structurally connected items:

```
1. Question comes in
2. Vector search → top-N similar items (existing behaviour)
3. For each top-N item, walk 1-2 hops through knowledge_relations
   - Filter by validated = true (or include ai_suggested with strength > 0.7)
   - Respect organisation_id scope
4. Graph-discovered items NOT already in top-N added with lower priority
5. Assembled context includes both "similar" and "structurally connected" items
6. LLM generates answer from combined set
7. Response cites both source types with relationship context
```

This is the same proven pattern as `graph_search` in project-tools (pgvector seeds + relationship graph walking).

---

## 6. API Endpoint

```
GET /api/v1/knowledge/{id}/graph
  ?relation_types=implements,depends_on    (optional filter)
  &max_hops=2                              (default 2)
  &include_reverse=true                    (walk both directions)
  &min_strength=0.3                        (filter weak relationships)
  &validated_only=false                    (include unvalidated if desired)
```

Returns the subgraph around an item. Used by:
- UIs showing "how does this connect to everything else?"
- Agents exploring context around a knowledge item
- The /ask endpoint internally for graph-augmented retrieval

---

## 7. Strength and Decay

The `strength` field (0-1) allows relationships to weaken over time:
- Frequently accessed relationships maintain strength
- Unused relationships decay gradually (same pattern as project-tools `decay_knowledge`)
- Below a minimum threshold (e.g., 0.05), relationships are archived, not deleted
- Periodic maintenance job handles decay

---

## 8. What This Gives Us That Vector Similarity Doesn't

- **Causal chains:** API endpoint → entity dependency → config pattern → compliance rule
- **Structural knowledge:** "This is part of the payroll module" (vocabulary doesn't overlap)
- **Contradiction awareness:** "These two rules conflict under certain conditions"
- **Resolution tracking:** "This support issue was resolved by this specific pattern"
- **Impact analysis:** "If this compliance rule changes, what config patterns are affected?" (reverse walk from the rule through `implements` relationships)

---

*Resolves: GAP-1 from session prep doc*
*Decided: 2026-02-25, John + Desktop session*
*Next: Write up into knowledge_items deep dive schema, update decisions tracker*
