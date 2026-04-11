# Storage Rules

## 6 Systems — Use the Right One

| I have... | Put it in | Tool |
|-----------|-----------|------|
| API key, auth token, password | **Credential Vault** | `set_secret(key, value, project)` |
| Endpoint URL, config value | **Notepad** | `store_session_fact(key, value, "config")` |
| Decision made this session | **Notepad** | `store_session_fact(key, value, "decision")` |
| Pattern, gotcha, lesson learned | **Memory** | `remember(content, "pattern")` |
| Decision future Claudes need | **Memory** | `remember(content, "decision")` |
| Working notes on a component | **Filing Cabinet** | `stash(component, title, content)` |
| API endpoint, OData entity, schema | **Reference Library** | `catalog(entity_type, properties)` |
| Domain concept spanning multiple systems | **Reference Library** | `catalog("domain_concept", properties)` |
| Procedure or process | **Skill** or **BPMN** | Create skill or BPMN process model |

## Key Rules

- **Credential Vault** = persistent secrets in Windows Credential Manager. Survives across ALL sessions forever. Use for any secret the user provides (API keys, tokens, passwords). Retrieve with `get_secret(key, project)` — check here BEFORE asking the user for credentials. Use `list_secrets(project)` to see what's registered.
- **Notepad** = this session only. Survives compaction, gone after session. Use for non-secret config.
- **Memory** = future sessions. Min 80 chars. NOT for task acks or progress.
- **Filing Cabinet** = component working papers across sessions. `unstash()` to reload.
- **Reference Library** = structured data with schemas. Search via `recall_entities()`. Use `domain_concept` type for hub entities that tie together endpoints, workfiles, and knowledge.
- **Vault** = John's documentation layer (architecture overviews, research narratives, project descriptions). NOT for Claude's operational knowledge — use the DB systems above instead.

## Credential Workflow

When a credential is needed:
1. **First**: Call `get_secret(key, project)` — it may already be in the vault
2. **If not found**: Ask the user for the credential
3. **After receiving**: Call `set_secret(key, value, project)` to store it permanently
4. **Never again**: Future sessions will find it via `get_secret()` automatically

## Domain Concepts (Hub Entities)

When you complete significant research on a topic that spans multiple storage systems, create a `domain_concept` entity via `catalog("domain_concept", {...})`.

## Maintain Your Knowledge (MANDATORY)

You are responsible for the quality of your knowledge stores. Don't leave wrong, stale, or duplicate entries for the next session.

**When you discover a problem** (wrong memory, duplicate, stale entry):
- `list_memories(project)` — browse what's stored, spot issues
- `update_memory(id, content)` — fix incorrect content (re-embeds automatically)
- `archive_memory(id, reason)` — soft-delete wrong/stale entries
- `merge_memories(keep_id, archive_id)` — consolidate duplicates
- `archive_workfile(component, title)` — retire stale workfiles

**When to maintain**: When recall_memories or remember returns a `maintenance_hint`, act on it. Don't ignore it.

**Never use SQL** to fix knowledge. All operations go through MCP tools.

## Anti-Patterns

- `store_session_fact("api_key", "sk-...", "credential")` → use `set_secret("api_key", "sk-...")` — session facts die, vault persists
- `remember("found API key: sk-...")` → use `set_secret()` — NEVER put secrets in memory
- `remember("task 3 done")` → use `store_session_fact("progress", "...", "note")`
- `remember("OData entity User...")` → use `catalog("odata_entity", {...})`
- Design notes in session facts → use `stash("component", "design-notes", content)`
- Writing vault docs for Claude's knowledge → use `remember()`, `catalog()`, or `stash()` instead
- SOPs as vault markdown → create a skill or BPMN process model instead

## Before Storing: Check First

- `get_secret(key, project)` — check if credential already stored
- `list_secrets(project)` — see all registered secrets
- `list_session_facts()` — see your notepad
- `list_workfiles()` — check if a drawer already exists
- `recall_memories(query)` — check if already remembered
- `recall_entities(query)` — check if a concept or entity already exists
