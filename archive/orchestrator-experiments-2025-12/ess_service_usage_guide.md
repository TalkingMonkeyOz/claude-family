# ESS Service - Usage Guide & Implementation

## Overview

The `ess_service.py` module provides comprehensive Employee Share Scheme (ESS) taxation calculations for Section 12 of the Australian tax return, implementing Division 83A-C of the Income Tax Assessment Act 1997.

## File Location

```
backend/app/services/ess_service.py
```

## Key Features Implemented

### 1. **ESS Type Support**
- ✅ Discount shares (most common)
- ✅ Options
- ✅ Rights
- ✅ Restricted shares

### 2. **$1,000 Exemption Logic** (s 83A-75)
Automatically applies to:
- Salary sacrifice schemes
- Small business schemes  
- Employer contribution schemes
- Exemption amount: $1,000.00

### 3. **Deferred Taxing Point** (s 83A-35, s 83A-80)
Calculates deferral eligibility based on:
- Real Risk of Forfeiture requirement
- Earliest of: cessation, scheme change, disposal, 15 years
- Validates acquisition date (≥ 1 July 2009)

### 4. **Option Exercise Scenarios**
- Standard exercise
- Cashless exercise
- Cashless cashout
- Calculates gain on exercise
- Tracks cost base for resulting shares

### 5. **CGT Cost Base Tracking**
For eventual disposal:
- Cost base = amount paid + taxable discount
- Component-based calculation
- Audit trail of cost base components

### 6. **Tax Return Formatting**
Outputs Section 12 income entry with:
- Taxable amounts
- Deferred taxing point details
- Employer information
- CGT reference notes

## Data Classes

### Core Classes

```python
# ESS Interest - represents one ESS interest
ESSInterest(
    interest_id: str              # Unique ID
    ess_type: ESSType             # DISCOUNT_SHARE, OPTION, RIGHT, RESTRICTED_SHARE
    scheme_type: SchemeType       # SALARY_SACRIFICE, EMPLOYER_CONTRIBUTION, etc.
    acquisition_date: date        # When acquired
    amount_paid: Decimal          # What employee paid
    market_value_acquisition: Decimal  # MV at acquisition
    employer_name: str
    plan_name: str
    expiry_date: Optional[date]
    has_real_risk_forfeiture: bool    # For deferral eligibility
    conditions_of_deferral: Optional[str]
)

# ESS Statement - batch of interests from employer
ESSStatement(
    statement_id: str
    employer_name: str
    employer_abn: str
    statement_date: date
    tax_year: str               # e.g., "2024-25"
    interests: List[ESSInterest]
    notes: Optional[str]
)

# Taxable Discount - discount calculation result
TaxableDiscount(
    raw_discount: Decimal       # MV - amount paid
    exemption_applied: Decimal  # $0 or $1,000
    taxable_discount: Decimal   # Raw - exemption
    is_eligible_for_exemption: bool
    exemption_notes: str
)

# Deferred Taxing Point - deferral eligibility
DeferralEligibility(
    is_eligible: bool
    reason_code: Optional[DeferralReasonCode]
    eligible_until_date: Optional[date]
    notes: Optional[str]
)

# CGT Cost Base - for share disposal later
CGTCostBase(
    acquisition_date: date
    cost_base_amount: Decimal
    components: Dict[str, Decimal]  # Breakdown of cost base
    notes: str
)
```

## Main Service Class

### `ESSService`

#### Core Methods

##### 1. `calculate_taxable_discount(interest, current_date=None) -> TaxableDiscount`

Calculates taxable discount with $1,000 exemption.

```python
service = ESSService()

# Calculate discount for a discount share
taxable_discount = service.calculate_taxable_discount(
    interest=my_ess_interest,
    current_date=date(2024, 6, 30)
)

print(f"Raw discount: ${taxable_discount.raw_discount}")
print(f"Exemption: ${taxable_discount.exemption_applied}")
print(f"Taxable: ${taxable_discount.taxable_discount}")
print(taxable_discount.exemption_notes)
```

**Returns:**
- `raw_discount`: Market value - Amount paid
- `exemption_applied`: Min(raw_discount, $1,000)
- `taxable_discount`: Amount includible in income
- `is_eligible_for_exemption`: True/False
- `exemption_notes`: Detailed explanation

---

##### 2. `check_deferred_taxing_point_eligibility(interest, current_date=None) -> DeferralEligibility`

Determines if deferred taxing point applies (Subdivision 83A-C).

```python
deferral = service.check_deferred_taxing_point_eligibility(
    interest=my_option,
    current_date=date(2024, 6, 30)
)

if deferral.is_eligible:
    print(f"Deferral eligible until: {deferral.eligible_until_date}")
    print(deferral.notes)
```

**Eligibility Requirements:**
1. ✅ Interest type supports deferral (share, option, right)
2. ✅ Acquired on/after 1 July 2009
3. ✅ Real Risk of Forfeiture exists
4. ✅ Before 15-year anniversary of acquisition

**Triggers for Taxing Point:**
- Cessation of employment
- Change in scheme
- Disposal/transfer
- 15 years from acquisition

---

##### 3. `calculate_option_exercise(interest, option_details, exercise_scenario) -> Dict`

Models option exercise and resulting shares.

```python
exercise_result = service.calculate_option_exercise(
    interest=option_interest,
    option_details=OptionDetails(
        exercise_price=Decimal("15.00"),
        number_of_shares_underlying=1000
    ),
    exercise_scenario=OptionExerciseScenario(
        exercise_date=date(2024, 3, 15),
        exercise_type=OptionExerciseType.STANDARD_EXERCISE,
        market_value_at_exercise=Decimal("22.50"),
        shares_acquired=1000,
        exercise_price_paid=Decimal("15000.00")
    )
)

print(f"Gain on exercise: ${exercise_result['gain_on_exercise']}")
print(f"Cost base: ${exercise_result['cost_base']}")
print(f"Cost base per share: ${exercise_result['cost_base_per_share']}")
```

**Outputs:**
- `gain_on_exercise`: MV - exercise price paid
- `cost_base`: Cost base for resulting shares (CGT)
- `deferral_applied`: Whether option had deferral
- Exercise date, price, shares, etc.

---

##### 4. `calculate_cgt_cost_base(interest, taxable_discount_info, additional_cost_components) -> CGTCostBase`

Calculates cost base for CGT purposes when taxing point triggers.

```python
cost_base = service.calculate_cgt_cost_base(
    interest=discount_share,
    taxable_discount_info=taxable_discount,
    additional_cost_components={
        "brokerage": Decimal("50.00"),
        "stamp_duty": Decimal("100.00")
    }
)

print(f"Total cost base: ${cost_base.cost_base_amount}")
for component, amount in cost_base.components.items():
    print(f"  {component}: ${amount}")
```

**Components:**
- Amount paid
- Taxable discount (when included in income)
- Brokerage, stamp duty, etc.
- Other acquisition costs

---

##### 5. `process_statement(statement, current_date=None) -> Dict`

Batch process entire ESS statement.

```python
service = ESSService()
results = service.process_statement(
    statement=ess_statement,
    current_date=date(2024, 6, 30)
)

# Results include:
# - Per-interest calculations
# - Summary totals
# - Deferred interests count
print(f"Total taxable discount: ${results['summary']['total_taxable_discount']}")
print(f"Deferred interests: {results['summary']['interests_with_deferred_taxing_point']}")
```

---

##### 6. `format_for_tax_return(statement, current_date=None, tax_year=None) -> Dict`

Formats ESS information for tax return Section 12.

```python
tax_return_entry = service.format_for_tax_return(
    statement=ess_statement,
    current_date=date(2024, 6, 30),
    tax_year="2024-25"
)

# Output formatted as:
# {
#   "section": 12,
#   "income_type": "Employee Share Scheme",
#   "employer": {...},
#   "income_details": [
#     {
#       "interest_id": "...",
#       "amount_included_in_income": "...",
#       "deferred_taxing_point_eligible": True/False,
#       ...
#     }
#   ],
#   "summary": {
#     "total_income": "...",
#     "total_exemptions": "...",
#     "total_deferred_interests": ...
#   },
#   "cgt_notes": "..."
# }
```

## Usage Examples

### Example 1: Simple Discount Share

```python
from ess_service import ESSService, ESSStatementBuilder, SchemeType
from datetime import date
from decimal import Decimal

# Create statement
builder = ESSStatementBuilder(
    statement_id="STMT-2024-001",
    employer_name="TechCorp Australia",
    employer_abn="12345678901"
)

# Add discount share
builder.add_discount_share(
    interest_id="SHARE-001",
    plan_name="Salary Sacrifice Share Plan",
    acquisition_date=date(2023, 7, 15),
    amount_paid=Decimal("5000.00"),
    market_value=Decimal("7500.00"),  # $2,500 discount
    scheme_type=SchemeType.SALARY_SACRIFICE,
    has_rrof=True  # Has real risk of forfeiture
)

statement = builder.build()

# Calculate
service = ESSService()

# Get taxable discount (with $1,000 exemption applied)
discount = service.calculate_taxable_discount(statement.interests[0])
print(f"Raw discount: ${discount.raw_discount}")      # $2,500.00
print(f"Exemption: ${discount.exemption_applied}")    # $1,000.00
print(f"Taxable: ${discount.taxable_discount}")        # $1,500.00

# Check deferral
deferral = service.check_deferred_taxing_point_eligibility(statement.interests[0])
print(f"Deferred taxing point: {deferral.is_eligible}")  # True
print(f"Eligible until: {deferral.eligible_until_date}") # 15 July 2038

# Format for tax return
tax_return = service.format_for_tax_return(statement)
print(json.dumps(tax_return, indent=2, default=str))
```

### Example 2: Option Exercise

```python
from ess_service import (
    ESSService, ESSStatementBuilder, SchemeType,
    OptionDetails, OptionExerciseScenario, OptionExerciseType
)
from datetime import date
from decimal import Decimal

# Create option interest
builder = ESSStatementBuilder(
    statement_id="STMT-2024-002",
    employer_name="TechCorp Australia",
    employer_abn="12345678901"
)

builder.add_option(
    interest_id="OPTION-001",
    plan_name="Executive Option Plan",
    acquisition_date=date(2022, 1, 1),
    exercise_price=Decimal("15.00"),
    number_of_shares=1000,
    scheme_type=SchemeType.GENERAL,
    has_rrof=True
)

statement = builder.build()
service = ESSService()

# Option is exercised
option_details = OptionDetails(
    exercise_price=Decimal("15.00"),
    number_of_shares_underlying=1000
)

exercise_scenario = OptionExerciseScenario(
    exercise_date=date(2024, 3, 15),
    exercise_type=OptionExerciseType.STANDARD_EXERCISE,
    market_value_at_exercise=Decimal("22.50"),  # Share price on exercise
    shares_acquired=1000,
    exercise_price_paid=Decimal("15000.00")  # 1000 × $15
)

result = service.calculate_option_exercise(
    interest=statement.interests[0],
    option_details=option_details,
    exercise_scenario=exercise_scenario
)

print(f"Gain on exercise: ${result['gain_on_exercise']}")  # $7,500
print(f"Cost base per share: ${result['cost_base_per_share']}")  # $22.50
```

### Example 3: Multiple Interests in Statement

```python
# Create comprehensive statement
builder = ESSStatementBuilder(
    statement_id="STMT-2024-COMPREHENSIVE",
    employer_name="MegaCorp Australia",
    employer_abn="98765432101"
)

builder.with_statement_date(date(2024, 6, 30))
builder.with_tax_year("2024-25")

# Interest 1: Salary sacrifice discount share
builder.add_discount_share(
    interest_id="DISC-001",
    plan_name="Salary Sacrifice Plan",
    acquisition_date=date(2023, 7, 15),
    amount_paid=Decimal("5000.00"),
    market_value=Decimal("7500.00"),
    scheme_type=SchemeType.SALARY_SACRIFICE,
    has_rrof=True
)

# Interest 2: General scheme discount share (no exemption)
builder.add_discount_share(
    interest_id="DISC-002",
    plan_name="General Share Purchase Plan",
    acquisition_date=date(2024, 1, 1),
    amount_paid=Decimal("10000.00"),
    market_value=Decimal("12000.00"),
    scheme_type=SchemeType.GENERAL,
    has_rrof=False
)

# Interest 3: Option (no discount initially)
builder.add_option(
    interest_id="OPT-001",
    plan_name="Executive Options",
    acquisition_date=date(2022, 1, 1),
    exercise_price=Decimal("10.00"),
    number_of_shares=2000,
    scheme_type=SchemeType.GENERAL,
    has_rrof=True
)

statement = builder.build()

# Process all interests
service = ESSService()
results = service.process_statement(statement)

print("Statement Summary:")
print(f"Total raw discount: ${results['summary']['total_raw_discount']}")
print(f"Total exemption: ${results['summary']['total_exemption']}")
print(f"Total taxable: ${results['summary']['total_taxable_discount']}")
print(f"Interests with deferral: {results['summary']['interests_with_deferred_taxing_point']}")

# Format for tax return
tax_entry = service.format_for_tax_return(statement)
```

## Validation

### Using ESSValidator

```python
from ess_service import ESSValidator

# Validate entire statement
errors = ESSValidator.validate_statement(statement)
if errors:
    for error in errors:
        print(f"❌ {error}")
else:
    print("✅ Statement is valid")

# Validate single interest
errors = ESSValidator.validate_interest(interest)
```

## Tax Rules Implemented

### Division 83A-C (ATO)

| Rule | Implementation | Key Points |
|------|---|---|
| **s 83A-75** ($1,000 exemption) | `calculate_taxable_discount()` | Salary sacrifice, small business, employer contribution schemes only |
| **s 83A-35** (Deferred taxing point) | `check_deferred_taxing_point_eligibility()` | Earliest of: cessation, scheme change, disposal, 15 years |
| **s 83A-80** (Real risk of forfeiture) | Deferral eligibility check | Required for deferral to apply |
| **Division 83A application date** | Validation in service | Only applies to interests acquired from 1 July 2009 |
| **Discount calculation** | `raw_discount` property | Market value - amount paid |
| **Cost base tracking** | `calculate_cgt_cost_base()` | For eventual disposal under CGT provisions |

### ATO Rulings Referenced

- **TR 2002/17**: Employee Share Schemes - Taxation Treatment
- **TR 2018/2**: Discount Shares - Subdivision 83A
- **Practical Compliance Guideline PCG 2017/5**: Division 83A - Employee Share Schemes

## Integration with Tax Return System

### Output Format

The `format_for_tax_return()` method outputs Section 12 in format compatible with:
- ATO Tax Return section 12 (Employee share schemes)
- Capital Gains Tax cost base tracking
- Deferred income scheduling
- Multi-year tax planning

### Sample Output

```json
{
  "section": 12,
  "income_type": "Employee Share Scheme",
  "tax_year": "2024-25",
  "statement_date": "2024-06-30",
  "employer": {
    "name": "TechCorp Australia Pty Ltd",
    "abn": "12345678901"
  },
  "income_details": [
    {
      "interest_id": "SHARE-001",
      "type": "discount_share",
      "acquisition_date": "2023-07-15",
      "amount_included_in_income": "1500.00",
      "deferred_taxing_point_eligible": true,
      "eligible_until": "2038-07-15",
      "notes": "Discount of $2,500.00 exceeds $1,000 exemption..."
    }
  ],
  "summary": {
    "total_income": "1500.00",
    "total_exemptions": "1000.00",
    "total_deferred_interests": 1
  },
  "cgt_notes": "For shares acquired via ESS, cost base is amount paid plus taxable discount included in income..."
}
```

## Constants

```python
class ESSService:
    EXEMPTION_AMOUNT = Decimal("1000.00")  # s 83A-75
    ACQUISITION_DATE_THRESHOLD = date(2009, 7, 1)  # Division 83A starts
    MAX_DEFERRAL_YEARS = 15  # s 83A-35(1)(c)
```

## Error Handling

All classes validate inputs and raise `ValueError` for:
- Negative amounts
- Invalid date ranges
- Inconsistent data
- Missing required fields

```python
try:
    interest = ESSInterest(
        interest_id="TEST",
        ess_type=ESSType.DISCOUNT_SHARE,
        # ... other fields
        amount_paid=Decimal("-1000"),  # Invalid!
    )
except ValueError as e:
    print(f"Error: {e}")
```

## Performance Notes

- All calculations are O(n) where n = number of interests
- Suitable for batch processing of large employer statements
- No external dependencies beyond standard library
- Decimal precision for all monetary calculations

## Testing

```python
# Recommended test cases
- Discount > $1,000 (exemption applies)
- Discount < $1,000 (full discount exempt)
- Non-eligible scheme (no exemption)
- Before 1 July 2009 (not in Division 83A)
- No real risk of forfeiture (no deferral)
- Option exercise (standard, cashless, cashout)
- CGT cost base with multiple components
```

## File Integration

To use in your ATO Tax Agent backend:

```python
# In backend/app/services/ess_service.py
from .ess_service import (
    ESSService,
    ESSStatement,
    ESSInterest,
    ESSStatementBuilder,
    TaxableDiscount,
    DeferralEligibility,
    CGTCostBase
)

# In your tax return builder
from app.services.ess_service import ESSService

def build_tax_return_section_12(employer_statements: List[ESSStatement]):
    service = ESSService()
    section_12 = []
    
    for statement in employer_statements:
        section_entry = service.format_for_tax_return(statement)
        section_12.append(section_entry)
    
    return section_12
```

## Version & Updates

- **Version**: 1.0.0
- **Tax Year**: 2024-25
- **Last Updated**: 2024
- **ATO Rules Updated**: Division 83A-C current as of 1 July 2024

---

**For ATO Compliance**: This service implements current tax law as of the 2024-25 tax year. Refer to ATO Rulings TR 2002/17 and TR 2018/2 for detailed guidance.
