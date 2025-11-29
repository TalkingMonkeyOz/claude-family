# ATO Tax Tools Plugin

Comprehensive validation and compliance tools for Australian tax calculations and ATO regulations.

**Version**: 1.0.0  
**Author**: Claude Family  
**Purpose**: Tax calculation validation, compliance verification, and scenario testing

## Overview

The ATO Tax Tools plugin provides three complementary commands for validating tax calculations, testing scenarios, and ensuring full ATO compliance.

## Commands

### 1. `/ato-validate`
Validates tax calculations against ATO rules and edge cases.

**Features**:
- Income threshold validation
- Deduction compliance checking
- Tax offset verification
- Medicare levy calculation validation
- Edge case testing (bracket boundaries, maximum deductions)

**Use When**: You need to verify a specific tax calculation is correct and compliant.

### 2. `/ato-test-scenarios`
Generates and executes test scenarios through the tax calculation engine.

**Features**:
- Multiple scenario types (individuals, high-income earners, special circumstances)
- Edge case scenarios
- Predefined test suites (Basic, Intermediate, Advanced, Compliance)
- Comparison of expected vs actual results
- Detailed pass/fail reporting

**Use When**: You need to test the tax calculation engine against realistic scenarios or validate a calculation approach.

### 3. `/ato-compliance-check`
Verifies all tax forms and calculations meet ATO specifications.

**Features**:
- Data format validation
- Tax form compliance checking
- Calculation rules verification
- ATO rule compliance assessment
- Three-level compliance reporting (Critical, Warning, Information)
- Risk assessment and audit trigger detection

**Use When**: You need to ensure complete ATO compliance before filing or in response to audit requirements.

## Installation

The plugin is located at:
```
C:\Projects\claude-family\.claude-plugins\ato-tax-tools\
```

## Usage Workflow

### For Single Calculation Validation
```
1. Use /ato-validate
2. Provide income, deductions, and offsets
3. Receive validation report with any issues
```

### For Testing Tax Logic
```
1. Use /ato-test-scenarios
2. Select test suite (or create custom)
3. Review comparison of expected vs actual results
4. Iterate on calculation logic
```

### For Compliance Certification
```
1. Use /ato-compliance-check
2. Provide complete tax return data
3. Receive compliance audit report
4. Address any critical or warning items
5. File with confidence
```

### Combined Workflow
```
1. /ato-test-scenarios (to validate logic)
2. /ato-validate (to check specific calculations)
3. /ato-compliance-check (before filing)
```

## Key Features

✅ **ATO Rule Implementation**: Current 2024-25 tax year rules  
✅ **Comprehensive Coverage**: Individuals and corporate tax  
✅ **Edge Case Testing**: Bracket boundaries, maximums, phase-outs  
✅ **Detailed Reporting**: Clear pass/fail with explanations  
✅ **Risk Assessment**: Audit trigger detection  
✅ **Scenario Testing**: Pre-built and custom test cases  

## Common Scenarios

### Individual Tax Return Validation
1. Run `/ato-test-scenarios` with individual income scenario
2. Run `/ato-validate` on actual return data
3. Run `/ato-compliance-check` before filing

### Complex Multi-Income Scenario
1. Use `/ato-test-scenarios` - Intermediate Suite
2. Validate capital gains treatment with `/ato-validate`
3. Check full compliance with `/ato-compliance-check`

### Corporate Tax Compliance
1. Run `/ato-compliance-check` - Corporate mode
2. Validate specific calculations with `/ato-validate`
3. Run `/ato-test-scenarios` - Advanced Suite

## ATO References

This plugin implements current guidance from:
- Income Tax Assessment Acts 1936 & 1997
- Tax Administration Act 1953
- ATO Compliance Rules
- ATO Law Administration Rules
- Current Tax Year (2024-25) Rates and Thresholds

## Technical Details

- **Format**: Claude Code Plugin
- **Plugin Type**: Commands
- **Configuration**: `.claude-plugin/plugin.json`
- **Commands Directory**: `./commands/`

## Support and Updates

For issues, feature requests, or updates:
1. Check the command documentation (see Commands section above)
2. Review recent ATO guidance changes
3. Test with `/ato-test-scenarios` before reporting issues

## Related Projects

This plugin is part of the Claude Family infrastructure and integrates with:
- ATO Tax Agent application (claude-pm project)
- Tax compliance workflows
- Financial advisory systems

---

**Last Updated**: October 2025  
**Status**: Production Ready
