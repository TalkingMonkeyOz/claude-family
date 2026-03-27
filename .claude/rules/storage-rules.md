# Storage Rules

## 6 Systems - Use the Right One

| I have... | Put it in | Tool |
|-----------|-----------|------|
| Credential, endpoint, config | **Notepad** | `store_session_fact(key, value, type)` |
| Decision made this session | **Notepad** | `store_session_fact(key, value, "decision")` |
| Pattern, gotcha, lesson learned | **Memory** | `remember(content, "pattern")` |
| Decision future Claudes need | **Memory** | `remember(content, "decision")` |
| Working notes on a component | **Filing Cabinet** | `stash(component, title, content)` |
| API endpoint, OData entity, schema | **Reference Library** | `catalog(entity_type, properties)` |
| Procedure, SOP, research doc | **Vault** | Write to `knowledge-vault/` |
| 10+ structured records to process | **Scratch Workspace** | Write script, output to `.claude/scratch/` |

## Key Rules

- **Notepad** = this session only. Survives compaction, gone after session.
- **Memory** = future sessions. Min 80 chars. NOT for task acks or progress.
- **Filing Cabinet** = component working papers across sessions. `unstash()` to reload.
- **Reference Library** = structured data with schemas. `recall_entities()` returns summaries by default. Use `detail="full"` for complete properties, `entity_id="xxx"` for single entity.
- **Vault** = long-form markdown with YAML frontmatter. Auto-searched via RAG.
- **Scratch Workspace** = temporary structured data on disk. Script writes to `.claude/scratch/`, Claude reads results. Deleted when done. `.gitignored`.

## Scratch Workspace Rules

When you have **10+ structured records** (users, API responses, DB rows):
1. **Write a Python script** that fetches/processes the data
2. Script outputs to `.claude/scratch/{task}_{date}.json` (or `.db` for SQLite)
3. Script prints **summary to stdout** - only this enters context
4. **Read results selectively** via `Read` tool if you need specifics
5. Store a session fact: `store_session_fact("scratch_file", path, "reference")`
6. **Clean up** scratch files when task complete

**Thresholds**: < 10 records = in context. 10-100 = JSON. 100+ or complex queries = SQLite.

## Anti-Patterns

- `remember("found API key: sk-...")` - use `store_session_fact`
- `remember("task 3 done")` - use `store_session_fact("progress", ...)`
- `remember("OData entity User...")` - use `catalog("odata_entity", {...})`
- Design notes in session facts - use `stash("component", "notes", content)`
- 500-word remember() - write a vault doc instead
- Processing 50+ records in context - write a script, use scratch workspace
- Loading full entity properties when summary suffices - default `recall_entities()` returns summaries

## Before Storing: Check First

- `list_session_facts()` - see your notepad
- `list_workfiles()` - check if a drawer already exists
- `recall_memories(query)` - check if already remembered
