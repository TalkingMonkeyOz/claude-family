---
description: Store a test definition in the database for persistent regression testing
---

# Store Test

Store a test definition so it can be run across sessions. Arguments: `$ARGUMENTS`

## Step 1: Parse Test Definition

Extract from arguments or current context:
- **Test Name**: Unique identifier for this test
- **Test Type**: unit | integration | e2e | process | workflow
- **Test Definition**: JSON describing how to run the test

## Step 2: Get Project ID

```sql
SELECT project_id FROM claude.projects
WHERE project_name = '<current_project>';
```

## Step 3: Store the Test

```sql
INSERT INTO claude.stored_tests (
    project_id,
    test_name,
    test_type,
    test_definition,
    created_by_identity_id
)
VALUES (
    '<project_id>',
    '<test_name>',
    '<test_type>',
    '<test_definition_json>'::jsonb,
    'ff32276f-9d05-4a18-b092-31b54c82fff9'::uuid  -- claude-code-unified
)
RETURNING test_id, test_name;
```

## Test Definition Schema

```json
{
  "description": "What this test verifies",
  "preconditions": ["File X exists", "Service Y running"],
  "steps": [
    {"action": "run_command", "command": "pnpm test src/module.test.ts"},
    {"action": "check_output", "contains": "PASS"},
    {"action": "check_exit_code", "expected": 0}
  ],
  "cleanup": ["optional cleanup commands"],
  "tags": ["api", "auth", "critical"]
}
```

## Example Usage

Store a unit test:
```
/store-test auth-login-test unit {"description":"Test login endpoint","steps":[{"action":"run_command","command":"pnpm test src/auth/login.test.ts"}]}
```

Store a process test:
```
/store-test session-start-flow process {"description":"Verify session start hooks work","steps":[{"action":"check_table","table":"claude.sessions","condition":"count > 0"}]}
```

## Step 4: Confirm Storage

```
Test stored successfully:
- Test ID: <uuid>
- Name: <test_name>
- Type: <test_type>

Run with: /run-tests <test_name>
Run all: /run-tests --all
```
