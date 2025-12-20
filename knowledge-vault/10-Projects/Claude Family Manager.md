---
created: 2025-12-20
path: C:\Projects\claude-family-manager
project_id: 5c893d12-33c9-41a2-a805-f6d6c1d7f87e
status: planning
synced: true
synced_at: '2025-12-20T23:29:45.910403'
tech_stack:
- Electron
- React
- MUI Community
- PostgreSQL
- Vite
title: Claude Family Manager
type: project
---

# Claude Family Manager

Desktop application that replaces batch file startup and MCW dashboard.

## Purpose

1. **Launcher**: Replace batch files with proper desktop app for launching Claude Code
2. **Dashboard**: Migrate working MCW features (sessions, agents, projects, feedback)
3. **Config View**: Visualize CLAUDE.md hierarchy and inheritance

## Tech Stack

- **Electron**: Desktop shell
- **React 18**: UI framework
- **MUI Community**: Component library (free tier)
- **Direct pg**: PostgreSQL via IPC (no HTTP API)
- **Vite**: Fast builds

## Key Features

### Phase 1: Launcher MVP
- Project selector from workspaces.json
- Health checks (DB, MCP servers)
- Message preview (pending count)
- TODO preview from previous session
- Launch button with env var setup

### Phase 2: Config Tree View
- Visualize CLAUDE.md hierarchy
- Show global -> project -> plugin inheritance
- Highlight overrides

### Phase 3+: Dashboard Migration
- Migrate working MCW features
- Skip broken features (scheduler CRUD, reminders create, project tasks)

## Links

- [[Claude Family]] - Parent infrastructure project
- [[Mission Control Web]] - Being replaced by this
- Implementation Plan: `docs/IMPLEMENTATION_PLAN.md`

## Status

| Phase | Status |
|-------|--------|
| Scaffolding | In Progress |
| Launcher MVP | Pending |
| Config Tree | Pending |
| Dashboard | Pending |

---

**Created**: 2025-12-20
**Last Updated**: 2025-12-20