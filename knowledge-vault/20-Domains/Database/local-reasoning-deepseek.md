---
category: local-ai
confidence: 85
created: 2025-12-19
projects:
- claude-family
synced: true
synced_at: '2025-12-20T11:08:45.268853'
tags:
- deepseek
- ollama
- local-llm
- reasoning
title: Local Reasoning with DeepSeek-r1 on RTX 5080
type: architecture
---

# Local Reasoning with DeepSeek-r1 on RTX 5080

## Summary
DeepSeek-r1:14b provides excellent local reasoning capability with 77 tok/s eval rate on RTX 5080.

## Test Results
- **Accuracy**: Excellent (solved trick question correctly)
- **Speed**: 77 tok/s eval rate
- **Cold start**: 22s model load (subsequent requests fast)
- **Capability**: Shows chain-of-thought reasoning

## Integration Options

| Option | Description | Best For |
|--------|-------------|----------|
| A) Direct API | Via ollama-mcp, manual invocation | Testing, exploration |
| B) Orchestrator Agent | Reusable "local-reasoner" type | Production use |
| C) Both | Test first, then productionize | Recommended path |

## When to Use

### Use DeepSeek-r1 For:
- Math/logic chain problems
- Privacy-sensitive reasoning
- Cost savings on simple tasks
- Offline capability needs

### Keep Claude For:
- Complex multi-step reasoning
- Large context (200K tokens)
- Best quality requirements
- Nuanced understanding

## Code Example
```python
# Via ollama Python library
import ollama

response = ollama.generate(
    model='deepseek-r1:14b',
    prompt='Solve step by step: If I have 3 apples...'
)
print(response['response'])
```

```bash
# Via CLI
ollama run deepseek-r1:14b "Your reasoning prompt here"
```

## Hardware Requirements
- GPU: RTX 5080 or equivalent (16GB+ VRAM recommended)
- RAM: 32GB+ system RAM
- Storage: ~28GB for 14b model

## Related
- [[ollama-mcp-setup]]
- [[local-llm-comparison]]