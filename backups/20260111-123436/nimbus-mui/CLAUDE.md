# Nimbus MUI - Modern Tauri Desktop Application

**Type**: Application
**Status**: Implementation
**Project ID**: `93571d08-788f-4a52-b19a-082222eb68f4`

---

## Coding Standards (Auto-Loaded)

@~/.claude/standards/core/markdown-documentation.md
@~/.claude/standards/language/typescript.md
@~/.claude/standards/language/rust.md
@~/.claude/standards/framework/react.md
@~/.claude/standards/framework/mui.md

---

## Problem Statement

Provide a modern, cross-platform desktop application for importing workforce management data into Nimbus systems. The app replaces legacy WinForms nimbus-user-loader with a modular, portable, and user-friendly solution.

**Key Requirements**:
- Pre-import validation (schema, referential, business rules, dry-run)
- Import execution (batch API, environment-aware, UAT→prod promotion)
- Error detection & reporting (row-level logs, CSV/Excel export)
- Post-import cross-checking (counts, key fields, audit trail)
- Award scenario validation (template-based, auto-compare)
- Selective import (all sections or individual sections)
- Security (role-based, production approvals)

---

## Architecture Overview

**Modular Design**: 6 pluggable modules (connection, cache, validation, import, report, audit)

**Portable Deployment**: Single EXE creates own folder structure (config/, logs/, cache/, exports/)

**Tech Stack**:
- Frontend: React 19 + MUI 7 + Zustand 5
- Desktop: Tauri 2.0
- Backend: Rust (reqwest, keyring, calamine, tokio)
- Build: Vite 7 + TypeScript 5

**Full details**: See `docs/ARCHITECTURE.md`

---

## Current Phase

**Phase**: P0 - Foundation (Week 1-2, 34 hours)
**Focus**: Project setup, authentication, profiles, Tauri commands
**Plan**: See plan file in `.claude/plans/` or `docs/IMPLEMENTATION_PLAN.md`

---

## Project Structure

```
nimbus-mui/
├── CLAUDE.md              # This file - Project constitution
├── docs/
│   ├── ARCHITECTURE.md    # Module design, data flows
│   ├── API_REFERENCE.md   # REST, OData, UserSDK endpoints
│   ├── VALIDATION_RULES.md # All validation rules documented
│   └── DEPLOYMENT.md      # Portable deployment guide
├── src/
│   ├── core/              # Core services (always loaded)
│   │   ├── api/           # API clients (HTTP, OData, REST, UserSDK)
│   │   ├── config/        # Configuration management
│   │   ├── logging/       # Structured logging + audit trail
│   │   └── types/         # Shared TypeScript types
│   ├── modules/           # Pluggable modules
│   │   ├── connection/    # Connection Module
│   │   ├── cache/         # Cache Module (IndexedDB + Zustand)
│   │   ├── validation/    # Validation Module (4-layer)
│   │   ├── import/        # Import Module (parallel batch)
│   │   ├── report/        # Report Module
│   │   └── audit/         # Audit Module
│   └── components/        # Shared UI components
└── src-tauri/             # Rust backend
    └── commands/          # Tauri IPC commands
```

---

## Coding Standards

- **TypeScript**: Strict mode, no `any` types
- **React**: Functional components, hooks only
- **Rust**: Safe code, minimal unwrap(), proper error handling
- **Imports**: Absolute paths via `@/` alias
- **Comments**: Only for complex business logic

---

## Work Tracking

| I have... | Put it in... | How |
|-----------|--------------|-----|
| A bug | feedback | type='bug' |
| A feature idea | feedback | type='idea' |
| An import task | TodoWrite | session only |

**Database First**: Check `claude.column_registry` before writing to constrained columns.

---

## Configuration

**Project Type**: `application` (no defaults inherited)

**MCP Servers**:
- `postgres` - Database access
- `memory` - Persistent memory graph
- `orchestrator` - Agent spawning
- `vault-rag` - Knowledge search

**Skills**: code-review, testing-patterns

**Hooks**: TodoWrite sync (PostToolUse)

---

## Standard Operating Procedures

For common operations, **read the vault SOP first**:

| Operation | Vault SOP |
|-----------|-----------|
| Nimbus authentication | `20-Domains/APIs/nimbus-authentication.md` |
| Entity creation | `20-Domains/APIs/nimbus-entity-creation-order.md` |
| OData caching | `20-Domains/APIs/nimbus-cache-strategy.md` |
| Parallel upload | `20-Domains/APIs/nimbus-parallel-upload.md` |

---

## Key Patterns

### Entity Dependency Order (CRITICAL)

```
1. Locations         ← No dependencies
2. Location Groups   ← Contains Locations (needs LocationIDs)
3. Departments       ← Belongs to Location (needs LocationID)
4. Cost Centres      ← No dependencies
5. Schedule Groups   ← References Location Groups
6. Users             ← References all above
```

### Two-Tier Caching

1. **IndexedDB** (persistent) - survives app restart
2. **Zustand Maps** (memory) - O(1) lookups

### Credential Storage

- **Tauri/Rust**: `keyring` crate → Windows Credential Manager
- **Service**: `"nimbus-mui"`
- **Key**: `profile:{profileName}`
- **Password**: Never in files, only OS keyring
- **Token**: In memory only, re-auth on restart

### Import Control Sections

**Not monolithic** - users toggle individual sections:
- User Core, User Details, Employments, Locations, Departments, Security Roles, etc.
- Each section has dependencies (e.g., Departments requires Locations)
- Security roles have modes: Add, Update, Replace

### Error Exports

All validation and import errors → `exports/` folder:
- `validation-errors-{timestamp}.xlsx` - Multi-sheet Excel
- `import-failures-{timestamp}.xlsx` - Failed records with API responses
- `import-summary-{timestamp}.html` - Visual report

---

## Critical Reference Files

Port these directly:
- `nimbus-import\src\services\validationEngine.ts` (778 lines)
- `nimbus-import\src\services\cacheLoader.ts` (1062 lines)
- `nimbus-import\src\services\entityCreation.ts` (400 lines)

Reference for patterns:
- `nimbus-user-loader\Services\ImportOrchestrator.cs`
- `nimbus-user-loader\Plugins.Monash\Services\NewmanProcessManagerV2.cs`

---

## Recent Changes

| Date | Change |
|------|--------|
| 2025-12-31 | Project initialized, registered in database, .claude/ folder created |

**Full changelog**: See git log

---

## Quick Queries

```sql
-- Check project status
SELECT * FROM claude.projects WHERE project_id = '93571d08-788f-4a52-b19a-082222eb68f4'::uuid;

-- Recent sessions
SELECT session_start, summary FROM claude.sessions
WHERE project_name = 'nimbus-mui' ORDER BY session_start DESC LIMIT 5;

-- Current todos
SELECT content, status FROM claude.todos
WHERE project_id = '93571d08-788f-4a52-b19a-082222eb68f4'::uuid
  AND is_deleted = false
ORDER BY display_order, priority;
```

---

**Version**: 1.0 (Initial setup)
**Created**: 2025-12-31
**Updated**: 2025-12-31
**Location**: C:\Projects\nimbus-mui\CLAUDE.md
