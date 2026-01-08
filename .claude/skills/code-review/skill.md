---
name: code-review
description: Code review patterns, testing, and pre-commit quality gates
model: sonnet
context: fork
allowed-tools:
  - Read
  - Bash
  - Grep
  - mcp__orchestrator__spawn_agent
---

# Code Review Skill

**Status**: Active
**Last Updated**: 2026-01-08

---

## Overview

This skill provides guidance for code review, testing patterns, and pre-commit quality gates.

---

## When to Use

Invoke this skill when:
- Preparing to commit code changes
- Reviewing pull requests
- Implementing new features
- Refactoring existing code
- Writing or updating tests

---

## Quick Reference

### Pre-Commit Checklist

Before committing, verify:
- [ ] Code follows project conventions
- [ ] Tests added/updated for changes
- [ ] No debugging code (console.log, print statements)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling implemented
- [ ] Documentation updated if needed

---

## Code Review Process

### 1. Self-Review First

Before requesting review:

```bash
# Check diff
git diff

# Run tests
npm test  # or pytest, dotnet test, etc.

# Run linter
npm run lint

# Check for common issues
grep -r "console.log" src/
grep -r "TODO" src/
```

### 2. Use Review Agent

For comprehensive review:

```bash
# Spawn reviewer-sonnet agent
mcp__orchestrator__spawn_agent(
    agent_type="reviewer-sonnet",
    task="Review changes in src/ directory for code quality, best practices, and potential bugs",
    workspace_dir="/path/to/project"
)
```

### 3. Address Findings

**Severity levels**:
- **Critical**: Security issues, data loss risks
- **High**: Bugs, performance problems
- **Medium**: Code quality, maintainability
- **Low**: Style, minor improvements

---

## Testing Patterns

### Test Coverage Requirements

| Code Type | Min Coverage |
|-----------|--------------|
| Business logic | 80%+ |
| API endpoints | 70%+ |
| Utilities | 90%+ |
| UI components | 60%+ |

### Test Structure (AAA Pattern)

```python
def test_user_login():
    # Arrange
    user = create_test_user(email="test@example.com")

    # Act
    result = auth_service.login(user.email, "password123")

    # Assert
    assert result.success == True
    assert result.token is not None
```

### Common Test Types

| Type | Purpose | Example |
|------|---------|---------|
| **Unit** | Test individual functions | `test_calculate_total()` |
| **Integration** | Test component interaction | `test_api_endpoint()` |
| **E2E** | Test user flows | `test_user_can_login()` |
| **Regression** | Prevent bug recurrence | `test_issue_123_fixed()` |

---

## Security Review

### Critical Security Checks

```bash
# 1. Check for hardcoded secrets
grep -r "password\s*=\s*['\"]" src/
grep -r "api_key\s*=\s*['\"]" src/
grep -r "secret\s*=\s*['\"]" src/

# 2. Check for SQL injection risks
grep -r "execute.*f\"" src/  # Python f-strings in SQL
grep -r "\${.*}" src/        # Template literals in SQL

# 3. Check for XSS risks
grep -r "innerHTML\s*=" src/
grep -r "dangerouslySetInnerHTML" src/
```

### Using Security Agent

```bash
mcp__orchestrator__spawn_agent(
    agent_type="security-sonnet",
    task="Scan codebase for security vulnerabilities (SQL injection, XSS, hardcoded secrets)",
    workspace_dir="/path/to/project"
)
```

---

## Code Quality Metrics

### Cyclomatic Complexity

**Target**: <10 per function

**High complexity indicators**:
- Deeply nested if/else statements
- Multiple try/catch blocks
- Long switch/case statements

**Solution**: Extract methods, use early returns

### Code Smells

| Smell | Example | Fix |
|-------|---------|-----|
| Long methods | 100+ lines | Extract methods |
| Large classes | 500+ lines | Split responsibilities |
| Duplicated code | Copy-paste | Create shared function |
| Magic numbers | `if (x > 86400)` | Use constants (`SECONDS_PER_DAY`) |
| Deep nesting | 4+ levels | Use guard clauses, early returns |

---

## Common Patterns

### Error Handling

```python
# GOOD: Specific exceptions, meaningful messages
try:
    user = db.get_user(user_id)
except UserNotFoundError as e:
    logger.error(f"User {user_id} not found: {e}")
    raise
except DatabaseError as e:
    logger.critical(f"Database error retrieving user: {e}")
    raise

# BAD: Catching everything, hiding errors
try:
    user = db.get_user(user_id)
except Exception:
    pass  # Silently fails!
```

### Null Safety

```typescript
// GOOD: Explicit null checks
function getUserEmail(user: User | null): string {
    if (!user) {
        throw new Error("User is null");
    }
    return user.email;
}

// BAD: Trusting inputs
function getUserEmail(user: User): string {
    return user.email;  // Crashes if user is null!
}
```

---

## Git Best Practices

### Commit Messages

**Format**: `<type>: <description>`

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructure (no behavior change)
- `test`: Add/update tests
- `docs`: Documentation only
- `chore`: Maintenance (deps, config)

**Example**:
```
feat: Add user authentication with JWT

- Implement login/logout endpoints
- Add JWT token generation
- Create auth middleware for protected routes

Closes #123
```

### Branch Naming

```
feature/user-authentication
bugfix/login-error-message
refactor/auth-service
hotfix/security-vulnerability
```

---

## Review Checklist Templates

### Feature Review

- [ ] Feature meets acceptance criteria
- [ ] Tests cover happy path and edge cases
- [ ] Error states handled gracefully
- [ ] Performance acceptable (<100ms API response)
- [ ] Accessibility requirements met (WCAG AA)
- [ ] Documentation updated

### Bug Fix Review

- [ ] Root cause identified and documented
- [ ] Fix addresses root cause (not just symptoms)
- [ ] Regression test added
- [ ] No unintended side effects
- [ ] Related bugs checked

### Refactoring Review

- [ ] Behavior unchanged (tests still pass)
- [ ] Code more maintainable/readable
- [ ] Performance same or improved
- [ ] No new dependencies without justification

---

## Related Skills

- `testing-patterns` - Detailed testing guidance
- `database-operations` - SQL review patterns
- `session-management` - Pre-commit workflows

---

## Key Gotchas

### 1. Skipping Tests

**Problem**: "Tests are too slow" leads to bugs in production

**Solution**: Use fast unit tests, slower integration tests in CI

### 2. Reviewing Own Code

**Problem**: Author blindness - can't see own mistakes

**Solution**: Use reviewer agent, wait 1 hour before self-review

### 3. Not Testing Edge Cases

**Problem**: Code works for happy path, fails on edge cases

**Solution**: Test null inputs, empty arrays, max values, unicode, etc.

---

**Version**: 1.0
**Created**: 2025-12-26
**Location**: .claude/skills/code-review/skill.md
