---
projects:
- nimbus-mui
- nimbus-import
tags:
- nimbus
- api
- discovery
- testing
synced: false
---

# Nimbus API Discovery SOP

## Purpose

Systematically test and document Nimbus API behavior to build institutional knowledge. This is an iterative process - each Claude session can contribute new discoveries.

---

## When to Run

1. **Starting work on new entity type** - Discover its API patterns first
2. **Encountering unexpected API behavior** - Document the finding
3. **Building new import/export features** - Verify CRUD patterns work
4. **After Nimbus platform updates** - Re-verify existing knowledge

---

## Prerequisites

| Requirement | How to Verify |
|-------------|---------------|
| UAT connection | `credentials.baseUrl` contains 'uat' or 'test' |
| nimbus-knowledge MCP | Check `mcp__nimbus-knowledge__get_stats()` responds |
| Sandbox user | Query for Payroll='SANDBOX001' or create via DiagnosticsModule |

---

## Discovery Process

### Step 1: Identify Target Entity

```sql
-- Check what entities we have schema knowledge for
SELECT entity_name, property_count
FROM nimbus_context.api_entities
ORDER BY entity_name;
```

### Step 2: Compare OData vs REST

For the target entity (e.g., User):

```
GET /odata/User({id})?$select=*
GET /RESTApi/User/{id}
```

Document:
- Field naming differences
- Fields unique to each endpoint
- Response structure differences

### Step 3: Test CRUD Methods

| Method | Endpoint | Expected Result |
|--------|----------|-----------------|
| GET | /odata/{Entity}({id}) | ✅ Works |
| GET | /RESTApi/{Entity}/{id} | ✅ Works |
| POST (create) | /RESTApi/{Entity} | ✅ ID=0 creates |
| POST (update) | /RESTApi/{Entity} | ✅ ID={n} updates |
| PATCH | /odata/{Entity}({id}) | ❌ 405 typically |
| PUT | /RESTApi/{Entity} | ❌ 405 typically |
| DELETE | /RESTApi/{Entity}/{id} | ⚠️ Test carefully |

### Step 4: Document Special Cases

Look for:
- Required fields not in schema
- Fields that trigger validation errors
- Fields that are read-only
- Authentication/permission requirements
- Rate limiting behavior

---

## Capturing Knowledge

### Use nimbus-knowledge MCP

```typescript
// For patterns discovered
mcp__nimbus-knowledge__add_learning({
  learning_type: 'pattern',
  situation: 'What you were testing',
  action_taken: 'Exact request made',
  outcome: 'Result received',
  lesson_learned: 'Key insight for future reference'
});

// For constraints/facts
mcp__nimbus-knowledge__add_fact({
  fact_type: 'constraint',  // or 'technical', 'architecture'
  category: 'api',
  title: 'Short descriptive title',
  description: 'Full details including examples',
  importance: 2  // 1=critical, 5=low
});
```

### Knowledge Categories

| Category | Use For |
|----------|---------|
| `api` | API endpoint behavior, methods, responses |
| `usersdk` | UserSDK-specific patterns |
| `odata` | OData query patterns, $filter, $expand |
| `rest` | REST API patterns |

---

## Sandbox User Management

### Create Sandbox User

Via DiagnosticsModule or direct API:

```json
POST /RESTApi/User
{
  "Username": "sandbox_test@nimbus.cloud",
  "Forename": "Sandbox",
  "Surname": "TestUser",
  "Payroll": "SANDBOX001",
  "Active": true,
  "StartDate": "2024-01-01T00:00:00",
  "Rosterable": false,
  "TimezoneID": 20
}
```

### Cleanup After Testing

Reset sandbox user to known state:

```json
POST /RESTApi/User
{
  "Id": {sandbox_id},
  "Forename": "Sandbox",
  "Surname": "TestUser"
}
```

---

## Integration with Claude Family

### Session Startup

When starting nimbus-mui session, Claude should:

1. Load relevant facts: `mcp__nimbus-knowledge__get_facts({category: 'api'})`
2. Check for recent learnings: `mcp__nimbus-knowledge__get_learnings()`
3. Note any gaps in knowledge for the planned work

### Session End

Before ending session:

1. Capture any new API discoveries
2. Update facts if behavior changed
3. Send message to Claude Family if critical discovery

---

## Example Discovery Session

```
Claude: Starting API Discovery for Department entity...

1. Fetching Department(1) via OData...
   ✅ Fields: DepartmentID, Description, LocationID, Active, ...

2. Fetching Department/1 via REST...
   ✅ Fields: Id, Description, LocationId, Active, ...

3. Testing POST create...
   ✅ 201 Created - returns new DepartmentID

4. Testing POST update...
   ✅ 200 OK - updated successfully

5. Capturing learning...
   📝 Added: "Department CRUD follows standard Nimbus REST pattern"

Summary: Department entity behaves as expected. No special handling needed.
```

---

## Related Documents

- [[nimbus-rest-crud-pattern]] - General CRUD pattern
- [[nimbus-entity-creation-order]] - Entity dependencies
- [[nimbus-authentication]] - Auth flow

---

**Version**: 1.0
**Created**: 2026-01-18
**Updated**: 2026-01-18
**Location**: 40-Procedures/Nimbus API Discovery SOP.md
