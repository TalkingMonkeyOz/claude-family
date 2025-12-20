---
category: nimbus-api
confidence: 90
created: 2025-12-19
projects:
- nimbus-import
synced: true
synced_at: '2025-12-20T13:15:19.793305'
tags:
- nimbus
- api
- activities
title: Nimbus Activity Type Prefixes
type: pattern
---

# Nimbus Activity Type Prefixes

## Summary
Activity types in Nimbus use prefixes to indicate scheduling mode. Must match full description including prefix.

## Details
When working with Activity entities in Nimbus, the Description field includes a prefix that indicates the scheduling mode:

| Prefix | Mode | Meaning |
|--------|------|---------|
| `TT:` | Timetabled | Fixed schedule, repeating pattern |
| `S:` | Scheduled | Manually scheduled, flexible |
| `U:` | Unscheduled | Not yet assigned to schedule |

## Code Example
```csharp
// WRONG - Won't find the activity
var activity = activities.FirstOrDefault(a => a.Description == "Morning Shift");

// CORRECT - Include the prefix
var activity = activities.FirstOrDefault(a => a.Description == "S: Morning Shift");

// BETTER - Check prefix separately
var scheduledActivities = activities
    .Where(a => a.Description.StartsWith("S:"))
    .ToList();
```

## Gotcha
When importing or matching activities from external systems (like Excel), the source data may not include the prefix. Add logic to match with or without prefix, or prepend the appropriate prefix.

## Related
- [[nimbus-odata-field-naming]]