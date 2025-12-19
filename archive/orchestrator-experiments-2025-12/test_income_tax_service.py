"""
Comprehensive test scenarios for CORE CALCULATION services - ATO Tax Agent
Test file: test_income_tax_service.py

This module tests income tax bracket calculations including:
- Tax bracket determination
- Progressive tax calculation
- Threshold boundary testing
- 2024-25 specific brackets and rates

ATO 2024-25 Tax Brackets:
- 0% to $18,200 (tax-free threshold)
- 19% on income from $18,201 to $45,000
- 32.5% on income from $45,001 to $120,000
- 37% on income from $120,001 to $180,000
- 45% on income over $180,000

Tax Free Threshold: $18,200 (standard resident, not senior, not injured worker)
"""

import pytest
from decimal import Decimal
from dataclasses import dataclass
from typing import Tuple, Optional
from enum import Enum


class TaxBracket(Enum):
    """Tax bracket classification"""
    TAX_FREE = "tax_free"
    FIRST_BRACKET = "first_bracket"  # 19%
    SECOND_BRACKET = "second_bracket"  # 32.5%
    THIRD_BRACKET = "third_bracket"  # 37%
    TOP_BRACKET = "top_bracket"  # 45%


@dataclass
class BracketThreshold:
    """Represents a tax bracket threshold"""
    lower_limit: Decimal
    upper_limit: Decimal
    rate: Decimal
    bracket_name: str


class MockIncomeTaxService:
    """Mock implementation of income tax service for testing"""
    
    # 2024-25 Tax brackets
    TAX_BRACKETS = [
        BracketThreshold(Decimal('0'), Decimal('18200'), Decimal('0'), 'tax_free'),
        BracketThreshold(Decimal('18201'), Decimal('45000'), Decimal('0.19'), 'first_bracket'),
        BracketThreshold(Decimal('45001'), Decimal('120000'), Decimal('0.325'), 'second_bracket'),
        BracketThreshold(Decimal('120001'), Decimal('180000'), Decimal('0.37'), 'third_bracket'),
        BracketThreshold(Decimal('180001'), Decimal('999999999'), Decimal('0.45'), 'top_bracket'),
    ]
    
    def determine_bracket(self, taxable_income: Decimal) -> Optional[BracketThreshold]:
        """Determine which tax bracket applies to given income"""
        if taxable_income < 0:
            return None
        
        for bracket in self.TAX_BRACKETS:
            if bracket.lower_limit <= taxable_income <= bracket.upper_limit:
                return bracket
        
        return None
    
    def calculate_progressive_tax(self, taxable_income: Decimal) -> Decimal:
        """Calculate tax using progressive tax brackets"""
        if taxable_income <= 0:
            return Decimal('0')
        
        total_tax = Decimal('0')
        
        # Tax-free threshold
        if taxable_income <= Decimal('18200'):
            return Decimal('0')
        
        # First bracket: $18,201 to $45,000 @ 19%
        if taxable_income > Decimal('18200'):
            first_bracket_income = min(taxable_income, Decimal('45000')) - Decimal('18200')
            total_tax += first_bracket_income * Decimal('0.19')
        
        # Second bracket: $45,001 to $120,000 @ 32.5%
        if taxable_income > Decimal('45000'):
            second_bracket_income = min(taxable_income, Decimal('120000')) - Decimal('45000')
            total_tax += second_bracket_income * Decimal('0.325')
        
        # Third bracket: $120,001 to $180,000 @ 37%
        if taxable_income > Decimal('120000'):
            third_bracket_income = min(taxable_income, Decimal('180000')) - Decimal('120000')
            total_tax += third_bracket_income * Decimal('0.37')
        
        # Top bracket: over $180,000 @ 45%
        if taxable_income > Decimal('180000'):
            top_bracket_income = taxable_income - Decimal('180000')
            total_tax += top_bracket_income * Decimal('0.45')
        
        return total_tax
    
    def get_average_tax_rate(self, taxable_income: Decimal) -> Decimal:
        """Calculate average tax rate"""
        if taxable_income <= 0:
            return Decimal('0')
        
        tax = self.calculate_progressive_tax(taxable_income)
        return (tax / taxable_income * Decimal('100')).quantize(Decimal('0.01'))
    
    def get_marginal_rate(self, taxable_income: Decimal) -> Decimal:
        """Get marginal tax rate for given income"""
        bracket = self.determine_bracket(taxable_income)
        return bracket.rate if bracket else Decimal('0')
    
    def calculate_cumulative_tax(self, taxable_income: Decimal, brackets_list: list) -> Tuple[Decimal, list]:
        """Calculate tax showing cumulative contribution by bracket"""
        if taxable_income <= 0:
            return Decimal('0'), []
        
        cumulative = []
        total = Decimal('0')
        
        # Tax-free
        if taxable_income <= Decimal('18200'):
            cumulative.append({'bracket': 'tax_free', 'amount': Decimal('0'), 'rate': Decimal('0')})
            return Decimal('0'), cumulative
        
        cumulative.append({'bracket': 'tax_free', 'amount': Decimal('0'), 'rate': Decimal('0')})
        
        # First bracket
        if taxable_income > Decimal('18200'):
            first_income = min(taxable_income - Decimal('18200'), Decimal('45000') - Decimal('18200'))
            first_tax = first_income * Decimal('0.19')
            cumulative.append({'bracket': 'first_bracket', 'amount': first_income, 'tax': first_tax, 'rate': Decimal('0.19')})
            total += first_tax
        
        # Second bracket
        if taxable_income > Decimal('45000'):
            second_income = min(taxable_income - Decimal('45000'), Decimal('120000') - Decimal('45000'))
            second_tax = second_income * Decimal('0.325')
            cumulative.append({'bracket': 'second_bracket', 'amount': second_income, 'tax': second_tax, 'rate': Decimal('0.325')})
            total += second_tax
        
        # Third bracket
        if taxable_income > Decimal('120000'):
            third_income = min(taxable_income - Decimal('120000'), Decimal('180000') - Decimal('120000'))
            third_tax = third_income * Decimal('0.37')
            cumulative.append({'bracket': 'third_bracket', 'amount': third_income, 'tax': third_tax, 'rate': Decimal('0.37')})
            total += third_tax
        
        # Top bracket
        if taxable_income > Decimal('180000'):
            top_income = taxable_income - Decimal('180000')
            top_tax = top_income * Decimal('0.45')
            cumulative.append({'bracket': 'top_bracket', 'amount': top_income, 'tax': top_tax, 'rate': Decimal('0.45')})
            total += top_tax
        
        return total, cumulative


# Test fixtures
@pytest.fixture
def tax_service():
    """Fixture providing income tax service instance"""
    return MockIncomeTaxService()


# Normal cases - typical income scenarios
class TestIncomeTaxServiceNormalCases:
    """Test normal/typical income scenarios"""
    
    def test_below_tax_free_threshold(self, tax_service):
        """
        Test: Income below tax-free threshold ($18,200)
        Expected: Bracket is tax-free, tax = $0
        """
        taxable_income = Decimal('15000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'tax_free'
        assert bracket.rate == Decimal('0')
        assert tax == Decimal('0')
    
    def test_first_bracket_typical(self, tax_service):
        """
        Test: Income in first bracket ($30,000)
        Expected: 19% marginal rate, tax = $2,242
        """
        taxable_income = Decimal('30000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'first_bracket'
        assert bracket.rate == Decimal('0.19')
        # Tax: ($30,000 - $18,200) * 0.19 = $11,800 * 0.19 = $2,242
        assert tax == Decimal('2242')
        assert tax_service.get_marginal_rate(taxable_income) == Decimal('0.19')
    
    def test_second_bracket_typical(self, tax_service):
        """
        Test: Income in second bracket ($75,000)
        Expected: 32.5% marginal rate
        """
        taxable_income = Decimal('75000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'second_bracket'
        assert bracket.rate == Decimal('0.325')
        # Tax: $8,550 + ($75,000 - $45,000) * 0.325 = $8,550 + $9,750 = $18,300
        assert tax == Decimal('18300')
        assert tax_service.get_marginal_rate(taxable_income) == Decimal('0.325')
    
    def test_third_bracket_typical(self, tax_service):
        """
        Test: Income in third bracket ($150,000)
        Expected: 37% marginal rate
        """
        taxable_income = Decimal('150000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'third_bracket'
        assert bracket.rate == Decimal('0.37')
        # Tax: $31,305 + ($150,000 - $120,000) * 0.37 = $31,305 + $11,100 = $42,405
        assert tax == Decimal('42405')
        assert tax_service.get_marginal_rate(taxable_income) == Decimal('0.37')
    
    def test_top_bracket_typical(self, tax_service):
        """
        Test: Income in top bracket ($250,000)
        Expected: 45% marginal rate
        """
        taxable_income = Decimal('250000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'top_bracket'
        assert bracket.rate == Decimal('0.45')
        # Tax: $53,705 + ($250,000 - $180,000) * 0.45 = $53,705 + $31,500 = $85,205
        assert tax == Decimal('85205')
        assert tax_service.get_marginal_rate(taxable_income) == Decimal('0.45')


# Edge cases - boundary conditions
class TestIncomeTaxServiceEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_zero_income(self, tax_service):
        """
        Test: Zero income
        Expected: Tax-free bracket, $0 tax
        """
        taxable_income = Decimal('0')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'tax_free'
        assert tax == Decimal('0')
    
    def test_exact_threshold_18200(self, tax_service):
        """
        Test: Income exactly at tax-free threshold
        Expected: Still in tax-free, no tax
        """
        taxable_income = Decimal('18200')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'tax_free'
        assert tax == Decimal('0')
    
    def test_one_dollar_above_threshold(self, tax_service):
        """
        Test: Income $1 above tax-free threshold
        Expected: First bracket, minimal tax = $0.19
        """
        taxable_income = Decimal('18201')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'first_bracket'
        assert tax == Decimal('0.19')
    
    def test_exact_45000_boundary(self, tax_service):
        """
        Test: Income exactly at $45,000 bracket boundary
        Expected: Still in first bracket
        """
        taxable_income = Decimal('45000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'first_bracket'
        # Tax: ($45,000 - $18,200) * 0.19 = $26,800 * 0.19 = $5,092
        assert tax == Decimal('5092')
    
    def test_one_dollar_above_45000(self, tax_service):
        """
        Test: Income $1 above $45,000 boundary
        Expected: Crosses into second bracket
        """
        taxable_income = Decimal('45001')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'second_bracket'
        # Tax: $5,092 + $1 * 0.325 = $5,092.325
        assert tax == Decimal('5092.325')
    
    def test_exact_120000_boundary(self, tax_service):
        """
        Test: Income exactly at $120,000 boundary
        Expected: Still in second bracket
        """
        taxable_income = Decimal('120000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'second_bracket'
        # Tax: $8,550 + ($120,000 - $45,000) * 0.325 = $8,550 + $24,375 = $32,925
        assert tax == Decimal('32925')
    
    def test_one_dollar_above_120000(self, tax_service):
        """
        Test: Income $1 above $120,000 boundary
        Expected: Crosses into third bracket
        """
        taxable_income = Decimal('120001')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'third_bracket'
        # Tax: $32,925 + $1 * 0.37 = $32,925.37
        assert tax == Decimal('32925.37')
    
    def test_exact_180000_boundary(self, tax_service):
        """
        Test: Income exactly at $180,000 boundary
        Expected: Still in third bracket
        """
        taxable_income = Decimal('180000')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'third_bracket'
        # Tax: $31,305 + ($180,000 - $120,000) * 0.37 = $31,305 + $22,200 = $53,505
        assert tax == Decimal('53505')
    
    def test_one_dollar_above_180000(self, tax_service):
        """
        Test: Income $1 above $180,000 boundary
        Expected: Crosses into top bracket
        """
        taxable_income = Decimal('180001')
        
        bracket = tax_service.determine_bracket(taxable_income)
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        assert bracket.bracket_name == 'top_bracket'
        # Tax: $53,705 + $1 * 0.45 = $53,705.45
        assert tax == Decimal('53705.45')


# ATO-specific rules and calculations
class TestIncomeTaxServiceATOSpecificRules:
    """Test ATO-specific rules and calculations"""
    
    def test_average_tax_rate_calculation(self, tax_service):
        """
        Test: Average tax rate calculation
        Scenario: $50,000 taxable income
        Expected: Average rate = Tax / Income * 100
        """
        taxable_income = Decimal('50000')
        tax = tax_service.calculate_progressive_tax(taxable_income)
        avg_rate = tax_service.get_average_tax_rate(taxable_income)
        
        expected_tax = Decimal('6042')
        expected_avg_rate = (Decimal('6042') / Decimal('50000') * Decimal('100')).quantize(Decimal('0.01'))
        
        assert tax == expected_tax
        assert avg_rate == expected_avg_rate
    
    def test_marginal_vs_average_rate(self, tax_service):
        """
        Test: Marginal rate is higher than average rate
        Scenario: Income in middle bracket
        Expected: Marginal (32.5%) > Average (~20%)
        """
        taxable_income = Decimal('80000')
        
        marginal_rate = tax_service.get_marginal_rate(taxable_income)
        avg_rate = tax_service.get_average_tax_rate(taxable_income)
        
        assert marginal_rate == Decimal('0.325')
        assert avg_rate > Decimal('0')
        assert marginal_rate > avg_rate
    
    def test_cumulative_tax_by_bracket(self, tax_service):
        """
        Test: Cumulative tax contribution by bracket
        Scenario: Income crossing multiple brackets
        Expected: Each bracket shows correct tax contribution
        """
        taxable_income = Decimal('150000')
        
        total_tax, cumulative = tax_service.calculate_cumulative_tax(taxable_income, [])
        
        # Should have contributions from 1st, 2nd, and 3rd brackets
        assert len(cumulative) >= 4  # tax_free + 3 brackets
        
        # First bracket: ($45,000 - $18,200) * 0.19 = $5,092
        assert cumulative[1]['tax'] == Decimal('5092')
        
        # Second bracket: ($120,000 - $45,000) * 0.325 = $24,375
        assert cumulative[2]['tax'] == Decimal('24375')
        
        # Third bracket: ($150,000 - $120,000) * 0.37 = $11,100
        assert cumulative[3]['tax'] == Decimal('11100')
    
    def test_progressive_tax_application(self, tax_service):
        """
        Test: Progressive taxation correctly applied
        Scenario: Compare marginal vs total tax on next dollar
        Expected: Next dollar taxed at marginal rate
        """
        income1 = Decimal('100000')
        income2 = Decimal('100001')
        
        tax1 = tax_service.calculate_progressive_tax(income1)
        tax2 = tax_service.calculate_progressive_tax(income2)
        tax_on_next_dollar = tax2 - tax1
        
        marginal_rate = tax_service.get_marginal_rate(income1)
        
        assert tax_on_next_dollar == marginal_rate


# Tax bracket calculations with precision
class TestIncomeTaxServicePrecision:
    """Test precision and calculation accuracy"""
    
    def test_decimal_precision_maintained(self, tax_service):
        """
        Test: Decimal precision maintained in calculations
        Scenario: Income with cents
        Expected: Correct calculation to 2 decimal places
        """
        taxable_income = Decimal('50000.50')
        
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        # Tax: ($50,000.50 - $18,200) * 0.19 = $31,800.50 * 0.19 = $6,042.095
        expected_tax = Decimal('6042.095')
        assert tax == expected_tax
    
    def test_large_income_precision(self, tax_service):
        """
        Test: Precision with very large income
        Scenario: $1 million income
        Expected: Correct calculation with multiple decimal places
        """
        taxable_income = Decimal('1000000')
        
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        # Components: $8,550 + $24,375 + $22,200 + $737,000 * 0.45
        expected_tax = Decimal('8550') + Decimal('24375') + Decimal('22200') + (Decimal('1000000') - Decimal('180000')) * Decimal('0.45')
        assert tax == expected_tax
    
    def test_cents_in_tax_calculation(self, tax_service):
        """
        Test: Tax calculation with cents in income
        Scenario: Multiple incomes totaling amount with cents
        Expected: Correct rounding behavior
        """
        taxable_income = Decimal('75000.75')
        
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        expected = Decimal('8550') + (Decimal('75000.75') - Decimal('45000')) * Decimal('0.325')
        assert tax == expected


# Complex scenarios combining multiple features
class TestIncomeTaxServiceComplexScenarios:
    """Test complex scenarios combining multiple features"""
    
    def test_income_spanning_all_brackets(self, tax_service):
        """
        Test: Very high income spanning all brackets
        Scenario: $500,000 income
        Expected: Correct tax across all 5 bracket levels
        """
        taxable_income = Decimal('500000')
        
        tax = tax_service.calculate_progressive_tax(taxable_income)
        
        # Manually calculate:
        # Tax-free: $0
        # 1st bracket: ($45,000 - $18,200) * 0.19 = $5,092
        # 2nd bracket: ($120,000 - $45,000) * 0.325 = $24,375
        # 3rd bracket: ($180,000 - $120,000) * 0.37 = $22,200
        # Top bracket: ($500,000 - $180,000) * 0.45 = $144,000
        expected_tax = Decimal('5092') + Decimal('24375') + Decimal('22200') + Decimal('144000')
        
        assert tax == expected_tax
    
    def test_average_rate_progression(self, tax_service):
        """
        Test: Average tax rate increases with income
        Scenario: Compare average rates at different income levels
        Expected: Higher income has higher average rate
        """
        incomes = [
            Decimal('30000'),
            Decimal('75000'),
            Decimal('150000'),
            Decimal('250000')
        ]
        
        avg_rates = [tax_service.get_average_tax_rate(income) for income in incomes]
        
        # Verify rates are increasing
        for i in range(len(avg_rates) - 1):
            assert avg_rates[i] < avg_rates[i + 1], \
                f"Average rate should increase with income: {avg_rates[i]} < {avg_rates[i + 1]}"


# Parametrized tests for comprehensive bracket coverage
class TestIncomeTaxServiceParametrized:
    """Parametrized tests for comprehensive bracket coverage"""
    
    @pytest.mark.parametrize("income,expected_bracket,expected_rate", [
        (Decimal('5000'), 'tax_free', Decimal('0')),
        (Decimal('18200'), 'tax_free', Decimal('0')),
        (Decimal('30000'), 'first_bracket', Decimal('0.19')),
        (Decimal('45000'), 'first_bracket', Decimal('0.19')),
        (Decimal('80000'), 'second_bracket', Decimal('0.325')),
        (Decimal('120000'), 'second_bracket', Decimal('0.325')),
        (Decimal('150000'), 'third_bracket', Decimal('0.37')),
        (Decimal('180000'), 'third_bracket', Decimal('0.37')),
        (Decimal('250000'), 'top_bracket', Decimal('0.45')),
    ])
    def test_bracket_determination(self, tax_service, income, expected_bracket, expected_rate):
        """Test bracket determination for various income levels"""
        bracket = tax_service.determine_bracket(income)
        
        assert bracket.bracket_name == expected_bracket
        assert bracket.rate == expected_rate
    
    @pytest.mark.parametrize("income,expected_tax", [
        (Decimal('18200'), Decimal('0')),
        (Decimal('30000'), Decimal('2242')),
        (Decimal('45000'), Decimal('5092')),
        (Decimal('60000'), Decimal('8550') + (Decimal('60000') - Decimal('45000')) * Decimal('0.325')),
        (Decimal('120000'), Decimal('8550') + Decimal('24375')),
        (Decimal('180000'), Decimal('53505')),
    ])
    def test_progressive_tax_calculation(self, tax_service, income, expected_tax):
        """Test progressive tax calculation for various income levels"""
        tax = tax_service.calculate_progressive_tax(income)
        
        assert tax == expected_tax


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
