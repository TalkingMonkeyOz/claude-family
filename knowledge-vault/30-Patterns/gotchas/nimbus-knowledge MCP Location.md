---
title: nimbus-knowledge MCP Location
created: 2026-01-20
updated: 2026-01-20
tags: [mcp, nimbus, gotcha, configuration]
category: gotcha
status: active
severity: high
---

# nimbus-knowledge MCP Location

## The Gotcha

The nimbus-knowledge MCP server is **NOT** in claude-family - it's in **nimbus-mui**.

## Wrong Path (Does Not Exist)

```
C:\Projects\claude-family\mcp-servers\nimbus-knowledge\server.py  ❌
```

## Correct Path

```
C:\Projects\nimbus-mui\mcp-server\server.py  ✅
```

## Database Reference

```sql
SELECT mcp_package FROM claude.mcp_configs
WHERE mcp_server_name = 'nimbus-knowledge';
-- Result: local:C:\\Projects\\nimbus-mui\\mcp-server\\server.py
```

## Correct .mcp.json Config

```json
{
  "mcpServers": {
    "nimbus-knowledge": {
      "command": "uv",
      "args": ["run", "C:/Projects/nimbus-mui/mcp-server/server.py"],
      "env": {}
    }
  }
}
```

## Projects Using nimbus-knowledge

- monash-nimbus-reports
- nimbus-mui
- nimbus-import

## Why This Matters

If you configure the wrong path, Claude Code will show `nimbus-knowledge · ✗ failed` in `/mcp` output with no helpful error message.

---

## Keywords

nimbus-knowledge, mcp, server location, nimbus-mui, failed, configuration

---

**Version**: 1.0
**Created**: 2026-01-20
**Updated**: 2026-01-20
**Location**: knowledge-vault/30-Patterns/gotchas/nimbus-knowledge MCP Location.md
