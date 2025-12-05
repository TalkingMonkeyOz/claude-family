# SOP-003: Document Classification

**Version:** 1.0
**Created:** 2025-12-03
**Status:** Active
**Author:** claude-code-unified

---

## Purpose

Define rules for classifying documents into types and categories, identifying core documents, and linking documents to projects.

---

## Document Types

Documents are classified by filename patterns. Order matters - first match wins.

| Type | Filename Patterns | Description |
|------|-------------------|-------------|
| `ADR` | `adr-`, `adr_`, `/adr/` | Architecture Decision Records |
| `ARCHITECTURE` | `architecture`, `arch_`, `system_design`, `design_spec` | System architecture docs |
| `CLAUDE_CONFIG` | `claude.md` | Claude Code configuration files |
| `README` | `readme` | Project README files |
| `SOP` | `sop`, `procedure`, `workflow` | Standard Operating Procedures |
| `GUIDE` | `guide`, `how-to`, `howto`, `tutorial`, `quick_start`, `quickstart`, `getting_started` | How-to guides and tutorials |
| `API` | `api`, `swagger`, `openapi`, `endpoint` | API documentation |
| `SPEC` | `spec`, `requirement`, `prd` | Specifications and requirements |
| `SESSION_NOTE` | `session_note`, `session-note`, `completion_report`, `delivery_summary` | Session documentation |
| `MIGRATION` | `migration`, `upgrade` | Migration guides |
| `TROUBLESHOOTING` | `troubleshoot`, `debug`, `fix`, `_fix_`, `investigation`, `audit` | Troubleshooting docs |
| `COMPLETION_REPORT` | `completion`, `complete`, `summary`, `report`, `status` | Completion reports |
| `REFERENCE` | `reference`, `cheat_sheet`, `cheatsheet`, `index` | Reference materials |
| `OTHER` | (fallback) | Unclassified documents |

---

## Categories

Documents are grouped into broader categories:

| Category | Contains Types | Purpose |
|----------|----------------|---------|
| `architecture` | ARCHITECTURE | System design |
| `claude_config` | CLAUDE_CONFIG | Claude setup |
| `readme` | README | Project descriptions |
| `sop` | SOP | Procedures |
| `guide` | GUIDE | Tutorials |
| `api` | API | API docs |
| `spec` | SPEC | Requirements |
| `session_note` | SESSION_NOTE | Session work |
| `adr` | ADR | Decisions |
| `migration` | MIGRATION | Migrations |
| `troubleshooting` | TROUBLESHOOTING | Problem solving |
| `completion_report` | COMPLETION_REPORT | Reports |
| `reference` | REFERENCE | References |
| `other` | OTHER | Unclassified |

---

## Core Documents

Core documents (`is_core = true`) appear across ALL projects.

### Automatic Core Documents
The scanner marks these as core:
- `CLAUDE.md` files
- Files in `C:\claude\shared\docs\`
- Session commands in `.claude\commands\`

### Core Document Reasons
| Pattern | Core Reason |
|---------|-------------|
| `claude.md` | Claude configuration - applies to all sessions |
| `/shared/docs/` | Shared documentation for all projects |
| `/commands/session-` | Session commands used by all instances |

### Setting Core Manually
```sql
UPDATE claude.documents
SET is_core = true, core_reason = 'Explanation here'
WHERE doc_id = 'uuid';
```

---

## Project Linking

Documents are linked to projects via `claude.document_projects` junction table.

### Automatic Linking
Scanner auto-links based on file path:
- `C:\Projects\{project-name}\...` → Links to project `{project-name}`

### Link Types
| linked_by | Meaning |
|-----------|---------|
| `scanner` | Automatically linked by document scanner |
| `manual` | Manually linked by user/Claude |
| `auto` | Linked by automated rule |

### Primary Project
Each document has ONE primary project (`is_primary = true`):
- The project containing the file
- Or first project linked if multiple

### Linking Query
```sql
-- Link document to project
INSERT INTO claude.document_projects (doc_id, project_id, is_primary, linked_by)
VALUES ('doc-uuid', 'project-uuid', true, 'manual');

-- Find all documents for a project
SELECT d.doc_title, d.doc_type, dp.is_primary
FROM claude.document_projects dp
JOIN claude.documents d ON dp.doc_id = d.doc_id
WHERE dp.project_id = 'project-uuid';

-- Find all projects for a document
SELECT p.project_name, dp.is_primary
FROM claude.document_projects dp
JOIN claude.projects p ON dp.project_id = p.project_id
WHERE dp.doc_id = 'doc-uuid';
```

---

## Scanner Behavior

The `scripts/scan_documents.py` script:

1. **Scans directories**: `C:\Projects\*` and `C:\claude\shared\docs\`
2. **Detects type**: From filename patterns
3. **Extracts title**: From first `# heading` or filename
4. **Calculates hash**: SHA256 for change detection
5. **Links to project**: Based on file path
6. **Marks core**: Based on patterns above

### Scanner Exclusions
Skip these directories:
- `node_modules`
- `.git`
- `__pycache__`
- `venv`
- `.next`

Skip files smaller than 50 bytes.

---

## Reducing "OTHER" Classification

To reduce unclassified documents:

1. **Add patterns**: Update `DOC_TYPE_PATTERNS` in scanner
2. **Manual reclassification**:
```sql
UPDATE claude.documents
SET doc_type = 'GUIDE', category = 'guide'
WHERE doc_title LIKE '%tutorial%';
```

3. **Review regularly**: Weekly orphan report job

---

## Naming Conventions

For automatic classification, name files following patterns:

| Want Type | Name Like |
|-----------|-----------|
| ADR | `ADR-001-decision-name.md` |
| Architecture | `ARCHITECTURE.md`, `system_design.md` |
| SOP | `SOP-001-procedure-name.md` |
| Guide | `GUIDE_feature_name.md`, `how-to-X.md` |
| API | `API_module.md`, `endpoints.md` |

---

## Related SOPs
- SOP-001: Knowledge vs Documents vs Tasks
- SOP-002: Build Task Lifecycle

---

**Revision History:**
| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-03 | Initial version |
