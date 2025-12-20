---
category: nimbus-api
confidence: 90
created: 2025-12-19
projects:
- nimbus-import
- nimbus-user-loader
synced: true
synced_at: '2025-12-20T11:08:45.261020'
tags:
- nimbus
- rest
- api
- scheduleshift
title: Nimbus ScheduleShift GET idorfilter Patterns
type: api-reference
---

# Nimbus ScheduleShift GET idorfilter Patterns

## Summary
GET /RESTApi/ScheduleShift/:idorfilter supports special filter values beyond numeric IDs.

## Details
The `:idorfilter` parameter in the ScheduleShift endpoint accepts different types of values:

### Filter Types

| Value | Behavior |
|-------|----------|
| Numeric ID | Returns specific shift by ScheduleShiftID |
| `LocationShifts` | Returns shifts by location on specific date |

### LocationShifts Filter

For the `LocationShifts` filter, pass additional query parameters:
- `LocationID` - Required, the location to filter by
- `Date` - Optional, defaults to current day if not provided

## Code Example
```http
# Get specific shift by ID
GET /RESTApi/ScheduleShift/12345

# Get all shifts for a location today
GET /RESTApi/ScheduleShift/LocationShifts?LocationID=100

# Get all shifts for a location on specific date
GET /RESTApi/ScheduleShift/LocationShifts?LocationID=100&Date=2025-12-19
```

## Important
This pattern applies to ScheduleShift endpoint only. Other endpoints may have different idorfilter options - check API documentation for each entity.

## Related
- [[nimbus-rest-crud-pattern]]
- [[nimbus-time-fields]]