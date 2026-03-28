---
projects:
- claude-family
- project-metis
tags:
- research
- architecture
- coding-intelligence
- design
---

# SCE Approaches Detail

Companion to [[Semantic Code Engine — Research Document]].

## Approach 1: Enhanced CKG (Engineering)

**What**: Add symbol bodies to existing CKG. Build `get_context()`. Continuous re-indexing via hooks.

**Key tools**: `get_context(symbol, depth)` — returns symbol body + callers + callees + types + patterns + standards in ONE call.

**Solves**: Discovery overhead (eliminates re-reading), pattern inconsistency (detects, doesn't prevent).

**Doesn't solve**: Missing constraints, accumulated drift.

## Approach 2: Semantic Code Layer (Engineering)

**What**: Files for git, DB as AI working copy. AI reads/writes DB. Files generated for build/commit.

**Key tools**: `update_symbol()`, `create_symbol()`, `generate_files()`, `build_project()`.

**Solves**: Context loss (full DB always in sync), cross-file coordination (atomic changes), error cascade (transactions + rollback).

## Approach 3: Intent-Based Programming (Research)

**What**: Store structured INTENT, not code. `{intent: "fetch_odata_entity", strategy: "tauri_command"}` → generates TypeScript/Rust/C#.

**Key insight**: Wrong patterns become structurally impossible. Intent declarations constrain implementation strategies.

**Research questions**:
- Can an intent schema cover all programming constructs?
- How do you handle edge cases that don't fit the schema?
- Can AI generate its own code generator from intent specifications?
- What's the debugging experience when generated code fails at runtime?

**Prior art**: Intentional Programming (Simonyi), Domain-Specific Languages.

## Approach 4: Component Assembly (Engineering)

**What**: Store higher-level COMPONENTS. Each = interface + dependencies + behavior spec + implementation. ONE ODataEntityFetcher, every page uses it.

**Key insight**: Reuse becomes structural, not aspirational. Components are versioned with stable interfaces.

## Approach 5: AI Intermediate Representation (Research)

**What**: Representation organized by CONCEPTS and BEHAVIOR, not files and syntax. "OData Data Layer" is one concept with entities, constraints, patterns.

**Research questions**:
- What's the right granularity for concepts?
- How do concepts compose and inherit?
- Can existing codebases be reverse-engineered into concepts?
- How does cross-language generation work (same concept → TypeScript + Rust)?

## Approach 6: Pattern-Constrained Generation (Engineering)

**What**: Formalize repeating patterns as templates + data + constraints. AI parameterizes patterns. Generator produces code.

**Key tools**:
- `register_pattern(name, template, constraints, anti_patterns)`
- `apply_pattern(name, parameters)` — instantiate template
- `regenerate_from_pattern(name)` — update ALL instances
- `detect_pattern_violation(file)` — check existing code

**Pattern record structure**:
```yaml
name: odata-entity-fetcher
language: typescript
framework: react + tauri
template: (code template with ${placeholders} and ${EXTENSION_POINT}s)
constraints: [MUST use execute_odata_query, MUST return [] on error]
anti_patterns: [MUST NOT use execute_rest_get]
examples: [fetchAgreements, fetchScheduleGroups]
test_template: (test generation template)
scope: src/lib/api/
```

**Killer feature**: Change pattern template once → regenerate all instances. Turns 2-day refactoring into 10-minute operation.

## Realistic Scenario Impact

| Scenario | Current | +Approach 1 | +Approach 6 | +Approach 3 |
|---|---|---|---|---|
| Add entity fetcher | 5-60 min | 2-3 min | 30 sec | 30 sec |
| Refactor API calls | 1-3 hours | 30-60 min | 5-10 min | 5 min |
| Parallel run breaks | 2-4 DAYS | 30-60 min | Impossible | Impossible |
| New project setup | Hours | Hours | 30 min (patterns) | Minutes (intents) |
| Cross-language port | Days-weeks | Days | Hours (templates) | Auto-generated |

---
**Version**: 1.0
**Created**: 2026-03-25
**Updated**: 2026-03-25
**Location**: knowledge-vault/20-Domains/coding-intelligence/sce-approaches-detail.md
