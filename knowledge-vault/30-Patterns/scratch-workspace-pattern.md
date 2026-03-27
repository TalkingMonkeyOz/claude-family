---
projects:
- claude-family
- nimbus-mui
tags:
- context-management
- scratch-workspace
- data-processing
- F137
---

# Scratch Workspace Pattern

## Problem
AI agents working on data-heavy tasks (cross-referencing 67 users across 3 APIs, batch processing records, data migration) fill context windows by loading structured data directly. Need a pattern for intermediate working data that's too big for session facts, too transient for entity catalog, and too structured for plain text notes.

## The Gap in Storage Systems
| System | Why It Doesn't Fit |
|--------|--------------------|
| Notepad (session facts) | Key-value only, ~100 bytes per entry |
| Memory (remember) | Permanent patterns/decisions, not working data |
| Filing Cabinet (stash) | Text-oriented, no querying |
| Reference Library (catalog) | Too permanent, pollutes catalog |
| Vault | Long-form docs, not structured data |
| **Scratch Workspace** | **NEW: Structured temporary data outside context** |

## Industry Research (2026-03)
No mainstream agent framework has a first-class "temporary structured working dataset" primitive. Approaches:
- **Cursor**: `.cursor/scratchpad.md` for notes, no structured data support
- **SQLite as agent memory**: Engram, EchoVault, sqlite-memory projects converging on SQLite
- **LangGraph**: Typed state checkpointing (framework-locked)
- **MemGPT/Letta**: Self-editing memory blocks (not SQL-queryable)
- **Claude Code native**: Write script, run it, read results (the pragmatic pattern)

## Our Pattern: Script-First with SQLite Escalation

### Decision Rule
- **< 10 records**: Process in context directly
- **10-100 records, simple queries**: Write Python script, output to JSON
- **100+ records OR complex queries**: Python script with SQLite scratch DB

### Convention
- Scratch files go in `{project}/.claude/scratch/`
- Directory is `.gitignored`
- Files named `{task-context}_{date}.{json|db|csv}`
- Clean up when task is complete
- CSV uses 56% fewer tokens than JSON when data must re-enter context

### Script Pattern (Default)
```python
# Claude writes this script, runs via Bash
import json
results = process_all_users(preprod_api, prod_api, copy_api)
# Write to scratch file — data stays OUT of context
with open('.claude/scratch/user_crossref.json', 'w') as f:
    json.dump(results, f, indent=2)
# Print summary to stdout — only THIS enters context
print(f"Processed {len(results)} users: {n_ok} OK, {n_fix} need fixing")
```

### SQLite Pattern (Complex Queries)
```python
import sqlite3
db = sqlite3.connect('.claude/scratch/migration.db')
db.execute('CREATE TABLE users (user_id INT, env TEXT, data JSON, status TEXT)')
# ... populate ...
# Query specific subsets without loading everything
missing = db.execute('SELECT * FROM users WHERE status = "missing_profile"').fetchall()
```

### Key Principle
**The AI is the orchestrator, not the data processor.** Premium model for thinking (what to query, how to fix), cheap Python for doing (fetching, comparing, transforming). Data never enters context — only summaries and targeted results.

## Compaction Survival
- Scratch files persist on disk regardless of context compaction
- Store a session fact pointing to the scratch file: `store_session_fact("scratch_file", ".claude/scratch/crossref.json", "reference")`
- After compaction, re-read the file selectively

## Sources
- Cursor Agent Best Practices (scratchpad)
- SQLite Is the Best Database for AI Agents (dev.to)
- Engram: Persistent Memory for AI Coding Agents (SQLite + FTS5)
- Anthropic Context Engineering Guide
- LangGraph Persistence and Checkpointing

---
**Version**: 1.0
**Created**: 2026-03-27
**Updated**: 2026-03-27
**Location**: knowledge-vault/30-Patterns/scratch-workspace-pattern.md
