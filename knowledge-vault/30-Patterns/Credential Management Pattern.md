---
projects:
  - claude-family
  - all
tags:
  - pattern/credentials
  - pattern/security
  - infrastructure
synced: false
---

# Credential Management Pattern

All Claude Family projects follow a single pattern for storing, loading, and using credentials.

---

## Single Source of Truth

**All credentials live in .env files**, loaded by `scripts/config.py` in priority order:

1. Environment variables (highest priority, never overridden)
2. `scripts/.env` (project-local)
3. `claude-family/.env` (project root)
4. `C:\claude\shared\.env` (shared across projects)
5. `~/.claude/.env` (user-level)
6. `ai-workspace\.env` (legacy fallback)

**Format**: `KEY=value` — supports `"quoted"` and `'quoted'` values, skips `${VAR}` placeholders.

---

## The Shared Module: `scripts/config.py`

**This is THE credential module.** All scripts import from here — no copy-pasting.

### Functions

| Function | Purpose | Mode |
|----------|---------|------|
| `detect_psycopg()` | Cached v3/v2 detection. Returns `(module, version, dict_row, cursor_class)` | Cached |
| `get_database_uri()` | Checks `DATABASE_URI` > `DATABASE_URL` > `POSTGRES_CONNECTION_STRING` > builds from parts. Sets both env vars. | Lazy |
| `get_db_connection(strict=False)` | Full connection with psycopg auto-detect. `strict=False` returns None (hooks). `strict=True` raises (MCP servers). | Lazy |
| `get_voyage_key()` | `os.environ.get('VOYAGE_API_KEY')` | Lazy |
| `get_anthropic_key()` | `os.environ.get('ANTHROPIC_API_KEY')` | Lazy |

### Legacy Exports (unchanged)

`POSTGRES_CONFIG`, `DATABASE_URI`, `ANTHROPIC_API_KEY`, `CLAUDE_FAMILY_ROOT`, `STANDARDS_PATH`, `SHARED_PATH`

### Usage Pattern (3 lines)

```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection, detect_psycopg
DB_AVAILABLE = detect_psycopg()[0] is not None
```

For embed scripts (URI only):
```python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_database_uri
DB_CONNECTION = get_database_uri()
```

---

## Standard Environment Variables

| Variable | Required | Used By | Notes |
|----------|----------|---------|-------|
| `POSTGRES_HOST` | Yes | All DB connections | Default: `localhost` |
| `POSTGRES_DATABASE` | Yes | All DB connections | Default: `ai_company_foundation` |
| `POSTGRES_USER` | Yes | All DB connections | Default: `postgres` |
| `POSTGRES_PASSWORD` | Yes | All DB connections | |
| `DATABASE_URI` | Built | MCP servers, hooks | Constructed from POSTGRES_* by `get_database_uri()` |
| `DATABASE_URL` | Alias | Legacy scripts | Set automatically by `get_database_uri()` |
| `VOYAGE_API_KEY` | Optional | RAG, embeddings | Disabled gracefully if missing |
| `ANTHROPIC_API_KEY` | Optional | Agent spawning | |

---

## Three Rules

### 1. Encapsulation — Servers Load Their Own Config

Callers (Desktop, Code, hooks) do NOT pass credentials. Servers load from .env internally.

**Correct**: `{"command": "python.exe", "args": ["server_v2.py"]}` — no `env` block.

**Wrong**: Passing `DATABASE_URI` in the caller's `env` block. Claude Desktop doesn't expand `${VAR}` ([GitHub #1039](https://github.com/modelcontextprotocol/servers/issues/1039)).

### 2. Lazy Loading — Read Keys When Needed

```python
# CORRECT — lazy function from config.py
from config import get_voyage_key
key = get_voyage_key()  # reads os.environ at call time

# WRONG — module-level constant (None forever if .env loads later)
VOYAGE_API_KEY = os.environ.get('VOYAGE_API_KEY')
```

### 3. Single Loader — Import from config.py

**Never copy-paste** psycopg detection, .env loading, or `get_db_connection()`. Import from `scripts/config.py`.

---

## BPMN Model

The credential loading flow is modeled in: `processes/infrastructure/credential_loading.bpmn`

Flow: load .env files -> detect psycopg -> resolve URI -> attempt connection -> strict/graceful failure paths.

19 tests in `tests/test_credential_loading.py` cover all 7 paths (happy + 3 failure modes x strict/graceful).

---

## Adding a New Credential

1. Add to `.env`: `NEW_API_KEY=value`
2. Add lazy getter to `config.py`: `def get_new_key(): return os.environ.get('NEW_API_KEY')`
3. Document in the table above
4. Access via the getter at call time

## Rotating a Credential

1. Get new key from provider
2. Update `.env` with new value
3. Restart: MCP servers need restart; hooks re-read on each invocation
4. Verify: Run a tool that uses the credential

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "No psycopg driver found" | Neither psycopg nor psycopg2 installed | `pip install psycopg` |
| "No database URI" | POSTGRES_PASSWORD missing from .env | Add to .env file |
| `strict=True` raising | MCP server can't connect | Check .env exists, DB is running |
| `strict=False` returning None | Expected in hooks when DB is down | Hook continues without DB |
| `${VAR}` in logs | Claude Desktop bug | Don't use `env` blocks in MCP config |

---

**Version**: 2.0
**Created**: 2026-02-26
**Updated**: 2026-02-26
**Location**: knowledge-vault/30-Patterns/Credential Management Pattern.md
