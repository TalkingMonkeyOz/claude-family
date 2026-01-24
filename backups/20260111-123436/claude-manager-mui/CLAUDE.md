# Claude Manager MUI

**Type**: Desktop Application
**Status**: Planning
**Stack**: Tauri + React + MUI X
**Project ID**: `a796c1e8-ff53-4595-99b1-82e2ad438c9e`
**Identity**: `claude-manager-mui` (`602627d4-2530-46d8-9af9-a62e5bc4da45`)

---

## Coding Standards (Auto-Loaded)

@~/.claude/standards/core/markdown-documentation.md
@~/.claude/standards/language/typescript.md
@~/.claude/standards/language/rust.md
@~/.claude/standards/framework/react.md
@~/.claude/standards/framework/mui.md

---

## Purpose

Modern desktop application for managing Claude Code sessions, projects, and configuration using Material-UI.

**Replaces**: `claude-family-manager-v2` (WPF) and original Electron version

**Why MUI X?**: Best-in-class React component library with beautiful design, excellent TypeScript support, and comprehensive data grid/charts.

See `docs/PROBLEM_STATEMENT.md` for full context.

---

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Tauri | 2.x |
| Frontend | React + TypeScript | 19.x |
| UI Library | Material-UI (MUI) | 7.x |
| Data Grid | MUI X Data Grid | 8.x |
| Charts | MUI X Charts | 8.x |
| State | Zustand | 5.x |
| Server State | TanStack Query | 5.x |
| Routing | React Router | 7.x |
| Database | PostgreSQL (via Tauri) | - |

---

## Features to Implement

From `claude-family-manager-v2`:

### Phase 1: MVP
1. **Sidebar** - Project list with favorites (star toggle)
2. **Project Info Card** - Name, type chip, description, path
3. **Launch Controls** - Model selector + Launch button
4. **Database Integration** - Connect to PostgreSQL via Tauri backend

### Phase 2: Core Features
5. **Sessions Tab** - Active/recent sessions from `claude.sessions`
6. **Messages Tab** - Pending messages from `claude.messages`
7. **TODO Tab** - Render `docs/TODO_NEXT_SESSION.md`
8. **Process Spawning** - Launch Claude Code via Windows Terminal

### Phase 3: Advanced
9. **Config Tab** - Tree view of CLAUDE.md hierarchy
10. **Health Checks** - Database + MCP server status
11. **Agent Monitoring** - Spawned agents and their status
12. **Real-time Updates** - Live session state changes

---

## Database Queries

All data comes from PostgreSQL `ai_company_foundation`, schema `claude`:

```sql
-- Projects
SELECT * FROM claude.projects ORDER BY project_name;

-- Active sessions
SELECT * FROM claude.sessions
WHERE project_name = ? AND session_end IS NULL;

-- Pending messages
SELECT * FROM claude.messages
WHERE to_project = ? AND status = 'pending';

-- Persistent todos
SELECT * FROM claude.todos
WHERE project_id = ? AND is_deleted = false
  AND status IN ('pending', 'in_progress');
```

---

## Configuration (Database-Driven)

**Project Type**: `tauri-react` (inherits defaults from `project_type_configs`)

**Config Flow**: Database → `generate_project_settings.py` → `.claude/settings.local.json` (generated)

**Self-Healing**: Settings regenerate from database on every SessionStart.

**Details**: See `C:\Projects\claude-family\knowledge-vault\40-Procedures\Config Management SOP.md`

---

## MUI Theme

Using custom theme from `finance-mui` with:
- WCAG AA compliant colors
- Light/dark mode support
- Enhanced focus indicators for accessibility
- Consistent spacing and typography

**Theme file**: `src/theme/theme.ts`

---

## Project Structure

```
claude-manager-mui/
├── src/
│   ├── features/          # Feature modules
│   │   ├── projects/      # Project list, selection
│   │   ├── sessions/      # Session monitoring
│   │   ├── messages/      # Message inbox
│   │   ├── todos/         # TODO viewer
│   │   └── launcher/      # Launch controls
│   ├── components/        # Shared components
│   │   ├── ProjectCard.tsx
│   │   ├── SessionList.tsx
│   │   └── MessageList.tsx
│   ├── services/          # Backend integration
│   │   ├── database.ts    # Tauri commands
│   │   ├── launcher.ts    # Process spawning
│   │   └── api.ts         # API client
│   ├── store/             # Zustand stores
│   │   ├── projectStore.ts
│   │   └── themeStore.ts
│   ├── hooks/             # Custom React hooks
│   │   ├── useProjects.ts
│   │   └── useSessions.ts
│   ├── theme/             # MUI theme
│   │   └── theme.ts
│   ├── types/             # TypeScript types
│   │   ├── project.ts
│   │   └── session.ts
│   └── App.tsx            # Main app component
├── src-tauri/             # Rust backend
│   ├── src/
│   │   ├── main.rs        # Entry point
│   │   ├── commands.rs    # Tauri commands
│   │   └── database.rs    # PostgreSQL integration
│   └── Cargo.toml
├── .claude/               # Claude Code config
│   ├── commands/          # Slash commands
│   └── skills/            # Project skills
└── docs/                  # Documentation
    ├── PROBLEM_STATEMENT.md
    ├── ARCHITECTURE.md
    └── TODO_NEXT_SESSION.md
```

---

## Getting Started

```bash
# Install dependencies
cd C:\Projects\claude-manager-mui
npm install

# Run development server
npm run tauri dev

# Build for production
npm run tauri build
```

---

## MCP Servers Available

| Server | Purpose |
|--------|---------|
| postgres | Database queries |
| orchestrator | Spawn agents for subtasks |
| memory | Persist context |

---

## Standard Operating Procedures

For common operations, **FIRST read the vault SOP, THEN execute**:

| Operation | Vault SOP Location |
|-----------|-------------------|
| New project | `claude-family/knowledge-vault/40-Procedures/New Project SOP.md` |
| Add MCP server | `claude-family/knowledge-vault/40-Procedures/Add MCP Server SOP.md` |
| Update configs | `claude-family/knowledge-vault/40-Procedures/Config Management SOP.md` |

**Workflow**: Check CLAUDE.md → Read vault SOP → Execute → Done correctly

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `README.md` | Project overview, features, getting started |
| `ARCHITECTURE.md` | System design, component architecture |
| `docs/PROBLEM_STATEMENT.md` | Why this project exists |
| `docs/MIGRATION_FROM_V2.md` | WPF → React/MUI translation guide |
| `docs/TODO_NEXT_SESSION.md` | Current progress and next steps |

---

## Source Reference

### From claude-family-manager-v2 (WPF)
- Feature requirements and database queries
- Launch workflow and process management
- Health check logic

### From finance-mui (MUI theme and patterns)
- Theme configuration (`src/theme/theme.ts`)
- Component structure and best practices
- Tauri integration patterns
- Testing setup

---

**Version**: 1.0 (Initial creation)
**Created**: 2025-12-29
**Updated**: 2025-12-29
