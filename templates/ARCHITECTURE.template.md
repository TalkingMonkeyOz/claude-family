# Architecture - {{PROJECT_NAME}}

**Project**: {{PROJECT_NAME}}
**Version**: 1.0
**Updated**: {{CREATED_DATE}}
**Status**: Active

---

## Overview

{{PROJECT_OVERVIEW}}

```
{{ARCHITECTURE_DIAGRAM}}
```

---

## System Components

### 1. {{COMPONENT_1_NAME}}

{{COMPONENT_1_DESCRIPTION}}

### 2. {{COMPONENT_2_NAME}}

{{COMPONENT_2_DESCRIPTION}}

### 3. {{COMPONENT_3_NAME}}

{{COMPONENT_3_DESCRIPTION}}

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | {{FRONTEND_TECH}} | {{FRONTEND_PURPOSE}} |
| Backend | {{BACKEND_TECH}} | {{BACKEND_PURPOSE}} |
| Database | {{DATABASE_TECH}} | {{DATABASE_PURPOSE}} |
| Infrastructure | {{INFRA_TECH}} | {{INFRA_PURPOSE}} |

---

## Key Workflows

### {{WORKFLOW_1_NAME}}

```
{{WORKFLOW_1_DIAGRAM}}
```

### {{WORKFLOW_2_NAME}}

```
{{WORKFLOW_2_DIAGRAM}}
```

---

## Directory Structure

```
{{PROJECT_NAME}}/
├── src/                  # Source code
│   ├── {{SRC_FOLDER_1}}/
│   └── {{SRC_FOLDER_2}}/
├── tests/                # Test files
├── docs/                 # Documentation
├── CLAUDE.md             # Claude instructions
├── PROBLEM_STATEMENT.md  # Problem definition
├── ARCHITECTURE.md       # This document
└── README.md             # User documentation
```

---

## Data Model

### Key Entities

| Entity | Purpose | Key Fields |
|--------|---------|------------|
| {{ENTITY_1}} | {{ENTITY_1_PURPOSE}} | {{ENTITY_1_FIELDS}} |
| {{ENTITY_2}} | {{ENTITY_2_PURPOSE}} | {{ENTITY_2_FIELDS}} |

---

## Integration Points

### External Services

| Service | Purpose | Notes |
|---------|---------|-------|
| {{SERVICE_1}} | {{SERVICE_1_PURPOSE}} | {{SERVICE_1_NOTES}} |

### Internal APIs

| Endpoint | Method | Purpose |
|----------|--------|---------|
| {{ENDPOINT_1}} | {{METHOD_1}} | {{ENDPOINT_1_PURPOSE}} |

---

## Security Considerations

- {{SECURITY_1}}
- {{SECURITY_2}}

---

## Related Documents

- `PROBLEM_STATEMENT.md` - What problem this solves
- `CLAUDE.md` - Claude instructions
- `README.md` - User documentation

---

## Architectural Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| ADR-001 | {{ADR_1_TITLE}} | {{ADR_1_STATUS}} |

See `claude.architecture_decisions` table for full records.

---

**Maintained by**: {{MAINTAINER}}
**Review Cycle**: Monthly or on major changes
