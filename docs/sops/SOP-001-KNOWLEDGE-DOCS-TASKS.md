# SOP-001: Knowledge vs Documents vs Tasks Decision Framework

**Version:** 1.0
**Created:** 2025-12-03
**Status:** Active
**Author:** claude-code-unified

---

## Purpose

Define clear rules for when to use the KNOWLEDGE table vs DOCUMENTS table vs BUILD_TASKS vs PM_TASKS. Eliminates ambiguity about where information should be stored.

---

## Decision Matrix

| Use This | When You Have | Examples |
|----------|---------------|----------|
| **KNOWLEDGE** | Reusable patterns, lessons learned, gotchas, best practices that apply across sessions | "Always use dict_row with psycopg3", "C# requires nullable reference types enabled" |
| **DOCUMENTS** | Files on disk that need indexing (specs, guides, READMEs, architecture docs) | CLAUDE.md, README.md, API specs, design docs |
| **BUILD_TASKS** | Development work tied to code components/features | "Add dark mode toggle", "Fix login bug", "Refactor auth module" |
| **PM_TASKS** | Project management work with dates, phases, milestones | "Phase 2 kickoff meeting", "Q1 deliverable review" |

---

## KNOWLEDGE Table (`claude.knowledge`)

### When to Add
- Bug fix that others might hit
- Pattern that worked well
- Gotcha/trap that cost time
- Best practice worth remembering
- API limitation discovered
- Architecture decision rationale

### Required Fields
- `title`: Short descriptive name
- `knowledge_type`: One of the 8 standard types (see below)
- `content`: The actual knowledge content
- `project_name`: Which project this relates to (or NULL for universal)

### Standard Knowledge Types
| Type | Use For |
|------|---------|
| `pattern` | Reusable code/design patterns |
| `gotcha` | Common pitfalls/traps to avoid |
| `best-practice` | Recommended approaches |
| `bug-fix` | Bug fixes and workarounds |
| `reference` | Facts, configs, references |
| `architecture` | System design decisions |
| `troubleshooting` | How to fix problems |
| `api-reference` | API patterns and limitations |

### Example
```sql
INSERT INTO claude.knowledge (title, knowledge_type, content, project_name)
VALUES (
    'psycopg3 requires dict_row factory',
    'gotcha',
    'When using psycopg (version 3), you must specify row_factory=dict_row to get dictionary results. Default returns tuples.',
    'claude-family'
);
```

---

## DOCUMENTS Table (`claude.documents`)

### When to Add
Documents are automatically indexed by `scan_documents.py`. Manual additions only needed for:
- External files not in scanned directories
- Files that need special classification

### Required Fields
- `doc_title`: Human-readable title
- `doc_type`: Classification (see SOP-003)
- `file_path`: Absolute path to file
- `file_hash`: SHA256 hash for change detection
- `category`: Broader category grouping

### Core Documents (is_core = true)
These appear in ALL projects:
- CLAUDE.md files
- Session commands (`/session-start`, `/session-end`)
- Shared documentation in `C:\claude\shared\docs\`

---

## BUILD_TASKS Table (`claude.build_tasks`)

### When to Add
- New feature to implement
- Bug to fix
- Code refactoring needed
- Test to write
- Technical debt to address

### Required Fields
- `task_name`: Short descriptive name
- `task_type`: `code` or `test`
- `status`: `todo`, `in_progress`, `completed`, `blocked`
- `priority`: 1-10 (1-4 critical, 5 normal, 6-10 backlog)

### Optional Fields
- `task_description`: Detailed description
- `component_id`: Link to component being modified
- `feature_id`: Link to feature being built
- `assigned_to`: Who is working on it

### Example
```sql
INSERT INTO claude.build_tasks (task_name, task_description, task_type, status, priority)
VALUES (
    'Add dark mode toggle',
    'Implement dark mode toggle in settings panel with localStorage persistence',
    'code',
    'todo',
    5
);
```

---

## Quick Decision Flowchart

```
Is it a file on disk?
├── YES → DOCUMENTS (indexed by scanner)
└── NO → Continue...

Is it a lesson learned / reusable insight?
├── YES → KNOWLEDGE
└── NO → Continue...

Is it development work (code/tests)?
├── YES → BUILD_TASKS
└── NO → Continue...

Is it project management (meetings/milestones)?
├── YES → PM_TASKS (work_tasks table)
└── NO → Ask for clarification
```

---

## Anti-Patterns

**DON'T:**
- Put code snippets in DOCUMENTS (use KNOWLEDGE with type `pattern`)
- Create KNOWLEDGE entries for one-time fixes (use session notes)
- Create BUILD_TASKS for research/exploration (just do it)
- Duplicate content across tables

**DO:**
- Link BUILD_TASKS to components/features when possible
- Set project_name on KNOWLEDGE entries
- Use scanner for DOCUMENTS rather than manual inserts
- Keep KNOWLEDGE entries concise and actionable

---

## Related SOPs
- SOP-002: Build Task Lifecycle
- SOP-003: Document Classification

---

**Revision History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-03 | Initial version |
