"""
Comprehensive test scenarios for CORE CALCULATION services - ATO Tax Agent
Test file: test_layer1_service.py

This module tests Layer 1 processing including:
- Income aggregation and classification
- Gross income calculation
- Medicare levy threshold calculations
- Assessable income computation
- Income source verification and validation

Layer 1 Processing:
- Aggregates all income sources (employment, investment, other)
- Calculates gross income
- Determines Medicare levy thresholds
- Prepares assessable income calculation
- Validates income sources and amounts

ATO 2024-25 Rules:
- Medicare Levy: 2% standard (exemptions/reductions apply)
- Individual threshold: ~$21,845 (indexed)
- Couples/families: Different thresholds
- Work-related allowances and reimbursements can be excluded
"""

import pytest
from decimal import Decimal
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import datetime, date


class IncomeSourceType(Enum):
    """Types of income sources"""
    SALARY = "salary"
    WAGES = "wages"
    INTEREST = "interest"
    DIVIDENDS = "dividends"
    RENTAL = "rental"
    BUSINESS = "business"
    CAPITAL_GAINS = "capital_gains"
    ALLOWANCES = "allowances"
    SUPERANNUATION = "superannuation"
    OTHER = "other"


class TaxResidencyStatus(Enum):
    """Tax residency status"""
    AUSTRALIAN_RESIDENT = "australian_resident"
    NON_RESIDENT = "non_resident"
    TEMPORARY_RESIDENT = "temporary_resident"


@dataclass
class IncomeSource:
    """Represents a single income source"""
    source_type: IncomeSourceType
    amount: Decimal
    description: str
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    tax_withheld: Decimal = Decimal('0')
    is_assessable: bool = True
    notes: str = ""


@dataclass
class TaxpayerProfile:
    """Taxpayer profile for Layer 1 processing"""
    name: str
    tax_file_number: Optional[str] = None
    tax_residency_status: TaxResidencyStatus = TaxResidencyStatus.AUSTRALIAN_RESIDENT
    age: Optional[int] = None
    spouse_income: Optional[Decimal] = None
    has_dependants: bool = False
    num_dependants: int = 0
    financial_year_start: date = field(default_factory=lambda: date(2024, 7, 1))
    financial_year_end: date = field(default_factory=lambda: date(2025, 6, 30))


@dataclass
class Layer1ProcessingInput:
    """Input for Layer 1 processing"""
    taxpayer: TaxpayerProfile
    income_sources: List[IncomeSource]
    adjustments: Dict[str, Decimal] = field(default_factory=dict)


@dataclass
class Layer1ProcessingResult:
    """Result from Layer 1 processing"""
    total_gross_income: Decimal
    income_by_source: Dict[str, Decimal]
    total_assessable_income: Decimal
    non_assessable_amounts: Dict[str, Decimal]
    medicare_levy_threshold: Decimal
    exceeds_medicare_threshold: bool
    income_validation: Dict[str, bool]
    warnings: List[str] = field(default_factory=list)


class MockLayer1Service:
    """Mock implementation of Layer 1 service"""
    
    # Medicare Levy thresholds (2024-25)
    MEDICARE_LEVY_SINGLE_THRESHOLD = Decimal('21845')
    MEDICARE_LEVY_COUPLE_THRESHOLD = Decimal('43690')
    MEDICARE_LEVY_FAMILY_THRESHOLD = Decimal('51885')
    MEDICARE_LEVY_EACH_CHILD = Decimal('3005')
    
    # Non-assessable allowances (examples)
    NON_ASSESSABLE_ALLOWANCES = {
        'fbt_exempt_allowance': True,
        'reimbursement': True,
        'employer_contribution_super': True,
    }
    
    def process_layer1(self, input_data: Layer1ProcessingInput) -> Layer1ProcessingResult:
        """Process Layer 1 - income aggregation and initial calculations"""
        
        # Aggregate income sources
        total_gross_income = Decimal('0')
        income_by_source = {}
        non_assessable_amounts = {}
        validation_results = {}
        warnings = []
        
        for source in input_data.income_sources:
            # Validate income amount
            validation_results[source.description] = self._validate_income_source(source)
            
            if source.is_assessable:
                income_by_source[source.description] = source.amount
                total_gross_income += source.amount
            else:
                non_assessable_amounts[source.description] = source.amount
        
        # Calculate assessable income (excluding non-assessable)
        total_assessable_income = total_gross_income
        
        # Apply adjustments if any
        for adj_name, adj_amount in input_data.adjustments.items():
            total_assessable_income += adj_amount
        
        # Determine Medicare levy threshold
        medicare_threshold = self._get_medicare_levy_threshold(input_data.taxpayer)
        exceeds_threshold = total_gross_income > medicare_threshold
        
        # Add warnings for anomalies
        if total_gross_income == Decimal('0'):
            warnings.append("No income reported")
        
        if total_gross_income < Decimal('0'):
            warnings.append("Negative income detected - may indicate loss or adjustment")
        
        return Layer1ProcessingResult(
            total_gross_income=total_gross_income,
            income_by_source=income_by_source,
            total_assessable_income=total_assessable_income,
            non_assessable_amounts=non_assessable_amounts,
            medicare_levy_threshold=medicare_threshold,
            exceeds_medicare_threshold=exceeds_threshold,
            income_validation=validation_results,
            warnings=warnings
        )
    
    def aggregate_income_sources(self, sources: List[IncomeSource]) -> Decimal:
        """Aggregate all assessable income sources"""
        total = Decimal('0')
        for source in sources:
            if source.is_assessable:
                total += source.amount
        return total
    
    def classify_income_sources(self, sources: List[IncomeSource]) -> Dict[IncomeSourceType, Decimal]:
        """Classify and group income by source type"""
        classified = {}
        for source in sources:
            if source.source_type not in classified:
                classified[source.source_type] = Decimal('0')
            if source.is_assessable:
                classified[source.source_type] += source.amount
        return classified
    
    def calculate_gross_income(self, sources: List[IncomeSource]) -> Decimal:
        """Calculate gross income from all sources"""
        return self.aggregate_income_sources(sources)
    
    def get_medicare_levy_threshold(self, taxpayer: TaxpayerProfile) -> Decimal:
        """Get Medicare levy threshold for taxpayer"""
        return self._get_medicare_levy_threshold(taxpayer)
    
    def _get_medicare_levy_threshold(self, taxpayer: TaxpayerProfile) -> Decimal:
        """Internal method to get Medicare levy threshold"""
        if taxpayer.spouse_income is not None:
            # Couple threshold
            if taxpayer.has_dependants:
                # Family threshold
                return (self.MEDICARE_LEVY_FAMILY_THRESHOLD + 
                       (self.MEDICARE_LEVY_EACH_CHILD * taxpayer.num_dependants))
            else:
                return self.MEDICARE_LEVY_COUPLE_THRESHOLD
        else:
            # Single threshold
            if taxpayer.has_dependants:
                # Single with dependants
                return (self.MEDICARE_LEVY_SINGLE_THRESHOLD +
                       (self.MEDICARE_LEVY_EACH_CHILD * taxpayer.num_dependants))
            else:
                return self.MEDICARE_LEVY_SINGLE_THRESHOLD
    
    def calculate_medicare_levy(self, gross_income: Decimal, 
                               threshold: Decimal) -> Decimal:
        """Calculate Medicare levy (2% of income above threshold)"""
        if gross_income <= threshold:
            return Decimal('0')
        
        assessable_income = gross_income - threshold
        return assessable_income * Decimal('0.02')
    
    def validate_income_sources(self, sources: List[IncomeSource]) -> Dict[str, bool]:
        """Validate all income sources"""
        validation = {}
        for source in sources:
            validation[source.description] = self._validate_income_source(source)
        return validation
    
    def _validate_income_source(self, source: IncomeSource) -> bool:
        """Validate a single income source"""
        # Check amount is not negative (unless it's a business loss)
        if source.amount < Decimal('0') and source.source_type != IncomeSourceType.BUSINESS:
            return False
        
        # Check amount is reasonable (not NaN or inf)
        if source.amount == float('inf') or source.amount == float('-inf'):
            return False
        
        return True
    
    def reconcile_income_sources(self, sources: List[IncomeSource], 
                                gross_income_reported: Decimal) -> bool:
        """Verify reported income matches sum of sources"""
        calculated_total = self.aggregate_income_sources(sources)
        return calculated_total == gross_income_reported


# Test fixtures
@pytest.fixture
def layer1_service():
    """Fixture providing Layer 1 service instance"""
    return MockLayer1Service()


@pytest.fixture
def basic_taxpayer():
    """Fixture providing basic taxpayer profile"""
    return TaxpayerProfile(
        name="Test Taxpayer",
        tax_residency_status=TaxResidencyStatus.AUSTRALIAN_RESIDENT,
        age=35,
        spouse_income=None,
        has_dependants=False
    )


# Normal cases - typical income scenarios
class TestLayer1ServiceNormalCases:
    """Test normal/typical income scenarios"""
    
    def test_single_income_source(self, layer1_service, basic_taxpayer):
        """
        Test: Single income source (salary)
        Scenario: Taxpayer with salary income of $50,000
        Expected: Gross income = $50,000, assessable income = $50,000
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('50000'),
                description="Annual salary"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('50000')
        assert result.total_assessable_income == Decimal('50000')
        assert len(result.income_by_source) == 1
    
    def test_multiple_income_sources(self, layer1_service, basic_taxpayer):
        """
        Test: Multiple income sources
        Scenario: Salary + Interest + Dividends
        Expected: Income aggregated correctly
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('70000'),
                description="Annual salary"
            ),
            IncomeSource(
                source_type=IncomeSourceType.INTEREST,
                amount=Decimal('2000'),
                description="Bank interest"
            ),
            IncomeSource(
                source_type=IncomeSourceType.DIVIDENDS,
                amount=Decimal('3000'),
                description="Dividend income"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('75000')
        assert result.total_assessable_income == Decimal('75000')
        assert len(result.income_by_source) == 3
    
    def test_income_below_medicare_threshold(self, layer1_service, basic_taxpayer):
        """
        Test: Income below Medicare levy threshold
        Scenario: Income of $20,000 (below $21,845 threshold)
        Expected: Exceeds threshold = False
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.WAGES,
                amount=Decimal('20000'),
                description="Part-time wages"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('20000')
        assert result.exceeds_medicare_threshold == False
    
    def test_income_above_medicare_threshold(self, layer1_service, basic_taxpayer):
        """
        Test: Income above Medicare levy threshold
        Scenario: Income of $60,000
        Expected: Exceeds threshold = True
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('60000'),
                description="Annual salary"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('60000')
        assert result.exceeds_medicare_threshold == True
    
    def test_non_assessable_income(self, layer1_service, basic_taxpayer):
        """
        Test: Non-assessable income excluded
        Scenario: Salary + non-assessable reimbursement
        Expected: Reimbursement not counted as assessable income
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('50000'),
                description="Annual salary",
                is_assessable=True
            ),
            IncomeSource(
                source_type=IncomeSourceType.ALLOWANCES,
                amount=Decimal('5000'),
                description="Reimbursement",
                is_assessable=False
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('50000')
        assert len(result.non_assessable_amounts) == 1
        assert result.non_assessable_amounts['Reimbursement'] == Decimal('5000')


# Edge cases - boundary conditions
class TestLayer1ServiceEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_income(self, layer1_service, basic_taxpayer):
        """
        Test: Zero income
        Expected: No income, warning generated
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('0'),
                description="No income"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('0')
        assert result.exceeds_medicare_threshold == False
        assert len(result.warnings) > 0
    
    def test_no_income_sources(self, layer1_service, basic_taxpayer):
        """
        Test: No income sources provided
        Expected: Gross income = $0
        """
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=[]
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('0')
        assert result.total_assessable_income == Decimal('0')
    
    def test_medicare_threshold_single(self, layer1_service, basic_taxpayer):
        """
        Test: Income exactly at Medicare levy threshold
        Expected: Threshold = $21,845
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('21845'),
                description="Annual salary"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.medicare_levy_threshold == Decimal('21845')
        assert result.total_gross_income == Decimal('21845')
        # At threshold, doesn't exceed
        assert result.exceeds_medicare_threshold == False
    
    def test_medicare_threshold_one_dollar_above(self, layer1_service, basic_taxpayer):
        """
        Test: Income $1 above Medicare levy threshold
        Expected: Exceeds threshold = True
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('21846'),
                description="Annual salary"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.exceeds_medicare_threshold == True
    
    def test_couple_medicare_threshold(self, layer1_service):
        """
        Test: Couple Medicare levy threshold
        Expected: Threshold = $43,690
        """
        couple_taxpayer = TaxpayerProfile(
            name="Couple Taxpayer",
            spouse_income=Decimal('50000'),
            has_dependants=False
        )
        
        threshold = layer1_service.get_medicare_levy_threshold(couple_taxpayer)
        
        assert threshold == Decimal('43690')
    
    def test_family_medicare_threshold(self, layer1_service):
        """
        Test: Family Medicare levy threshold
        Scenario: Single parent with 2 dependants
        Expected: Threshold = $21,845 + (2 * $3,005)
        """
        family_taxpayer = TaxpayerProfile(
            name="Family Taxpayer",
            spouse_income=None,
            has_dependants=True,
            num_dependants=2
        )
        
        threshold = layer1_service.get_medicare_levy_threshold(family_taxpayer)
        
        expected = Decimal('21845') + (Decimal('3005') * 2)
        assert threshold == expected


# ATO-specific rules and scenarios
class TestLayer1ServiceATOSpecificRules:
    """Test ATO-specific rules for Layer 1 processing"""
    
    def test_income_classification(self, layer1_service):
        """
        Test: Income classification by source type
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('70000'),
                description="Salary"
            ),
            IncomeSource(
                source_type=IncomeSourceType.INTEREST,
                amount=Decimal('2000'),
                description="Interest"
            ),
            IncomeSource(
                source_type=IncomeSourceType.RENTAL,
                amount=Decimal('5000'),
                description="Rental"
            )
        ]
        
        classified = layer1_service.classify_income_sources(sources)
        
        assert classified[IncomeSourceType.SALARY] == Decimal('70000')
        assert classified[IncomeSourceType.INTEREST] == Decimal('2000')
        assert classified[IncomeSourceType.RENTAL] == Decimal('5000')
    
    def test_medicare_levy_calculation(self, layer1_service, basic_taxpayer):
        """
        Test: Medicare levy calculation (2% of income above threshold)
        Scenario: Income $60,000, threshold $21,845
        Expected: Medicare levy = ($60,000 - $21,845) * 2% = $762.30
        """
        threshold = layer1_service.get_medicare_levy_threshold(basic_taxpayer)
        gross_income = Decimal('60000')
        
        levy = layer1_service.calculate_medicare_levy(gross_income, threshold)
        
        expected = (gross_income - threshold) * Decimal('0.02')
        assert levy == expected
    
    def test_business_loss_allowed(self, layer1_service, basic_taxpayer):
        """
        Test: Business loss (negative amount) is valid
        Scenario: Salary $50,000 + Business loss ($10,000)
        Expected: Negative business income is valid
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('50000'),
                description="Salary"
            ),
            IncomeSource(
                source_type=IncomeSourceType.BUSINESS,
                amount=Decimal('-10000'),
                description="Business loss"
            )
        ]
        
        validation = layer1_service.validate_income_sources(sources)
        
        assert validation['Salary'] == True
        assert validation['Business loss'] == True
        
        total_income = layer1_service.aggregate_income_sources(sources)
        assert total_income == Decimal('40000')
    
    def test_australian_resident_vs_non_resident(self, layer1_service):
        """
        Test: Tax residency status recorded
        """
        resident_taxpayer = TaxpayerProfile(
            name="Resident",
            tax_residency_status=TaxResidencyStatus.AUSTRALIAN_RESIDENT
        )
        
        non_resident_taxpayer = TaxpayerProfile(
            name="Non-resident",
            tax_residency_status=TaxResidencyStatus.NON_RESIDENT
        )
        
        assert resident_taxpayer.tax_residency_status == TaxResidencyStatus.AUSTRALIAN_RESIDENT
        assert non_resident_taxpayer.tax_residency_status == TaxResidencyStatus.NON_RESIDENT


# Complex scenarios
class TestLayer1ServiceComplexScenarios:
    """Test complex realistic scenarios"""
    
    def test_complex_family_scenario(self, layer1_service):
        """
        Test: Complex family scenario
        Scenario:
        - Primary earner: $85,000 salary
        - Investment income: $5,000 (interest + dividends)
        - Partner income: $60,000
        - 2 dependants
        Expected: Correct aggregation and Medicare threshold
        """
        taxpayer = TaxpayerProfile(
            name="Family Taxpayer",
            spouse_income=Decimal('60000'),
            has_dependants=True,
            num_dependants=2
        )
        
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('85000'),
                description="Primary salary"
            ),
            IncomeSource(
                source_type=IncomeSourceType.INTEREST,
                amount=Decimal('2500'),
                description="Interest"
            ),
            IncomeSource(
                source_type=IncomeSourceType.DIVIDENDS,
                amount=Decimal('2500'),
                description="Dividends"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('90000')
        assert result.total_assessable_income == Decimal('90000')
        
        # Medicare threshold for couple with 2 dependants
        expected_threshold = Decimal('43690') + (Decimal('3005') * 2)
        assert result.medicare_levy_threshold == expected_threshold
        assert result.exceeds_medicare_threshold == True
    
    def test_mixed_assessable_non_assessable(self, layer1_service, basic_taxpayer):
        """
        Test: Mix of assessable and non-assessable income
        Scenario: Salary + expense reimbursement + employer super contribution
        Expected: Only assessable income counted
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('60000'),
                description="Salary",
                is_assessable=True
            ),
            IncomeSource(
                source_type=IncomeSourceType.ALLOWANCES,
                amount=Decimal('3000'),
                description="Expense reimbursement",
                is_assessable=False
            ),
            IncomeSource(
                source_type=IncomeSourceType.SUPERANNUATION,
                amount=Decimal('9900'),
                description="Employer super contribution",
                is_assessable=False
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == Decimal('60000')
        assert result.total_assessable_income == Decimal('60000')
        assert len(result.non_assessable_amounts) == 2


# Validation and error handling
class TestLayer1ServiceValidation:
    """Test validation and error handling"""
    
    def test_income_validation(self, layer1_service):
        """
        Test: Income source validation
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('50000'),
                description="Valid salary"
            ),
            IncomeSource(
                source_type=IncomeSourceType.INTEREST,
                amount=Decimal('-500'),
                description="Invalid interest (negative)"
            )
        ]
        
        validation = layer1_service.validate_income_sources(sources)
        
        assert validation['Valid salary'] == True
        assert validation['Invalid interest (negative)'] == False
    
    def test_income_reconciliation(self, layer1_service):
        """
        Test: Reconcile calculated vs reported income
        """
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=Decimal('50000'),
                description="Salary"
            ),
            IncomeSource(
                source_type=IncomeSourceType.INTEREST,
                amount=Decimal('2000'),
                description="Interest"
            )
        ]
        
        # Correct reconciliation
        assert layer1_service.reconcile_income_sources(sources, Decimal('52000')) == True
        
        # Incorrect reconciliation
        assert layer1_service.reconcile_income_sources(sources, Decimal('50000')) == False


# Parametrized tests for comprehensive coverage
class TestLayer1ServiceParametrized:
    """Parametrized tests for comprehensive coverage"""
    
    @pytest.mark.parametrize("income,expected_exceeds", [
        (Decimal('10000'), False),
        (Decimal('21844'), False),
        (Decimal('21845'), False),
        (Decimal('21846'), True),
        (Decimal('50000'), True),
        (Decimal('100000'), True),
    ])
    def test_medicare_threshold_various_incomes(self, layer1_service, basic_taxpayer, 
                                                income, expected_exceeds):
        """Test Medicare threshold determination for various income levels"""
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY,
                amount=income,
                description="Salary"
            )
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.exceeds_medicare_threshold == expected_exceeds
    
    @pytest.mark.parametrize("num_sources,source_amounts,expected_total", [
        (1, [Decimal('50000')], Decimal('50000')),
        (2, [Decimal('50000'), Decimal('10000')], Decimal('60000')),
        (3, [Decimal('50000'), Decimal('2000'), Decimal('3000')], Decimal('55000')),
        (4, [Decimal('60000'), Decimal('2000'), Decimal('3000'), Decimal('5000')], Decimal('70000')),
    ])
    def test_multiple_income_aggregation(self, layer1_service, basic_taxpayer, 
                                        num_sources, source_amounts, expected_total):
        """Test aggregation of multiple income sources"""
        sources = [
            IncomeSource(
                source_type=IncomeSourceType.SALARY if i == 0 else IncomeSourceType.INTEREST,
                amount=amount,
                description=f"Income source {i+1}"
            )
            for i, amount in enumerate(source_amounts)
        ]
        
        input_data = Layer1ProcessingInput(
            taxpayer=basic_taxpayer,
            income_sources=sources
        )
        
        result = layer1_service.process_layer1(input_data)
        
        assert result.total_gross_income == expected_total


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
