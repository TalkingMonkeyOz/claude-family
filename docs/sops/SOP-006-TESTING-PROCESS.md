# SOP-006: Testing Process

**Status**: Active
**Version**: 1.0
**Created**: 2025-12-06
**Owner**: Claude Family Infrastructure

---

## Purpose

This SOP defines the standardized testing process for all Claude Family projects. It ensures code quality, prevents regressions, and catches breaking changes before they reach production.

---

## Test Levels

### Level 1: Quick Smoke Test (<30 seconds)
**When**: Before every commit
**What**: Fast checks that catch obvious issues

| Check | Command | Catches |
|-------|---------|---------|
| Type check | `pnpm build` / `dotnet build` | Type errors |
| Lint | `pnpm lint` / `dotnet format --verify-no-changes` | Code style issues |
| Schema validation | `python scripts/validate_schema.py` | Column mismatches |

### Level 2: Integration Test (~2 minutes)
**When**: Before push, after significant changes
**What**: Verify components work together

| Check | Command | Catches |
|-------|---------|---------|
| API smoke test | `python scripts/api_smoke_test.py` | Broken endpoints |
| Database queries | `python scripts/query_validation.py` | Query errors |
| Unit tests | `pnpm test` / `dotnet test` | Logic errors |

### Level 3: Full Regression (~5-10 minutes)
**When**: Before release, after major changes
**What**: End-to-end validation of key workflows

| Check | Command | Catches |
|-------|---------|---------|
| E2E tests | `npx playwright test` | UI/UX regressions |
| Cross-project validation | `python scripts/cross_project_check.py` | Breaking changes |
| Data quality review | `python scripts/reviewer_data_quality.py` | Data issues |
| Doc quality review | `python scripts/reviewer_doc_quality.py` | Stale docs |

---

## Pre-Commit Hook

Add to `.claude/hooks.json`:

```json
{
  "hooks": [
    {
      "event": "PreCommit",
      "script": "python scripts/pre_commit_check.py",
      "blocking": true
    }
  ]
}
```

The pre-commit check runs Level 1 tests automatically.

---

## Schema Validation

### Problem
Schema changes (views, columns) can silently break downstream consumers. Example: `v_core_documents` was missing `project_id` column, causing MCW 500 errors.

### Solution
Before changing any `claude.*` view or table:

1. **Identify consumers**: Query which projects use the object
2. **Run consumer check**: Verify all consumers still work after change
3. **Update column_registry**: If adding columns, register valid values

### Script: `scripts/validate_schema.py`

```python
# Validates that all expected columns exist in views/tables
# Run before committing schema changes
python scripts/validate_schema.py --view v_core_documents
```

---

## API Smoke Test

### Purpose
Verify all API endpoints return 200 (or expected status codes).

### Script: `scripts/api_smoke_test.py`

```python
# Hits all /api/* routes and reports failures
python scripts/api_smoke_test.py --base-url http://localhost:3000
```

### Output
```
API Smoke Test Results
======================
✅ GET /api/projects - 200 (45ms)
✅ GET /api/sessions - 200 (32ms)
❌ GET /api/documents - 500 (12ms)
   Error: column "project_id" does not exist

FAILED: 1/15 endpoints
```

---

## Cross-Project Validation

### Problem
Changes in `claude-family` (schema, views, scripts) can break other projects.

### Solution
Before merging changes to shared infrastructure:

```bash
# Check all projects still work
python scripts/cross_project_check.py
```

This script:
1. Identifies projects using changed files
2. Runs their smoke tests
3. Reports any failures

---

## Test Data Management

### Rules
1. **Never commit test data to production tables**
2. **Clean up test data after testing** - Use `--cleanup` flag
3. **Use recognizable patterns** - Prefix with `TEST_` or `E2E_`
4. **Auto-reviewer catches test data** - `data-reviewer-sonnet` flags it

### Cleanup
```bash
# Find and report test data
python scripts/reviewer_data_quality.py --json | grep -i test

# Manual cleanup (with confirmation)
python scripts/cleanup_test_data.py --dry-run
python scripts/cleanup_test_data.py --execute
```

---

## Project-Specific Testing

### Next.js Projects (MCW, etc.)

```bash
# Level 1
pnpm build && pnpm lint

# Level 2
pnpm test

# Level 3
pnpm build && npx playwright test
```

### Python Projects (MCP servers, scripts)

```bash
# Level 1
python -m py_compile *.py
ruff check .

# Level 2
pytest tests/

# Level 3
pytest tests/ --cov --cov-report=html
```

### C#/.NET Projects (Nimbus, etc.)

```bash
# Level 1
dotnet build
dotnet format --verify-no-changes

# Level 2
dotnet test

# Level 3
dotnet test --collect:"XPlat Code Coverage"
```

---

## Automated Testing Agents

Use orchestrator agents for comprehensive testing:

### test-coordinator-sonnet
Orchestrates multiple test agents in parallel:
```python
spawn_agent("test-coordinator-sonnet",
    "Run full test suite for mission-control-web",
    workspace_dir="C:/Projects/mission-control-web")
```

### nextjs-tester-haiku
Next.js-specific E2E testing:
```python
spawn_agent("nextjs-tester-haiku",
    "Test all page routes and API endpoints",
    workspace_dir="C:/Projects/mission-control-web")
```

### debugger-haiku
Fast failure analysis:
```python
spawn_agent("debugger-haiku",
    "Analyze test failures and identify root cause",
    workspace_dir="C:/Projects/project-name")
```

---

## CI/CD Integration (Future)

### GitHub Actions Workflow

```yaml
name: Test Suite
on: [push, pull_request]

jobs:
  level1:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Type Check
        run: pnpm build
      - name: Lint
        run: pnpm lint

  level2:
    needs: level1
    runs-on: ubuntu-latest
    steps:
      - name: Unit Tests
        run: pnpm test
      - name: API Smoke Test
        run: python scripts/api_smoke_test.py

  level3:
    needs: level2
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - name: E2E Tests
        run: npx playwright test
```

---

## Troubleshooting

### Tests pass locally but fail in CI
1. Check environment variables
2. Verify database connection
3. Check for hardcoded paths (use relative or env vars)

### Schema validation fails
1. Run `python scripts/validate_schema.py --verbose`
2. Check `claude.column_registry` for expected columns
3. Verify view definition matches expectations

### API smoke test times out
1. Ensure dev server is running
2. Check port conflicts
3. Increase timeout in script

---

## Checklist

### Before Every Commit
- [ ] Level 1 tests pass
- [ ] No TypeScript/lint errors
- [ ] Schema validation passes (if schema changed)

### Before Push
- [ ] Level 2 tests pass
- [ ] API endpoints respond correctly
- [ ] Unit tests pass

### Before Release
- [ ] Level 3 tests pass
- [ ] E2E tests pass
- [ ] Cross-project validation passes
- [ ] Documentation updated
- [ ] Data quality review clean

---

## Related Documents

- `SOP-005-AUTO-REVIEWERS.md` - Quality review agents
- `ENFORCEMENT_HIERARCHY.md` - Hook enforcement system
- `scripts/validate_schema.py` - Schema validation script
- `scripts/api_smoke_test.py` - API smoke test script

---

**Version**: 1.0
**Created**: 2025-12-06
**Location**: C:\Projects\claude-family\docs\sops\SOP-006-TESTING-PROCESS.md
