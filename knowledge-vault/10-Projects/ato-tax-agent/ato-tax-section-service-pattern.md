---
category: service-architecture
confidence: 95
created: 2025-12-19
projects:
- ato-tax-agent
synced: true
synced_at: '2025-12-20T13:15:19.809598'
tags:
- ato
- tax
- python
- services
title: ATO Tax Section Service Pattern
type: pattern
---

# ATO Tax Section Service Pattern

## Summary
Standard pattern for creating ATO tax section calculation services in Python.

## Details
When implementing a new tax section (e.g., FMD, CGT, Deductions), follow this consistent pattern:

### 1. Create Dataclasses for Entities
```python
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class FMDDeposit:
    deposit_date: date
    amount: Decimal
    bank_name: str
    
    @property
    def net_income(self) -> Decimal:
        """Computed property for derived values"""
        return self.amount * Decimal("0.85")
```

### 2. Create Service Class
```python
class FMDService:
    def __init__(self):
        self.deposits: list[FMDDeposit] = []
    
    def add(self, deposit: FMDDeposit) -> None:
        """Add entity to collection"""
        self.deposits.append(deposit)
    
    def calculate(self) -> Decimal:
        """Perform calculations"""
        return sum(d.amount for d in self.deposits)
    
    def validate(self) -> list[str]:
        """Return list of validation errors"""
        errors = []
        if not self.deposits:
            errors.append("No deposits recorded")
        return errors
    
    def format(self) -> dict:
        """Format for ATO return"""
        return {
            "D": self.total_deposits,
            "N": self.net_income,
            "R": self.retained_earnings
        }
    
    def get_ato_references(self) -> dict:
        """Help text and links"""
        return {
            "guide_url": "https://ato.gov.au/...",
            "form_label": "Farm Management Deposits"
        }
```

### 3. Convenience Function
```python
def calculate_fmd(deposits: list[dict]) -> dict:
    """Direct calculation without service instantiation"""
    service = FMDService()
    for d in deposits:
        service.add(FMDDeposit(**d))
    return service.format()
```

## Key Elements

| Element | Purpose |
|---------|---------|
| Dataclasses | Type-safe entity representation |
| Computed properties | Derived values (net_income, assessable_amount) |
| add/calculate/validate/format | Standard service interface |
| get_ato_references() | Help text and ATO links |
| Convenience function | Simple API for direct use |
| ATO labels (D, N, R, E) | Standard field codes |
| LOSS handling | Negative amounts where applicable |
| Threshold constants | Module-level constants |

## Related
- [[ato-cgt-calculations]]
- [[ato-deduction-patterns]]