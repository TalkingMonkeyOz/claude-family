# List and Filter Feedback

Display feedback items with optional filters for status, type, search keywords, and timeframe.

**Schema is `claude.*` — never `claude_pm.*` or `claude_family.*`.**

---

## Execute These Steps

### Step 1: Detect Current Project

```sql
SELECT id, project_code, project_name
FROM claude.projects
WHERE project_code ILIKE '%current-project-keyword%'
   OR project_name ILIKE '%current-project-keyword%'
LIMIT 1;
```

### Step 2: Ask User for Filters (Optional)

Ask what they want to see:

1. **Status**: All / New / Triaged / In Progress / Resolved / Won't Fix
2. **Type**: All / Bug / Design / Question / Change
3. **Search**: Keywords to search in descriptions (optional)
4. **Timeframe**: All time / Last 7 days / Last 30 days / This year

### Step 3: Build and Execute Query

**Default Query (all open items, newest first):**

```sql
SELECT
    f.id::text,
    f.feedback_type,
    f.status,
    f.priority,
    f.description,
    f.created_at,
    f.updated_at
FROM claude.feedback f
WHERE f.project_id = 'PROJECT-ID'::uuid
  AND f.status IN ('new', 'triaged', 'in_progress')
ORDER BY f.priority ASC, f.created_at DESC;
```

**Add type filter:**
```sql
-- Append to WHERE clause:
AND f.feedback_type = 'bug'  -- bug | design | question | change
```

**Add status filter:**
```sql
-- Replace status filter or append:
AND f.status = 'resolved'  -- new | triaged | in_progress | resolved | wont_fix | duplicate
```

**Add keyword search:**
```sql
-- Append to WHERE clause:
AND f.description ILIKE '%search-keyword%'
```

**Add timeframe:**
```sql
-- Append to WHERE clause:
AND f.created_at > NOW() - INTERVAL '7 days'  -- or '30 days', '1 year'
```

### Step 4: Display Results

Format results as a readable list:

```
FEEDBACK LIST - [Project Name]

Filters: [Status: New/Triaged/In Progress] [Type: All] [Search: none] [Timeframe: All]
Total Results: X items

ID (prefix)  | Type    | Status      | Priority | Created    | Description
-------------|---------|-------------|----------|------------|------------
a1b2c3d4     | bug     | new         | 2-high   | 2026-03-01 | Export button...
b2c3d4e5     | design  | in_progress | 3-medium | 2026-02-28 | Sidebar layout...

---
View details:  SELECT * FROM claude.feedback WHERE id = 'full-uuid'::uuid;
Advance status: mcp__project-tools__advance_status(type="feedback", id="FB-N", status="triaged")
```

### Step 5: Offer Actions

```
What would you like to do?

1. View details of a specific item (provide FB code or ID prefix)
2. Advance the status of an item
3. Create new feedback (/feedback-create)
4. Check open items summary (/feedback-check)
```

---

## Advanced Queries

**Count by status and type:**

```sql
SELECT
    feedback_type,
    status,
    COUNT(*) as count
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
GROUP BY feedback_type, status
ORDER BY feedback_type, status;
```

**Aging report (how long items have been open):**

```sql
SELECT
    id::text,
    feedback_type,
    status,
    description,
    created_at,
    EXTRACT(DAY FROM (NOW() - created_at))::int as days_open
FROM claude.feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'triaged', 'in_progress')
ORDER BY days_open DESC;
```

**All projects — cross-project view:**

```sql
SELECT
    p.project_code,
    f.feedback_type,
    f.status,
    COUNT(*) as count
FROM claude.feedback f
JOIN claude.projects p ON f.project_id = p.id
WHERE f.status IN ('new', 'triaged', 'in_progress')
GROUP BY p.project_code, f.feedback_type, f.status
ORDER BY p.project_code, f.feedback_type;
```

---

## Error Handling

**If no results:**
```
No feedback items match your filters.

Try:
- Broaden status filter (include 'resolved' items)
- Remove search keywords
- Expand timeframe
```

**If project not found:**
- Query `SELECT id, project_code FROM claude.projects ORDER BY project_code;`
- Use `/project-init` to register if missing

---

## Valid Column Values

| Column | Valid Values |
|--------|-------------|
| `feedback_type` | `bug`, `design`, `question`, `change` |
| `status` | `new`, `triaged`, `in_progress`, `resolved`, `wont_fix`, `duplicate` |
| `priority` | `1` (critical) to `5` (low) |

---

**Version**: 2.0 (Rewrote: use claude.feedback schema, removed all claude_pm.* references)
**Created**: 2025-12-20
**Updated**: 2026-03-09
**Location**: .claude/commands/feedback-list.md
