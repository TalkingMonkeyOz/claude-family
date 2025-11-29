---
name: ato-test-scenarios
description: Generate and run test scenarios through the tax calculation engine
category: testing
priority: high
---

# ATO Test Scenario Generator

Generates realistic test scenarios and runs them through the tax calculation engine to verify accuracy and compliance.

## Functionality

This command creates comprehensive test data and executes validation against expected outcomes.

### Test Scenario Categories

#### Individual Income Earners
- Salary only (straightforward case)
- Multiple income sources (salary + rental income)
- Investment income with tax-deferred accounts
- Self-employment income

#### High-Income Earners
- Income above Medicare levy surcharge threshold
- Dividend income with franking credits
- Capital gains with CGT discount
- Superannuation contribution caps

#### Special Circumstances
- Low-income earner tax offset eligibility
- Pensioner/retiree status
- Senior Australian Pensioner Tax Offset (SAPTO)
- Dependent spouse income splitting
- Parental leave pay

#### Edge Cases
- Income at tax bracket boundaries (e.g., $45,000, $120,000)
- Deductions at maximum allowable amounts
- Tax offset phase-out ranges
- Loss carry-forward scenarios

### Test Execution

Each test scenario includes:
1. **Input Data**: Complete financial picture
2. **Expected Results**: Correct tax liability and offsets
3. **Actual Results**: Calculation engine output
4. **Comparison**: Expected vs actual with variance analysis
5. **Report**: Pass/fail with detailed breakdown

### Output Report

```
Test Scenario: Salary + Rental Income
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Input:
  Salary:              $75,000
  Rental Income:       $12,000
  Rental Deductions:   $8,000

Expected Results:
  Taxable Income:      $79,000
  Tax Payable:         $17,442
  Medicare Levy:       $1,580

Actual Results:
  Taxable Income:      $79,000
  Tax Payable:         $17,442
  Medicare Levy:       $1,580

Status: ✅ PASSED (All values match)
```

## Predefined Test Suites

### Basic Suite
- Single income earner
- Family with dependent children
- Retiree with only super income

### Intermediate Suite
- Multiple income sources
- Investment portfolio
- Home office deductions

### Advanced Suite
- Complex capital gains
- Superannuation strategy
- Income splitting scenarios

### Compliance Suite
- ATO audit scenarios
- Common dispute cases
- Edge cases from recent ATO guidance

## Related Commands
- `/ato-validate` - Single calculation validation
- `/ato-compliance-check` - Full system compliance audit
