# Knowledge Capture

Capture a piece of knowledge from this session — either into the 3-tier cognitive memory system (fast, searchable) or the Obsidian vault (detailed, long-form).

**Prefer `remember()` for concise facts and patterns. Use the vault for documents that need 200+ lines of explanation.**

---

## When to Use Which Path

| Knowledge Type | Best Path | Why |
|---------------|-----------|-----|
| Pattern, gotcha, decision, fact | `remember()` | Instantly searchable, auto-linked, budget-capped recall |
| Detailed procedure or reference | Vault file | Human-readable, Obsidian-navigable |
| Both concise summary + full detail | `remember()` + vault file | Summary in memory, depth in vault |

---

## Path A: Cognitive Memory (Preferred for Concise Knowledge)

### Step 1: Ask What Was Learned

"What insight, pattern, gotcha, or decision is worth remembering?"

### Step 2: Categorize It

| memory_type | When to Use |
|-------------|-------------|
| `pattern` | Reusable approach or technique confirmed to work |
| `gotcha` | Non-obvious behavior that trips you up |
| `decision` | Architecture or design decision with reasoning |
| `fact` | Learned fact about the codebase, API, or system |
| `procedure` | Step-by-step process to follow |

### Step 3: Store It

Call `mcp__project-tools__remember` with the knowledge and type:

```
mcp__project-tools__remember(
    content="Clear, specific description of what was learned. Include the why, not just the what.",
    memory_type="pattern"   -- pattern | gotcha | decision | fact | procedure
)
```

The tool auto-routes to the right memory tier (mid for working knowledge, long for proven patterns), deduplicates against existing entries (>85% similarity is merged), and auto-links related memories.

### Step 4: Confirm

Tell the user what was stored and which tier it landed in.

---

## Path B: Vault File (For Long-Form Knowledge)

Use this path when the knowledge needs 200+ lines of explanation, code examples, or structured reference material.

### Step 1: Choose Location

| Content | Location |
|---------|----------|
| Project-specific knowledge | `knowledge-vault/10-Projects/{project}/` |
| Domain expertise (APIs, DB) | `knowledge-vault/20-Domains/` |
| Reusable patterns | `knowledge-vault/30-Patterns/` |
| Procedures or SOPs | `knowledge-vault/40-Procedures/` |
| Quick capture (unsorted) | `knowledge-vault/00-Inbox/` |

### Step 2: Create the File

Use this template:

```markdown
---
projects:
- {project-name}
tags:
- {relevant-tag}
- {another-tag}
synced: false
---

# {Clear Descriptive Title}

## Summary
{1-2 sentence summary of what this covers}

## Details
{Full explanation}

## Code Example (if applicable)
```{language}
// Example code
```

## Related
- [[Related topic]]

---
**Version**: 1.0
**Created**: {today}
**Updated**: {today}
**Location**: knowledge-vault/{path}/{filename}.md
```

### Step 3: Sync to Embeddings (Optional but Recommended)

After creating the file, remind the user:

```bash
python scripts/embed_vault_documents.py
```

This updates the RAG embeddings so the document is discoverable by semantic search.

---

## Example Interactions

**User**: "I learned that `build_tasks.status` must be `todo` not `pending`"

- Path A is appropriate (short gotcha)
- Call: `remember(content="build_tasks.status valid values are: todo, in_progress, blocked, completed, cancelled. 'pending' is NOT valid and will cause a constraint violation.", memory_type="gotcha")`

**User**: "I want to document the full session lifecycle for the team"

- Path B is appropriate (long-form procedure)
- Create `knowledge-vault/40-Procedures/Session Lifecycle - Overview.md`
- Also call `remember()` with a concise summary pointing to the vault doc

---

**Version**: 2.0 (Added remember() as primary path, kept vault as secondary; removed sync_obsidian_to_db.py reference)
**Created**: 2025-12-15
**Updated**: 2026-03-09
**Location**: .claude/commands/knowledge-capture.md
