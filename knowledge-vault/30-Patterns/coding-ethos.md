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

## Prime Directive — Value Is System Quality

**Every decision is judged by whether it makes the system work better.** Not by tokens saved. Not by money saved. Not by time-to-finish. Not by effort-to-avoid.

When faced with a choice between "quick" and "right", pick right unless the user has explicitly scoped the work to quick. When faced with "archive stale content to move faster" vs "split and preserve properly", preserve properly. When faced with "bypass the hook with OVERRIDE" vs "fix the root cause", fix the root cause.

Tokens and money are *constraints*, not *goals*. Value is what the system does for its users after this change — clarity for future readers, precision for future retrieval, correctness under edge cases, resilience under failure. Optimise for that, and the other constraints come out right on average.

The anti-pattern to watch for in yourself: "this is easier / quicker / cheaper, so it must be better." It usually is not. If a choice saves effort *and* produces a better system, good. If it saves effort but produces a worse system, it is not the right choice — even if the user said "crack on".

## The Four Pillars

Every line of code must be **Readable**, **Extendable**, **Maintainable**, and **Testable**:

- **Readable**: A stranger can understand the code without asking the author
- **Extendable**: New features can be added without rewriting existing code
- **Maintainable**: Bugs can be found and fixed without side effects
- **Testable**: The code can be verified automatically without manual inspection

If you must sacrifice one, sacrifice extendability. Readable + maintainable + testable code can be made extendable later. Tests are the safety net that makes AI-assisted development viable.

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
- **Never commit code you can't explain** — if asked "why does this work?", you must be able to answer
- **Read before writing** — always read the file and surrounding code first
- **Check for existing patterns** — search before creating new utilities (`find_symbol`, `check_collision`)
- **Match existing style** — semicolons, quotes, indentation, naming
- **Minimize blast radius** — change as little as possible to achieve the goal
- **Prefer simple over abstract** — 3 similar lines > premature abstraction. AI can refactor later if needed

### For the Human:
- AI code has **1.7x more issues** than human code — review every line
- Provide context — the more Claude knows, the better the result
- Commit frequently — small commits isolate AI-introduced issues
- Use standards files — they're read every session automatically
- **Don't accept code you can't explain** — if you don't understand it, don't merge it

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

**Version**: 1.2
**Created**: 2026-03-19
**Updated**: 2026-04-24
**Location**: knowledge-vault/30-Patterns/coding-ethos.md

**Changelog**:
- v1.2 (2026-04-24): Added Prime Directive — value is system quality, not tokens or money.
- v1.1 (2026-03-22): Detail examples.
- v1.0 (2026-03-19): 4 Pillars + 12 Rules.
