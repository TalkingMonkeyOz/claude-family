# ANTI-HALLUCINATION PROTOCOL
**Created:** 2025-10-19
**Purpose:** Prevent future bloat. Keep system lean FOREVER.

---

## What Just Happened (The Lesson)

**Before cleanup:**
- 55 database tables
- 45 empty tables (82% hallucination rate)
- CLAUDE.md = 659 lines
- Diana loaded 30K+ tokens before user spoke
- Result: Lost track, confused, wasted tokens

**After cleanup:**
- 10 database tables
- 0 empty tables
- CLAUDE.md = 200 lines
- Startup context = ~5K tokens
- Result: Focused, fast, on-track

**The Pattern:** Build for "future features" → 90% never used → context bloat → AI loses track

---

## The Iron Laws (NEVER BREAK THESE)

### Law 1: NO SPECULATIVE BUILDING
❌ "Let's create tables for features we might need"
❌ "This architecture will be useful later"
❌ "I'll add extra columns just in case"

✅ "User asked for X, build ONLY X"
✅ "When user asks for Y, add Y then"

**Rule:** If user didn't explicitly request it, DON'T BUILD IT.

### Law 2: NO EMPTY TABLES
Empty table = hallucination.

**Before creating ANY table:**
```sql
-- Ask: Will this be populated in the next 5 minutes?
-- NO → Don't create it
-- YES → Create it AND populate it immediately
```

**Audit quarterly:**
```sql
SELECT tablename, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname = 'public' AND n_live_tup = 0;
-- If any results → DROP THEM
```

### Law 3: CLAUDE.md ≤ 250 LINES
Context is precious. Every line costs tokens.

**What belongs in CLAUDE.md:**
- Identity (name, role, UUID)
- Database connection (what tables ACTUALLY EXIST)
- MCP protocol (3-sentence summary)
- Critical gotchas (must-know issues)

**What DOESN'T belong:**
- Elaborate workflows (put in MCPs)
- Detailed examples (put in shared_knowledge table)
- "Helpful" explanations (if we need it, query MCP)
- Environment specs (query when needed)

**Audit monthly:** If CLAUDE.md > 250 lines, find what to move to MCPs.

### Law 4: STORE BIG, LOAD SMALL
**Industry standard** (Mem0, MCP Memory, LangGraph):
- Store 1000 patterns in database
- Load 10 relevant ones per session
- Result: 90% token savings

**NOT this:**
- Store 1000 patterns in database
- Load all 1000 in CLAUDE.md
- Result: Context explosion

**Implementation:**
- Use `mcp__memory__search_nodes(query="relevant-keywords")` at session start
- Don't load everything in CLAUDE.md
- Query on-demand, not upfront

### Law 5: NO "AI COMPANY" ARCHITECTURE
**The Dream:** AI agents coordinate via elaborate orchestration system

**The Reality:** 45 empty tables, Diana loses track

**What Actually Works:**
- User talks to Claude directly
- Claude logs to postgres (session_history, shared_knowledge)
- Claude queries MCPs for context
- No orchestration layer, no departments, no routing

**When user wants multi-agent:** Use Task tool to spawn focused sub-agents, not persistent infrastructure.

---

## Enforcement Checklist

### Weekly Audit (Every Friday)
```sql
-- 1. Check for empty tables
SELECT tablename, n_live_tup
FROM pg_stat_user_tables
WHERE schemaname IN ('claude_family', 'public') AND n_live_tup = 0;
-- Drop any results

-- 2. Check total table count
SELECT schemaname, COUNT(*)
FROM pg_stat_user_tables
WHERE schemaname IN ('claude_family', 'public')
GROUP BY schemaname;
-- public should be ≤ 10 tables
```

```bash
# 3. Check CLAUDE.md line count
wc -l C:/Projects/claude-family/CLAUDE.md
# Should be ≤ 250 lines
```

### Monthly Deep Audit
1. **Database review:** Which tables were accessed in past 30 days?
   - Unused → Mark for deletion
   - Used < 5 times → Candidate for deletion

2. **CLAUDE.md review:** What sections were actually referenced?
   - Unused sections → Move to separate docs or MCPs

3. **Memory MCP review:** Query top 20 most-accessed entities
   - These are your "hot" knowledge
   - Everything else = cold storage (fine)

---

## Red Flags (Stop Immediately If You See These)

🚩 **Creating table "for later"** → NO. Build when needed.
🚩 **"This will be useful for future features"** → NO. YAGNI principle.
🚩 **CLAUDE.md growing past 300 lines** → STOP. What can you move to MCPs?
🚩 **Multiple empty tables in database** → STOP. Drop them now.
🚩 **"Let's build an architecture for..."** → STOP. User asked for what exactly?

---

## The Recovery Plan (When Bloat Returns)

**Signs bloat is back:**
- Claude loses track of conversation
- Startup takes >10 seconds
- CLAUDE.md >300 lines
- >15 tables in public schema

**Recovery steps:**
1. Run table audit (see above)
2. Drop all empty tables
3. Slim CLAUDE.md (see Law 3)
4. Move knowledge to MCPs
5. Test: Does Claude stay on track now?

**Target metrics:**
- CLAUDE.md: ≤250 lines
- public schema: ≤10 tables
- All tables have data (zero empty)
- Startup context: ~5K tokens

---

## What Success Looks Like

### Good Session Pattern
1. User: "Help me with X"
2. Claude: Queries memory MCP for "X-related patterns" (finds 3)
3. Claude: Queries postgres for "work_packages WHERE name ILIKE '%X%'" (finds 1)
4. Claude: Works on X
5. Claude: Stores result in shared_knowledge + memory MCP
6. Session log updated

**Token cost:** ~5K startup, ~20K work, ~2K logging = 27K total

### Bad Session Pattern (What We're Preventing)
1. Claude loads 50 table schemas (15K tokens)
2. Claude loads 659-line CLAUDE.md (25K tokens)
3. Claude loads "AI Company" architecture (10K tokens)
4. **50K tokens used before user says anything**
5. User: "Help me with X"
6. Claude: Confused, loses track, hallucinates

**Token cost:** 50K startup + 30K confused wandering = 80K wasted

---

## The Commitment

**WE WILL NEVER AGAIN:**
- Create empty tables "for future use"
- Build elaborate architectures before we have use cases
- Load everything into CLAUDE.md "just in case"
- Over-engineer solutions to simple problems

**WE WILL ALWAYS:**
- Build what's requested, when it's requested
- Query MCPs for context (don't preload everything)
- Keep CLAUDE.md under 250 lines
- Audit and delete bloat regularly

---

## Version History

**v1.0 (2025-10-19):** Initial protocol after 45-table cleanup
- Dropped 82% of tables
- Slimmed CLAUDE.md by 70%
- Established iron laws
- Created enforcement checklists

**Future versions:** Update when we discover new bloat patterns to prevent.

---

**This document is NON-NEGOTIABLE.**

If future Claude proposes violating these laws, **STOP and re-read this file.**

**The bloat will try to return. This protocol prevents it. Forever.**
