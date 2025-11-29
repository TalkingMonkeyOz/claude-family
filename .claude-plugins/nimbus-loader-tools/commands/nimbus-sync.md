---
name: nimbus-sync
description: Sync users from Nimbus API to local database
category: nimbus
tags:
  - sync
  - users
  - database
  - integration
---

# Nimbus User Sync

Synchronize user data from the Nimbus API to the local database.

## Overview

This command performs a complete sync of user data from the Nimbus API:
- Connects to Nimbus API using configured credentials
- Fetches all active user records
- Maps Nimbus user data to local database schema
- Updates existing users and creates new ones
- Validates data during import
- Reports sync results with success/failure counts

## Usage

```bash
/nimbus-sync [options]
```

### Options

- `--dry-run` - Preview changes without committing to database
- `--incremental` - Only sync users modified since last sync
- `--force` - Force full re-sync regardless of timestamp
- `--verbose` - Show detailed progress output
- `--limit N` - Limit sync to first N users (for testing)

### Examples

```bash
# Preview sync without committing
/nimbus-sync --dry-run

# Incremental sync (default)
/nimbus-sync

# Full re-sync all users
/nimbus-sync --force

# Sync with detailed output
/nimbus-sync --verbose

# Test with first 10 users
/nimbus-sync --limit 10
```

## What Happens

1. **Connection Check**: Verifies Nimbus API connectivity and authentication
2. **Fetch Users**: Retrieves user list from Nimbus (with pagination if needed)
3. **Data Mapping**: Transforms Nimbus data to local schema:
   - `nimbus_id` → database `external_id`
   - `email_address` → `email`
   - `first_name`, `last_name` → `name`
   - `status` → normalized status values
   - Timestamps and metadata preserved
4. **Validation**: Checks each record for required fields and format
5. **Database Update**: 
   - Inserts new users
   - Updates changed records
   - Marks deleted Nimbus users as inactive
6. **Report**: Displays summary with counts:
   - Total users processed
   - New records created
   - Records updated
   - Records deleted/deactivated
   - Validation errors (if any)

## Database Schema

Users synced to `ai_company_foundation.public.users` with:
- `external_id` (Nimbus UUID)
- `email` (unique, indexed)
- `name` (full name)
- `status` (active/inactive/pending)
- `metadata` (JSON: raw Nimbus data)
- `synced_at` (last sync timestamp)
- `synced_from` ('nimbus' identifier)

## Configuration

Requires `.env` or config file with:
```
NIMBUS_API_URL=https://api.nimbus.example.com
NIMBUS_API_KEY=sk_xxxxx
NIMBUS_API_SECRET=secret_xxxxx
NIMBUS_SYNC_TIMEOUT=30
```

## Error Handling

- API connection failures: Retries 3 times with exponential backoff
- Validation errors: Logs errors, continues with next record
- Partial failures: Rolls back transaction if critical error occurs
- Network timeouts: Resumes from last successful checkpoint

## Performance

- Batch inserts: 1000 users per transaction
- Pagination: 5000 users per API request
- Typical sync time: ~30 seconds for 10,000 users
- Memory efficient: Streaming processor for large datasets

## Related Commands

- `/nimbus-validate-users` - Validate user data after sync
- `/nimbus-test-connection` - Test Nimbus API connectivity
- `/nimbus-rollback` - Rollback last sync (if needed)
