**MANDATORY END-OF-SESSION CHECKLIST**

Before ending this session, complete ALL steps below using MCP tools (no raw SQL).

---

## Step 1: Review Session

Summarize what happened:
- What was accomplished this session?
- What tasks were completed?
- What decisions were made?
- What's left for next session?

## Step 2: Capture Knowledge (if applicable)

For each **significant** learning, pattern, or decision discovered this session, call:

```
store_knowledge(
    title="Short descriptive title",
    description="Detailed explanation of the learning",
    knowledge_type="learned|pattern|gotcha|preference|fact|procedure",
    knowledge_category="relevant-domain",
    source="session"
)
```

**Only capture reusable knowledge** - skip session-specific context that won't help future sessions.

## Step 3: Close Session

Call `end_session()` with ALL parameters:

```
end_session(
    summary="1-2 sentence recap of what was accomplished",
    next_steps=["First thing to do next session", "Second thing"],
    tasks_completed=["Task 1 description", "Task 2 description"],
    learnings=["Key learning 1", "Key learning 2"]
)
```

**Note**: Learnings passed here are automatically stored as searchable knowledge entries with embeddings. Keep them specific and reusable (min 20 chars each, max 5).

## Step 4: Report Results

Show the user what was saved:
- Session closed (session_id)
- Conversation extracted (turn count)
- Knowledge entries created (count)
- Next steps saved

---

## What NOT to Do

- Do NOT use raw SQL to update sessions or store knowledge
- Do NOT reference `claude_family.*` schema (use `claude.*` via MCP tools)
- Do NOT skip knowledge capture if you learned something reusable
- Do NOT store trivial or session-specific facts as knowledge

## Cost of Skipping

- Next Claude spends 30 minutes rediscovering your solution
- Same bug gets solved 3 times by different Claudes
- Institutional knowledge stays at zero
- User gets frustrated repeating themselves

**Remember**: Knowledge capture is how the Claude Family learns and grows.
