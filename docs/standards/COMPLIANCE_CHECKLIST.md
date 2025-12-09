# Standards Compliance Checklist

**Document Type**: Checklist
**Version**: 1.0
**Created**: 2025-12-08
**Status**: Active
**Purpose**: Verify project compliance with Claude Family standards

---

## How to Use This Checklist

1. **Select applicable sections** based on project type
2. **Check each item** - mark ✅ (compliant), ❌ (non-compliant), or N/A
3. **Document exceptions** with justification
4. **Track remediation** for non-compliant items

---

## 1. Project Structure (All Projects)

> Reference: DEVELOPMENT_STANDARDS.md Section 1

### Required Files

| Item | Status | Notes |
|------|--------|-------|
| CLAUDE.md exists at root | [ ] | |
| ARCHITECTURE.md exists at root | [ ] | |
| PROBLEM_STATEMENT.md exists at root | [ ] | |
| README.md exists at root | [ ] | |
| .gitignore exists | [ ] | |
| .claude/hooks.json exists | [ ] | |
| .claude/settings.local.json exists | [ ] | |

### Project Identity

| Item | Status | Notes |
|------|--------|-------|
| CLAUDE.md has project ID | [ ] | |
| CLAUDE.md has current phase/status | [ ] | |
| CLAUDE.md has recent changes section | [ ] | |
| ARCHITECTURE.md describes system design | [ ] | |
| PROBLEM_STATEMENT.md defines goals | [ ] | |

---

## 2. Development Standards

> Reference: DEVELOPMENT_STANDARDS.md

### Naming Conventions

| Item | Status | Notes |
|------|--------|-------|
| Directories use lowercase-kebab | [ ] | |
| TypeScript files use kebab-case | [ ] | |
| Python files use snake_case | [ ] | |
| Test files follow pattern (*.test.ts, *_test.py) | [ ] | |
| Variables use camelCase (TS) or snake_case (Python) | [ ] | |
| Classes/Types use PascalCase | [ ] | |
| Constants use UPPER_SNAKE_CASE | [ ] | |
| Boolean vars have is/has/can prefix | [ ] | |

### Code Organization

| Item | Status | Notes |
|------|--------|-------|
| Component files ≤ 200 lines | [ ] | |
| Service/module files ≤ 300 lines | [ ] | |
| Test files ≤ 500 lines | [ ] | |
| Functions ≤ 50 lines (ideal 10-20) | [ ] | |
| Imports follow standard order | [ ] | |

### Error Handling

| Item | Status | Notes |
|------|--------|-------|
| API errors use standard format | [ ] | |
| Specific error types (not generic catch) | [ ] | |
| No silent error swallowing | [ ] | |
| Structured logging used | [ ] | |
| No console.log in production code | [ ] | |

### TypeScript Quality

| Item | Status | Notes |
|------|--------|-------|
| No use of `any` type | [ ] | |
| Functions have explicit return types | [ ] | |
| Uses optional chaining (?.) | [ ] | |
| Uses nullish coalescing (??) | [ ] | |
| No TypeScript errors or warnings | [ ] | |

### Git Standards

| Item | Status | Notes |
|------|--------|-------|
| Commits follow type: description format | [ ] | |
| Branches follow type/ticket-description | [ ] | |
| No debug/console statements committed | [ ] | |
| No commented-out code | [ ] | |
| No hardcoded secrets | [ ] | |

---

## 3. UI Component Standards (Web Applications)

> Reference: UI_COMPONENT_STANDARDS.md

### Data Tables

| Item | Status | Notes |
|------|--------|-------|
| Tables have pagination | [ ] | |
| Default page size is 20 | [ ] | |
| Page size selector available | [ ] | |
| Shows "Showing X-Y of Z" | [ ] | |
| Tables have column sorting | [ ] | |
| Sort direction indicator visible | [ ] | |
| Tables have at least one filter | [ ] | |
| Text filters are debounced (300ms) | [ ] | |
| Status filters have "All" option | [ ] | |
| "Clear all filters" button when active | [ ] | |
| Row actions available (view/edit/delete) | [ ] | |
| >3 actions use dropdown menu | [ ] | |
| Delete action requires confirmation | [ ] | |

### Forms

| Item | Status | Notes |
|------|--------|-------|
| Labels appear ABOVE inputs | [ ] | |
| Required fields marked with asterisk (*) | [ ] | |
| Helper text below fields (gray) | [ ] | |
| Error text replaces helper (red) | [ ] | |
| Errors show on blur or submit | [ ] | |
| Client-side validation (format, required) | [ ] | |
| Server-side validation (uniqueness) | [ ] | |
| Scrolls to first error | [ ] | |
| Focuses first error field | [ ] | |
| Submit button shows loading state | [ ] | |
| Submit button disabled while submitting | [ ] | |
| Success feedback (toast/redirect) | [ ] | |

### Component States

| Item | Status | Notes |
|------|--------|-------|
| Loading state shows skeleton/spinner | [ ] | |
| Empty state has illustration | [ ] | |
| Empty state has helpful message | [ ] | |
| Empty state has action button | [ ] | |
| Error state has retry option | [ ] | |
| Error state logs to console | [ ] | |
| No technical errors shown to users | [ ] | |

### Dialogs

| Item | Status | Notes |
|------|--------|-------|
| Destructive actions have confirmation | [ ] | |
| Confirmation shows consequence | [ ] | |
| Cancel button on left (secondary) | [ ] | |
| Confirm button on right | [ ] | |
| Delete button styled as danger (red) | [ ] | |
| Closes on Escape key | [ ] | |
| Focus trapped inside modal | [ ] | |

### Accessibility

| Item | Status | Notes |
|------|--------|-------|
| All elements keyboard navigable | [ ] | |
| Visible focus indicators | [ ] | |
| Logical tab order | [ ] | |
| Icon buttons have aria-label | [ ] | |
| Form inputs have associated labels | [ ] | |
| Text has 4.5:1 contrast ratio | [ ] | |
| Not relying on color alone | [ ] | |

### Responsive Design

| Item | Status | Notes |
|------|--------|-------|
| Works on mobile (640px) | [ ] | |
| Works on tablet (768px) | [ ] | |
| Works on desktop (1024px+) | [ ] | |
| Tables adapt for mobile | [ ] | |
| Forms stack on mobile | [ ] | |

---

## 4. API Standards (Backend Services)

> Reference: API_STANDARDS.md

### URL Structure

| Item | Status | Notes |
|------|--------|-------|
| Uses plural nouns (/users not /user) | [ ] | |
| Lowercase with hyphens | [ ] | |
| No trailing slashes | [ ] | |
| No verbs in URLs (except actions) | [ ] | |
| Version in URL (/api/v1/) | [ ] | |

### HTTP Methods

| Item | Status | Notes |
|------|--------|-------|
| GET for reading | [ ] | |
| POST for creating (returns 201) | [ ] | |
| PUT for full replace | [ ] | |
| PATCH for partial update | [ ] | |
| DELETE for removal (returns 204) | [ ] | |

### Response Format

| Item | Status | Notes |
|------|--------|-------|
| Single resource in `data` wrapper | [ ] | |
| Collections in `data` array | [ ] | |
| Pagination in `meta` object | [ ] | |
| Errors in `error` object | [ ] | |
| Error has `code` field | [ ] | |
| Error has `message` field | [ ] | |
| Uses standard error codes | [ ] | |
| camelCase for JSON keys | [ ] | |

### Pagination

| Item | Status | Notes |
|------|--------|-------|
| All list endpoints paginated | [ ] | |
| Supports page & pageSize params | [ ] | |
| Default pageSize is 20 | [ ] | |
| Max pageSize is 100 | [ ] | |
| Returns totalItems in meta | [ ] | |
| Returns totalPages in meta | [ ] | |

### Security

| Item | Status | Notes |
|------|--------|-------|
| Authentication required | [ ] | |
| Authorization checks in place | [ ] | |
| Input validation on all inputs | [ ] | |
| No sensitive data in responses | [ ] | |
| Parameterized SQL queries | [ ] | |
| Rate limiting configured | [ ] | |
| CORS headers set correctly | [ ] | |

---

## 5. Database Standards (PostgreSQL)

> Reference: DATABASE_STANDARDS.md

### Schema Design

| Item | Status | Notes |
|------|--------|-------|
| Tables use plural snake_case | [ ] | |
| Columns use snake_case | [ ] | |
| UUID primary keys (not SERIAL) | [ ] | |
| Foreign keys reference table_id | [ ] | |
| Index names follow idx_table_column | [ ] | |
| Constraint names follow type_table_column | [ ] | |

### Standard Columns

| Item | Status | Notes |
|------|--------|-------|
| All tables have `id` (UUID) | [ ] | |
| All tables have `created_at` (TIMESTAMPTZ) | [ ] | |
| All tables have `updated_at` (TIMESTAMPTZ) | [ ] | |
| updated_at trigger exists | [ ] | |

### Data Types

| Item | Status | Notes |
|------|--------|-------|
| Uses TIMESTAMPTZ (not TIMESTAMP) | [ ] | |
| Uses NUMERIC for money (not FLOAT) | [ ] | |
| Uses VARCHAR+CHECK for enums (not ENUM) | [ ] | |
| Uses JSONB (not JSON) | [ ] | |

### Constraints

| Item | Status | Notes |
|------|--------|-------|
| Foreign keys have indexes | [ ] | |
| Status columns have CHECK constraints | [ ] | |
| Unique constraints where needed | [ ] | |
| NOT NULL on required fields | [ ] | |
| Cascade/restrict set appropriately | [ ] | |

### Query Standards

| Item | Status | Notes |
|------|--------|-------|
| All queries paginated (no SELECT *) | [ ] | |
| Explicit column selection | [ ] | |
| Parameterized queries (no concatenation) | [ ] | |
| No N+1 query patterns | [ ] | |
| EXPLAIN ANALYZE checked | [ ] | |

### Data Gateway (Claude Family)

| Item | Status | Notes |
|------|--------|-------|
| column_registry checked before writes | [ ] | |
| Valid values documented for enums | [ ] | |
| CHECK constraints match registry | [ ] | |

---

## 6. Workflow Standards

> Reference: WORKFLOW_STANDARDS.md

### Session Management

| Item | Status | Notes |
|------|--------|-------|
| /session-start run at beginning | [ ] | |
| /session-end run at end | [ ] | |
| Session logged to database | [ ] | |
| Summary includes work done | [ ] | |
| Summary includes next steps | [ ] | |

### Development Process

| Item | Status | Notes |
|------|--------|-------|
| Read existing code before modifying | [ ] | |
| Check for existing patterns | [ ] | |
| Design before building (complex features) | [ ] | |
| Tests written/run | [ ] | |
| Documentation updated | [ ] | |

### Code Review

| Item | Status | Notes |
|------|--------|-------|
| Self-review checklist completed | [ ] | |
| Tests pass before review | [ ] | |
| No console.log statements | [ ] | |
| No commented-out code | [ ] | |
| No hardcoded credentials | [ ] | |

---

## Compliance Summary

### Project Information

| Field | Value |
|-------|-------|
| Project Name | |
| Audit Date | |
| Auditor | |
| Project Type | Web App / API / Python / Other |

### Compliance Scores

| Standard | Compliant | Non-Compliant | N/A | Score |
|----------|-----------|---------------|-----|-------|
| Project Structure | | | | /7 |
| Development | | | | /25 |
| UI Components | | | | /45 |
| API | | | | /30 |
| Database | | | | /25 |
| Workflow | | | | /12 |
| **Total** | | | | |

### Non-Compliant Items (Priority Order)

| # | Item | Standard | Severity | Remediation |
|---|------|----------|----------|-------------|
| 1 | | | High/Med/Low | |
| 2 | | | | |
| 3 | | | | |

### Exceptions (Documented)

| Item | Justification | Approved By |
|------|---------------|-------------|
| | | |

---

## Audit History

| Date | Auditor | Score | Notes |
|------|---------|-------|-------|
| | | | |

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-08 | Initial version |

---

**Location**: C:\Projects\claude-family\docs\standards\COMPLIANCE_CHECKLIST.md
