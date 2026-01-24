# finance-mui

**Type**: Web Application (Desktop via Tauri)
**Tech Stack**: React + TypeScript + MUI + Tauri (Rust)
**Purpose**: Personal Finance Management System - React+MUI implementation

---

## Problem Statement

Build a comprehensive, AI-powered personal finance system that provides complete visibility and control over all financial accounts, with specialized SMSF compliance and retirement planning capabilities.

This project compares **React + MUI** approach against WPF and HTMX+Alpine implementations.

**Full details**: See `PROBLEM_STATEMENT.md` and `C:\Projects\claude-family\knowledge-vault\John's Notes\Personal Finance Orig\prd-personal-finance-system.md`

---

## Current Phase

**Phase**: Planning & Setup
**Focus**: Project initialization and architecture setup

---

## Tech Stack

- **Frontend**: React 18 + TypeScript + Material-UI (MUI) v6 + MUI-X
- **Backend**: Tauri (Rust) with embedded commands
- **Database**: SQLite (embedded) or PostgreSQL (local)
- **Desktop**: Tauri v2 (native desktop app)
- **Build**: Vite + SWC (fast builds)
- **State**: React Query + Zustand (or Context API)

---

## Architecture

**Tauri SPA Architecture:**
```
User Interface (React + MUI Components)
    ↓
React Query (Data fetching & caching)
    ↓
Tauri Commands (Rust API)
    ↓
Business Logic (Rust)
    ↓
Database (SQLite/PostgreSQL)
```

**Key Benefits:**
- No separate server process
- Native desktop experience
- Rich, interactive UI (MUI components)
- Type-safe (TypeScript + Rust)
- Small bundle size (~10-15MB)

---

## Build Commands

```bash
# Install dependencies
npm install

# Development (hot reload)
npm run tauri dev

# Build for production
npm run tauri build

# Add MUI dependencies
npm install @mui/material @emotion/react @emotion/styled
npm install @mui/x-data-grid @mui/x-date-pickers
npm install @mui/icons-material
```

---

## Project Structure

```
finance-mui/
├── src/                    # React frontend
│   ├── features/          # Feature-based organization
│   │   ├── accounts/
│   │   ├── transactions/
│   │   ├── smsf/
│   │   └── reports/
│   ├── components/        # Shared UI components
│   ├── hooks/            # Custom React hooks
│   ├── services/         # Tauri command wrappers
│   ├── store/            # State management
│   ├── App.tsx
│   └── main.tsx
├── src-tauri/             # Rust backend
│   ├── src/
│   │   ├── main.rs       # Tauri app entry
│   │   ├── commands.rs   # API commands
│   │   ├── db.rs         # Database logic
│   │   └── finance/      # Business logic
│   ├── Cargo.toml
│   └── tauri.conf.json
├── CLAUDE.md
├── PROBLEM_STATEMENT.md
├── package.json
└── tsconfig.json
```

---

## Key Features (from PRD)

### Phase 1: Foundation
- Account aggregation
- Transaction tracking
- CSV import
- Basic categorization

### Phase 2: AI Categorization
- Claude Haiku/Sonnet integration
- Pattern learning
- Anomaly detection

### Phase 3: SMSF Management
- Portfolio tracking
- Compliance monitoring
- Document management
- Retirement projections

---

## MUI Component Strategy

**Key MUI Components to use:**
- **DataGrid** (MUI-X): Transaction tables, SMSF holdings
- **DatePicker** (MUI-X): Date range filters
- **Charts** (MUI-X): Net worth trends, spending visualization
- **Drawer**: Navigation sidebar
- **Card**: Dashboard widgets
- **Dialog**: Transaction details, confirmations
- **Autocomplete**: Category selection
- **Tabs**: Organize complex views

**Theme:**
- Use MUI theming for consistent design
- Support light/dark mode
- Customize primary color to finance-appropriate (blue/green)

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

## Comparison Notes

**This project compares 3 tech stacks for the same application:**
1. **WPF** (C# desktop) - Existing
2. **HTMX + Alpine.js** (finance-htmx) - Server-driven, minimal JS
3. **React + MUI** (This project) - SPA, rich UI

**React + MUI Benefits:**
- Rich, interactive UI (data grids, charts, forms)
- Large ecosystem of components
- Modern development experience
- Type-safe with TypeScript

**React + MUI Trade-offs:**
- More JavaScript complexity
- Larger bundle size than HTMX
- State management overhead
- Requires Node.js for building

---

## Avoiding Node.js Runtime Issues

**Important**: React requires Node.js for **building** but NOT at runtime:
- **Build time**: Vite uses Node.js to bundle the app
- **Run time**: Tauri runs the app (no Node.js process)

**This solves your concerns:**
- ✅ No Node.js backend (Tauri/Rust handles that)
- ✅ No separate server process
- ✅ Desktop app, not browser
- ⚠️ Still need Node.js installed for development

---

## Next Steps

1. ✅ Project created
2. ⏳ Install MUI dependencies
3. ⏳ Set up database schema
4. ⏳ Create feature structure
5. ⏳ Implement Tauri commands
6. ⏳ Build Phase 1 features

---

**Version**: 1.0
**Created**: 2025-12-28
**Location**: C:\Projects\finance-mui\CLAUDE.md
