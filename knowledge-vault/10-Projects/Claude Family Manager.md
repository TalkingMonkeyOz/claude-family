---
created: 2025-12-20
updated: 2025-12-21
path: C:\Projects\claude-family-manager-v2
status: implementation
tech_stack:
- C# WinForms
- .NET 9
- PostgreSQL
title: Claude Family Manager v2
type: project
aliases:
- CFM v2
- claude-family-manager-v2
---

# Claude Family Manager v2

Desktop application for Claude Family management. WinForms C# replacement for abandoned Electron and MAUI Blazor approaches.

## History

| Version | Tech Stack | Status |
|---------|------------|--------|
| v1 | Electron + React | Archived |
| v1.5 | MAUI Blazor Hybrid | Abandoned |
| **v2** | **C# WinForms** | **Active** |

## Purpose

1. **Launcher**: Replace batch files with proper desktop app for launching Claude Code
2. **Dashboard**: Session management, agent monitoring, project overview
3. **Config View**: Visualize CLAUDE.md hierarchy and inheritance

## Tech Stack

- **C# WinForms**: Desktop UI (works with VS2026)
- **.NET 9**: Runtime
- **PostgreSQL**: Direct database access via Npgsql
- **No MCP dependency**: Direct DB queries for simplicity

## Folder

Location: `C:\Projects\claude-family-manager-v2`

## Links

- [[Claude Family]] - Parent infrastructure project
- [[WinForms Designer Rules]] - Designer safety rules

---

**Created**: 2025-12-20
**Updated**: 2025-12-21
