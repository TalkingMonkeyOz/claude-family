---
name: ato-compliance-check
description: Verify tax calculations and forms meet ATO specifications and compliance standards
category: compliance
priority: critical
---

# ATO Compliance Checker

Comprehensive compliance verification tool that ensures all tax calculations, forms, and data meet ATO specifications and reporting standards.

## Functionality

Performs systematic compliance audits across multiple dimensions of tax compliance.

### Data Format Validation
- **Numeric Precision**: Amounts rounded to cents correctly
- **Data Types**: Income, deductions, offsets use correct format
- **Field Population**: Required fields are complete and non-empty
- **Date Formats**: All dates conform to ATO standards (DD/MM/YYYY)
- **Character Encoding**: Text fields use valid character sets

### Tax Form Compliance
- **Tax Return Fields**: All mandatory fields populated
- **Schedules**: Supplementary schedules match main return
- **Attachments**: Required supporting documents referenced
- **Cross-References**: Line item consistency across forms
- **Electronic Format**: eFiling XML/JSON compliance

### Calculation Rules Compliance

#### Income Recognition
- ✓ Correct income categorization (salary, capital gains, etc.)
- ✓ Proper treatment of exempt income
- ✓ Correct foreign income inclusion
- ✓ CGT asset identification and treatment

#### Deduction Rules
- ✓ Only allowable deductions claimed
- ✓ Work-related expenses within limits
- ✓ Apportionment of mixed-purpose expenses
- ✓ Substantiation requirements met

#### Tax Offset Application
- ✓ Eligibility verification for each offset
- ✓ Correct calculation of offset amount
- ✓ Phase-out rules properly applied
- ✓ Non-refundable offset limits respected

### ATO Rule Verification

```
Compliance Areas Checked:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Tax Bracket Application         [✅ PASS]
2. Medicare Levy Calculation       [✅ PASS]
3. Tax-Free Threshold Rules        [✅ PASS]
4. Deduction Substantiation        [⚠️  WARNING]
5. Offset Eligibility              [✅ PASS]
6. CGT Discount Application        [✅ PASS]
7. Superannuation Contributions    [✅ PASS]
8. Foreign Income Disclosure       [✅ PASS]
9. Division 7A Compliance          [❌ FAIL]
10. Transfer Pricing Rules         [✅ PASS]
```

### Compliance Report Levels

#### Level 1: Critical Issues
- Tax calculation errors
- Mandatory form fields missing
- Incorrect tax treatment
- Non-compliance with filing requirements

#### Level 2: Warnings
- Deductions lacking documentation
- Unusual deduction patterns
- Edge cases requiring explanation
- Potential audit triggers

#### Level 3: Information
- Compliance confirmations
- Best practice suggestions
- Available optimization opportunities

### Common Compliance Checks

| Check | Description | Impact |
|-------|-------------|--------|
| Tax Bracket Alignment | Income correctly placed in ATO bracket | High |
| Deduction Limits | Deductions within ATO maximum | High |
| Offset Eligibility | All claimed offsets are eligible | Critical |
| Form Completeness | All required fields completed | Critical |
| Data Validation | All data formats correct | High |
| Period Alignment | Income/deductions match FY period | High |
| Documentation | Substantiation available for claims | Medium |

### Output Format

The compliance checker provides:

1. **Executive Summary**: Overall compliance status
2. **Detailed Findings**: Issue-by-issue breakdown
3. **Risk Assessment**: Audit risk analysis
4. **Remediation**: Steps to resolve non-compliance
5. **Certification**: Compliance status for filing

## Integration Points

- Works with `/ato-validate` for calculation verification
- Feeds results to `/ato-test-scenarios` for scenario testing
- Supports both individual and corporate tax compliance
- Compatible with ATO e-filing requirements

## Related Commands
- `/ato-validate` - Detailed calculation validation
- `/ato-test-scenarios` - Test scenario generation and execution
