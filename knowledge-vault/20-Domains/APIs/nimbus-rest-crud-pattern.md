---
category: nimbus-api
confidence: 95
created: 2025-12-19
projects:
- nimbus-import
synced: true
synced_at: '2025-12-20T11:08:45.264021'
tags:
- nimbus
- rest
- api
- crud
title: Nimbus REST CRUD Pattern
type: pattern
---

# Nimbus REST CRUD Pattern

## Summary
Nimbus REST API uses POST for both create AND update operations (non-standard REST pattern).

## Details
Unlike standard REST where:
- POST = Create new record
- PUT = Update existing record

Nimbus uses POST for both operations. The API determines create vs update based on whether the ID field is populated.

### Create (ID = null or 0)
```http
POST /RESTApi/Employee
Content-Type: application/json

{
  "EmployeeID": 0,
  "FirstName": "John",
  "LastName": "Doe"
}
```

### Update (ID = existing value)
```http
POST /RESTApi/Employee
Content-Type: application/json

{
  "EmployeeID": 12345,
  "FirstName": "John",
  "LastName": "Smith"
}
```

## Code Example
```csharp
// Both create and update use the same endpoint and method
public async Task<Employee> SaveEmployee(Employee employee)
{
    // If EmployeeID is 0, this creates a new record
    // If EmployeeID has a value, this updates the existing record
    return await _client.PostAsJsonAsync("/RESTApi/Employee", employee);
}
```

## Gotcha
Do NOT use PUT for updates - it will likely return a 405 Method Not Allowed.

## Related
- [[nimbus-odata-field-naming]]
- [[nimbus-time-fields]]