---
projects:
- claude-family
tags:
- vault
- organization
- filing
- sop
---

# Vault & Folder Organization SOP

## Purpose

Where files go — for all Claude instances, all projects. This is the decision tree for file placement, not a description of storage systems (see [[storage-architecture-guide]] for that).

## Part 1: Knowledge Vault Structure

The vault at `knowledge-vault/` is the shared knowledge base for all Claude Family projects.

| Folder | What Goes Here | Examples |
|--------|---------------|----------|
| `00-Inbox/` | Quick capture, unsorted | Notes from meetings, raw dumps |
| `10-Projects/` | Project-specific knowledge | `Project-Metis/`, `claude-family/` |
| `20-Domains/` | Domain expertise (not project-specific) | Database patterns, API design, coding intelligence |
| `30-Patterns/` | Reusable patterns, gotchas, solutions | Storage architecture, coding ethos, cheat sheets |
| `40-Procedures/` | SOPs, workflows, how-to guides | This file, config management, project lifecycle |

### Decision Tree: "Where does my vault doc go?"

```
Is it about a SPECIFIC project?
  YES → 10-Projects/{Project-Name}/
    Does the project folder have 10+ files?
      YES → Use topic subfolders (gates/, research/, audits/)
      NO → Root of the project folder is fine

Is it a PROCEDURE or SOP (how to do something)?
  YES → 40-Procedures/
    Is it infrastructure-specific? → 40-Procedures/infrastructure/

Is it a PATTERN, gotcha, or reusable lesson?
  YES → 30-Patterns/

Is it DOMAIN knowledge (applies across projects)?
  YES → 20-Domains/
    Sub-folder by domain: Database/, API/, etc.

Not sure?
  → 00-Inbox/ (triage later)
```

### Subfolder Rules

- **10+ files** in a project folder → create topic subfolders
- **3+ files** sharing a name prefix → they belong in a subfolder
- Root-level files in project folders = project-level docs only (README, ethos, plan-of-attack)

## Part 2: Project Working Folders

Every project follows this structure. Files created during work go here, NOT in the vault.

| Folder | What Goes Here | Notes |
|--------|---------------|-------|
| `docs/` | Plans, specs, reports, audit results | Working documents, not permanent knowledge |
| `docs/adr/` | Architecture Decision Records | Permanent decisions |
| `docs/sop/` | Project-specific SOPs | If generic, move to vault instead |
| `docs/archive/` | Old/superseded docs | Don't delete, archive |
| `scripts/` | Python utilities, automation | Hooks live here too |
| `tests/` | Test files | Mirror the structure of what they test |
| `.claude/` | Claude Code config (DB-deployed) | Skills, rules, instructions, agents — don't manually edit |

### What Goes in docs/ vs vault?

```
Is it TEMPORARY working output? (audit report, test results, design notes)
  → docs/

Is it PERMANENT knowledge that other projects/sessions should find?
  → knowledge-vault/

Rule of thumb: if you'd want to find it via RAG search in 3 months, it's vault.
If it's useful for this week's work, it's docs/.
```

## Part 3: Cross-Project Conventions

| Content Type | Where It Goes | Why |
|-------------|--------------|-----|
| Project-specific knowledge | `10-Projects/{Project-Name}/` | Grouped by project |
| Domain knowledge discovered in any project | `20-Domains/` | Shared across all projects |
| Research outputs | `20-Domains/{topic}/` or `10-Projects/{project}/research/` | Domain if general, project if specific |
| Competitive analysis | `10-Projects/{project}/` | Always project-specific |
| SOPs that apply everywhere | `40-Procedures/` | Shared |
| SOPs for one project only | `{project}/docs/sop/` | Not in vault |

### File Naming

| Type | Pattern | Example |
|------|---------|---------|
| Temporal (audits, handoffs) | `YYYY-MM-DD-description.md` | `2026-03-14-system-audit.md` |
| Evergreen (patterns, SOPs) | `kebab-case.md` | `config-management-sop.md` |
| Core project files | `UPPERCASE.md` | `CLAUDE.md`, `ARCHITECTURE.md` |

## Part 4: Quick Reference — "I Have X, Where Does It Go?"

| I have... | Storage System | File Location |
|-----------|---------------|---------------|
| A credential or API key | **Notepad** | `store_session_fact()` — no file |
| A decision for future sessions | **Memory** | `remember()` — no file |
| Component working notes | **Filing Cabinet** | `stash()` — no file |
| An API endpoint or schema | **Reference Library** | `catalog()` — no file |
| A procedure/SOP | **Vault** | `knowledge-vault/40-Procedures/` |
| A reusable pattern | **Vault** | `knowledge-vault/30-Patterns/` |
| Domain expertise | **Vault** | `knowledge-vault/20-Domains/` |
| Project-specific knowledge | **Vault** | `knowledge-vault/10-Projects/{project}/` |
| An audit report | **docs/** | `{project}/docs/` |
| Test results | **docs/** | `{project}/docs/` or `{project}/tests/` |
| A design document | **docs/** | `{project}/docs/` |
| Research (general) | **Vault** | `knowledge-vault/20-Domains/` |
| Research (project-specific) | **Vault** | `knowledge-vault/10-Projects/{project}/research/` |
| An ADR | **docs/** | `{project}/docs/adr/` |

## Enforcement

This SOP is enforced through:
1. **Stop hook** (prompt-based) — evaluates response completeness
2. **Standards validator hook** — checks file content rules on Write/Edit
3. **Vault librarian** (async audit) — detects misplacements periodically
4. **Future: file placement tool** — `get_file_path(content_type)` returns correct directory

Advisory approach: warn on wrong placement, don't block work.

---

**Version**: 1.0
**Created**: 2026-03-22
**Updated**: 2026-03-22
**Location**: knowledge-vault/40-Procedures/vault-organization-sop.md
