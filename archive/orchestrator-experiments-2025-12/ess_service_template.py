"""
Employee Share Scheme (ESS) Service for Section 12 of Australian Tax Return

Implements Division 83A-C logic for:
- Discount calculation on ESS interests
- Deferred taxing point eligibility
- $1,000 exemption application
- Exercise of options scenarios
- Cost base tracking for CGT purposes

Reference: Income Tax Assessment Act 1997, Division 83A-C
ATO Ruling: TR 2002/17, TR 2018/2 (ESS discount shares)
"""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict
from abc import ABC, abstractmethod


# ============================================================================
# ENUMS
# ============================================================================

class ESSType(Enum):
    """Types of Employee Share Scheme interests"""
    DISCOUNT_SHARE = "discount_share"
    OPTION = "option"
    RIGHT = "right"
    RESTRICTED_SHARE = "restricted_share"


class SchemeType(Enum):
    """Types of ESS schemes for exemption eligibility"""
    SALARY_SACRIFICE = "salary_sacrifice"  # Full $1,000 exemption eligible
    EMPLOYER_CONTRIBUTION = "employer_contribution"  # $1,000 exemption eligible
    SMALL_BUSINESS = "small_business"  # $1,000 exemption eligible (s 83A-75)
    GENERAL = "general"  # No exemption


class DeferralReasonCode(Enum):
    """Reasons deferred taxing point may apply (s 83A-35)"""
    REAL_RISK_FORFEITURE = "real_risk_forfeiture"  # s 83A-80
    CESSATION = "cessation"  # s 83A-35(1)(a)
    SCHEME_CHANGE = "scheme_change"  # s 83A-35(1)(b)
    FIFTEEN_YEARS = "fifteen_years"  # s 83A-35(1)(c)
    DISPOSAL = "disposal"  # s 83A-35(1)(d)


class TaxingPointStatus(Enum):
    """Current status of the taxing point"""
    NOT_YET_ARISEN = "not_yet_arisen"
    DEFERRED = "deferred"
    TRIGGERED = "triggered"
    ASSESSED = "assessed"


class OptionExerciseType(Enum):
    """Type of option exercise scenario"""
    STANDARD_EXERCISE = "standard_exercise"
    CASHLESS_EXERCISE = "cashless_exercise"
    CASHLESS_CASHOUT = "cashless_cashout"


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class ESSInterest:
    """
    Represents a single ESS interest (share, option, or right)
    
    Attributes:
        interest_id: Unique identifier for this ESS interest
        ess_type: Type of interest (discount_share, option, right, etc.)
        scheme_type: Type of scheme for exemption eligibility
        acquisition_date: Date interest was acquired
        amount_paid: Amount paid by employee for the interest
        market_value_acquisition: Market value at acquisition date
        expiry_date: Date interest expires (for options/rights)
        has_real_risk_forfeiture: Whether RROF applies for deferral
        conditions_of_deferral: Optional text describing conditions
        employer_name: Name of employer offering scheme
        plan_name: Name of ESS plan
    """
    interest_id: str
    ess_type: ESSType
    scheme_type: SchemeType
    acquisition_date: date
    amount_paid: Decimal
    market_value_acquisition: Decimal
    employer_name: str
    plan_name: str
    expiry_date: Optional[date] = None
    has_real_risk_forfeiture: bool = False
    conditions_of_deferral: Optional[str] = None
    
    def __post_init__(self):
        """Validate data consistency"""
        if self.market_value_acquisition < 0:
            raise ValueError("Market value cannot be negative")
        if self.amount_paid < 0:
            raise ValueError("Amount paid cannot be negative")
        if self.expiry_date and self.expiry_date <= self.acquisition_date:
            raise ValueError("Expiry date must be after acquisition date")

    @property
    def raw_discount(self) -> Decimal:
        """Calculate raw discount: MV at acquisition - Amount paid"""
        return self.market_value_acquisition - self.amount_paid
    
    @property
    def has_discount(self) -> bool:
        """Check if this interest has a discount"""
        return self.raw_discount > 0


@dataclass
class OptionDetails:
    """Details specific to option interests"""
    exercise_price: Decimal
    number_of_shares_underlying: int
    vesting_date: Optional[date] = None
    
    def __post_init__(self):
        if self.exercise_price < 0:
            raise ValueError("Exercise price cannot be negative")
        if self.number_of_shares_underlying <= 0:
            raise ValueError("Number of shares must be positive")


@dataclass
class RightDetails:
    """Details specific to rights interests (subsidiary to options)"""
    number_of_shares_underlying: int
    vesting_percentage: Decimal = field(default=Decimal("100"))
    
    def __post_init__(self):
        if self.number_of_shares_underlying <= 0:
            raise ValueError("Number of shares must be positive")
        if self.vesting_percentage <= 0 or self.vesting_percentage > 100:
            raise ValueError("Vesting percentage must be between 0 and 100")


@dataclass
class DeferralEligibility:
    """Determines if deferred taxing point applies"""
    is_eligible: bool
    reason_code: Optional[DeferralReasonCode] = None
    eligible_until_date: Optional[date] = None
    notes: Optional[str] = None


@dataclass
class TaxableDiscount:
    """
    Calculates taxable discount with exemption application
    
    Section 83A-75: $1,000 exemption for salary sacrifice, small business
    """
    raw_discount: Decimal
    exemption_applied: Decimal  # $0 or $1,000
    taxable_discount: Decimal
    is_eligible_for_exemption: bool
    exemption_notes: str
    
    def __post_init__(self):
        if self.taxable_discount < 0:
            raise ValueError("Taxable discount cannot be negative")


@dataclass
class OptionExerciseScenario:
    """Models option exercise and resulting shares"""
    exercise_date: date
    exercise_type: OptionExerciseType
    market_value_at_exercise: Decimal
    shares_acquired: int
    exercise_price_paid: Decimal
    
    def __post_init__(self):
        if self.market_value_at_exercise < 0:
            raise ValueError("Market value cannot be negative")
        if self.shares_acquired <= 0:
            raise ValueError("Must exercise at least 1 share")
        if self.exercise_price_paid < 0:
            raise ValueError("Exercise price cannot be negative")


@dataclass
class CGTCostBase:
    """
    Cost base for CGT purposes after taxing point triggers
    
    For discount shares: cost base = (amount paid + taxable discount)
    For options exercised: cost base = (exercise price paid + taxable gain)
    """
    acquisition_date: date
    cost_base_amount: Decimal
    components: Dict[str, Decimal] = field(default_factory=dict)
    notes: str = ""
    
    def __post_init__(self):
        if self.cost_base_amount < 0:
            raise ValueError("Cost base cannot be negative")


@dataclass
class ESSStatement:
    """
    Statement of ESS interests from employer
    
    Contains one or more ESS interests and related information
    """
    statement_id: str
    employer_name: str
    employer_abn: str
    statement_date: date
    tax_year: str  # e.g., "2024-25"
    interests: List[ESSInterest] = field(default_factory=list)
    notes: Optional[str] = None
    
    def add_interest(self, interest: ESSInterest) -> None:
        """Add an ESS interest to this statement"""
        self.interests.append(interest)
    
    def get_interests_by_type(self, ess_type: ESSType) -> List[ESSInterest]:
        """Get all interests of a specific type"""
        return [i for i in self.interests if i.ess_type == ess_type]


# ============================================================================
# ESS SERVICE (Main Logic)
# ============================================================================

class ESSService:
    """
    Comprehensive service for calculating ESS taxation positions
    
    Implements Division 83A-C logic including:
    - Discount calculation with $1,000 exemption
    - Deferred taxing point determination
    - Exercise of options scenarios
    - Cost base tracking for CGT
    
    Key reference dates:
    - 1 July 2009: Division 83A applies from this date
    - 15 years: Maximum deferral period from acquisition
    """
    
    EXEMPTION_AMOUNT = Decimal("1000.00")  # s 83A-75
    ACQUISITION_DATE_THRESHOLD = date(2009, 7, 1)  # Division 83A starts
    MAX_DEFERRAL_YEARS = 15  # s 83A-35(1)(c) - 15 year limit
    
    def __init__(self):
        """Initialize ESS Service"""
        self.interests_processed: List[ESSInterest] = []
        self.deferred_interests: List[ESSInterest] = []
    
    # ========================================================================
    # CORE CALCULATION METHODS
    # ========================================================================
    
    def calculate_taxable_discount(
        self, 
        interest: ESSInterest,
        current_date: Optional[date] = None
    ) -> TaxableDiscount:
        """
        Calculate taxable discount with exemption application
        
        Section 83A-75: $1,000 exemption applies for:
        - Salary sacrifice scheme (s 83A-75(1)(a))
        - Small business scheme (s 83A-75(2))
        
        Args:
            interest: The ESS interest to calculate discount for
            current_date: Date for calculations (defaults to today)
        
        Returns:
            TaxableDiscount with breakdown of discount and exemption
        
        Raises:
            ValueError: If interest type doesn't support discount calculation
        """
        if current_date is None:
            current_date = date.today()
        
        # Only discount shares have taxable discounts
        if interest.ess_type not in [ESSType.DISCOUNT_SHARE, ESSType.RESTRICTED_SHARE]:
            return TaxableDiscount(
                raw_discount=Decimal("0"),
                exemption_applied=Decimal("0"),
                taxable_discount=Decimal("0"),
                is_eligible_for_exemption=False,
                exemption_notes="Discount calculation does not apply to this ESS type"
            )
        
        raw_discount = interest.raw_discount
        
        # Determine exemption eligibility (s 83A-75)
        is_eligible = self._is_eligible_for_exemption(interest)
        
        exemption_applied = Decimal("0")
        if is_eligible and raw_discount > 0:
            exemption_applied = min(raw_discount, self.EXEMPTION_AMOUNT)
        
        taxable_discount = max(Decimal("0"), raw_discount - exemption_applied)
        
        exemption_notes = self._generate_exemption_notes(
            interest, raw_discount, exemption_applied, is_eligible
        )
        
        return TaxableDiscount(
            raw_discount=raw_discount,
            exemption_applied=exemption_applied,
            taxable_discount=taxable_discount,
            is_eligible_for_exemption=is_eligible,
            exemption_notes=exemption_notes
        )
    
    def check_deferred_taxing_point_eligibility(
        self,
        interest: ESSInterest,
        current_date: Optional[date] = None
    ) -> DeferralEligibility:
        """
        Determine if deferred taxing point applies
        
        Deferred taxing point arises on earliest of:
        1. Cessation of employment (s 83A-35(1)(a))
        2. Change in scheme (s 83A-35(1)(b))
        3. 15 years from acquisition (s 83A-35(1)(c))
        4. Disposal/transfer (s 83A-35(1)(d))
        
        Real Risk of Forfeiture (s 83A-80): Must exist for deferral to apply
        
        Args:
            interest: The ESS interest to check
            current_date: Date for calculations
        
        Returns:
            DeferralEligibility with status and details
        """
        if current_date is None:
            current_date = date.today()
        
        # Condition 1: Interest type must be deferral-eligible
        if interest.ess_type not in [ESSType.DISCOUNT_SHARE, 
                                      ESSType.RESTRICTED_SHARE, 
                                      ESSType.OPTION, 
                                      ESSType.RIGHT]:
            return DeferralEligibility(
                is_eligible=False,
                notes="This interest type is not eligible for deferral"
            )
        
        # Condition 2: Must be acquired on or after 1 July 2009
        if interest.acquisition_date < self.ACQUISITION_DATE_THRESHOLD:
            return DeferralEligibility(
                is_eligible=False,
                notes="Interest acquired before 1 July 2009 - Division 83A does not apply"
            )
        
        # Condition 3: Real Risk of Forfeiture must exist (s 83A-80)
        if not interest.has_real_risk_forfeiture:
            return DeferralEligibility(
                is_eligible=False,
                reason_code=None,
                notes="Real risk of forfeiture does not exist - deferral not available"
            )
        
        # Calculate 15-year date
        fifteen_year_date = date(
            interest.acquisition_date.year + self.MAX_DEFERRAL_YEARS,
            interest.acquisition_date.month,
            interest.acquisition_date.day
        )
        
        # Deferral eligible until earliest of events
        eligible_until = fifteen_year_date
        
        return DeferralEligibility(
            is_eligible=True,
            reason_code=DeferralReasonCode.REAL_RISK_FORFEITURE,
            eligible_until_date=eligible_until,
            notes=(
                f"Deferred taxing point eligible. Real risk of forfeiture applies. "
                f"Taxing point will arise on earliest of: cessation, scheme change, "
                f"disposal, or {eligible_until.strftime('%d %B %Y')} (15 years)"
            )
        )
    
    def calculate_option_exercise(
        self,
        interest: ESSInterest,
        option_details: OptionDetails,
        exercise_scenario: OptionExerciseScenario
    ) -> Dict:
        """
        Calculate taxation position when option is exercised
        
        On exercise, employee acquires shares. Taxing point may arise depending on:
        - Whether deferral applied to the option
        - Type of exercise (standard, cashless, etc.)
        - Market value differences
        
        Args:
            interest: The original option interest
            option_details: Option-specific details
            exercise_scenario: Exercise scenario details
        
        Returns:
            Dictionary with exercise results and taxation position
        """
        if interest.ess_type != ESSType.OPTION:
            raise ValueError("This method only applies to option interests")
        
        # Calculate gain on exercise
        gain_on_exercise = (
            exercise_scenario.market_value_at_exercise * exercise_scenario.shares_acquired
        ) - exercise_scenario.exercise_price_paid
        
        # Determine if deferral was applicable to the option
        deferral_check = self.check_deferred_taxing_point_eligibility(interest)
        
        # Cost base for resulting shares
        cost_base = exercise_scenario.exercise_price_paid + max(Decimal("0"), gain_on_exercise)
        
        return {
            "exercise_date": exercise_scenario.exercise_date,
            "exercise_type": exercise_scenario.exercise_type,
            "shares_acquired": exercise_scenario.shares_acquired,
            "exercise_price_paid": exercise_scenario.exercise_price_paid,
            "market_value_at_exercise": exercise_scenario.market_value_at_exercise,
            "gain_on_exercise": gain_on_exercise,
            "deferral_applied": deferral_check.is_eligible,
            "cost_base": cost_base,
            "cost_base_per_share": cost_base / exercise_scenario.shares_acquired,
            "notes": f"Exercised {exercise_scenario.shares_acquired} shares on {exercise_scenario.exercise_date.strftime('%d %B %Y')}"
        }
    
    def calculate_cgt_cost_base(
        self,
        interest: ESSInterest,
        taxable_discount_info: Optional[TaxableDiscount] = None,
        additional_cost_components: Optional[Dict[str, Decimal]] = None
    ) -> CGTCostBase:
        """
        Calculate cost base for CGT purposes
        
        When taxing point triggers:
        - For discount shares: cost base = amount paid + taxable discount included in income
        - For options exercised: cost base = exercise price paid + taxable gain
        
        Args:
            interest: The ESS interest
            taxable_discount_info: TaxableDiscount information if applicable
            additional_cost_components: Additional cost base components
        
        Returns:
            CGTCostBase with breakdown
        """
        components = {}
        cost_base = Decimal("0")
        
        # Base component: amount paid
        components["amount_paid"] = interest.amount_paid
        cost_base += interest.amount_paid
        
        # Add taxable discount if included in income
        if taxable_discount_info and taxable_discount_info.taxable_discount > 0:
            components["taxable_discount"] = taxable_discount_info.taxable_discount
            cost_base += taxable_discount_info.taxable_discount
        
        # Add any other components
        if additional_cost_components:
            components.update(additional_cost_components)
            cost_base += sum(additional_cost_components.values())
        
        return CGTCostBase(
            acquisition_date=interest.acquisition_date,
            cost_base_amount=cost_base,
            components=components,
            notes="Cost base for CGT purposes when taxing point arises"
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _is_eligible_for_exemption(self, interest: ESSInterest) -> bool:
        """
        Check if interest is eligible for $1,000 exemption
        
        Section 83A-75: Exemption applies to:
        1. Salary sacrifice scheme
        2. Small business scheme
        
        Also requires scheme to meet other conditions (typically satisfied
        if provided as ESS statement from employer)
        """
        if interest.scheme_type in [
            SchemeType.SALARY_SACRIFICE,
            SchemeType.EMPLOYER_CONTRIBUTION,
            SchemeType.SMALL_BUSINESS
        ]:
            return True
        return False
    
    def _generate_exemption_notes(
        self,
        interest: ESSInterest,
        raw_discount: Decimal,
        exemption_applied: Decimal,
        is_eligible: bool
    ) -> str:
        """Generate detailed notes about exemption application"""
        if raw_discount <= 0:
            return "No discount - exemption does not apply"
        
        if not is_eligible:
            scheme_type_name = interest.scheme_type.value
            return (
                f"Scheme type '{scheme_type_name}' is not eligible for $1,000 exemption. "
                f"Full discount of ${raw_discount:,.2f} is taxable."
            )
        
        if exemption_applied == 0:
            return "Interest eligible for exemption but discount is zero"
        
        if exemption_applied == raw_discount:
            return (
                f"Full discount of ${raw_discount:,.2f} covered by $1,000 exemption "
                f"under s 83A-75"
            )
        
        return (
            f"Discount of ${raw_discount:,.2f} exceeds $1,000 exemption. "
            f"Exemption of ${exemption_applied:,.2f} applied, "
            f"taxable discount of ${raw_discount - exemption_applied:,.2f}"
        )
    
    def _years_from_acquisition(self, acquisition_date: date, to_date: date) -> int:
        """Calculate years between acquisition and given date"""
        return to_date.year - acquisition_date.year
    
    # ========================================================================
    # BATCH PROCESSING
    # ========================================================================
    
    def process_statement(
        self,
        statement: ESSStatement,
        current_date: Optional[date] = None
    ) -> Dict:
        """
        Process entire ESS statement and calculate all positions
        
        Args:
            statement: ESSStatement to process
            current_date: Date for calculations
        
        Returns:
            Dictionary with comprehensive tax positions for all interests
        """
        if current_date is None:
            current_date = date.today()
        
        results = {
            "statement_id": statement.statement_id,
            "employer_name": statement.employer_name,
            "tax_year": statement.tax_year,
            "interests": [],
            "summary": {
                "total_raw_discount": Decimal("0"),
                "total_exemption": Decimal("0"),
                "total_taxable_discount": Decimal("0"),
                "total_deferred": Decimal("0"),
                "interests_with_deferred_taxing_point": 0
            }
        }
        
        for interest in statement.interests:
            interest_result = {
                "interest_id": interest.interest_id,
                "type": interest.ess_type.value,
                "acquisition_date": interest.acquisition_date.isoformat(),
                "amount_paid": str(interest.amount_paid),
                "market_value": str(interest.market_value_acquisition)
            }
            
            # Calculate discount if applicable
            if interest.ess_type in [ESSType.DISCOUNT_SHARE, ESSType.RESTRICTED_SHARE]:
                discount_info = self.calculate_taxable_discount(interest, current_date)
                interest_result["discount"] = {
                    "raw_discount": str(discount_info.raw_discount),
                    "exemption_applied": str(discount_info.exemption_applied),
                    "taxable_discount": str(discount_info.taxable_discount),
                    "eligible_for_exemption": discount_info.is_eligible_for_exemption,
                    "notes": discount_info.exemption_notes
                }
                results["summary"]["total_raw_discount"] += discount_info.raw_discount
                results["summary"]["total_exemption"] += discount_info.exemption_applied
                results["summary"]["total_taxable_discount"] += discount_info.taxable_discount
            
            # Check deferral eligibility
            deferral_info = self.check_deferred_taxing_point_eligibility(interest, current_date)
            interest_result["deferred_taxing_point"] = {
                "is_eligible": deferral_info.is_eligible,
                "eligible_until": deferral_info.eligible_until_date.isoformat() if deferral_info.eligible_until_date else None,
                "notes": deferral_info.notes
            }
            
            if deferral_info.is_eligible:
                results["summary"]["interests_with_deferred_taxing_point"] += 1
                if interest.ess_type in [ESSType.DISCOUNT_SHARE, ESSType.RESTRICTED_SHARE]:
                    discount_info = self.calculate_taxable_discount(interest, current_date)
                    results["summary"]["total_deferred"] += discount_info.taxable_discount
            
            results["interests"].append(interest_result)
        
        return results
    
    # ========================================================================
    # TAX RETURN FORMATTING
    # ========================================================================
    
    def format_for_tax_return(
        self,
        statement: ESSStatement,
        current_date: Optional[date] = None,
        tax_year: Optional[str] = None
    ) -> Dict:
        """
        Format ESS information for inclusion in tax return (Section 12)
        
        Output includes:
        - Employee share scheme income (taxable discounts)
        - Deferred taxing point details
        - Employer information
        - Supporting notes for CGT
        
        Args:
            statement: ESSStatement to format
            current_date: Date for calculations
            tax_year: Tax year (e.g., "2024-25") - uses statement if not provided
        
        Returns:
            Dictionary formatted for tax return entry
        """
        if current_date is None:
            current_date = date.today()
        
        if tax_year is None:
            tax_year = statement.tax_year
        
        processed = self.process_statement(statement, current_date)
        
        # Build Section 12 entry
        section_12_entry = {
            "section": 12,
            "income_type": "Employee Share Scheme",
            "tax_year": tax_year,
            "statement_date": statement.statement_date.isoformat(),
            "employer": {
                "name": statement.employer_name,
                "abn": statement.employer_abn
            },
            "income_details": []
        }
        
        # Add income for each interest with taxable amount
        for interest_result in processed["interests"]:
            if "discount" in interest_result:
                discount = interest_result["discount"]
                if discount["taxable_discount"] != "0.00":
                    income_detail = {
                        "interest_id": interest_result["interest_id"],
                        "type": interest_result["type"],
                        "acquisition_date": interest_result["acquisition_date"],
                        "amount_included_in_income": discount["taxable_discount"],
                        "notes": discount["notes"]
                    }
                    
                    # Add deferral info if applicable
                    if interest_result["deferred_taxing_point"]["is_eligible"]:
                        income_detail["deferred_taxing_point_eligible"] = True
                        income_detail["eligible_until"] = interest_result["deferred_taxing_point"]["eligible_until"]
                    
                    section_12_entry["income_details"].append(income_detail)
        
        # Add summary
        section_12_entry["summary"] = {
            "total_income": str(processed["summary"]["total_taxable_discount"]),
            "total_exemptions": str(processed["summary"]["total_exemption"]),
            "total_deferred_interests": processed["summary"]["interests_with_deferred_taxing_point"]
        }
        
        # Add CGT reference
        section_12_entry["cgt_notes"] = (
            "For shares acquired via ESS, cost base is amount paid plus "
            "taxable discount included in income. See Capital Gains Tax section "
            "for disposal calculations."
        )
        
        return section_12_entry


# ============================================================================
# FACTORY/BUILDER
# ============================================================================

class ESSStatementBuilder:
    """Builder pattern for constructing ESS statements"""
    
    def __init__(self, statement_id: str, employer_name: str, employer_abn: str):
        self.statement = ESSStatement(
            statement_id=statement_id,
            employer_name=employer_name,
            employer_abn=employer_abn,
            statement_date=date.today(),
            tax_year="2024-25"
        )
    
    def with_statement_date(self, statement_date: date) -> "ESSStatementBuilder":
        self.statement.statement_date = statement_date
        return self
    
    def with_tax_year(self, tax_year: str) -> "ESSStatementBuilder":
        self.statement.tax_year = tax_year
        return self
    
    def add_discount_share(
        self,
        interest_id: str,
        plan_name: str,
        acquisition_date: date,
        amount_paid: Decimal,
        market_value: Decimal,
        scheme_type: SchemeType = SchemeType.GENERAL,
        has_rrof: bool = False
    ) -> "ESSStatementBuilder":
        """Add discount share interest"""
        interest = ESSInterest(
            interest_id=interest_id,
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=scheme_type,
            acquisition_date=acquisition_date,
            amount_paid=amount_paid,
            market_value_acquisition=market_value,
            employer_name=self.statement.employer_name,
            plan_name=plan_name,
            has_real_risk_forfeiture=has_rrof
        )
        self.statement.add_interest(interest)
        return self
    
    def add_option(
        self,
        interest_id: str,
        plan_name: str,
        acquisition_date: date,
        exercise_price: Decimal,
        number_of_shares: int,
        scheme_type: SchemeType = SchemeType.GENERAL,
        has_rrof: bool = False
    ) -> "ESSStatementBuilder":
        """Add option interest"""
        interest = ESSInterest(
            interest_id=interest_id,
            ess_type=ESSType.OPTION,
            scheme_type=scheme_type,
            acquisition_date=acquisition_date,
            amount_paid=Decimal("0"),  # Options typically granted
            market_value_acquisition=Decimal("0"),
            employer_name=self.statement.employer_name,
            plan_name=plan_name,
            has_real_risk_forfeiture=has_rrof
        )
        self.statement.add_interest(interest)
        return self
    
    def build(self) -> ESSStatement:
        return self.statement


# ============================================================================
# VALIDATION
# ============================================================================

class ESSValidator:
    """Validation utilities for ESS data"""
    
    @staticmethod
    def validate_statement(statement: ESSStatement) -> List[str]:
        """
        Validate ESS statement for completeness and consistency
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not statement.interests:
            errors.append("Statement contains no interests")
        
        if not statement.employer_abn or len(statement.employer_abn) != 11:
            errors.append("Invalid or missing employer ABN (must be 11 digits)")
        
        for interest in statement.interests:
            interest_errors = ESSValidator.validate_interest(interest)
            errors.extend(interest_errors)
        
        return errors
    
    @staticmethod
    def validate_interest(interest: ESSInterest) -> List[str]:
        """Validate individual interest"""
        errors = []
        
        if interest.amount_paid > interest.market_value_acquisition and interest.ess_type == ESSType.DISCOUNT_SHARE:
            errors.append(
                f"Interest {interest.interest_id}: Amount paid cannot exceed "
                f"market value for discount share"
            )
        
        if interest.acquisition_date > date.today():
            errors.append(
                f"Interest {interest.interest_id}: Acquisition date cannot be in future"
            )
        
        return errors


if __name__ == "__main__":
    """Example usage and demonstration"""
    
    # Create a statement with discount shares
    builder = ESSStatementBuilder(
        statement_id="STMT-2024-001",
        employer_name="TechCorp Australia Pty Ltd",
        employer_abn="12345678901"
    )
    
    # Add discount share - salary sacrifice scheme (eligible for $1,000 exemption)
    builder.add_discount_share(
        interest_id="SHARE-001",
        plan_name="TechCorp Salary Sacrifice Share Plan",
        acquisition_date=date(2023, 7, 15),
        amount_paid=Decimal("5000.00"),
        market_value=Decimal("7500.00"),
        scheme_type=SchemeType.SALARY_SACRIFICE,
        has_rrof=True
    )
    
    # Add option
    builder.add_option(
        interest_id="OPTION-001",
        plan_name="TechCorp Executive Option Plan",
        acquisition_date=date(2022, 1, 1),
        exercise_price=Decimal("15.00"),
        number_of_shares=1000,
        scheme_type=SchemeType.GENERAL,
        has_rrof=True
    )
    
    statement = builder.build()
    
    # Process statement
    service = ESSService()
    tax_return_format = service.format_for_tax_return(statement)
    
    # Print results
    import json
    print(json.dumps(tax_return_format, indent=2, default=str))
