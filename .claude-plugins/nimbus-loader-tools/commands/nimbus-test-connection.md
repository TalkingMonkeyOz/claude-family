---
name: nimbus-test-connection
description: Test Nimbus API connectivity and endpoint functionality
category: nimbus
tags:
  - diagnostics
  - connection
  - api
  - troubleshooting
---

# Nimbus Connection Test

Test connectivity to the Nimbus API, verify credentials, and validate endpoint functionality.

## Overview

This command performs comprehensive connectivity and functionality tests:
- Checks Nimbus API server availability
- Verifies API credentials (API key, secret)
- Tests all critical endpoints
- Measures API response times
- Validates data formats
- Generates diagnostic report

## Usage

```bash
/nimbus-test-connection [options]
```

### Options

- `--verbose` - Show detailed request/response information
- `--timeout N` - Set connection timeout in seconds (default: 10)
- `--endpoints [all|users|teams|sync]` - Which endpoints to test (default: all)
- `--validate-ssl` - Verify SSL certificate (default: true in production)
- `--output [table|json|verbose]` - Output format (default: table)
- `--save PATH` - Save diagnostic report to file

### Examples

```bash
# Quick connection test
/nimbus-test-connection

# Test with detailed output
/nimbus-test-connection --verbose

# Test specific endpoints
/nimbus-test-connection --endpoints users,teams

# Generate JSON report
/nimbus-test-connection --output json

# Save diagnostic report
/nimbus-test-connection --save ./nimbus-diagnostics.json

# Test with custom timeout
/nimbus-test-connection --timeout 30
```

## Test Results

### Success Output

```
╔════════════════════════════════════════════════════════════════╗
║               NIMBUS API CONNECTION TEST                       ║
╠════════════════════════════════════════════════════════════════╣
║ API URL: https://api.nimbus.example.com                       ║
║ Status: ✓ CONNECTED                                           ║
║ Test Time: 2025-10-23T14:30:00Z                              ║
╠════════════════════════════════════════════════════════════════╣
║ AUTHENTICATION                                                  ║
║  ✓ API Key: Valid (sk_xxxxx...)                              ║
║  ✓ API Secret: Valid                                          ║
║  ✓ Permissions: admin, users:read, users:write               ║
╠════════════════════════════════════════════════════════════════╣
║ ENDPOINTS (response times)                                      ║
║  ✓ GET /api/v1/health                    42ms                ║
║  ✓ GET /api/v1/users                    156ms (12,450 users) ║
║  ✓ GET /api/v1/teams                     89ms (247 teams)    ║
║  ✓ POST /api/v1/sync/start               234ms               ║
║  ✓ GET /api/v1/sync/status               67ms                ║
║ Average Response Time: 117ms                                   ║
╠════════════════════════════════════════════════════════════════╣
║ DATA VALIDATION                                                 ║
║  ✓ User record format: Valid JSON schema                      ║
║  ✓ Required fields present: email, id, name                  ║
║  ✓ Date formats: Valid ISO 8601                              ║
║  ✓ Pagination: Supported (limit=5000)                        ║
╠════════════════════════════════════════════════════════════════╣
║ SUMMARY                                                         ║
║  Status: ✓ ALL CHECKS PASSED                                 ║
║  Ready for sync: Yes                                          ║
║  Last tested: 2025-10-23T14:30:00Z                           ║
╚════════════════════════════════════════════════════════════════╝
```

### Failure Output

```
╔════════════════════════════════════════════════════════════════╗
║               NIMBUS API CONNECTION TEST                       ║
╠════════════════════════════════════════════════════════════════╣
║ API URL: https://api.nimbus.example.com                       ║
║ Status: ✗ FAILED                                              ║
╠════════════════════════════════════════════════════════════════╣
║ ERRORS                                                          ║
║  ✗ Network timeout: No response after 10s                     ║
║    - Possible causes:                                          ║
║      • Network connectivity issue                              ║
║      • API server is down                                      ║
║      • Firewall blocking request                               ║
║    - Troubleshooting:                                          ║
║      • Try: ping api.nimbus.example.com                       ║
║      • Check firewall rules                                    ║
║      • Verify API_URL environment variable                    ║
╠════════════════════════════════════════════════════════════════╣
║ RECOMMENDATIONS                                                 ║
║  1. Check network connectivity to api.nimbus.example.com      ║
║  2. Verify firewall/proxy settings                            ║
║  3. Confirm NIMBUS_API_URL is correct                         ║
║  4. Check Nimbus API status page                              ║
║  5. Review system logs for connection errors                  ║
╚════════════════════════════════════════════════════════════════╝
```

## Detailed Tests

### 1. Server Availability
- Checks if Nimbus API server responds
- Verifies HTTP/HTTPS connectivity
- Measures initial handshake time
- Tests DNS resolution

### 2. Authentication
- Validates API key format and signature
- Verifies API secret is recognized
- Confirms credentials are not expired
- Checks assigned permissions/scopes

### 3. Endpoint Functionality
Tests these critical endpoints:
- `GET /api/v1/health` - Server health check
- `GET /api/v1/users` - Fetch users (pagination)
- `GET /api/v1/teams` - Fetch teams
- `GET /api/v1/departments` - Fetch departments
- `POST /api/v1/sync/start` - Initiate sync
- `GET /api/v1/sync/status` - Check sync status

### 4. Data Validation
- Verifies JSON schema compliance
- Checks required fields are present
- Validates data types and formats
- Confirms pagination support

### 5. Performance Metrics
- Response time for each endpoint
- Throughput (records per second)
- Connection establishment time
- Server processing time

## JSON Output Format

Use `--output json` for automation:

```json
{
  "test_run": "2025-10-23T14:30:00Z",
  "api_url": "https://api.nimbus.example.com",
  "status": "success",
  "authentication": {
    "api_key_valid": true,
    "api_secret_valid": true,
    "permissions": ["admin", "users:read", "users:write"]
  },
  "endpoints": [
    {
      "method": "GET",
      "path": "/api/v1/users",
      "status_code": 200,
      "response_time_ms": 156,
      "records_returned": 12450,
      "error": null
    }
  ],
  "data_validation": {
    "schema_valid": true,
    "required_fields_present": true,
    "date_format_valid": true
  },
  "summary": {
    "all_passed": true,
    "ready_for_sync": true,
    "total_tests": 15,
    "passed": 15,
    "failed": 0
  }
}
```

## Troubleshooting Guide

| Symptom | Cause | Solution |
|---------|-------|----------|
| Connection timeout | Network/firewall | Check connectivity, verify firewall rules |
| 401 Unauthorized | Invalid credentials | Verify API key and secret in config |
| 403 Forbidden | Insufficient permissions | Check API key permissions in Nimbus |
| 404 Not Found | Wrong API URL | Verify NIMBUS_API_URL setting |
| Slow responses | High server load | Retry during off-peak hours |
| SSL certificate error | Network interception | Verify SSL/TLS setup, check proxy |

## Configuration Check

Verifies these environment variables are set:
- `NIMBUS_API_URL` - Nimbus API endpoint
- `NIMBUS_API_KEY` - API authentication key
- `NIMBUS_API_SECRET` - API authentication secret
- `NIMBUS_TIMEOUT` - Connection timeout (optional)
- `NIMBUS_PROXY` - Proxy URL (optional)

## Related Commands

- `/nimbus-sync` - Sync users after successful connection test
- `/nimbus-validate-users` - Validate synced user data
- `/nimbus-logs` - View Nimbus integration logs
