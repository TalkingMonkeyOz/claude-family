---
projects:
- claude-family
- all
tags:
- coding-standards
- ethos
- examples
---

# Coding Ethos — Detail

Detailed examples and guidance for each rule in [[Coding Ethos]].

## Rule 3: Naming Conventions

**Variables** — nouns describing the data:
```
// Bad           // Good
const d = [];    const activeProjects = [];
const tmp = x;   const formattedDate = formatDate(raw);
const flag = t;  const isAuthenticated = true;
```

**Functions** — verbs describing the action:
```
// Bad           // Good
process()        validateUserInput()
handle()         handleFormSubmission()
do()             calculateMonthlyRevenue()
```

**Booleans** — start with `is`, `has`, `should`, `can`:
```
isLoading, hasPermission, shouldRefresh, canEdit
```

**Constants** — UPPER_SNAKE_CASE:
```
MAX_RETRY_COUNT, DEFAULT_PAGE_SIZE, API_BASE_URL
```

## Rule 4: Comment Examples

```typescript
// Bad: increments counter
counter++;

// Good: retry up to 3 times — vendor API has transient 503s
counter++;

// Good: skip first element — API returns header row mixed with data
const dataRows = response.slice(1);
```

**When to comment**: business rules, workarounds (with issue link), performance choices, complex algorithms (pseudocode summary).

**When NOT to comment**: self-explanatory code, TODOs without tracking ref (use `// TODO(FB42): desc`).

## Rule 5: Single Responsibility Example

```typescript
// Bad: does two things
function loadAndDisplayUsers() { ... }

// Good: separated
function loadUsers(): User[] { ... }
function displayUsers(users: User[]): void { ... }
```

**Test**: Can you describe the function in one sentence without using "and"?

## Rule 7: Error Handling

```typescript
// Bad: silent failure
try { await save(data); } catch { }

// Good: explicit handling
try {
  await save(data);
} catch (err) {
  console.error('Failed to save:', err);
  showErrorNotification('Save failed. Please try again.');
}
```

## Rule 8: Flat Over Nested

```typescript
// Bad: 4 levels deep
if (user) {
  if (user.isActive) {
    if (user.hasPermission('edit')) {
      doEdit();
    }
  }
}

// Good: flat with guards
if (!user) return;
if (!user.isActive) return;
if (!user.hasPermission('edit')) return;
doEdit();
```

## Research Basis

These principles draw from:
- **Clean Code** (Robert Martin) — naming, SRP, small functions
- **Qodo State of AI Code Quality 2025** — AI code has 1.7x more bugs
- **Addy Osmani's AI Coding Workflow** — spec-first, small chunks, CLAUDE.md rules
- **CodeRabbit 2026 Report** — shift from speed to quality
- **GetDX Enterprise AI Adoption** — 65% cite missing context as top refactoring issue

---

**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: knowledge-vault/30-Patterns/coding-ethos-detail.md
