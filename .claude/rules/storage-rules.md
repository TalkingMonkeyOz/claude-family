# Storage Rules

## 4 Systems — Use the Right One

Claude Family has 4 storage systems organised by purpose:

| I have... | Put it in | Tool |
|-----------|-----------|------|
| API key, auth token, password | **Secrets** (Credential Vault) | `secret(action="set", secret_key=k, secret_value=v)` |
| This-session note, endpoint, decision | **Scratch** (Notepad) | `store_session_fact(key, value, "config")` |
| Pattern, gotcha, decision for future sessions | **Knowledge Graph** (as memory) | `remember(content, memory_type)` |
| API endpoint, OData entity, domain concept | **Knowledge Graph** (as entity) | `entity_store(entity_type, properties)` |
| Research narrative, investigation, architecture | **Knowledge Graph** (as article) | `article_write(title, abstract)` + `article_write(article_id, section_title, section_body)` |
| Working notes on a component | **Workfiles** (Filing Cabinet) | `workfile_store(component, title, content)` |
| Procedure or process | **Skill** or **BPMN** | Create skill or BPMN process model |

## The 4 Systems Explained

**1. Secrets (Credential Vault)** — persistent secrets in Windows Credential Manager. Survives across ALL sessions forever. For any secret the user provides (API keys, tokens, passwords). Retrieve with `secret(action="get", secret_key=k)` — check here BEFORE asking the user for credentials. `secret(action="list")` shows what's registered.

**2. Scratch (Notepad)** — this session only. Survives compaction, gone after session ends. For non-secret config (endpoints, decisions, session-scoped facts).

**3. Knowledge Graph** — everything persistent. Three write paths into one searchable graph:
- **Memories** (`remember()`) — patterns, gotchas, decisions, learnings. Min 80 chars. Auto-deduplicates with union-merge on >0.75 similarity (no content loss on merge).
- **Entities** (`entity_store()`) — structured data with schemas (API endpoints, OData entities, domain concepts as hub entries).
- **Articles** (`article_write()`) — narrative knowledge linking multiple concepts/entities. Section-granular (500-5000 tokens/section), independently searchable.

All three surface together in `recall_memories()` results.

**4. Workfiles (Filing Cabinet)** — component working papers across sessions. `workfile_read(component=name)` to reload. Use for in-progress notes that don't belong in the Knowledge Graph yet.

**Tier model** — Claude sees 2 tiers: **session** (Scratch, lives only in this session) and **persistent** (Secrets + Knowledge Graph + Workfiles, survive across sessions). Internally the Knowledge Graph has automatic short→mid→long promotion — you don't need to think about it.

**Vault** — John's documentation layer for humans (architecture overviews, research narratives). NOT a Claude storage system. Don't write Claude's operational knowledge there — use the 4 systems above.

## Credential Workflow

When a credential is needed:
1. **First**: `secret(action="get", secret_key=k)` — it may already be in the vault
2. **If not found**: ask the user
3. **After receiving**: `secret(action="set", secret_key=k, secret_value=v)` to store it permanently
4. **Never again**: future sessions find it via `secret(action="get")` automatically

## Domain Concepts (Hub Entries)

When you complete significant research on a topic spanning multiple areas, create a `domain_concept` entity via `entity_store(entity_type="domain_concept", properties={...})`. These are first-class hub entries that tie together endpoints, workfiles, and knowledge.

## Chunking Rule (MANDATORY)

Records stay **300-500 lines**. Anything larger must be split into multiple linked records with a proper index. No 10K-line essays. The `remember()` tool auto-flags `chunking_required: true` when a merged description exceeds 500 lines — split when you see this signal.

## Maintain Your Knowledge (MANDATORY)

You own your knowledge quality. Don't leave wrong, stale, or duplicate entries for the next session.

**When you discover a problem**:
- `memory_manage(action="list", project=p)` — browse what's stored, spot issues
- `memory_manage(action="update", memory_id=id, content=new)` — fix incorrect content (re-embeds automatically)
- `memory_manage(action="archive", memory_id=id, reason=r)` — soft-delete wrong/stale entries
- `memory_manage(action="merge", keep_id=k, archive_id=a)` — consolidate duplicates
- `workfile_store(component=c, title=t, mode="archive")` — retire stale workfiles

**When to maintain**: when `recall_memories` or `remember` returns a `maintenance_hint`, act on it.

**Never use SQL** to fix knowledge — all operations go through MCP tools.

## Anti-Patterns

- `store_session_fact("api_key", "sk-...", "credential")` → use `secret(action="set", ...)` — session facts die, vault persists
- `remember("found API key: sk-...")` → use `secret(action="set")` — NEVER put secrets in the Knowledge Graph
- `remember("task 3 done")` → use `store_session_fact("progress", "...", "note")`
- `remember("OData entity User...")` → use `entity_store(entity_type="odata_entity", properties={...})`
- Design notes in session facts → use `workfile_store("component", "design-notes", content)`
- Writing vault docs for Claude's knowledge → use `remember()`, `entity_store()`, `article_write()`, or `workfile_store()` instead
- SOPs as vault markdown → create a skill or BPMN process model instead

## Before Storing: Check First

- `secret(action="get", secret_key=k)` — check if credential already stored
- `secret(action="list")` — see all registered secrets
- `session_facts()` — see your notepad
- `workfile_read()` — check if a drawer already exists
- `recall_memories(query)` — check Knowledge Graph for existing memories/articles
- `entity_read(query=q)` — check Knowledge Graph for existing entities
