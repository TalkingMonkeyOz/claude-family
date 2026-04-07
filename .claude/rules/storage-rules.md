# Storage Rules

## 5 Systems — Use the Right One

| I have... | Put it in | Tool |
|-----------|-----------|------|
| Credential, endpoint, config | **Notepad** | `store_session_fact(key, value, type)` |
| Decision made this session | **Notepad** | `store_session_fact(key, value, "decision")` |
| Pattern, gotcha, lesson learned | **Memory** | `remember(content, "pattern")` |
| Decision future Claudes need | **Memory** | `remember(content, "decision")` |
| Working notes on a component | **Filing Cabinet** | `stash(component, title, content)` |
| API endpoint, OData entity, schema | **Reference Library** | `catalog(entity_type, properties)` |
| Domain concept spanning multiple systems | **Reference Library** | `catalog("domain_concept", properties)` |
| Procedure, SOP, research doc | **Vault** | Write to `knowledge-vault/` |

## Key Rules

- **Notepad** = this session only. Survives compaction, gone after session.
- **Memory** = future sessions. Min 80 chars. NOT for task acks or progress.
- **Filing Cabinet** = component working papers across sessions. `unstash()` to reload.
- **Reference Library** = structured data with schemas. Search via `recall_entities()`. Use `domain_concept` type for hub entities that tie together endpoints, workfiles, and knowledge.
- **Vault** = long-form markdown with YAML frontmatter. Auto-searched via RAG.

## Domain Concepts (Hub Entities)

When you complete significant research on a topic that spans multiple storage systems (e.g., an API with multiple endpoints + a workfile + scattered gotchas), create a `domain_concept` entity:

```
catalog("domain_concept", {
    "name": "UserSDK",
    "domain": "nimbus/time2work",
    "purpose": "Bulk user import/update endpoint",
    "overview": "What it is, how it works, key behaviors...",
    "usage_modes": ["Mode A: ...", "Mode B: ..."],
    "gotchas": ["Watch out for X", "Y doesn't work"],
    "workfile_refs": [{"component": "usersdk-discovery", "title": "Full findings"}],
    "vault_refs": [],
    "verified": {"date": "2026-03-29", "environment": "demo.time2work.com"}
})
```

This creates a searchable entry point that `recall_entities()` finds alongside the specific data entities.

## Anti-Patterns

- `remember("found API key: sk-...")` → use `store_session_fact("api_key", "sk-...", "credential")`
- `remember("task 3 done")` → use `store_session_fact("progress", "...", "note")`
- `remember("OData entity User...")` → use `catalog("odata_entity", {...})`
- Design notes in session facts → use `stash("component", "design-notes", content)`
- 500-word remember() → write a vault doc instead
- Scattered knowledge with no entry point → create a `domain_concept`

## Before Storing: Check First

- `list_session_facts()` — see your notepad
- `list_workfiles()` — check if a drawer already exists
- `recall_memories(query)` — check if already remembered
- `recall_entities(query)` — check if a concept or entity already exists
