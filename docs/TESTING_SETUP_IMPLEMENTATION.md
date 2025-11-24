# Testing Setup Implementation Plan

**Date:** 2025-10-19
**Scope:** All Claude Family members + Tax Wizard + Nimbus projects

---

## Project Inventory

### Python Projects
1. **Tax Wizard Tools** (`C:/Projects/ai-workspace/tax-wizard-tools/`)
   - Python 3.13.7
   - 4 tools: wizard_template_generator, formula_validator, wizard_flow_visualizer, ato_change_detector
   - **Needs:** pytest, Playwright, Hypothesis, python-testing-mcp

### .NET Projects
2. **Nimbus User Loader** (`C:/Projects/nimbus-user-loader/`)
   - .NET 8.0 (net8.0 + net8.0-windows)
   - Windows Forms GUI + Console
   - **Needs:** xUnit, FlaUI (UI automation), FluentAssertions

---

## Implementation Plan

### Step 1: Create Testing Venv
**New venv:** `C:/venvs/testing` (shared by all Python test tools)

```bash
python -m venv C:/venvs/testing
C:/venvs/testing/Scripts/activate

# Install core testing tools
pip install pytest pytest-cov pytest-xdist pytest-asyncio
pip install playwright
playwright install
pip install hypothesis
pip install python-testing-mcp

# Install project-specific dependencies
pip install -r C:/Projects/ai-workspace/tax-wizard-tools/requirements.txt
```

### Step 2: Set Up Tax Wizard Testing

**Structure:**
```
C:/Projects/ai-workspace/tax-wizard-tools/
├── tests/
│   ├── __init__.py
│   ├── unit/                    # Fast unit tests
│   │   ├── test_wizard_generator.py
│   │   ├── test_formula_validator.py
│   │   ├── test_flow_visualizer.py
│   │   └── test_change_detector.py
│   ├── integration/              # Database + API tests
│   │   ├── test_wizard_db_integration.py
│   │   └── test_openai_integration.py
│   ├── e2e/                     # Playwright web tests (future)
│   │   └── test_wizard_ui.py
│   └── properties/              # Hypothesis property-based tests
│       ├── test_formula_properties.py
│       └── test_wizard_logic_properties.py
├── conftest.py                  # Pytest fixtures
├── pytest.ini                   # Pytest configuration
└── .coveragerc                  # Coverage configuration
```

**Files to create:**
1. `pytest.ini`
2. `conftest.py`
3. `.coveragerc`
4. Example test files

### Step 3: Set Up Nimbus .NET Testing

**Create test project:**
```bash
cd C:/Projects/nimbus-user-loader
dotnet new xunit -n nimbus-user-loader.Tests -f net8.0
cd nimbus-user-loader.Tests

# Add references
dotnet add reference ../src/nimbus-user-loader/nimbus-user-loader.csproj

# Add testing packages
dotnet add package FluentAssertions --version 7.0.0
dotnet add package Moq --version 4.20.72
dotnet add package FlaUI.UIA3 --version 4.0.0
dotnet add package Microsoft.NET.Test.Sdk --version 17.11.1

# Add to solution
cd ..
dotnet sln add nimbus-user-loader.Tests/nimbus-user-loader.Tests.csproj
```

**Structure:**
```
C:/Projects/nimbus-user-loader/
├── src/
│   ├── nimbus-user-gui/
│   └── nimbus-user-loader/
├── tests/
│   └── nimbus-user-loader.Tests/
│       ├── UnitTests/           # Fast unit tests
│       │   ├── UserLoaderTests.cs
│       │   └── ValidationTests.cs
│       ├── IntegrationTests/    # API + Database tests
│       │   └── NimbusApiTests.cs
│       └── UITests/             # FlaUI desktop tests
│           └── MainFormTests.cs
└── nimbus-user-loader.sln
```

### Step 4: Install python-testing-mcp for All Family

**Update `.mcp.json` for:**
- `C:/claude/claude-console-01/.mcp.json` (me)
- `C:/claude/claude-desktop-01/.mcp.json` (claude-desktop)
- `C:/claude/diana/.mcp.json` (diana)

**Add to each:**
```json
{
  "mcpServers": {
    "python-testing-mcp": {
      "command": "C:\\venvs\\testing\\Scripts\\python.exe",
      "args": ["-m", "python_testing_mcp"],
      "env": {}
    }
  }
}
```

---

## Recommended Testing Stack

### Python (Tax Wizard)
| Tool | Purpose | Installation |
|------|---------|--------------|
| **pytest** | Test framework | `pip install pytest` |
| **pytest-cov** | Coverage reports | `pip install pytest-cov` |
| **pytest-xdist** | Parallel execution | `pip install pytest-xdist` |
| **Playwright** | Web UI testing | `pip install playwright && playwright install` |
| **Hypothesis** | Property-based testing | `pip install hypothesis` |
| **python-testing-mcp** | MCP integration | `pip install python-testing-mcp` |

### .NET (Nimbus)
| Tool | Purpose | Installation |
|------|---------|--------------|
| **xUnit** | Test framework | `dotnet add package xunit` |
| **FluentAssertions** | Readable assertions | `dotnet add package FluentAssertions` |
| **Moq** | Mocking framework | `dotnet add package Moq` |
| **FlaUI** | UI automation | `dotnet add package FlaUI.UIA3` |
| **Coverlet** | Code coverage | `dotnet add package coverlet.collector` |

---

## Configuration Files

### pytest.ini (Tax Wizard)
```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Async support
asyncio_mode = auto

# Output
addopts =
    -v
    --strict-markers
    --tb=short
    --cov=.
    --cov-report=html
    --cov-report=term-missing

# Markers
markers =
    unit: Fast unit tests
    integration: Integration tests requiring database/API
    e2e: End-to-end tests with Playwright
    slow: Tests that take >1 second
    properties: Property-based tests with Hypothesis

# Coverage
[coverage:run]
source = .
omit =
    */tests/*
    */venv/*
    */__pycache__/*
```

### conftest.py (Tax Wizard)
```python
"""
Pytest configuration and shared fixtures
"""
import pytest
import psycopg2
from pathlib import Path

# Test database connection
@pytest.fixture
def db_connection():
    """PostgreSQL test database connection"""
    conn = psycopg2.connect(
        host="localhost",
        database="ai_company_foundation",
        user="postgres",
        password="your_password"
    )
    yield conn
    conn.close()

@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs"""
    output_dir = tmp_path / "test_outputs"
    output_dir.mkdir()
    return output_dir

@pytest.fixture
def sample_wizard_json():
    """Sample wizard_questions JSON for testing"""
    return {
        "question_id": "Q1",
        "deduction_type": "car_expenses",
        "question_text": "Do you use your car for work?",
        "question_type": "yes_no",
        "question_order": 1
    }

@pytest.fixture
def ato_test_cases():
    """ATO test cases for formula validation"""
    return [
        {"km": 1000, "rate": 0.85, "expected": 850.00},
        {"km": 5000, "rate": 0.85, "expected": 4250.00},
        {"km": 5001, "rate": 0.85, "expected": "error"},  # Over limit
    ]
```

### .coveragerc (Tax Wizard)
```ini
[run]
source = .
omit =
    */tests/*
    */venv/*
    */__pycache__/*
    */migrations/*

[report]
precision = 2
show_missing = True
skip_covered = False

[html]
directory = htmlcov
```

---

## Example Test Files

### test_formula_properties.py (Hypothesis)
```python
"""
Property-based tests for formula validation using Hypothesis
"""
from hypothesis import given, strategies as st
import pytest

@given(
    kilometers=st.integers(min_value=1, max_value=5000),
    rate=st.just(0.85)  # ATO 2024-25 rate
)
def test_cents_per_km_always_positive(kilometers: int, rate: float):
    """Property: Result should always be positive"""
    from formula_validator import calculate_cents_per_km

    result = calculate_cents_per_km(kilometers, rate)

    assert result > 0, f"Expected positive result, got {result}"

@given(
    kilometers=st.integers(min_value=1, max_value=5000),
    rate=st.just(0.85)
)
def test_cents_per_km_equals_formula(kilometers: int, rate: float):
    """Property: Result should equal km * rate"""
    from formula_validator import calculate_cents_per_km

    result = calculate_cents_per_km(kilometers, rate)
    expected = kilometers * rate

    assert abs(result - expected) < 0.01, \
        f"Expected {expected}, got {result}"

@given(
    kilometers=st.integers(min_value=5001, max_value=50000),
    rate=st.just(0.85)
)
def test_cents_per_km_rejects_over_limit(kilometers: int, rate: float):
    """Property: Should reject km > 5000"""
    from formula_validator import calculate_cents_per_km

    with pytest.raises(ValueError, match="exceeds 5000 km limit"):
        calculate_cents_per_km(kilometers, rate)
```

### UserLoaderTests.cs (xUnit + FluentAssertions)
```csharp
using Xunit;
using FluentAssertions;
using Nimbus.UserLoader;

namespace Nimbus.UserLoader.Tests
{
    public class UserLoaderTests
    {
        [Fact]
        public void GetFlexibleVal_WithValidInput_ReturnsValue()
        {
            // Arrange
            var input = new Dictionary<string, object>
            {
                ["username"] = "john.doe"
            };

            // Act
            var result = UserHelper.GetFlexibleVal(input, "username");

            // Assert
            result.Should().Be("john.doe");
        }

        [Theory]
        [InlineData("2024-10-19", "2024-10-19T00:00:00Z")]
        [InlineData("19/10/2024", "2024-10-19T00:00:00Z")]
        [InlineData("10-19-2024", "2024-10-19T00:00:00Z")]
        public void NormalizeDate_WithVariousFormats_ReturnsISO8601(
            string input,
            string expected)
        {
            // Act
            var result = DateHelper.NormalizeToISO8601(input);

            // Assert
            result.Should().Be(expected);
        }

        [Fact]
        public void ValidateEmptyRecords_WithAllEmptyFields_ThrowsException()
        {
            // Arrange
            var emptyRecord = new UserRecord
            {
                Username = "",
                Email = "",
                FirstName = "",
                LastName = ""
            };

            // Act & Assert
            FluentActions
                .Invoking(() => Validator.ValidateRecord(emptyRecord))
                .Should()
                .Throw<ValidationException>()
                .WithMessage("All fields are empty");
        }
    }
}
```

---

## Execution Commands

### Tax Wizard (Python)
```bash
# Activate testing venv
C:/venvs/testing/Scripts/activate

# Run all tests
cd C:/Projects/ai-workspace/tax-wizard-tools
pytest

# Run specific test types
pytest -m unit              # Fast unit tests only
pytest -m integration       # Integration tests
pytest -m properties        # Property-based tests

# Run with coverage
pytest --cov --cov-report=html

# Run in parallel (faster)
pytest -n auto

# Run specific file
pytest tests/properties/test_formula_properties.py

# Run with verbose output
pytest -vv
```

### Nimbus (.NET)
```bash
# Run all tests
cd C:/Projects/nimbus-user-loader
dotnet test

# Run with detailed output
dotnet test --logger "console;verbosity=detailed"

# Run with coverage
dotnet test /p:CollectCoverage=true /p:CoverletOutputFormat=opencover

# Run specific test
dotnet test --filter "FullyQualifiedName~UserLoaderTests.GetFlexibleVal"

# Run in parallel (default)
dotnet test --parallel
```

---

## CI/CD Integration (Future)

### GitHub Actions (.github/workflows/test.yml)
```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test-python:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest playwright hypothesis
          playwright install
      - name: Run tests
        run: pytest --cov

  test-dotnet:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'
      - name: Restore dependencies
        run: dotnet restore
      - name: Build
        run: dotnet build --no-restore
      - name: Test
        run: dotnet test --no-build --verbosity normal
```

---

## MCP Integration

### Using python-testing-mcp in Diana

```python
# Diana generates tests automatically
mcp__python_testing__generate_unit_tests(
    file_path="C:/Projects/ai-workspace/tax-wizard-tools/formula_validator.py",
    test_framework="pytest",
    coverage_target=80
)

# Diana runs tests and gets results
mcp__python_testing__run_tests(
    project_path="C:/Projects/ai-workspace/tax-wizard-tools",
    test_path="tests/unit"
)

# Diana analyzes coverage
mcp__python_testing__coverage_analysis(
    project_path="C:/Projects/ai-workspace/tax-wizard-tools"
)
```

---

## Installation Checklist

### Prerequisites
- [x] Python 3.13.7 installed
- [x] .NET 9.0 SDK installed
- [x] PostgreSQL accessible
- [x] Git Bash available

### Step-by-Step

**1. Create testing venv**
```bash
python -m venv C:/venvs/testing
```

**2. Install Python testing tools**
```bash
C:/venvs/testing/Scripts/activate
pip install pytest pytest-cov pytest-xdist pytest-asyncio
pip install playwright && playwright install
pip install hypothesis
pip install python-testing-mcp
```

**3. Create tax-wizard test structure**
```bash
cd C:/Projects/ai-workspace/tax-wizard-tools
mkdir -p tests/{unit,integration,e2e,properties}
touch tests/__init__.py
touch conftest.py pytest.ini .coveragerc
```

**4. Create Nimbus test project**
```bash
cd C:/Projects/nimbus-user-loader
dotnet new xunit -n nimbus-user-loader.Tests -f net8.0
cd nimbus-user-loader.Tests
dotnet add reference ../src/nimbus-user-loader/nimbus-user-loader.csproj
dotnet add package FluentAssertions --version 7.0.0
dotnet add package Moq --version 4.20.72
dotnet add package FlaUI.UIA3 --version 4.0.0
cd ..
dotnet sln add nimbus-user-loader.Tests/nimbus-user-loader.Tests.csproj
```

**5. Add python-testing-mcp to all family members**
```bash
# Update .mcp.json files (see Section 4 above)
```

**6. Verify installations**
```bash
# Python
pytest --version
playwright --version

# .NET
dotnet test --help
```

---

## Next Steps After Setup

1. **Generate first test** with OpenAI/python-testing-mcp
2. **Run test suite** to verify setup
3. **Check coverage** (target: 80%+)
4. **Add CI/CD** (GitHub Actions)
5. **Document** test patterns in wiki

---

**Document Status:** Implementation Ready
**Estimated Setup Time:** 30-45 minutes
**Ready for:** Execution
