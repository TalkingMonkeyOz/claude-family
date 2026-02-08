---
name: code-review
description: Code review patterns, testing, and pre-commit quality gates
model: sonnet
context: fork
agent: reviewer-sonnet
allowed-tools:
  - Read
  - Bash
  - Grep
  - Task
---

# Code Review Skill

**Status**: Active
**Last Updated**: 2026-02-08

---

## Overview

Pre-commit code review, testing patterns, and quality gates using native Claude agents.

---

## When to Use

Invoke this skill when:
- Preparing to commit code changes
- Reviewing pull requests
- Implementing new features (quality gate)
- Writing or updating tests

---

## MANDATORY: Review Before Commit

**ALWAYS spawn a reviewer before committing**. Use the native Task tool:

```
Task(
    subagent_type="reviewer-sonnet",
    description="Review staged changes",
    prompt="Review all staged changes for: code quality, security issues, performance, and potential bugs. Provide severity-rated findings."
)
```

For comprehensive quality gates, run review + security + tests in parallel:

```
# All three run simultaneously in one message:
Task(subagent_type="reviewer-sonnet", prompt="Review staged changes for quality and bugs")
Task(subagent_type="security-sonnet", prompt="Security scan of changed files")
Task(subagent_type="tester-haiku", prompt="Verify test coverage for changed code")
```

---

## Pre-Commit Checklist

Before committing, verify:
- [ ] Code follows project conventions
- [ ] Tests added/updated for changes
- [ ] No debugging code (console.log, print statements)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling implemented
- [ ] reviewer-sonnet spawned and findings addressed

---

## Review Process

### 1. Self-Review

```bash
git diff --staged           # Review staged changes
git diff --stat             # Check scope of changes
```

### 2. Spawn Reviewer

```
Task(subagent_type="reviewer-sonnet", prompt="Review the following changes: [describe]")
```

### 3. Address Findings

| Severity | Action |
|----------|--------|
| **Critical** | Must fix before commit (security, data loss) |
| **High** | Should fix (bugs, performance) |
| **Medium** | Fix if time allows (quality, maintainability) |
| **Low** | Note for future (style, minor improvements) |

---

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

---

## Key Gotchas

1. **Skipping review**: "It's just a small change" - bugs hide in small changes. Always review.
2. **Author blindness**: Can't see own mistakes. The reviewer agent catches what self-review misses.
3. **Missing edge cases**: Test null inputs, empty arrays, max values, unicode.

---

**Version**: 2.0 (Rewritten to use native Task agents instead of orchestrator MCP)
**Created**: 2025-12-26
**Updated**: 2026-02-08
**Location**: .claude/skills/code-review/skill.md
