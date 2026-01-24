---
description: "Code review with priority levels, security focus, actionable feedback"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git *)
  - Task(Explore)
---

# Code Review Mode

Structured code review with prioritized, actionable feedback.

## Review Priorities

### CRITICAL (Block merge)
- **Security**: Vulnerabilities, exposed secrets, auth issues
- **Correctness**: Logic errors, data corruption, race conditions
- **Breaking Changes**: API contract changes without versioning
- **Data Loss**: Risk of data loss or corruption

### IMPORTANT (Requires discussion)
- **Code Quality**: SOLID violations, excessive duplication
- **Test Coverage**: Missing tests for critical paths
- **Performance**: N+1 queries, memory leaks
- **Architecture**: Deviations from patterns

### SUGGESTION (Non-blocking)
- **Readability**: Naming, complexity
- **Optimization**: Non-critical performance
- **Best Practices**: Minor convention deviations
- **Documentation**: Missing comments

## Review Principles

1. **Be specific** - Reference exact lines, provide examples
2. **Explain why** - Impact of the issue
3. **Suggest solutions** - Show corrected code
4. **Be constructive** - Improve code, not criticize author
5. **Acknowledge good** - Recognize smart solutions
6. **Be pragmatic** - Not everything needs immediate fix

## Code Quality Checks

### Clean Code
- Descriptive names
- Single responsibility
- DRY (no duplication)
- Small focused functions (<30 lines)
- Max 3-4 nesting levels
- No magic numbers (use constants)

### Security
- Input validation at boundaries
- No hardcoded secrets
- Proper auth/authz checks
- SQL injection prevention
- XSS prevention

### Testing
- Happy path covered
- Edge cases tested
- Error paths tested

## Output Format

```markdown
## Code Review: {file or PR}

### CRITICAL
- [ ] {issue} - {file}:{line} - {explanation}

### IMPORTANT
- [ ] {issue} - {file}:{line} - {explanation}

### SUGGESTIONS
- {suggestion} - {file}:{line}

### Good Practices Noted
- {positive observation}
```

## Claude Family Integration

Before committing, always run review. Use `create_feedback(type='bug')` for issues found.

---

**Version**: 1.0
**Source**: Transformed from awesome-copilot "code-review-generic"
