"""
Employee Share Scheme (ESS) Service for Australian Tax Return - Section 12.

Handles ESS statements from employers and implements Division 83A rules for
taxable income calculation with support for deferred taxing points and
capital gains tax linkage.

Key Rules (2024-25):
- Discount = Market Value at Acquisition - Amount Paid
- $1,000 exemption for eligible schemes (salary sacrifice/small business)
- Deferred taxing point: earliest of cessation, scheme change, 15 years
- Real risk of forfeiture required for deferral eligibility
- Division 83A applies to interests acquired from 1 July 2009

References:
- Division 83A-C (ITAA 1997)
- ATO ID 2009/81: Deferred taxing point under Division 83A
- ATO ID 2009/59: Real risk of forfeiture
"""

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import uuid4


class ESSType(Enum):
    """Types of Employee Share Scheme interests."""
    DISCOUNT_ON_SHARES = "discount_on_shares"  # Shares acquired at discount
    SHARE_OPTIONS = "share_options"  # Right to purchase shares at fixed price
    SHARE_RIGHTS = "share_rights"  # Right to receive shares on conditions
    RESTRICTED_SHARES = "restricted_shares"  # Shares with restrictions


class SchemeType(Enum):
    """ESS scheme types affecting taxing point and exemptions."""
    ELIGIBLE_SALARY_SACRIFICE = "eligible_salary_sacrifice"  # $1,000 exemption
    SMALL_BUSINESS_SHARES = "small_business_shares"  # $1,000 exemption
    OTHER_SCHEME = "other_scheme"  # No exemption, immediate taxing point


class DeferralReason(Enum):
    """Reasons for deferral of taxing point."""
    REAL_RISK_OF_FORFEITURE = "real_risk_of_forfeiture"  # Holdings forfeit if conditions not met
    SCHEME_CONDITION = "scheme_condition"  # Scheme rules impose retention period
    NONE = "none"  # No deferral, immediate taxing point


class TaxingPointTrigger(Enum):
    """Events that trigger the deferred taxing point."""
    SCHEME_CESSATION = "scheme_cessation"  # Employer ceases ESS
    INTEREST_CESSATION = "interest_cessation"  # Employee ceases holding interest
    SCHEME_MODIFICATION = "scheme_modification"  # Scheme rules change substantially
    FIFTEEN_YEAR_ANNIVERSARY = "fifteen_year_anniversary"  # 15 years from acquisition
    EARLIEST_PERMISSIBLE_DATE = "earliest_permissible_date"  # Earliest date set by scheme


@dataclass
class ESSInterest:
    """Single ESS interest (share, option, or right) acquired by employee."""
    
    interest_id: str = field(default_factory=lambda: str(uuid4()))
    interest_type: ESSType = ESSType.DISCOUNT_ON_SHARES
    acquisition_date: date = field(default_factory=date.today)
    quantity: Decimal = Decimal("0")
    
    # Pricing details
    amount_paid: Decimal = Decimal("0")  # What employee paid
    market_value_at_acquisition: Decimal = Decimal("0")  # FMV at acquisition
    
    # Deferral details
    deferral_reason: DeferralReason = DeferralReason.NONE
    has_real_risk_of_forfeiture: bool = False
    
    # Deferred taxing point
    deferred_taxing_point_date: Optional[date] = None  # When deferral ends
    taxing_point_trigger: Optional[TaxingPointTrigger] = None
    
    # Additional details for tracking
    exercise_price: Optional[Decimal] = None  # For options/rights
    conditions_satisfied_date: Optional[date] = None  # When conditions met
    
    def calculate_discount(self) -> Decimal:
        """
        Calculate discount on acquisition.
        
        Discount = Market Value at Acquisition - Amount Paid
        
        Returns:
            Decimal: Discount amount (per unit for per-unit storage)
        """
        if self.interest_type == ESSType.SHARE_OPTIONS:
            # Options: discount is difference between FMV and exercise price
            if self.exercise_price is None:
                return Decimal("0")
            return max(Decimal("0"), self.market_value_at_acquisition - self.exercise_price)
        
        # Shares and rights: discount is FMV minus amount paid
        return max(Decimal("0"), self.market_value_at_acquisition - self.amount_paid)
    
    def total_discount(self) -> Decimal:
        """Calculate total discount across all units."""
        return self.calculate_discount() * self.quantity
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "interest_id": self.interest_id,
            "interest_type": self.interest_type.value,
            "acquisition_date": self.acquisition_date.isoformat(),
            "quantity": str(self.quantity),
            "amount_paid": str(self.amount_paid),
            "market_value_at_acquisition": str(self.market_value_at_acquisition),
            "deferral_reason": self.deferral_reason.value,
            "has_real_risk_of_forfeiture": self.has_real_risk_of_forfeiture,
            "deferred_taxing_point_date": self.deferred_taxing_point_date.isoformat() if self.deferred_taxing_point_date else None,
            "taxing_point_trigger": self.taxing_point_trigger.value if self.taxing_point_trigger else None,
            "exercise_price": str(self.exercise_price) if self.exercise_price else None,
            "conditions_satisfied_date": self.conditions_satisfied_date.isoformat() if self.conditions_satisfied_date else None,
        }


@dataclass
class ESSStatement:
    """ESS statement from employer for a tax year."""
    
    statement_id: str = field(default_factory=lambda: str(uuid4()))
    tax_year: str = ""  # Format: "2024-25"
    employer_name: str = ""
    employer_abn: str = ""
    statement_date: date = field(default_factory=date.today)
    
    scheme_name: str = ""
    scheme_type: SchemeType = SchemeType.OTHER_SCHEME
    
    interests: List[ESSInterest] = field(default_factory=list)
    
    def add_interest(self, interest: ESSInterest) -> None:
        """Add an ESS interest to this statement."""
        self.interests.append(interest)
    
    def total_discount(self) -> Decimal:
        """Sum of all discounts on interests."""
        return sum((interest.total_discount() for interest in self.interests), Decimal("0"))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "statement_id": self.statement_id,
            "tax_year": self.tax_year,
            "employer_name": self.employer_name,
            "employer_abn": self.employer_abn,
            "statement_date": self.statement_date.isoformat(),
            "scheme_name": self.scheme_name,
            "scheme_type": self.scheme_type.value,
            "interests": [interest.to_dict() for interest in self.interests],
            "total_discount": str(self.total_discount()),
        }


class ESSCalculator:
    """Calculator for ESS taxable income under Division 83A."""
    
    EXEMPTION_AMOUNT = Decimal("1000")  # $1,000 exemption for eligible schemes
    DEFERRAL_PERIOD_YEARS = 15  # Maximum 15-year deferral
    DIVISION_83A_START_DATE = date(2009, 7, 1)  # Division 83A applies from this date
    
    @staticmethod
    def is_eligible_for_exemption(scheme_type: SchemeType) -> bool:
        """
        Check if scheme type qualifies for $1,000 exemption.
        
        Eligible schemes:
        - Eligible salary sacrifice schemes
        - Small business shares schemes
        
        Args:
            scheme_type: Type of ESS scheme
            
        Returns:
            bool: True if eligible for exemption
        """
        return scheme_type in (
            SchemeType.ELIGIBLE_SALARY_SACRIFICE,
            SchemeType.SMALL_BUSINESS_SHARES,
        )
    
    @staticmethod
    def is_eligible_for_deferral(interest: ESSInterest, current_date: date) -> bool:
        """
        Check if ESS interest is eligible for deferred taxing point.
        
        Eligibility criteria:
        1. Acquisition date on or after 1 July 2009 (Division 83A)
        2. Real risk of forfeiture must exist, OR
        3. Scheme rules must prohibit earlier cessation
        
        Args:
            interest: ESS interest to check
            current_date: Current date for age calculations
            
        Returns:
            bool: True if eligible for deferral
        """
        # Check Division 83A applicability
        if interest.acquisition_date < ESSCalculator.DIVISION_83A_START_DATE:
            return False
        
        # Real risk of forfeiture is key eligibility criterion
        if interest.deferral_reason == DeferralReason.REAL_RISK_OF_FORFEITURE:
            return interest.has_real_risk_of_forfeiture
        
        # Scheme condition deferral (scheme rules prevent earlier cessation)
        if interest.deferral_reason == DeferralReason.SCHEME_CONDITION:
            return True
        
        return False
    
    @staticmethod
    def calculate_deferred_taxing_point(interest: ESSInterest) -> Optional[date]:
        """
        Calculate deferred taxing point date.
        
        Deferred taxing point is the earliest of:
        1. Scheme cessation date (employer ceases ESS)
        2. Interest cessation date (employee ceases holding)
        3. Scheme modification date (substantial change)
        4. 15 years from acquisition
        5. Earliest permissible date set by scheme
        
        Args:
            interest: ESS interest with deferral details
            
        Returns:
            Optional[date]: Deferred taxing point date, or None if not deferred
        """
        if not interest.deferred_taxing_point_date:
            return None
        
        # Calculate 15-year anniversary
        fifteen_year_limit = interest.acquisition_date + timedelta(days=365.25 * 15)
        
        # Return the specified deferred taxing point (should be earliest of triggers)
        return interest.deferred_taxing_point_date
    
    @staticmethod
    def calculate_taxable_amount(
        interest: ESSInterest,
        scheme_type: SchemeType,
        current_date: date,
    ) -> Decimal:
        """
        Calculate taxable amount for ESS interest.
        
        Rules:
        1. Taxable amount = Discount on interest
        2. Less: $1,000 exemption (if eligible scheme and eligible interest)
        3. Applied when taxing point occurs (not at acquisition for deferred)
        
        Args:
            interest: ESS interest
            scheme_type: Type of scheme
            current_date: Current date for checking taxing point
            
        Returns:
            Decimal: Taxable amount (0 or positive)
        """
        discount = interest.total_discount()
        
        # Check if deferred taxing point has occurred
        if interest.deferred_taxing_point_date:
            if current_date < interest.deferred_taxing_point_date:
                # Deferral period not yet over
                return Decimal("0")
        
        # Apply exemption if eligible
        exemption = Decimal("0")
        if ESSCalculator.is_eligible_for_exemption(scheme_type):
            exemption = ESSCalculator.EXEMPTION_AMOUNT
        
        # Taxable amount = discount - exemption (minimum 0)
        taxable = discount - exemption
        return max(Decimal("0"), taxable)


@dataclass
class ESSIncome:
    """ESS taxable income derived from a statement for a tax year."""
    
    income_id: str = field(default_factory=lambda: str(uuid4()))
    statement_id: str = ""
    tax_year: str = ""
    
    # Discount details
    total_discount: Decimal = Decimal("0")
    exemption_amount: Decimal = Decimal("0")
    taxable_amount: Decimal = Decimal("0")
    
    # Breakdown by deferral status
    immediate_taxing_discount: Decimal = Decimal("0")
    deferred_taxing_discount: Decimal = Decimal("0")
    
    # Deferred items
    deferred_interests: List[str] = field(default_factory=list)  # interest_ids
    
    # CGT linkage
    cost_base_adjustment: Decimal = Decimal("0")  # Amount to add to cost base
    cgt_category: str = "CGT asset at acquisition date"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "income_id": self.income_id,
            "statement_id": self.statement_id,
            "tax_year": self.tax_year,
            "total_discount": str(self.total_discount),
            "exemption_amount": str(self.exemption_amount),
            "taxable_amount": str(self.taxable_amount),
            "immediate_taxing_discount": str(self.immediate_taxing_discount),
            "deferred_taxing_discount": str(self.deferred_taxing_discount),
            "deferred_interests": self.deferred_interests,
            "cost_base_adjustment": str(self.cost_base_adjustment),
            "cgt_category": self.cgt_category,
        }


class ESSService:
    """
    Service for handling Employee Share Scheme (ESS) calculations.
    
    Responsibilities:
    - Parse ESS statements from employers
    - Calculate taxable income under Division 83A
    - Track deferred taxing points
    - Link to CGT for future disposal
    - Format ESS income for tax return
    """
    
    def __init__(self):
        """Initialize ESS service."""
        self.calculator = ESSCalculator()
        self.statements: Dict[str, ESSStatement] = {}
        self.income_records: Dict[str, ESSIncome] = {}
    
    def create_statement(
        self,
        tax_year: str,
        employer_name: str,
        employer_abn: str,
        scheme_name: str,
        scheme_type: SchemeType,
        statement_date: Optional[date] = None,
    ) -> ESSStatement:
        """
        Create a new ESS statement.
        
        Args:
            tax_year: Tax year (e.g., "2024-25")
            employer_name: Name of employer
            employer_abn: ABN of employer
            scheme_name: Name of ESS scheme
            scheme_type: Type of scheme
            statement_date: Date statement issued (default: today)
            
        Returns:
            ESSStatement: New statement instance
        """
        if statement_date is None:
            statement_date = date.today()
        
        statement = ESSStatement(
            tax_year=tax_year,
            employer_name=employer_name,
            employer_abn=employer_abn,
            scheme_name=scheme_name,
            scheme_type=scheme_type,
            statement_date=statement_date,
        )
        
        self.statements[statement.statement_id] = statement
        return statement
    
    def add_discount_shares_interest(
        self,
        statement: ESSStatement,
        acquisition_date: date,
        quantity: Decimal,
        amount_paid: Decimal,
        market_value_at_acquisition: Decimal,
        deferral_reason: DeferralReason = DeferralReason.NONE,
        has_real_risk_of_forfeiture: bool = False,
        deferred_taxing_point_date: Optional[date] = None,
        taxing_point_trigger: Optional[TaxingPointTrigger] = None,
    ) -> ESSInterest:
        """
        Add shares acquired at discount to statement.
        
        Args:
            statement: ESS statement
            acquisition_date: Date shares acquired
            quantity: Number of shares
            amount_paid: Total amount employee paid
            market_value_at_acquisition: FMV of shares at acquisition
            deferral_reason: Reason for any deferral
            has_real_risk_of_forfeiture: Whether real risk of forfeiture exists
            deferred_taxing_point_date: When deferral ends (if applicable)
            taxing_point_trigger: What event triggers the taxing point
            
        Returns:
            ESSInterest: The created interest
        """
        interest = ESSInterest(
            interest_type=ESSType.DISCOUNT_ON_SHARES,
            acquisition_date=acquisition_date,
            quantity=quantity,
            amount_paid=amount_paid,
            market_value_at_acquisition=market_value_at_acquisition,
            deferral_reason=deferral_reason,
            has_real_risk_of_forfeiture=has_real_risk_of_forfeiture,
            deferred_taxing_point_date=deferred_taxing_point_date,
            taxing_point_trigger=taxing_point_trigger,
        )
        
        statement.add_interest(interest)
        return interest
    
    def add_options_interest(
        self,
        statement: ESSStatement,
        acquisition_date: date,
        quantity: Decimal,
        exercise_price: Decimal,
        market_value_at_acquisition: Decimal,
        deferral_reason: DeferralReason = DeferralReason.NONE,
        has_real_risk_of_forfeiture: bool = False,
        deferred_taxing_point_date: Optional[date] = None,
        taxing_point_trigger: Optional[TaxingPointTrigger] = None,
    ) -> ESSInterest:
        """
        Add share options to statement.
        
        Options taxable amount = (FMV at acquisition - Exercise price) × Quantity
        
        Args:
            statement: ESS statement
            acquisition_date: Date options acquired
            quantity: Number of options
            exercise_price: Fixed price to exercise options
            market_value_at_acquisition: FMV of underlying shares at acquisition
            deferral_reason: Reason for any deferral
            has_real_risk_of_forfeiture: Whether real risk of forfeiture exists
            deferred_taxing_point_date: When deferral ends (if applicable)
            taxing_point_trigger: What event triggers the taxing point
            
        Returns:
            ESSInterest: The created interest
        """
        interest = ESSInterest(
            interest_type=ESSType.SHARE_OPTIONS,
            acquisition_date=acquisition_date,
            quantity=quantity,
            exercise_price=exercise_price,
            market_value_at_acquisition=market_value_at_acquisition,
            deferral_reason=deferral_reason,
            has_real_risk_of_forfeiture=has_real_risk_of_forfeiture,
            deferred_taxing_point_date=deferred_taxing_point_date,
            taxing_point_trigger=taxing_point_trigger,
        )
        
        statement.add_interest(interest)
        return interest
    
    def add_rights_interest(
        self,
        statement: ESSStatement,
        acquisition_date: date,
        quantity: Decimal,
        market_value_at_acquisition: Decimal,
        conditions_satisfied_date: Optional[date] = None,
        deferral_reason: DeferralReason = DeferralReason.NONE,
        has_real_risk_of_forfeiture: bool = False,
        deferred_taxing_point_date: Optional[date] = None,
        taxing_point_trigger: Optional[TaxingPointTrigger] = None,
    ) -> ESSInterest:
        """
        Add share rights (conditional rights to receive shares) to statement.
        
        Rights taxable amount = FMV at acquisition × Quantity
        (Conditions satisfied date triggers taxing point if deferred)
        
        Args:
            statement: ESS statement
            acquisition_date: Date rights acquired
            quantity: Number of rights/shares underlying
            market_value_at_acquisition: FMV of shares at acquisition
            conditions_satisfied_date: Date when conditions satisfied
            deferral_reason: Reason for any deferral
            has_real_risk_of_forfeiture: Whether real risk of forfeiture exists
            deferred_taxing_point_date: When deferral ends (if applicable)
            taxing_point_trigger: What event triggers the taxing point
            
        Returns:
            ESSInterest: The created interest
        """
        interest = ESSInterest(
            interest_type=ESSType.SHARE_RIGHTS,
            acquisition_date=acquisition_date,
            quantity=quantity,
            market_value_at_acquisition=market_value_at_acquisition,
            conditions_satisfied_date=conditions_satisfied_date,
            deferral_reason=deferral_reason,
            has_real_risk_of_forfeiture=has_real_risk_of_forfeiture,
            deferred_taxing_point_date=deferred_taxing_point_date,
            taxing_point_trigger=taxing_point_trigger,
        )
        
        statement.add_interest(interest)
        return interest
    
    def calculate_income(
        self,
        statement: ESSStatement,
        current_date: Optional[date] = None,
    ) -> ESSIncome:
        """
        Calculate ESS taxable income for a statement.
        
        Calculates:
        1. Total discount on all interests
        2. Exemption amount (if eligible)
        3. Taxable amount (discount - exemption)
        4. Tracks deferred items
        5. CGT cost base adjustment
        
        Args:
            statement: ESS statement
            current_date: Current date for checking deferred taxing points
            
        Returns:
            ESSIncome: Calculated income record
        """
        if current_date is None:
            current_date = date.today()
        
        income = ESSIncome(
            statement_id=statement.statement_id,
            tax_year=statement.tax_year,
        )
        
        exemption_available = Decimal("0")
        if self.calculator.is_eligible_for_exemption(statement.scheme_type):
            exemption_available = ESSCalculator.EXEMPTION_AMOUNT
        
        total_discount = Decimal("0")
        total_taxable = Decimal("0")
        total_immediate = Decimal("0")
        total_deferred = Decimal("0")
        cost_base_total = Decimal("0")
        
        for interest in statement.interests:
            discount = interest.total_discount()
            total_discount += discount
            
            # Calculate taxable amount for this interest
            taxable = self.calculator.calculate_taxable_amount(
                interest, statement.scheme_type, current_date
            )
            total_taxable += taxable
            
            # Track deferred items
            if interest.deferred_taxing_point_date:
                if current_date < interest.deferred_taxing_point_date:
                    total_deferred += discount
                    income.deferred_interests.append(interest.interest_id)
                else:
                    total_immediate += discount
            else:
                total_immediate += discount
            
            # Cost base adjustment for CGT
            # Amount paid is part of cost base; amount of discount is also added
            cost_base_total += interest.amount_paid + discount
        
        # Apply exemption (applies once per statement/scheme)
        exemption_used = min(exemption_available, total_taxable)
        
        income.total_discount = total_discount
        income.exemption_amount = exemption_used
        income.taxable_amount = total_taxable - exemption_used
        income.immediate_taxing_discount = total_immediate
        income.deferred_taxing_discount = total_deferred
        income.cost_base_adjustment = cost_base_total
        
        self.income_records[income.income_id] = income
        return income
    
    def format_for_tax_return(self, income: ESSIncome) -> Dict[str, Any]:
        """
        Format ESS income for tax return Section 12 (Other income).
        
        Structure:
        {
            "section": "12 - Other income",
            "line_item": "Employee share scheme",
            "description": "Details from employer statement",
            "amounts": {
                "gross_amount": total_discount,
                "less_exemption": exemption_amount,
                "net_amount": taxable_amount,
            },
            "supporting_details": {
                "employer": employer name,
                "scheme": scheme name,
                "deferred_items": count of deferred interests,
                "cgt_linkage": "Cost base adjustment for CGT",
            }
        }
        
        Args:
            income: Calculated ESS income
            
        Returns:
            Dict: Formatted for tax return
        """
        # Retrieve statement for context
        statement = self.statements.get(income.statement_id)
        if not statement:
            return {}
        
        return {
            "section": "12 - Other income",
            "line_item": "Employee share scheme",
            "description": f"{statement.scheme_name} from {statement.employer_name}",
            "amounts": {
                "gross_amount": str(income.total_discount),
                "less_exemption": str(income.exemption_amount),
                "net_amount": str(income.taxable_amount),
            },
            "supporting_details": {
                "tax_year": income.tax_year,
                "employer_name": statement.employer_name,
                "employer_abn": statement.employer_abn,
                "scheme_name": statement.scheme_name,
                "scheme_type": statement.scheme_type.value,
                "statement_date": statement.statement_date.isoformat(),
                "number_of_interests": len(statement.interests),
                "deferred_items_count": len(income.deferred_interests),
                "cost_base_adjustment": str(income.cost_base_adjustment),
                "cgt_linkage": "Cost base of shares acquired under ESS is amount paid plus taxable discount",
            },
            "notes": [
                "Deferred taxing point interests not included in current year taxable income",
                "Cost base adjustment links to CGT treatment on future disposal",
                "Real risk of forfeiture required for deferred taxing point eligibility",
            ],
        }
    
    def get_statement(self, statement_id: str) -> Optional[ESSStatement]:
        """Get a statement by ID."""
        return self.statements.get(statement_id)
    
    def get_income_record(self, income_id: str) -> Optional[ESSIncome]:
        """Get an income record by ID."""
        return self.income_records.get(income_id)
    
    def list_statements(self) -> List[ESSStatement]:
        """Get all statements."""
        return list(self.statements.values())
    
    def list_income_records(self) -> List[ESSIncome]:
        """Get all income records."""
        return list(self.income_records.values())


# Example usage and testing
if __name__ == "__main__":
    from decimal import Decimal
    from datetime import date
    
    # Initialize service
    service = ESSService()
    
    # Example 1: Salary sacrifice shares with $1,000 exemption
    statement1 = service.create_statement(
        tax_year="2024-25",
        employer_name="TechCorp Pty Ltd",
        employer_abn="12345678901",
        scheme_name="Employee Share Plan - Salary Sacrifice",
        scheme_type=SchemeType.ELIGIBLE_SALARY_SACRIFICE,
    )
    
    # Add shares acquired at discount
    service.add_discount_shares_interest(
        statement1,
        acquisition_date=date(2024, 1, 15),
        quantity=Decimal("100"),
        amount_paid=Decimal("8000"),  # Paid $80/share
        market_value_at_acquisition=Decimal("9500"),  # FMV $95/share
        deferral_reason=DeferralReason.NONE,
    )
    
    # Calculate income
    income1 = service.calculate_income(statement1)
    print("\nExample 1: Salary Sacrifice Shares")
    print(f"Total Discount: ${income1.total_discount}")
    print(f"Exemption: ${income1.exemption_amount}")
    print(f"Taxable Amount: ${income1.taxable_amount}")
    
    # Example 2: Share options with deferral
    statement2 = service.create_statement(
        tax_year="2024-25",
        employer_name="StartupInc Pty Ltd",
        employer_abn="98765432101",
        scheme_name="Employee Options Plan",
        scheme_type=SchemeType.OTHER_SCHEME,
    )
    
    service.add_options_interest(
        statement2,
        acquisition_date=date(2022, 6, 1),
        quantity=Decimal("1000"),
        exercise_price=Decimal("5.00"),
        market_value_at_acquisition=Decimal("7.50"),
        deferral_reason=DeferralReason.REAL_RISK_OF_FORFEITURE,
        has_real_risk_of_forfeiture=True,
        deferred_taxing_point_date=date(2025, 6, 1),
        taxing_point_trigger=TaxingPointTrigger.FIFTEEN_YEAR_ANNIVERSARY,
    )
    
    income2 = service.calculate_income(statement2, current_date=date(2024, 12, 31))
    print("\nExample 2: Options with Deferral (not yet taxed)")
    print(f"Total Discount: ${income2.total_discount}")
    print(f"Taxable Amount (deferred): ${income2.taxable_amount}")
    print(f"Deferred Items: {len(income2.deferred_interests)}")
    
    # Example 3: Rights with conditions
    statement3 = service.create_statement(
        tax_year="2024-25",
        employer_name="PublicCorp Ltd",
        employer_abn="55555555555",
        scheme_name="Restricted Share Plan",
        scheme_type=SchemeType.SMALL_BUSINESS_SHARES,
    )
    
    service.add_rights_interest(
        statement3,
        acquisition_date=date(2024, 7, 1),
        quantity=Decimal("50"),
        market_value_at_acquisition=Decimal("25.00"),
        conditions_satisfied_date=date(2024, 12, 31),
        deferral_reason=DeferralReason.SCHEME_CONDITION,
        has_real_risk_of_forfeiture=True,
    )
    
    income3 = service.calculate_income(statement3)
    formatted = service.format_for_tax_return(income3)
    print("\nExample 3: Restricted Shares for Tax Return")
    print(f"Formatted output: {formatted['amounts']}")
