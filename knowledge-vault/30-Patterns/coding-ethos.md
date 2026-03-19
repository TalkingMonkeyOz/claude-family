---
projects:
- claude-family
- all
tags:
- coding-standards
- ethos
- architecture
---

# Coding Ethos — Universal Principles

**Applies to ALL projects, ALL languages.** Language-specific standards supplement these, never override them.

These principles exist because AI-assisted coding tends toward "point solutions" — each prompt acts in isolation, creating fragmented code that works but doesn't compose. These rules prevent that.

## The Three Pillars

Every line of code must be **Readable**, **Extendable**, and **Maintainable**:

- **Readable**: A stranger can understand the code without asking the author
- **Extendable**: New features can be added without rewriting existing code
- **Maintainable**: Bugs can be found and fixed without side effects

If you must sacrifice one, sacrifice extendability. Readable + maintainable code can be made extendable later.

## The 12 Rules

| # | Rule | One-liner |
|---|------|-----------|
| 1 | **Search Before You Create** | Before writing a function, search the codebase for an existing one |
| 2 | **If It's Used Twice, Extract It** | Two occurrences → extract to shared location immediately |
| 3 | **Name Things for Strangers** | Variables = nouns, functions = verbs, booleans = is/has/should |
| 4 | **Comment the WHY, Not the WHAT** | Code says what. Comments explain intent, constraints, workarounds |
| 5 | **Single Responsibility** | One function = one job. Describe it without using "and" |
| 6 | **Small Functions, Small Files** | Functions < 30 lines, files < 300 lines, params ≤ 3 |
| 7 | **Fail Explicitly** | Never swallow errors. Never return null when you mean "not found" |
| 8 | **Flat Over Nested** | Early returns and guard clauses beat 4 levels of if/else |
| 9 | **Consistent Patterns** | Follow the codebase's established patterns. Change everywhere or nowhere |
| 10 | **Separation of Concerns** | UI renders. Hooks manage state. Utils transform. Constants define |
| 11 | **Composition Over Inheritance** | Build complex from simple pieces, not deep hierarchies |
| 12 | **Delete Boldly** | Dead code confuses readers and AI. Git remembers |

**Detailed guidance with examples**: See [[Coding Ethos — Detail]]

## AI-Specific Guidance

### For Claude:
- **Read before writing** — always read the file and surrounding code first
- **Check for existing patterns** — search before creating new utilities
- **Match existing style** — semicolons, quotes, indentation, naming
- **Minimize blast radius** — change as little as possible to achieve the goal

### For the Human:
- AI code has **1.7x more issues** than human code — review every line
- Provide context — the more Claude knows, the better the result
- Commit frequently — small commits isolate AI-introduced issues
- Use standards files — they're read every session automatically

## Pseudocode Convention

For complex logic, write pseudocode comments FIRST, then implement:

```
// 1. Load active projects from DB
// 2. For each project, check if config is stale
// 3. Collect stale projects into report
// 4. If any stale: trigger sync, return report
```

This helps both humans and future AI sessions understand intent.

## Where to Extract

| What | Extract to |
|------|-----------|
| Utility function | `src/utils/` or shared library |
| UI component | `src/components/` |
| Business logic | Custom hook or service |
| Constants/maps | `src/constants/` |
| Type definitions | `src/types/` |

---

**Version**: 1.0
**Created**: 2026-03-19
**Updated**: 2026-03-19
**Location**: knowledge-vault/30-Patterns/coding-ethos.md
