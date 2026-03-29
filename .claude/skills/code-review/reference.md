# Code Review Skill — Detailed Reference

## Testing Patterns

### Test Coverage Targets

| Code Type | Min Coverage |
|-----------|-------------|
| Business logic | 80%+ |
| API endpoints | 70%+ |
| Utilities | 90%+ |
| UI components | 60%+ |

### Test Structure (AAA)

```python
def test_user_login():
    # Arrange
    user = create_test_user(email="test@example.com")
    # Act
    result = auth_service.login(user.email, "password123")
    # Assert
    assert result.success is True
```

### Spawning Test Writer

```
Task(
    subagent_type="tester-haiku",
    description="Write tests for auth module",
    prompt="Write unit tests for src/auth/middleware.ts covering: happy path, invalid token, expired token, missing header"
)
```

---

## Security Checks

```
Task(
    subagent_type="security-sonnet",
    description="Security scan",
    prompt="Scan src/ for: SQL injection, XSS, hardcoded secrets, auth issues"
)
```

---

## Code Quality Metrics

| Smell | Threshold | Fix |
|-------|-----------|-----|
| Long methods | >100 lines | Extract methods |
| Large classes | >500 lines | Split responsibilities |
| Deep nesting | >4 levels | Guard clauses, early returns |
| Magic numbers | Any | Named constants |
| Duplicated code | >3 occurrences | Extract shared function |
