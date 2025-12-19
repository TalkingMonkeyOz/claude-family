# Nimbus API Skill

**Status**: Placeholder
**Last Updated**: 2025-12-18

---

## Overview

This skill provides guidance for working with the Nimbus WFM (Workforce Management) API.

> **Note**: This is a placeholder file. Detailed content should be migrated from the `claude.knowledge` database entries categorized under `nimbus-api`.

---

## Quick Reference

### OData Endpoints

- `/odata/Employees` - Employee records
- `/odata/Shifts` - Shift schedules
- `/odata/Activities` - Activity definitions
- `/odata/ScheduleShifts` - Schedule shifts

### REST Endpoints

- `/api/v1/auth` - Authentication
- `/api/v1/users` - User management
- `/api/v1/shifts` - Shift operations

---

## Key Gotchas

### 1. Field Naming
Use `Description` not `Name` for all label fields in OData entities.

### 2. CRUD Pattern
POST handles both create AND update operations (non-standard REST).

### 3. Time Fields
Only send LOCAL times for ScheduleShift - UTC is auto-calculated.

### 4. Deleted Field Filter
`$filter=Deleted eq false` doesn't work server-side. Filter client-side.

---

## Related Knowledge

Query the database for complete knowledge:

```sql
SELECT title, content, confidence_level
FROM claude.knowledge
WHERE knowledge_category = 'nimbus-api'
ORDER BY confidence_level DESC;
```

---

**To Do**: Migrate full knowledge from database to this skill file for offline access.
