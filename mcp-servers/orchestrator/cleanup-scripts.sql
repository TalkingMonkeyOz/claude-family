-- ============================================================================
-- KNOWLEDGE TABLE DATA QUALITY CLEANUP SCRIPTS
-- ============================================================================
-- Database: ai_company_foundation
-- Schema: claude.knowledge
-- Date: 2025-10-24
--
-- BACKUP BEFORE RUNNING! These scripts are destructive.
-- Run in sequence: Phase 1 → Phase 2 → Phase 3 → Phase 4
-- ============================================================================


-- ============================================================================
-- PHASE 1: CRITICAL DATA INTEGRITY FIXES (9 minutes total)
-- ============================================================================

-- STEP 1.1: Remove 6 duplicate records (KEEP OLDEST, DELETE NEWER)
-- Expected: 6 rows deleted, reducing 144 → 138 records
-- ============================================================================
BEGIN;

WITH duplicates AS (
  SELECT 
    knowledge_id,
    title,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY title ORDER BY created_at DESC) as rn
  FROM claude.knowledge
  WHERE title IN (
    'OneDrive caches build folders causing stale DLL issues',
    'CancellationToken for graceful operation cancellation',
    'MCP server logs location for diagnostics',
    'HttpClient session affinity with CookieContainer',
    'Form.Shown event for control initialization requiring window handles',
    'Windows-MCP server requires uv package manager'
  )
)
SELECT COUNT(*) as records_to_delete FROM duplicates WHERE rn = 1;

-- Verify the query above returns 6 before running DELETE
-- Then uncomment to execute:
/*
WITH duplicates AS (
  SELECT 
    knowledge_id,
    title,
    created_at,
    ROW_NUMBER() OVER (PARTITION BY title ORDER BY created_at DESC) as rn
  FROM claude.knowledge
  WHERE title IN (
    'OneDrive caches build folders causing stale DLL issues',
    'CancellationToken for graceful operation cancellation',
    'MCP server logs location for diagnostics',
    'HttpClient session affinity with CookieContainer',
    'Form.Shown event for control initialization requiring window handles',
    'Windows-MCP server requires uv package manager'
  )
)
DELETE FROM claude.knowledge
WHERE knowledge_id IN (
  SELECT knowledge_id FROM duplicates WHERE rn = 1
);
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- STEP 1.2: Normalize case-sensitive knowledge types
-- Expected: 6 records updated (PATTERN→pattern, ARCHITECTURE→architecture, etc.)
-- ============================================================================
BEGIN;

-- Show what will be updated
SELECT knowledge_type, COUNT(*) as count
FROM claude.knowledge
WHERE knowledge_type IN ('PATTERN', 'ARCHITECTURE', 'GOTCHA', 'API_PATTERN')
GROUP BY knowledge_type;

-- Execute these updates:
/*
UPDATE claude.knowledge SET knowledge_type = 'pattern' 
WHERE knowledge_type = 'PATTERN';

UPDATE claude.knowledge SET knowledge_type = 'architecture' 
WHERE knowledge_type = 'ARCHITECTURE';

UPDATE claude.knowledge SET knowledge_type = 'gotcha' 
WHERE knowledge_type = 'GOTCHA';

UPDATE claude.knowledge SET knowledge_type = 'api-pattern'
WHERE knowledge_type = 'API_PATTERN';
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- STEP 1.3: Normalize typos and bug-fix variants
-- Expected: 5 records updated (bugfix, bug_fix_pattern, bug_workaround, etc.)
-- ============================================================================
BEGIN;

-- Show what will be updated
SELECT knowledge_type, COUNT(*) as count
FROM claude.knowledge
WHERE knowledge_type IN ('bugfix', 'bug_fix_pattern', 'bug_workaround')
GROUP BY knowledge_type;

-- Execute this update:
/*
UPDATE claude.knowledge SET knowledge_type = 'bug-fix' 
WHERE knowledge_type IN ('bugfix', 'bug_fix_pattern', 'bug_workaround');
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- STEP 1.4: Fix confidence level scale (0-100 to 1-10)
-- Expected: 6 records updated (85→9, 90→9, 95→10)
-- ============================================================================
BEGIN;

-- Show what will be updated
SELECT knowledge_id, title, confidence_level
FROM claude.knowledge
WHERE confidence_level NOT BETWEEN 1 AND 10
ORDER BY confidence_level DESC;

-- Execute this update:
/*
UPDATE claude.knowledge 
SET confidence_level = ROUND(confidence_level / 10.0)::int 
WHERE confidence_level > 10;
*/

-- Verify result
SELECT knowledge_id, title, confidence_level
FROM claude.knowledge
WHERE confidence_level IS NOT NULL
ORDER BY confidence_level DESC
LIMIT 10;

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- PHASE 2: STANDARDIZATION (8 minutes total)
-- ============================================================================

-- STEP 2.1: Consolidate *-pattern variants into 'pattern'
-- Expected: 7 records updated
-- ============================================================================
BEGIN;

-- Show what will be updated
SELECT knowledge_type, COUNT(*) as count
FROM claude.knowledge
WHERE knowledge_type IN (
  'code-pattern', 'design-pattern', 'technical-pattern',
  'performance-pattern', 'security-pattern', 'api-pattern', 'bug-pattern'
)
GROUP BY knowledge_type;

-- Execute these updates:
/*
UPDATE claude.knowledge SET knowledge_type = 'pattern' 
WHERE knowledge_type IN (
  'code-pattern',
  'design-pattern',
  'technical-pattern',
  'performance-pattern',
  'security-pattern',
  'api-pattern'
);

UPDATE claude.knowledge SET knowledge_type = 'bug-fix' 
WHERE knowledge_type = 'bug-pattern';
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- STEP 2.2: Map non-standard single-use types to core types
-- Expected: 20 records updated across 5 mappings
-- ============================================================================
BEGIN;

-- Show distribution of non-standard types
SELECT knowledge_type, COUNT(*) as count
FROM claude.knowledge
WHERE knowledge_type NOT IN (
  'pattern', 'gotcha', 'bug-fix', 'architecture', 'technique',
  'best-practice', 'troubleshooting', 'process', 'configuration',
  'mcp-tool', 'mcp-server'
)
GROUP BY knowledge_type
ORDER BY COUNT(*) DESC;

-- Execute these updates:
/*
-- Map infrastructure/system → architecture
UPDATE claude.knowledge SET knowledge_type = 'architecture' 
WHERE knowledge_type IN ('system', 'infrastructure', 'architecture_pattern');

-- Map performance/debugging/implementation → pattern
UPDATE claude.knowledge SET knowledge_type = 'pattern' 
WHERE knowledge_type IN ('performance', 'debugging', 'implementation');

-- Map testing/methodology → best-practice
UPDATE claude.knowledge SET knowledge_type = 'best-practice' 
WHERE knowledge_type IN ('testing', 'methodology');

-- Map lesson/reference/solution/procedure → process
UPDATE claude.knowledge SET knowledge_type = 'process' 
WHERE knowledge_type IN ('lesson', 'reference', 'solution', 'procedure');

-- Map api-limitation → gotcha
UPDATE claude.knowledge SET knowledge_type = 'gotcha'
WHERE knowledge_type = 'api-limitation';
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- PHASE 3: ADD VALIDATION CONSTRAINTS (7 minutes total)
-- ============================================================================

-- STEP 3.1: Add confidence_level validation constraint
-- Expected: Prevents future invalid confidence values (>10 or <1)
-- ============================================================================
BEGIN;

-- First verify no violations exist
SELECT COUNT(*) as violations
FROM claude.knowledge
WHERE confidence_level IS NOT NULL 
  AND (confidence_level < 1 OR confidence_level > 10);

-- Execute if result is 0:
/*
ALTER TABLE claude.knowledge 
ADD CONSTRAINT confidence_level_valid 
CHECK (confidence_level IS NULL OR (confidence_level >= 1 AND confidence_level <= 10));
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- STEP 3.2: Add knowledge_type NOT NULL and non-empty constraint
-- Expected: Ensures all records have a non-empty knowledge_type
-- ============================================================================
BEGIN;

-- Verify no violations exist
SELECT COUNT(*) as violations
FROM claude.knowledge
WHERE knowledge_type IS NULL OR knowledge_type = '';

-- Execute if result is 0:
/*
ALTER TABLE claude.knowledge 
ADD CONSTRAINT knowledge_type_not_empty 
CHECK (knowledge_type IS NOT NULL AND knowledge_type != '');
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- STEP 3.3: Add knowledge_type standardization constraint (OPTIONAL)
-- Expected: Restricts knowledge_type to 12 approved values
-- ============================================================================
BEGIN;

-- Verify all current types are in approved list
SELECT COUNT(*) as non_standard_types
FROM claude.knowledge
WHERE knowledge_type NOT IN (
  'pattern', 'gotcha', 'bug-fix', 'architecture', 'technique',
  'best-practice', 'troubleshooting', 'process', 'configuration',
  'mcp-tool', 'mcp-server'
);

-- Execute if result is 0:
/*
ALTER TABLE claude.knowledge 
ADD CONSTRAINT knowledge_type_standard 
CHECK (knowledge_type IN (
  'pattern', 'gotcha', 'bug-fix', 'architecture', 'technique',
  'best-practice', 'troubleshooting', 'process', 'configuration',
  'mcp-tool', 'mcp-server'
));
*/

ROLLBACK;  -- Change to COMMIT when ready to execute


-- ============================================================================
-- PHASE 4: METADATA CLEANUP (25 minutes total)
-- ============================================================================

-- STEP 4.1: Identify records with missing applies_to_projects
-- Expected: 11 records
-- ============================================================================
SELECT 
  knowledge_id,
  title,
  knowledge_type,
  created_at,
  applies_to_projects
FROM claude.knowledge 
WHERE applies_to_projects IS NULL 
  OR array_length(applies_to_projects, 1) IS NULL
ORDER BY created_at DESC;

-- Review these records and decide what projects they apply to
-- Then run targeted updates like:
/*
UPDATE claude.knowledge 
SET applies_to_projects = ARRAY['claude-pm']
WHERE title LIKE '%PostgreSQL%' 
  AND applies_to_projects IS NULL;
*/


-- ============================================================================
-- STEP 4.2: Review records with missing learned_by_identity_id
-- Expected: 33 records
-- ============================================================================
SELECT 
  knowledge_id,
  title,
  knowledge_type,
  created_at,
  learned_by_identity_id
FROM claude.knowledge 
WHERE learned_by_identity_id IS NULL
ORDER BY created_at DESC
LIMIT 20;

-- Option 1: Leave as NULL if knowledge is collective
-- Option 2: Assign to 'system' identity if created by batch process:
/*
UPDATE claude.knowledge 
SET learned_by_identity_id = (
  SELECT identity_id 
  FROM claude.identities
  WHERE name = 'system'
)
WHERE learned_by_identity_id IS NULL 
  AND created_at = '2025-10-10 21:53:44';  -- Batch creation time
*/


-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- ============================================================================
-- POST-CLEANUP VERIFICATION (Run after all phases complete)
-- ============================================================================

-- Overall quality metrics
SELECT 
  COUNT(*) as total_records,
  COUNT(DISTINCT title) as distinct_titles,
  COUNT(DISTINCT LOWER(knowledge_type)) as distinct_types,
  COUNT(CASE WHEN applies_to_projects IS NULL THEN 1 END) as null_projects,
  COUNT(CASE WHEN learned_by_identity_id IS NULL THEN 1 END) as null_owner,
  COUNT(CASE WHEN confidence_level IS NULL THEN 1 END) as null_confidence,
  COUNT(CASE WHEN confidence_level BETWEEN 1 AND 10 THEN 1 END) as valid_confidence,
  COUNT(CASE WHEN code_example IS NULL OR TRIM(code_example) = '' THEN 1 END) as null_examples
FROM claude.knowledge;

-- Expected results:
-- total_records: 138 (down from 144)
-- distinct_titles: 138
-- distinct_types: 11-12 (standardized)
-- null_projects: 0-2 (after cleanup)
-- null_owner: depends on Phase 4.2 decision
-- null_confidence: 2
-- valid_confidence: 136+
-- null_examples: 5-7


-- Show final knowledge_type distribution
SELECT 
  knowledge_type,
  COUNT(*) as count,
  ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM claude.knowledge), 1) as pct
FROM claude.knowledge
GROUP BY knowledge_type
ORDER BY COUNT(*) DESC;

-- Expected: All 11-12 core types, no outliers


-- Data quality score calculation
WITH quality_metrics AS (
  SELECT 
    COUNT(*) as total,
    COUNT(DISTINCT title) as unique_titles,
    ROUND(100.0 * COUNT(DISTINCT title) / COUNT(*), 2) as uniqueness_pct,
    COUNT(CASE WHEN knowledge_type IS NOT NULL THEN 1 END) as with_type,
    COUNT(CASE WHEN applies_to_projects IS NOT NULL 
               AND array_length(applies_to_projects, 1) > 0 THEN 1 END) as with_scope,
    COUNT(CASE WHEN confidence_level BETWEEN 1 AND 10 THEN 1 END) as valid_confidence,
    COUNT(CASE WHEN code_example IS NOT NULL 
               AND TRIM(code_example) != '' THEN 1 END) as with_examples
  FROM claude.knowledge
)
SELECT 
  total,
  unique_titles,
  uniqueness_pct,
  ROUND(100.0 * with_type / total, 2) as type_coverage_pct,
  ROUND(100.0 * with_scope / total, 2) as scope_coverage_pct,
  ROUND(100.0 * valid_confidence / total, 2) as confidence_validity_pct,
  ROUND(100.0 * with_examples / total, 2) as example_coverage_pct,
  ROUND((100.0 * with_type / total + 100.0 * with_scope / total + 
         100.0 * valid_confidence / total + 100.0 * with_examples / total) / 4, 1) as overall_quality_score
FROM quality_metrics;

-- Expected: overall_quality_score should be 92+ (up from 78)


-- Check for any remaining issues
SELECT 'Case sensitivity violations' as issue, 
       COUNT(*) as count
FROM claude.knowledge
WHERE knowledge_type != LOWER(knowledge_type)
UNION ALL
SELECT 'Invalid confidence levels',
       COUNT(*) 
FROM claude.knowledge
WHERE confidence_level IS NOT NULL 
  AND (confidence_level < 1 OR confidence_level > 10)
UNION ALL
SELECT 'Non-standard types',
       COUNT(*)
FROM claude.knowledge
WHERE knowledge_type NOT IN (
  'pattern', 'gotcha', 'bug-fix', 'architecture', 'technique',
  'best-practice', 'troubleshooting', 'process', 'configuration',
  'mcp-tool', 'mcp-server'
)
UNION ALL
SELECT 'Duplicate titles',
       COUNT(*) as count
FROM (
  SELECT title FROM claude.knowledge
  GROUP BY title
  HAVING COUNT(*) > 1
) t;

-- Expected: All counts should be 0


-- ============================================================================
-- EXECUTION CHECKLIST
-- ============================================================================
-- [ ] Backup database before starting
-- [ ] Run Phase 1 scripts in order (1.1, 1.2, 1.3, 1.4)
-- [ ] Run Phase 2 scripts in order (2.1, 2.2)
-- [ ] Run Phase 3 scripts in order (3.1, 3.2, 3.3 optional)
-- [ ] Run Phase 4 scripts in order (4.1, 4.2)
-- [ ] Run verification queries
-- [ ] Verify overall_quality_score is 92+
-- [ ] Verify no issues remain in final issue check
-- [ ] Update any application code/documentation that references removed types
-- ============================================================================
