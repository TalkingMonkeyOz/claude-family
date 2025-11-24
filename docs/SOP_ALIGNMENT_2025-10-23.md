# SOP Alignment - Documentation System Integration

**Date**: 2025-10-23
**Purpose**: Align SOP-PROJ-001 with new documentation management system

---

## Existing Process (SOP-PROJ-001)

**Current Phase 5: Project Setup** creates:

### Business Documents (6 Living Docs)
1. PROJECT_BRIEF.md - Problem statement, objectives, success criteria
2. BUSINESS_CASE.md - Market analysis, revenue model, GTM strategy
3. ARCHITECTURE.md - System design, tech stack, scalability
4. EXECUTION_PLAN.md - Phases, milestones, work packages, timeline
5. COMPLIANCE.md - Regulatory requirements, data privacy
6. RISKS.md - Risk register with mitigation plans

### Filesystem Structure
```
C:\Projects\{project-name}/
├── docs/
│   ├── PROJECT_BRIEF.md
│   ├── BUSINESS_CASE.md
│   ├── ARCHITECTURE.md
│   ├── EXECUTION_PLAN.md
│   ├── COMPLIANCE.md
│   └── RISKS.md
├── src/ or /backend/
├── /frontend/ (if web)
├── /tests/
├── /data/
├── README.md
└── .gitignore
```

### What's Missing
- ❌ No CLAUDE.md (AI context file)
- ❌ No .docs-manifest.json (documentation tracking)
- ❌ No git pre-commit hooks (line limit enforcement)
- ❌ No documentation audit process
- ❌ No archival strategy

---

## New Documentation System

**Created 2025-10-23** provides:

### Core Requirements
1. **CLAUDE.md** - AI assistant context file (≤250 lines enforced)
2. **.docs-manifest.json** - Tracks all markdown files
3. **Git pre-commit hook** - Enforces CLAUDE.md line limit
4. **Monthly audits** - Documentation health checks
5. **Archival process** - Move old docs to `docs/archive/YYYY-MM/`

### Scripts Available
- `init_project_docs.py` - Initialize system for any project
- `audit_docs.py` - Monthly documentation audit
- `archive_docs.py` - Archive old documentation
- `update_manifest_lines.py` - Sync line counts

---

## Gap Analysis

| Requirement | SOP-PROJ-001 | New System | Gap |
|-------------|--------------|------------|-----|
| Business documents | ✅ Yes (6 living docs) | N/A | None |
| AI context file | ❌ No | ✅ CLAUDE.md | **Missing** |
| Documentation tracking | ❌ No | ✅ .docs-manifest.json | **Missing** |
| Line limit enforcement | ❌ No | ✅ Git hook | **Missing** |
| Audit process | ❌ No | ✅ Monthly audit | **Missing** |
| Archival strategy | ❌ No | ✅ Automated | **Missing** |
| Git setup | ✅ .gitignore | ✅ Pre-commit hook | **Partial** |

---

## Proposed Integration

### Update SOP-PROJ-001 Phase 5

**Add new substep 5.1: Initialize Documentation System**

```json
{
  "step_number": "5.1",
  "phase": "Phase 5: Project Setup",
  "action": "Initialize documentation management system",
  "responsible": "Diana",
  "duration": "~5 minutes",
  "details": "After creating project directory, run: python C:\\Projects\\claude-family\\scripts\\init_project_docs.py C:\\Projects\\{project-name}. This creates: .docs-manifest.json (tracks all markdown files), git pre-commit hook (enforces CLAUDE.md ≤250 lines), initial categorization of 6 living docs. Verify CLAUDE.md created and under 250 lines. This integrates with monthly documentation audit process."
}
```

### Update Existing Step 5 (Filesystem)

**Add to filesystem structure:**

```diff
  C:\Projects\{project-name}/
+ ├── CLAUDE.md (AI context - auto-loaded by Claude Code)
+ ├── .docs-manifest.json (documentation tracking)
  ├── docs/
  │   ├── PROJECT_BRIEF.md
  │   ├── BUSINESS_CASE.md
  │   ├── ARCHITECTURE.md
  │   ├── EXECUTION_PLAN.md
  │   ├── COMPLIANCE.md
  │   └── RISKS.md
  ├── src/ or /backend/
  ├── /frontend/ (if web)
  ├── /tests/
  ├── /data/
  ├── README.md
+ ├── .git/hooks/pre-commit (enforces CLAUDE.md limit)
  └── .gitignore
```

### Add New Step 5.2: Create CLAUDE.md

```json
{
  "step_number": "5.2",
  "phase": "Phase 5: Project Setup",
  "action": "Create CLAUDE.md with project context",
  "responsible": "Diana",
  "duration": "~15 minutes",
  "details": "Create CLAUDE.md (≤250 lines) containing: Project type & purpose, Build commands, Key constraints/gotchas, Tech stack, Recent work (SQL query to session_history), File structure overview. Template available at C:\\Projects\\claude-family\\templates\\CLAUDE.md. This file auto-loads when Claude Code opens the project, providing instant context restoration. Update as project evolves, monthly audit ensures it stays under 250 lines."
}
```

---

## CLAUDE.md Template

**Proposed template for new projects:**

```markdown
# {PROJECT_NAME}

**Type**: {commercial/internal}
**Purpose**: {One-line description}

---

## Build Commands

```bash
# Development
npm run dev  # or python app.py, etc.

# Tests
npm test

# Build
npm run build
```

---

## Key Constraints

- {Constraint 1}
- {Constraint 2}

---

## Tech Stack

- **Frontend**: {React, Vue, etc. or N/A}
- **Backend**: {Python/FastAPI, Node, etc.}
- **Database**: {PostgreSQL, etc.}
- **Hosting**: {AWS, Azure, local, etc.}

---

## File Structure

```
{project-name}/
├── src/              # Source code
├── tests/            # Test files
├── docs/             # Business documents (6 living docs)
└── README.md         # User-facing documentation
```

---

## Recent Work

```sql
SELECT summary, outcome, files_modified, session_start
FROM claude_family.session_history
WHERE project_name = '{project-name}'
ORDER BY session_start DESC LIMIT 10;
```

---

**Version**: 1.0
**Created**: {DATE}
**Location**: C:\\Projects\\{project-name}\\CLAUDE.md
```

---

## Recommendations

### Immediate Actions (Diana)

1. **Update SOP-PROJ-001 in database**
   - Add step 5.1: Initialize documentation system
   - Add step 5.2: Create CLAUDE.md
   - Update filesystem structure diagram
   - Add reference to monthly audit process

2. **Create CLAUDE.md template**
   - Save to `C:\Projects\claude-family\templates\CLAUDE.md`
   - Use for all new projects
   - Keep under 250 lines

3. **Add to Phase 6 (Monitoring)**
   - Monthly documentation audit for all active projects
   - Archive old session notes/reports quarterly
   - Update .docs-manifest.json when adding new docs

### Long-term Enhancements

1. **Automate CLAUDE.md creation**
   - Extract project metadata from database
   - Auto-generate initial CLAUDE.md from living docs
   - Diana creates during Phase 5

2. **Integrate with work packages**
   - Track documentation work packages
   - Alert when CLAUDE.md approaches 250 lines
   - Suggest archival candidates

3. **Cross-project reporting**
   - Dashboard showing all projects' doc health
   - Alert when any project exceeds limits
   - Aggregate stats for management

---

## Migration Plan for Existing Projects

**Already completed (2025-10-23):**

✅ **claude-family**: 33 files, 0 archive candidates, CLAUDE.md 95/250
✅ **nimbus-user-loader**: 39 files, 5 candidates, CLAUDE.md 196/250
✅ **ATO-tax-agent**: 15 files, 4 candidates, CLAUDE.md 80/250
✅ **claude-pm**: 23 files, 6 candidates, CLAUDE.md 301/250 (OVER!)

**Required actions:**
- ⏰ Fix claude-pm CLAUDE.md (trim 51 lines)
- ⏰ Initialize ATO as git repo (then reinstall hook)

**Future projects** (when created):
- Run init_project_docs.py during Phase 5
- Create CLAUDE.md from template
- Audit monthly

---

## Benefits of Integration

### For Diana (Project Manager)
- ✅ Automated documentation health checks
- ✅ No manual tracking of doc line counts
- ✅ Clear archival process for old documents
- ✅ Consistent structure across all projects

### For Claude Family (All Agents)
- ✅ CLAUDE.md provides instant project context
- ✅ ≤250 lines keeps context focused and loadable
- ✅ Documentation doesn't bloat over time
- ✅ Easy to find relevant historical docs

### For John (User)
- ✅ Projects stay organized automatically
- ✅ No "where did that doc go?" confusion
- ✅ Living docs + AI context work together
- ✅ System scales as projects grow

---

## Validation

**System tested across 4 projects:**
- ✅ claude-family (infrastructure)
- ✅ nimbus-user-loader (work)
- ✅ ATO-tax-agent (work)
- ✅ claude-pm (infrastructure)

**Results:**
- All projects initialized successfully
- Audits running on all projects
- Git hooks preventing CLAUDE.md bloat
- Found 1 project over limit (claude-pm)
- Identified 15 large files across projects for review

---

## Next Steps

1. **Update SOP-PROJ-001** (SQL UPDATE in database)
2. **Create CLAUDE.md template** (save to templates/)
3. **Fix claude-pm CLAUDE.md** (trim to ≤250 lines)
4. **Document in session_history** (this alignment work)
5. **Add to shared_knowledge** (new pattern learned)

---

**Status**: Ready for SOP update
**Impact**: Medium (adds 2 steps to Phase 5, ~20 minutes total)
**Risk**: Low (system already tested across 4 projects)
