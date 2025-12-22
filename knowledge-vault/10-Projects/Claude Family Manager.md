---
aliases:
- CFM v2
- claude-family-manager-v2
created: 2025-12-20
path: C:\Projects\claude-family-manager-v2
status: implementation
synced: true
synced_at: '2025-12-21T23:23:15.080749'
tech_stack:
- C# WinForms (current)
- WPF + WPF UI (planned)
- .NET 10
- PostgreSQL
title: Claude Family Manager v2
type: project
updated: 2025-12-22
---

# Claude Family Manager v2

Desktop application for Claude Family management. WinForms C# implementation, with planned migration to WPF + WPF UI.

## History

| Version | Tech Stack | Status |
|---------|------------|--------|
| v1 | Electron + React | Archived |
| v1.5 | MAUI Blazor Hybrid | Abandoned |
| v2.0 | C# WinForms | **Current** |
| v2.5 | WPF + WPF UI | **Planned** |

## Purpose

1. **Launcher**: Replace batch files with proper desktop app for launching Claude Code
2. **Dashboard**: Session management, agent monitoring, project overview
3. **Config View**: Visualize CLAUDE.md hierarchy and inheritance

## Current Tech Stack (v2.0)

- **C# WinForms**: Desktop UI with manual dark theme
- **.NET 10**: Runtime
- **PostgreSQL**: Direct database access via Npgsql
- **No MCP dependency**: Direct DB queries for simplicity

## Planned Migration (v2.5)

### Why WPF UI?

[WPF UI](https://github.com/lepoco/wpfui) by Leszek Pomianowski:
- Fluent Design (Windows 11 native look)
- Built-in dark/light theme switching
- Used in Microsoft PowerToys
- Being integrated into official .NET WPF (semi-official Microsoft)
- Modern controls: NavigationView, Snackbar, Cards

### Migration Benefits

| Current (WinForms) | Future (WPF UI) |
|--------------------|-----------------|
| Manual dark theme colors | Built-in theme manager |
| TabControl | NavigationView (sidebar) |
| MessageBox | Snackbar/Dialog |
| Custom styling | Fluent Design native |

### Tooling Created

Global instructions auto-apply when editing WPF files:
- `~/.claude/instructions/wpf-ui.instructions.md` → applies to `*.xaml`
- `~/.claude/instructions/mvvm.instructions.md` → applies to `*ViewModel.cs`

### Architecture Change

```
WinForms (current)     →  WPF + MVVM (planned)
├── MainForm.cs        →  ├── ViewModels/
├── Services/          →  │   └── MainViewModel.cs
└── Models/            →  ├── Views/
                       →  │   └── MainWindow.xaml
                       →  ├── Services/ (same)
                       →  └── Models/ (same)
```

## Folder

Location: `C:\Projects\claude-family-manager-v2`

## Links

- [[Claude Family]] - Parent infrastructure project
- [[WinForms Designer Rules]] - Designer safety rules
- [[WPF UI]] - Target framework for migration

---

**Created**: 2025-12-20
**Updated**: 2025-12-22