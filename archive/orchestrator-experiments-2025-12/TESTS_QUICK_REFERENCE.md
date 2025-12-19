# ATO Tax Agent Test Suite - Quick Reference

## Test Files at a Glance

### 📊 test_calculation_service.py
**Purpose**: Main tax calculation engine (workflow, integration, overall liability)

| Scenario | Input | Expected Output | Test Name |
|----------|-------|-----------------|-----------|
| Low income (below threshold) | $15,000 | $0 tax | `test_low_income_no_tax` |
| Middle income | $50,000 | $5,337 net tax | `test_middle_income` |
| High income | $90,000 | $19,085 with levy | `test_high_income` |
| Very high income | $200,000 | $58,365 with levy | `test_very_high_income` |
| With deductions | $80,000 - $5,000 deductions | Adjusted correctly | `test_with_deductions` |
| Multiple offsets | $40,000 + LITO+LDCO | Aggregated correctly | `test_multiple_offsets` |
| LITO phase-out | $66,667 | LITO reduces | `test_lito_phase_out` |
| Zero income | $0 | $0 tax | `test_zero_income` |
| Offsets exceed tax | $30,000 | $0 net tax | `test_zero_tax_with_offsets` |

---

### 💰 test_income_tax_service.py
**Purpose**: Income tax bracket calculations (progressive taxation, rates, boundaries)

| Bracket | Income Range | Rate | Marginal Rate |
|---------|-------------|------|---------------|
| Tax-free | $0-$18,200 | 0% | 0% |
| 1st | $18,201-$45,000 | 19% | 19% |
| 2nd | $45,001-$120,000 | 32.5% | 32.5% |
| 3rd | $120,001-$180,000 | 37% | 37% |
| Top | $180,000+ | 45% | 45% |

| Test Scenario | Income | Expected Tax | Test Name |
|---------------|--------|--------------|-----------|
| Below threshold | $15,000 | $0 | `test_below_threshold` |
| First bracket | $30,000 | $2,242 | `test_first_bracket` |
| Second bracket | $75,000 | $18,300 | `test_second_bracket` |
| Third bracket | $150,000 | $42,405 | `test_third_bracket` |
| Top bracket | $250,000 | $85,205 | `test_top_bracket` |
| Boundary at $45k | $45,000 | $5,092 | `test_boundary_45k` |
| Boundary at $120k | $120,000 | $32,925 | `test_boundary_120k` |
| Boundary at $180k | $180,000 | $53,705 | `test_boundary_180k` |

---

### 🎁 test_tax_offset_service.py
**Purpose**: Tax offset calculations (LITO, SAPTO, LDCO eligibility, aggregation, phase-out)

| Offset | Max Amount | Eligibility | Phase-out |
|--------|-----------|-------------|-----------|
| LITO | $705 | All residents | $66,667-$90,000 |
| SAPTO | $1,445-$1,602 | Age 65+ | After $56,548 |
| LDCO | $1,657/dependent | Income <$80,000 | Hard cutoff at $80,000 |

| Scenario | Income | Dependents | Age/Status | Expected Offsets | Test Name |
|----------|--------|-----------|-----------|------------------|-----------|
| Low income | $30,000 | 0 | 35 | LITO $705 | `test_lito_full` |
| LITO phase-out | $78,333 | 0 | 35 | LITO $589 | `test_lito_phase_out` |
| Senior full | $20,000 | 0 | 70 | SAPTO $1,445 | `test_sapto_full` |
| Senior tax-free | $10,000 | 0 | 70, tax-free | SAPTO $1,602 | `test_sapto_tax_free` |
| Family | $40,000 | 1 | 35 | LITO $705 + LDCO $1,657 | `test_combined_offsets` |
| High income | $150,000 | 0 | 35 | $0 | `test_no_offsets` |
| At LDCO cap | $79,999 | 2 | 35 | LDCO $3,314 | `test_ldco_eligible` |
| Above LDCO cap | $80,000 | 2 | 35 | $0 | `test_ldco_ineligible` |

---

### 📋 test_layer1_service.py
**Purpose**: Income aggregation, gross income, Medicare thresholds, assessable income

| Taxpayer Type | Gross Income | Sources | Medicare Threshold | Exceeds |
|---------------|-------------|---------|-------------------|---------|
| Single | $50,000 | Salary | $21,845 | Yes |
| Single low | $15,000 | Wages | $21,845 | No |
| Couple | $85,000 | Salary+Investment | $43,690 | Yes |
| Family (2 kids) | $90,000 | Multiple | $57,895 | Yes |
| Non-resident | $60,000 | Salary | Different rules | N/A |

| Scenario | Gross | Sources | Assessable | Medicare Level | Test Name |
|----------|-------|---------|-----------|-----------------|-----------|
| Single source | $50,000 | Salary | $50,000 | Below threshold | `test_single_source` |
| Multiple sources | $75,000 | Salary+Interest+Dividends | $75,000 | Above threshold | `test_multiple_sources` |
| With non-assessable | $60,000 | Salary+Reimbursement | $60,000 | Above threshold | `test_non_assessable` |
| Business loss | $40,000 | Salary-$10k loss | $40,000 | Above threshold | `test_business_loss` |
| Family | $90,000 | Multiple | $90,000 | Above family threshold | `test_family_scenario` |
| At threshold | $21,845 | Salary | $21,845 | At threshold (No) | `test_threshold_boundary` |
| Just above | $21,846 | Salary | $21,846 | Just above (Yes) | `test_above_threshold` |

---

## Key ATO 2024-25 Values to Remember

### Tax Thresholds
- **Tax-free threshold**: $18,200
- **LITO full amount**: Up to $66,667
- **LITO phase-out**: $66,667-$90,000 ($0.01 per $1)
- **SAPTO phase-out**: After $56,548

### Medicare Levy Thresholds
- **Single**: $21,845
- **Couple**: $43,690
- **Family base**: $51,885
- **Per dependent child**: +$3,005

### Offset Amounts
- **LITO**: $705 max
- **SAPTO (tax-free person)**: $1,602
- **SAPTO (other)**: $1,445
- **LDCO per dependent**: $1,657

### Tax Rates
- 19% on $18,201-$45,000
- 32.5% on $45,001-$120,000
- 37% on $120,001-$180,000
- 45% on $180,000+
- Medicare levy: 2% (standard rate)

---

## Running Tests

### All CORE Tests
```bash
pytest test_*_service.py -v
```

### Single Test File
```bash
pytest test_calculation_service.py -v
pytest test_income_tax_service.py -v
pytest test_tax_offset_service.py -v
pytest test_layer1_service.py -v
```

### Specific Test Class
```bash
pytest test_calculation_service.py::TestCalculationServiceNormalCases -v
pytest test_income_tax_service.py::TestIncomeTaxServiceEdgeCases -v
```

### Specific Test Case
```bash
pytest test_calculation_service.py::TestCalculationServiceNormalCases::test_middle_income_single_bracket -v
```

### With Coverage
```bash
pytest test_*_service.py --cov --cov-report=html
```

### Show Print Statements
```bash
pytest test_calculation_service.py -v -s
```

### Stop on First Failure
```bash
pytest test_*_service.py -x
```

---

## Test Data Quick Reference

### Typical Taxpayer Scenarios

**Young Professional**
- Age: 25-35
- Income: $35,000-$65,000
- Sources: Single salary
- Offsets: LITO only
- Medicare: Yes (above threshold)

**Middle-Income Earner**
- Age: 35-55
- Income: $65,000-$120,000
- Sources: Salary + investments
- Offsets: LITO (if eligible)
- Medicare: Yes
- Typical tax: $12,000-$32,000

**High-Income Earner**
- Age: 40-60
- Income: $120,000+
- Sources: Multiple sources
- Offsets: None
- Medicare: Yes
- Typical tax: $32,000+

**Senior Pensioner**
- Age: 65+
- Income: $20,000-$50,000
- Sources: Pension + investments
- Offsets: SAPTO ($1,445+)
- Medicare: Varies
- Typical tax: Minimal to $8,000

**Young Family**
- Ages: 30-40
- Primary income: $60,000-$80,000
- Dependents: 1-3
- Sources: Salary + spouse income
- Offsets: LITO + LDCO
- Medicare: Yes, family threshold
- Typical tax: $8,000-$15,000

---

## Common Edge Cases

### Threshold Boundaries
- Exactly at tax-free threshold: $18,200 → $0 tax
- $1 above: $18,201 → $0.19 tax
- At bracket boundary: $45,000 → last dollar at 19%
- Just above bracket: $45,001 → $0.325 tax on new dollar

### Offset Phase-out
- LITO at phase-out start: $66,667 → $705 (full)
- LITO mid-phase-out: $78,333 → $589
- LITO at elimination: $90,000 → $0
- SAPTO phase-out: $56,548+ → linear reduction

### Medicare Levy
- At single threshold: $21,845 → No levy
- Just above: $21,846 → 2% of $1 = $0.02 levy
- At couple threshold: $43,690 → No levy
- Family with 2 kids: Threshold is $57,895

### Income Reconciliation
- Zero income: $0 tax, possible warnings
- Negative income: Rare, usually business loss
- Multiple sources: Sum correctly before tax
- Non-assessable: Exclude from tax calculation

---

## Debugging Tests

### Common Issues

**Test fails on bracket calculation**
- Check: 2024-25 brackets are correct
- Verify: $45k, $120k, $180k thresholds
- Confirm: Rates are 19%, 32.5%, 37%, 45%

**Offset calculation wrong**
- Check: Correct offset max amounts
- Verify: Phase-out rates and ranges
- Confirm: Income thresholds for eligibility

**Medicare levy incorrect**
- Check: $21,845 single threshold
- Verify: $43,690 couple threshold
- Confirm: 2% rate applied correctly

**Precision errors**
- Use: Decimal class (not float)
- Check: Rounding behavior
- Verify: Two decimal place output

---

## Integration Checklist

- [ ] Copy test files to `backend/tests/`
- [ ] Replace mock imports with real services
- [ ] Install pytest dependencies
- [ ] Run full test suite
- [ ] Generate coverage report
- [ ] Verify all 47+ tests pass
- [ ] Check coverage > 90%
- [ ] Update CI/CD pipeline
- [ ] Document any test failures
- [ ] Refine services based on results

---

## Test Suite Statistics

| Metric | Value |
|--------|-------|
| Total Test Files | 4 |
| Total Test Classes | 33 |
| Total Test Cases | 47+ |
| Lines of Code | ~2,500+ |
| Coverage Focus | Core calculation services |
| ATO Rules Version | 2024-25 |
| Realistic Scenarios | 30+ |
| Edge Cases | 25+ |
| Test Framework | pytest |

---

## Support & Troubleshooting

### Test won't import
- Ensure service files exist at expected location
- Check Python path includes backend module
- Verify mock implementations if using

### Test fails but shouldn't
- Check ATO 2024-25 rules are current
- Verify test data is accurate
- Compare with ATO official calculations
- Review test comments for assumptions

### Need to add new test
- Follow existing test class structure
- Use realistic Australian scenarios
- Include docstring explaining scenario
- Add to appropriate test class

---

**Last Updated**: 2025-12-08
**ATO Year**: 2024-25
**Status**: Ready for Integration
