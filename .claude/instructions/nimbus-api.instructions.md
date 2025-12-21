---
description: 'Nimbus WFM API patterns and gotchas'
applyTo: '**/nimbus-*/**/*.cs,**/nimbus-*/**/*.ts,**/nimbus-*/**/*.tsx'
source: 'Claude Family knowledge vault (consolidated)'
---

# Nimbus WFM API Guidelines

## Field Naming Convention

**CRITICAL**: Nimbus uses `Description` for name/label fields, NOT `Name`.

```csharp
// WRONG - Field doesn't exist or is empty
var label = employee.Name;

// CORRECT - Use Description
var label = employee.Description;
```

This applies to ALL entities: Employee, Activity, Shift Templates, Locations, etc.

## REST CRUD Pattern (Non-Standard)

**Nimbus uses POST for both create AND update** - not standard REST!

```csharp
// Create (ID = 0 or null)
POST /RESTApi/Employee
{ "EmployeeID": 0, "FirstName": "John" }

// Update (ID = existing value)
POST /RESTApi/Employee
{ "EmployeeID": 12345, "FirstName": "Jane" }
```

**DO NOT use PUT** - returns 405 Method Not Allowed.

## Time Fields

**Only send LOCAL times** - UTC is auto-calculated by the server.

```json
// CORRECT - Local times only
{
  "StartTime": "2025-10-21T20:00:00",
  "FinishTime": "2025-10-21T23:00:00"
}

// WRONG - Never send UTC times
{
  "StartTimeUTC": "2025-10-21T09:00:00"  // DON'T DO THIS
}
```

The API calculates UTC from local using tenant timezone (e.g., Melbourne AEDT = local - 11 hours).

## IdOrFilter Patterns

ScheduleShift endpoint supports special filter values:

```http
# Get specific shift by ID
GET /RESTApi/ScheduleShift/12345

# Get shifts by location (today)
GET /RESTApi/ScheduleShift/LocationShifts?LocationID=100

# Get shifts by location on date
GET /RESTApi/ScheduleShift/LocationShifts?LocationID=100&Date=2025-12-19
```

## Activity Type Prefixes

Activity descriptions include scheduling mode prefixes:

| Prefix | Mode | Meaning |
|--------|------|---------|
| `TT:` | Timetabled | Fixed repeating pattern |
| `S:` | Scheduled | Manually scheduled |
| `U:` | Unscheduled | Not yet assigned |

```csharp
// WRONG - Won't find activity
var activity = activities.FirstOrDefault(a => a.Description == "Morning Shift");

// CORRECT - Include prefix
var activity = activities.FirstOrDefault(a => a.Description == "S: Morning Shift");

// BETTER - Filter by prefix
var scheduled = activities.Where(a => a.Description.StartsWith("S:"));
```

## OData Queries

```http
# Filter employees by location
GET /OData/Employee?$filter=LocationID eq 100

# Include related entities
GET /OData/Employee?$expand=Location

# Select specific fields
GET /OData/Employee?$select=EmployeeID,Description,Email

# Combined query
GET /OData/ScheduleShift?$filter=Date ge 2025-01-01&$expand=Employee&$top=100
```

## Common Gotchas

1. **Field naming**: Always `Description`, never `Name`
2. **CRUD method**: Always POST, never PUT for updates
3. **Time zones**: Send local, server calculates UTC
4. **Activity matching**: Include the prefix (TT:, S:, U:)
5. **Empty results**: Check filter syntax - OData is case-sensitive
