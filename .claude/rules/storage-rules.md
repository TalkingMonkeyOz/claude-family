# Storage Rules

## 7 Systems — Use the Right One

| I have... | Put it in | Tool |
|-----------|-----------|------|
| API key, auth token, password | **Credential Vault** | `secret(action="set", secret_key=k, secret_value=v)` |
| Endpoint URL, config value | **Notepad** | `store_session_fact(key, value, "config")` |
| Decision made this session | **Notepad** | `store_session_fact(key, value, "decision")` |
| Pattern, gotcha, lesson learned | **Memory** | `remember(content, "pattern")` |
| Decision future Claudes need | **Memory** | `remember(content, "decision")` |
| Working notes on a component | **Filing Cabinet** | `workfile_store(component, title, content)` |
| API endpoint, OData entity, schema | **Reference Library** | `entity_store(entity_type, properties)` |
| Domain concept spanning multiple systems | **Reference Library** | `entity_store("domain_concept", properties)` |
| Narrative linking multiple concepts/entities | **Knowledge Articles** | `article_write(title, abstract)` + `article_write(article_id, section_title, section_body)` |
| Research findings, investigation results | **Knowledge Articles** | `article_write(title, abstract, article_type="research")` |
| Procedure or process | **Skill** or **BPMN** | Create skill or BPMN process model |

## Key Rules

- **Credential Vault** = persistent secrets in Windows Credential Manager. Survives across ALL sessions forever. Use for any secret the user provides (API keys, tokens, passwords). Retrieve with `secret(action="get", secret_key=k)` — check here BEFORE asking the user for credentials. Use `secret(action="list")` to see what's registered.
- **Notepad** = this session only. Survives compaction, gone after session. Use for non-secret config.
- **Memory** = future sessions. Min 80 chars. NOT for task acks or progress.
- **Filing Cabinet** = component working papers across sessions. `workfile_read(component=name)` to reload.
- **Reference Library** = structured data with schemas. Search via `entity_read(query=...)`. Use `domain_concept` type for hub entities that tie together endpoints, workfiles, and knowledge.
- **Knowledge Articles** = narrative knowledge linking entities/concepts. DB-stored, section-granular (500-5000 tokens/section), independently searchable. Cross-project. Search via `article_read(query=...)`. Also surfaces in `recall_memories()` results.
- **Vault** = John's documentation layer (architecture overviews, research narratives, project descriptions). NOT for Claude's operational knowledge — use the DB systems above instead.

## Credential Workflow

When a credential is needed:
1. **First**: Call `secret(action="get", secret_key=k)` — it may already be in the vault
2. **If not found**: Ask the user for the credential
3. **After receiving**: Call `secret(action="set", secret_key=k, secret_value=v)` to store it permanently
4. **Never again**: Future sessions will find it via `secret(action="get")` automatically

## Domain Concepts (Hub Entities)

When you complete significant research on a topic that spans multiple storage systems, create a `domain_concept` entity via `entity_store(entity_type="domain_concept", properties={...})`.

## Maintain Your Knowledge (MANDATORY)

You are responsible for the quality of your knowledge stores. Don't leave wrong, stale, or duplicate entries for the next session.

**When you discover a problem** (wrong memory, duplicate, stale entry):
- `memory_manage(action="list", project=p)` — browse what's stored, spot issues
- `memory_manage(action="update", memory_id=id, content=new)` — fix incorrect content (re-embeds automatically)
- `memory_manage(action="archive", memory_id=id, reason=r)` — soft-delete wrong/stale entries
- `memory_manage(action="merge", keep_id=k, archive_id=a)` — consolidate duplicates
- `workfile_store(component=c, title=t, mode="archive")` — retire stale workfiles

**When to maintain**: When recall_memories or remember returns a `maintenance_hint`, act on it. Don't ignore it.

**Never use SQL** to fix knowledge. All operations go through MCP tools.

## Anti-Patterns

- `store_session_fact("api_key", "sk-...", "credential")` → use `secret(action="set", ...)` — session facts die, vault persists
- `remember("found API key: sk-...")` → use `secret(action="set")` — NEVER put secrets in memory
- `remember("task 3 done")` → use `store_session_fact("progress", "...", "note")`
- `remember("OData entity User...")` → use `entity_store(entity_type="odata_entity", properties={...})`
- Design notes in session facts → use `workfile_store("component", "design-notes", content)`
- Writing vault docs for Claude's knowledge → use `remember()`, `entity_store()`, or `workfile_store()` instead
- SOPs as vault markdown → create a skill or BPMN process model instead

## Before Storing: Check First

- `secret(action="get", secret_key=k)` — check if credential already stored
- `secret(action="list")` — see all registered secrets
- `session_facts()` — see your notepad
- `workfile_read()` — check if a drawer already exists
- `recall_memories(query)` — check if already remembered
- `entity_read(query=q)` — check if a concept or entity already exists