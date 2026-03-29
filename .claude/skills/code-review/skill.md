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

---

## Overview

Pre-commit code review, testing patterns, and quality gates using native Claude agents.

**Detailed reference**: See [reference.md](./reference.md) for test patterns, security checks, and code quality metrics.

---

## When to Use

- Preparing to commit code changes
- Reviewing pull requests
- Implementing new features (quality gate)
- Writing or updating tests

---

## MANDATORY: Review Before Commit

**ALWAYS spawn a reviewer before committing**:

```
Task(
    subagent_type="reviewer-sonnet",
    description="Review staged changes",
    prompt="Review all staged changes for: code quality, security issues, performance, and potential bugs."
)
```

For comprehensive quality gates, run in parallel:

```
Task(subagent_type="reviewer-sonnet", prompt="Review staged changes for quality and bugs")
Task(subagent_type="security-sonnet", prompt="Security scan of changed files")
Task(subagent_type="tester-haiku", prompt="Verify test coverage for changed code")
```

---

## Pre-Commit Checklist

- [ ] Code follows project conventions
- [ ] Tests added/updated for changes
- [ ] No debugging code (console.log, print statements)
- [ ] No hardcoded secrets or credentials
- [ ] Error handling implemented
- [ ] reviewer-sonnet spawned and findings addressed

---

## Review Process

1. **Self-review**: `git diff --staged` and `git diff --stat`
2. **Spawn reviewer**: `Task(subagent_type="reviewer-sonnet", prompt="Review...")`
3. **Address findings** by severity:

| Severity | Action |
|----------|--------|
| **Critical** | Must fix (security, data loss) |
| **High** | Should fix (bugs, performance) |
| **Medium** | Fix if time allows (quality) |
| **Low** | Note for future (style) |

---

## Key Gotchas

1. **Skipping review** — bugs hide in small changes. Always review.
2. **Author blindness** — reviewer agent catches what self-review misses.
3. **Missing edge cases** — test null inputs, empty arrays, max values, unicode.

---

**Version**: 3.0 (Progressive disclosure: split to SKILL.md overview + reference.md detail)
**Created**: 2025-12-26
**Updated**: 2026-03-29
**Location**: .claude/skills/code-review/SKILL.md
