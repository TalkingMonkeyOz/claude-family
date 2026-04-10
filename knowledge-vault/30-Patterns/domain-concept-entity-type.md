---
projects:
- claude-family
- nimbus-mui
tags:
- storage
- entity-catalog
- domain-concept
- knowledge-management
---

# Domain Concept Entity Type

## What It Is

A `domain_concept` is an entity type in the Reference Library (entity catalog) that acts as a **hub node** — a searchable entry point that describes what a domain concept IS and links to related catalog entries, workfiles, and knowledge across all 5 storage systems.

## When to Create One

Create a domain_concept when you complete significant research on a topic that:
- Spans **multiple storage systems** (e.g., API endpoints in catalog + findings in workfiles + gotchas in knowledge)
- Has **no single entry point** explaining what it is
- Would require a new Claude to query 3+ systems independently to understand

**Examples:** UserSDK, Nimbus REST API, Nimbus OData API, Claude Family Memory System.

## Schema

Required: `name`, `domain`, `purpose`

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Concept name (e.g., "UserSDK") |
| `domain` | string | Domain path (e.g., "nimbus/time2work") |
| `purpose` | string | One-line: what business problem this solves |
| `overview` | string | 2-3 paragraph explanation — what it is, how it works, key behaviors |
| `usage_modes` | array | Key usage patterns or modes of operation |
| `gotchas` | array | Critical watch-outs and known issues |
| `workfile_refs` | array | Pointers to workfile dossiers: `[{component, title}]` |
| `vault_refs` | array | Vault doc paths for deeper reading |
| `verified` | object | Verification status: `{date, environment}` |

## How to Create

```python
catalog("domain_concept", {
    "name": "UserSDK",
    "domain": "nimbus/time2work",
    "purpose": "Bulk user import/update endpoint for Time2Work",
    "overview": "UserSDK is the primary integration endpoint...",
    "usage_modes": ["Simple Mode: INSERT-ONLY", "Mapping Mode: intelligent matching"],
    "gotchas": ["autoCreate sets Payroll to '{UserID}'"],
    "workfile_refs": [{"component": "usersdk-discovery", "title": "Full findings"}],
    "vault_refs": [],
    "verified": {"date": "2026-03-29", "environment": "demo.time2work.com"}
}, project="nimbus-mui", tags=["nimbus", "usersdk", "domain-concept"])
```

After creating, link to child entities via entity_relationships if applicable.

## How It Works in Practice

When a Claude calls `recall_entities("UserSDK")`, the domain_concept appears alongside specific api_endpoint and odata_entity entries. The concept provides the big picture; the specific entries provide the detail.

**Retrieval flow:**
1. `recall_entities("UserSDK")` → concept card + endpoint entries
2. Read concept overview for understanding
3. Follow `workfile_refs` via `unstash()` for deep research
4. Follow entity_relationships for specific child entity detail

## Relationship to Other Storage Systems

| System | Role for Domain Concepts |
|--------|------------------------|
| **Reference Library** | Home — domain_concepts live here |
| **Filing Cabinet** | Deep research — concept points to workfiles via `workfile_refs` |
| **Memory** | Atomic gotchas — concept summarizes, memory has details |
| **Vault** | Long-form docs — concept points to vault docs via `vault_refs` |
| **Notepad** | Not related — session-only |

## Measurability

Track `entities.access_count` on domain_concept entities. If Claudes are finding and using them, access_count grows. Review after 2-4 weeks of usage.

---
**Version**: 1.0
**Created**: 2026-03-29
**Updated**: 2026-03-29
**Location**: knowledge-vault/30-Patterns/domain-concept-entity-type.md
