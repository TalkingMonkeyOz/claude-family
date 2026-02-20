
import sys, os
sys.path.insert(0, r'C:\Projects\claude-family\mcp-servers\bpmn-engine')
os.chdir(r'C:\Projects\claude-family\mcp-servers\bpmn-engine')
from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

def complete(wf, name, data=None):
    tasks = [t for t in wf.get_tasks(state=TaskState.READY, manual=True) if t.task_spec.name == name]
    ready = [t.task_spec.name for t in wf.get_tasks(state=TaskState.READY, manual=True)]
    assert tasks, f"'{name}' not READY. Ready: {ready}"
    if data: tasks[0].data.update(data)
    tasks[0].run()
    wf.do_engine_steps()

# Test L1->L2: feature lifecycle with task_lifecycle callActivity
parser = BpmnParser()
parser.add_bpmn_file('processes/architecture/L1_work_tracking.bpmn')
parser.add_bpmn_file('processes/lifecycle/task_lifecycle.bpmn')
spec = parser.get_spec('L1_work_tracking')
subspecs = parser.get_subprocess_specs('L1_work_tracking')
print(f'Subspecs: {list(subspecs.keys())}')
wf = BpmnWorkflow(spec, subspecs)
wf.do_engine_steps()
complete(wf, 'identify_work', {'work_type': 'feature'})
complete(wf, 'plan_feature')
complete(wf, 'create_task', {'has_tasks': True, 'action': 'complete'})
complete(wf, 'work_on_task', {'action': 'complete'})
complete(wf, 'assess_task_completion', {'all_tasks_done': True})
assert wf.is_completed()
assert wf.data.get('feature_status') == 'completed'
print('Test 1: Feature lifecycle with L2 - PASSED')

# Test L0->L1->L2: full hierarchy
L1_FILES = {
    'L1_session_management': 'processes/architecture/L1_session_management.bpmn',
    'L1_work_tracking': 'processes/architecture/L1_work_tracking.bpmn',
    'L1_knowledge_management': 'processes/architecture/L1_knowledge_management.bpmn',
    'L1_enforcement': 'processes/architecture/L1_enforcement.bpmn',
    'L1_agent_orchestration': 'processes/architecture/L1_agent_orchestration.bpmn',
    'L1_config_management': 'processes/architecture/L1_config_management.bpmn',
}
parser2 = BpmnParser()
for f in L1_FILES.values(): parser2.add_bpmn_file(f)
parser2.add_bpmn_file('processes/lifecycle/task_lifecycle.bpmn')
parser2.add_bpmn_file('processes/architecture/L0_claude_family.bpmn')
spec2 = parser2.get_spec('claude_process')
subspecs2 = parser2.get_subprocess_specs('claude_process')
print(f'Full hierarchy subspecs: {len(subspecs2)} ({list(subspecs2.keys())})')
wf2 = BpmnWorkflow(spec2, subspecs2)
wf2.do_engine_steps()
# Adhoc path (avoids L2)
for name, data in [
    ('load_state', {'prior_state': False}), ('receive_prompt', {'action': 'end_auto'}),
    ('process_prompt', {}), ('identify_work', {'work_type': 'adhoc'}),
    ('create_tasks', {}), ('identify_km_action', {'km_action': 'retrieve'}),
    ('apply_knowledge', {}), ('identify_tool', {'is_gated': False}),
    ('execute_tool', {}), ('assess_complexity', {'need_agent': False}),
    ('execute_direct', {}), ('identify_config', {'config_scope': 'project'}),
    ('validate_config', {}),
]:
    complete(wf2, name, data)
assert wf2.is_completed()
print('Test 2: Full L0->L1 hierarchy (adhoc path) - PASSED')

# Test L0->L1->L2 with feature path
parser3 = BpmnParser()
for f in L1_FILES.values(): parser3.add_bpmn_file(f)
parser3.add_bpmn_file('processes/lifecycle/task_lifecycle.bpmn')
parser3.add_bpmn_file('processes/architecture/L0_claude_family.bpmn')
spec3 = parser3.get_spec('claude_process')
subspecs3 = parser3.get_subprocess_specs('claude_process')
wf3 = BpmnWorkflow(spec3, subspecs3)
wf3.do_engine_steps()
for name, data in [
    ('load_state', {'prior_state': False}), ('receive_prompt', {'action': 'end_auto'}),
    ('process_prompt', {}), ('identify_work', {'work_type': 'feature'}),
    ('plan_feature', {}),
    ('create_task', {'has_tasks': True, 'action': 'complete'}),
    ('work_on_task', {'action': 'complete'}),
    ('assess_task_completion', {'all_tasks_done': True}),
    ('identify_km_action', {'km_action': 'retrieve'}),
    ('apply_knowledge', {}), ('identify_tool', {'is_gated': False}),
    ('execute_tool', {}), ('assess_complexity', {'need_agent': False}),
    ('execute_direct', {}), ('identify_config', {'config_scope': 'project'}),
    ('validate_config', {}),
]:
    complete(wf3, name, data)
assert wf3.is_completed()
print('Test 3: Full L0->L1->L2 hierarchy (feature path) - PASSED')

print('\\n=== ALL L1->L2 INTEGRATION TESTS PASSED ===')
