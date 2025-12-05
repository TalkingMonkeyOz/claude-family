# {{PROJECT_NAME}}

**Type**: {{PROJECT_TYPE}}
**Status**: {{PROJECT_PHASE}}
**Project ID**: `{{PROJECT_ID}}`

---

## Problem Statement

{{PROBLEM_SUMMARY}}

**Full details**: See `PROBLEM_STATEMENT.md`

---

## Current Phase

**Phase**: {{PROJECT_PHASE}}
**Focus**: {{CURRENT_FOCUS}}

---

## Session Protocol

**BEFORE starting work:**
```
/session-start
```

**BEFORE ending session:**
```
/session-end
```

---

## Work Tracking

| I have... | Put it in... | How |
|-----------|--------------|-----|
| An idea | feedback | type='idea' |
| A bug | feedback | type='bug' |
| A feature to build | features | link to project |
| A task to do | build_tasks | link to feature |
| Work right now | TodoWrite | session only |

---

## Data Gateway

**MANDATORY**: Before writing to constrained columns, check valid values:

```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

---

## Build Commands

```bash
# Development
{{DEV_COMMAND}}

# Test
{{TEST_COMMAND}}

# Build
{{BUILD_COMMAND}}
```

---

## Key Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | This file - Claude instructions |
| `PROBLEM_STATEMENT.md` | What problem this solves |
| `ARCHITECTURE.md` | System design |
| `README.md` | User documentation |

---

## Recent Work

```sql
SELECT summary, outcome, session_start
FROM claude.sessions
WHERE project_name = '{{PROJECT_NAME}}'
ORDER BY session_start DESC LIMIT 5;
```

---

**Version**: 1.0
**Created**: {{CREATED_DATE}}
**Location**: C:\Projects\{{PROJECT_NAME}}\CLAUDE.md
