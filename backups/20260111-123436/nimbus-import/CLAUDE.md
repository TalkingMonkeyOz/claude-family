# Nimbus Import Application

**Type**: Work (Private)
**Status**: Active
**Phase**: Implementation
**Project ID**: `9b563af2-4762-4878-b5bf-429dac0cc481`

---

## Problem Statement

Standalone Tauri application to import staff scheduling data (shifts and task attendance) from Excel into Nimbus workforce management system. Features pre-flight validation, entity auto-creation, and hybrid API/database import approach.

**Full details**: See `PROBLEM_STATEMENT.md`

---

## Current Phase

**Phase**: Implementation
**Focus**: Build features (Priority 1 first, then Priority 2)
**Tech**: Tauri 2.0, React 19, Material UI v7, Rust

### Features (9 total)

**Priority 1 - Core Infrastructure:**
- Connection Management (system)
- Excel Data Loading (feature)
- Cache Building System (system)
- Validation Engine (feature)
- State Management & Persistence (system)
- Rust Backend Commands (system)

**Priority 2 - Import Execution:**
- Entity Preparation (feature)
- Shift Import via API (feature)
- Task Attendance Import via SQL (feature)

---

## Architecture Overview

- **Frontend**: React + Material UI wizard (5 steps)
- **Desktop**: Tauri for cross-platform deployment
- **Backend**: Rust for performance (Excel parsing, SQL)
- **Auth**: Dual-path (Nimbus API + Azure Entra MFA)
- **Cache**: IndexedDB for lookup data

**Full details**: See `ARCHITECTURE.md`

---

## Project Structure

```
nimbus-import/
├── CLAUDE.md              # This file
├── PROBLEM_STATEMENT.md   # Problem definition
├── ARCHITECTURE.md        # System design
├── README.md              # Human-readable overview
├── package.json           # Node dependencies
├── vite.config.ts         # Vite configuration
├── src/                   # React frontend
│   ├── components/
│   ├── stores/
│   └── services/
├── src-tauri/             # Rust backend
│   ├── Cargo.toml
│   └── src/
└── docs/
    └── PID.md             # Full Project Initiation Document
```

---

## Configuration (Database-Driven)

**Project Type**: `tauri-react` (inherits defaults from `project_type_configs`)

**Config Flow**: Database → `generate_project_settings.py` → `.claude/settings.local.json` (generated)

**Self-Healing**: Settings regenerate from database on every SessionStart. Manual file edits are temporary.

**Details**: See `../claude-family/knowledge-vault/40-Procedures/Config Management SOP.md`

---

## Standard Operating Procedures

For common operations, **FIRST read the vault SOP, THEN execute**:

| Operation | Vault SOP Location | Command |
|-----------|-------------------|---------|
| New project | `../claude-family/knowledge-vault/40-Procedures/New Project SOP.md` | `/project-init` |
| Add MCP server | `../claude-family/knowledge-vault/40-Procedures/Add MCP Server SOP.md` | SQL + config |
| Update configs | `../claude-family/knowledge-vault/40-Procedures/Config Management SOP.md` | DB update |

**Workflow**: Check CLAUDE.md → Read vault SOP → Execute → Done correctly

---

## MCP Servers

**MUI MCP** (`@mui/mcp`) is installed and provides:
- Up-to-date MUI documentation directly in prompts
- Accurate, version-specific component information
- Tools: `useMuiDocs`, `fetchDocs`

**Usage**: The MCP auto-loads when Claude works in this project.

---

## Coding Standards

- **TypeScript**: Strict mode, explicit types
- **React**: Functional components, hooks only
- **Rust**: Clippy clean, proper error handling
- **MUI**: Use sx prop for styling, theme.spacing() for margins, alpha() for transparency

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

## Session Protocol

**BEFORE starting work:** `/session-start`
**BEFORE ending session:** `/session-end`

---

## Key References

| Document | Purpose |
|----------|---------|
| docs/PID.md | Full project initiation document with all specs |
| nimbus-user-loader/ | Reference for OData patterns, validation |
| Syllabus Plus Plugin | Schedule/location creation patterns |
| UI_COMPONENT_STANDARDS.md | MUI component guidelines |

---

## API Endpoints (Reference)

### OData Queries (Cache Building)
- `/odata/User?$filter=Active eq 1 and Deleted eq 0&$select=UserID,Payroll,Forename,Surname`
- `/odata/Location?$filter=Active eq 1 and Deleted eq 0&$select=LocationID,Description`
- `/odata/Department?$filter=Active eq 1 and Deleted eq 0&$select=DepartmentID,Description,LocationID`
- `/odata/Schedule?$filter=Active eq 1 and Deleted eq 0&$select=ScheduleID,LocationID,ScheduleStart,ScheduleFinish`

### REST API (Entity Creation & Import)
- `POST /RESTapi/CostCentre`
- `POST /RESTapi/Location`
- `POST /RESTapi/Department`
- `POST /RESTapi/ScheduleGroup`
- `POST /RESTapi/UserLocation`
- `POST /RESTapi/ScheduleShift`
- `POST /RESTapi/Task`

### Direct SQL (Task Attendance)
- `INSERT INTO ScheduleShiftAttendance`
- `INSERT INTO ScheduleShiftAttendanceUserTime`
- `INSERT INTO ScheduleShiftAttendanceActivity`

---

## Related Projects

| Project | Relationship |
|---------|--------------|
| nimbus-user-loader | C# app for user imports - complementary |
| ATO-Tax-Agent | Same tech stack (Tauri + React + MUI) |
| mission-control-web | React + MUI patterns reference |

---

**Version**: 1.2 (Database-driven config, SOP router)
**Created**: 2025-12-12
**Updated**: 2025-12-27
**Location**: C:\Projects\nimbus-import\CLAUDE.md
