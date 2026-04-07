---
projects:
- claude-family
tags:
- architecture
- information-discovery
- context-management
- dedup
---

# Information Discovery Architecture

How Claude instances find, load, and route information across the Claude Family ecosystem.

---

## The 8-Layer Model

Information is layered by frequency of need. Higher layers cost more context but are always available. Lower layers are cheap but require explicit action.

| # | Layer | When Loaded | Token Cost | What Lives Here |
|---|-------|-------------|------------|-----------------|
| 1 | **CLAUDE.md** | Always (session start) | ~500-800 | Identity, architecture, config management, work tracking, project structure |
| 2 | **Core Protocol** | Every prompt (hook-injected) | ~400-600 | Behavioral rules (DECOMPOSE, STORAGE, DELEGATE, etc.), active features, pinned workfiles, session facts summary |
| 3 | **Rules** | Always (pattern-matched) | ~200-400 | MUST/MUST NOT constraints: storage-rules, database-rules, commit-rules, build-tracking, testing-rules |
| 4 | **Auto-Memory** | Always (MEMORY.md loaded) | ~200-400 | Cross-session user prefs, gotchas, system references |
| 5 | **Instructions** | Auto (file-pattern match) | ~100-300 | Coding standards: csharp, winforms, wpf-ui, sql-postgres, markdown, react |
| 6 | **RAG Hook** | Auto (on questions) | ~200-500 | Vault doc fragments matched by embedding similarity |
| 7 | **Skills** | On demand (Skill tool) | ~300-800 | Domain procedures: database-operations, session-management, coding-intelligence |
| 8 | **MCP Tools** | On demand (Claude decides) | varies | recall_memories(), recall_entities(), unstash(), find_symbol(), get_context() |

**Total always-on cost**: Layers 1-4 = ~1,300-2,200 tokens. This is the baseline context tax.

---

## The Discovery Flow

```
Session Start
  ├── CLAUDE.md loaded (Global + Project)
  ├── Core Protocol injected (rules + active work summary)
  ├── Rules auto-loaded (based on project .claude/rules/)
  └── Auto-Memory loaded (MEMORY.md)

Prompt Arrives
  ├── RAG hook fires → searches vault embeddings → injects matching docs
  ├── Instructions matched → coding standards injected if editing matching files
  └── Core Protocol re-injected (behavioral rules + context)

Claude Needs More Info
  ├── Check skills → Skill tool if task matches a domain skill
  ├── Check memories → recall_memories(query) for patterns/decisions/gotchas
  ├── Check entities → recall_entities(query) for search, explore_entities() for browsing
  ├── Check workfiles → unstash(component) for component working notes
  ├── Check code → find_symbol() / get_context() for codebase understanding
  └── Read vault directly → Read tool on knowledge-vault/ files
```

**Key principle**: Auto-loaded layers handle 80% of needs. On-demand tools handle the remaining 20%. Claude should rarely need to read vault files directly.

---

## What Goes Where (Single Source of Truth)

Each type of information has ONE authoritative home. Other layers may **reference** it but never **duplicate** it.

| Information Type | Authoritative Home | Other Layers Say... |
|-----------------|-------------------|---------------------|
| Project identity & architecture | Project CLAUDE.md | — |
| Environment & platform | Global CLAUDE.md | — |
| Tool index & MCP tools | Global CLAUDE.md | Project says "see Global" |
| Skills list & descriptions | Global CLAUDE.md | Project says "see Global" |
| Behavioral rules (universal) | Core Protocol (DB-versioned) | — |
| Storage routing (5 systems) | `storage-rules.md` (rule file) | Core Protocol says "see storage-rules.md" |
| Database constraints | `database-rules.md` (rule file) | — |
| Commit conventions | `commit-rules.md` (rule file) | — |
| Build tracking workflow | `build-tracking-rules.md` (rule file) | — |
| File placement rules | [[File Placement Standards]] (vault SOP) | CLAUDE.md project structure points here |
| Coding standards per language | `.claude/instructions/*.md` | — |
| Domain procedures / SOPs | Vault (`40-Procedures/`) | CLAUDE.md uses `[[wiki-links]]` |
| Domain knowledge | Vault (`20-Domains/`) | RAG auto-discovers |
| Patterns & gotchas | Vault (`30-Patterns/`) + Memory (3-tier) | RAG auto-discovers |
| Structured reference data | Entity catalog (`catalog`/`recall_entities`) | — |
| Session-scoped context | Session facts (`store_session_fact`) | — |
| Component working notes | Filing cabinet (`stash`/`unstash`) | — |
| Cross-session user prefs | Auto-Memory (`~/.claude/projects/{id}/memory/`) | — |

---

## Routing Rules

How layers reference each other without creating duplication.

### Rule 1: Never Hardcode Vault Paths

```
BAD:  See knowledge-vault/40-Procedures/config-management-sop.md
GOOD: See [[Config Management SOP]]
```

Wiki-links are resolved by RAG (name-based lookup). If a vault file is renamed or moved, the wiki-link still works as long as the document title matches.

### Rule 2: Delegate to Rules Files

When CLAUDE.md or Core Protocol needs to reference a constraint domain, point to the rule file rather than repeating the rules.

```
BAD:  (in Core Protocol) Storage: Notepad for creds, Memory for patterns...
GOOD: (in Core Protocol) STORAGE: 5 systems, use the right one. See storage-rules.md (auto-loaded).
```

### Rule 3: Use Tools for Dynamic Data

Don't put structured data in CLAUDE.md or vault docs. Use the entity catalog.

```
BAD:  (in CLAUDE.md) OData endpoints: POST /api/v1/users...
GOOD: (in CLAUDE.md) Use recall_entities("endpoint name") for API reference data
```

### Rule 4: Global Owns Discovery, Project Owns Specifics

Global CLAUDE.md is the entry point for ALL Claudes across all projects. It owns:
- Tool discovery (MCP tool index)
- Skills discovery (list + descriptions)
- Session workflow
- Delegation rules

Project CLAUDE.md owns project-specific context:
- Architecture overview
- Work tracking conventions
- Config management (DB source of truth)
- Project structure

If something appears in both, Global wins. Project should say "see Global" not repeat.

---

## Dedup Remediation Checklist

These actions align the current system with the architecture above.

- [ ] **1. Dedup Global vs Project CLAUDE.md**: Remove tool index and skills list from Project CLAUDE.md. Add "See Global CLAUDE.md for tools and skills."
- [ ] **2. Merge working-memory-rules into storage-rules**: Move session facts table into storage-rules.md. Reduce working-memory-rules to 2 lines (config warning only) or delete entirely.
- [ ] **3. Prune MEMORY.md**: Audit entries, remove stale pre-2026-03 gotchas, update version references.
- [ ] **4. Fix duplicate Key Procedures**: Remove the duplicate "Key Procedures" section from Project CLAUDE.md.
- [ ] **5. Align Core Protocol fallback**: Sync DEFAULT_CORE_PROTOCOL in rag_query_hook.py with DB version (check `get_active_protocol()`).
- [ ] **6. Reduce storage routing duplication**: Core Protocol rule 3 should say "see storage-rules.md" only. Remove the inline storage table from Core Protocol. Storage-rules.md is the single source of truth.

**Estimated savings**: ~800-1,200 tokens off always-on context cost.

---

**Version**: 1.0
**Created**: 2026-04-06
**Updated**: 2026-04-06
**Location**: knowledge-vault/40-Procedures/information-discovery-architecture.md
