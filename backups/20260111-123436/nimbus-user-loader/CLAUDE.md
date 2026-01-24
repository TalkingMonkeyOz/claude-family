# Nimbus User Loader

**Type**: Work (Private)
**Status**: Implementation
**Phase**: Maintenance (Core 100%, Plugins 70%)
**Project ID**: `2b17ba9f-fc92-470e-8d00-6fb179d78ec1`

---

## Problem Statement

Windows Forms application for batch importing user data and timetables to Nimbus workforce management system. Plugin architecture enables institution-specific features.

**Full details**: See `PROBLEM_STATEMENT.md`

---

## Current Phase

**Phase**: Maintenance
**Focus**: Core features complete, Monash plugin 70%
**Tech**: C# .NET 8, Windows Forms, Plugin Architecture

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

## MANDATORY C# WORKFLOW

**ALL C# code must be validated with Roslyn MCP before presenting to user.**

**WORKFLOW (NON-NEGOTIABLE):**
1. **Research** - Use Context7 for unfamiliar APIs: `use library /dotnet/winforms topic "threading"`
2. **Analyze** - Run `mcp__roslyn__ValidateFile` + `FindUsages` BEFORE editing to understand structure
3. **Implement** - Make code changes based on Roslyn analysis
4. **Validate** - Run `mcp__roslyn__ValidateFile` again, verify no new errors introduced
5. **Log** - Output validation results: "✅ ROSLYN: MainForm.cs (0 errors, 2 warnings CA1031, IDE0051)"
6. **Present** - Show code only after validation passes

**CRITICAL LESSON (2025-10-28):** 6hrs wasted on duplicate InitializeComponent() - Roslyn FindUsages would have caught it instantly. Analyze BEFORE editing, not after.

**CONTEXT7 LIBRARY IDs:** /dotnet/winforms, /dotnet/csharp, /npgsql/npgsql
**QUICK VALIDATION:** Type `/validate-csharp` to validate all modified files
**SECURITY:** NEVER use Context7 for Nimbus/ATO internals (safe: public frameworks only)

---

## Project Overview

Comprehensive Windows Forms application for managing Nimbus user data imports and timetable uploads.

**Tech Stack:**
- C# .NET 8
- Windows Forms (GUI)
- Plugin Architecture (IPluginModule, IPluginHost)
- PostgreSQL integration (context storage)
- UserSDK library (Nimbus API integration)
- Newman (Postman CLI) for parallel uploads

---

## Database Schema

**Active Schema**: `nimbus_context`

**Key Tables:**
- User data tables (load on demand)
- Import history tracking
- Validation rules

**Rule**: Query specific tables only - don't load entire schema upfront.

---

## Data Gateway

**MANDATORY**: Before writing to constrained columns, check valid values:

```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

---

## Application Structure

**Main Projects:**
- `nimbus-user-loader` - Core library (CLI + business logic + plugin infrastructure)
- `nimbus-user-gui` - Windows Forms GUI (implements IPluginHost)
- `nimbus-user-loader.Plugins.Monash` - Monash-specific features (optional plugin)

**Plugin Architecture:**
- Plugins discovered from `bin/.../plugins/` folder at startup
- Each plugin provides TabPage controls added to main TabControl
- Host provides services via IPluginHost (logging, connection manager, UI helpers)
- Clean separation between core and institution-specific features

## Current Features

**Core Features (100%):**
- ✅ User Import (UserSDK) - Batch and single mode with session affinity
- ✅ Import Control - Granular section control (Employments, Hours, Job Roles, etc.)
- ✅ Core Config Upload - Departments, Locations, Teams, Skills
- ✅ Profile Management - Save/load connection and import settings
- ✅ Authentication - Basic, RESTApi, OAuth2 Password modes
- ✅ Reporting - report.csv, failures.csv, summary.txt

**Monash Plugin Features:**
- ✅ Syllabus Plus Upload (100%) - Newman parallel processing, 200k records in ~4.5 hours
- 🔄 Pre-Upload Setup (70%) - JSON analysis, Location Group creation, SG config export

## Build Commands

```bash
# Build entire solution (includes plugins)
cd C:\Projects\nimbus-user-loader
dotnet build -c Release

# Clean and rebuild
dotnet clean
dotnet build -c Release

# Run GUI application
.\src\nimbus-user-gui\bin\Release\net8.0-windows\win-x64\nimbus-user-gui.exe
```

---

## Code Conventions

**C# Style:**
- PascalCase for public members
- camelCase for private fields with `_` prefix
- Descriptive names (e.g., `GetFlexibleVal` not `GetVal`)
- XML comments for public APIs

**Windows Forms:**
- Designer-generated code in `.Designer.cs` files
- Manual layout calculations for complex UIs
- Event handlers named `Control_Event` pattern

---

## Critical Rules (Nimbus-Specific)

### Data Handling
1. **NEVER modify UserSDK** payload generation logic without thorough testing
2. **Use GetFlexibleVal()** instead of GetVal() for data extraction
3. **Normalize dates** to ISO 8601 format
4. **Validate empty records** for all entities
5. **Test with real data** before committing changes

### Performance & Architecture
6. **Session Affinity is CRITICAL**: Always use ONE HttpClient with CookieContainer per session
   - ✅ CORRECT: Create handler once, reuse for all requests
   - ❌ WRONG: Create new handler per request
7. **Batch Mode**: Use `--batch-mode` for large imports (50-100 users per request)
8. **Import Control**: All sections default to OFF for safety
9. **Plugin DLLs**: Auto-copied to `plugins/` folder on build

### Nimbus API Quirks
10. **Authentication**: Use `/RESTApi/Authenticate` (not `/RESTApi/Authentication`)
11. **Create vs Update**: POST with ID = update, POST without ID = create (non-standard REST)
12. **Avoid GET on large collections**: LocationGroup and Location endpoints timeout
13. **TenantID**: Never include in payloads - automatically set from authenticated user

---

## Key Files (Quick Reference)

**Plugin Infrastructure:**
```
src/nimbus-user-loader/Plugins/
├── IPluginModule.cs      # Plugin interface
├── IPluginHost.cs        # Services host provides to plugins
└── PluginManager.cs      # Plugin discovery and loading
```

**Main Application:**
```
src/nimbus-user-gui/
├── MainForm.cs                        # Main form (implements IPluginHost, loads plugins)
├── MainForm.Designer.cs               # UI layout
├── MainForm.ImportControlEvents.cs    # Import Control tab logic
└── Program.cs                         # GUI entry point
```

**Core Logic:**
```
src/nimbus-user-loader/
├── Program.cs                         # CLI entry point, UserSDK batch processing
├── Models/                            # Data models
├── Services/
│   ├── NimbusConnectionManager.cs     # Global auth/connection management
│   └── ...
```

**Monash Plugin:**
```
src/nimbus-user-loader.Plugins.Monash/
├── MonashPlugin.cs                    # Plugin entry point (returns 2 tabs)
├── Services/
│   ├── PreUploadSetupAnalyzer.cs      # JSON analysis, Location Group planning
│   ├── NimbusLocationGroupManager.cs  # Location Group API calls
│   ├── SyllabusPlusSplitter.cs        # Split JSON into chunks
│   └── NewmanProcessManager.cs        # Parallel Newman process orchestration
├── PreUploadSetup/
│   └── PreUploadSetupTabControl.cs    # Pre-Upload Setup UI
└── SyllabusPlusUpload/
    └── SyllabusPlusUploadTabControl.cs # Syllabus Plus Upload UI
```

**Documentation:**
```
README.md                              # User documentation (updated with plugin architecture)
CLAUDE.md                              # This file - Claude context
IMPORT_CONTROL_IMPLEMENTATION.md       # Import Control feature spec
NIMBUS_API_PATTERNS.md                 # API patterns and quirks
docs/SyllabusPlusUpload_QuickStart.md  # Syllabus Plus user guide
```

---

**Version**: 3.0 | **Updated**: 2025-12-14
