# {{PROJECT_NAME}} - C# Desktop Application

**Type**: C# Desktop
**Created**: {{CREATED_DATE}}

---

## Project Overview

C# desktop application (WinForms / WPF / MAUI).

---

## Project Structure

```
{{PROJECT_NAME}}/
├── src/
│   └── {{PROJECT_NAME}}/
│       ├── {{PROJECT_NAME}}.csproj
│       ├── Program.cs
│       ├── MainForm.cs (or MainWindow.xaml)
│       └── ...
├── tests/
│   └── {{PROJECT_NAME}}.Tests/
├── {{PROJECT_NAME}}.sln
├── CLAUDE.md           # This file
└── README.md           # Project overview
```

---

## Build Commands

```bash
# Restore packages
dotnet restore

# Build
dotnet build

# Run
dotnet run --project src/{{PROJECT_NAME}}

# Run tests
dotnet test
```

---

## Key Technologies

- .NET 8+
- Framework: (WinForms / WPF / MAUI)
- Nullable reference types enabled

---

## Code Standards

- Enable nullable reference types
- Use file-scoped namespaces
- Use primary constructors where appropriate
- Follow C# naming conventions (PascalCase for public, _camelCase for private fields)

---

## When Working Here

- Check for null safety
- Follow MVVM pattern (if WPF/MAUI)
- Write unit tests
- Handle exceptions appropriately

---

## Recent Work

```sql
SELECT summary, outcome, session_start
FROM claude.sessions
WHERE project_name = '{{PROJECT_NAME}}'
ORDER BY session_start DESC LIMIT 5;
```

---

**Version**: 1.0
**Location**: {{PROJECT_PATH}}/CLAUDE.md
