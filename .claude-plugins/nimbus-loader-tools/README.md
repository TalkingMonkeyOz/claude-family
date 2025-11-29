# Nimbus Loader Tools Plugin

Professional-grade Nimbus User Loader sync and validation tools for Claude Code.

## Overview

The **nimbus-loader-tools** plugin provides three essential commands for managing user data synchronization from the Nimbus API:

1. **`/nimbus-test-connection`** - Diagnose Nimbus API connectivity
2. **`/nimbus-sync`** - Synchronize users from Nimbus to local database
3. **`/nimbus-validate-users`** - Validate user data integrity

## Installation

1. Clone or place this directory in your Claude Code `.claude-plugins` folder:
```
C:\Projects\claude-family\.claude-plugins\nimbus-loader-tools\
```

2. Verify the structure:
```
nimbus-loader-tools/
├── .claude-plugin/
│   └── plugin.json
├── commands/
│   ├── nimbus-sync.md
│   ├── nimbus-validate-users.md
│   └── nimbus-test-connection.md
└── README.md
```

3. Restart Claude Code to load the plugin.

4. Verify installation:
```
/nimbus-test-connection
```

## Quick Start

### 1. Test Connection

First, verify your Nimbus API is accessible:

```bash
/nimbus-test-connection
```

Expected output: ✓ ALL CHECKS PASSED

### 2. Sync Users

Once connection is confirmed, sync user data:

```bash
# Preview changes (recommended first time)
/nimbus-sync --dry-run

# Actually sync
/nimbus-sync

# Sync with verbose output
/nimbus-sync --verbose
```

### 3. Validate Data

After sync, validate the imported data:

```bash
# Run validation
/nimbus-validate-users

# Show detailed results
/nimbus-validate-users --verbose

# Auto-fix common issues
/nimbus-validate-users --fix

# Export report
/nimbus-validate-users --export ./report.json
```

## Command Reference

### nimbus-test-connection

Test Nimbus API connectivity and configuration.

```bash
/nimbus-test-connection [options]

Options:
  --verbose          Show detailed request/response info
  --timeout N        Connection timeout in seconds (default: 10)
  --endpoints LIST   Which endpoints to test (default: all)
  --output FORMAT    Output format: table, json, verbose (default: table)
  --save PATH        Save diagnostic report
```

**Use Cases:**
- Verify API credentials before sync
- Diagnose connectivity issues
- Check endpoint availability
- Performance benchmarking
- Generate diagnostic reports

### nimbus-sync

Synchronize user data from Nimbus API to local database.

```bash
/nimbus-sync [options]

Options:
  --dry-run          Preview changes without committing
  --incremental      Only sync modified records (default)
  --force            Full re-sync of all users
  --verbose          Show detailed progress
  --limit N          Limit to first N users (for testing)
```

**Use Cases:**
- Initial bulk user import
- Regular sync of user changes
- Scheduled automated sync
- Testing with sample data
- Recovery from failed sync

### nimbus-validate-users

Validate user data for integrity and compliance.

```bash
/nimbus-validate-users [options]

Options:
  --scope TYPE       What to validate: all, recent, source:nimbus
  --strict           Enable strict validation rules
  --fix              Auto-fix common issues
  --export PATH      Export report to file
  --verbose          Show all details
  --since DATE       Validate records after DATE (ISO 8601)
```

**Use Cases:**
- Data quality assurance
- Identify duplicate records
- Verify email formats
- Find data inconsistencies
- Compliance validation
- Post-sync verification

## Configuration

The plugin requires environment variables or configuration file:

```env
# Required
NIMBUS_API_URL=https://api.nimbus.example.com
NIMBUS_API_KEY=sk_xxxxxxxxxxxxx
NIMBUS_API_SECRET=secret_xxxxxxxxxxxxx

# Optional
NIMBUS_API_TIMEOUT=30
NIMBUS_PROXY_URL=
NIMBUS_VERIFY_SSL=true
```

### Database Configuration

Synced users are stored in:
```
Database: ai_company_foundation
Schema: public
Table: users
```

Columns:
- `id` - Local primary key
- `external_id` - Nimbus UUID
- `email` - User email (unique)
- `name` - Full name
- `status` - active, inactive, pending, deleted
- `metadata` - JSON: raw Nimbus data
- `synced_at` - Last sync timestamp
- `synced_from` - Source system identifier
- `created_at` - Record creation time
- `updated_at` - Last modification time

## Workflow Examples

### Daily Automated Sync

```bash
# In cron or scheduler
/nimbus-sync --incremental --verbose
/nimbus-validate-users --scope recent
```

### Initial Import

```bash
# Step 1: Test connection
/nimbus-test-connection

# Step 2: Preview sync
/nimbus-sync --dry-run --limit 100

# Step 3: Run full sync
/nimbus-sync --force --verbose

# Step 4: Validate all data
/nimbus-validate-users --scope all --strict

# Step 5: Export validation report
/nimbus-validate-users --export ./initial-validation.json
```

### Troubleshooting Failed Sync

```bash
# Step 1: Check connection
/nimbus-test-connection --verbose

# Step 2: Validate recent changes
/nimbus-validate-users --since 2025-10-22T00:00:00Z

# Step 3: Check what's different
/nimbus-sync --dry-run --verbose

# Step 4: Review and fix any data issues
# (manually or with --fix flag)

# Step 5: Retry sync
/nimbus-sync --incremental
```

### Data Quality Check

```bash
# Full validation with auto-fix
/nimbus-validate-users --scope all --strict --fix --export ./pre-audit.json

# Review report
# (examine ./pre-audit.json manually)

# Manual fixes if needed
# (use database tools to update records)

# Final validation
/nimbus-validate-users --scope all --export ./post-audit.json
```

## Features

### Data Sync
- ✓ Full and incremental sync modes
- ✓ Automatic pagination handling (5000 users/request)
- ✓ Batch inserts for performance (1000 users/batch)
- ✓ Transactional integrity
- ✓ Timestamp tracking
- ✓ Dry-run preview mode

### Validation
- ✓ Required field checks
- ✓ Email format validation
- ✓ Duplicate detection
- ✓ Referential integrity checks
- ✓ Data consistency validation
- ✓ Strict and lenient modes
- ✓ Auto-fix capabilities

### Diagnostics
- ✓ Connection testing
- ✓ Endpoint verification
- ✓ Response time measurement
- ✓ Permission validation
- ✓ SSL/TLS verification
- ✓ Detailed error reporting

### Reporting
- ✓ Table format output
- ✓ JSON export
- ✓ Detailed verbose output
- ✓ Actionable recommendations
- ✓ Audit trail logging

## Troubleshooting

### Connection Issues

**Error: "Connection timeout"**
- Check network connectivity: `ping api.nimbus.example.com`
- Verify firewall allows outbound HTTPS
- Check `NIMBUS_API_URL` setting

**Error: "401 Unauthorized"**
- Verify `NIMBUS_API_KEY` is correct
- Verify `NIMBUS_API_SECRET` is correct
- Regenerate API credentials if expired

**Error: "403 Forbidden"**
- API key lacks required permissions
- Verify permissions in Nimbus admin panel
- Request admin to grant `users:read` and `users:write`

### Sync Issues

**Error: "No new users synced"**
- Try `/nimbus-sync --force` for full re-sync
- Check if users were modified since last sync
- Run `/nimbus-validate-users` to check for errors

**Error: "Duplicate email detected"**
- Run `/nimbus-validate-users --fix` to auto-correct
- Review similar emails manually in database
- Update Nimbus records if duplicates are errors

### Validation Issues

**Many missing emails**
- Check if Nimbus records have email addresses
- Map correct Nimbus field to email column
- Coordinate with Nimbus administrator

**Future timestamps**
- Likely clock skew on Nimbus server
- Use `/nimbus-validate-users --fix` to correct
- Verify server time synchronization

## Support

For issues or questions:
1. Run `/nimbus-test-connection --verbose` to diagnose
2. Check logs in `.claude-plugins/nimbus-loader-tools/logs/`
3. Review validation report: `/nimbus-validate-users --export ./report.json`
4. Contact Nimbus integration team

## Version History

- **1.0.0** (2025-10-23) - Initial release
  - nimbus-test-connection command
  - nimbus-sync command
  - nimbus-validate-users command
  - Comprehensive documentation

## License

Claude Family Infrastructure - Internal Use

## Author

Claude Family
