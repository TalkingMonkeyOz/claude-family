# System Change Process Rule

## When This Applies

Any time you modify files in these categories:
- **Hook scripts**: `scripts/*_hook*.py`, `scripts/*_hook.py`
- **Workflow code**: `mcp-servers/*/server*.py`, state machine logic
- **Config management**: `scripts/generate_*.py`, `scripts/deploy_*.py`
- **BPMN processes**: `mcp-servers/bpmn-engine/processes/**/*.bpmn`
- **Enforcement rules**: `.claude/rules/*.md`, `.claude/skills/**/*.md`

## Required Process (BPMN-First)

Before implementing changes to the above systems, follow this process:

1. **Search existing models**: Use `search_processes` or `list_processes` from the bpmn-engine MCP to check if the system you're changing is already modeled in BPMN.

2. **If modeled**: Review the current model (`get_process`), identify the gap between the model and needed change, then update the BPMN model FIRST.

3. **If not modeled**: Create a new BPMN model for the system before implementing code changes.

4. **Test the model**: Write/update pytest tests for the BPMN process. Run them. Fix until green.

5. **Implement code**: Now implement the actual code changes.

6. **Commit together**: Always commit the BPMN model changes alongside the code changes. Never commit code without its corresponding model update.

## Process Failure Capture

When a process failure occurs (hook error, state machine violation, unexpected behavior):

1. **Capture the failure**: File feedback via `create_feedback` with type='bug'
2. **Check if modeled**: Search BPMN models for the failing system
3. **Model the fix**: Update or create BPMN model showing the correct behavior
4. **Test and implement**: Follow the standard BPMN-first flow

## Reference

- Process BPMN: `processes/development/system_change_process.bpmn`
- Skill: `/bpmn-modeling`
- Feature: F113 (BPMN Process Coverage + Self-Enforcement)
