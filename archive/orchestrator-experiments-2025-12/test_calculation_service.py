"""
Comprehensive test scenarios for CORE CALCULATION services - ATO Tax Agent
Test file: test_calculation_service.py

This module tests the main tax calculation engine including:
- Tax calculation workflow
- Integration between different calculation steps
- Multiple income source handling
- Overall tax liability computation

ATO Rules (2024-25 FY):
- Tax-free threshold: $18,200
- Tax brackets: $45,000, $120,000, $180,000+
- Medicare Levy: 2% (standard), thresholds apply
- LITO (Low Income Tax Offset): Up to $705
"""

import pytest
from decimal import Decimal
from dataclasses import dataclass
from typing import Dict, List, Optional


# Mock service class - replace with actual import when integrated
@dataclass
class TaxCalculationInput:
    """Input data for tax calculation"""
    gross_income: Decimal
    tax_offsets: Dict[str, Decimal]
    medicare_levy: Decimal
    deductions: Decimal = Decimal('0')
    other_adjustments: Dict[str, Decimal] = None

    def __post_init__(self):
        if self.other_adjustments is None:
            self.other_adjustments = {}


@dataclass
class TaxCalculationResult:
    """Result from tax calculation"""
    assessable_income: Decimal
    taxable_income: Decimal
    base_tax: Decimal
    medicare_levy: Decimal
    total_tax_liability: Decimal
    total_offsets: Decimal
    net_tax_payable: Decimal


class MockCalculationService:
    """Mock implementation of calculation service for testing"""
    
    def calculate_tax(self, income_input: TaxCalculationInput) -> TaxCalculationResult:
        """Main tax calculation method"""
        # Calculate assessable income
        assessable_income = income_input.gross_income - income_input.deductions
        
        # Apply tax-free threshold
        taxable_income = max(Decimal('0'), assessable_income - Decimal('18200'))
        
        # Calculate base tax using 2024-25 brackets
        base_tax = self._calculate_base_tax(taxable_income)
        
        # Calculate total offsets
        total_offsets = sum(income_input.tax_offsets.values())
        
        # Calculate net tax before Medicare levy
        tax_before_levy = max(Decimal('0'), base_tax - total_offsets)
        
        # Add Medicare levy
        total_tax_liability = tax_before_levy + income_input.medicare_levy
        
        return TaxCalculationResult(
            assessable_income=assessable_income,
            taxable_income=taxable_income,
            base_tax=base_tax,
            medicare_levy=income_input.medicare_levy,
            total_tax_liability=total_tax_liability,
            total_offsets=total_offsets,
            net_tax_payable=max(Decimal('0'), total_tax_liability)
        )
    
    def _calculate_base_tax(self, taxable_income: Decimal) -> Decimal:
        """Calculate tax using 2024-25 tax brackets"""
        if taxable_income <= 0:
            return Decimal('0')
        
        # 2024-25 tax brackets
        if taxable_income <= Decimal('45000'):
            return taxable_income * Decimal('0.19')
        elif taxable_income <= Decimal('120000'):
            return Decimal('8550') + (taxable_income - Decimal('45000')) * Decimal('0.325')
        elif taxable_income <= Decimal('180000'):
            return Decimal('31305') + (taxable_income - Decimal('120000')) * Decimal('0.37')
        else:
            return Decimal('53705') + (taxable_income - Decimal('180000')) * Decimal('0.45')


# Test fixtures
@pytest.fixture
def calc_service():
    """Fixture providing calculation service instance"""
    return MockCalculationService()


# Normal cases - typical taxpayer scenarios
class TestCalculationServiceNormalCases:
    """Test normal/typical taxpayer scenarios"""
    
    def test_low_income_no_tax_below_threshold(self, calc_service):
        """
        Test: Single income earner below tax-free threshold
        Scenario: Income of $15,000 (below $18,200 threshold)
        Expected: No tax payable, assessable income = $15,000
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('15000'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('15000')
        assert result.taxable_income == Decimal('0')  # Below threshold
        assert result.base_tax == Decimal('0')
        assert result.net_tax_payable == Decimal('0')
    
    def test_middle_income_single_bracket(self, calc_service):
        """
        Test: Single income of $50,000
        Scenario: Typical middle-income taxpayer
        Expected: Taxable income = $31,800, tax = $6,042
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('50000'),
            tax_offsets={'LITO': Decimal('705')},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('50000')
        assert result.taxable_income == Decimal('31800')
        # Tax: $31,800 * 0.19 = $6,042
        assert result.base_tax == Decimal('6042')
        # After LITO: $6,042 - $705 = $5,337
        assert result.net_tax_payable == Decimal('5337')
    
    def test_high_income_multiple_brackets(self, calc_service):
        """
        Test: Income of $90,000
        Scenario: Higher middle-income earner crossing bracket
        Expected: Crosses 19% and 32.5% brackets
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('90000'),
            tax_offsets={},
            medicare_levy=Decimal('1800')  # 2% Medicare levy on $90k
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('90000')
        assert result.taxable_income == Decimal('71800')
        # Tax: $8,550 + ($71,800 - $45,000) * 0.325 = $8,550 + $8,735 = $17,285
        assert result.base_tax == Decimal('17285')
        assert result.medicare_levy == Decimal('1800')
        assert result.total_tax_liability == Decimal('19085')
    
    def test_very_high_income_top_bracket(self, calc_service):
        """
        Test: Income of $200,000
        Scenario: High income earner in top tax bracket (45%)
        Expected: Spans multiple brackets including top rate
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('200000'),
            tax_offsets={},
            medicare_levy=Decimal('3850')  # 2% on high income
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('200000')
        assert result.taxable_income == Decimal('181800')
        # Tax: $53,705 + ($181,800 - $180,000) * 0.45 = $53,705 + $810 = $54,515
        assert result.base_tax == Decimal('54515')
        assert result.total_tax_liability == Decimal('58365')
    
    def test_with_deductions(self, calc_service):
        """
        Test: Income $80,000 with $5,000 deductions
        Scenario: Taxpayer with work-related expenses
        Expected: Deductions reduce assessable income
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('80000'),
            tax_offsets={'LITO': Decimal('350')},
            medicare_levy=Decimal('1560'),  # 2%
            deductions=Decimal('5000')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('75000')
        assert result.taxable_income == Decimal('56800')
        # Tax: $8,550 + ($56,800 - $45,000) * 0.325 = $8,550 + $3,835 = $12,385
        assert result.base_tax == Decimal('12385')
        assert result.total_offsets == Decimal('350')


# Edge cases - boundary conditions and special scenarios
class TestCalculationServiceEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_income(self, calc_service):
        """
        Test: Zero income
        Expected: No tax payable
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('0'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('0')
        assert result.taxable_income == Decimal('0')
        assert result.base_tax == Decimal('0')
        assert result.net_tax_payable == Decimal('0')
    
    def test_exact_threshold_boundary(self, calc_service):
        """
        Test: Income exactly at tax-free threshold ($18,200)
        Expected: Taxable income = 0, no tax
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('18200'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('18200')
        assert result.taxable_income == Decimal('0')
        assert result.base_tax == Decimal('0')
        assert result.net_tax_payable == Decimal('0')
    
    def test_just_above_threshold(self, calc_service):
        """
        Test: Income $1 above tax-free threshold
        Expected: Minimal tax on $1
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('18201'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.taxable_income == Decimal('1')
        assert result.base_tax == Decimal('0.19')
    
    def test_bracket_boundary_45k(self, calc_service):
        """
        Test: Income at 19%/32.5% bracket boundary ($45,000)
        Expected: Still in 19% bracket
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('45000'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.taxable_income == Decimal('26800')
        # Tax: $26,800 * 0.19 = $5,092
        assert result.base_tax == Decimal('5092')
    
    def test_bracket_boundary_120k(self, calc_service):
        """
        Test: Income at 32.5%/37% bracket boundary ($120,000)
        Expected: Tax calculated correctly across boundary
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('120000'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.taxable_income == Decimal('101800')
        # Tax: $8,550 + ($101,800 - $45,000) * 0.325 = $8,550 + $18,585 = $27,135
        assert result.base_tax == Decimal('27135')
    
    def test_deductions_exceed_income(self, calc_service):
        """
        Test: Deductions greater than income
        Expected: Assessable income capped at zero
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('50000'),
            tax_offsets={},
            medicare_levy=Decimal('0'),
            deductions=Decimal('75000')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('0')  # Can't be negative
        assert result.taxable_income == Decimal('0')
        assert result.base_tax == Decimal('0')
    
    def test_large_income_scenario(self, calc_service):
        """
        Test: Very high income ($500,000+)
        Expected: All income in 45% bracket
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('500000'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('500000')
        assert result.taxable_income == Decimal('481800')
        # Tax: $53,705 + ($481,800 - $180,000) * 0.45 = $53,705 + $135,810 = $189,515
        assert result.base_tax == Decimal('189515')


# ATO-specific rules and scenarios
class TestCalculationServiceATOSpecificRules:
    """Test ATO-specific rules and tax scenarios"""
    
    def test_multiple_offsets_aggregation(self, calc_service):
        """
        Test: Multiple tax offsets (LITO + other offsets)
        Scenario: LITO ($705) + Low income dependant offset ($150)
        Expected: Offsets aggregate correctly
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('40000'),
            tax_offsets={
                'LITO': Decimal('705'),
                'LDCO': Decimal('150')  # Low income dependant credit
            },
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.total_offsets == Decimal('855')
        expected_base_tax = (Decimal('40000') - Decimal('18200')) * Decimal('0.19')
        assert result.base_tax == expected_base_tax
        assert result.net_tax_payable == max(Decimal('0'), expected_base_tax - Decimal('855'))
    
    def test_lito_phase_out(self, calc_service):
        """
        Test: LITO phase-out scenario
        Scenario: Income $66,667 (LITO starts to phase out)
        Expected: LITO reduced compared to lower income
        """
        # LITO phases out at $90,000 by $0.01 per $1 above $65,926
        input_data = TaxCalculationInput(
            gross_income=Decimal('66667'),
            tax_offsets={'LITO': Decimal('629')},  # Phased out
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        # Verify that phased-out LITO is used correctly
        assert result.total_offsets == Decimal('629')
    
    def test_medicare_levy_standard_threshold(self, calc_service):
        """
        Test: Medicare levy at standard 2% threshold
        Scenario: Single income $90,000
        Expected: Medicare levy = 2% = $1,800
        """
        income = Decimal('90000')
        input_data = TaxCalculationInput(
            gross_income=income,
            tax_offsets={},
            medicare_levy=income * Decimal('0.02')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.medicare_levy == Decimal('1800')
    
    def test_medicare_levy_exemption(self, calc_service):
        """
        Test: Medicare levy exemption for low income
        Scenario: Income $17,000 (below threshold of ~$21,845)
        Expected: No Medicare levy
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('17000'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.medicare_levy == Decimal('0')
        assert result.total_tax_liability == Decimal('0')
    
    def test_zero_tax_with_offsets(self, calc_service):
        """
        Test: Offsets eliminate all tax liability
        Scenario: $30,000 income with $2,356 total offsets
        Expected: Net tax payable = $0 (but offsets may not be claimable)
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('30000'),
            tax_offsets={'offset': Decimal('2356')},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        base_tax = (Decimal('30000') - Decimal('18200')) * Decimal('0.19')
        assert result.base_tax == Decimal('2242')
        assert result.net_tax_payable == Decimal('0')


# Error handling and validation
class TestCalculationServiceErrorHandling:
    """Test error handling and validation"""
    
    def test_negative_gross_income_clamped(self, calc_service):
        """
        Test: Negative income should be treated as zero
        Expected: No tax on negative income
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('-1000'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('-1000')
        assert result.taxable_income == Decimal('0')  # Clamped
        assert result.net_tax_payable == Decimal('0')
    
    def test_negative_offsets_handled(self, calc_service):
        """
        Test: Negative offset values (shouldn't happen but test robustness)
        Expected: Sum correctly including negative offsets
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('100000'),
            tax_offsets={
                'positive_offset': Decimal('500'),
                'adjustment': Decimal('-100')
            },
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.total_offsets == Decimal('400')
    
    def test_precision_maintained_decimal(self, calc_service):
        """
        Test: Decimal precision maintained in calculations
        Scenario: Income with cents
        Expected: Correct calculation to 2 decimal places
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('50000.50'),
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('50000.50')
        assert result.taxable_income == Decimal('31800.50')


# Integration scenarios
class TestCalculationServiceIntegration:
    """Test integration scenarios combining multiple features"""
    
    def test_complex_income_scenario(self, calc_service):
        """
        Test: Complex realistic scenario
        Scenario:
        - Salary: $75,000
        - Deductions: $3,000
        - Offsets: LITO ($705)
        - Medicare: 2%
        Expected: All components calculated correctly
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('75000'),
            tax_offsets={'LITO': Decimal('705')},
            medicare_levy=Decimal('1500'),
            deductions=Decimal('3000')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.assessable_income == Decimal('72000')
        assert result.taxable_income == Decimal('53800')
        expected_base_tax = Decimal('8550') + (Decimal('53800') - Decimal('45000')) * Decimal('0.325')
        assert result.base_tax == expected_base_tax
        assert result.total_offsets == Decimal('705')
        assert result.total_tax_liability == result.base_tax - result.total_offsets + result.medicare_levy
    
    def test_family_support_scenario(self, calc_service):
        """
        Test: Family with multiple support scenarios
        Scenario: Income with various offsets applied
        Expected: Correct offset aggregation and tax calculation
        """
        input_data = TaxCalculationInput(
            gross_income=Decimal('85000'),
            tax_offsets={
                'LITO': Decimal('434'),
                'family_offset': Decimal('200'),
                'other_offset': Decimal('100')
            },
            medicare_levy=Decimal('1700')
        )
        
        result = calc_service.calculate_tax(input_data)
        
        assert result.total_offsets == Decimal('734')
        assert result.assessable_income == Decimal('85000')
        assert result.taxable_income == Decimal('66800')


# Parametrized tests for comprehensive coverage
class TestCalculationServiceParametrized:
    """Parametrized tests for broad coverage"""
    
    @pytest.mark.parametrize("income,expected_taxable", [
        (Decimal('0'), Decimal('0')),
        (Decimal('18200'), Decimal('0')),
        (Decimal('18201'), Decimal('1')),
        (Decimal('45000'), Decimal('26800')),
        (Decimal('120000'), Decimal('101800')),
        (Decimal('180000'), Decimal('161800')),
        (Decimal('500000'), Decimal('481800')),
    ])
    def test_various_income_levels(self, calc_service, income, expected_taxable):
        """Test various income levels against expected taxable income"""
        input_data = TaxCalculationInput(
            gross_income=income,
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        assert result.taxable_income == expected_taxable
    
    @pytest.mark.parametrize("taxable_income,expected_tax", [
        (Decimal('0'), Decimal('0')),
        (Decimal('10000'), Decimal('1900')),
        (Decimal('26800'), Decimal('5092')),
        (Decimal('56800'), Decimal('12385')),
        (Decimal('101800'), Decimal('27135')),
        (Decimal('161800'), Decimal('53705') + (Decimal('161800') - Decimal('180000') + Decimal('161800')) * Decimal('0')),
    ])
    def test_tax_bracket_calculations(self, calc_service, taxable_income, expected_tax):
        """Test correct tax calculation for various taxable incomes"""
        # Add threshold offset to get gross income
        gross_income = taxable_income + Decimal('18200')
        
        input_data = TaxCalculationInput(
            gross_income=gross_income,
            tax_offsets={},
            medicare_levy=Decimal('0')
        )
        
        result = calc_service.calculate_tax(input_data)
        assert result.base_tax == expected_tax


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
