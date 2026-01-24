---
name: sql-optimization
description: SQL performance tuning, indexing, query optimization for PostgreSQL
model: haiku
allowed-tools:
  - Read
  - mcp__postgres__execute_sql
  - mcp__postgres__explain_query
  - mcp__postgres__analyze_query_indexes
---

# SQL Optimization Skill

**Status**: Active
**Last Updated**: 2026-01-24

---

## Overview

SQL performance optimization for PostgreSQL. Query tuning, indexing strategies, execution plan analysis.

---

## Core Patterns

### Query Performance

```sql
-- BAD: Function on column prevents index use
SELECT * FROM orders WHERE YEAR(created_at) = 2024;

-- GOOD: Range comparison uses index
SELECT * FROM orders
WHERE created_at >= '2024-01-01' AND created_at < '2025-01-01';
```

### JOIN Optimization

```sql
-- BAD: LEFT JOIN with filter = implicit INNER
SELECT o.*, c.name FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
WHERE c.status = 'active';

-- GOOD: Explicit INNER JOIN
SELECT o.id, o.total, c.name FROM orders o
INNER JOIN customers c ON o.customer_id = c.id AND c.status = 'active';
```

### Subquery → Window Function

```sql
-- BAD: Correlated subquery (runs for each row)
SELECT * FROM products p
WHERE price > (SELECT AVG(price) FROM products WHERE category_id = p.category_id);

-- GOOD: Window function (single pass)
SELECT * FROM (
  SELECT *, AVG(price) OVER (PARTITION BY category_id) as avg_price
  FROM products
) t WHERE price > avg_price;
```

### Pagination

```sql
-- BAD: OFFSET (scans skipped rows)
SELECT * FROM products ORDER BY created_at DESC LIMIT 20 OFFSET 10000;

-- GOOD: Cursor-based (uses index)
SELECT * FROM products
WHERE created_at < '2024-06-15 10:30:00'
ORDER BY created_at DESC LIMIT 20;
```

---

## Index Strategy

### Composite Index Order

```sql
-- Columns in order of: equality → range → sort
CREATE INDEX idx_orders_status_date ON orders(status, created_at);

-- For: WHERE status = 'pending' ORDER BY created_at DESC
```

### Partial Indexes

```sql
-- Only index relevant rows
CREATE INDEX idx_orders_pending ON orders(created_at)
WHERE status = 'pending';
```

### Covering Indexes

```sql
-- Include columns to avoid table lookup
CREATE INDEX idx_users_email_name ON users(email) INCLUDE (first_name, last_name);
```

---

## Analyze Queries

```sql
-- Execution plan with timing
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) SELECT ...;

-- Key things to look for:
-- - Seq Scan on large tables (need index?)
-- - High "actual rows" vs "estimated rows" (stale stats?)
-- - Nested Loop with high row counts (JOIN issue?)
```

---

## Claude Family Integration

Use MCP tools for analysis:

```
mcp__postgres__explain_query(sql="SELECT ...")
mcp__postgres__analyze_query_indexes(sql="SELECT ...")
```

---

## Related Skills

- `database` - Database operations, schema patterns
- `code-review` - SQL code review

---

**Version**: 1.0
**Source**: Transformed from awesome-copilot "sql-optimization"
