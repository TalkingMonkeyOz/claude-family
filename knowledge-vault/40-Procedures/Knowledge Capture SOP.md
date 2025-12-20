---
projects:
- claude-family
synced: true
synced_at: '2025-12-20T23:29:45.922661'
tags:
- sop
- knowledge
- procedures
---

# Knowledge Capture SOP

Standard procedure for capturing and organizing knowledge in the Claude Family vault.

---

## When to Capture Knowledge

Capture knowledge when you encounter:

| Type | Example | Priority |
|------|---------|----------|
| **Gotcha** | API quirk, unexpected behavior | High |
| **Solution** | Working code pattern, fix | High |
| **Decision** | Why we chose X over Y | Medium |
| **Process** | How to do recurring task | Medium |
| **Reference** | API docs, schema info | Low |

---

## Quick Capture (Inbox)

When you don't have time to organize:

### Step 1: Create Note

Create file in `00-Inbox/` with basic frontmatter:

```markdown
---
projects:
- your-project
---

# Quick Note Title

Your content here. Include:
- What you learned
- Why it matters
- Code examples if relevant
```

### Step 2: Save and Continue

You can organize later. The key is capturing before you forget.

---

## Organized Capture

When you have time to do it right:

### Step 1: Choose Location

| If it's... | Put it in... |
|------------|--------------|
| Project-specific insight | `10-Projects/{project}/` |
| Domain knowledge (API, DB) | `20-Domains/{domain}/` |
| Bug/gotcha you hit | `30-Patterns/gotchas/` |
| Solution you found | `30-Patterns/solutions/` |
| Procedure to follow | `40-Procedures/` |
| Core system doc | `Claude Family/` |

### Step 2: Create with Full Frontmatter

```yaml
---
projects:
- claude-family
tags:
- relevant-tag
- another-tag
synced: false
---
```

### Step 3: Follow Template

Use the standard structure from [[Documentation Standards]]:

1. Overview section
2. Main content with tables/code
3. Related documents with wiki-links
4. Version footer

### Step 4: Add Cross-References

Link to related documents:

```markdown
## Related Documents

- [[Existing Doc]] - How it relates
- [[Another Doc]] - Why it's relevant
```

### Step 5: Sync to Database

```bash
python scripts/sync_obsidian_to_db.py
```

Verify sync worked:

```sql
SELECT title, updated_at
FROM claude.knowledge
WHERE title LIKE '%Your Doc Title%';
```

---

## Capture Checklist

Before considering a capture complete:

- [ ] Frontmatter has `projects:` array
- [ ] Content is scannable (headers, bullets, tables)
- [ ] Code examples are tested/working
- [ ] Related docs are wiki-linked
- [ ] Version footer is present
- [ ] Synced to database

---

## Session End Capture

At the end of every significant session:

### What to Capture

| Type | Put in... |
|------|-----------|
| Gotcha you hit | `30-Patterns/gotchas/{topic}.md` |
| Pattern you discovered | `30-Patterns/solutions/{topic}.md` |
| Project-specific learning | `10-Projects/{project}/{topic}.md` |

### Quick Template for Session Learnings

```markdown
---
projects:
- your-project
tags:
- session-learning
synced: false
---

# {Brief Title}

**Session**: {date}
**Context**: {what you were doing}

## What Happened

{Description of the issue/discovery}

## Solution/Learning

{What you learned or how you fixed it}

## Code Example

```{language}
// Working code
```

---

**Created**: {date}
```

---

## Organizing Inbox

Periodically review `00-Inbox/` and move notes:

### Step 1: Review Each Note

Ask: What type of knowledge is this?

### Step 2: Move to Proper Location

```bash
# In Obsidian: drag and drop
# Or: cut/paste in file explorer
```

### Step 3: Enrich Content

- Add proper frontmatter
- Expand with context
- Add wiki-links
- Add version footer

### Step 4: Re-sync

```bash
python scripts/sync_obsidian_to_db.py
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Note not syncing | Check frontmatter YAML is valid |
| Wrong project filter | Update `projects:` array |
| Note seems lost | Check `00-Inbox/` or search vault |
| Duplicate content | Search before creating, merge if found |

---

## Related Documents

- [[Documentation Standards]] - Formatting guidelines
- [[Knowledge System]] - How sync works
- [[session End]] - End-of-session checklist

---

**Version**: 1.0
**Created**: 2025-12-20
**Updated**: 2025-12-20
**Location**: knowledge-vault/40-Procedures/Knowledge Capture SOP.md