---
category: nimbus-api
confidence: 95
created: 2025-12-19
projects:
- nimbus-import
synced: true
synced_at: '2025-12-20T11:08:45.266102'
tags:
- nimbus
- odata
- api
- time
- utc
title: Nimbus ScheduleShift Time Fields
type: api-reference
---

# Nimbus ScheduleShift Time Fields

## Summary
ScheduleShift API only needs LOCAL times - UTC is auto-calculated by the server.

## Details
When creating or updating ScheduleShift records, only send local times. The Nimbus API automatically calculates UTC times based on the tenant timezone setting.

**API PAYLOAD (what to send):**
- StartTime = local time (e.g., "2025-10-21T18:00:00")
- FinishTime = local time (e.g., "2025-10-21T21:00:00")

**DATABASE (what gets stored):**
- StartTime / FinishTime = local times (as sent)
- StartTimeUTC / FinishTimeUTC = AUTO-CALCULATED (local - 11 hours for Melbourne AEDT)

## Code Example
```json
// CORRECT - Send local times only
{
  "StartTime": "2025-10-21T20:00:00",
  "FinishTime": "2025-10-21T23:00:00"
}

// WRONG - Don't send UTC times
{
  "StartTime": "2025-10-21T20:00:00",
  "StartTimeUTC": "2025-10-21T09:00:00"  // Don't do this!
}
```

## Important
Do NOT send UTC times - the API calculates them automatically from local times using the tenant timezone setting.

## Related
- [[nimbus-odata-field-naming]]
- [[nimbus-rest-crud-pattern]]