# Knowledge Vault Compliance Remediation Plan

**Date:** 2025-12-27
**Based On:** VAULT_COMPLIANCE_AUDIT_2025-12-26.md
**Current Compliance:** 6.7% (4 of 60 files)
**Target Compliance:** 100% (60 of 60 files)

---

## Executive Summary

**Scope:** Fix 56 non-compliant files across 4 issue categories
**Estimated Effort:** 4-6 hours (using agent automation)
**Approach:** Prioritize by severity, automate where possible

---

## Issue Priorities

### Priority 1: CRITICAL - Oversized Files (12 files)
**Impact:** Blocks AI comprehension, violates documentation standards
**Action:** Split into multiple files or condense

| File | Lines | Over By | Action |
|------|-------|---------|--------|
| Session User Stories.md | 1,374 | 1,074 | **Split into 5-6 files** (already started) |
| Database Schema - Core Tables.md | 691 | 391 | **Split by table category** |
| Session Lifecycle.md | 674 | 374 | **Split into workflow docs** (already done) |
| Identity System.md | 532 | 232 | **Split into 2 files** |
| AI_READABLE_DOCUMENTATION_RESEARCH.md | 391 | 91 | **Condense or archive** |
| Documentation Philosophy.md | 370 | 220 | **Split into principles + examples** |
| Auto-Apply Instructions.md | 299 | 149 | **Condense** |
| Session Architecture.md | 296 | 146 | **Already split, may need more** |
| MCP Registry.md | 232 | 82 | **Condense or accept** |
| Orchestrator MCP.md | 213 | 63 | **Condense** |
| Knowledge System.md | 213 | 63 | **Condense** |
| Observability.md | 192 | 42 | **Condense** |

**Strategy:**
- Session User Stories: Already split into Overview + 5 user stories ✅
- Database Schema: Split into Overview, Core Tables, Supporting Tables, Workspace & Agents
- Session Lifecycle: Already split into Overview, Reference, Start, End ✅
- Others: Condense by removing redundancy, moving examples to separate files

---

### Priority 2: HIGH - Missing Version Footers (48 files)
**Impact:** Violates documentation standards, hard to track updates
**Action:** Add footer template to all files

**Footer Template:**
```markdown
---

**Version**: 1.0
**Created**: YYYY-MM-DD
**Updated**: YYYY-MM-DD
**Location**: knowledge-vault/[folder]/[filename].md
```

**Automation Approach:**
```python
# Script: add_version_footers.py
# For each file:
#   - Check if has footer
#   - If not, append footer with:
#     - Version: 1.0
#     - Created: file creation date (from git)
#     - Updated: last modified date (from git)
#     - Location: relative path from vault root
```

**Files to Fix:** All 48 files listed in audit section "Missing Version Footer"

---

### Priority 3: MEDIUM - Missing YAML Fields (27 files missing tags, 11 missing projects)
**Impact:** Reduces searchability, violates standards
**Action:** Add missing YAML fields based on file location/content

**Tag Assignment Rules:**
- `Claude Family/` → `claude-family`, `quick-reference`, `[topic]`
- `20-Domains/` → `domain-knowledge`, `[domain]`, `[technology]`
- `30-Patterns/` → `pattern`, `[category]` (gotcha/solution)
- `40-Procedures/` → `procedure`, `sop`, `[workflow]`

**Project Assignment Rules:**
- `Claude Family/Project - X.md` → projects: [X]
- WinForms docs → projects: [claude-family-manager-v2, mission-control-web]
- Database docs → projects: [claude-family]
- Generic patterns/procedures → projects: [] (empty array, applies to all)

**Automation Approach:**
```python
# Script: fix_yaml_frontmatter.py
# For each file:
#   - Parse YAML frontmatter
#   - If missing 'tags:', infer from folder + filename
#   - If missing 'projects:', infer from content/folder
#   - Update YAML
#   - Preserve existing values
```

---

### Priority 4: LOW - Missing YAML Entirely (2 files)
**Impact:** Violates standards, not indexed
**Action:** Add complete YAML frontmatter

**Files:**
1. `John's Notes/AI_READABLE_DOCUMENTATION_RESEARCH.md`
2. `John's Notes/Copiliot awsome Git hub.md`

**Action:** Add frontmatter based on content analysis

---

## Implementation Plan

### Phase 1: Critical Oversized Files (Day 1, 2-3 hours)

**Task 1.1: Database Schema Split** ⏱ 60 min
- ✅ Already split (done in Dec 27): Overview, Core Tables, Supporting Tables, Workspace & Agents
- Verify each < 300 lines
- Add cross-references

**Task 1.2: Identity System Split** ⏱ 30 min
- Create "Identity System - Overview.md" (200 lines)
- Create "Identity System - Per Project.md" (200 lines)
- Move content from 532-line file
- Update cross-references

**Task 1.3: Other Oversized Files** ⏱ 60 min
- Documentation Philosophy.md → Split into principles + examples
- Auto-Apply Instructions.md → Condense
- MCP Registry.md → Condense (remove redundant examples)
- Orchestrator MCP.md → Condense
- Knowledge System.md → Condense
- Observability.md → Condense

### Phase 2: Version Footers (Day 1, 1-2 hours)

**Task 2.1: Automated Footer Addition** ⏱ 30 min
- Write `add_version_footers.py` script
- Extract git creation/modified dates
- Generate footer text
- Test on 3 files

**Task 2.2: Bulk Footer Addition** ⏱ 60 min
- Run script on all 48 files
- Manual review of 10 random files
- Fix any edge cases

### Phase 3: YAML Frontmatter (Day 2, 1-2 hours)

**Task 3.1: Automated YAML Fix** ⏱ 45 min
- Write `fix_yaml_frontmatter.py` script
- Tag inference rules
- Project inference rules
- Test on 5 files

**Task 3.2: Bulk YAML Fix** ⏱ 60 min
- Run script on 27 files (missing tags)
- Run script on 11 files (missing projects)
- Run script on 2 files (missing YAML entirely)
- Manual review of inferred tags/projects

### Phase 4: Verification (Day 2, 30 min)

**Task 4.1: Re-run Audit** ⏱ 15 min
- Run compliance audit script
- Generate new CSV report
- Compare to baseline

**Task 4.2: Quality Check** ⏱ 15 min
- Verify 10 random files fully compliant
- Check cross-references work
- Update this plan with results

---

## Automation Scripts Required

### Script 1: `add_version_footers.py`
**Purpose:** Add version footers to files missing them
**Input:** List of file paths (from audit CSV)
**Output:** Updated markdown files with footers
**Logic:**
1. For each file:
2. Read content
3. Check if already has footer (search for "**Version**:")
4. If not, get git history (creation date, last modified)
5. Generate footer template
6. Append to file
7. Log changes

**Example:**
```python
import subprocess
from pathlib import Path

def get_git_dates(file_path):
    # Get creation date (first commit)
    created = subprocess.check_output(
        ['git', 'log', '--diff-filter=A', '--format=%aI', file_path],
        text=True
    ).strip().split('\n')[-1]

    # Get last modified date
    updated = subprocess.check_output(
        ['git', 'log', '-1', '--format=%aI', file_path],
        text=True
    ).strip()

    return created[:10], updated[:10]
```

### Script 2: `fix_yaml_frontmatter.py`
**Purpose:** Add missing YAML fields (tags, projects)
**Input:** List of file paths + folder location
**Output:** Updated markdown files with complete YAML
**Logic:**
1. Parse existing YAML frontmatter
2. Infer tags from folder + filename if missing
3. Infer projects from content/folder if missing
4. Generate new YAML block
5. Replace frontmatter
6. Log changes

**Tag Inference Rules:**
```python
def infer_tags(file_path):
    folder = file_path.parent.name
    filename = file_path.stem.lower()

    tags = []

    # Folder-based tags
    if folder == "Claude Family":
        tags.extend(["claude-family", "quick-reference"])
    elif folder in ["APIs", "Database", "CSharp", "WinForms"]:
        tags.extend(["domain-knowledge", folder.lower()])
    elif folder == "gotchas":
        tags.extend(["pattern", "gotcha"])
    elif folder == "solutions":
        tags.extend(["pattern", "solution"])
    elif "Procedures" in file_path.parts:
        tags.extend(["procedure", "sop"])

    # Filename-based tags (extract keywords)
    if "mcp" in filename:
        tags.append("mcp")
    if "session" in filename:
        tags.append("session")
    if "hook" in filename:
        tags.append("hooks")

    return list(set(tags))
```

### Script 3: `audit_compliance.py` (already exists?)
**Purpose:** Re-run audit to verify compliance
**Input:** Vault directory
**Output:** CSV report + markdown summary
**Already exists?** Check `scripts/` directory

---

## Agent Delegation Strategy

**Option 1: Use doc-keeper-haiku agent**
- Designed for vault maintenance
- Has filesystem + postgres access
- Can run scripts and verify results

**Option 2: Use python-coder-haiku agent**
- Write the automation scripts
- Test on sample files
- Run bulk operations

**Option 3: Manual with lightweight-haiku**
- Fix files one-by-one
- Good for complex content decisions
- Slower but more accurate

**Recommendation:** Hybrid approach
1. **python-coder-haiku**: Write automation scripts (1 hour)
2. **doc-keeper-haiku**: Run scripts + verify (1 hour)
3. **Manual review**: Complex files (Documentation Philosophy, etc.) (1 hour)

---

## Success Criteria

✅ **All files < size limit** (300 lines for most, 150 for Claude Family/)
✅ **All files have version footer** (48 files fixed)
✅ **All files have complete YAML** (tags, projects fields)
✅ **Compliance > 95%** (57+ of 60 files)
✅ **Cross-references valid** (no broken wiki-links)
✅ **Audit CSV updated** (new baseline)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Automation introduces errors | High | Manual review of 10 random files |
| Git history missing for some files | Medium | Use file modified date as fallback |
| Tag/project inference wrong | Medium | Dry-run mode, show inferred values before applying |
| Breaking existing cross-references | High | Validate all wiki-links after split |
| Content loss during splits | Critical | Git commit before each phase |

---

## Rollback Plan

**If automation fails:**
1. Git reset to commit before Phase 2/3
2. Manual fix on subset of files (priority 1 only)
3. Document issues for future improvement

**Git Commit Strategy:**
- Commit after Phase 1 (oversized files fixed)
- Commit after Phase 2 (version footers added)
- Commit after Phase 3 (YAML fixed)
- Each commit = rollback point

---

## Next Steps

1. **Decide on approach**: Agent automation vs manual?
2. **Phase 1**: Fix critical oversized files (manual, 2 hours)
3. **Phase 2**: Write automation scripts (python-coder-haiku, 1 hour)
4. **Phase 3**: Run automation (doc-keeper-haiku, 1 hour)
5. **Phase 4**: Verify compliance (audit script, 15 min)
6. **Update database todo**: Mark compliance task complete

---

**Estimated Total Time:** 4-6 hours
**Recommended Start:** Next session
**Agent Support:** python-coder-haiku + doc-keeper-haiku
**Manual Work Required:** ~2 hours (oversized files + review)

---

**Created:** 2025-12-27
**Status:** Ready for execution
**Approval Required:** User confirmation on approach
