---
category: nimbus-api
confidence: 100
created: 2026-01-07
projects:
- nimbus-mui
- nimbus-import
- nimbus-user-loader
synced: false
tags:
- nimbus
- api
- rest
- odata
- endpoints
title: Nimbus API Endpoints Reference
type: reference
source: nimbus-user-loader/Constants/ApiEndpoints.cs
---

# Nimbus API Endpoints Reference

## Summary

Complete reference for all Nimbus Time2Work API endpoints. Two API types: REST API (CRUD) and OData (queries).

## API Quirks (CRITICAL)

| Quirk | Details |
|-------|---------|
| Auth endpoint | `/RESTApi/Authenticate` NOT `/Authentication` |
| POST with ID | Updates existing record (non-standard REST) |
| POST without ID | Creates new record |
| TenantID | NEVER in payloads (auto-set from auth context) |
| Case sensitivity | PascalCase for request/response bodies |

## Authentication

```
POST /RESTApi/Authenticate       # Returns AuthenticationToken, UserID
POST /connect/token              # OAuth2 fallback for cloud instances
```

## User Management

```
POST /RESTApi/UserSDK            # Bulk user imports (batch mode)
POST /RESTApi/User               # Individual user operations
GET  /RESTApi/UserSecurityRole   # User security role assignments
DEL  /RESTApi/UserSecurityRole/{id}
GET  /RESTApi/UserLocation       # User location assignments
```

## Reference Data

```
/RESTApi/Location          # WARNING: GET may timeout with large datasets
/RESTApi/LocationGroup     # WARNING: GET may return HTML for large datasets
/RESTApi/Department
/RESTApi/DepartmentType
/RESTApi/Team
/RESTApi/JobRole
/RESTApi/Skill
/RESTApi/SecurityRole
/RESTApi/ScheduleGroup
/RESTApi/ActivityType
/RESTApi/Rule              # All rule types
/RESTApi/Country
/RESTApi/Timezone
/RESTApi/PublicHolidayGroup
/RESTApi/OpeningHoursGroup
/RESTApi/ContractRuleObject  # Contract rules with full config
```

## OData API

Base path: `/CoreAPI/Odata`

```
GET /CoreAPI/Odata/{EntityName}              # Query entity
GET /CoreAPI/Odata/{EntityName}/$count       # Count records
GET /CoreAPI/Odata/$metadata                 # Schema metadata
```

**Common OData Entities**:
- User, Location, Department, JobRole, Skill
- ScheduleShift, ScheduleGroup, ActivityType
- ContractRule, AwardRule, SecurityRole

## Swagger Documentation

```
/CoreAPI/swagger/v2/swagger.json
/CoreAPI/swagger/docs/v1
```

## Helper Patterns

**Delete by ID**:
```
DELETE /RESTApi/{Entity}/{id}
DELETE /RESTApi/{Entity}?idorfilter={id}
```

**OData Query Examples**:
```
/CoreAPI/Odata/User?$top=10&$select=userID,payroll
/CoreAPI/Odata/Location?$filter=Active eq true
/CoreAPI/Odata/Department?$expand=LocationObject
```

## Header Requirements

All authenticated requests need:
```http
AuthenticationToken: {token}
UserID: {userId}
Authorization: Bearer {token}
Content-Type: application/json
```

## Related

- [[nimbus-authentication]] - Auth flow details
- [[nimbus-rest-crud-pattern]] - CRUD patterns
- [[nimbus-odata-field-naming]] - Field naming conventions
- [[nimbus-entity-creation-order]] - Dependency order

---

**Version**: 1.0
**Created**: 2026-01-07
**Updated**: 2026-01-07
**Location**: 20-Domains/APIs/nimbus-api-endpoints.md
