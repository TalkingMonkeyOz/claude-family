# NEXT SESSION: Start Here - Tax Pack Analysis Phase 1

**Session Status:** ✅ PILOT COMPLETE - Ready to begin Phase 1
**Date:** 2025-10-19
**Previous Session ID:** 73d8efb0-d94b-4a56-a0e2-8b85f073bd12
**Methodology Knowledge ID:** 52f668ca-eec1-4f0d-a2b9-273519721c9d

---

## ⚡ QUICK START (5 commands)

```bash
# 1. Load startup context
python C:\claude\shared\scripts\load_claude_startup_context.py

# 2. Query pilot results
mcp__postgres__execute_sql("SELECT section_code, section_name, analysis_status FROM tax_calculator.section_analysis_master WHERE analysis_status = 'complete' ORDER BY section_code;")

# 3. Load methodology
mcp__postgres__execute_sql("SELECT title, description, code_example FROM claude_family.shared_knowledge WHERE knowledge_id = '52f668ca-eec1-4f0d-a2b9-273519721c9d';")

# 4. Read pilot completion report
Read C:\claude\claude-console-01\workspace\PILOT_STUDY_COMPLETE_2025-10-19.md

# 5. Begin Phase 1 Section 2
# Extract Section 2 text and start analysis
```

---

## 🎯 WHAT WAS COMPLETED

### Pilot Study Results (3 sections in 45 minutes)

| Section | Name | Complexity | Records Created | Status |
|---------|------|------------|-----------------|--------|
| 1 | Salary or wages | 2/5 | Entry:1, Data:6, Map:4, Rel:3, Special:4 | ✅ Complete |
| D1 | Work-related car expenses | 4/5 | Entry:1, Data:9, Map:4, Rel:5, Special:10 | ✅ Complete |
| T1 | Seniors and pensioners tax offset | 4/5 | Entry:2, Data:11, Map:3, Rel:2, Special:11 | ✅ Complete |

**Total:** 80 database records created (4 entries, 26 data requirements, 11 mappings, 10 relationships, 25 special cases)

**Methodology:** ✅ Validated as systematic, repeatable, zero hallucination
**Time Estimate Revised:** 15-20 hours for full 42 sections (was 60-80 hours)

---

## 📋 NEXT TASK: Phase 1 - Income Sections (2-14)

### Income Sections to Analyze (13 sections, ~4 hours)

**Priority Order:**
1. **Section 2** - Allowances, earnings, tips, directors fees etc
2. **Section 3** - Employer lump sum payments
3. **Section 4** - Employment termination payments (ETP)
4. **Section 5** - Australian Government allowances and payments
5. **Section 6** - Australian Government pensions and allowances
6. **Section 7** - Australian superannuation income stream
7. **Section 8** - Attributed personal services income
8. **Section 9** - Gross interest
9. **Section 10** - Dividends
10. **Section 11** - Employee share schemes (ESS)
11. **Section 12** - Partnership and trust distributions
12. **Section 13** - Net capital gain or loss
13. **Section 14** - Foreign source income and foreign assets or property

**Estimated Time:** 13 sections × 20 min avg = 4.3 hours

---

## 🔄 PROVEN METHODOLOGY (5 Steps)

### Step 1: Extract Section Text
```bash
# Find section boundaries
grep -n "^2 " "C:\Projects\ATO-Tax-Agent\data\txt\individual_tax_return_2025_instructions.txt"
grep -n "^3 " "C:\Projects\ATO-Tax-Agent\data\txt\individual_tax_return_2025_instructions.txt"

# Read specific lines
Read file_path offset:XXX limit:150
```

### Step 2: Document Entry Condition(s)
```sql
INSERT INTO tax_calculator.section_entry_conditions
(section_code, condition_question, condition_type, condition_logic, skip_if_no, notes)
VALUES
('2',
 'Did you receive...?',
 'has_income',
 '{"requirements": [...]}'::jsonb,
 true,
 'Extracted from line XXX. If NO, skip to Section X.');
```

### Step 3: Document Data Requirements
```sql
INSERT INTO tax_calculator.section_data_requirements
(section_code, field_name, field_label, field_description, data_type,
 is_required, is_multi_entry, max_entries,
 data_source_type, data_source_document_name, customer_collection_method,
 help_text, validation_rules, display_order, extracted_from_line, extracted_from_pdf)
VALUES
('2', 'field_name', 'Field Label', 'Description', 'text', true, false, null,
 'payment_summary', 'PAYG Payment Summary', 'upload_doc',
 'Help text for user', '{"min": 0, "max": 999999}'::jsonb, 1, XXX, 'individual_tax_return_2025_instructions.txt');
```

### Step 4: Map to Form Boxes
```sql
INSERT INTO tax_calculator.section_form_mappings
(section_code, field_name, form_box_number, form_box_label,
 mapping_type, calculation_formula, aggregation_function, notes)
VALUES
('2', 'field_name', '2', 'Box label', 'direct_copy', null, 'SUM', 'Extracted from line XXX');
```

### Step 5: Document Relationships and Special Cases
```sql
-- Create placeholders for referenced sections first
INSERT INTO tax_calculator.section_analysis_master
(section_code, section_name, section_category, tax_year, analysis_status)
VALUES ('X', 'Section name', 'category', '2024-25', 'not_started')
ON CONFLICT (section_code) DO NOTHING;

-- Relationships
INSERT INTO tax_calculator.section_relationships
(from_section, to_section, relationship_type, condition_description, is_mandatory, notes, extracted_from_line)
VALUES ('2', 'X', 'triggers', 'If condition met, go to X', false, 'Notes', XXX);

-- Special cases
INSERT INTO tax_calculator.section_special_cases
(section_code, case_name, case_description, detection_rule, handling_instructions, extracted_from_line)
VALUES ('2', 'Special Case Name', 'Description', '{"rule": "value"}'::jsonb, 'Instructions', XXX);
```

### Step 6: Mark Complete
```sql
UPDATE tax_calculator.section_analysis_master
SET analysis_status = 'complete',
    analysis_date = NOW(),
    updated_at = NOW(),
    notes = 'Analysis complete. Documented: X entries, Y data reqs, Z mappings, etc.'
WHERE section_code = '2';
```

---

## 📊 DATABASE VERIFICATION QUERIES

### Check Progress
```sql
SELECT
    section_code,
    section_name,
    complexity_rating,
    analysis_status,
    TO_CHAR(analysis_date, 'YYYY-MM-DD HH24:MI') as completed
FROM tax_calculator.section_analysis_master
WHERE analysis_status = 'complete'
ORDER BY section_code;
```

### Count Findings for a Section
```sql
SELECT
    'Section X Analysis' as status,
    (SELECT COUNT(*) FROM tax_calculator.section_entry_conditions WHERE section_code = 'X') as entry_conditions,
    (SELECT COUNT(*) FROM tax_calculator.section_data_requirements WHERE section_code = 'X') as data_requirements,
    (SELECT COUNT(*) FROM tax_calculator.section_form_mappings WHERE section_code = 'X') as form_mappings,
    (SELECT COUNT(*) FROM tax_calculator.section_relationships WHERE from_section = 'X') as relationships,
    (SELECT COUNT(*) FROM tax_calculator.section_special_cases WHERE section_code = 'X') as special_cases;
```

---

## ⚠️ KEY REMINDERS

**Zero Hallucination:**
- ✅ Every finding MUST include `extracted_from_line` number
- ✅ Copy exact text from PDF for questions and labels
- ✅ No assumptions - only documented facts
- ✅ Verify calculations match PDF formulas exactly

**Foreign Key Safety:**
- ✅ Create placeholder records for referenced sections BEFORE inserting relationships
- ✅ Use `ON CONFLICT (section_code) DO NOTHING` to avoid duplicates

**JSONB Validation Rules:**
- ✅ Use for complex logic: `{"min": 0, "max": 5000, "method_required": "cents_per_km"}`
- ✅ Allowed values: `{"allowed_values": ["A", "B", "C"]}`
- ✅ Conditional requirements: `{"required_if": "has_spouse"}`

**Multi-Entry Sections:**
- ✅ Set `is_multi_entry = true` and `max_entries` in data_requirements
- ✅ Document aggregation in form_mappings (SUM, CONCAT, etc.)

**Method-Dependent Fields:**
- ✅ Store in validation_rules: `{"method_required": "logbook"}`
- ✅ Document both methods if applicable (like D1 cents vs logbook)

**ATO-Calculated Values:**
- ✅ Document what customer ENTERS vs what ATO CALCULATES
- ✅ Use mapping_type = 'component' for ATO-calculated amounts

---

## 🎓 LESSONS FROM PILOT

**What Worked:**
1. Line references critical for verification
2. JSONB validation_rules handle complex conditional logic
3. Complexity ratings predict time accurately (2→15min, 4→25min)
4. Multi-condition eligibility: use multiple entry_condition rows

**What to Watch:**
1. Create placeholders for ALL referenced sections
2. Don't assume - read actual PDF text
3. Record BOTH what user enters AND what ATO calculates
4. Special cases often outnumber data requirements (T1: 11 special cases)

**Time Savers:**
1. grep for section boundaries first
2. Read exact line ranges (don't read entire file)
3. Copy-paste exact text from PDF for questions
4. Use previous section as template for SQL structure

---

## 📁 FILE LOCATIONS

**Work Directory:**
- `C:\claude\claude-console-01\workspace\`

**Source PDFs (text format):**
- `C:\Projects\ATO-Tax-Agent\data\txt\individual_tax_return_2025_instructions.txt` (8,800 lines)
- `C:\Projects\ATO-Tax-Agent\data\txt\individual_tax_return_2025_supporting_information.txt` (1,252 lines)
- `C:\Projects\ATO-Tax-Agent\data\txt\Tax_return_for_individuals_2025.txt` (626 lines)
- `C:\Projects\ATO-Tax-Agent\data\txt\website Individual supplementary tax return and instructions 2025.txt` (6,136 lines)

**Reports:**
- `PILOT_STUDY_COMPLETE_2025-10-19.md` - Full pilot summary
- `SESSION_RESUME_2025-10-19.md` - Original session resume
- `TAX_PACK_ANALYSIS_PROJECT_PLAN.md` - Complete project plan
- `NEXT_SESSION_START_HERE.md` - This file

**Database:**
- PostgreSQL: `ai_company_foundation`
- Schema: `tax_calculator`
- 7 analysis tables created in migration 006

---

## ✅ PRE-SESSION CHECKLIST

Before starting Phase 1, verify:

- [ ] PostgreSQL database accessible
- [ ] 3 pilot sections marked 'complete' in section_analysis_master
- [ ] Methodology loaded from shared_knowledge
- [ ] Source PDF text files accessible
- [ ] Workspace directory ready: `C:\claude\claude-console-01\workspace\`

**Verification SQL:**
```sql
-- Should return 3 rows (sections 1, D1, T1)
SELECT COUNT(*) as pilot_complete
FROM tax_calculator.section_analysis_master
WHERE analysis_status = 'complete';

-- Should return 1 row (methodology pattern)
SELECT COUNT(*) as methodology_stored
FROM claude_family.shared_knowledge
WHERE knowledge_id = '52f668ca-eec1-4f0d-a2b9-273519721c9d';
```

---

## 🚀 BEGIN PHASE 1: Section 2

**Command:**
```bash
grep -n "^2 " "C:\Projects\ATO-Tax-Agent\data\txt\individual_tax_return_2025_instructions.txt" | head -5
```

**Expected:** Find Section 2 line numbers, then Read and analyze following proven 5-step methodology.

**Estimated Time:** 15-20 minutes (Section 2 likely complexity 2-3)

---

**STATUS:** ✅ Ready to continue
**NEXT ACTION:** Begin Section 2 analysis
**METHODOLOGY:** Proven and stored (knowledge_id: 52f668ca-eec1-4f0d-a2b9-273519721c9d)
**USER APPROVAL:** Proceed with Option 1 (full 42-section analysis)

---

*Quick start guide created: 2025-10-19 23:48*
*Previous session: 73d8efb0-d94b-4a56-a0e2-8b85f073bd12*
*Analyst: claude-code-console-001*
