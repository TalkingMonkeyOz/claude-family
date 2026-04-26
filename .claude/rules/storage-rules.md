# Storage Rules

> **Provenance**: DB-managed (`claude.rules` table, scope='global' + 'project'). Edit via `UPDATE claude.rules` then `config_manage(action="deploy_project")` — never edit the deployed `.md` directly. **Last updated 2026-04-26** to reflect Knowledge Architecture v2 (vault sunset, DB-first canonical).

## Canonical Position (Architecture v2, 2026-04-09)

**The Knowledge Graph (DB) is the single source of truth for Claude's persistent knowledge.** The legacy markdown vault is being sunset — its content is being migrated to entities, articles, and memories (open task #649). Vault remains as read-only legacy with an embeddings bridge so its content still surfaces in `recall_memories()` until migration completes; **do not write new operational knowledge there**.

## 4 Systems — Use the Right One

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

## Vault — Legacy / Sunset

The markdown vault at `knowledge-vault/` is the **pre-v2 human documentation layer**. Per Architecture v2 (2026-04-09, knowledge_id `88c08f11-…`), entity-catalog domain concepts are the PRIMARY reference for domain knowledge — not vault. Sunset benchmark (`d22ad1e7-…`) confirmed entities + workfiles cover all 14 benchmark queries without the vault.

**Status**: read-only legacy. Embeddings still indexed so vault content surfaces in `recall_memories()` results during the migration window. Migration to DB is task #649.

**What this means for you**:
- ❌ Don't write new operational knowledge to the vault
- ❌ Don't update SOPs as vault markdown — create a skill or BPMN process model
- ✅ It's fine to *read* vault docs when explicitly asked or when an embedding hit lands
- ✅ When you find vault content that should be in the DB, migrate it via `remember()` / `entity_store()` / `article_write()` and flag the vault doc for archival

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

You own your knowledge quality. Don't leave wrong, stale, or duplicate entries for the next session. **This includes the auto-loaded surfaces** — if you discover that a rule, dossier, or pinned workfile is stale, update it (`UPDATE claude.rules` + deploy, `update_entity` for dossiers, `workfile_store(mode="replace")` for workfiles) — don't just leave a memory contradicting it.

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
- Writing new docs into `knowledge-vault/` for Claude's knowledge → use `remember()`, `entity_store()`, `article_write()`, or `workfile_store()` instead
- SOPs as vault markdown → create a skill or BPMN process model instead
- Editing deployed files (`.claude/rules/*.md`, `CLAUDE.md`) directly → update DB and deploy

## Before Storing: Check First

- `secret(action="get", secret_key=k)` — check if credential already stored
- `secret(action="list")` — see all registered secrets
- `session_facts()` — see your notepad
- `workfile_read()` — check if a drawer already exists
- `recall_memories(query)` — check Knowledge Graph for existing memories/articles
- `entity_read(query=q)` — check Knowledge Graph for existing entities

## Memory-Update Discipline (Rule 7, NEW 2026-04-26)

**Every system change is recorded in memory before commit.** This replaces the vault paper trail (vault is sunset).

**When this applies**: any change to hooks, rules, schemas, BPMN models, MCP server code, deployed configs, architecture decisions, or anything in the System Change Process scope.

**What to do**:
1. Make the change
2. **Before commit**: `remember(content=..., memory_type='decision'|'pattern'|'gotcha')` describing what changed and why
3. Reference any FB# / F# / BT# / commit SHA so future Claude can trace
4. Commit

**Why**: vault used to record every architectural decision in markdown so a fresh session could read the change-log. Memory replaces that role. If the change isn't in memory, it's invisible to future Claude.

**Test**: would a different Claude instance starting fresh tomorrow understand what just changed and why? If no, you didn't remember enough.

## Non-Destructive Migration (MANDATORY, NEW 2026-04-26)

**Every change preserves existing state.** Burned by FB320 (deep-merge bug wiped workspace overrides). Not happening again.

**Schema migrations**: ADDITIVE only.
- `ADD COLUMN ... NULL` ✅
- `CREATE INDEX IF NOT EXISTS` ✅
- `DROP COLUMN` ❌ (use deprecation envelope, retire later)
- `ALTER COLUMN ... NOT NULL` without default ❌
- `RENAME COLUMN` ❌ (add new + dual-write + retire)

**Config deployments**: PRESERVE overrides.
- `generate_project_settings.py` keeps existing permissions (line 489-490)
- Workspace `hooks` overrides must merge, not replace
- Per-project secrets/env never get clobbered by global deploy

**Backfills**: IDEMPOTENT.
- `WHERE column IS NULL` guard so re-running doesn't overwrite populated rows
- Never `UPDATE … SET col = …` without filter — use the IS NULL discriminator
- Never bulk DELETE without explicit user confirmation

**Test**: can you run this change twice and get the same result? If no, it's not idempotent. Can a user with overrides run a deploy without losing them? If no, it's destructive.

## Tool-Discovery Reflex (MANDATORY, NEW 2026-04-26)

**Two questions before any action.** FB341 caught a regression where 8 of 12 SQL calls in one session were avoidable bypasses.

**Q1: Do I have a tool for this?**
- Check protocol injection (RELEVANT KNOWLEDGE, GOTCHAS, ENTITY CATALOG)
- Check `entity_read(query='...', entity_type='tool')`
- Check `recall_memories('how to do X')`
- Check the auto-loaded skills list
- Check `system_info()` for available MCP surfaces

**Q2: Do I know how to use it?**
- `entity_read('tool-name')` for usage signature
- `recall_memories('tool-name pattern')` for known gotchas
- If unclear, surface the gap (`store_session_fact` or file feedback)

**If the answer to either is "no"**: that's a discoverability gap. Either a tool is missing (file improvement feedback) or the discovery surface is failing (file design feedback). Don't silently fall back to raw SQL / direct file ops.

**Specific bypass to avoid** (per FB341):
- `mcp__postgres__execute_sql` against `claude.feedback`/`features`/`build_tasks` -> use `work_board()` / `get_ready_tasks()` / `work_status()` instead
- `mcp__postgres__execute_sql` against `claude.knowledge`/`entities` -> use `recall_memories()` / `entity_read()` / `memory_manage()`
- Reading `information_schema.columns` -> file FB345 (until `get_schema(table=…, mode='raw')` ships)

If you MUST use raw SQL (telemetry, mcp_usage, scheduled_jobs — currently no MCP wrapper), add an `-- OVERRIDE: <reason>` comment so the gap is visible to FB343/FB344.
