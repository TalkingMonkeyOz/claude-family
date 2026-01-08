---
category: nimbus-api
confidence: 95
created: 2026-01-07
projects:
- nimbus-mui
- nimbus-import
- nimbus-user-loader
synced: false
tags:
- nimbus
- entity-creation
- dependency
- import
title: Nimbus Entity Creation Order
type: sop
---

# Nimbus Entity Creation Order

## Summary

Entities must be created in dependency order. Creating out of order causes referential integrity errors.

## Critical Dependency Chain

```
1. Locations         <- No dependencies (create FIRST)
2. Location Groups   <- Contains Locations (needs LocationIDs)
3. Departments       <- Belongs to Location (needs LocationID)
4. Cost Centres      <- No dependencies (can create early)
5. Schedule Groups   <- References Location Groups
6. Users             <- References ALL above
```

## Dependency Matrix

| Entity | Depends On | Created By |
|--------|------------|------------|
| Locations | None | Core Setup |
| Location Groups | Locations | Core Setup |
| Departments | Locations | Core Setup |
| Cost Centres | None | Core Setup |
| Schedule Groups | Location Groups | Core Setup |
| Activity Types | None | Core Setup |
| Job Roles | None | Core Setup |
| Employment Types | None | Core Setup |
| Security Roles | None | Admin Setup |
| Users | Locations, Departments, Job Roles | User Import |
| Employments | Users, Employment Types | User Import |
| User Security | Users, Security Roles | User Import |
| Shifts | Users, Locations, Activity Types | Shift Import |

## Import Section Dependencies

When importing, enable sections in order:

### Phase 1: Foundation (No dependencies)
- Locations
- Cost Centres
- Activity Types
- Job Roles
- Employment Types

### Phase 2: Grouped Entities
- Location Groups (needs Locations)
- Departments (needs Locations)
- Schedule Groups (needs Location Groups)

### Phase 3: People
- Users (needs Phase 1 + Phase 2)
- Employments (needs Users)
- User Security (needs Users)

### Phase 4: Operations
- Shifts (needs Users + Locations + Activity Types)
- Attendances (needs Shifts)

## Code Pattern

```typescript
// Correct order
await createLocations(data);
await createLocationGroups(data);  // Now has LocationIDs
await createDepartments(data);     // Now has LocationIDs
await createUsers(data);           // Now has all references
```

## Gotcha

Never parallelize creation of dependent entities:

```typescript
// WRONG - Race condition
await Promise.all([
  createLocations(data),
  createDepartments(data)  // May fail - no LocationIDs yet!
]);

// CORRECT - Sequential
await createLocations(data);
await createDepartments(data);
```

## Related

- [[nimbus-rest-crud-pattern]]
- [[nimbus-cache-strategy]]

---

**Version**: 1.0
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: 20-Domains/APIs/nimbus-entity-creation-order.md
