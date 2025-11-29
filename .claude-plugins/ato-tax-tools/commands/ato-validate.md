---
name: ato-validate
description: Validate tax calculations against ATO rules and edge cases
category: validation
priority: high
---

# ATO Tax Calculation Validator

Validates tax calculations and logic against Australian Taxation Office (ATO) rules and specifications.

## Functionality

This command performs comprehensive validation of tax calculations including:

### Core Validations
- **Income Threshold Checks**: Verify income falls within expected ATO tax brackets
- **Deduction Validation**: Ensure deductions comply with ATO allowable categories
- **Tax Offset Verification**: Check tax offsets are correctly applied and within limits
- **Medicare Levy Calculation**: Validate Medicare levy is calculated according to ATO rules

### Edge Case Testing
- Income thresholds at bracket boundaries
- Deductions at maximum allowable amounts
- Tax offset phase-out calculations
- Low-income earner offsets
- Senior Australian Pensioner Tax Offset (SAPTO) eligibility

### ATO Rules Verification
- Tax-free threshold application
- Dividend imputation credits
- Capital gains tax treatment
- Work-related expense deductions
- Contribution caps for superannuation

## Usage

The validator accepts tax calculation inputs and compares them against ATO specifications.

### Input Format
- Gross income
- Deductions breakdown
- Applicable tax offsets
- Special circumstances (e.g., pensioner status)

### Output
- ✅ Validation passed with calculations verified
- ⚠️ Warnings for edge cases or unusual patterns
- ❌ Errors with specific ATO rule violations
- Detailed explanation of any discrepancies

## Common Validations

| Scenario | Validation |
|----------|-----------|
| Income below tax-free threshold | No tax payable |
| Income at bracket boundary | Correct marginal rate applied |
| Deduction above limit | Flag as non-compliant |
| Tax offset above threshold | Phase-out correctly applied |

## Related Commands
- `/ato-test-scenarios` - Generate test cases
- `/ato-compliance-check` - Full compliance audit
