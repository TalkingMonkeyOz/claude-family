# Process Router LLM Enhancement Plan

## Executive Summary

Enhance the process_router.py with LLM-based intent classification to improve trigger matching accuracy while maintaining cost efficiency.

**Problem**: Current regex/keyword matching misses natural language variations (e.g., "there is a bug" vs "fix the bug")

**Solution**: Hybrid approach - fast regex first, LLM fallback for unmatched prompts

**Cost**: ~$0.53/month for 1000 prompts/day (assuming 10% fallback rate)

---

## Current System Analysis

### Strengths
- Fast regex/keyword matching (~1ms, $0 cost)
- 43 active triggers across 6 categories (dev, doc, data, project, comm, qa)
- Well-structured database (process_registry, process_triggers, process_steps)
- Priority-based matching (1-8, lower = higher priority)

### Weaknesses
- Brittle pattern matching
- Natural language variations missed
- Cannot understand semantic intent
- Examples of failures:
  * "there is a bug" ❌ vs "fix the bug" ✅
  * "I found a bug" ❌ vs "getting error" ✅
  * "create new feature" ✅ vs "I need to add functionality" ❌

---

## Proposed Architecture

### Multi-Tier Matching Strategy

```
User Prompt
    ↓
┌─────────────────────────────────────────┐
│ TIER 1: Fast Regex/Keywords (0-1ms)    │
│ - Current implementation                 │
│ - High priority triggers (1-3)          │
│ - Cost: $0                              │
└─────────────────────────────────────────┘
    ↓ (if no match)
┌─────────────────────────────────────────┐
│ TIER 2: LLM Classification (200-500ms)  │
│ - Call Claude Haiku                     │
│ - Semantic intent understanding         │
│ - Cost: ~$0.0002 per call               │
└─────────────────────────────────────────┘
    ↓
Return matches or empty result
```

### Benefits
- ✅ Fast path for 90% of cases (regex)
- ✅ Intelligent fallback for edge cases (LLM)
- ✅ Cost-efficient (only pay when needed)
- ✅ Better user experience (catches variations)

---

## LLM Classification Design

### 1. Classification Prompt

```python
CLASSIFICATION_PROMPT_TEMPLATE = """You are a task classifier for a development workflow system.

Analyze the user's prompt and match it to relevant processes.

USER PROMPT: "{user_prompt}"

AVAILABLE PROCESSES:
{processes_json}

INSTRUCTIONS:
1. Identify the user's primary intent
2. Match to one or more processes
3. Assign confidence scores (0.0-1.0)
4. Provide brief reasoning

OUTPUT FORMAT (JSON):
{{
  "matches": [
    {{
      "process_id": "PROC-DEV-002",
      "confidence": 0.95,
      "reasoning": "User reported a bug and needs debugging workflow"
    }}
  ]
}}

RULES:
- Only return matches with confidence >= 0.5
- Return empty array if no clear match
- Consider process category and description
- Prioritize processes with higher priority values
"""
```

### 2. Process List Format

```json
[
  {
    "process_id": "PROC-DEV-002",
    "name": "Bug Fix Workflow",
    "description": "Report, investigate, fix, and document bugs",
    "category": "dev",
    "priority": 5,
    "keywords": ["bug", "error", "issue", "broken", "not working"]
  },
  {
    "process_id": "PROC-DEV-001",
    "name": "Feature Implementation",
    "description": "Implement feature through build tasks",
    "category": "dev",
    "priority": 5,
    "keywords": ["feature", "build", "create", "implement"]
  }
]
```

### 3. Example Classification

**Input**: "there is a bug in the login page"

**LLM Response**:
```json
{
  "matches": [
    {
      "process_id": "PROC-DEV-002",
      "confidence": 0.98,
      "reasoning": "User explicitly mentioned a bug, matches Bug Fix Workflow"
    },
    {
      "process_id": "PROC-QA-001",
      "confidence": 0.4,
      "reasoning": "May need testing after fix, but not primary intent"
    }
  ]
}
```

**Filtered Output**: Only PROC-DEV-002 (confidence >= 0.5)

---

## Implementation Plan

### Phase 1: Foundation (Week 1)

**File**: `scripts/llm_classifier.py`

```python
#!/usr/bin/env python3
"""
LLM-based Process Classifier

Uses Claude Haiku to classify user prompts into process categories
when regex/keyword matching fails.
"""

import json
import time
from typing import List, Dict, Optional
import anthropic


class ProcessClassifier:
    """LLM-based classifier for process intent detection."""
    
    def __init__(self, api_key: str, config: dict):
        """Initialize classifier with API key and config."""
        self.client = anthropic.Anthropic(api_key=api_key)
        self.config = config
        self.cache = {}  # Simple in-memory cache
        self.stats = {
            "total_calls": 0,
            "cache_hits": 0,
            "total_tokens_in": 0,
            "total_tokens_out": 0,
            "total_cost_usd": 0.0
        }
    
    def classify(self, user_prompt: str, processes: List[Dict]) -> List[Dict]:
        """
        Classify user prompt into process matches.
        
        Args:
            user_prompt: The user's input text
            processes: List of process dicts with id, name, description, keywords
        
        Returns:
            List of matched processes with confidence scores
        """
        # Check cache
        cache_key = self._get_cache_key(user_prompt)
        if cache_key in self.cache:
            cached_result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.config["cache_ttl_seconds"]:
                self.stats["cache_hits"] += 1
                return cached_result
        
        # Build prompt
        prompt = self._build_prompt(user_prompt, processes)
        
        # Call API
        try:
            response = self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                temperature=0,  # Deterministic for classification
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Update stats
            self.stats["total_calls"] += 1
            self.stats["total_tokens_in"] += response.usage.input_tokens
            self.stats["total_tokens_out"] += response.usage.output_tokens
            
            # Calculate cost (Haiku pricing: $0.25/$1.25 per 1M tokens)
            cost = (response.usage.input_tokens * 0.25 / 1_000_000 + 
                   response.usage.output_tokens * 1.25 / 1_000_000)
            self.stats["total_cost_usd"] += cost
            
            # Parse response
            matches = self._parse_response(response.content[0].text)
            
            # Cache result
            self.cache[cache_key] = (matches, time.time())
            
            return matches
            
        except Exception as e:
            # Log error but don't crash
            print(f"LLM classification error: {e}", file=sys.stderr)
            return []
    
    def _build_prompt(self, user_prompt: str, processes: List[Dict]) -> str:
        """Build classification prompt."""
        # Limit processes to avoid token bloat
        processes_limited = processes[:self.config["max_processes_in_prompt"]]
        
        processes_json = json.dumps(processes_limited, indent=2)
        
        return f"""You are a task classifier for a development workflow system.

Analyze the user's prompt and match it to relevant processes.

USER PROMPT: "{user_prompt}"

AVAILABLE PROCESSES:
{processes_json}

INSTRUCTIONS:
1. Identify the user's primary intent
2. Match to one or more processes
3. Assign confidence scores (0.0-1.0)
4. Provide brief reasoning

OUTPUT FORMAT (JSON only, no other text):
{{
  "matches": [
    {{
      "process_id": "PROC-XXX-XXX",
      "confidence": 0.95,
      "reasoning": "Brief explanation"
    }}
  ]
}}

RULES:
- Only return matches with confidence >= {self.config["confidence_threshold"]}
- Return empty array if no clear match
- Consider keywords, description, and category
- Be conservative with confidence scores
"""
    
    def _parse_response(self, response_text: str) -> List[Dict]:
        """Parse LLM response and filter by confidence."""
        try:
            # Extract JSON from response (in case LLM adds extra text)
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_text = response_text[json_start:json_end]
            
            data = json.loads(json_text)
            matches = data.get("matches", [])
            
            # Filter by confidence threshold
            threshold = self.config["confidence_threshold"]
            filtered = [m for m in matches if m.get("confidence", 0) >= threshold]
            
            return filtered
            
        except (json.JSONDecodeError, ValueError) as e:
            print(f"Failed to parse LLM response: {e}", file=sys.stderr)
            return []
    
    def _get_cache_key(self, user_prompt: str) -> str:
        """Generate cache key from prompt."""
        # Simple hash (could use hashlib for production)
        return user_prompt.lower().strip()
    
    def get_stats(self) -> dict:
        """Return classification statistics."""
        return self.stats.copy()
```

**File**: `scripts/process_router_config.py`

```python
"""Configuration for process router and LLM classifier."""

import os

# LLM Classification Configuration
LLM_CONFIG = {
    "enabled": os.getenv("PROCESS_ROUTER_LLM_ENABLED", "false").lower() == "true",
    "confidence_threshold": float(os.getenv("LLM_CONFIDENCE_THRESHOLD", "0.5")),
    "timeout_ms": int(os.getenv("LLM_TIMEOUT_MS", "1000")),
    "cache_ttl_seconds": int(os.getenv("LLM_CACHE_TTL", "3600")),
    "max_processes_in_prompt": int(os.getenv("LLM_MAX_PROCESSES", "25"))
}

# Anthropic API Key
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Feature flags
FEATURES = {
    "llm_fallback": LLM_CONFIG["enabled"],
    "fuzzy_matching": False,  # Future enhancement
    "learning_mode": False    # Future: Learn from corrections
}
```

### Phase 2: Integration (Week 2)

**Modify**: `scripts/process_router.py`

```python
# Add imports at top
from llm_classifier import ProcessClassifier
from process_router_config import LLM_CONFIG, ANTHROPIC_API_KEY, FEATURES

# Global classifier instance (initialized once)
_classifier = None

def get_classifier():
    """Get or create classifier instance."""
    global _classifier
    if _classifier is None and FEATURES["llm_fallback"] and ANTHROPIC_API_KEY:
        _classifier = ProcessClassifier(ANTHROPIC_API_KEY, LLM_CONFIG)
    return _classifier


def classify_with_llm_fallback(conn, user_prompt: str) -> List[Dict[str, Any]]:
    """
    Use LLM to classify user intent when regex/keywords fail.
    
    Returns:
        List of matched process dicts (same format as get_matching_processes)
    """
    classifier = get_classifier()
    if not classifier:
        return []
    
    # Get all active processes
    cur = conn.cursor()
    cur.execute("""
        SELECT
            pr.process_id,
            pr.process_name,
            pr.description,
            pr.category,
            pr.enforcement,
            pr.sop_ref,
            pr.command_ref,
            COALESCE(
                json_agg(pt.pattern) FILTER (WHERE pt.trigger_type = 'keywords'),
                '[]'
            ) as keywords
        FROM claude.process_registry pr
        LEFT JOIN claude.process_triggers pt ON pr.process_id = pt.process_id
        WHERE pr.is_active = true
        GROUP BY pr.process_id, pr.process_name, pr.description, pr.category,
                 pr.enforcement, pr.sop_ref, pr.command_ref
        ORDER BY pr.process_id
    """)
    
    processes = []
    for row in cur.fetchall():
        # Extract keywords from JSON arrays
        keywords = []
        if row['keywords']:
            for kw_json in row['keywords']:
                try:
                    keywords.extend(json.loads(kw_json))
                except:
                    pass
        
        processes.append({
            "process_id": row['process_id'],
            "name": row['process_name'],
            "description": row['description'],
            "category": row['category'],
            "keywords": keywords
        })
    
    # Classify with LLM
    llm_matches = classifier.classify(user_prompt, processes)
    
    # Convert LLM matches back to full process dicts
    matched_process_ids = [m['process_id'] for m in llm_matches]
    
    if not matched_process_ids:
        return []
    
    # Fetch full process details
    placeholders = ','.join(['%s'] * len(matched_process_ids))
    cur.execute(f"""
        SELECT DISTINCT
            pr.process_id,
            pr.process_name,
            pr.category,
            pr.description,
            pr.enforcement,
            pr.sop_ref,
            pr.command_ref
        FROM claude.process_registry pr
        WHERE pr.process_id IN ({placeholders})
    """, matched_process_ids)
    
    matches = [dict(row) for row in cur.fetchall()]
    
    # Add LLM metadata to matches
    for match in matches:
        llm_match = next(m for m in llm_matches if m['process_id'] == match['process_id'])
        match['llm_confidence'] = llm_match['confidence']
        match['llm_reasoning'] = llm_match['reasoning']
    
    return matches


def get_matching_processes(conn, user_prompt: str) -> List[Dict[str, Any]]:
    """
    Find all processes that match the user prompt.
    
    Enhanced with LLM fallback when regex/keywords don't match.
    """
    if not conn:
        return []

    cur = conn.cursor()

    # Get all active triggers ordered by priority
    cur.execute("""
        SELECT
            pt.trigger_id,
            pt.process_id,
            pt.trigger_type,
            pt.pattern,
            pt.priority,
            pr.process_name,
            pr.category,
            pr.description,
            pr.enforcement,
            pr.sop_ref,
            pr.command_ref
        FROM claude.process_triggers pt
        JOIN claude.process_registry pr ON pt.process_id = pr.process_id
        WHERE pt.is_active = true AND pr.is_active = true
        ORDER BY pt.priority ASC
    """)

    triggers = cur.fetchall()
    matches = []

    # TIER 1: Try regex/keyword matching (existing logic)
    for trigger in triggers:
        matched = False

        if trigger['trigger_type'] == 'regex':
            try:
                if re.search(trigger['pattern'], user_prompt, re.IGNORECASE):
                    matched = True
            except re.error:
                pass

        elif trigger['trigger_type'] == 'keywords':
            try:
                keywords = json.loads(trigger['pattern'])
                prompt_lower = user_prompt.lower()
                if any(kw.lower() in prompt_lower for kw in keywords):
                    matched = True
            except json.JSONDecodeError:
                pass

        if matched:
            if not any(m['process_id'] == trigger['process_id'] for m in matches):
                matches.append(dict(trigger))

    # TIER 2: If no matches and LLM enabled, try LLM classification
    if not matches and FEATURES["llm_fallback"]:
        try:
            matches = classify_with_llm_fallback(conn, user_prompt)
            
            # Log LLM usage
            if matches:
                classifier = get_classifier()
                if classifier:
                    stats = classifier.get_stats()
                    # Could log to database here for monitoring
                    
        except Exception as e:
            # Don't let LLM failures break the system
            print(f"LLM fallback error: {e}", file=sys.stderr)

    return matches
```

### Phase 3: Testing & Validation

**Test Cases** (`tests/test_llm_classifier.py`):

```python
import pytest
from scripts.llm_classifier import ProcessClassifier

TEST_CONFIG = {
    "confidence_threshold": 0.5,
    "cache_ttl_seconds": 3600,
    "max_processes_in_prompt": 25
}

TEST_PROCESSES = [
    {
        "process_id": "PROC-DEV-002",
        "name": "Bug Fix Workflow",
        "description": "Report, investigate, fix, and document bugs",
        "category": "dev",
        "keywords": ["bug", "error", "issue", "broken"]
    },
    {
        "process_id": "PROC-DEV-001",
        "name": "Feature Implementation",
        "description": "Implement feature through build tasks",
        "category": "dev",
        "keywords": ["feature", "build", "create"]
    }
]

@pytest.fixture
def classifier():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set")
    return ProcessClassifier(api_key, TEST_CONFIG)


def test_bug_classification(classifier):
    """Test that bug-related prompts match bug workflow."""
    prompts = [
        "there is a bug in the login",
        "I found a bug",
        "something is broken",
        "getting an error"
    ]
    
    for prompt in prompts:
        matches = classifier.classify(prompt, TEST_PROCESSES)
        assert len(matches) > 0, f"No match for: {prompt}"
        assert matches[0]["process_id"] == "PROC-DEV-002"
        assert matches[0]["confidence"] >= 0.5


def test_feature_classification(classifier):
    """Test that feature-related prompts match feature workflow."""
    prompts = [
        "create a new feature",
        "I need to add functionality",
        "let's build a login page",
        "implement user authentication"
    ]
    
    for prompt in prompts:
        matches = classifier.classify(prompt, TEST_PROCESSES)
        assert len(matches) > 0, f"No match for: {prompt}"
        assert matches[0]["process_id"] == "PROC-DEV-001"


def test_no_match(classifier):
    """Test that irrelevant prompts return no match."""
    prompts = [
        "hello",
        "what's the weather",
        "random text"
    ]
    
    for prompt in prompts:
        matches = classifier.classify(prompt, TEST_PROCESSES)
        assert len(matches) == 0, f"Unexpected match for: {prompt}"


def test_caching(classifier):
    """Test that identical prompts hit cache."""
    prompt = "there is a bug"
    
    # First call
    matches1 = classifier.classify(prompt, TEST_PROCESSES)
    calls_after_first = classifier.stats["total_calls"]
    
    # Second call (should hit cache)
    matches2 = classifier.classify(prompt, TEST_PROCESSES)
    calls_after_second = classifier.stats["total_calls"]
    
    assert matches1 == matches2
    assert calls_after_second == calls_after_first  # No new API call
    assert classifier.stats["cache_hits"] > 0
```

**Manual Testing**:

```bash
# Test with sample prompts
cd C:\Projects\claude-family\scripts

# Enable LLM fallback
export PROCESS_ROUTER_LLM_ENABLED=true
export ANTHROPIC_API_KEY=your_key_here

# Test prompts
echo '{"prompt": "there is a bug in login"}' | python process_router.py
echo '{"prompt": "I need to add a feature"}' | python process_router.py
echo '{"prompt": "lets build something"}' | python process_router.py
```

### Phase 4: Monitoring & Metrics

**Database Table**: `claude.process_classification_log`

```sql
CREATE TABLE claude.process_classification_log (
    log_id SERIAL PRIMARY KEY,
    user_prompt TEXT NOT NULL,
    classification_method VARCHAR(20) NOT NULL, -- 'regex', 'keywords', 'llm'
    matched_process_ids TEXT[], -- Array of process IDs
    llm_confidence DECIMAL(3,2), -- If LLM was used
    llm_reasoning TEXT, -- If LLM was used
    latency_ms INTEGER,
    cost_usd DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_classification_log_method ON claude.process_classification_log(classification_method);
CREATE INDEX idx_classification_log_created ON claude.process_classification_log(created_at);
```

**Monitoring Queries**:

```sql
-- LLM usage stats (last 7 days)
SELECT
    DATE(created_at) as date,
    COUNT(*) as llm_calls,
    AVG(latency_ms) as avg_latency_ms,
    SUM(cost_usd) as total_cost_usd,
    AVG(llm_confidence) as avg_confidence
FROM claude.process_classification_log
WHERE classification_method = 'llm'
  AND created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- Classification method breakdown
SELECT
    classification_method,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM claude.process_classification_log
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY classification_method;

-- Top unmatched prompts (candidates for new triggers)
SELECT
    user_prompt,
    COUNT(*) as frequency
FROM claude.process_classification_log
WHERE matched_process_ids = ARRAY[]::TEXT[]
  AND created_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY user_prompt
ORDER BY frequency DESC
LIMIT 20;
```

---

## Cost Analysis

### Haiku Pricing (December 2024)
- Input: $0.25 per 1M tokens
- Output: $1.25 per 1M tokens

### Per-Classification Cost
- Input tokens: ~200 (prompt + 20 processes)
- Output tokens: ~100 (JSON response)
- **Cost per call: ~$0.0002**

### Projected Monthly Cost

| Daily Prompts | LLM Fallback Rate | LLM Calls/Day | Cost/Day | Cost/Month |
|---------------|-------------------|---------------|----------|------------|
| 100           | 10%               | 10            | $0.002   | $0.06      |
| 1,000         | 10%               | 100           | $0.02    | $0.60      |
| 10,000        | 10%               | 1,000         | $0.20    | $6.00      |

**Conclusion**: Cost is negligible (<$1/month for typical usage)

### Optimization Strategies
1. **Caching**: Identical prompts hit cache (0 cost)
2. **Batch learning**: Successful LLM matches → new regex patterns
3. **Token efficiency**: Limit processes in prompt to top 25 by priority
4. **Smart fallback**: Only call LLM if prompt length > 10 words

---

## Rollout Strategy

### Week 1: Development
- [ ] Create `llm_classifier.py` module
- [ ] Create `process_router_config.py` config
- [ ] Add Anthropic SDK dependency: `pip install anthropic`
- [ ] Write unit tests
- [ ] Test offline with sample prompts

### Week 2: Integration
- [ ] Modify `process_router.py` to add LLM fallback
- [ ] Add feature flag (default: disabled)
- [ ] Add logging for LLM calls
- [ ] Test in development environment
- [ ] Document configuration in CLAUDE.md

### Week 3: Alpha Testing
- [ ] Enable LLM fallback for 1 Claude instance (test user)
- [ ] Monitor performance metrics
- [ ] Collect edge cases that LLM catches
- [ ] Tune confidence threshold based on data
- [ ] Fix any bugs

### Week 4: Production Rollout
- [ ] Enable LLM fallback for all instances
- [ ] Set up monitoring dashboard
- [ ] Create runbook for troubleshooting
- [ ] Document in SOPs

### Week 5+: Optimization
- [ ] Analyze top LLM-matched patterns
- [ ] Create new regex triggers for common patterns
- [ ] Reduce LLM fallback rate through learning
- [ ] Consider prompt caching API (beta feature)

---

## Success Metrics

### Primary KPIs
- **Match Rate**: % of prompts that match a process (target: >95%)
- **LLM Accuracy**: % of LLM matches that are correct (target: >90%)
- **Latency**: p95 response time (target: <500ms for LLM calls)
- **Cost Efficiency**: Cost per 1000 prompts (target: <$0.50)

### Secondary KPIs
- False positive rate (incorrect matches)
- False negative rate (missed matches)
- User satisfaction (implicit: do they follow guidance?)
- Cache hit rate (higher = better efficiency)

### Data Collection
```python
# Add to process_router.py
def log_classification(method, prompt, matches, latency_ms, cost_usd=None):
    """Log classification for analytics."""
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO claude.process_classification_log
            (user_prompt, classification_method, matched_process_ids,
             llm_confidence, llm_reasoning, latency_ms, cost_usd)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            prompt,
            method,
            [m['process_id'] for m in matches],
            matches[0].get('llm_confidence') if matches else None,
            matches[0].get('llm_reasoning') if matches else None,
            latency_ms,
            cost_usd
        ))
        conn.commit()
    except:
        pass  # Best effort logging
```

---

## Risk Mitigation

### Risk 1: API Latency
- **Impact**: User experience degradation
- **Mitigation**: 
  * Set timeout to 1000ms
  * Fall back to no match if timeout
  * Cache aggressively

### Risk 2: API Costs
- **Impact**: Unexpected billing
- **Mitigation**:
  * Feature flag for quick disable
  * Daily cost monitoring alerts
  * Rate limiting (max 1000 LLM calls/day initially)

### Risk 3: Classification Errors
- **Impact**: Wrong process triggered
- **Mitigation**:
  * Conservative confidence threshold (0.5)
  * Log all classifications for review
  * User can always bypass process guidance

### Risk 4: API Outage
- **Impact**: LLM fallback unavailable
- **Mitigation**:
  * Graceful degradation (regex still works)
  * Error logging without blocking user
  * Automatic retry with exponential backoff

---

## Future Enhancements

### Phase 2: Learning System
- Collect user corrections ("This process doesn't apply")
- Fine-tune prompts based on feedback
- Auto-generate new regex patterns from LLM successes

### Phase 3: Multi-Intent Detection
- Support multiple processes in one prompt
- Example: "fix the bug and write tests" → DEV-002 + QA-001

### Phase 4: Context-Aware Classification
- Include project context in classification
- Different matching for different project types
- User preference learning

### Phase 5: Local LLM Option
- Support local models (Llama, Mistral) for privacy
- Zero-cost classification at expense of accuracy

---

## Conclusion

This enhancement brings intelligent intent understanding to process routing while maintaining:
- ✅ Cost efficiency (~$0.50/month for 1000 prompts/day)
- ✅ Performance (regex fast path for 90% of cases)
- ✅ Reliability (graceful degradation on failures)
- ✅ Measurability (comprehensive logging and metrics)

The hybrid approach (regex + LLM fallback) gives us the best of both worlds: speed and intelligence.

---

**Author**: analyst-sonnet (Task ID: dd522d5d-340e-4c4e-b5fc-56451ddc0b1c)  
**Date**: 2025-12-08  
**Version**: 1.0
