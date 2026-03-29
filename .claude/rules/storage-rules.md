# Storage Rules

## 5 Systems â€” Use the Right One

| I have... | Put it in | Tool |
|-----------|-----------|------|
| Credential, endpoint, config | **Notepad** | `store_session_fact(key, value, type)` |
| Decision made this session | **Notepad** | `store_session_fact(key, value, "decision")` |
| Pattern, gotcha, lesson learned | **Memory** | `remember(content, "pattern")` |
| Decision future Claudes need | **Memory** | `remember(content, "decision")` |
| Working notes on a component | **Filing Cabinet** | `stash(component, title, content)` |
| API endpoint, OData entity, schema | **Reference Library** | `catalog(entity_type, properties)` |
| Procedure, SOP, research doc | **Vault** | Write to `knowledge-vault/` |

## Key Rules

- **Notepad** = this session only. Survives compaction, gone after session.
- **Memory** = future sessions. Min 80 chars. NOT for task acks or progress.
- **Filing Cabinet** = component working papers across sessions. `unstash()` to reload.
- **Reference Library** = structured data with schemas. Search via `recall_entities()`.
- **Vault** = long-form markdown with YAML frontmatter. Auto-searched via RAG.

## Anti-Patterns

- `remember("found API key: sk-...")` â†’ use `store_session_fact("api_key", "sk-...", "credential")`
- `remember("task 3 done")` â†’ use `store_session_fact("progress", "...", "note")`
- `remember("OData entity User...")` â†’ use `catalog("odata_entity", {...})`
- Design notes in session facts â†’ use `stash("component", "design-notes", content)`
- 500-word remember() â†’ write a vault doc instead

## Before Storing: Check First

- `list_session_facts()` â€” see your notepad
- `list_workfiles()` â€” check if a drawer already exists
- `recall_memories(query)` â€” check if already remembered
