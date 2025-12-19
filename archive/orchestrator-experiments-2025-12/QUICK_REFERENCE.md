# ESS Service - Quick Reference Card

## 🎯 30-Second Usage

```python
from ess_service import ESSStatementBuilder, ESSService, SchemeType
from datetime import date
from decimal import Decimal

# Create statement
builder = ESSStatementBuilder("STMT-001", "TechCorp", "12345678901")

# Add discount share: Paid $5,000, Worth $7,500 → $2,500 discount
builder.add_discount_share(
    "SHARE-001", "Salary Sacrifice Plan",
    date(2023, 7, 15),
    Decimal("5000.00"),    # Amount paid
    Decimal("7500.00"),    # Market value
    SchemeType.SALARY_SACRIFICE,  # Eligible for $1,000 exemption
    has_rrof=True  # Has real risk of forfeiture
)

# Calculate
service = ESSService()
result = service.format_for_tax_return(builder.build())

# Result
print(result['summary']['total_income'])  # $1,500.00 (after exemption)
```

---

## 📋 Core Methods

### 1. Calculate Discount with Exemption
```python
discount = service.calculate_taxable_discount(interest)
# Returns: TaxableDiscount
#   raw_discount: Decimal (MV - amount paid)
#   exemption_applied: Decimal (usually $1,000)
#   taxable_discount: Decimal (amount in income)
#   is_eligible_for_exemption: bool
#   exemption_notes: str (explanation)
```

### 2. Check Deferral Eligibility
```python
deferral = service.check_deferred_taxing_point_eligibility(interest)
# Returns: DeferralEligibility
#   is_eligible: bool
#   eligible_until_date: date (15 years from acquisition)
#   notes: str (explanation)
```

### 3. Process Option Exercise
```python
result = service.calculate_option_exercise(
    interest=option,
    option_details=OptionDetails(...),
    exercise_scenario=OptionExerciseScenario(...)
)
# Returns: Dict
#   gain_on_exercise: Decimal
#   cost_base: Decimal (for CGT)
#   deferral_applied: bool
```

### 4. Calculate Cost Base for CGT
```python
cost_base = service.calculate_cgt_cost_base(
    interest,
    taxable_discount_info
)
# Returns: CGTCostBase
#   cost_base_amount: Decimal (total cost base)
#   components: Dict (breakdown)
```

### 5. Process Entire Statement
```python
results = service.process_statement(statement)
# Returns: Dict with all per-interest and summary results
```

### 6. Format for Tax Return
```python
tax_return = service.format_for_tax_return(statement)
# Returns: Dict formatted as Section 12 entry
```

---

## 🔧 Builder Pattern (Fluent API)

```python
builder = ESSStatementBuilder("STMT-ID", "Employer", "12345678901")

# Add discount share
builder.add_discount_share(
    interest_id="SHARE-001",
    plan_name="Plan name",
    acquisition_date=date(2023, 7, 15),
    amount_paid=Decimal("5000.00"),
    market_value=Decimal("7500.00"),
    scheme_type=SchemeType.SALARY_SACRIFICE,  # or SMALL_BUSINESS, GENERAL
    has_rrof=True  # Has real risk of forfeiture
)

# Add option
builder.add_option(
    interest_id="OPTION-001",
    plan_name="Option plan",
    acquisition_date=date(2022, 1, 1),
    exercise_price=Decimal("15.00"),
    number_of_shares=1000,
    scheme_type=SchemeType.GENERAL,
    has_rrof=True
)

# Build
statement = builder.build()
```

---

## 📊 Quick Reference Table

| Scenario | Calculation | Method |
|----------|---|---|
| Discount share | MV - Amount paid | `interest.raw_discount` |
| Taxable discount | Discount - exemption | `calculate_taxable_discount()` |
| Exemption eligible | Scheme type = SALARY_SACRIFICE, SMALL_BUSINESS | Auto-checked |
| Deferral eligible | RROF + ≥ 1-7-2009 + < 15 years | `check_deferred_taxing_point_eligibility()` |
| Option gain | (Shares × MV) - Exercise price | `calculate_option_exercise()` |
| Cost base | Amount paid + discount | `calculate_cgt_cost_base()` |
| Batch process | All interests | `process_statement()` |
| Tax return | Section 12 format | `format_for_tax_return()` |

---

## 🔑 Key Constants

```python
EXEMPTION_AMOUNT = Decimal("1000.00")           # s 83A-75
ACQUISITION_DATE_THRESHOLD = date(2009, 7, 1)  # Division 83A start
MAX_DEFERRAL_YEARS = 15                        # s 83A-35(1)(c)
```

---

## 🎓 Enums

### ESSType
- `DISCOUNT_SHARE` - Most common
- `OPTION` - Executive options
- `RIGHT` - Rights to shares
- `RESTRICTED_SHARE` - With conditions

### SchemeType
- `SALARY_SACRIFICE` - ✅ $1,000 exemption
- `SMALL_BUSINESS` - ✅ $1,000 exemption
- `EMPLOYER_CONTRIBUTION` - ✅ $1,000 exemption
- `GENERAL` - ❌ No exemption

### OptionExerciseType
- `STANDARD_EXERCISE` - Employee pays cash
- `CASHLESS_EXERCISE` - Via broker, no cash
- `CASHLESS_CASHOUT` - Immediate sale

---

## ✅ Validation

```python
from ess_service import ESSValidator

# Validate statement
errors = ESSValidator.validate_statement(statement)
if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ Valid")

# Validate single interest
errors = ESSValidator.validate_interest(interest)
```

---

## 📦 Data Classes

### ESSInterest (core)
```python
ESSInterest(
    interest_id: str,
    ess_type: ESSType,
    scheme_type: SchemeType,
    acquisition_date: date,
    amount_paid: Decimal,
    market_value_acquisition: Decimal,
    employer_name: str,
    plan_name: str,
    has_real_risk_forfeiture: bool = False
)
```

### ESSStatement (batch)
```python
ESSStatement(
    statement_id: str,
    employer_name: str,
    employer_abn: str,
    statement_date: date,
    tax_year: str,  # "2024-25"
    interests: List[ESSInterest] = []
)
```

---

## 💾 File Locations

```
ess_service.py              ← Main service (COPY THIS)
test_ess_service.py         ← Tests (copy to tests/)
ess_service_usage_guide.md  ← API docs (read first)
ESS_SERVICE_README.md       ← Complete guide
ESS_SERVICE_SUMMARY.md      ← Executive summary
ESS_SERVICE_INDEX.md        ← Navigation guide
ess_integration_examples.py ← Integration patterns
DELIVERABLES.md             ← Delivery checklist
QUICK_REFERENCE.md          ← This file
```

---

## 🚀 Quick Start

### Step 1: Copy File
```bash
cp ess_service.py backend/app/services/
```

### Step 2: Import
```python
from app.services.ess_service import (
    ESSStatementBuilder,
    ESSService,
    SchemeType
)
```

### Step 3: Use
```python
builder = ESSStatementBuilder("STMT-001", "TechCorp", "12345678901")
builder.add_discount_share(...)
service = ESSService()
result = service.format_for_tax_return(builder.build())
```

### Step 4: Verify
```bash
pytest test_ess_service.py -v --cov
# Expected: 40+ tests PASSED, 100% coverage
```

---

## 📝 Common Patterns

### Parse Employer JSON
```python
import json
data = json.loads(employer_json_string)
builder = ESSStatementBuilder(
    data["statement_id"],
    data["employer_name"],
    data["employer_abn"]
)
for interest in data["interests"]:
    builder.add_discount_share(...)
statement = builder.build()
```

### Calculate for Multiple Employers
```python
results = []
for statement in employer_statements:
    result = service.format_for_tax_return(statement)
    results.append(result)

total_income = sum(Decimal(r["summary"]["total_income"]) for r in results)
```

### Validate Before Processing
```python
errors = ESSValidator.validate_statement(statement)
if errors:
    raise ValueError(f"Invalid statement: {errors}")

result = service.process_statement(statement)
```

### Log for Audit
```python
from ess_integration_examples import ESSAuditLogger

logger = ESSAuditLogger(tfn="123456789")
logger.log_discount_calculation(
    "SHARE-001",
    Decimal("2500.00"),  # raw
    Decimal("1000.00"),  # exemption
    Decimal("1500.00")   # taxable
)
audit_json = logger.export_audit_trail()
```

---

## 🧪 Test Examples

```python
# Test discount with exemption
interest = ESSInterest(..., scheme_type=SchemeType.SALARY_SACRIFICE, ...)
result = service.calculate_taxable_discount(interest)
assert result.exemption_applied == Decimal("1000.00")

# Test deferral eligibility
deferral = service.check_deferred_taxing_point_eligibility(interest)
assert deferral.is_eligible == True

# Test option exercise
result = service.calculate_option_exercise(
    option, option_details, exercise_scenario
)
assert result["cost_base"] > 0
```

---

## ⚠️ Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `ValueError: Amount paid cannot be negative` | Negative amount_paid | Use positive Decimal |
| `ValueError: Real risk of forfeiture does not exist` | has_rrof=False | Set has_rrof=True |
| `ValueError: Discount calculation does not apply` | Wrong interest type | Use DISCOUNT_SHARE |
| `ValueError: Invalid 11-digit ABN` | Bad ABN format | Use 11-digit ABN |
| `KeyError: ESSType` | Wrong enum value | Use ESSType.DISCOUNT_SHARE |

---

## 📊 Example Output

```python
result['summary'] = {
    'total_raw_discount': Decimal('2500.00'),
    'total_exemption': Decimal('1000.00'),
    'total_taxable_discount': Decimal('1500.00'),
    'total_deferred': Decimal('1500.00'),
    'interests_with_deferred_taxing_point': 1
}

result['section'] = 12
result['income_type'] = 'Employee Share Scheme'
result['total_income'] = '1500.00'
result['total_exemptions'] = '1000.00'
```

---

## 🔍 Debugging

```python
# Check what you're calculating
print(interest.raw_discount)  # MV - amount paid
print(discount.taxable_discount)  # What's in income
print(deferral.is_eligible)  # Is deferred?
print(deferral.eligible_until_date)  # Until when?

# Validate before processing
errors = ESSValidator.validate_statement(statement)
print(f"Validation errors: {errors}")

# Process with details
results = service.process_statement(statement)
print(f"Summary: {results['summary']}")
print(f"Interests: {results['interests']}")
```

---

## 🎯 Tax Rules (Quick)

| Rule | What | Where |
|------|------|-------|
| Exemption | $1,000 for eligible schemes | s 83A-75 |
| Deferral | Earliest of 4 events | s 83A-35 |
| RROF | Required for deferral | s 83A-80 |
| Discount | MV - amount paid | Subdivision 83A |
| Cost base | Amount + discount | CGT rules |
| Start date | 1 July 2009 | Division 83A |
| Max years | 15 from acquisition | s 83A-35(1)(c) |

---

## 📞 Where to Find Things

| Need | File |
|------|------|
| How to use it | ess_service_usage_guide.md |
| All the details | ESS_SERVICE_README.md |
| Quick overview | ESS_SERVICE_SUMMARY.md |
| Which file to read | ESS_SERVICE_INDEX.md |
| Integration examples | ess_integration_examples.py |
| Test examples | test_ess_service.py |
| File checklist | DELIVERABLES.md |
| This quick ref | QUICK_REFERENCE.md |

---

## ✅ Checklist Before Deploy

- [ ] Copied ess_service.py to backend/app/services/
- [ ] Can import ESSService without errors
- [ ] Ran tests: pytest test_ess_service.py -v --cov
- [ ] All 40+ tests PASSED
- [ ] Coverage is 100%
- [ ] Read ess_service_usage_guide.md
- [ ] Tested with sample employer data
- [ ] Integrated into tax return builder
- [ ] Validated output matches ATO format
- [ ] Ready for production

---

## 🚀 One-Liner Commands

```bash
# Copy service
cp ess_service.py /path/to/project/backend/app/services/

# Run tests
pytest test_ess_service.py -v --cov

# Check coverage
pytest test_ess_service.py --cov=ess_service --cov-report=term-missing

# Show test summary
pytest test_ess_service.py -v --tb=short
```

---

**Version:** 1.0.0 | **Tax Year:** 2024-25 | **Status:** ✅ Production Ready

Start with → **ess_service_usage_guide.md**
