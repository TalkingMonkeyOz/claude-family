# project-tools MCP — tests

Pytest scaffolding for the `project-tools` MCP server. Baseline coverage
for regression catching; expand in follow-ups.

## Running

```bash
cd mcp-servers/project-tools
pytest                       # run all tests
pytest -m "not db"           # skip DB-backed tests
pytest tests/test_imports.py # single file
```

Tests auto-load `DATABASE_URL` from the repo-root `.env` and bridge it to
`DATABASE_URI` (which `server.py` expects). No external dotenv dependency.

## Layout

| File | Purpose |
|------|---------|
| `conftest.py` | Environment bootstrap, `db_conn` + `monkey_db` fixtures |
| `test_imports.py` | Import smoke tests — catch latent type-annotation and import bugs |
| `test_tier_classification.py` | Verifies `tool_remember` short/mid/long type sets |

## Adding DB-backed tests

Mark with `@pytest.mark.db` and use the `monkey_db` fixture, which
monkey-patches `server.get_db_connection` to return a connection wrapped
in a transaction that is rolled back at fixture teardown. Tool `close()`
and `commit()` calls are intercepted — tests cannot pollute shared tables.

```python
@pytest.mark.db
def test_remember_short_routes_to_session_fact(monkey_db):
    import asyncio, server
    result = asyncio.run(server.tool_remember(
        content="api_base_url=https://example.test",
        memory_type="endpoint",
        project_name="test-project",
    ))
    assert result["tier"] == "short"
    assert result["action"] == "created"
```

## Known limitations

- `monkey_db` wrapper intercepts `commit()` — tools that depend on
  observing their own commits across multiple connections will not work.
  Most tools in server.py open a single connection per call, so this
  pattern is sufficient for ~90% of the tool surface.
- Embedding-dependent paths (Voyage AI / local ONNX) will still make
  network or subprocess calls; mock at the requests boundary for unit
  tests, or mark `@pytest.mark.slow` and run on CI only.
- No async event-loop fixture yet — `tool_*` coroutines need explicit
  `asyncio.run(...)` until we add an `asyncio` marker.

## Next steps (not in this MVP)

- `test_remember.py` — dedup union-merge happy path (requires embeddings)
- `test_workfile_chunking.py` — chunking flag at >500 lines
- `test_read.py` — TOC envelope + section fetch
- `test_entity_store.py` — JSONB schema validation path
- Refactor `short_types` / `mid_types` / `long_types` to module-level
  constants so `test_tier_classification.py` can drop the source-parsing
  hack (currently reads `server.tool_remember` source text).
