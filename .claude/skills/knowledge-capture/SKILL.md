---
name: knowledge-capture
description: "Capture knowledge into cognitive memory (remember) or Obsidian vault (long-form documents)"
user-invocable: true
disable-model-invocation: true
---

# Knowledge Capture

Capture a piece of knowledge — either into the 3-tier cognitive memory system (fast, searchable) or the Obsidian vault (detailed, long-form).

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

Call `mcp__project-tools__remember` with the knowledge and type. The tool auto-routes to the right memory tier, deduplicates, and auto-links related memories.

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

Use YAML frontmatter with `projects` and `tags` fields. Include Summary, Details, Code Example (if applicable), and Related sections. Add version footer.

### Step 3: Sync to Embeddings (Optional but Recommended)

```bash
python scripts/embed_vault_documents.py
```

---

## Examples

**Short gotcha**: `remember(content="build_tasks.status valid values are: todo, in_progress, blocked, completed, cancelled. 'pending' is NOT valid.", memory_type="gotcha")`

**Long-form procedure**: Create `knowledge-vault/40-Procedures/Session Lifecycle - Overview.md` and also call `remember()` with a concise summary pointing to the vault doc.

---

**Version**: 1.0
**Created**: 2026-03-15
**Updated**: 2026-03-15
**Location**: .claude/skills/knowledge-capture/SKILL.md
