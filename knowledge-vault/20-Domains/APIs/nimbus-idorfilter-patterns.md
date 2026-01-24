---
category: nimbus-api
confidence: 90
created: 2025-12-19
projects:
- nimbus-import
- nimbus-user-loader
- monash-nimbus-reports
synced: false
tags:
- nimbus
- rest
- api
- scheduleshift
- task
title: Nimbus REST API Filter Patterns (idorfilter and query params)
type: api-reference
---

# Nimbus REST API Filter Patterns

## Summary
Several Nimbus REST endpoints support special filter patterns beyond numeric IDs.

## ScheduleShift - idorfilter Patterns

The `:idorfilter` parameter in the ScheduleShift endpoint accepts different types of values:

| Value | Behavior |
|-------|----------|
| Numeric ID | Returns specific shift by ScheduleShiftID |
| `LocationShifts` | Returns shifts by location on specific date |

### LocationShifts Filter

Query parameters:
- `LocationID` - Required, the location to filter by
- `Date` - Optional, defaults to current day if not provided

```http
# Get specific shift by ID
GET /RESTApi/ScheduleShift/12345

# Get all shifts for a location today
GET /RESTApi/ScheduleShift/LocationShifts?LocationID=100

# Get all shifts for a location on specific date
GET /RESTApi/ScheduleShift/LocationShifts?LocationID=100&Date=2025-12-19
```

---

## Task - Schedule Filter

The Task endpoint supports filtering by schedule via query parameter:

| Parameter | Behavior |
|-----------|----------|
| `schedule` | Returns all tasks associated with a ScheduleID |

```http
# Get all tasks for a schedule
GET /RESTApi/Task?schedule=236457

# Response includes TaskHours (budget), Description, TaskTypeDescription
```

### Why This Matters

**Task is REST-only** - not available via OData. This filter is the primary way to get all tasks for a schedule efficiently.

### Report Pattern: Task Hours by Schedule

```python
# Step 1: Get tasks with budget hours
tasks = GET /RESTApi/Task?schedule={schedule_id}
# Returns: TaskID, TaskHours, Description, TaskTypeDescription

# Step 2: Get attendances for schedule (OData - bulk efficient)
attendances = GET /CoreAPI/Odata/ScheduleShiftAttendance?$filter=ScheduleID eq {schedule_id}
# Returns: Id, UserID, ScheduleID

# Step 3: Get activities with TaskID (REST - has TaskID)
activities = GET /RESTApi/ScheduleShiftAttendanceActivity
# Filter by ScheduleShiftAttendanceID from step 2
# Returns: TaskID, StartTime, FinishTime (calculate hours)
```

---

## Important

Each endpoint may have different filter options. Always check API documentation or test in Swagger.

## Related
- [[nimbus-rest-crud-pattern]]
- [[nimbus-time-fields]]
- [[NIMBUS_TASKS_AND_ATTENDANCES]] (detailed task/attendance documentation)

---

**Version**: 1.1
**Created**: 2025-12-26
**Updated**: 2026-01-22
**Location**: 20-Domains/APIs/nimbus-idorfilter-patterns.md