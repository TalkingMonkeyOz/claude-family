---
category: database
confidence: 95
created: 2025-12-19
projects:
- claude-family
synced: true
synced_at: '2025-12-20T13:15:19.783940'
tags:
- python
- postgresql
- psycopg
title: psycopg3 vs psycopg2 Connection Parameters
type: gotcha
---

# psycopg3 vs psycopg2 Connection Parameters

## Summary
psycopg3 uses `dbname` for database name, while psycopg2 uses `database`. Convert the key when migrating.

## Details
When upgrading from psycopg2 to psycopg3 (or using both in a project), the connection parameter for the database name is different.

### psycopg2
```python
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="ai_company_foundation",  # Uses 'database'
    user="postgres",
    password="password"
)
```

### psycopg3
```python
import psycopg

conn = psycopg.connect(
    host="localhost",
    port=5432,
    dbname="ai_company_foundation",  # Uses 'dbname'
    user="postgres",
    password="password"
)
```

## Code Example
```python
# Shared config dict designed for psycopg2
POSTGRES_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "ai_company_foundation",
    "user": "postgres",
    "password": "password"
}

# Convert for psycopg3
def get_psycopg3_config(config: dict) -> dict:
    """Convert psycopg2 config to psycopg3 format"""
    config = config.copy()
    if "database" in config:
        config["dbname"] = config.pop("database")
    return config

# Usage
import psycopg
conn = psycopg.connect(**get_psycopg3_config(POSTGRES_CONFIG))
```

## Error You'll See
```
TypeError: connect() got an unexpected keyword argument 'database'
```

## Related
- [[database-connection-patterns]]
- [[claude-schema-consolidation]]