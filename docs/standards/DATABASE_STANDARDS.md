# Database Standards

**Document Type**: Standard
**Version**: 1.0
**Created**: 2025-12-07
**Status**: Active
**Enforcement**: MANDATORY - All database work MUST follow these standards

---

## Purpose

Define consistent database patterns for all projects using PostgreSQL. These standards ensure:
- Consistent schema design across projects
- Data integrity through constraints
- Query performance through proper indexing
- Maintainable migrations and versioning

---

## 1. Schema Design

### 1.1 Schema Organization

```sql
-- Use schemas to organize related tables
CREATE SCHEMA IF NOT EXISTS app;      -- Application data
CREATE SCHEMA IF NOT EXISTS audit;    -- Audit logs
CREATE SCHEMA IF NOT EXISTS config;   -- Configuration tables

-- Set search path
SET search_path TO app, public;
```

**Claude Family Standard:**
- Schema: `claude` (consolidated)
- All new tables in `claude` schema
- Legacy schemas (`claude_family`, `claude_pm`, `claude_mission_control`) are deprecated

### 1.2 Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Tables | plural snake_case | `users`, `build_tasks` |
| Columns | snake_case | `user_id`, `created_at` |
| Primary keys | `id` or `{table}_id` | `user_id` |
| Foreign keys | `{referenced_table}_id` | `project_id` |
| Indexes | `idx_{table}_{columns}` | `idx_users_email` |
| Constraints | `{type}_{table}_{column}` | `chk_users_status` |
| Functions | snake_case verb | `get_user_sessions()` |
| Triggers | `trg_{table}_{action}` | `trg_users_audit` |

### 1.3 Standard Columns (ALL Tables)

```sql
CREATE TABLE example (
    -- Primary key (UUID preferred)
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Business columns here...

    -- Standard audit columns (REQUIRED)
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100)
);

-- Auto-update trigger (REQUIRED)
CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON example
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 2. Data Types

### 2.1 Preferred Types

| Data | Type | Why |
|------|------|-----|
| IDs | `UUID` | Globally unique, no guessing |
| Short text | `VARCHAR(n)` | Explicit length limit |
| Long text | `TEXT` | Unlimited length |
| Boolean | `BOOLEAN` | Not INT or CHAR |
| Money | `NUMERIC(12,2)` | Exact precision |
| Dates | `DATE` | When time not needed |
| Timestamps | `TIMESTAMPTZ` | Always with timezone |
| JSON | `JSONB` | Binary, indexable |
| Enums | `VARCHAR` + CHECK | More flexible than ENUM |

### 2.2 Avoid These Types

| Avoid | Use Instead | Why |
|-------|-------------|-----|
| `SERIAL` | `UUID` or `BIGINT` with sequence | UUIDs are safer |
| `ENUM` type | `VARCHAR` + CHECK | Easier to modify |
| `TIMESTAMP` | `TIMESTAMPTZ` | Always store timezone |
| `FLOAT/REAL` | `NUMERIC` | Precision issues |
| `CHAR(n)` | `VARCHAR(n)` | Padding wastes space |

### 2.3 Status/Enum Pattern

```sql
-- Use VARCHAR with CHECK constraint
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled')),
    priority INTEGER NOT NULL DEFAULT 3
        CHECK (priority BETWEEN 1 AND 5)
);

-- Document valid values in column_registry (Claude Family specific)
INSERT INTO claude.column_registry (table_name, column_name, valid_values)
VALUES ('tasks', 'status', '["pending", "in_progress", "completed", "cancelled"]');
```

---

## 3. Data Gateway (Claude Family)

### 3.1 Column Registry

**BEFORE writing to constrained columns**, check valid values:

```sql
SELECT valid_values FROM claude.column_registry
WHERE table_name = 'TABLE' AND column_name = 'COLUMN';
```

### 3.2 Key Constraints

| Field | Valid Values | Notes |
|-------|--------------|-------|
| status | Varies by table | Check registry |
| priority | 1-5 | 1=critical, 5=low |
| feedback_type | bug, design, question, change | feedback table |

### 3.3 Constraint Enforcement

```sql
-- Constraints are enforced at database level
-- If INSERT/UPDATE fails with constraint violation:
-- 1. Check column_registry for valid values
-- 2. Update your value to match allowed list
-- 3. If new value needed, update constraint (with approval)
```

---

## 4. Constraints

### 4.1 Primary Keys

```sql
-- UUID primary key (preferred)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid()
);

-- Composite primary key (for join tables)
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);
```

### 4.2 Foreign Keys

```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    project_id UUID
        REFERENCES projects(id)
        ON DELETE SET NULL
);
```

**ON DELETE Actions:**
| Action | When to Use |
|--------|-------------|
| CASCADE | Child can't exist without parent (sessions → users) |
| SET NULL | Preserve child, clear reference (tasks → assignee) |
| RESTRICT | Prevent deletion if children exist (projects → tasks) |

### 4.3 Check Constraints

```sql
-- Value validation
ALTER TABLE users ADD CONSTRAINT chk_users_email
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$');

-- Range validation
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_priority
    CHECK (priority BETWEEN 1 AND 5);

-- Enum validation
ALTER TABLE tasks ADD CONSTRAINT chk_tasks_status
    CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled'));
```

### 4.4 Unique Constraints

```sql
-- Single column
ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);

-- Multi-column
ALTER TABLE project_members ADD CONSTRAINT uq_project_members_user_project
    UNIQUE (project_id, user_id);

-- Partial unique (conditional)
CREATE UNIQUE INDEX uq_users_active_email ON users (email)
    WHERE deleted_at IS NULL;
```

---

## 5. Indexing

### 5.1 When to Index

**Always index:**
- Foreign key columns
- Columns in WHERE clauses (high selectivity)
- Columns in JOIN conditions
- Columns in ORDER BY
- Columns in unique constraints

**Don't over-index:**
- Small tables (< 1000 rows)
- Columns with low selectivity (boolean, status)
- Tables with heavy writes

### 5.2 Index Types

```sql
-- B-tree (default, most common)
CREATE INDEX idx_users_email ON users (email);

-- Partial index (subset of rows)
CREATE INDEX idx_tasks_active ON tasks (status)
    WHERE status IN ('pending', 'in_progress');

-- Covering index (includes additional columns)
CREATE INDEX idx_users_name_email ON users (name) INCLUDE (email);

-- GIN index (for JSONB, arrays, full-text)
CREATE INDEX idx_users_metadata ON users USING GIN (metadata);

-- Expression index
CREATE INDEX idx_users_lower_email ON users (LOWER(email));
```

### 5.3 Index Naming

```sql
-- Pattern: idx_{table}_{columns}
idx_users_email
idx_tasks_project_id_status
idx_sessions_user_id_created_at
```

---

## 6. Queries

### 6.1 Always Paginate

```sql
-- NEVER do this
SELECT * FROM users;

-- ALWAYS paginate
SELECT * FROM users
ORDER BY created_at DESC
LIMIT 20 OFFSET 0;
```

### 6.2 Select Only Needed Columns

```sql
-- Avoid SELECT *
SELECT * FROM users;

-- Be explicit
SELECT id, name, email, created_at FROM users;
```

### 6.3 Use EXPLAIN ANALYZE

```sql
-- Before deploying queries to production
EXPLAIN ANALYZE
SELECT * FROM tasks
WHERE project_id = 'abc' AND status = 'pending'
ORDER BY created_at DESC
LIMIT 20;

-- Check for:
-- - Sequential scans on large tables (add index)
-- - High row estimates vs actual (update statistics)
-- - Nested loops on large joins (add index or optimize)
```

### 6.4 Avoid N+1 Queries

```sql
-- BAD: N+1 queries
-- Query 1: SELECT * FROM users
-- Query 2-N: SELECT * FROM sessions WHERE user_id = ?

-- GOOD: Single join query
SELECT u.*, s.*
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
WHERE u.status = 'active';

-- Or batch load
SELECT * FROM sessions WHERE user_id = ANY($1);
```

### 6.5 Parameterized Queries

```sql
-- NEVER concatenate user input
-- BAD (SQL injection risk)
SELECT * FROM users WHERE email = '${userInput}';

-- GOOD (parameterized)
SELECT * FROM users WHERE email = $1;
```

---

## 7. Transactions

### 7.1 Transaction Basics

```sql
BEGIN;

-- Multiple operations that must succeed together
INSERT INTO accounts (id, balance) VALUES ('A', 1000);
INSERT INTO accounts (id, balance) VALUES ('B', 0);
UPDATE accounts SET balance = balance - 100 WHERE id = 'A';
UPDATE accounts SET balance = balance + 100 WHERE id = 'B';

COMMIT;

-- If any fails:
ROLLBACK;
```

### 7.2 Isolation Levels

| Level | Use Case |
|-------|----------|
| READ COMMITTED | Default, most queries |
| REPEATABLE READ | Reports needing consistent snapshot |
| SERIALIZABLE | Financial operations, inventory |

### 7.3 Deadlock Prevention

```sql
-- Always lock in consistent order
-- If you need to update users and accounts:
-- Always: users first, then accounts

-- Use SELECT FOR UPDATE carefully
SELECT * FROM accounts WHERE id = 'A' FOR UPDATE;
```

---

## 8. Migrations

### 8.1 Migration File Naming

```
migrations/
├── 001_create_users.sql
├── 002_create_projects.sql
├── 003_add_user_email_index.sql
└── 004_add_status_column.sql
```

### 8.2 Migration Structure

```sql
-- migrations/003_add_user_email_index.sql

-- Description: Add index on users.email for faster lookups
-- Author: claude-code-unified
-- Date: 2025-12-07

-- Up migration
CREATE INDEX CONCURRENTLY idx_users_email ON users (email);

-- Down migration (comment out, run manually if needed)
-- DROP INDEX idx_users_email;
```

### 8.3 Safe Migration Practices

```sql
-- Use CONCURRENTLY for indexes (no table lock)
CREATE INDEX CONCURRENTLY idx_name ON table (column);

-- Add columns as nullable first
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Then update data
UPDATE users SET phone = '' WHERE phone IS NULL;

-- Then add constraint
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;

-- For column renames, add new → migrate → drop old
ALTER TABLE users ADD COLUMN full_name VARCHAR(200);
UPDATE users SET full_name = name;
ALTER TABLE users DROP COLUMN name;
```

---

## 9. Performance

### 9.1 Table Statistics

```sql
-- Update statistics after bulk changes
ANALYZE users;
ANALYZE VERBOSE users;  -- With details

-- Check table size
SELECT pg_size_pretty(pg_total_relation_size('users'));

-- Check index usage
SELECT
    indexrelname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE schemaname = 'claude'
ORDER BY idx_scan DESC;
```

### 9.2 Connection Pooling

```typescript
// Use connection pooling (not new connection per query)
// PgBouncer or built-in pool

const pool = new Pool({
  max: 20,              // Max connections
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 2000,
});
```

### 9.3 Query Timeouts

```sql
-- Set statement timeout to prevent runaway queries
SET statement_timeout = '30s';

-- Or per-session
ALTER ROLE app_user SET statement_timeout = '30s';
```

---

## 10. Security

### 10.1 Role-Based Access

```sql
-- Application role (limited permissions)
CREATE ROLE app_user WITH LOGIN PASSWORD 'secret';
GRANT USAGE ON SCHEMA claude TO app_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA claude TO app_user;
REVOKE DELETE ON claude.audit_log FROM app_user;

-- Admin role (full access)
CREATE ROLE app_admin WITH LOGIN PASSWORD 'secret';
GRANT ALL ON SCHEMA claude TO app_admin;
```

### 10.2 Row-Level Security

```sql
-- Enable RLS
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own projects
CREATE POLICY projects_tenant_isolation ON projects
    FOR ALL
    USING (tenant_id = current_setting('app.tenant_id')::uuid);
```

### 10.3 Sensitive Data

```sql
-- Never store plaintext passwords
-- Use pgcrypto or application-level hashing
password_hash VARCHAR(100) NOT NULL,

-- Mask sensitive data in logs
-- Configure in postgresql.conf:
-- log_parameter_max_length = 0
```

---

## 11. Backup and Recovery

### 11.1 Backup Strategy

| Type | Frequency | Retention |
|------|-----------|-----------|
| Full backup (pg_dump) | Daily | 7 days |
| WAL archiving | Continuous | 7 days |
| Point-in-time recovery | Available | 7 days |

### 11.2 Backup Commands

```bash
# Full backup
pg_dump -Fc ai_company_foundation > backup_$(date +%Y%m%d).dump

# Restore
pg_restore -d ai_company_foundation backup_20251207.dump

# Specific schema
pg_dump -n claude ai_company_foundation > claude_schema.sql
```

---

## Quick Reference Checklist

Before deploying database changes:

- [ ] Tables have UUID primary keys
- [ ] All foreign keys have indexes
- [ ] Status columns have CHECK constraints
- [ ] Standard audit columns (created_at, updated_at)
- [ ] Updated_at trigger exists
- [ ] Queries are paginated
- [ ] Queries use parameterized values
- [ ] Indexes on filtered/sorted columns
- [ ] Migration is reversible
- [ ] EXPLAIN ANALYZE shows good plan
- [ ] Column registry updated for constrained columns

---

## Related Documents

- DEVELOPMENT_STANDARDS.md - Code conventions
- API_STANDARDS.md - API patterns
- DATA_GATEWAY_MASTER_PLAN.md - Full data gateway spec

---

**Revision History:**

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-07 | Initial version |
