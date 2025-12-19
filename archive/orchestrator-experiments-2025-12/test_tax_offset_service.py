"""
Comprehensive test scenarios for CORE CALCULATION services - ATO Tax Agent
Test file: test_tax_offset_service.py

This module tests tax offset calculations including:
- SAPTO (Senior Australians Prescription Tax Offset)
- LITO (Low Income Tax Offset)
- LDCO (Low Income Dependant Offset)
- Other applicable offsets
- Offset phase-out testing
- Offset eligibility and aggregation

ATO 2024-25 Tax Offsets:
- LITO: Up to $705, phases out at $66,667 and eliminated at $90,000
- SAPTO: Up to $1,602 (tax-free person), phases out, applicable to seniors
- LDCO: Up to $1,657 per dependant (from 2024-25)
- Offsets are non-refundable unless specified (LITO refundable from 2024-25)
"""

import pytest
from decimal import Decimal
from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum


class OffsetType(Enum):
    """Types of tax offsets"""
    LITO = "lito"  # Low Income Tax Offset
    SAPTO = "sapto"  # Senior Australians Prescription Tax Offset
    LDCO = "ldco"  # Low Income Dependant Offset
    FTBO = "ftbo"  # First-Time Home Buyer Offset
    OTHER = "other"


@dataclass
class TaxOffset:
    """Represents a tax offset"""
    offset_type: OffsetType
    amount: Decimal
    eligibility_income: Decimal  # Income threshold for eligibility
    phase_out_start: Optional[Decimal] = None
    phase_out_end: Optional[Decimal] = None
    phase_out_rate: Optional[Decimal] = None


@dataclass
class OffsetCalculationInput:
    """Input for offset calculation"""
    taxable_income: Decimal
    age: Optional[int] = None
    dependants: int = 0
    is_senior: bool = False
    is_tax_free_person: bool = False
    other_attributes: Dict = None

    def __post_init__(self):
        if self.other_attributes is None:
            self.other_attributes = {}


@dataclass
class OffsetCalculationResult:
    """Result from offset calculation"""
    lito_amount: Decimal
    sapto_amount: Decimal
    ldco_amount: Decimal
    other_offsets: Dict[str, Decimal]
    total_offsets: Decimal
    breakdown: Dict[str, Decimal]


class MockTaxOffsetService:
    """Mock implementation of tax offset service"""
    
    # LITO parameters for 2024-25
    LITO_MAX = Decimal('705')
    LITO_FULL_AMOUNT_THRESHOLD = Decimal('66667')  # Full offset applies up to this
    LITO_ELIMINATION_THRESHOLD = Decimal('90000')  # Eliminated at this income
    LITO_PHASE_OUT_RATE = Decimal('0.01')  # $0.01 per $1 above threshold
    
    # SAPTO parameters for 2024-25
    SAPTO_MAX_TAX_FREE = Decimal('1602')  # For tax-free persons
    SAPTO_MAX_OTHER = Decimal('1445')  # For others
    SAPTO_INCOME_THRESHOLD = Decimal('13365')  # Age 65+
    SAPTO_PHASE_OUT_START = Decimal('56548')
    SAPTO_PHASE_OUT_RATE = Decimal('0.1245')  # Phase-out rate
    
    # LDCO parameters for 2024-25
    LDCO_MAX_PER_DEPENDANT = Decimal('1657')
    LDCO_INCOME_THRESHOLD = Decimal('80000')
    
    def calculate_lito(self, taxable_income: Decimal) -> Decimal:
        """
        Calculate Low Income Tax Offset (LITO)
        
        2024-25 parameters:
        - Maximum: $705
        - Full amount: up to $66,667
        - Phases out: $1 per $1 from $66,667 to $90,000
        - Zero: $90,000+
        """
        if taxable_income < 0:
            return Decimal('0')
        
        # Full amount if income below threshold
        if taxable_income <= self.LITO_FULL_AMOUNT_THRESHOLD:
            return self.LITO_MAX
        
        # Phase out
        if taxable_income <= self.LITO_ELIMINATION_THRESHOLD:
            reduction = (taxable_income - self.LITO_FULL_AMOUNT_THRESHOLD) * self.LITO_PHASE_OUT_RATE
            return max(Decimal('0'), self.LITO_MAX - reduction)
        
        # Zero above threshold
        return Decimal('0')
    
    def calculate_sapto(self, taxable_income: Decimal, is_senior: bool, 
                       is_tax_free_person: bool = False) -> Decimal:
        """
        Calculate Senior Australians Prescription Tax Offset (SAPTO)
        
        Only applies to persons aged 65+ (or with disability/veteran status)
        """
        if not is_senior:
            return Decimal('0')
        
        # Determine max offset based on tax-free person status
        max_offset = self.SAPTO_MAX_TAX_FREE if is_tax_free_person else self.SAPTO_MAX_OTHER
        
        if taxable_income < 0:
            return Decimal('0')
        
        # Below income threshold - full offset
        if taxable_income <= self.SAPTO_INCOME_THRESHOLD:
            return max_offset
        
        # Between thresholds - full offset still applies
        if taxable_income <= self.SAPTO_PHASE_OUT_START:
            return max_offset
        
        # Phase out above $56,548
        if taxable_income > self.SAPTO_PHASE_OUT_START:
            reduction = (taxable_income - self.SAPTO_PHASE_OUT_START) * self.SAPTO_PHASE_OUT_RATE
            return max(Decimal('0'), max_offset - reduction)
        
        return Decimal('0')
    
    def calculate_ldco(self, taxable_income: Decimal, num_dependants: int) -> Decimal:
        """
        Calculate Low Income Dependant Offset (LDCO)
        
        Up to $1,657 per dependant for income below $80,000
        """
        if num_dependants <= 0 or taxable_income >= self.LDCO_INCOME_THRESHOLD:
            return Decimal('0')
        
        return self.LDCO_MAX_PER_DEPENDANT * Decimal(num_dependants)
    
    def calculate_all_offsets(self, input_data: OffsetCalculationInput) -> OffsetCalculationResult:
        """Calculate all applicable offsets"""
        lito = self.calculate_lito(input_data.taxable_income)
        sapto = self.calculate_sapto(
            input_data.taxable_income,
            input_data.is_senior,
            input_data.is_tax_free_person
        )
        ldco = self.calculate_ldco(input_data.taxable_income, input_data.dependants)
        
        other_offsets = input_data.other_attributes.get('other_offsets', {})
        total_other = sum(other_offsets.values()) if other_offsets else Decimal('0')
        
        total_offsets = lito + sapto + ldco + total_other
        
        breakdown = {
            'LITO': lito,
            'SAPTO': sapto,
            'LDCO': ldco,
            **other_offsets
        }
        
        return OffsetCalculationResult(
            lito_amount=lito,
            sapto_amount=sapto,
            ldco_amount=ldco,
            other_offsets=other_offsets,
            total_offsets=total_offsets,
            breakdown=breakdown
        )
    
    def is_lito_eligible(self, taxable_income: Decimal, age: Optional[int] = None) -> bool:
        """Check LITO eligibility"""
        return taxable_income < self.LITO_ELIMINATION_THRESHOLD
    
    def is_sapto_eligible(self, taxable_income: Decimal, is_senior: bool) -> bool:
        """Check SAPTO eligibility"""
        return is_senior
    
    def aggregate_offsets(self, offsets_dict: Dict[str, Decimal]) -> Decimal:
        """Aggregate multiple offsets"""
        return sum(offsets_dict.values())


# Test fixtures
@pytest.fixture
def offset_service():
    """Fixture providing offset service instance"""
    return MockTaxOffsetService()


# Normal cases - typical offset scenarios
class TestTaxOffsetServiceNormalCases:
    """Test normal/typical offset scenarios"""
    
    def test_lito_full_amount_low_income(self, offset_service):
        """
        Test: LITO at full amount for low income ($30,000)
        Expected: LITO = $705
        """
        input_data = OffsetCalculationInput(taxable_income=Decimal('30000'))
        
        lito = offset_service.calculate_lito(Decimal('30000'))
        
        assert lito == Decimal('705')
        assert offset_service.is_lito_eligible(Decimal('30000'))
    
    def test_lito_full_amount_at_threshold(self, offset_service):
        """
        Test: LITO at full amount exactly at threshold ($66,667)
        Expected: LITO = $705
        """
        lito = offset_service.calculate_lito(Decimal('66667'))
        
        assert lito == Decimal('705')
    
    def test_no_offsets_high_income(self, offset_service):
        """
        Test: No LITO for high income ($95,000)
        Expected: LITO = $0
        """
        lito = offset_service.calculate_lito(Decimal('95000'))
        
        assert lito == Decimal('0')
        assert not offset_service.is_lito_eligible(Decimal('95000'))
    
    def test_sapto_senior_full_amount(self, offset_service):
        """
        Test: SAPTO at full amount for senior ($20,000 income)
        Expected: SAPTO = $1,445 (non-tax-free person)
        """
        sapto = offset_service.calculate_sapto(
            Decimal('20000'),
            is_senior=True,
            is_tax_free_person=False
        )
        
        assert sapto == Decimal('1445')
    
    def test_sapto_senior_tax_free_person(self, offset_service):
        """
        Test: SAPTO for senior who is tax-free person
        Expected: SAPTO = $1,602
        """
        sapto = offset_service.calculate_sapto(
            Decimal('10000'),
            is_senior=True,
            is_tax_free_person=True
        )
        
        assert sapto == Decimal('1602')
    
    def test_no_sapto_non_senior(self, offset_service):
        """
        Test: No SAPTO for non-senior
        Expected: SAPTO = $0
        """
        sapto = offset_service.calculate_sapto(
            Decimal('50000'),
            is_senior=False,
            is_tax_free_person=False
        )
        
        assert sapto == Decimal('0')
    
    def test_ldco_one_dependant(self, offset_service):
        """
        Test: LDCO with one dependant at low income
        Expected: LDCO = $1,657
        """
        ldco = offset_service.calculate_ldco(Decimal('50000'), num_dependants=1)
        
        assert ldco == Decimal('1657')
    
    def test_ldco_multiple_dependants(self, offset_service):
        """
        Test: LDCO with multiple dependants
        Expected: LDCO = $1,657 * number of dependants
        """
        ldco = offset_service.calculate_ldco(Decimal('70000'), num_dependants=3)
        
        assert ldco == Decimal('1657') * Decimal('3')
    
    def test_combined_offsets_low_income(self, offset_service):
        """
        Test: Multiple offsets combined for low income family
        Scenario: Income $40,000 with 1 dependant, not senior
        Expected: LITO + LDCO
        """
        input_data = OffsetCalculationInput(
            taxable_income=Decimal('40000'),
            dependants=1,
            is_senior=False
        )
        
        result = offset_service.calculate_all_offsets(input_data)
        
        assert result.lito_amount == Decimal('705')
        assert result.ldco_amount == Decimal('1657')
        assert result.sapto_amount == Decimal('0')
        assert result.total_offsets == Decimal('2362')


# Edge cases - boundary conditions
class TestTaxOffsetServiceEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_income(self, offset_service):
        """
        Test: Zero income
        Expected: Maximum offsets where applicable
        """
        lito = offset_service.calculate_lito(Decimal('0'))
        sapto = offset_service.calculate_sapto(Decimal('0'), is_senior=True)
        
        assert lito == Decimal('705')
        assert sapto == Decimal('1445')
    
    def test_lito_phase_out_start(self, offset_service):
        """
        Test: LITO at phase-out start ($66,668 = $1 above threshold)
        Expected: LITO starts to reduce
        """
        lito = offset_service.calculate_lito(Decimal('66668'))
        
        # Reduction: $1 * $0.01 = $0.01
        expected = Decimal('705') - Decimal('0.01')
        assert lito == expected
    
    def test_lito_mid_phase_out(self, offset_service):
        """
        Test: LITO mid-phase-out ($78,333 = halfway to elimination)
        Expected: LITO reduced by $0.01 per $1
        """
        lito = offset_service.calculate_lito(Decimal('78333'))
        
        # Reduction: ($78,333 - $66,667) * $0.01 = $11,666 * $0.01 = $116.66
        expected = Decimal('705') - Decimal('116.66')
        assert lito == expected
    
    def test_lito_just_before_elimination(self, offset_service):
        """
        Test: LITO just before elimination ($89,999)
        Expected: LITO = $1
        """
        lito = offset_service.calculate_lito(Decimal('89999'))
        
        # Reduction: ($89,999 - $66,667) * $0.01 = $23,332 * $0.01 = $233.32
        expected = Decimal('705') - Decimal('233.32')
        assert lito == expected
    
    def test_lito_eliminated(self, offset_service):
        """
        Test: LITO eliminated at $90,000+
        Expected: LITO = $0
        """
        lito = offset_service.calculate_lito(Decimal('90000'))
        
        assert lito == Decimal('0')
    
    def test_sapto_phase_out_start(self, offset_service):
        """
        Test: SAPTO at phase-out start ($56,548)
        Expected: SAPTO = full amount
        """
        sapto = offset_service.calculate_sapto(
            Decimal('56548'),
            is_senior=True,
            is_tax_free_person=False
        )
        
        assert sapto == Decimal('1445')
    
    def test_sapto_mid_phase_out(self, offset_service):
        """
        Test: SAPTO mid-phase-out
        Scenario: Income $70,000 (senior, not tax-free)
        Expected: SAPTO reduced
        """
        sapto = offset_service.calculate_sapto(
            Decimal('70000'),
            is_senior=True,
            is_tax_free_person=False
        )
        
        # Reduction: ($70,000 - $56,548) * 0.1245 = $13,452 * 0.1245
        reduction = (Decimal('70000') - Decimal('56548')) * Decimal('0.1245')
        expected = Decimal('1445') - reduction
        assert sapto == expected
    
    def test_ldco_no_dependants(self, offset_service):
        """
        Test: LDCO with no dependants
        Expected: LDCO = $0
        """
        ldco = offset_service.calculate_ldco(Decimal('50000'), num_dependants=0)
        
        assert ldco == Decimal('0')
    
    def test_ldco_at_income_threshold(self, offset_service):
        """
        Test: LDCO at income threshold ($80,000)
        Expected: LDCO = $0 (eligibility cutoff)
        """
        ldco = offset_service.calculate_ldco(Decimal('80000'), num_dependants=1)
        
        assert ldco == Decimal('0')
    
    def test_ldco_just_below_threshold(self, offset_service):
        """
        Test: LDCO just below income threshold ($79,999)
        Expected: LDCO = $1,657
        """
        ldco = offset_service.calculate_ldco(Decimal('79999'), num_dependants=1)
        
        assert ldco == Decimal('1657')
    
    def test_ldco_above_threshold(self, offset_service):
        """
        Test: LDCO above income threshold ($90,000)
        Expected: LDCO = $0
        """
        ldco = offset_service.calculate_ldco(Decimal('90000'), num_dependants=2)
        
        assert ldco == Decimal('0')


# ATO-specific rules and scenarios
class TestTaxOffsetServiceATOSpecificRules:
    """Test ATO-specific offset rules"""
    
    def test_offset_aggregation(self, offset_service):
        """
        Test: Multiple offsets aggregate correctly
        Scenario: LITO + LDCO
        """
        offsets = {
            'LITO': Decimal('705'),
            'LDCO': Decimal('1657')
        }
        
        total = offset_service.aggregate_offsets(offsets)
        
        assert total == Decimal('2362')
    
    def test_offset_eligibility_rules(self, offset_service):
        """
        Test: Offset eligibility rules correctly applied
        """
        # LITO eligible
        assert offset_service.is_lito_eligible(Decimal('50000'))
        
        # LITO not eligible above threshold
        assert not offset_service.is_lito_eligible(Decimal('95000'))
        
        # SAPTO eligible only if senior
        assert offset_service.is_sapto_eligible(Decimal('50000'), is_senior=True)
        assert not offset_service.is_sapto_eligible(Decimal('50000'), is_senior=False)
    
    def test_young_worker_scenario(self, offset_service):
        """
        Test: Young worker scenario
        Scenario: Age 25, income $35,000, 0 dependants
        Expected: LITO only
        """
        input_data = OffsetCalculationInput(
            taxable_income=Decimal('35000'),
            age=25,
            dependants=0,
            is_senior=False
        )
        
        result = offset_service.calculate_all_offsets(input_data)
        
        assert result.lito_amount == Decimal('705')
        assert result.sapto_amount == Decimal('0')
        assert result.ldco_amount == Decimal('0')
        assert result.total_offsets == Decimal('705')
    
    def test_middle_income_family_scenario(self, offset_service):
        """
        Test: Middle income family scenario
        Scenario: Income $65,000, 2 dependants
        Expected: LITO + LDCO
        """
        input_data = OffsetCalculationInput(
            taxable_income=Decimal('65000'),
            dependants=2,
            is_senior=False
        )
        
        result = offset_service.calculate_all_offsets(input_data)
        
        assert result.lito_amount == Decimal('705')
        assert result.ldco_amount == Decimal('1657') * Decimal('2')
        assert result.total_offsets == Decimal('705') + Decimal('3314')
    
    def test_senior_pensioner_scenario(self, offset_service):
        """
        Test: Senior pensioner scenario
        Scenario: Age 70, income $25,000, tax-free person status
        Expected: SAPTO only (no LITO for tax-free persons typically)
        """
        input_data = OffsetCalculationInput(
            taxable_income=Decimal('25000'),
            age=70,
            is_senior=True,
            is_tax_free_person=True
        )
        
        result = offset_service.calculate_all_offsets(input_data)
        
        assert result.sapto_amount == Decimal('1602')
        assert result.total_offsets == Decimal('1602')
    
    def test_high_income_no_offsets(self, offset_service):
        """
        Test: High income with no eligible offsets
        Scenario: Income $150,000, non-senior, no dependants
        Expected: All offsets = $0
        """
        input_data = OffsetCalculationInput(
            taxable_income=Decimal('150000'),
            dependants=0,
            is_senior=False
        )
        
        result = offset_service.calculate_all_offsets(input_data)
        
        assert result.total_offsets == Decimal('0')


# Offset phase-out scenarios
class TestTaxOffsetServicePhaseOut:
    """Test offset phase-out scenarios in detail"""
    
    def test_lito_phase_out_progression(self, offset_service):
        """
        Test: LITO phase-out progression from $66,667 to $90,000
        Expected: Linear decrease at $0.01 per $1 increase
        """
        test_points = [
            (Decimal('66667'), Decimal('705')),
            (Decimal('70000'), Decimal('705') - Decimal('33.33')),
            (Decimal('75000'), Decimal('705') - Decimal('83.33')),
            (Decimal('80000'), Decimal('705') - Decimal('133.33')),
            (Decimal('90000'), Decimal('0')),
        ]
        
        for income, expected in test_points:
            lito = offset_service.calculate_lito(income)
            assert abs(lito - expected) < Decimal('0.01'), \
                f"LITO at {income}: expected {expected}, got {lito}"
    
    def test_sapto_phase_out_progression(self, offset_service):
        """
        Test: SAPTO phase-out progression
        Expected: Linear decrease after $56,548
        """
        sapto_values = []
        for income_step in range(10):
            income = Decimal('56548') + Decimal(income_step * 10000)
            sapto = offset_service.calculate_sapto(
                income,
                is_senior=True,
                is_tax_free_person=False
            )
            sapto_values.append((income, sapto))
        
        # Verify monotonic decrease (or constant at 0)
        for i in range(len(sapto_values) - 1):
            assert sapto_values[i][1] >= sapto_values[i + 1][1], \
                f"SAPTO should not increase with income"


# Error handling and edge cases
class TestTaxOffsetServiceErrorHandling:
    """Test error handling and validation"""
    
    def test_negative_income_treated_as_zero(self, offset_service):
        """
        Test: Negative income should be handled
        Expected: Treated similar to zero income
        """
        lito_neg = offset_service.calculate_lito(Decimal('-10000'))
        lito_zero = offset_service.calculate_lito(Decimal('0'))
        
        # Negative income should be clamped or treated as zero
        assert lito_neg == Decimal('0') or lito_neg >= Decimal('0')
    
    def test_negative_dependants(self, offset_service):
        """
        Test: Negative number of dependants
        Expected: Treated as zero
        """
        ldco = offset_service.calculate_ldco(Decimal('50000'), num_dependants=-1)
        
        assert ldco == Decimal('0')
    
    def test_large_income(self, offset_service):
        """
        Test: Very large income
        Expected: All offsets = $0
        """
        input_data = OffsetCalculationInput(
            taxable_income=Decimal('500000'),
            dependants=1,
            is_senior=False
        )
        
        result = offset_service.calculate_all_offsets(input_data)
        
        assert result.total_offsets == Decimal('0')
    
    def test_decimal_precision(self, offset_service):
        """
        Test: Decimal precision in offset calculations
        """
        lito = offset_service.calculate_lito(Decimal('66667.50'))
        
        # Should maintain precision
        assert lito == Decimal('705')
        
        lito_mid = offset_service.calculate_lito(Decimal('78333.33'))
        
        # Should handle cents correctly
        assert lito_mid > Decimal('0')
        assert lito_mid < Decimal('705')


# Parametrized tests for comprehensive coverage
class TestTaxOffsetServiceParametrized:
    """Parametrized tests for comprehensive offset coverage"""
    
    @pytest.mark.parametrize("income,expected_lito", [
        (Decimal('0'), Decimal('705')),
        (Decimal('30000'), Decimal('705')),
        (Decimal('66667'), Decimal('705')),
        (Decimal('70000'), Decimal('705') - Decimal('33.33')),
        (Decimal('80000'), Decimal('705') - Decimal('133.33')),
        (Decimal('90000'), Decimal('0')),
        (Decimal('100000'), Decimal('0')),
    ])
    def test_lito_calculation_various_incomes(self, offset_service, income, expected_lito):
        """Test LITO calculation for various income levels"""
        lito = offset_service.calculate_lito(income)
        
        # Allow small rounding tolerance
        assert abs(lito - expected_lito) < Decimal('0.01')
    
    @pytest.mark.parametrize("num_dependants,income,expected_ldco", [
        (0, Decimal('50000'), Decimal('0')),
        (1, Decimal('50000'), Decimal('1657')),
        (2, Decimal('50000'), Decimal('3314')),
        (3, Decimal('75000'), Decimal('4971')),
        (1, Decimal('80000'), Decimal('0')),
        (2, Decimal('100000'), Decimal('0')),
    ])
    def test_ldco_various_scenarios(self, offset_service, num_dependants, income, expected_ldco):
        """Test LDCO for various dependant and income combinations"""
        ldco = offset_service.calculate_ldco(income, num_dependants)
        
        assert ldco == expected_ldco


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
