# List and Filter Feedback

Display feedback items with optional filters for status, type, and search keywords.

---

## Step 1: Detect Current Project

Determine project_id from current working directory:

**Quick Reference:**
- `claude-pm` → `a3097e59-7799-4114-86a7-308702115905`
- `nimbus-user-loader` → `07206097-4caf-423b-9eb8-541d4c25da6c`
- `ATO-Tax-Agent` → `7858ecf4-4550-456d-9509-caea0339ec0d`

---

## Step 2: Ask User for Filters (Optional)

Use AskUserQuestion to ask what they want to see:

**Filter Options:**
1. **Status**: All / New / In Progress / Fixed / Won't Fix
2. **Type**: All / Bug / Design / Question / Change
3. **Search**: Keywords to search in descriptions (optional)
4. **Timeframe**: All time / Last 7 days / Last 30 days / This year

---

## Step 3: Build and Execute Query

Based on user's selections, build the appropriate SQL:

**Default Query (All Open):**
```sql
SELECT
    feedback_id::text,
    feedback_type,
    status,
    description,
    created_at,
    updated_at,
    resolved_at,
    (SELECT COUNT(*) FROM claude_pm.project_feedback_comments c
     WHERE c.feedback_id = f.feedback_id) as comments
FROM claude_pm.project_feedback f
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'in_progress')
ORDER BY created_at DESC;
```

**With Type Filter:**
```sql
-- Add to WHERE clause:
AND feedback_type = 'bug'  -- or 'design', 'question', 'change'
```

**With Status Filter:**
```sql
-- Add to WHERE clause:
AND status = 'fixed'  -- or 'new', 'in_progress', 'wont_fix'
```

**With Search:**
```sql
-- Add to WHERE clause:
AND description ILIKE '%search-keyword%'
```

**With Timeframe:**
```sql
-- Add to WHERE clause:
AND created_at > NOW() - INTERVAL '7 days'  -- or '30 days', '1 year'
```

---

## Step 4: Display Results

Format results in a readable table:

```
📋 FEEDBACK LIST - [Project Name]

Filters: [Status: New/In Progress] [Type: All] [Search: none] [Timeframe: All]

Total Results: X items

┌──────────────────────────────────────┬──────────┬──────────┬─────────────┬──────────┬──────────┐
│ ID (first 8 chars)                   │ Type     │ Status   │ Created     │ Comments │ Desc     │
├──────────────────────────────────────┼──────────┼──────────┼─────────────┼──────────┼──────────┤
│ a1b2c3d4                             │ 🐛 Bug   │ New      │ 2025-11-05  │ 2        │ Login... │
│ b2c3d4e5                             │ 🎨 Design│ Progress │ 2025-11-04  │ 5        │ Export.. │
└──────────────────────────────────────┴──────────┴──────────┴─────────────┴──────────┴──────────┘

---
View details: SELECT * FROM claude_pm.project_feedback WHERE feedback_id = 'full-uuid'::uuid
View comments: SELECT * FROM claude_pm.project_feedback_comments WHERE feedback_id = 'full-uuid'::uuid ORDER BY created_at
```

---

## Step 5: Offer Actions

Present common next actions:

```
What would you like to do?

1. View details of specific item (provide ID)
2. Update status
3. Add comment
4. Create new feedback
5. Export to CSV (if needed)

Commands:
- /feedback-check - Quick view of open items
- /feedback-create - Create new item
```

---

## Advanced Queries

**Get Statistics:**
```sql
-- Count by status and type
SELECT
    feedback_type,
    status,
    COUNT(*) as count
FROM claude_pm.project_feedback
WHERE project_id = 'PROJECT-ID'::uuid
GROUP BY feedback_type, status
ORDER BY feedback_type, status;
```

**Get Most Discussed:**
```sql
-- Items with most comments
SELECT
    f.feedback_id::text,
    f.feedback_type,
    f.description,
    COUNT(c.comment_id) as comment_count
FROM claude_pm.project_feedback f
LEFT JOIN claude_pm.project_feedback_comments c ON f.feedback_id = c.feedback_id
WHERE f.project_id = 'PROJECT-ID'::uuid
GROUP BY f.feedback_id, f.feedback_type, f.description
HAVING COUNT(c.comment_id) > 0
ORDER BY comment_count DESC
LIMIT 10;
```

**Get Aging Report:**
```sql
-- How long items have been open
SELECT
    feedback_id::text,
    feedback_type,
    status,
    description,
    created_at,
    EXTRACT(DAY FROM (NOW() - created_at)) as days_open
FROM claude_pm.project_feedback
WHERE project_id = 'PROJECT-ID'::uuid
  AND status IN ('new', 'in_progress')
ORDER BY days_open DESC;
```

---

## Export Options

**CSV Export (if requested):**
```sql
-- Copy to CSV
COPY (
    SELECT
        feedback_id,
        feedback_type,
        status,
        description,
        created_at,
        updated_at,
        resolved_at
    FROM claude_pm.project_feedback
    WHERE project_id = 'PROJECT-ID'::uuid
    ORDER BY created_at DESC
) TO 'C:\Projects\{project}\feedback_export.csv' WITH CSV HEADER;
```

---

## Error Handling

**If no results:**
```
✅ No feedback items match your filters.

Try:
- Broaden status filter (include 'fixed' items)
- Remove search keywords
- Expand timeframe
```

**If project not found:**
- Guide to project registration
- Link to feedback-system-guide.md

---

**Quick Usage Examples:**

1. "Show all bugs" → Type filter: bug, Status: all
2. "What's fixed this week?" → Status: fixed, Timeframe: 7 days
3. "Search for login issues" → Search: "login"
4. "Show everything" → All filters: All
