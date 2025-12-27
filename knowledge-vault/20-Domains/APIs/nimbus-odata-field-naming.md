---
category: nimbus-api
confidence: 95
created: 2025-12-18
projects:
- nimbus-import
- nimbus-user-loader
synced: true
synced_at: '2025-12-20T13:15:19.798187'
tags:
- nimbus
- odata
- api
- field-naming
title: Nimbus OData Field Naming
type: gotcha
---

# Nimbus OData Field Naming

## Summary
In the Nimbus WFM OData API, all entities use "Description" for name/label fields, NOT "Name".

## Details
This is a non-obvious naming convention in the Nimbus API that trips up many developers. When you expect a field called "Name" to contain the human-readable label, you actually need to use "Description".

This applies to:
- Employee entities
- Activity types
- Shift templates
- All custom entities

## Code Example
```csharp
// WRONG - This field doesn't exist or is empty
var label = employee.Name;

// CORRECT - Use Description for the label
var label = employee.Description;
```

## Related
- [[nimbus-rest-crud-pattern]]
- [[nimbus-time-fields]]
---

**Version**: 1.0
**Created**: 2025-12-26
**Updated**: 2025-12-26
**Location**: 20-Domains/APIs/nimbus-odata-field-naming.md