# Comprehensive Rules Audit Report

**Date**: 2026-01-19
**Auditor**: analyst-sonnet
**Scope**: All rule/standard/instruction files across project and global locations

---

## Executive Summary

**Total Files Found**: 36 rule/standard/instruction files across 3 locations
**Database Entries**: 3 rules (project-specific), 15 coding standards, 16 context rules
**Status**: MOSTLY CURRENT with several gaps and inconsistencies

### Key Findings

1. ✅ **Project rules match database** - All 3 files in `.claude/rules/` are in sync
2. ⚠️ **Instructions directory mismatch** - 9 files in `~/.claude/instructions/` but only 6 match coding_standards
3. ⚠️ **Standards directory has duplicates** - 24 files with some redundant/legacy copies
4. ✅ **Context rules are comprehensive** - 16 active rules covering major task types
5. ⚠️ **Missing global rules directory** - `~/.claude/rules/` doesn't exist (expected per docs)

---

## 1. Project Rules (`C:\Projects\claude-family\.claude\rules\`)

### Files Found: 3

| File | Purpose | Database Match | Status | Issues |
|------|---------|---------------|--------|--------|
| `commit-rules.md` | Git commit conventions | ✅ Yes | ✅ CURRENT | None |
| `database-rules.md` | Database operations | ✅ Yes | ✅ CURRENT | None |
| `testing-rules.md` | Testing requirements | ✅ Yes | ✅ CURRENT | None |

**Database Verification**:
```sql
-- All 3 rules exist in claude.rules table:
- commit-rules (scope: project, active: true)
- database-rules (scope: project, active: true)
- testing-rules (scope: project, active: true)
```

**Assessment**: ✅ **PERFECT SYNC** - Project rules are correctly stored in database and match filesystem files.

---

## 2. Global Instructions (`C:\Users\johnd\.claude\instructions\`)

### Files Found: 9

| File | Matches coding_standards | Status | Issues |
|------|--------------------------|--------|--------|
| `a11y.instructions.md` | ❌ No | ⚠️ ORPHAN | Not in database |
| `csharp.instructions.md` | ✅ Yes (csharp) | ✅ CURRENT | Matches |
| `markdown.instructions.md` | ✅ Yes (markdown-documentation) | ⚠️ DUPLICATE | Also in standards/ |
| `mvvm.instructions.md` | ❌ No | ⚠️ ORPHAN | Not in database |
| `playwright.instructions.md` | ❌ No | ⚠️ ORPHAN | Not in database |
| `sql-postgres.instructions.md` | ✅ Yes (sql-postgres) | ⚠️ DUPLICATE | Also in standards/ |
| `winforms.instructions.md` | ✅ Yes (winforms) | ✅ CURRENT | Matches |
| `winforms-dark-theme.instructions.md` | ❌ No | ⚠️ ORPHAN | Not in database |
| `wpf-ui.instructions.md` | ❌ No | ⚠️ ORPHAN | Not in database |

**Assessment**: ⚠️ **INCONSISTENT** - 5 orphan files not tracked in coding_standards table.

### Orphan Instructions Analysis

#### 1. `a11y.instructions.md`
- **Content**: WCAG 2.2 AA accessibility guidelines
- **Applies To**: `**/*.cs,**/*.tsx,**/*.ts,**/*.css`
- **Status**: HIGH VALUE - Should be in coding_standards
- **Recommendation**: Add to database as `category='pattern', name='a11y'`

#### 2. `mvvm.instructions.md`
- **Content**: MVVM pattern for WPF with CommunityToolkit.Mvvm
- **Applies To**: `**/ViewModels/**/*.cs,**/Views/**/*.xaml`
- **Status**: HIGH VALUE - Should be in coding_standards
- **Recommendation**: Add to database as `category='pattern', name='mvvm'`

#### 3. `playwright.instructions.md`
- **Content**: Playwright E2E testing patterns
- **Applies To**: `**/*.spec.ts,**/tests/**/*.ts`
- **Status**: HIGH VALUE - Should be in coding_standards
- **Recommendation**: Add to database as `category='pattern', name='playwright'`

#### 4. `winforms-dark-theme.instructions.md`
- **Content**: Dark theme implementation for WinForms
- **Applies To**: `**/Forms/**/*.cs,**/*Form.cs`
- **Status**: MEDIUM VALUE - Specialized, could be in database
- **Recommendation**: Add to database as `category='pattern', name='winforms-dark-theme'`

#### 5. `wpf-ui.instructions.md`
- **Content**: WPF UI library (Fluent Design) quick reference
- **Applies To**: `**/*.xaml,**/Views/**/*.cs`
- **Status**: HIGH VALUE - Should be in coding_standards
- **Recommendation**: Add to database as `category='framework', name='wpf-ui'`

---

## 3. Global Standards (`C:\Users\johnd\.claude\standards\`)

### Files Found: 24 (including duplicates)

#### Core (1 file)
| File | Database Match | Status |
|------|---------------|--------|
| `core/markdown-documentation.md` | ✅ Yes | ✅ CURRENT |

#### Language (4 files)
| File | Database Match | Status |
|------|---------------|--------|
| `language/csharp.md` | ✅ Yes | ✅ CURRENT |
| `language/rust.md` | ✅ Yes | ✅ CURRENT |
| `language/sql-postgres.md` | ✅ Yes | ✅ CURRENT |
| `language/typescript.md` | ✅ Yes | ✅ CURRENT |

#### Framework (9 files, some duplicates)
| File | Database Match | Status | Notes |
|------|---------------|--------|-------|
| `framework/azure-bicep.md` | ✅ Yes | ✅ CURRENT | |
| `framework/Azure Bicep.md` | ✅ Yes | ⚠️ DUPLICATE | Space in name |
| `framework/azure-functions.md` | ✅ Yes | ✅ CURRENT | |
| `framework/Azure Functions.md` | ✅ Yes | ⚠️ DUPLICATE | Space in name |
| `framework/azure-logic-apps.md` | ✅ Yes | ✅ CURRENT | |
| `framework/Azure Logic Apps.md` | ✅ Yes | ⚠️ DUPLICATE | Space in name |
| `framework/mui.md` | ✅ Yes | ✅ CURRENT | |
| `framework/mui-design-system.md` | ✅ Yes | ✅ CURRENT | |
| `framework/react.md` | ✅ Yes | ✅ CURRENT | |
| `framework/winforms.md` | ✅ Yes | ✅ CURRENT | |

#### Pattern (6 files, some duplicates)
| File | Database Match | Status | Notes |
|------|---------------|--------|-------|
| `pattern/docker.md` | ✅ Yes | ✅ CURRENT | |
| `pattern/Docker Containerization.md` | ✅ Yes | ⚠️ DUPLICATE | Space in name |
| `pattern/github-actions.md` | ✅ Yes | ✅ CURRENT | |
| `pattern/GitHub Actions CI\CD.md` | ✅ Yes | ⚠️ DUPLICATE | Space in name |
| `pattern/security-aspnet.md` | ✅ Yes | ✅ CURRENT | |
| `pattern/Security & ASP.NET APIs.md` | ✅ Yes | ⚠️ DUPLICATE | Space in name |

#### Legacy/Duplicates (4 files)
| File | Status | Notes |
|------|--------|-------|
| `~\.claude\standards\framework\azure-bicep.md` | ⚠️ LEGACY | Nested path duplicate |
| `~\.claude\standards\framework\azure-functions.md` | ⚠️ LEGACY | Nested path duplicate |
| `~\.claude\standards\framework\azure-logic-apps.md` | ⚠️ LEGACY | Nested path duplicate |
| `README.md` | ✅ INDEX | Documentation file |

**Assessment**: ⚠️ **DUPLICATES PRESENT** - 9 duplicate files with spaces in names, 3 nested path duplicates.

**Recommendation**: Delete duplicates, keep kebab-case versions.

---

## 4. Database: `claude.rules` Table

### Schema
```
- rule_id (uuid, PK)
- name (varchar, NOT NULL)
- scope (varchar, NOT NULL) - CHECK: 'global', 'project', 'user'
- scope_ref (varchar, nullable) - project_id for project scope
- content (text, NOT NULL)
- rule_type (varchar, nullable)
- is_active (boolean, default true)
- created_at, updated_at (timestamptz)
```

### Current Entries: 3 (all project-scoped)

| Name | Scope | Type | Active | Last Updated |
|------|-------|------|--------|--------------|
| commit-rules | project (claude-family) | commit | ✅ Yes | 2026-01-11 |
| database-rules | project (claude-family) | database | ✅ Yes | 2026-01-11 |
| testing-rules | project (claude-family) | testing | ✅ Yes | 2026-01-11 |

**Issues Found**:
1. ❌ **No global-scoped rules** - All rules are project-specific
2. ❌ **Orphan instruction files** - 5 files not in database
3. ✅ **File content matches database** - Verified for all 3 rules

---

## 5. Database: `claude.coding_standards` Table

### Schema
```
- standard_id (uuid, PK)
- category (varchar) - CHECK: 'core', 'language', 'framework', 'pattern'
- name (varchar, NOT NULL, UNIQUE)
- file_path (varchar) - relative to ~/.claude/standards/
- content (text)
- applies_to_patterns (text[]) - glob patterns
- validation_rules (jsonb)
- active (boolean, default true)
```

### Current Entries: 15

| Category | Name | Applies To | Active |
|----------|------|------------|--------|
| core | markdown-documentation | `**/*.md` | ✅ |
| language | csharp | `**/*.cs` | ✅ |
| language | rust | `**/*.rs` | ✅ |
| language | sql-postgres | `**/*.sql` | ✅ |
| language | typescript | `**/*.ts, **/*.tsx` | ✅ |
| framework | Azure Bicep | `**/*.bicep` | ✅ |
| framework | Azure Functions | `**/*Function*.cs` | ✅ |
| framework | Azure Logic Apps | `**/workflow.json` | ✅ |
| framework | mui | `**/*.tsx, **/*.jsx` | ✅ |
| framework | mui-design-system | `**/*.tsx, **/*.ts` | ✅ |
| framework | react | `**/*.tsx, **/*.jsx` | ✅ |
| framework | winforms | `**/*.Designer.cs` | ✅ |
| pattern | Docker Containerization | `**/Dockerfile*` | ✅ |
| pattern | GitHub Actions CI/CD | `**/.github/workflows/*.yml` | ✅ |
| pattern | Security & ASP.NET APIs | `**/*.cs` | ✅ |

**Missing from Database** (present in instructions/):
1. a11y (accessibility)
2. mvvm (MVVM pattern)
3. playwright (E2E testing)
4. winforms-dark-theme (WinForms theming)
5. wpf-ui (WPF UI library)

---

## 6. Database: `claude.context_rules` Table

### Schema
```
- rule_id (uuid, PK)
- name (text, NOT NULL, UNIQUE)
- description (text)
- task_keywords (text[])
- file_patterns (text[])
- agent_types (text[])
- inject_standards (text[])
- inject_vault_query (text)
- inject_static_context (text) - Rule content injected
- priority (int, default 50)
- active (boolean, default true)
```

### Current Entries: 16 (all active)

| Name | Priority | Keywords | Agent Types | Status |
|------|----------|----------|-------------|--------|
| ui-ux-design | 95 | design, ui, ux, accessibility | designer-sonnet | ✅ CURRENT |
| workflow-read-first | 90 | build, create, implement | (all) | ✅ CURRENT |
| winforms-development | 80 | winforms, form, designer | winforms-coder-haiku | ✅ CURRENT |
| architecture-design | 75 | architecture, design, system | architect-opus | ✅ CURRENT |
| mui-development | 75 | mui, material, datagrid | mui-coder-sonnet | ✅ CURRENT |
| security-audit | 75 | security, vulnerability, owasp | security-sonnet | ✅ CURRENT |
| code-review-patterns | 70 | review, pr, code quality | reviewer-sonnet | ✅ CURRENT |
| database-operations | 70 | sql, database, postgres | python-coder-haiku | ✅ CURRENT |
| planning-patterns | 65 | plan, breakdown, task | planner-sonnet | ✅ CURRENT |
| research-patterns | 65 | research, analyze | researcher-opus, analyst-sonnet | ✅ CURRENT |
| testing-patterns | 65 | test, pytest, jest | tester-haiku, web-tester-haiku | ✅ CURRENT |
| csharp-development | 60 | c#, .net, class | coder-haiku, coder-sonnet | ✅ CURRENT |
| git-operations | 60 | git, commit, branch | git-haiku | ✅ CURRENT |
| python-development | 60 | python, pip, pytest | python-coder-haiku | ✅ CURRENT |
| typescript-react | 60 | typescript, react, tsx | coder-haiku, coder-sonnet | ✅ CURRENT |
| documentation-standards | 50 | document, docs, markdown | doc-keeper-haiku | ✅ CURRENT |

**Assessment**: ✅ **COMPREHENSIVE** - Covers all major task types with appropriate delegation guidance.

**Context Rule Content Analysis**:
- All 16 rules have `inject_static_context` with actionable guidance
- Includes mandatory checks (database-operations, code-review-patterns)
- References vault SOPs and patterns appropriately
- Delegation recommendations match agent capabilities

---

## 7. Cross-Reference Analysis

### Rules in Database but NOT in Filesystem

**None found** - All database rules have corresponding files ✅

### Rules in Filesystem but NOT in Database

#### Instructions Directory Orphans (5 files):
1. `a11y.instructions.md` - Accessibility guidelines
2. `mvvm.instructions.md` - MVVM pattern
3. `playwright.instructions.md` - E2E testing
4. `winforms-dark-theme.instructions.md` - Dark theme
5. `wpf-ui.instructions.md` - WPF UI library

**Impact**: These files exist but are NOT automatically loaded or enforced by the system.

### Duplicate Files

#### Standards Directory (9 duplicates):
1. `Azure Bicep.md` vs `azure-bicep.md` (keep kebab-case)
2. `Azure Functions.md` vs `azure-functions.md` (keep kebab-case)
3. `Azure Logic Apps.md` vs `azure-logic-apps.md` (keep kebab-case)
4. `Docker Containerization.md` vs `docker.md` (keep kebab-case)
5. `GitHub Actions CI\CD.md` vs `github-actions.md` (keep kebab-case)
6. `Security & ASP.NET APIs.md` vs `security-aspnet.md` (keep kebab-case)

#### Nested Path Duplicates (3 legacy):
7. `~\.claude\standards\framework\azure-bicep.md` (nested duplicate)
8. `~\.claude\standards\framework\azure-functions.md` (nested duplicate)
9. `~\.claude\standards\framework\azure-logic-apps.md` (nested duplicate)

**Impact**: Causes confusion, may load duplicate content, wastes disk space.

---

## 8. Content Quality Assessment

### All Files Reviewed for:
1. ✅ **Actionability** - Instructions are specific and executable
2. ✅ **Currency** - References current systems (claude schema, hooks, MCP)
3. ⚠️ **Contradictions** - Minor inconsistency found (see below)
4. ✅ **Completeness** - Covers necessary detail

### Issues Found

#### 1. Markdown Standards Contradiction
- **File**: `markdown.instructions.md` (line 11)
- **States**: "Keep it short - Target 250-500 tokens"
- **File**: `~/.claude/standards/core/markdown-documentation.md` (line 25)
- **States**: "CRITICAL: Chunking vs Summarizing - Split, don't summarize"
- **Issue**: The instructions file emphasizes brevity without the chunking context
- **Resolution**: Instructions file should reference the full standards file

#### 2. SQL Standards Duplication
- **Location 1**: `sql-postgres.instructions.md` (118 lines)
- **Location 2**: `~/.claude/standards/language/sql-postgres.md` (79 lines)
- **Difference**: Instructions file has more examples
- **Issue**: Content drift - which is authoritative?
- **Resolution**: Consolidate into standards file, remove instructions duplicate

#### 3. Missing Version Footers
Files missing required version footer (per markdown standards):
- `a11y.instructions.md` ❌
- `csharp.instructions.md` ❌
- `mvvm.instructions.md` ❌
- `playwright.instructions.md` ❌
- `sql-postgres.instructions.md` ❌
- `winforms.instructions.md` ❌
- `winforms-dark-theme.instructions.md` ❌

**Impact**: Can't track version history or last update date.

---

## 9. Recommendations

### Immediate Actions (High Priority)

1. **Add Orphan Instructions to Database** ⚠️ CRITICAL
   ```sql
   -- Add missing coding standards
   INSERT INTO claude.coding_standards (category, name, file_path, content, applies_to_patterns)
   VALUES
   ('pattern', 'a11y', 'pattern/a11y.md', ..., ARRAY['**/*.cs', '**/*.tsx']),
   ('pattern', 'mvvm', 'pattern/mvvm.md', ..., ARRAY['**/ViewModels/**/*.cs']),
   ('pattern', 'playwright', 'pattern/playwright.md', ..., ARRAY['**/*.spec.ts']),
   ('pattern', 'winforms-dark-theme', 'pattern/winforms-dark-theme.md', ..., ARRAY['**/*Form.cs']),
   ('framework', 'wpf-ui', 'framework/wpf-ui.md', ..., ARRAY['**/*.xaml']);
   ```

2. **Delete Duplicate Files** ⚠️ CRITICAL
   ```bash
   # Delete space-named duplicates
   rm "C:\Users\johnd\.claude\standards\framework\Azure Bicep.md"
   rm "C:\Users\johnd\.claude\standards\framework\Azure Functions.md"
   rm "C:\Users\johnd\.claude\standards\framework\Azure Logic Apps.md"
   rm "C:\Users\johnd\.claude\standards\pattern\Docker Containerization.md"
   rm "C:\Users\johnd\.claude\standards\pattern\GitHub Actions CI\CD.md"
   rm "C:\Users\johnd\.claude\standards\pattern\Security & ASP.NET APIs.md"

   # Delete nested duplicates
   rm -r "C:\Users\johnd\.claude\standards\~\.claude"
   ```

3. **Add Version Footers** ⚠️ MEDIUM
   - Add standard footer to all 7 orphan instructions files
   - Template:
     ```markdown
     ---
     **Version**: 1.0
     **Created**: YYYY-MM-DD
     **Updated**: YYYY-MM-DD
     **Location**: ~/.claude/instructions/filename.md
     ```

4. **Consolidate SQL Standards** ⚠️ MEDIUM
   - Keep: `~/.claude/standards/language/sql-postgres.md` (authoritative)
   - Update: Add best examples from instructions file
   - Delete: `sql-postgres.instructions.md` (after merging content)

### Medium Priority Actions

5. **Create Global Rules Structure** 📋
   - Document expected `~/.claude/rules/` directory usage
   - OR clarify in docs that global rules go in `coding_standards` table
   - Currently unclear if `rules` table should have global scope entries

6. **Standardize File Naming** 📋
   - Use kebab-case for all standard files
   - Update database `file_path` if using display names
   - Consistency: `azure-functions.md` not `Azure Functions.md`

7. **Review Context Rule Priorities** 📋
   - Consider if priority 50-95 range is correct
   - Test if workflow-read-first (90) always fires before specific rules (70)
   - Document priority guidelines

### Low Priority Actions

8. **Add Rule Type Taxonomy** 📋
   - `claude.rules.rule_type` is free-text, could be enum
   - Suggest: commit, database, testing, security, documentation
   - Add to `claude.column_registry`

9. **Consider Rules Table Consolidation** 💡
   - Three separate tables: `rules`, `coding_standards`, `context_rules`
   - Overlap in purpose (all are "rules" for behavior)
   - Consider: unified `claude.governance_rules` table with `rule_category` field

10. **Add Validation Scripts** 💡
    - Script to verify files match database content
    - Script to detect duplicates automatically
    - Script to enforce version footers

---

## 10. Summary Table

| Location | Files | Database Match | Issues | Priority |
|----------|-------|----------------|--------|----------|
| `.claude/rules/` (project) | 3 | ✅ 3/3 match | None | ✅ GOOD |
| `~/.claude/instructions/` | 9 | ⚠️ 4/9 match | 5 orphans, 2 duplicates | 🔴 HIGH |
| `~/.claude/standards/` | 24 | ✅ 15/15 match | 12 duplicates | 🟡 MEDIUM |
| `claude.rules` (DB) | 3 | ✅ All current | No global rules | 🟢 LOW |
| `claude.coding_standards` (DB) | 15 | ✅ All current | 5 missing | 🔴 HIGH |
| `claude.context_rules` (DB) | 16 | ✅ All current | None | ✅ GOOD |

---

## 11. Action Plan

### Phase 1: Critical Fixes (Do First)
- [ ] Add 5 orphan instruction files to `coding_standards` table
- [ ] Delete 12 duplicate files in standards directory
- [ ] Test that auto-apply still works after cleanup

### Phase 2: Content Improvements
- [ ] Add version footers to 7 instruction files
- [ ] Consolidate SQL standards (merge then delete duplicate)
- [ ] Update README.md in standards/ to reflect current structure

### Phase 3: Documentation
- [ ] Clarify global vs project rule storage strategy
- [ ] Document file naming conventions (kebab-case)
- [ ] Update vault SOP for adding new rules/standards

### Phase 4: Validation
- [ ] Create automated duplicate detection script
- [ ] Create file-to-database sync verification script
- [ ] Add pre-commit hook to enforce version footers

---

## Appendix A: File Inventory

### Project Rules (3)
```
C:\Projects\claude-family\.claude\rules\
├── commit-rules.md (40 lines) ✅
├── database-rules.md (32 lines) ✅
└── testing-rules.md (37 lines) ✅
```

### Global Instructions (9)
```
C:\Users\johnd\.claude\instructions\
├── a11y.instructions.md (122 lines) ⚠️ ORPHAN
├── csharp.instructions.md (62 lines) ✅
├── markdown.instructions.md (122 lines) ⚠️ DUPLICATE
├── mvvm.instructions.md (241 lines) ⚠️ ORPHAN
├── playwright.instructions.md (71 lines) ⚠️ ORPHAN
├── sql-postgres.instructions.md (118 lines) ⚠️ DUPLICATE
├── winforms.instructions.md (110 lines) ✅
├── winforms-dark-theme.instructions.md (163 lines) ⚠️ ORPHAN
└── wpf-ui.instructions.md (320 lines) ⚠️ ORPHAN
```

### Global Standards (24 total, 15 unique)
```
C:\Users\johnd\.claude\standards\
├── README.md (113 lines) ✅
├── core/
│   └── markdown-documentation.md (122 lines) ✅
├── language/
│   ├── csharp.md (174 lines) ✅
│   ├── rust.md (203 lines) ✅
│   ├── sql-postgres.md (79 lines) ✅
│   └── typescript.md (188 lines) ✅
├── framework/
│   ├── azure-bicep.md (205 lines) ✅
│   ├── Azure Bicep.md (205 lines) ⚠️ DUPLICATE
│   ├── azure-functions.md (149 lines) ✅
│   ├── Azure Functions.md (149 lines) ⚠️ DUPLICATE
│   ├── azure-logic-apps.md (112 lines) ✅
│   ├── Azure Logic Apps.md (112 lines) ⚠️ DUPLICATE
│   ├── mui.md (267 lines) ✅
│   ├── mui-design-system.md (198 lines) ✅
│   ├── react.md (184 lines) ✅
│   └── winforms.md (189 lines) ✅
├── pattern/
│   ├── docker.md (197 lines) ✅
│   ├── Docker Containerization.md (197 lines) ⚠️ DUPLICATE
│   ├── github-actions.md (169 lines) ✅
│   ├── GitHub Actions CI\CD.md (169 lines) ⚠️ DUPLICATE
│   ├── security-aspnet.md (274 lines) ✅
│   └── Security & ASP.NET APIs.md (274 lines) ⚠️ DUPLICATE
└── ~\.claude\standards\ ⚠️ LEGACY NESTED
    └── framework/
        ├── azure-bicep.md ⚠️ DUPLICATE
        ├── azure-functions.md ⚠️ DUPLICATE
        └── azure-logic-apps.md ⚠️ DUPLICATE
```

---

**Version**: 1.0
**Created**: 2026-01-19
**Updated**: 2026-01-19
**Location**: C:\Projects\claude-family\docs\RULES_AUDIT_REPORT.md
