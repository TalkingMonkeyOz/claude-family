# Claude Family Manager v2

**Type**: Desktop Application
**Status**: Implementation (core features working)
**Stack**: .NET 9 WPF + WPF-UI 3.0
**Project ID**: `ba39352f-9068-495b-b5d8-8cb222b633c9`
**Identity**: `claude-manager-v2` (`ce4e2b53-52a6-4ba3-bc4e-48c59c086295`)

---

## Purpose

Port of `C:\Projects\claude-family-manager\` (Electron) to native .NET to eliminate:
- Memory leaks (150+ orphaned Node.js processes)
- High resource usage from Electron runtime
- Process cleanup issues

See `docs/PROBLEM_STATEMENT.md` for full context.

---

## Tech Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | .NET WPF | 9.0 |
| UI Library | WPF-UI | 3.0.5 |
| MVVM | CommunityToolkit.Mvvm | 8.4.0 |
| Database | Npgsql | 10.0.1 |
| Markdown | Markdig | 0.44.0 |

---

## Features to Port

From `C:\Projects\claude-family-manager\`:

1. **Sidebar** - Project list with favorites (star toggle)
2. **Project Info Card** - Name, type chip, description, path, active sessions
3. **Tabs** - Sessions, Messages, TODO, Config
4. **Sessions Tab** - Active/recent sessions from `claude.sessions`
5. **Messages Tab** - Pending messages from `claude.messages`
6. **TODO Tab** - Render `docs/TODO_NEXT_SESSION.md`
7. **Config Tab** - Tree view of CLAUDE.md hierarchy
8. **Launch Controls** - Model selector + Launch button
9. **Process Spawning** - Launch Claude Code via Windows Terminal

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
```

---

## Configuration (Database-Driven)

**Project Type**: `csharp-winforms` (inherits defaults from `project_type_configs`)

**Config Flow**: Database → `generate_project_settings.py` → `.claude/settings.local.json` (generated)

**Self-Healing**: Settings regenerate from database on every SessionStart. Manual file edits are temporary.

**Details**: See `knowledge-vault/40-Procedures/Config Management SOP.md` in claude-family project

---

## Standard Operating Procedures

For common operations, **FIRST read the vault SOP, THEN execute**:

| Operation | Vault SOP Location | Command |
|-----------|-------------------|---------|
| New project | `claude-family/knowledge-vault/40-Procedures/New Project SOP.md` | `/project-init` |
| Add MCP server | `claude-family/knowledge-vault/40-Procedures/Add MCP Server SOP.md` | SQL + config |
| Update configs | `claude-family/knowledge-vault/40-Procedures/Config Management SOP.md` | DB update |

**Workflow**: Check CLAUDE.md → Read vault SOP → Execute → Done correctly

---

## MCP Servers Available

| Server | Purpose |
|--------|---------|
| postgres | Database queries |
| orchestrator | Spawn agents for subtasks |
| memory | Persist context |

Note: Roslyn MCP removed (incompatible with VS 2026).

---

## WinForms Development

This project includes WinForms components. Follow these rules:

### Critical Rules

1. **NEVER** directly edit \ files unless explicitly asked
2. Designer code follows **serialization rules** - no lambdas, no control flow
3. Regular code can use **modern C# features**
4. Prefer **layout controls** over absolute positioning

### Layout Priority

1. TableLayoutPanel - for grid/form layouts
2. FlowLayoutPanel - for button bars, dynamic lists
3. SplitContainer - for resizable panels
4. Panel + Dock/Anchor - for simple layouts

### Naming Conventions

| Control | Prefix | Example |
|---------|--------|---------|
| Button | btn | btnSave |
| TextBox | txt | txtName |
| Label | lbl | lblTitle |
| ComboBox | cbo | cboCountry |
| DataGridView | dgv | dgvOrders |

**Skill**: **Agent**: Use \ for complex WinForms tasks

---

## NuGet Packages (Installed)

```xml
<PackageReference Include="WPF-UI" Version="3.0.5" />
<PackageReference Include="CommunityToolkit.Mvvm" Version="8.4.0" />
<PackageReference Include="Microsoft.Extensions.DependencyInjection" Version="9.0.0" />
<PackageReference Include="Npgsql" Version="10.0.1" />
<PackageReference Include="Markdig" Version="0.44.0" />
<PackageReference Include="YamlDotNet" Version="16.3.0" />
```

---

## Documentation

| Doc | Purpose |
|-----|---------|
| `README.md` | Project overview, getting started, features |
| `ARCHITECTURE.md` | System design, component architecture, patterns |
| `docs/PROBLEM_STATEMENT.md` | Why this project exists |
| `docs/COMPONENT_MAPPING.md` | React → Blazor translation guide |
| `docs/TODO_NEXT_SESSION.md` | Current progress and next steps |

---

## Source Reference (Electron)

| File | Purpose |
|------|---------|
| `C:\Projects\claude-family-manager\src\views\Launcher.tsx` | Main UI (600 lines) |
| `C:\Projects\claude-family-manager\src\components\ConfigPanel.tsx` | Config tree (283 lines) |
| `C:\Projects\claude-family-manager\src\components\MarkdownViewer.tsx` | MD renderer |
| `C:\Projects\claude-family-manager\electron\db.ts` | Database queries |
| `C:\Projects\claude-family-manager\PROBLEM_STATEMENT.md` | Original problem |
| `C:\Projects\claude-family-manager\docs\IMPLEMENTATION_PLAN.md` | Original plan |

---

## Getting Started

```bash
# Run the WPF app
cd ClaudeLauncherWpf && dotnet run

# Or with hot reload
cd ClaudeLauncherWpf && dotnet watch
```

---

**Version**: 2.1 (Database-driven config, SOP router)
**Created**: 2025-12-20
**Updated**: 2025-12-27
