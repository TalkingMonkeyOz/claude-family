# Phone-a-Friend MCP Analysis

**Date:** 2025-12-01
**Author:** claude-code-unified
**Status:** EVALUATED - NOT RECOMMENDED

---

## What It Does

**Phone-a-Friend MCP** is an AI-to-AI consultation system that routes queries through OpenRouter to external AI models (GPT-4, Claude, Gemini, etc.). The primary AI sends context + a task, gets back a response from the "friend" AI.

**Key features:**
- Single tool: `phone_a_friend(all_related_context, any_additional_context, task)`
- Designed for "long context reasoning" (100k+ tokens)
- Uses OpenRouter as the routing layer

**Source:** https://mcp.so/server/phone-a-friend-mcp-server/abhishekbhakat

---

## Context Usage

**High context cost** - by design, it sends "all related context" to the external AI. This is the opposite of what we want when tokens are low.

---

## Comparison to Our Orchestrator

| Aspect | Phone-a-Friend | Our Orchestrator |
|--------|----------------|------------------|
| **Purpose** | Deep analysis via external AI | Spawn isolated Claude agents |
| **Context** | Sends ALL context to friend | Each agent starts fresh (isolated) |
| **Cost** | External API costs (OpenRouter) | Same Claude API, but isolated |
| **Communication** | One-shot query/response | Messaging system (inbox, broadcast) |
| **Persistence** | None | DB-backed messages |

---

## Assessment: Would It Help Us?

**No.** Here's why:

1. **We already have inter-Claude messaging** via `instance_messages` table and orchestrator tools (`send_message`, `check_inbox`, `broadcast`)

2. **Our agents are isolated by design** - Phone-a-Friend sends full context, ours spawn fresh agents with only the task description

3. **External API dependency** - Adds OpenRouter as another cost/failure point

4. **Different problem space** - Phone-a-Friend is for "I need a second opinion on this complex analysis." Our system is for "Spawn a specialist to do this work."

---

## What We're Missing (That Phone-a-Friend Hints At)

The concept of **synchronous consultation** is interesting:
- Currently our orchestrator spawns agents that work and return results
- Phone-a-Friend is more like "pause, ask an expert, continue"

If we wanted this, we could add a `consult_expert` tool to orchestrator that:
1. Sends a focused question (not full context) to a specialist agent
2. Waits for response
3. Returns just the answer

But this is different from what Phone-a-Friend does, and our current spawn model already handles specialist work.

---

## Verdict

**Not needed.** Our orchestrator already handles inter-Claude coordination better:
- Isolated agents (low context per agent)
- Persistent messaging (survives crashes)
- DB-backed audit trail
- No external API dependency

The only gap is real-time "consultation" which we could add if needed, but it's not a priority vs. the schema consolidation and event-driven scheduling work underway.

---

## Future Consideration

If we ever need "phone a friend" style consultation:
1. Add `consult_specialist` tool to orchestrator
2. Keep context minimal (just the question)
3. Use our existing agent spawning (not external APIs)
4. Log consultation to activity_feed

**Priority:** Low - current spawn model sufficient

---

**Document Version:** 1.0
