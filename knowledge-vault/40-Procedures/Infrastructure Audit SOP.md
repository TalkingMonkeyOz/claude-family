---
projects:
- claude-family
tags:
- audit
- sop
- infrastructure
- maintenance
synced: false
---

# Infrastructure Audit SOP

**Purpose**: Comprehensive audit procedure for Claude Family infrastructure health.

---

## When to Run

- After major schema changes
- After deprecating features/MCPs
- Monthly maintenance check
- After system outages

---

## Audit Scope

| Component | Table/Location | Agent Type |
|-----------|----------------|------------|
| Commands | `.claude/commands/` | analyst-sonnet |
| Skills | `.claude/skills/` + `skill_content` | analyst-sonnet |
| Rules | `.claude/rules/` + `rules`, `coding_standards`, `context_rules` | analyst-sonnet |
| Vault docs | `knowledge-vault/` (138+ docs) | analyst-sonnet |
| Config tables | 13 config tables in `claude` schema | analyst-sonnet |
| Hooks/scripts | `scripts/` + plugin scripts | analyst-sonnet |
| RAG system | `rag_usage_log`, `vault_embeddings`, `knowledge` | direct query |

---

## Phase 1: Commands Audit

**Check For:**
1. Legacy schema references (`claude_family`, `claude_pm`)
2. References to removed MCPs (`memory`, `vault-rag`)
3. Outdated table/column names
4. Commands that don't match current workflows

**Query:**
```bash
grep -r "claude_family\|claude_pm\|memory\|vault-rag" .claude/commands/
```

---

## Phase 2: Skills Audit

**Check For:**
1. Skills in `skill_content` table match filesystem
2. Context rules reference valid skills
3. No orphan skill files

**Query:**
```sql
SELECT name, category, source FROM claude.skill_content WHERE active = true;
```

---

## Phase 3: Rules Audit

**Check For:**
1. Project rules match `claude.rules` table
2. Instructions in `~/.claude/instructions/` are in `coding_standards`
3. No duplicate files in `~/.claude/standards/`
4. Version footers on all files

**Files to Check:**
- `.claude/rules/*.md`
- `~/.claude/instructions/*.md`
- `~/.claude/standards/**/*.md`

---

## Phase 4: Vault Docs Audit

**Check For:**
1. Missing YAML frontmatter
2. Missing version footers
3. Outdated schema/architecture references
4. Broken wiki-links

**Search patterns:**
```bash
grep -r "claude_family\|claude_pm\|process_registry" knowledge-vault/
```

**Quality metrics:**
- 95%+ frontmatter compliance
- 93%+ version footer compliance
- <10% outdated content

---

## Phase 5: Config Tables Audit

**Tables to check (13):**
1. `config_templates` - Template hierarchy
2. `project_type_configs` - Project type defaults
3. `workspaces` - Project registry
4. `profiles` - Cached CLAUDE.md
5. `skill_content` - Skills repository
6. `rules` - Project rules
7. `instructions` - Auto-apply instructions
8. `coding_standards` - Language/framework standards
9. `context_rules` - Context injection rules
10. `global_config` - Global settings
11. `mcp_configs` - MCP installation history
12. `project_config_assignments` - Template assignments
13. `doc_templates` - Document templates

**Check For:**
- Legacy MCP references in `default_mcp_servers`
- Orphaned foreign key references
- Legacy schema references in content

---

## Phase 6: Hooks/Scripts Audit

**Check For:**
1. Hardcoded database credentials (SECURITY CRITICAL)
2. Legacy schema usage
3. Orphaned scripts not in hook config
4. Scripts with missing error handling

**Security Pattern (REQUIRED):**
```python
# GOOD - secure config loading
try:
    sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
    from config import POSTGRES_CONFIG as _PG_CONFIG
    DEFAULT_CONN_STR = f"postgresql://{_PG_CONFIG['user']}:{_PG_CONFIG['password']}@{_PG_CONFIG['host']}/{_PG_CONFIG['database']}"
except ImportError:
    DEFAULT_CONN_STR = None

# BAD - hardcoded credentials
DATABASE_URI = 'postgresql://postgres:PASSWORD@localhost/db'  # NEVER DO THIS
```

---

## Phase 7: RAG System Audit

**Metrics to check:**

```sql
-- Embedding coverage
SELECT
    'vault_embeddings' as source,
    COUNT(*) as total_chunks,
    COUNT(DISTINCT doc_path) as unique_docs
FROM claude.vault_embeddings;

-- RAG performance
SELECT
    query_type,
    COUNT(*) as queries,
    AVG(top_similarity)::numeric(4,2) as avg_similarity,
    COUNT(CASE WHEN top_similarity > 0.5 THEN 1 END) as high_matches
FROM claude.rag_usage_log
GROUP BY query_type;
```

**Quality thresholds:**
- Avg similarity > 0.45 (user prompts)
- Avg similarity > 0.60 (session preloads)
- High match rate > 20%

---

## Common Issues Found

| Issue | Severity | Fix |
|-------|----------|-----|
| Hardcoded credentials | CRITICAL | Use secure config pattern |
| Legacy MCP refs | HIGH | Update to `project-tools` |
| Outdated schema refs | MEDIUM | Replace with `claude.*` |
| Missing version footers | LOW | Add standard footer |
| Duplicate standard files | LOW | Delete duplicates |

---

## Reporting

Save audit reports to: `docs/*_AUDIT_REPORT.md`

**Required sections:**
1. Executive Summary
2. Detailed Findings
3. Recommendations
4. Action Items with Priority

---

## Post-Audit Actions

1. **Security issues** - Fix immediately
2. **Config table issues** - Fix via SQL
3. **File duplicates** - Delete duplicates
4. **Outdated docs** - Schedule update session
5. **Missing metadata** - Batch add via script

---

**Version**: 1.0
**Created**: 2026-01-19
**Updated**: 2026-01-19
**Location**: knowledge-vault/40-Procedures/Infrastructure Audit SOP.md
