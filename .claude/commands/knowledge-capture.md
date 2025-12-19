# Knowledge Capture

Capture a new piece of knowledge from this session to the Obsidian vault.

## Instructions

When the user runs `/knowledge-capture`, help them document something they learned:

1. **Ask what they learned** - What insight, pattern, gotcha, or solution did they discover?

2. **Categorize it**:
   - `pattern` - A reusable approach or technique
   - `gotcha` - Something that trips you up (non-obvious behavior)
   - `solution` - A proven fix for a specific problem
   - `api-reference` - API quirk or documentation
   - `best-practice` - Optimal approach discovered

3. **Identify the domain**:
   - Which project? (nimbus-import, ato-tax-agent, mission-control-web)
   - Which domain? (APIs, Database, Frontend, Testing)

4. **Create the file** in the Obsidian vault:
   - Location: `C:\Projects\claude-family\knowledge-vault\00-Inbox\`
   - Filename: `{slug-title}.md`
   - Use the appropriate template from `_templates/`

5. **Format**:
```markdown
---
title: {Clear descriptive title}
category: {domain like nimbus-api, database, frontend}
type: {pattern|gotcha|solution|api-reference|best-practice}
tags: [{relevant}, {tags}]
confidence: {60-100 based on how certain this is}
projects: [{project-names}]
created: {today's date}
synced: false
---

# {Title}

## Summary
{1-2 sentence summary}

## Details
{Full explanation}

## Code Example (if applicable)
```{language}
// Example code
```

## Related
- [[Related topic if any]]
```

6. **Confirm** the knowledge was saved and remind them to run `python scripts/sync_obsidian_to_db.py` to sync to database.

## Example

User: `/knowledge-capture`
Claude: "What did you learn today that's worth remembering?"
User: "Nimbus API returns 500 errors if you send UTC times in the wrong format"
Claude: [Creates file in 00-Inbox with gotcha template, asks for more details]
