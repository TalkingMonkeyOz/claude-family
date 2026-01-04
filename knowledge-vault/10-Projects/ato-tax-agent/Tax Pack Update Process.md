---
projects:
- ato-tax-agent
tags:
- procedure
- annual-update
- ato
synced: false
---

# Tax Pack Update Process

**Purpose**: Annual process for updating to new ATO tax pack
**Timing**: Each July when new tax pack released

---

## Update Phases

### Phase 1: Download (July)
- Individual Tax Return Instructions PDF
- Individual Tax Return Form PDF
- Supplementary Section Instructions PDF
- Tax Tables/Rates PDF

### Phase 2: Database Updates
Update these tables:
- `section_analysis_master` - New sections, tax_year
- `section_data_requirements` - Field changes
- `tax_return_binary_gates` - Updated questions
- `tax_return_instructional_content` - Re-embed content

### Phase 3: Code Updates
- `calculation_service.py` - Tax brackets, rates
- `tax_rates.json` - Rate tables
- `thresholds.json` - Threshold values
- `section_explanations.json` - Help content

### Phase 4: Testing
- Calculation tests with new rates
- All sections render correctly
- PDF generation works
- E2E tests pass

---

## Key Values to Check Annually

- Tax brackets and rates
- Medicare levy threshold
- Low income tax offset (LITO)
- Super contribution caps
- Private health insurance thresholds

---

## Version Control

1. Branch: `feature/tax-year-YYYY-YY`
2. Update all content
3. Full test suite
4. PR with change summary
5. Tag previous year release

---

**Version**: 1.0
**Created**: 2026-01-04
**Location**: knowledge-vault/10-Projects/ato-tax-agent/
