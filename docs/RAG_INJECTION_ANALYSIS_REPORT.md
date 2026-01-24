# RAG Hook Injection System Analysis

**Date**: 2026-01-19
**Analyst**: analyst-sonnet
**Scope**: Effectiveness of automatic RAG context injection via `rag_query_hook.py`

---

## Executive Summary

The RAG hook injection system is **operational and working well** with 770 queries logged in the past 30 days. However, there are significant gaps in what's being surfaced and opportunities to improve relevance. The system is successfully injecting vault documentation but is **NOT surfacing features or build_tasks**, and knowledge recall has low confidence levels.

**Key Metrics**:
- **770 queries** processed in 30 days
- **Average latency**: 881ms (needs optimization)
- **Average similarity**: 0.47 (medium quality)
- **High quality matches** (≥0.70): 0%
- **Medium quality matches** (0.50-0.69): 31%
- **Low quality matches** (0.30-0.49): 63%
- **Zero results**: 3% of queries

---

## WORKING WELL ✅

### 1. Vault Documentation Surfacing
- **8,289 vault chunks** embedded across 587 documents
- Successfully returning 2-3 relevant docs per query
- Most surfaced docs align with user needs:
  - Session lifecycle docs (94 hits for "Session User Story - Resume Session")
  - Infrastructure docs (Add MCP Server SOP: 38 hits)
  - Procedure documentation is discoverable

### 2. Knowledge Table Structure
- **290+ knowledge entries** embedded and queryable
- Dominant types: patterns (178), gotchas (35), best-practices (17)
- Access tracking working (last_accessed_at updates correctly)
- Confidence levels tracked (though many are low at 5-10%)

### 3. Implicit Feedback Detection
- **51 rephrase detections** with 78% avg confidence
- **3 explicit negative signals** ("that didn't work", etc.)
- Quality tracking identifies problematic docs (6 docs flagged for review after 3+ misses)

### 4. Session Context Detection
- Session keywords detected in **4.7% of queries** (36/770)
- Keywords like "where was i", "what todos", "resume" trigger context loading
- Function `get_session_context()` pulls todos, focus, last session summary

### 5. Vocabulary Expansion
- `expand_query_with_vocabulary()` translates user phrases to canonical concepts
- Example: "spin up" → "create", improving semantic matching

### 6. Logging and Observability
- All queries logged to `claude.rag_usage_log` with:
  - Query text, results count, top similarity, latency
  - Docs returned (array), session_id
- Comprehensive hook logging to `~/.claude/hooks.log`

---

## ISSUES FOUND ❌

### 1. **CRITICAL: Features and Build Tasks NOT Being Surfaced**

**Finding**: The system has 67 feature documents embedded (`doc_source='feature'`) but they are **NOT being queried by the RAG hook**.

**Evidence**:
```sql
-- Features embedded in vault_embeddings
SELECT COUNT(*) FROM claude.vault_embeddings WHERE doc_source = 'feature';
-- Result: 67 feature docs across 6 projects

-- BUT: features/build_tasks tables have NO embedding column
SELECT column_name FROM information_schema.columns
WHERE table_name = 'features' AND column_name LIKE '%embed%';
-- Result: EMPTY (no embedding column exists)
```

**Impact**: Users asking "what should I work on?" or "what features are planned?" won't see relevant features or build tasks in their context.

**Root Cause**:
- Features are only embedded as *documents* in `vault_embeddings` (from plan_data JSONB)
- The RAG hook queries `vault_embeddings` BUT does NOT query `claude.features` or `claude.build_tasks` directly
- No direct feature/task surfacing mechanism exists

---

### 2. **Low Similarity Scores (63% Below 0.50)**

**Finding**: 484 of 770 queries (63%) returned results with similarity **below 0.50**, indicating weak semantic matches.

**Evidence**:
```
High quality (≥0.70): 0 queries (0%)
Medium (0.50-0.69):   238 queries (31%)
Low (0.30-0.49):      484 queries (63%)
```

**Sample weak matches**:
- Query: "its a bit small" → Similarity: 0.48
- Query: "yes add the link" → Similarity: 0.35
- Query: "is this for me or you" → Similarity: 0.38

**Impact**: Irrelevant context injected, increasing noise and token cost.

**Root Cause**:
- Min similarity threshold too low (0.30 for vault, 0.45 for knowledge)
- Short, vague queries match tangentially related docs
- Voyage-3 embeddings may need query reformulation

---

### 3. **Knowledge Entries Have Low Confidence**

**Finding**: 290 knowledge entries exist, but many have **confidence ≤10%**, and only 64 have been applied even once.

**Evidence**:
```
Pattern entries: 178 (avg confidence: 41%)
Gotchas: 35 (avg confidence: 35%)
Best-practices: 17 (avg confidence: 19%)
Troubleshooting: 7 (avg confidence: 8%)

Applied at least once: 64/290 (22%)
Never applied: 226/290 (78%)
```

**Impact**: Low confidence reduces trust; unapplied entries suggest they're not useful or not discoverable.

**Root Cause**:
- Knowledge entries created during development with arbitrary confidence values
- No systematic calibration or testing of confidence levels
- `times_applied` not being incremented consistently

---

### 4. **High Latency (881ms Average)**

**Finding**: Average RAG query latency is **881ms**, with some queries taking 1-2 seconds.

**Evidence**:
```
Average latency: 881ms
Vault query examples:
  - "application project implementation..." → 1,948ms
  - "infrastructure project planning..." → 1,175ms
  - "add the rust backend commands..." → 1,214ms
```

**Impact**: Noticeable delay before Claude receives context, especially on complex queries.

**Root Cause**:
- Voyage AI API call (~200-300ms)
- Database query with pgvector similarity search (~300-500ms)
- Network latency and JSON serialization
- No query result caching

---

### 5. **Session Context Not Always Injected**

**Finding**: Session context is only injected when **specific keywords** are detected (4.7% of queries).

**Evidence**:
```python
SESSION_KEYWORDS = [
    "where was i", "what was i working on", "resume",
    "what todos", "next steps", "last session", ...
]
```

Only 36 of 770 queries (4.7%) triggered session context loading.

**Impact**:
- Users asking "what's next?" without magic keywords won't get todos/focus
- Missed opportunities to provide relevant session state

**Root Cause**:
- Keyword-based detection is brittle (relies on exact phrases)
- Should use semantic similarity for session-related queries
- Should inject session context more proactively (e.g., first query of session)

---

### 6. **Awesome-Copilot Docs Dominating Results**

**Finding**: The vault contains a large corpus of `awesome-copilot-reference` docs (GitHub Copilot patterns), which frequently appear in results even when not relevant to Claude Family infrastructure.

**Evidence**: Top surfaced docs include:
- `20-Domains/awesome-copilot-reference/agents/atlassian-requirements-to-jira.agent.md` (65 hits)
- `20-Domains/awesome-copilot-reference/agents/terraform-azure-implement.agent.md` (59 hits)
- `20-Domains/awesome-copilot-reference/instructions/power-bi-security-rls-best-practices.instructions.md` (56 hits)

**Impact**: Generic GitHub Copilot patterns crowd out Claude Family-specific knowledge.

**Root Cause**:
- Awesome-copilot docs are numerous and verbose
- No weighting/boosting for Claude Family-specific docs
- No filtering by project relevance

---

### 7. **Doc Quality Tracking Not Actionable**

**Finding**: 6 docs flagged for review after 3+ misses, but no automated remediation or alerts.

**Flagged docs**:
```
- 40-Procedures/Session Lifecycle - Reference.md (4 misses)
- 10-Projects/claude-family/Session User Story - Resume Session.md (6 misses)
- 20-Domains/awesome-copilot-reference/instructions/tasksync.instructions.md (6 misses)
```

**Impact**: Low-quality docs continue to be surfaced, wasting tokens.

**Root Cause**:
- No integration with alerting system
- No automated adjustment of similarity thresholds for flagged docs
- Manual review required

---

## SPECIFIC RECOMMENDATIONS 🎯

### Priority 1: Surface Features and Build Tasks (CRITICAL)

**Problem**: Features and build_tasks are not surfaced in RAG results.

**Solution**:
1. **Add direct feature/task query** to `rag_query_hook.py`:
   ```python
   def query_features_and_tasks(user_prompt, project_name):
       # Query claude.features WHERE status IN ('planned', 'in_progress')
       # Query claude.build_tasks WHERE status = 'pending' AND NOT blocked
       # Return top 2-3 matches by similarity to user prompt
   ```

2. **Inject feature context** alongside vault and knowledge:
   ```python
   combined_context_parts = []
   if session_context:
       combined_context_parts.append(session_context)
   if feature_context:  # NEW
       combined_context_parts.append(feature_context)
   if knowledge_context:
       combined_context_parts.append(knowledge_context)
   if rag_context:
       combined_context_parts.append(rag_context)
   ```

3. **Create embeddings for features/tasks** on INSERT/UPDATE:
   - Add `embedding` column to `claude.features` and `claude.build_tasks`
   - Create trigger to auto-generate embedding from `feature_name + description`
   - Query these tables directly (not just vault_embeddings)

**Expected Impact**: Users asking "what should I work on?" will see relevant features and ready tasks.

---

### Priority 2: Raise Similarity Thresholds

**Problem**: 63% of queries return low-quality matches (similarity <0.50).

**Solution**:
1. **Increase minimum thresholds**:
   ```python
   # Current
   min_similarity_vault = 0.30
   min_similarity_knowledge = 0.45

   # Recommended
   min_similarity_vault = 0.45  # +0.15
   min_similarity_knowledge = 0.55  # +0.10
   ```

2. **Add dynamic threshold adjustment**:
   - If top result <0.50, return nothing (better no context than bad context)
   - Log "no high-quality results" to rag_usage_log

3. **Monitor impact**: Track queries with zero results and adjust if too high (target <10%).

**Expected Impact**: 30-40% reduction in low-quality injections, lower token waste.

---

### Priority 3: Optimize Latency (Target <500ms)

**Problem**: Average latency 881ms is too high for inline injection.

**Solution**:
1. **Cache embeddings** for common queries:
   ```python
   # LRU cache for query embeddings (TTL 5 minutes)
   from functools import lru_cache

   @lru_cache(maxsize=100)
   def cached_embedding(query_text):
       return generate_embedding(query_text)
   ```

2. **Parallel database queries**:
   ```python
   # Query vault_embeddings and knowledge concurrently
   import asyncio
   vault_results, knowledge_results = await asyncio.gather(
       query_vault_async(...),
       query_knowledge_async(...)
   )
   ```

3. **Reduce top_k**:
   - Current: top_k=3 for vault, top_k=2 for knowledge
   - Recommended: top_k=2 for vault, top_k=1 for knowledge (if high similarity)

4. **Add timeout**: If query takes >1 second, return empty context (don't block user)

**Expected Impact**: 40-50% latency reduction (target 400-500ms).

---

### Priority 4: Proactive Session Context Injection

**Problem**: Session context only injected for 4.7% of queries (keyword-based detection).

**Solution**:
1. **Inject session context on first query of session**:
   ```python
   # Check if this is first query (no prior rag_usage_log entries for session_id)
   if is_first_query(session_id):
       session_context = get_session_context(project_name)
   ```

2. **Use semantic similarity** for session-related queries:
   ```python
   # Embed session keywords, compare to user prompt
   SESSION_EMBEDDING = generate_embedding("session resume todos what's next")
   query_similarity = cosine_similarity(query_embedding, SESSION_EMBEDDING)
   if query_similarity >= 0.60:
       session_context = get_session_context(project_name)
   ```

3. **Add "resume" mode** flag:
   - If user runs `/session-resume`, set env var `CLAUDE_RESUME_MODE=true`
   - RAG hook injects session context for next 3 queries

**Expected Impact**: 2-3x increase in session context injection (from 5% to 10-15%).

---

### Priority 5: Downweight Awesome-Copilot Docs

**Problem**: Generic GitHub Copilot patterns crowding out Claude Family docs.

**Solution**:
1. **Boost Claude Family docs** by 1.5x similarity:
   ```python
   if doc_path.startswith('Claude Family/') or doc_path.startswith('40-Procedures/'):
       similarity_score *= 1.5  # Boost
   elif doc_path.startswith('20-Domains/awesome-copilot-reference/'):
       similarity_score *= 0.7  # Penalize
   ```

2. **Filter by project relevance**:
   - Add `applies_to_projects` metadata to vault_embeddings
   - Prioritize docs tagged with current project_name

3. **Separate "general patterns" from "project-specific"**:
   - Query project-specific docs first (top_k=2)
   - Then query general patterns (top_k=1)

**Expected Impact**: 50% increase in Claude Family-specific doc hits.

---

### Priority 6: Calibrate Knowledge Confidence Levels

**Problem**: Many knowledge entries have low confidence (≤10%) and are rarely applied.

**Solution**:
1. **Audit and recalibrate**:
   ```sql
   -- Set baseline confidence based on knowledge_type
   UPDATE claude.knowledge
   SET confidence_level = CASE knowledge_type
       WHEN 'pattern' THEN 70
       WHEN 'gotcha' THEN 80
       WHEN 'best-practice' THEN 75
       WHEN 'troubleshooting' THEN 60
       ELSE confidence_level
   END
   WHERE confidence_level < 30;
   ```

2. **Auto-increment confidence** when applied successfully:
   ```python
   # In mark_knowledge_applied()
   if success:
       cur.execute("""
           UPDATE claude.knowledge
           SET confidence_level = LEAST(confidence_level + 5, 100)
           WHERE knowledge_id = %s
       """, (knowledge_id,))
   ```

3. **Filter by confidence**:
   ```python
   # Only return knowledge with confidence ≥50%
   AND confidence_level >= 50
   ```

**Expected Impact**: Higher signal-to-noise ratio in knowledge recalls.

---

### Priority 7: Automate Doc Quality Review

**Problem**: 6 docs flagged for review, but no automated action.

**Solution**:
1. **Alert on flagged docs**:
   ```python
   # In update_doc_quality()
   if flagged:
       send_message(
           to_project='claude-family',
           subject='Doc Quality Alert',
           body=f'{doc_path} flagged after {miss_count} misses'
       )
   ```

2. **Auto-adjust thresholds**:
   ```python
   # If doc has quality_score < 0.3, require higher similarity to return
   if doc_quality_score < 0.3:
       required_similarity = 0.60  # Raise from 0.45
   ```

3. **Quarantine low-quality docs**:
   ```sql
   -- After 5 misses, exclude from RAG results for 7 days
   UPDATE claude.rag_doc_quality
   SET quarantined_until = NOW() + INTERVAL '7 days'
   WHERE miss_count >= 5;
   ```

**Expected Impact**: Reduced noise from repeatedly surfaced but unhelpful docs.

---

## Similarity Threshold Analysis

**Current thresholds**:
- Vault: 0.30 (too low)
- Knowledge: 0.45 (borderline)

**Recommended thresholds** based on data:
| Threshold | Queries Returned | Quality |
|-----------|------------------|---------|
| ≥0.30 | 746 (97%) | 63% low quality |
| ≥0.45 | 500 (65%) | 40% low quality (estimated) |
| ≥0.50 | 238 (31%) | Mostly medium/high quality |
| ≥0.60 | ~50 (6%) | High quality only |

**Recommendation**:
- **Vault**: Set min_similarity = **0.45** (sweet spot: 65% recall, 40% low quality)
- **Knowledge**: Set min_similarity = **0.55** (tighter filter for high-confidence)
- **Adaptive**: If top result <0.50, return nothing

---

## Proposed RAG Hook Flow (Updated)

```
┌────────────────────────────────────────────────────────────────┐
│ UserPromptSubmit Hook Triggered                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 1. Implicit Feedback Detection                                 │
│    - Check for "that didn't work" → Mark docs as miss          │
│    - Check for rephrase → Flag previous results                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 2. Session Context (PROACTIVE)                                 │
│    - If first query OR session keywords → Load todos/focus     │
│    - Semantic similarity to "resume" embedding                 │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 3. Feature/Task Context (NEW!)                                 │
│    - Query claude.features (status='in_progress')              │
│    - Query claude.build_tasks (status='pending', not blocked)  │
│    - Return top 2 by semantic similarity                       │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 4. Knowledge Recall (TIGHTENED)                                │
│    - Query claude.knowledge (min_similarity=0.55)              │
│    - Filter by confidence_level ≥ 50%                          │
│    - Return top 1 (down from 2)                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 5. Vault RAG (OPTIMIZED)                                       │
│    - Query vault_embeddings (min_similarity=0.45)              │
│    - Boost Claude Family docs by 1.5x                          │
│    - Penalize awesome-copilot by 0.7x                          │
│    - Return top 2 (down from 3)                                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 6. Combine and Inject                                          │
│    Priority: Session → Features → Knowledge → Vault            │
│    Max total: ~4000 chars (down from unlimited)                │
└────────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────────┐
│ 7. Log and Track                                               │
│    - Log to rag_usage_log with all context types              │
│    - Track latency, similarity, docs returned                 │
└────────────────────────────────────────────────────────────────┘
```

---

## Implementation Priority

| Priority | Recommendation | Effort | Impact |
|----------|---------------|--------|--------|
| **P0** | Surface features/tasks | High (2-3 days) | Critical - major missing feature |
| **P1** | Raise similarity thresholds | Low (30 min) | High - immediate quality improvement |
| **P1** | Optimize latency (caching) | Medium (4-6 hrs) | High - noticeable UX improvement |
| **P2** | Proactive session context | Low (1-2 hrs) | Medium - better resume flow |
| **P2** | Downweight awesome-copilot | Low (1 hr) | Medium - more relevant results |
| **P3** | Calibrate knowledge confidence | Medium (2-3 hrs) | Medium - higher trust in recalls |
| **P3** | Automate doc quality review | Medium (3-4 hrs) | Low - reduces manual work |

**Total Effort**: ~3-4 days of focused development

---

## Summary

The RAG hook injection system is **working but incomplete**. It successfully surfaces vault documentation with reasonable latency, but critical gaps exist:

1. ❌ **Features and build tasks are NOT surfaced** (most critical issue)
2. ⚠️ **Low similarity scores** (63% below 0.50) inject noisy context
3. ⚠️ **High latency** (881ms avg) impacts UX
4. ⚠️ **Session context** only triggered 5% of the time (too rare)
5. ⚠️ **Generic docs** (awesome-copilot) crowd out project-specific knowledge

**Key Strengths**:
- Implicit feedback detection working
- Comprehensive logging and observability
- Vocabulary expansion improving recall
- Doc quality tracking functional

**Next Steps**:
1. Implement P0: Feature/task surfacing (critical)
2. Implement P1: Threshold tuning + latency optimization (quick wins)
3. Monitor impact via rag_usage_log for 1 week
4. Iterate on P2/P3 based on user feedback

---

**Version**: 1.0
**Created**: 2026-01-19
**Location**: docs/RAG_INJECTION_ANALYSIS_REPORT.md
