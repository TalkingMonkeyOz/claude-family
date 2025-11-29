---
name: nimbus-validate-users
description: Validate user data in the database for integrity and compliance
category: nimbus
tags:
  - validation
  - users
  - data-quality
  - compliance
---

# Nimbus User Validation

Validate user data in the database for completeness, format compliance, and business rule adherence.

## Overview

This command performs comprehensive validation of user data:
- Checks all required fields are present
- Validates email formats and uniqueness
- Detects duplicate entries
- Verifies referential integrity
- Checks for data inconsistencies
- Generates validation report with actionable fixes

## Usage

```bash
/nimbus-validate-users [options]
```

### Options

- `--scope [all|recent|source:nimbus]` - What to validate (default: recent changes)
- `--strict` - Enable strict validation rules
- `--fix` - Automatically fix common issues
- `--export PATH` - Export validation report to file
- `--verbose` - Show all validation details
- `--since DATE` - Validate users modified after DATE (ISO 8601)

### Examples

```bash
# Validate recent changes (default)
/nimbus-validate-users

# Validate all users
/nimbus-validate-users --scope all

# Validate with strict rules
/nimbus-validate-users --strict

# Fix issues automatically
/nimbus-validate-users --fix

# Export report
/nimbus-validate-users --export ./validation-report.json

# Validate users modified in last 24 hours
/nimbus-validate-users --since 2025-10-22T00:00:00Z
```

## Validation Rules

### Required Fields
- ✓ `email` - Must be present
- ✓ `name` - Must be present and non-empty
- ✓ `external_id` - Must be present (Nimbus UUID)
- ✓ `status` - Must be one of: active, inactive, pending, deleted

### Email Validation
- ✓ Format: Valid RFC 5322 email address
- ✓ Uniqueness: No duplicate emails in database
- ✓ Whitespace: Trimmed, no leading/trailing spaces
- ✓ Case: Normalized to lowercase
- ✓ Domain: Known domain (optional strict mode)

### Data Consistency
- ✓ External ID uniqueness: No duplicate Nimbus IDs
- ✓ Referential integrity: Owner/group IDs point to valid records
- ✓ Status transitions: Valid status change history
- ✓ Timestamps: `created_at` ≤ `updated_at` ≤ `synced_at`
- ✓ No future timestamps

### Duplicate Detection
- ✓ Same external_id: Flags multiple records from Nimbus
- ✓ Same email: Identifies duplicate accounts
- ✓ Same name + domain: Suspicious duplicates
- ✓ Partial matches: Similar names/emails

### Strict Mode Additional Rules
- ✓ Name format: Must match pattern (no excessive punctuation)
- ✓ Phone: Optional but if present, must be valid
- ✓ Address: Optional but if present, must have all parts
- ✓ Department: Must be in list of valid departments
- ✓ Manager: If assigned, must exist in database

## Validation Report

Output includes:

```
╔════════════════════════════════════════════════════════════════╗
║                   USER VALIDATION REPORT                       ║
╠════════════════════════════════════════════════════════════════╣
║ Total Records Checked:        12,547                           ║
║ Valid Records:                12,450 (99.2%)                   ║
║ Invalid Records:              97 (0.8%)                        ║
╠════════════════════════════════════════════════════════════════╣
║ ERRORS (97)                                                     ║
║  • Missing email: 23 records                                   ║
║  • Invalid email format: 18 records                            ║
║  • Duplicate email: 12 records                                 ║
║  • Invalid status: 8 records                                   ║
║  • Timestamp issues: 14 records                                ║
║  • Future timestamps: 22 records                               ║
╠════════════════════════════════════════════════════════════════╣
║ WARNINGS (156)                                                  ║
║  • Suspicious name similarity: 89 records                      ║
║  • Similar email (possible duplicate): 45 records             ║
║  • Very long name: 22 records                                  ║
╠════════════════════════════════════════════════════════════════╣
║ RECOMMENDATIONS                                                 ║
║  1. Fix 23 missing emails before next sync                    ║
║  2. Review 12 duplicate emails manually                       ║
║  3. Correct 22 future-dated records                           ║
║  4. Investigate 45 similar email addresses                    ║
╚════════════════════════════════════════════════════════════════╝
```

## Auto-Fix Capabilities

With `--fix` flag, automatically:
- ✓ Normalize email addresses (lowercase, trim)
- ✓ Fix obvious timestamp issues (swap if reversed)
- ✓ Remove leading/trailing whitespace
- ✓ Correct common status typos
- ✓ Deduplicate exact matches
- ✓ Mark future-dated records with warning

## Export Formats

Use `--export` to save detailed report:

```json
{
  "validation_run": "2025-10-23T14:30:00Z",
  "scope": "recent",
  "summary": {
    "total_checked": 12547,
    "valid": 12450,
    "invalid": 97
  },
  "errors": [
    {
      "record_id": "usr_12345",
      "email": null,
      "error_type": "missing_field",
      "field": "email",
      "severity": "error",
      "message": "Email is required"
    }
  ],
  "warnings": [],
  "recommendations": []
}
```

## Related Commands

- `/nimbus-sync` - Sync users from Nimbus (before validation)
- `/nimbus-test-connection` - Verify API connectivity
- `/nimbus-audit-changes` - Audit user record modifications
