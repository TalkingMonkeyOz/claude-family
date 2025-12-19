"""
ESS Service Integration Examples

Real-world examples of integrating the ESS Service into your ATO Tax Agent backend.

Includes:
1. Parsing employer ESS statements
2. Batch processing multiple statements  
3. Tax return integration
4. API endpoints
5. Database storage
6. Audit trail generation
"""

import json
from datetime import date, datetime
from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import asdict

from ess_service import (
    ESSService,
    ESSStatement,
    ESSStatementBuilder,
    ESSType,
    SchemeType,
    ESSValidator,
)


# =============================================================================
# Example 1: Parse ESS Statement from Employer JSON
# =============================================================================

def parse_employer_ess_statement(json_data: str) -> ESSStatement:
    """
    Parse ESS statement from employer-provided JSON format
    
    Expected JSON format:
    {
      "statement_id": "STMT-2024-001",
      "employer_name": "TechCorp Australia",
      "employer_abn": "12345678901",
      "statement_date": "2024-06-30",
      "tax_year": "2024-25",
      "interests": [
        {
          "interest_id": "SHARE-001",
          "type": "discount_share",
          "scheme_type": "salary_sacrifice",
          "acquisition_date": "2023-07-15",
          "amount_paid": "5000.00",
          "market_value": "7500.00",
          "has_rrof": true,
          "plan_name": "Salary Sacrifice Plan"
        }
      ]
    }
    """
    data = json.loads(json_data)
    
    builder = ESSStatementBuilder(
        statement_id=data["statement_id"],
        employer_name=data["employer_name"],
        employer_abn=data["employer_abn"]
    )
    
    builder.with_statement_date(date.fromisoformat(data["statement_date"]))
    builder.with_tax_year(data["tax_year"])
    
    for interest_data in data.get("interests", []):
        interest_type = ESSType[interest_data["type"].upper()]
        scheme_type = SchemeType[interest_data["scheme_type"].upper()]
        
        if interest_type == ESSType.DISCOUNT_SHARE:
            builder.add_discount_share(
                interest_id=interest_data["interest_id"],
                plan_name=interest_data["plan_name"],
                acquisition_date=date.fromisoformat(interest_data["acquisition_date"]),
                amount_paid=Decimal(interest_data["amount_paid"]),
                market_value=Decimal(interest_data["market_value"]),
                scheme_type=scheme_type,
                has_rrof=interest_data.get("has_rrof", False)
            )
        elif interest_type == ESSType.OPTION:
            builder.add_option(
                interest_id=interest_data["interest_id"],
                plan_name=interest_data["plan_name"],
                acquisition_date=date.fromisoformat(interest_data["acquisition_date"]),
                exercise_price=Decimal(interest_data["exercise_price"]),
                number_of_shares=interest_data["number_of_shares"],
                scheme_type=scheme_type,
                has_rrof=interest_data.get("has_rrof", False)
            )
    
    return builder.build()


# Example usage
employer_json = '''
{
  "statement_id": "STMT-2024-001",
  "employer_name": "TechCorp Australia",
  "employer_abn": "12345678901",
  "statement_date": "2024-06-30",
  "tax_year": "2024-25",
  "interests": [
    {
      "interest_id": "SHARE-001",
      "type": "DISCOUNT_SHARE",
      "scheme_type": "SALARY_SACRIFICE",
      "acquisition_date": "2023-07-15",
      "amount_paid": "5000.00",
      "market_value": "7500.00",
      "has_rrof": true,
      "plan_name": "Salary Sacrifice Plan"
    },
    {
      "interest_id": "OPTION-001",
      "type": "OPTION",
      "scheme_type": "GENERAL",
      "acquisition_date": "2022-01-01",
      "exercise_price": "15.00",
      "number_of_shares": 1000,
      "has_rrof": true,
      "plan_name": "Executive Options"
    }
  ]
}
'''

if __name__ == "__main__":
    # Parse and validate
    statement = parse_employer_ess_statement(employer_json)
    errors = ESSValidator.validate_statement(statement)
    
    if not errors:
        print("✅ Statement parsed and validated successfully")
    else:
        print("❌ Validation errors:")
        for error in errors:
            print(f"  - {error}")


# =============================================================================
# Example 2: Tax Return Section 12 Builder
# =============================================================================

class TaxReturnBuilder:
    """Build complete tax return with ESS information"""
    
    def __init__(self, tfn: str, tax_year: str = "2024-25"):
        self.tfn = tfn
        self.tax_year = tax_year
        self.sections = {}
        self.ess_service = ESSService()
    
    def add_ess_statements(self, statements: List[ESSStatement]) -> "TaxReturnBuilder":
        """Add ESS statements to tax return"""
        ess_entries = []
        
        for statement in statements:
            # Validate
            errors = ESSValidator.validate_statement(statement)
            if errors:
                raise ValueError(f"Invalid ESS statement {statement.statement_id}: {errors}")
            
            # Format for tax return
            entry = self.ess_service.format_for_tax_return(statement, self.tax_year)
            ess_entries.append(entry)
        
        self.sections[12] = {
            "section": 12,
            "income_type": "Employee Share Schemes",
            "entries": ess_entries
        }
        
        return self
    
    def calculate_section_12_totals(self) -> Dict:
        """Calculate totals for Section 12"""
        if 12 not in self.sections:
            return {}
        
        total_income = Decimal("0")
        total_exemptions = Decimal("0")
        deferred_count = 0
        
        for entry in self.sections[12]["entries"]:
            summary = entry["summary"]
            total_income += Decimal(summary["total_income"])
            total_exemptions += Decimal(summary["total_exemptions"])
            deferred_count += summary["total_deferred_interests"]
        
        return {
            "total_income": str(total_income),
            "total_exemptions": str(total_exemptions),
            "deferred_interests": deferred_count
        }
    
    def build(self) -> Dict:
        """Build tax return"""
        tax_return = {
            "tfn": self.tfn,
            "tax_year": self.tax_year,
            "prepared_date": datetime.now().isoformat(),
            "sections": self.sections
        }
        
        # Add Section 12 totals
        if 12 in self.sections:
            tax_return["sections"][12]["totals"] = self.calculate_section_12_totals()
        
        return tax_return


# Example usage
if __name__ == "__main__":
    # Build tax return with ESS
    builder = TaxReturnBuilder(tfn="123456789", tax_year="2024-25")
    
    # Parse statements
    statement1 = parse_employer_ess_statement(employer_json)
    
    # Add to return
    builder.add_ess_statements([statement1])
    
    # Build
    tax_return = builder.build()
    
    print(json.dumps(tax_return, indent=2, default=str))


# =============================================================================
# Example 3: Batch Processing Multiple Employers
# =============================================================================

class ESSTaxReturnProcessor:
    """Process ESS information for complete tax return"""
    
    def __init__(self, tfn: str, tax_year: str = "2024-25"):
        self.tfn = tfn
        self.tax_year = tax_year
        self.service = ESSService()
        self.statements: List[ESSStatement] = []
        self.results = {}
    
    def add_statement(self, statement: ESSStatement) -> "ESSTaxReturnProcessor":
        """Add ESS statement"""
        errors = ESSValidator.validate_statement(statement)
        if errors:
            raise ValueError(f"Invalid statement: {errors}")
        
        self.statements.append(statement)
        return self
    
    def process_all(self) -> Dict:
        """Process all statements and generate tax return data"""
        self.results = {
            "tfn": self.tfn,
            "tax_year": self.tax_year,
            "prepared_date": datetime.now().isoformat(),
            "employers": [],
            "summary": {
                "total_raw_discount": Decimal("0"),
                "total_exemption": Decimal("0"),
                "total_taxable_income": Decimal("0"),
                "total_deferred_eligible": Decimal("0"),
                "employer_count": 0
            }
        }
        
        for statement in self.statements:
            # Process statement
            processed = self.service.process_statement(statement)
            
            # Format for tax return
            tax_return_entry = self.service.format_for_tax_return(statement)
            
            # Add to results
            employer_result = {
                "employer": statement.employer_name,
                "abn": statement.employer_abn,
                "statement_id": statement.statement_id,
                "statement_date": statement.statement_date.isoformat(),
                "interests_count": len(statement.interests),
                "tax_return_entry": tax_return_entry,
                "detailed_breakdown": processed
            }
            
            self.results["employers"].append(employer_result)
            
            # Update summary
            summary = processed["summary"]
            self.results["summary"]["total_raw_discount"] += Decimal(summary["total_raw_discount"])
            self.results["summary"]["total_exemption"] += Decimal(summary["total_exemption"])
            self.results["summary"]["total_taxable_income"] += Decimal(summary["total_taxable_discount"])
            self.results["summary"]["total_deferred_eligible"] += Decimal(summary.get("total_deferred", 0))
            self.results["summary"]["employer_count"] += 1
        
        return self.results
    
    def export_tax_return_format(self) -> Dict:
        """Export in standard tax return format"""
        if not self.results:
            self.process_all()
        
        return {
            "tfn": self.tfn,
            "tax_year": self.tax_year,
            "section_12": {
                "section": 12,
                "income_type": "Employee Share Schemes",
                "total_income": str(self.results["summary"]["total_taxable_income"]),
                "total_exemptions": str(self.results["summary"]["total_exemption"]),
                "employers": [
                    {
                        "name": emp["employer"],
                        "abn": emp["abn"],
                        "income": emp["tax_return_entry"]["summary"]["total_income"],
                        "exemptions": emp["tax_return_entry"]["summary"]["total_exemptions"]
                    }
                    for emp in self.results["employers"]
                ]
            }
        }
    
    def export_json(self) -> str:
        """Export complete results as JSON"""
        if not self.results:
            self.process_all()
        
        # Convert Decimal to string for JSON serialization
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return str(obj)
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(self.results, indent=2, default=decimal_default)


# Example usage
if __name__ == "__main__":
    # Parse multiple statements
    statement1 = parse_employer_ess_statement(employer_json)
    
    # Process
    processor = ESSTaxReturnProcessor(tfn="123456789", tax_year="2024-25")
    processor.add_statement(statement1)
    
    results = processor.process_all()
    
    print("=== Summary ===")
    print(f"Total raw discount: ${results['summary']['total_raw_discount']}")
    print(f"Total exemption: ${results['summary']['total_exemption']}")
    print(f"Total taxable income: ${results['summary']['total_taxable_income']}")
    
    print("\n=== Tax Return Format ===")
    tax_format = processor.export_tax_return_format()
    print(json.dumps(tax_format, indent=2, default=str))


# =============================================================================
# Example 4: Flask API Integration
# =============================================================================

class ESSAPIHandler:
    """Handle ESS calculations via API"""
    
    def __init__(self):
        self.service = ESSService()
    
    def calculate_discount(self, request_data: Dict) -> Dict:
        """
        API endpoint: POST /api/ess/calculate-discount
        
        Request:
        {
            "interest_id": "SHARE-001",
            "ess_type": "DISCOUNT_SHARE",
            "scheme_type": "SALARY_SACRIFICE",
            "acquisition_date": "2023-07-15",
            "amount_paid": "5000.00",
            "market_value": "7500.00"
        }
        
        Response:
        {
            "interest_id": "SHARE-001",
            "raw_discount": "2500.00",
            "exemption_applied": "1000.00",
            "taxable_discount": "1500.00",
            "eligible_for_exemption": true,
            "notes": "..."
        }
        """
        try:
            interest = ESSInterest(
                interest_id=request_data["interest_id"],
                ess_type=ESSType[request_data["ess_type"]],
                scheme_type=SchemeType[request_data["scheme_type"]],
                acquisition_date=date.fromisoformat(request_data["acquisition_date"]),
                amount_paid=Decimal(request_data["amount_paid"]),
                market_value_acquisition=Decimal(request_data["market_value"]),
                employer_name=request_data.get("employer_name", "Unknown"),
                plan_name=request_data.get("plan_name", "Unknown")
            )
            
            result = self.service.calculate_taxable_discount(interest)
            
            return {
                "success": True,
                "interest_id": interest.interest_id,
                "raw_discount": str(result.raw_discount),
                "exemption_applied": str(result.exemption_applied),
                "taxable_discount": str(result.taxable_discount),
                "eligible_for_exemption": result.is_eligible_for_exemption,
                "notes": result.exemption_notes
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_deferral(self, request_data: Dict) -> Dict:
        """
        API endpoint: POST /api/ess/check-deferral
        """
        try:
            interest = ESSInterest(
                interest_id=request_data["interest_id"],
                ess_type=ESSType[request_data["ess_type"]],
                scheme_type=SchemeType[request_data["scheme_type"]],
                acquisition_date=date.fromisoformat(request_data["acquisition_date"]),
                amount_paid=Decimal(request_data["amount_paid"]),
                market_value_acquisition=Decimal(request_data["market_value"]),
                employer_name=request_data.get("employer_name", "Unknown"),
                plan_name=request_data.get("plan_name", "Unknown"),
                has_real_risk_forfeiture=request_data.get("has_rrof", False)
            )
            
            result = self.service.check_deferred_taxing_point_eligibility(interest)
            
            return {
                "success": True,
                "interest_id": interest.interest_id,
                "is_eligible": result.is_eligible,
                "eligible_until": result.eligible_until_date.isoformat() if result.eligible_until_date else None,
                "notes": result.notes
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_statement_api(self, statement_data: Dict) -> Dict:
        """
        API endpoint: POST /api/ess/process-statement
        
        Processes entire ESS statement and returns tax return format
        """
        try:
            # Parse statement
            statement = parse_employer_ess_statement(json.dumps(statement_data))
            
            # Validate
            errors = ESSValidator.validate_statement(statement)
            if errors:
                return {
                    "success": False,
                    "errors": errors
                }
            
            # Process
            results = self.service.process_statement(statement)
            
            # Format for tax return
            tax_return = self.service.format_for_tax_return(statement)
            
            return {
                "success": True,
                "statement_id": statement.statement_id,
                "summary": results["summary"],
                "tax_return_entry": tax_return,
                "detailed_results": results
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# =============================================================================
# Example 5: Audit Trail & Compliance Logging
# =============================================================================

class ESSAuditLogger:
    """Log ESS calculations for compliance and audit"""
    
    def __init__(self, tfn: str):
        self.tfn = tfn
        self.logs: List[Dict] = []
    
    def log_calculation(
        self,
        calculation_type: str,
        interest_id: str,
        inputs: Dict,
        outputs: Dict,
        exemption_applied: bool = False
    ) -> None:
        """Log a calculation for audit trail"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tfn": self.tfn,
            "calculation_type": calculation_type,
            "interest_id": interest_id,
            "inputs": {k: str(v) for k, v in inputs.items()},  # Stringify decimals
            "outputs": {k: str(v) for k, v in outputs.items()},
            "exemption_applied": exemption_applied,
            "notes": ""
        }
        
        self.logs.append(log_entry)
    
    def log_discount_calculation(
        self,
        interest_id: str,
        raw_discount: Decimal,
        exemption_applied: Decimal,
        taxable_discount: Decimal
    ) -> None:
        """Log discount calculation"""
        self.log_calculation(
            calculation_type="DISCOUNT_CALCULATION",
            interest_id=interest_id,
            inputs={
                "raw_discount": raw_discount
            },
            outputs={
                "exemption_applied": exemption_applied,
                "taxable_discount": taxable_discount
            },
            exemption_applied=exemption_applied > 0
        )
    
    def log_deferral_check(
        self,
        interest_id: str,
        is_eligible: bool,
        reason: str,
        eligible_until: Optional[date] = None
    ) -> None:
        """Log deferral eligibility check"""
        self.log_calculation(
            calculation_type="DEFERRAL_ELIGIBILITY",
            interest_id=interest_id,
            inputs={"interest_id": interest_id},
            outputs={
                "is_eligible": is_eligible,
                "reason": reason,
                "eligible_until": eligible_until.isoformat() if eligible_until else None
            }
        )
    
    def export_audit_trail(self) -> str:
        """Export audit trail as JSON"""
        return json.dumps(self.logs, indent=2)


# Example usage
if __name__ == "__main__":
    # Create audit logger
    logger = ESSAuditLogger(tfn="123456789")
    
    # Log calculations
    logger.log_discount_calculation(
        interest_id="SHARE-001",
        raw_discount=Decimal("2500.00"),
        exemption_applied=Decimal("1000.00"),
        taxable_discount=Decimal("1500.00")
    )
    
    logger.log_deferral_check(
        interest_id="SHARE-001",
        is_eligible=True,
        reason="Has real risk of forfeiture, acquired after 1 July 2009",
        eligible_until=date(2038, 7, 15)
    )
    
    print(logger.export_audit_trail())


# =============================================================================
# Example 6: Complete End-to-End Workflow
# =============================================================================

def complete_workflow_example():
    """Complete workflow from ESS statement to tax return"""
    
    # Step 1: Parse ESS statement from employer
    print("=== Step 1: Parse ESS Statement ===")
    statement = parse_employer_ess_statement(employer_json)
    print(f"✓ Parsed statement: {statement.statement_id}")
    print(f"  Employer: {statement.employer_name}")
    print(f"  Interests: {len(statement.interests)}")
    
    # Step 2: Validate statement
    print("\n=== Step 2: Validate Statement ===")
    errors = ESSValidator.validate_statement(statement)
    if errors:
        print(f"✗ Validation errors: {errors}")
        return
    print("✓ Statement validated successfully")
    
    # Step 3: Calculate all positions
    print("\n=== Step 3: Calculate ESS Positions ===")
    service = ESSService()
    results = service.process_statement(statement)
    print(f"✓ Processed {len(results['interests'])} interests")
    print(f"  Total raw discount: ${results['summary']['total_raw_discount']}")
    print(f"  Total exemption: ${results['summary']['total_exemption']}")
    print(f"  Total taxable income: ${results['summary']['total_taxable_discount']}")
    
    # Step 4: Audit logging
    print("\n=== Step 4: Audit Logging ===")
    logger = ESSAuditLogger(tfn="123456789")
    for interest_result in results["interests"]:
        if "discount" in interest_result:
            discount = interest_result["discount"]
            logger.log_discount_calculation(
                interest_id=interest_result["interest_id"],
                raw_discount=Decimal(discount["raw_discount"]),
                exemption_applied=Decimal(discount["exemption_applied"]),
                taxable_discount=Decimal(discount["taxable_discount"])
            )
    print("✓ Audit trail created")
    
    # Step 5: Format for tax return
    print("\n=== Step 5: Format Tax Return ===")
    tax_return_entry = service.format_for_tax_return(statement)
    print(f"✓ Section 12 entry created")
    print(f"  Total income: ${tax_return_entry['summary']['total_income']}")
    
    # Step 6: Build complete tax return
    print("\n=== Step 6: Build Complete Tax Return ===")
    processor = ESSTaxReturnProcessor(tfn="123456789")
    processor.add_statement(statement)
    final_results = processor.process_all()
    print(f"✓ Tax return built for {final_results['summary']['employer_count']} employer(s)")
    
    # Step 7: Export
    print("\n=== Step 7: Export Results ===")
    tax_format = processor.export_tax_return_format()
    audit_trail = logger.export_audit_trail()
    print("✓ Exported tax return format and audit trail")
    
    return {
        "statement": statement,
        "results": results,
        "tax_return": tax_return_entry,
        "final_results": final_results,
        "audit_trail": audit_trail
    }


if __name__ == "__main__":
    print("=" * 70)
    print("ESS SERVICE - COMPLETE END-TO-END WORKFLOW")
    print("=" * 70)
    
    workflow = complete_workflow_example()
    
    print("\n" + "=" * 70)
    print("WORKFLOW COMPLETE")
    print("=" * 70)
