# Documents Table Data Quality Analysis
**Schema:** `claude`
**Table:** `documents`
**Total Rows:** 1,727
**Analysis Date:** 2025-01-16

---

## Executive Summary

The `documents` table contains **significant data quality issues** with a high degree of data duplication, inconsistent categorization, and organizational problems. Critical issues include:

- ⚠️ **94% of documents are orphaned** (no project association)
- ⚠️ **338 duplicate documents** (19.6% duplication rate)
- ⚠️ **Inconsistent category naming** (case sensitivity issues)
- ⚠️ **All file paths are NULL** (no direct file references)
- ✅ **All critical fields populated** (no nulls in doc_type, doc_title, status)

---

## 1. Document Type Distribution

### Current Distribution (12 Types)
| Doc Type | Count | % of Total |
|----------|-------|-----------|
| OTHER | 1,291 | 74.8% |
| TROUBLESHOOTING | 94 | 5.4% |
| SESSION_NOTE | 91 | 5.3% |
| README | 81 | 4.7% |
| GUIDE | 45 | 2.6% |
| ARCHITECTURE | 43 | 2.5% |
| SOP | 33 | 1.9% |
| CLAUDE_CONFIG | 16 | 0.9% |
| SPEC | 15 | 0.9% |
| MIGRATION | 8 | 0.5% |
| API | 6 | 0.3% |
| ADR | 4 | 0.2% |

### Assessment
- **POOR STANDARDIZATION**: 74.8% marked as "OTHER" — indicates either:
  1. Lack of clear categorization at ingestion time
  2. Overly broad "OTHER" category
  3. Missing document classification logic

- **Missing Type Validation**: No apparent constraints on `doc_type` values
- **Recommendation**: Create stricter taxonomy and migrate miscategorized documents

---

## 2. Project Association Analysis

### Orphaned Documents: 1,625 out of 1,727 (94.1%)
**CRITICAL ISSUE**

| Project ID | Count | % of Associated |
|-----------|-------|-----------------|
| 10382d62-a550-473d-b219-d5b391aab7f2 | 84 | 98.8% |
| 1ec10c78-df7a-4f5b-86c5-8c18b89aea30 | 12 | 1.4% |
| fe18c320-d901-45e5-802c-17b96a5ff0cd | 3 | 0.4% |
| a3097e59-7799-4114-86a7-308702115905 | 3 | 0.4% |

### Assessment
- **Only 102 documents (5.9%) have project associations**
- **1,625 orphaned documents** create knowledge silo
- **Unclear intent**: Are orphaned docs:
  - Global/shared documents by design?
  - Never properly categorized?
  - Legacy documents without project context?

### Cleanup Recommendations
1. **Audit orphaned documents**: Determine if they should be associated with projects
2. **Add project_id validation**: Implement FK constraint to `projects` table
3. **Tag system**: Use tags to indicate "global" vs "orphaned"
4. **Categorization sprint**: Assign projects to relevant orphaned documents

---

## 3. Duplicate Documents Analysis

### Duplication Overview
- **Total Documents**: 1,727
- **Unique Titles**: 1,389
- **Duplicate Records**: 338 (19.6% duplication rate)

### Top 20 Duplicated Documents

| Doc Title | Count | Doc Type | Issue |
|-----------|-------|----------|-------|
| Page snapshot | 78 | OTHER | 🔴 Excessive duplication - likely web captures |
| Session Start | 17 | SESSION_NOTE | 🟡 Expected (recurring sessions) |
| Session End | 17 | SESSION_NOTE | 🟡 Expected (recurring sessions) |
| Broadcast Message | 16 | OTHER | 🔴 Should deduplicate or archive |
| Team Status | 16 | OTHER | 🔴 Should deduplicate or version |
| Inbox Check | 16 | OTHER | 🔴 Should deduplicate or archive |
| Create Feedback | 14 | OTHER | 🔴 Should deduplicate or archive |
| Feedback Check | 14 | OTHER | 🔴 Should deduplicate or archive |
| Coordinator Agent | 11 | OTHER | 🟡 Possibly versioned |
| claude-family-core Plugin | 11 | README | 🟡 Possibly versioned |
| Readme | 6 | README | 🟡 Likely intended (project READMEs) |
| List and Filter Feedback | 6 | OTHER | 🔴 Should deduplicate |
| robots.txt | 4 | OTHER | 🔴 Web artifact - remove |
| Llama Project: Tax AI Assistant | 4 | GUIDE | 🟡 Possibly versioned |

### Root Causes
1. **Web captures** ("Page snapshot" × 78): Crawled pages stored as documents
2. **Slash command outputs**: Same command run multiple times (inbox-check, feedback-check)
3. **Session/agent outputs**: Repeated "Session Start/End", "Team Status"
4. **Lack of deduplication logic**: No UUID/hash-based uniqueness checks
5. **Version history**: Documents stored per-version instead of having version field

### Cleanup Recommendations
1. **Immediate**: Delete web artifacts (robots.txt, page snapshots with empty content)
2. **Deduplication strategy**:
   - Keep latest version (by `updated_at`) of recurring documents
   - Archive historical versions separately
   - Use `version` field for version control instead of duplicate rows
3. **Prevent future duplication**:
   - Add unique constraint on (project_id, doc_title, version)
   - Implement deduplication check in document ingestion pipeline

---

## 4. Missing/Empty Content Analysis

### File Path Status
- **File Path NULL**: 1,727 (100%)
- **File Path EMPTY**: 0

**Assessment**: ALL documents store content inline (not as file references). This suggests documents table is the source of truth for content, not metadata pointing to external files.

### Content Storage
- No `content` column visible in schema (checked: doc_id, doc_type, doc_title, project_id, file_path, file_hash, version, status, created_at, updated_at, category, tags, generated_by_agent, last_verified_at)
- **Possible**: Content stored in separate table with FK relationship, or content is not persisted in this documents table

---

## 5. Status & Category Analysis

### Status Distribution
- **All 1,727 documents**: Status = 'ACTIVE'
- **Assessment**: No archive/deprecation strategy; all documents treated equally

### Category Distribution (14 unique values)
| Category | Count | Notes |
|----------|-------|-------|
| other | 1,291 | 74.8% - Mirrors doc_type=OTHER |
| troubleshooting | 94 | - |
| session_note | 91 | - |
| readme | 81 | - |
| guide | 45 | - |
| architecture | 42 | - |
| claude_config | 16 | - |
| SOP | 15 | 📌 **Case sensitivity: "SOP" (uppercase)** |
| spec | 15 | - |
| sop | 15 | 📌 **Case sensitivity: "sop" (lowercase)** |
| migration | 8 | - |
| api | 6 | - |
| adr | 4 | - |
| Other | 3 | 📌 **Case sensitivity: "Other" (title case)** |

### Data Quality Issues in Categories
1. **Case Sensitivity**: `sop`, `SOP` stored separately (30 rows affected)
2. **Naming Mismatch**: `Other` vs `other` (3 rows affected)
3. **Schema Design Issue**: `doc_type` and `category` overlap conceptually — redundant fields?
4. **NULL values**: 1 document with NULL category (0.06%)

---

## Cleanup Recommendations

### Priority 1: Critical (Address Immediately)
| Issue | Impact | Action | Effort |
|-------|--------|--------|--------|
| 94% Orphaned Documents | Knowledge fragmentation | Audit and reassign projects OR mark as "global" | **HIGH** |
| "Page snapshot" × 78 | Storage waste, noise | Delete all page snapshots with empty content | **LOW** |
| SOP/sop case inconsistency | Query/filter errors | Normalize to lowercase "sop" | **LOW** |
| Other/other case inconsistency | Query/filter errors | Normalize to lowercase "other" | **LOW** |

### Priority 2: Important (Address Within Sprint)
| Issue | Impact | Action | Effort |
|-------|--------|--------|--------|
| 75% in "OTHER" category | Useless categorization | Implement categorization rules, reclassify docs | **HIGH** |
| Duplicate recurring documents | Storage bloat (338 records) | Implement versioning strategy, deduplicate | **MEDIUM** |
| No version control | No history tracking | Add `version` column strategy or use separate audit table | **MEDIUM** |
| All status = ACTIVE | No lifecycle management | Implement deprecation workflow, archival | **LOW** |

### Priority 3: Improvement (Address Long-term)
| Issue | Impact | Action | Effort |
|-------|--------|--------|--------|
| No content column in schema | Unclear where content stored | Map to actual content storage location | **MEDIUM** |
| All file_path = NULL | No file references | Decide: store content inline or as FKs? | **MEDIUM** |
| Overlapping doc_type & category | Schema confusion | Consolidate into single classification field | **MEDIUM** |
| No file hash validation | Content integrity unknown | Implement hash verification process | **LOW** |

---

## SQL Scripts for Cleanup

### 1. Normalize Category Case Sensitivity
```sql
-- Normalize SOP/sop to lowercase
UPDATE claude.documents SET category = 'sop' WHERE LOWER(category) = 'sop' AND category != 'sop';

-- Normalize Other/other to lowercase
UPDATE claude.documents SET category = 'other' WHERE LOWER(category) = 'other' AND category != 'other';

-- Verify
SELECT category, COUNT(*) FROM claude.documents WHERE category IS NOT NULL GROUP BY category ORDER BY COUNT(*) DESC;
```

### 2. List Detailed Duplicate Documents
```sql
-- Show all "Page snapshot" duplicates for review
SELECT doc_id, doc_title, doc_type, created_at, updated_at, file_hash 
FROM claude.documents 
WHERE doc_title = 'Page snapshot' 
ORDER BY created_at DESC;

-- Keep only the latest version of each duplicate
WITH ranked_docs AS (
  SELECT 
    doc_id,
    doc_title,
    ROW_NUMBER() OVER (PARTITION BY doc_title, doc_type ORDER BY updated_at DESC) as rn
  FROM claude.documents
  WHERE doc_title = 'Page snapshot'
)
SELECT doc_id FROM ranked_docs WHERE rn > 1; -- IDs to delete
```

### 3. Identify Orphaned Documents by Type
```sql
-- Show orphaned documents by type
SELECT doc_type, category, COUNT(*) as count 
FROM claude.documents 
WHERE project_id IS NULL 
GROUP BY doc_type, category 
ORDER BY COUNT(*) DESC;

-- Review session notes that are orphaned
SELECT doc_id, doc_title, doc_type, created_at 
FROM claude.documents 
WHERE project_id IS NULL AND doc_type = 'SESSION_NOTE' 
LIMIT 10;
```

### 4. Find Candidates for Archival
```sql
-- Documents not updated in 90 days (potential archives)
SELECT doc_id, doc_title, updated_at, doc_type, project_id
FROM claude.documents
WHERE updated_at < CURRENT_TIMESTAMP - INTERVAL '90 days'
ORDER BY updated_at ASC
LIMIT 100;
```

---

## Data Quality Score

| Dimension | Score | Status |
|-----------|-------|--------|
| **Completeness** | 8/10 | ✅ No nulls in key fields (doc_type, doc_title, status) |
| **Uniqueness** | 4/10 | ❌ 19.6% duplication rate |
| **Consistency** | 5/10 | ⚠️ Case sensitivity, doc_type/category overlap |
| **Validity** | 7/10 | ✅ All doc_types are standardized |
| **Organization** | 2/10 | ❌ 94% orphaned, 75% in "OTHER" |
| **Timeliness** | 6/10 | ⚠️ No update frequency tracking |
| **Overall Quality** | **5.3/10** | ⚠️ **NEEDS IMPROVEMENT** |

---

## Next Steps

### Week 1: Quick Wins
1. ✅ Run normalization scripts (Priority 1 issues)
2. ✅ Audit and delete invalid page snapshots
3. ✅ Create data quality dashboard

### Week 2-3: Deep Clean
1. Review orphaned documents (1,625 rows)
2. Implement deduplication rules
3. Set up versioning strategy

### Week 4+: Prevention
1. Add data quality checks to ingestion pipeline
2. Implement project_id validation
3. Create documentation taxonomy

---

## Questions for Stakeholder Review

1. **Orphaned Documents**: Are 1,625 documents intentionally global/project-agnostic?
2. **Duplicate Sessions**: Are "Session Start/End" duplicates by design (one per actual session), or should we consolidate?
3. **Content Storage**: Where is actual document content stored? (Not visible in schema)
4. **Purpose of doc_type vs category**: Why maintain both fields? Can they be consolidated?
5. **Page Snapshots**: Are the 78 "Page snapshot" records web crawls? Should they be archived or deleted?

---

**Report Generated:** 2025-01-16
**Next Review:** 2025-02-16 (Monthly)
