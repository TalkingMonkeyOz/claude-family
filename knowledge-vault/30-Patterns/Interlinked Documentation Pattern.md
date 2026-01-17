---
projects:
- claude-family
tags:
- pattern
- documentation
- planning
synced: false
---

# Interlinked Documentation Pattern

When documentation exceeds 300 lines, **chunk it into linked documents** - NEVER summarize away detail.

---

## The Problem

> "Short documents don't mean lack of detail"

When Claude gets the "300+ lines" warning, the temptation is to summarize. This is **dangerous** because:
- Details get lost
- Implementation drifts from original intent
- Features become different from what was discussed

---

## The Pattern

```
┌─────────────────────────────────────────────────┐
│              PLAN-OVERVIEW.md                    │
│  - Summary (what, why)                          │
│  - Index (links to detail docs)                 │
│  - Navigation (see also, related)              │
└────────────┬───────────────────┬───────────────┘
             │                   │
    ┌────────▼────────┐  ┌──────▼───────┐
    │ PLAN-STEP-1.md  │  │ PLAN-STEP-2.md│
    │ - Full detail   │  │ - Full detail │
    │ - Code examples │  │ - Code examples│
    │ - Back-link ↑   │  │ - Back-link ↑ │
    └─────────────────┘  └───────────────┘
```

---

## Structure Requirements

### 1. Overview Document (Index)

```markdown
# Feature Name - Overview

## Summary
[2-3 sentences: what it does, for whom, why]

## Index

| Section | Document | Status |
|---------|----------|--------|
| Data Models | [[Feature Name - Data Models]] | Complete |
| API Design | [[Feature Name - API Design]] | In Progress |
| UI Components | [[Feature Name - UI Components]] | Pending |

## Related
- [[Existing System X]] - How this integrates
- [[Pattern Y]] - Design pattern used
```

### 2. Detail Documents (Linked)

```markdown
# Feature Name - Data Models

**Parent**: [[Feature Name - Overview]]

## TypeScript Interfaces

[Full interface definitions here - NO summarizing]

## Database Schema

[Full CREATE TABLE statements]

## Mapping

[How TS types map to DB columns]

---

**Next**: [[Feature Name - API Design]]
**Back**: [[Feature Name - Overview]]
```

---

## Anti-Patterns

| Bad Practice | Why It's Bad | Correct Approach |
|-------------|--------------|------------------|
| "See code for details" | Details get lost | Write it in the doc |
| Summarizing to fit limit | Lost requirements | Split into linked docs |
| One 500-line doc | Hard to find, lost-in-middle | Split into 3-5 docs |
| Vague references | No traceability | Use specific wiki-links |

---

## When to Use

Use this pattern when:
1. **Plan exceeds 200 lines** - Split at logical boundaries
2. **Multiple implementation steps** - One doc per step
3. **Complex requirements** - Overview + detail docs
4. **Crash recovery needed** - DB stores plan_data, docs have full detail

---

## Database Integration

The Overview document goes in `features.plan_data`:

```sql
UPDATE claude.features
SET plan_data = '{
  "overview_doc": "knowledge-vault/10-Projects/nimbus-mui/F68-API-Uploads-Overview.md",
  "detail_docs": [
    "F68-Data-Models.md",
    "F68-API-Design.md",
    "F68-UI-Components.md"
  ],
  "requirements": [...],
  "risks": [...]
}'::jsonb
WHERE short_code = 68;
```

Session resume can then show: "See [[F68-API-Uploads-Overview]] for full plan"

---

## Checklist for New Plans

- [ ] Created overview with index table
- [ ] Each section has its own document
- [ ] Every detail doc has back-link to overview
- [ ] Overview stored in `features.plan_data`
- [ ] All docs have version footer
- [ ] No section over 300 lines

---

## Example: API Uploads Feature

```
nimbus-mui/plans/
├── F68-API-Uploads-Overview.md      # Index + summary (80 lines)
├── F68-Data-Models.md               # TypeScript interfaces (150 lines)
├── F68-ODataCacheService.md         # Cache service design (120 lines)
├── F68-Upload-Service.md            # Upload logic (180 lines)
└── F68-UI-Components.md             # React components (200 lines)
```

Total: 730 lines of detail, split into 5 navigable docs.

---

## Related

- [[Feature Planning System]] - DB-backed task tracking
- [[Markdown Documentation Standards]] - Chunking rules
- [[Structured Autonomy Workflow]] - Plan → Implement pattern

---

**Version**: 1.0
**Created**: 2026-01-17
**Location**: knowledge-vault/30-Patterns/Interlinked Documentation Pattern.md
