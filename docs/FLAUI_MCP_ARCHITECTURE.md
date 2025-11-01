# FlaUI MCP Server Architecture

**Purpose:** Audit-friendly, version-pinned UI regression testing for nimbus-user-loader and claude-pm WinForms applications.

**Created:** 2025-11-01
**Owner:** Claude Family Infrastructure

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Claude Console                            │
│  (User writes tests in natural language via MCP)            │
└─────────────┬───────────────────────────────────────────────┘
              │ MCP Protocol (stdio)
              ▼
┌─────────────────────────────────────────────────────────────┐
│              FlaUI MCP Server (C# .NET 8)                    │
│                                                              │
│  MCP Tools:                                                  │
│  ├─ create_test    (Write test to database)                 │
│  ├─ run_test       (Execute test, store results)            │
│  ├─ list_tests     (Query available tests)                  │
│  ├─ get_results    (Retrieve test execution history)        │
│  └─ take_screenshot (Capture UI state)                      │
└─────────────┬────────────────────┬────────────────────────┬──┘
              │                    │                        │
              ▼                    ▼                        ▼
    ┌─────────────────┐   ┌──────────────┐    ┌────────────────┐
    │ PostgreSQL DB   │   │ FlaUI Engine │    │ File System    │
    │ (Test Storage)  │   │ (UIA2/UIA3)  │    │ (Screenshots)  │
    └─────────────────┘   └──────┬───────┘    └────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  WinForms Apps         │
                    │  - nimbus-user-loader  │
                    │  - claude-pm           │
                    └────────────────────────┘
```

---

## Components

### 1. FlaUI MCP Server (C# Project)

**Location:** `C:\Projects\flaui-mcp-server\`

**NuGet Dependencies:**
```xml
<ItemGroup>
  <PackageReference Include="ModelContextProtocol" Version="1.0.0-preview.*" />
  <PackageReference Include="Microsoft.Extensions.Hosting" Version="8.0.*" />
  <PackageReference Include="FlaUI.UIA3" Version="4.0.*" />
  <PackageReference Include="FlaUI.Core" Version="4.0.*" />
  <PackageReference Include="Npgsql" Version="8.0.*" />
</ItemGroup>
```

**MCP Tools Exposed:**

| Tool | Description | Inputs | Outputs |
|------|-------------|--------|---------|
| `create_test` | Store a new UI test | project_name, test_name, steps (JSON) | test_id |
| `run_test` | Execute a test by ID/name | test_id OR test_name | result_id, status, screenshot_path |
| `list_tests` | Query tests for a project | project_name, category (optional) | Array of tests |
| `get_results` | Retrieve execution history | test_id, limit | Array of results |
| `update_test` | Modify existing test | test_id, steps (JSON) | Updated test |
| `find_elements` | Debug: Find UI elements | automationId, controlType | Element details |
| `take_screenshot` | Capture current app state | window_title | screenshot_path |

### 2. Database Storage (PostgreSQL)

**Tables:**
- `claude_family.ui_test_scripts` - Test definitions (JSON steps)
- `claude_family.ui_test_results` - Execution history
- `claude_family.ui_test_screenshots` - Failure screenshots

**Test Script JSON Format:**
```json
{
  "test_name": "Login with valid credentials",
  "project_name": "nimbus-user-loader",
  "steps": [
    {"action": "launch_app", "exe_path": "C:\\Projects\\nimbus-user-loader\\bin\\Debug\\Nimbus.exe"},
    {"action": "find_element", "automationId": "txtUsername", "timeout": 5000},
    {"action": "type_text", "automationId": "txtUsername", "text": "admin"},
    {"action": "type_text", "automationId": "txtPassword", "text": "password"},
    {"action": "click", "automationId": "btnLogin"},
    {"action": "assert_element_exists", "automationId": "mainWindow", "timeout": 10000}
  ],
  "assertions": [
    {"type": "element_visible", "automationId": "mainWindow"},
    {"type": "no_errors", "description": "Login should succeed without errors"}
  ]
}
```

### 3. File System Storage

**Screenshot Path:** `C:\Projects\test-screenshots\{project}\{test_id}\{timestamp}.png`

**Organization:**
```
C:\Projects\test-screenshots\
├── nimbus-user-loader\
│   ├── login-test\
│   │   ├── 2025-11-01_14-30-00_failure.png
│   │   └── 2025-11-01_14-35-00_pass.png
│   └── data-load-test\
└── claude-pm\
    └── window-open-test\
```

---

## Integration with Claude Console

### Installation

**1. Add to nimbus-user-loader `.mcp.json`:**
```json
{
  "mcpServers": {
    "flaui-testing": {
      "type": "stdio",
      "command": "C:\\Projects\\flaui-mcp-server\\bin\\Release\\net8.0\\FlaUIMcpServer.exe",
      "args": [
        "--project", "nimbus-user-loader",
        "--db-connection", "postgresql://postgres:***@localhost/ai_company_foundation"
      ],
      "env": {}
    }
  }
}
```

**2. Add to claude-pm `.mcp.json`:** (Same pattern, different project name)

### Usage Example (Claude Console)

**User:** "Create a test for nimbus that clicks the Load Data button and verifies the grid populates"

**Claude:** Uses `create_test` tool:
```json
{
  "project_name": "nimbus-user-loader",
  "test_name": "verify_data_grid_populates",
  "steps": [
    {"action": "launch_app", "exe_path": "C:\\Projects\\nimbus-user-loader\\bin\\Debug\\Nimbus.exe"},
    {"action": "click", "automationId": "btnLoadData"},
    {"action": "wait", "ms": 2000},
    {"action": "assert_element_exists", "automationId": "dataGrid"},
    {"action": "assert_property", "automationId": "dataGrid", "property": "ItemCount", "operator": ">", "value": 0}
  ]
}
```

**User:** "Run that test"

**Claude:** Uses `run_test` tool → Returns result_id + status

**User:** "Show me the results"

**Claude:** Uses `get_results` tool → Displays execution history, screenshots if failed

---

## Audit & Version Pinning

### Version Control
- **MCP Server:** Committed to git at `C:\Projects\flaui-mcp-server`
- **NuGet Packages:** Exact versions in `.csproj` (no wildcards in production)
- **Test Scripts:** Versioned in database (`version` column)

### Audit Trail
Every test execution logs:
- Who ran it (`run_by_identity_id`)
- When (`run_at`)
- What environment (`app_version`, `os_version`)
- Full results (`steps_executed` JSON)

### Reproducibility
1. Check out specific commit of MCP server
2. Pin NuGet package versions
3. Run tests with exact app version
4. Results are deterministic

---

## Why This Beats Existing MCPs

| Requirement | FlaUI MCP ✅ | Windows-MCP.Net ❌ |
|------------|-------------|-------------------|
| **WinForms Testing** | ✅ UI Automation for controls | ⚠️ Generic automation |
| **Test Storage** | ✅ Database with history | ❌ No storage |
| **Audit Trail** | ✅ Full execution logs | ❌ No tracking |
| **Version Pinning** | ✅ You control the code | ⚠️ External dependency |
| **Regression Focus** | ✅ Designed for tests | ❌ General purpose |
| **.NET Integration** | ✅ Same stack as apps | ✅ But .NET 10 required |

---

## Next Steps

1. ✅ Create C# project structure
2. ✅ Implement MCP tools
3. ✅ Test with nimbus-user-loader
4. ✅ Document test writing guide
5. ✅ Create example tests for both projects

---

**Evaluation ID:** `d5c27c0e-d1af-46cd-8de1-16c3577f1fd6`
**Stored in:** `claude_family.tool_evaluations`
