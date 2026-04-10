---
projects:
- claude-family
tags:
- standards
- file-placement
- project-structure
- enforcement
- chunking
---

# File Placement Standards

Where files go in Claude Family project directories. Based on audit of 17 projects and 800+ documents.

**Core principle**: Line limits mean MORE FILES, not less detail. A 600-line research doc becomes 3 linked 200-line parts — never a 200-line summary. Split, don't compress.

---

## The docs/ Directory Structure

`docs/` is the working document area for a project. It has defined subdirectories for different types of work. **Never dump files loose in docs/ root** — put them in the right subfolder.

```
docs/
├── adr/              # Architecture Decision Records (immutable)
├── research/         # Technology research, API analysis, library evaluations
├── designs/          # Feature specs, architecture proposals, implementation plans
├── investigations/   # Root cause analysis, debugging docs, fix summaries
├── findings/         # Audit results, analysis output, review summaries
├── archive/          # Completed/superseded docs (moved here, not deleted)
└── *.md              # Only truly temporary working notes (TODO, scratch)
```

### What Goes in Each Subfolder

| Subfolder | What goes here | Line limit | Naming |
|-----------|---------------|------------|--------|
| `docs/adr/` | Architecture decisions | 200 | `NNN-title.md` (numbered, immutable once accepted) |
| `docs/research/` | External API research, technology evaluations, library comparisons, competitor analysis | 200 per part | `topic-name.md` or `topic-name-part1.md` |
| `docs/designs/` | Feature specs, implementation plans, architecture proposals, build specs | 200 per part | `feature-name-spec.md`, `feature-name-implementation.md` |
| `docs/investigations/` | Bug root cause analysis, debugging notes, fix summaries, performance analysis | 200 | `YYYY-MM-DD-issue-description.md` |
| `docs/findings/` | Audit results, system analysis output, compliance reviews, test reports | 200 | `topic-audit.md`, `topic-analysis.md` |
| `docs/archive/` | Completed or superseded docs from any subfolder | — | Keep original name |
| `docs/` root | Only scratch notes and truly temporary files | 100 | Avoid — use a subfolder |

---

## Chunking: How to Split Large Documents

**The rule**: When your document exceeds its line limit, split it into linked parts. Each part should stand alone while linking to its siblings.

### Pattern: Multi-Part Research

```
docs/research/
├── odata-api-overview.md          # What it is, key findings, links to parts
├── odata-api-endpoints.md         # Endpoint details
├── odata-api-authentication.md    # Auth flow, tokens
└── odata-api-gotchas.md           # Edge cases, limitations
```

The overview file links to the parts: "For endpoint details, see [OData API Endpoints](odata-api-endpoints.md)."

### Pattern: Multi-Part Design

```
docs/designs/
├── auth-redesign-overview.md      # Problem, approach, decision
├── auth-redesign-schema.md        # Database changes
├── auth-redesign-api.md           # API contract
└── auth-redesign-migration.md     # Migration plan
```

### Pattern: Multi-Part Audit

```
docs/findings/
├── system-audit-summary.md        # Key findings, action items
├── system-audit-storage.md        # Storage subsystem detail
├── system-audit-bpmn.md           # BPMN subsystem detail
└── system-audit-memory.md         # Memory subsystem detail
```

**Key**: The overview/summary file is the entry point. Parts are the detail. Neither omits information — they just divide it.

---

## Project Root Files

Only these files belong in the project root:

| File | Purpose | Limit |
|------|---------|-------|
| `CLAUDE.md` | AI constitution (DB-managed) | 250 |
| `ARCHITECTURE.md` | System design | 300 |
| `PROBLEM_STATEMENT.md` | Problem definition | 300 |
| `README.md` | Public description | 300 |

Everything else goes in a subdirectory. No loose `.md` files in root.

---

## Knowledge Vault (claude-family only)

Long-lived knowledge that should persist and be RAG-searchable.

| Folder | Content | Limit |
|--------|---------|-------|
| `00-Inbox/` | Quick capture, unsorted | 300 |
| `10-Projects/` | Per-project knowledge | 300 |
| `20-Domains/` | Domain expertise (APIs, databases) | 300 |
| `30-Patterns/` | Gotchas, solutions, reusable patterns | 200 |
| `40-Procedures/` | SOPs, workflows, Family Rules | 300 |

All vault files require YAML frontmatter with `projects:` and `tags:`.

---

## DB-Managed Files — Don't Edit Directly

| File | Edit Via | Deploy Via |
|------|---------|-----------|
| `.claude/settings.local.json` | DB update | `regenerate_settings()` |
| `.claude/rules/*.md` | DB update | `sync_project.py --component rules` |
| `.claude/skills/*.md` | DB update | `sync_project.py --component skills` |
| `CLAUDE.md` | `update_claude_md()` | `deploy_claude_md()` |

---

## What NOT to Write as Files

| Don't create a file for... | Instead use... |
|---------------------------|----------------|
| Session summaries | `end_session()` — stored in DB |
| Session handoffs | Auto-stashed by `end_session()` |
| Credentials or endpoints | `store_session_fact()` |
| Task progress notes | `store_session_notes()` |
| Component working notes | `stash()` — filing cabinet |
| Structured reference data | `catalog()` — entity catalog |
| Quick decisions/findings | `remember()` — 3-tier memory |

---

## Cleanup Guidance

When auditing an existing project directory:

1. **Session summaries** (`SESSION_SUMMARY_*.md`) → delete (should be in DB)
2. **Loose docs/ root files** → sort into `research/`, `designs/`, `findings/`, or `archive/`
3. **Loose project root .md** → move to `docs/` subfolder or delete if stale
4. **SOPs in docs/** → move to vault `40-Procedures/`
5. **Old audit files** → move to `docs/archive/` if superseded
6. **Oversized files** → split into linked parts following chunking patterns above

---

**Version**: 2.0
**Created**: 2026-04-06
**Updated**: 2026-04-06
**Location**: knowledge-vault/40-Procedures/file-placement-standards.md
