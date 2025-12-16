---
description: Run stored tests for regression testing. Args: test_name | --all | --type=X
---

# Run Tests

Execute stored tests for regression testing. Arguments: `$ARGUMENTS`

## Step 1: Parse Arguments

Options:
- `<test_name>` - Run specific test by name
- `--all` - Run all active tests for current project
- `--type=unit|integration|e2e|process` - Run tests of specific type
- `--tag=<tag>` - Run tests with specific tag

## Step 2: Query Tests to Run

For specific test:
```sql
SELECT * FROM claude.stored_tests
WHERE test_name = '<test_name>'
  AND is_archived = false;
```

For all tests:
```sql
SELECT * FROM claude.stored_tests st
JOIN claude.projects p ON st.project_id = p.project_id
WHERE p.project_name = '<current_project>'
  AND st.is_archived = false
ORDER BY st.test_type, st.test_name;
```

For type filter:
```sql
SELECT * FROM claude.stored_tests st
JOIN claude.projects p ON st.project_id = p.project_id
WHERE p.project_name = '<current_project>'
  AND st.test_type = '<type>'
  AND st.is_archived = false;
```

## Step 3: Execute Each Test

For each test in the result set:

1. **Parse test_definition JSON**
2. **Check preconditions** (if any)
3. **Execute steps in order**:
   - `run_command`: Execute bash command
   - `check_output`: Verify output contains/matches
   - `check_exit_code`: Verify command exit code
   - `check_table`: Query database table
   - `check_file`: Verify file exists/contains
4. **Run cleanup** (if any)
5. **Record result**

## Step 4: Update Test Record

```sql
UPDATE claude.stored_tests
SET
    last_run_at = NOW(),
    last_result = '<pass|fail|error>',
    run_count = run_count + 1
WHERE test_id = '<test_id>';
```

## Step 5: Display Results

```
TEST RESULTS
═══════════════════════════════════════════════════════════════

 Test Name              Type        Result    Duration
───────────────────────────────────────────────────────────────
 auth-login-test        unit        PASS      1.2s
 session-start-flow     process     PASS      0.3s
 api-health-check       integration FAIL      2.1s
───────────────────────────────────────────────────────────────

SUMMARY: 2 passed, 1 failed, 0 skipped

FAILURES:
─────────────────────────────────────────────────────────────
api-health-check:
  Step: check_output
  Expected: "status": "ok"
  Actual: Connection refused to localhost:3000

  Recommendation: Ensure the API server is running
─────────────────────────────────────────────────────────────
```

## Step 6: Store Run History (Optional)

```sql
INSERT INTO claude.test_runs (test_id, result, duration_ms, output, run_by_identity_id)
VALUES ('<test_id>', '<result>', <duration>, '<output>', '<identity_id>');
```

## Quick Examples

```bash
# Run all tests
/run-tests --all

# Run specific test
/run-tests auth-login-test

# Run all unit tests
/run-tests --type=unit

# Run tests tagged 'critical'
/run-tests --tag=critical
```
