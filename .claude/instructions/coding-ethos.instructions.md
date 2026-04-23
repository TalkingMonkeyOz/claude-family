---
description: 'Universal coding ethos — readable, extendable, maintainable. Anti-point-solution rules.'
applyTo: '**/*.ts,**/*.tsx,**/*.py,**/*.cs,**/*.rs,**/*.sql'
source: 'Claude Family (DB: instructions)'
---

# Coding Ethos (Universal)

## Before Writing Code
1. **SEARCH first** — run `workspaceSymbol` (LSP) to check if function/variable already exists
2. **READ the file** — run `documentSymbol` (LSP) to understand file structure before editing
3. **CHECK IMPACT** — run `incomingCalls`/`outgoingCalls` (LSP) before changing function signatures
4. **STRUCTURAL SEARCH** — use `ast-grep --pattern` via Bash for cross-file pattern detection

## The 12 Rules
1. Search Before You Create — duplicate utilities are the #1 AI coding problem
2. If Used Twice, Extract It — to utils/, hooks/, constants/, components/
3. Name for Strangers — variables=nouns, functions=verbs, booleans=is/has/should
4. Comment WHY not WHAT — intent, constraints, workarounds
5. Single Responsibility — one function, one job
6. Small Functions (<30 lines), Small Files (<300 lines)
7. Fail Explicitly — never swallow errors
8. Flat Over Nested — early returns, guard clauses
9. Consistent Patterns — follow codebase conventions
10. Separation of Concerns — UI renders, hooks manage state, utils transform
11. Composition Over Inheritance
12. Delete Boldly — dead code confuses AI and humans. Git remembers.

## Pseudocode First
For complex logic: write numbered pseudocode comments, then implement beneath each.

Full details: [[Coding Ethos]]