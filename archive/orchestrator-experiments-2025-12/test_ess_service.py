"""
Unit tests for ESS Service

Tests Division 83A-C logic including:
- Discount calculations with exemptions
- Deferred taxing point eligibility
- Option exercise scenarios
- CGT cost base tracking
- Tax return formatting
"""

import unittest
from datetime import date, timedelta
from decimal import Decimal
from ess_service import (
    ESSService,
    ESSStatementBuilder,
    ESSStatement,
    ESSInterest,
    ESSType,
    SchemeType,
    TaxableDiscount,
    DeferralEligibility,
    OptionDetails,
    OptionExerciseScenario,
    OptionExerciseType,
    ESSValidator,
    CGTCostBase
)


class TestESSInterest(unittest.TestCase):
    """Test ESSInterest dataclass validation"""
    
    def test_valid_discount_share(self):
        """Test creating valid discount share interest"""
        interest = ESSInterest(
            interest_id="TEST-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Salary Sacrifice Plan",
            has_real_risk_forfeiture=True
        )
        self.assertEqual(interest.raw_discount, Decimal("2500.00"))
        self.assertTrue(interest.has_discount)
    
    def test_negative_amount_paid(self):
        """Test that negative amount paid raises error"""
        with self.assertRaises(ValueError):
            ESSInterest(
                interest_id="TEST-001",
                ess_type=ESSType.DISCOUNT_SHARE,
                scheme_type=SchemeType.GENERAL,
                acquisition_date=date(2023, 7, 15),
                amount_paid=Decimal("-1000.00"),
                market_value_acquisition=Decimal("7500.00"),
                employer_name="TechCorp",
                plan_name="Plan"
            )
    
    def test_negative_market_value(self):
        """Test that negative market value raises error"""
        with self.assertRaises(ValueError):
            ESSInterest(
                interest_id="TEST-001",
                ess_type=ESSType.DISCOUNT_SHARE,
                scheme_type=SchemeType.GENERAL,
                acquisition_date=date(2023, 7, 15),
                amount_paid=Decimal("5000.00"),
                market_value_acquisition=Decimal("-1000.00"),
                employer_name="TechCorp",
                plan_name="Plan"
            )
    
    def test_invalid_expiry_date(self):
        """Test that expiry date before acquisition raises error"""
        with self.assertRaises(ValueError):
            ESSInterest(
                interest_id="TEST-001",
                ess_type=ESSType.OPTION,
                scheme_type=SchemeType.GENERAL,
                acquisition_date=date(2023, 7, 15),
                amount_paid=Decimal("0.00"),
                market_value_acquisition=Decimal("0.00"),
                employer_name="TechCorp",
                plan_name="Plan",
                expiry_date=date(2023, 1, 1)  # Before acquisition
            )


class TestTaxableDiscountCalculation(unittest.TestCase):
    """Test discount calculation with $1,000 exemption"""
    
    def setUp(self):
        self.service = ESSService()
    
    def test_discount_with_salary_sacrifice_exemption(self):
        """Test $1,000 exemption applies to salary sacrifice scheme"""
        # Raw discount: $7,500 - $5,000 = $2,500
        # With $1,000 exemption: taxable discount = $1,500
        interest = ESSInterest(
            interest_id="TEST-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Salary Sacrifice Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("2500.00"))
        self.assertEqual(result.exemption_applied, Decimal("1000.00"))
        self.assertEqual(result.taxable_discount, Decimal("1500.00"))
        self.assertTrue(result.is_eligible_for_exemption)
    
    def test_discount_less_than_exemption(self):
        """Test discount < $1,000 (fully exempt)"""
        # Raw discount: $750
        # Exemption applied: $750 (full discount is exempt)
        # Taxable discount: $0
        interest = ESSInterest(
            interest_id="TEST-002",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("5750.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("750.00"))
        self.assertEqual(result.exemption_applied, Decimal("750.00"))
        self.assertEqual(result.taxable_discount, Decimal("0.00"))
    
    def test_no_exemption_for_general_scheme(self):
        """Test general scheme is not eligible for exemption"""
        interest = ESSInterest(
            interest_id="TEST-003",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.GENERAL,  # No exemption
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("2500.00"))
        self.assertEqual(result.exemption_applied, Decimal("0.00"))
        self.assertEqual(result.taxable_discount, Decimal("2500.00"))
        self.assertFalse(result.is_eligible_for_exemption)
    
    def test_no_discount(self):
        """Test interest with no discount (amount paid = market value)"""
        interest = ESSInterest(
            interest_id="TEST-004",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("7500.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("0.00"))
        self.assertEqual(result.taxable_discount, Decimal("0.00"))
    
    def test_exemption_on_small_business_scheme(self):
        """Test $1,000 exemption applies to small business scheme"""
        interest = ESSInterest(
            interest_id="TEST-005",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SMALL_BUSINESS,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="SmallCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertTrue(result.is_eligible_for_exemption)
        self.assertEqual(result.exemption_applied, Decimal("1000.00"))
    
    def test_option_no_discount(self):
        """Test that options (granted for free) have no discount"""
        interest = ESSInterest(
            interest_id="TEST-006",
            ess_type=ESSType.OPTION,
            scheme_type=SchemeType.GENERAL,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("0.00"),
            market_value_acquisition=Decimal("0.00"),
            employer_name="TechCorp",
            plan_name="Option Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("0.00"))
        self.assertEqual(result.taxable_discount, Decimal("0.00"))


class TestDeferredTaxingPoint(unittest.TestCase):
    """Test deferred taxing point eligibility"""
    
    def setUp(self):
        self.service = ESSService()
        self.current_date = date(2024, 6, 30)
    
    def test_eligible_with_rrof(self):
        """Test interest eligible for deferral with RROF"""
        interest = ESSInterest(
            interest_id="TEST-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan",
            has_real_risk_forfeiture=True  # Critical for deferral
        )
        
        result = self.service.check_deferred_taxing_point_eligibility(
            interest, self.current_date
        )
        
        self.assertTrue(result.is_eligible)
        self.assertIsNotNone(result.eligible_until_date)
        # Eligible until 15 July 2038 (15 years from acquisition)
        self.assertEqual(result.eligible_until_date, date(2038, 7, 15))
    
    def test_not_eligible_without_rrof(self):
        """Test deferral not eligible without real risk of forfeiture"""
        interest = ESSInterest(
            interest_id="TEST-002",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan",
            has_real_risk_forfeiture=False  # No RROF
        )
        
        result = self.service.check_deferred_taxing_point_eligibility(
            interest, self.current_date
        )
        
        self.assertFalse(result.is_eligible)
        self.assertIn("risk of forfeiture", result.notes.lower())
    
    def test_not_eligible_before_july_2009(self):
        """Test interest acquired before 1 July 2009 not in Division 83A"""
        interest = ESSInterest(
            interest_id="TEST-003",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2009, 6, 30),  # Before threshold
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan",
            has_real_risk_forfeiture=True
        )
        
        result = self.service.check_deferred_taxing_point_eligibility(
            interest, self.current_date
        )
        
        self.assertFalse(result.is_eligible)
        self.assertIn("before 1 July 2009", result.notes)
    
    def test_not_eligible_option_type(self):
        """Test that option type can be deferred eligible"""
        interest = ESSInterest(
            interest_id="TEST-004",
            ess_type=ESSType.OPTION,
            scheme_type=SchemeType.GENERAL,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("0.00"),
            market_value_acquisition=Decimal("0.00"),
            employer_name="TechCorp",
            plan_name="Plan",
            has_real_risk_forfeiture=True
        )
        
        result = self.service.check_deferred_taxing_point_eligibility(
            interest, self.current_date
        )
        
        self.assertTrue(result.is_eligible)
    
    def test_fifteen_year_limit(self):
        """Test 15-year deferral limit"""
        interest = ESSInterest(
            interest_id="TEST-005",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.GENERAL,
            acquisition_date=date(2009, 7, 1),  # Exactly at threshold
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan",
            has_real_risk_forfeiture=True
        )
        
        result = self.service.check_deferred_taxing_point_eligibility(
            interest, date(2024, 6, 30)
        )
        
        self.assertTrue(result.is_eligible)
        # Eligible until 1 July 2024 (15 years)
        self.assertEqual(result.eligible_until_date, date(2024, 7, 1))


class TestOptionExercise(unittest.TestCase):
    """Test option exercise scenarios"""
    
    def setUp(self):
        self.service = ESSService()
        self.option_interest = ESSInterest(
            interest_id="OPT-001",
            ess_type=ESSType.OPTION,
            scheme_type=SchemeType.GENERAL,
            acquisition_date=date(2022, 1, 1),
            amount_paid=Decimal("0.00"),
            market_value_acquisition=Decimal("0.00"),
            employer_name="TechCorp",
            plan_name="Executive Options",
            has_real_risk_forfeiture=True
        )
        self.option_details = OptionDetails(
            exercise_price=Decimal("15.00"),
            number_of_shares_underlying=1000
        )
    
    def test_standard_exercise(self):
        """Test standard option exercise"""
        exercise = OptionExerciseScenario(
            exercise_date=date(2024, 3, 15),
            exercise_type=OptionExerciseType.STANDARD_EXERCISE,
            market_value_at_exercise=Decimal("22.50"),
            shares_acquired=1000,
            exercise_price_paid=Decimal("15000.00")
        )
        
        result = self.service.calculate_option_exercise(
            self.option_interest,
            self.option_details,
            exercise
        )
        
        # Gain = (1000 × $22.50) - $15,000 = $22,500 - $15,000 = $7,500
        self.assertEqual(result["gain_on_exercise"], Decimal("7500.00"))
        # Cost base = $15,000 + $7,500 = $22,500
        self.assertEqual(result["cost_base"], Decimal("22500.00"))
        # Per share = $22,500 / 1000 = $22.50
        self.assertEqual(result["cost_base_per_share"], Decimal("22.50"))
        self.assertEqual(result["shares_acquired"], 1000)
    
    def test_cashless_exercise(self):
        """Test cashless exercise"""
        exercise = OptionExerciseScenario(
            exercise_date=date(2024, 3, 15),
            exercise_type=OptionExerciseType.CASHLESS_EXERCISE,
            market_value_at_exercise=Decimal("20.00"),
            shares_acquired=1000,
            exercise_price_paid=Decimal("0.00")  # No cash paid
        )
        
        result = self.service.calculate_option_exercise(
            self.option_interest,
            self.option_details,
            exercise
        )
        
        # Gain = (1000 × $20.00) - $0 = $20,000
        self.assertEqual(result["gain_on_exercise"], Decimal("20000.00"))
        # Cost base = $0 + $20,000 = $20,000
        self.assertEqual(result["cost_base"], Decimal("20000.00"))
    
    def test_option_exercise_not_applicable_to_share(self):
        """Test option exercise raises error for non-option interest"""
        share_interest = ESSInterest(
            interest_id="SHARE-001",
            ess_type=ESSType.DISCOUNT_SHARE,  # Not an option
            scheme_type=SchemeType.GENERAL,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        exercise = OptionExerciseScenario(
            exercise_date=date(2024, 3, 15),
            exercise_type=OptionExerciseType.STANDARD_EXERCISE,
            market_value_at_exercise=Decimal("10.00"),
            shares_acquired=100,
            exercise_price_paid=Decimal("1000.00")
        )
        
        with self.assertRaises(ValueError):
            self.service.calculate_option_exercise(
                share_interest,
                self.option_details,
                exercise
            )


class TestCGTCostBase(unittest.TestCase):
    """Test CGT cost base calculation"""
    
    def setUp(self):
        self.service = ESSService()
    
    def test_cost_base_with_discount(self):
        """Test cost base = amount paid + taxable discount"""
        interest = ESSInterest(
            interest_id="SHARE-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        taxable_discount = self.service.calculate_taxable_discount(interest)
        cost_base = self.service.calculate_cgt_cost_base(
            interest,
            taxable_discount
        )
        
        # Cost base = $5,000 + $1,500 = $6,500
        self.assertEqual(cost_base.cost_base_amount, Decimal("6500.00"))
        self.assertIn("amount_paid", cost_base.components)
        self.assertIn("taxable_discount", cost_base.components)
    
    def test_cost_base_with_additional_components(self):
        """Test cost base with additional components (brokerage, etc.)"""
        interest = ESSInterest(
            interest_id="SHARE-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.GENERAL,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("5000.00"),  # No discount
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        cost_base = self.service.calculate_cgt_cost_base(
            interest,
            additional_cost_components={
                "brokerage": Decimal("50.00"),
                "stamp_duty": Decimal("100.00")
            }
        )
        
        # Total = $5,000 + $50 + $100 = $5,150
        self.assertEqual(cost_base.cost_base_amount, Decimal("5150.00"))
        self.assertEqual(cost_base.components["brokerage"], Decimal("50.00"))
        self.assertEqual(cost_base.components["stamp_duty"], Decimal("100.00"))


class TestProcessStatement(unittest.TestCase):
    """Test batch statement processing"""
    
    def setUp(self):
        self.service = ESSService()
    
    def test_process_multiple_interests(self):
        """Test processing statement with multiple interests"""
        builder = ESSStatementBuilder(
            statement_id="STMT-2024-001",
            employer_name="TechCorp Australia",
            employer_abn="12345678901"
        )
        
        builder.add_discount_share(
            interest_id="SHARE-001",
            plan_name="Salary Sacrifice Plan",
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value=Decimal("7500.00"),
            scheme_type=SchemeType.SALARY_SACRIFICE,
            has_rrof=True
        )
        
        builder.add_discount_share(
            interest_id="SHARE-002",
            plan_name="General Plan",
            acquisition_date=date(2024, 1, 1),
            amount_paid=Decimal("10000.00"),
            market_value=Decimal("12000.00"),
            scheme_type=SchemeType.GENERAL,
            has_rrof=False
        )
        
        statement = builder.build()
        results = self.service.process_statement(statement)
        
        # Check totals
        self.assertEqual(len(results["interests"]), 2)
        # Total raw discount: $2,500 + $2,000 = $4,500
        self.assertEqual(
            results["summary"]["total_raw_discount"],
            Decimal("4500.00")
        )
        # Total exemption: $1,000 + $0 = $1,000 (only SALARY_SACRIFICE eligible)
        self.assertEqual(
            results["summary"]["total_exemption"],
            Decimal("1000.00")
        )
        # Total taxable: $1,500 + $2,000 = $3,500
        self.assertEqual(
            results["summary"]["total_taxable_discount"],
            Decimal("3500.00")
        )
        # Deferred interests: only 1 (SHARE-001 has RROF and on/after 1-7-2009)
        self.assertEqual(
            results["summary"]["interests_with_deferred_taxing_point"],
            1
        )


class TestTaxReturnFormatting(unittest.TestCase):
    """Test tax return formatting"""
    
    def setUp(self):
        self.service = ESSService()
    
    def test_format_for_tax_return(self):
        """Test formatting for tax return section 12"""
        builder = ESSStatementBuilder(
            statement_id="STMT-2024-001",
            employer_name="TechCorp Australia",
            employer_abn="12345678901"
        )
        
        builder.with_statement_date(date(2024, 6, 30))
        builder.with_tax_year("2024-25")
        
        builder.add_discount_share(
            interest_id="SHARE-001",
            plan_name="Salary Sacrifice Plan",
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value=Decimal("7500.00"),
            scheme_type=SchemeType.SALARY_SACRIFICE,
            has_rrof=True
        )
        
        statement = builder.build()
        tax_return = self.service.format_for_tax_return(statement)
        
        # Check structure
        self.assertEqual(tax_return["section"], 12)
        self.assertEqual(tax_return["income_type"], "Employee Share Scheme")
        self.assertEqual(tax_return["tax_year"], "2024-25")
        self.assertIn("employer", tax_return)
        self.assertIn("income_details", tax_return)
        self.assertIn("summary", tax_return)
        self.assertIn("cgt_notes", tax_return)
        
        # Check employer info
        self.assertEqual(tax_return["employer"]["name"], "TechCorp Australia")
        self.assertEqual(tax_return["employer"]["abn"], "12345678901")
        
        # Check summary
        self.assertEqual(
            tax_return["summary"]["total_income"],
            "1500.00"
        )
        self.assertEqual(
            tax_return["summary"]["total_exemptions"],
            "1000.00"
        )


class TestESSValidator(unittest.TestCase):
    """Test statement validation"""
    
    def test_validate_empty_statement(self):
        """Test validation catches empty statement"""
        statement = ESSStatement(
            statement_id="STMT-001",
            employer_name="TechCorp",
            employer_abn="12345678901",
            statement_date=date(2024, 6, 30),
            tax_year="2024-25"
        )
        
        errors = ESSValidator.validate_statement(statement)
        self.assertIn("no interests", errors[0].lower())
    
    def test_validate_invalid_abn(self):
        """Test validation catches invalid ABN"""
        statement = ESSStatement(
            statement_id="STMT-001",
            employer_name="TechCorp",
            employer_abn="123",  # Too short
            statement_date=date(2024, 6, 30),
            tax_year="2024-25",
            interests=[]
        )
        
        errors = ESSValidator.validate_statement(statement)
        self.assertTrue(any("ABN" in error for error in errors))
    
    def test_validate_valid_statement(self):
        """Test validation passes for valid statement"""
        builder = ESSStatementBuilder(
            statement_id="STMT-001",
            employer_name="TechCorp",
            employer_abn="12345678901"
        )
        
        builder.add_discount_share(
            interest_id="SHARE-001",
            plan_name="Plan",
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value=Decimal("7500.00")
        )
        
        statement = builder.build()
        errors = ESSValidator.validate_statement(statement)
        self.assertEqual(len(errors), 0)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""
    
    def setUp(self):
        self.service = ESSService()
    
    def test_discount_exactly_1000(self):
        """Test discount exactly equal to $1,000"""
        interest = ESSInterest(
            interest_id="TEST-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("6000.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("1000.00"))
        self.assertEqual(result.exemption_applied, Decimal("1000.00"))
        self.assertEqual(result.taxable_discount, Decimal("0.00"))
    
    def test_acquisition_on_july_1_2009(self):
        """Test interest acquired exactly on 1 July 2009"""
        interest = ESSInterest(
            interest_id="TEST-002",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2009, 7, 1),  # Exactly on threshold
            amount_paid=Decimal("5000.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan",
            has_real_risk_forfeiture=True
        )
        
        result = self.service.check_deferred_taxing_point_eligibility(interest)
        
        self.assertTrue(result.is_eligible)
    
    def test_zero_discount_share(self):
        """Test share with zero discount (market value = amount paid)"""
        interest = ESSInterest(
            interest_id="TEST-003",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("7500.00"),
            market_value_acquisition=Decimal("7500.00"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        self.assertEqual(result.raw_discount, Decimal("0.00"))
        self.assertEqual(result.taxable_discount, Decimal("0.00"))
        self.assertFalse(interest.has_discount)


class TestDecimalPrecision(unittest.TestCase):
    """Test decimal precision for monetary amounts"""
    
    def setUp(self):
        self.service = ESSService()
    
    def test_decimal_precision_in_discount(self):
        """Test that decimal calculations maintain precision"""
        interest = ESSInterest(
            interest_id="TEST-001",
            ess_type=ESSType.DISCOUNT_SHARE,
            scheme_type=SchemeType.SALARY_SACRIFICE,
            acquisition_date=date(2023, 7, 15),
            amount_paid=Decimal("3333.33"),
            market_value_acquisition=Decimal("5555.55"),
            employer_name="TechCorp",
            plan_name="Plan"
        )
        
        result = self.service.calculate_taxable_discount(interest)
        
        # Discount = $5555.55 - $3333.33 = $2222.22
        self.assertEqual(result.raw_discount, Decimal("2222.22"))
        # Exemption = $1000.00
        self.assertEqual(result.exemption_applied, Decimal("1000.00"))
        # Taxable = $1222.22
        self.assertEqual(result.taxable_discount, Decimal("1222.22"))


if __name__ == "__main__":
    unittest.main()
