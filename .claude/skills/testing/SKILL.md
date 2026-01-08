---
name: testing-patterns
description: Testing patterns and requirements for Claude Family projects
model: haiku
agent: tester-haiku
allowed-tools:
  - Read
  - Bash
  - Grep
  - mcp__orchestrator__spawn_agent
---

# Testing Patterns Skill

**Status**: Active
**Last Updated**: 2026-01-08

---

## Overview

This skill provides testing patterns and requirements for Claude Family projects.

---

## Quick Reference

### Test Levels

| Level | Purpose | When to Run |
|-------|---------|-------------|
| **Unit** | Individual function/class | Every change |
| **Integration** | Component interactions | Before commit |
| **Regression** | Full feature coverage | Before release |
| **Smoke** | Critical paths only | After deploy |

---

## Python Testing

### Framework: pytest

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_feature.py

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=src tests/
```

### Test Structure

```python
# tests/test_feature.py
import pytest

class TestFeature:
    def setup_method(self):
        """Run before each test method"""
        pass
    
    def test_happy_path(self):
        """Test normal operation"""
        result = function_under_test(valid_input)
        assert result == expected_output
    
    def test_edge_case(self):
        """Test boundary conditions"""
        pass
    
    def test_error_handling(self):
        """Test error scenarios"""
        with pytest.raises(ValueError):
            function_under_test(invalid_input)
```

### Fixtures

```python
@pytest.fixture
def db_connection():
    """Provide test database connection"""
    conn = create_test_connection()
    yield conn
    conn.close()

def test_database_query(db_connection):
    result = db_connection.execute("SELECT 1")
    assert result is not None
```

---

## TypeScript Testing

### Framework: Jest or Vitest

```bash
# Jest
npm test

# Vitest
npx vitest
```

### Test Structure

```typescript
import { describe, it, expect, beforeEach } from 'vitest';

describe('Feature', () => {
  beforeEach(() => {
    // Setup
  });
  
  it('should handle normal input', () => {
    const result = functionUnderTest(validInput);
    expect(result).toBe(expectedOutput);
  });
  
  it('should throw on invalid input', () => {
    expect(() => functionUnderTest(invalidInput)).toThrow();
  });
});
```

---

## Regression Testing

### Claude Family Pattern

```python
# scripts/run_regression_tests.py
def run_test(test_case):
    """Run single test case and return pass/fail"""
    try:
        result = execute_test(test_case)
        return result.success, result.message
    except Exception as e:
        return False, str(e)

def run_all_tests():
    """Run all regression tests"""
    results = []
    for test in TEST_CASES:
        passed, message = run_test(test)
        results.append((test.name, passed, message))
    return results
```

---

## Database Testing

### Test Database Pattern

```python
@pytest.fixture(scope="session")
def test_db():
    """Create isolated test database"""
    # Create test schema
    conn = get_connection()
    conn.execute("CREATE SCHEMA IF NOT EXISTS test_claude")
    
    yield conn
    
    # Cleanup
    conn.execute("DROP SCHEMA test_claude CASCADE")
```

### Data Validation Testing

```python
def test_column_registry_enforcement():
    """Verify column constraints are enforced"""
    with pytest.raises(psycopg.errors.CheckViolation):
        insert_invalid_status_value()
```

---

## Key Gotchas

### 1. Generic Constraints for Data Hooks

```typescript
// WRONG: TypeScript interfaces fail Record constraint
function useTableSort<T extends Record<string, unknown>>(data: T[]) {}

// CORRECT: Use broader object constraint
function useTableSort<T extends object>(data: T[]) {}
```

### 2. Test Isolation

Always clean up after tests. Use transactions that rollback:

```python
@pytest.fixture
def db_transaction(db_connection):
    with db_connection.transaction() as tx:
        yield tx
        tx.rollback()  # Always rollback
```

### 3. Async Testing

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

---

## Pre-Commit Checklist

Before committing code:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] No new lint warnings
- [ ] Coverage not decreased
- [ ] Edge cases covered

---

## Related Skills

- `database-operations` - Database testing specifics
- `code-review` - Review process includes test verification

---

**Version**: 1.0
