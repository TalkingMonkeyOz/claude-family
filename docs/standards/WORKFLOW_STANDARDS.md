# Workflow Standards

**Document Type**: Standard
**Version**: 1.0
**Created**: 2025-12-07
**Status**: Active
**Enforcement**: MANDATORY - All work MUST follow these workflows

---

## Purpose

Define consistent workflows for all development work. These standards ensure:
- Predictable process from idea to deployment
- Quality gates at each stage
- Clear handoffs and responsibilities
- Traceable work through the system

---

## 1. Work Item Lifecycle

### 1.1 Overview

```
IDEA → FEEDBACK → FEATURE → BUILD_TASKS → IMPLEMENTATION → REVIEW → DEPLOY
```

### 1.2 Work Item Types

| Type | What Goes Here | Table |
|------|----------------|-------|
| Feedback | Ideas, bugs, questions, design suggestions | `claude.feedback` |
| Feature | Approved scope, requirements | `claude.features` |
| Build Task | Individual implementation tasks | `claude.build_tasks` |
| Session | Work performed in a Claude session | `claude.sessions` |

### 1.3 Status Flow

**Feedback Status:**
```
new → in_progress → fixed/wont_fix
```

**Feature Status:**
```
draft → approved → in_progress → completed → cancelled
```

**Build Task Status:**
```
not_started → in_progress → blocked → completed → cancelled
```

---

## 2. Design → Build → Test → Document

### 2.1 The Core Workflow

Every feature follows this sequence:

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. DESIGN                                                        │
│    - Understand requirements                                     │
│    - Research existing code                                      │
│    - Plan approach                                               │
│    - Document decisions (ADR if significant)                     │
├─────────────────────────────────────────────────────────────────┤
│ 2. BUILD                                                         │
│    - Implement following DEVELOPMENT_STANDARDS.md               │
│    - Follow UI_COMPONENT_STANDARDS.md (if UI)                   │
│    - Follow API_STANDARDS.md (if API)                           │
│    - Follow DATABASE_STANDARDS.md (if DB)                       │
├─────────────────────────────────────────────────────────────────┤
│ 3. TEST                                                          │
│    - Write tests (unit, integration, E2E as needed)             │
│    - Run existing test suite                                     │
│    - Verify no regressions                                       │
│    - Manual testing of user flows                                │
├─────────────────────────────────────────────────────────────────┤
│ 4. DOCUMENT                                                      │
│    - Update CLAUDE.md if behavior changed                       │
│    - Update ARCHITECTURE.md if structure changed                │
│    - Add inline comments for complex logic                      │
│    - Update API docs if endpoints changed                       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Skipping Steps

| Situation | Can Skip |
|-----------|----------|
| Trivial bug fix (< 10 lines) | Design, Document |
| Pure refactoring (no behavior change) | Document (unless structure) |
| Documentation-only change | Build, Test |
| Emergency hotfix | Document (add later) |

**Never skip:** Test for any code change

---

## 3. Session Workflow

### 3.1 Session Start (MANDATORY)

```
/session-start
```

This command:
1. Auto-detects your Claude identity
2. Auto-detects project from working directory
3. Logs session start to PostgreSQL
4. Returns context from previous sessions

### 3.2 During Session

**Every task should:**
1. Check existing patterns before implementing new code
2. Use TodoWrite to track multi-step work
3. Reference relevant standards (see Section 6)
4. Run tests before declaring complete

**Check shared knowledge:**
```sql
SELECT * FROM claude.shared_knowledge
WHERE project_id = 'current-project-id'
  AND is_current = true
ORDER BY created_at DESC;
```

### 3.3 Session End (MANDATORY)

```
/session-end
```

This command:
1. Auto-finds your unclosed session
2. Prompts for summary (fill in templates)
3. Closes session in database
4. Logs work performed

**Summary template:**
```
## What was done
- [List key accomplishments]

## Files changed
- [List significant files]

## What's next
- [List follow-up tasks]

## Blockers/Issues
- [Any problems encountered]
```

---

## 4. Code Review Process

### 4.1 Self-Review Checklist

Before requesting review:

- [ ] Code compiles/runs without errors
- [ ] All tests pass
- [ ] No console.log or debug statements
- [ ] No commented-out code
- [ ] Follows naming conventions
- [ ] Error handling in place
- [ ] No hardcoded secrets/credentials
- [ ] Performance considerations addressed
- [ ] Mobile responsive (if UI)

### 4.2 Review Focus Areas

| Area | Check For |
|------|-----------|
| Logic | Edge cases, off-by-one, null handling |
| Security | Injection, auth, data exposure |
| Performance | N+1 queries, missing indexes, memory leaks |
| Maintainability | Complexity, naming, abstractions |
| Standards | Follows project patterns |

### 4.3 Review Response

| Severity | Action Required |
|----------|-----------------|
| Critical | Must fix before merge |
| High | Should fix, blocking |
| Medium | Fix or explain |
| Low | Nice to have |

---

## 5. Testing Process

### 5.1 Test Levels

| Level | What | When | Coverage Target |
|-------|------|------|-----------------|
| Unit | Individual functions | Every change | 80% new code |
| Integration | API endpoints, DB | Feature complete | Critical paths |
| E2E | User flows | Before release | Happy paths |
| Visual | Screenshots | UI changes | Key screens |

### 5.2 Test Naming

```typescript
// Pattern: should [action] when [condition]
describe('UserService', () => {
  describe('createUser', () => {
    it('should create user when valid data provided', async () => { });
    it('should throw ValidationError when email invalid', async () => { });
    it('should throw ConflictError when email exists', async () => { });
  });
});
```

### 5.3 Test Structure (AAA)

```typescript
it('should return user when found', async () => {
  // Arrange - set up test data
  const userId = 'test-id';
  const mockUser = { id: userId, name: 'Test' };
  db.users.findOne.mockResolvedValue(mockUser);

  // Act - call the function
  const result = await userService.getUser(userId);

  // Assert - verify expectations
  expect(result).toEqual(mockUser);
  expect(db.users.findOne).toHaveBeenCalledWith({ id: userId });
});
```

### 5.4 Running Tests

```bash
# Before committing
npm test                    # Unit tests
npm run test:integration    # Integration tests

# Before PR merge
npm run test:e2e           # E2E tests

# Check coverage
npm run test:coverage
```

---

## 6. Standards Reference by Task Type

### 6.1 Task Detection

The process router automatically injects relevant standards based on task keywords:

| Task Contains | Inject Standard |
|---------------|-----------------|
| UI, component, page, form, table | UI_COMPONENT_STANDARDS.md |
| API, endpoint, route, REST | API_STANDARDS.md |
| database, SQL, schema, migration | DATABASE_STANDARDS.md |
| code, implement, refactor, fix | DEVELOPMENT_STANDARDS.md |
| test, testing, spec | Testing sections |

### 6.2 Manual Reference

When in doubt, reference the appropriate standard:

```markdown
For UI work: See docs/standards/UI_COMPONENT_STANDARDS.md
For API work: See docs/standards/API_STANDARDS.md
For DB work: See docs/standards/DATABASE_STANDARDS.md
For all code: See docs/standards/DEVELOPMENT_STANDARDS.md
```

---

## 7. Git Workflow

### 7.1 Branch Strategy

```
main (production)
  └── develop (integration)
       ├── feature/PROJ-123-user-auth
       ├── feature/PROJ-124-dashboard
       └── bugfix/PROJ-125-login-error
```

### 7.2 Commit Guidelines

```
<type>: <description>

[body - explain WHY]

[footer - references]
```

**Types:** feat, fix, docs, style, refactor, test, chore

**Example:**
```
feat: Add user profile page

Allow users to view and edit their profile information.
Includes avatar upload and email change functionality.

Closes #123
```

### 7.3 PR Guidelines

**Title:** `[PROJ-123] Brief description`

**Body:**
```markdown
## Summary
Brief description of changes

## Changes
- List of specific changes

## Test Plan
- [ ] Unit tests added
- [ ] Manual testing done
- [ ] E2E tests pass

## Screenshots (if UI)
[Before/After screenshots]
```

---

## 8. Deployment Workflow

### 8.1 Pre-Deployment Checklist

- [ ] All tests pass
- [ ] Code reviewed and approved
- [ ] No blocking issues
- [ ] Documentation updated
- [ ] Database migrations ready
- [ ] Feature flags configured (if needed)
- [ ] Rollback plan documented

### 8.2 Deployment Steps

```
1. Merge PR to main
2. Run migrations (if any)
3. Deploy to staging
4. Smoke test staging
5. Deploy to production
6. Verify production
7. Monitor for errors
```

### 8.3 Rollback

If issues detected:
1. Immediately revert to previous version
2. Assess impact
3. Fix issue in new PR
4. Re-deploy when fixed

---

## 9. Documentation Workflow

### 9.1 When to Update Docs

| Change | Update |
|--------|--------|
| New feature | CLAUDE.md, possibly ARCHITECTURE.md |
| API change | API docs, CLAUDE.md |
| Architecture change | ARCHITECTURE.md |
| New process | SOP document |
| Significant decision | ADR document |

### 9.2 Document Staleness Rules

| Document | Max Age | Action |
|----------|---------|--------|
| CLAUDE.md | 7 days | Review and update |
| ARCHITECTURE.md | 30 days | Review structure |
| README.md | 30 days | Check accuracy |
| SOPs | 90 days | Validate process |

### 9.3 Version Footer

All docs must have:
```markdown
---
**Version**: 1.0
**Created**: YYYY-MM-DD
**Updated**: YYYY-MM-DD
**Location**: path/to/file.md
```

---

## 10. Emergency Procedures

### 10.1 Production Bug

```
1. Assess severity (P1-P4)
2. If P1/P2: Alert team immediately
3. Create hotfix branch from main
4. Fix with minimal changes
5. Test fix locally
6. Fast-track review (1 reviewer)
7. Deploy immediately
8. Create follow-up ticket for proper fix
```

### 10.2 Severity Levels

| Level | Description | Response Time |
|-------|-------------|---------------|
| P1 | Complete outage | Immediate |
| P2 | Major feature broken | < 1 hour |
| P3 | Minor feature broken | < 24 hours |
| P4 | Cosmetic/low impact | Normal sprint |

### 10.3 Post-Incident

After any P1/P2:
1. Document what happened
2. Identify root cause
3. Create prevention tasks
4. Share learnings

---

## Quick Reference

### Daily Workflow
```
1. /session-start
2. Check previous session context
3. Pick task from build_tasks or feedback
4. Design → Build → Test → Document
5. Update task status
6. /session-end
```

### Before Any Code Change
```
1. Read existing code first
2. Check for existing patterns
3. Reference relevant standard
4. Plan approach
```

### Before Committing
```
1. Run tests
2. Self-review checklist
3. Clear commit message
4. Update docs if needed
```

---

## Related Documents

- DEVELOPMENT_STANDARDS.md - Code conventions
- UI_COMPONENT_STANDARDS.md - UI patterns
- API_STANDARDS.md - API conventions
- DATABASE_STANDARDS.md - Database patterns
- SOP-002: Build Task Lifecycle - Task workflow
- SOP-006: Testing Process - Test requirements

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-07 | Initial version |
