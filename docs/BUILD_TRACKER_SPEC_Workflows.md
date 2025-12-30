# Build Tracker Data Gateway Specification - Workflows

**Purpose**: Cross-table business rules, workflow tool specifications, and workflow automation patterns.

See [[BUILD_TRACKER_SPEC_Overview]] for context and [[BUILD_TRACKER_SPEC_Table_Analysis]] for table definitions.

---

## Cross-Table Business Rules

### 1. Referential Integrity (Application-Level)

Since there are no foreign key constraints, implement these checks:

```python
def validate_references(entity_type, data):
    """Validate all foreign key references before insert/update"""

    if entity_type == 'component':
        if data.get('feature_id') and not feature_exists(data['feature_id']):
            raise ReferenceError(f"feature_id {data['feature_id']} not found")

    elif entity_type == 'build_task':
        if data.get('component_id') and not component_exists(data['component_id']):
            raise ReferenceError(f"component_id {data['component_id']} not found")
        if data.get('feature_id') and not feature_exists(data['feature_id']):
            raise ReferenceError(f"feature_id {data['feature_id']} not found")
        if data.get('blocked_by_task_id') and not task_exists(data['blocked_by_task_id']):
            raise ReferenceError(f"blocked_by_task_id {data['blocked_by_task_id']} not found")

    elif entity_type == 'requirement':
        if data.get('feature_id') and not feature_exists(data['feature_id']):
            raise ReferenceError(f"feature_id {data['feature_id']} not found")
        if data.get('implemented_by_component_id'):
            if not component_exists(data['implemented_by_component_id']):
                raise ReferenceError(
                    f"implemented_by_component_id {data['implemented_by_component_id']} not found"
                )
```

### 2. Hierarchical Consistency

```python
def validate_hierarchy(entity_type, data):
    """Ensure child status doesn't exceed parent status"""

    if entity_type == 'component':
        feature = get_feature(data['feature_id'])

        # Component can't be completed if feature is not started
        if data['status'] == 'completed' and feature['status'] in ['not_started', 'planned']:
            raise ValidationError(
                f"Cannot complete component when feature is '{feature['status']}'"
            )

    elif entity_type == 'build_task':
        if data.get('component_id'):
            component = get_component(data['component_id'])

            # Task can't be completed if component is planned
            if data['status'] == 'completed' and component['status'] == 'planned':
                raise ValidationError(
                    f"Cannot complete task when component is '{component['status']}'"
                )

    elif entity_type == 'requirement':
        feature = get_feature(data['feature_id'])

        # Requirement can't be verified if feature is not started
        if data['status'] == 'verified' and feature['status'] in ['not_started', 'planned']:
            raise ValidationError(
                f"Cannot verify requirement when feature is '{feature['status']}'"
            )
```

### 3. Completion Percentage Calculation

```python
def calculate_feature_completion(feature_id):
    """Auto-calculate feature completion from child entities"""

    # Get all components for feature
    components = get_components_by_feature(feature_id)

    if components:
        # Calculate from components
        total_components = len(components)
        completed_components = sum(
            1 for c in components
            if c['status'] in ['completed', 'tested', 'documented']
        )
        completion = int((completed_components / total_components) * 100)
    else:
        # Fallback to tasks if no components
        tasks = get_tasks_by_feature(feature_id)
        if tasks:
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t['status'] == 'completed')
            completion = int((completed_tasks / total_tasks) * 100)
        else:
            # No components or tasks, keep manual value
            return None

    # Update feature
    update_feature(feature_id, {'completion_percentage': completion})
    return completion

def trigger_completion_update(entity_type, entity_id, old_status, new_status):
    """Trigger completion recalculation when child status changes"""

    if entity_type == 'component' and old_status != new_status:
        component = get_component(entity_id)
        calculate_feature_completion(component['feature_id'])

    elif entity_type == 'build_task' and old_status != new_status:
        task = get_task(entity_id)
        if task.get('feature_id'):
            calculate_feature_completion(task['feature_id'])
```

### 4. Dependency Validation

```python
def validate_dependencies(task_id):
    """Check if task dependencies are satisfied"""

    task = get_task(task_id)

    # Check blocked_by_task_id
    if task.get('blocked_by_task_id'):
        blocking_task = get_task(task['blocked_by_task_id'])

        if blocking_task['status'] != 'completed':
            return False, f"Blocked by task: {blocking_task['task_name']}"

    # Check circular dependencies
    visited = set()
    current = task_id

    while current:
        if current in visited:
            return False, "Circular dependency detected"

        visited.add(current)
        t = get_task(current)
        current = t.get('blocked_by_task_id')

    return True, None

def get_ready_tasks(feature_id=None, component_id=None):
    """Get tasks that are unblocked and ready to start"""

    filters = {'status': 'todo'}
    if feature_id:
        filters['feature_id'] = feature_id
    if component_id:
        filters['component_id'] = component_id

    tasks = get_tasks(filters)
    ready = []

    for task in tasks:
        is_ready, _ = validate_dependencies(task['task_id'])
        if is_ready:
            ready.append(task)

    # Sort by priority
    return sorted(ready, key=lambda t: t.get('priority', 5))
```

### 5. Feature Completion Gating

```python
def can_complete_feature(feature_id):
    """Check if all requirements are met for feature completion"""

    checks = []

    # Check components
    components = get_components_by_feature(feature_id)
    incomplete_components = [
        c for c in components
        if c['status'] not in ['completed', 'tested', 'documented']
    ]
    if incomplete_components:
        checks.append(
            f"{len(incomplete_components)} components not completed: "
            f"{[c['component_name'] for c in incomplete_components]}"
        )

    # Check must-have requirements
    requirements = get_requirements_by_feature(feature_id)
    must_have_requirements = [r for r in requirements if r.get('must_have')]
    unverified_must_haves = [
        r for r in must_have_requirements
        if r['status'] != 'verified'
    ]
    if unverified_must_haves:
        checks.append(
            f"{len(unverified_must_haves)} must-have requirements not verified: "
            f"{[r['requirement_name'] for r in unverified_must_haves]}"
        )

    # Check tasks
    tasks = get_tasks_by_feature(feature_id)
    incomplete_tasks = [t for t in tasks if t['status'] != 'completed']
    if incomplete_tasks:
        checks.append(
            f"{len(incomplete_tasks)} tasks not completed: "
            f"{[t['task_name'] for t in incomplete_tasks]}"
        )

    return len(checks) == 0, checks
```

---

## Workflow Tool Specifications

### Tool: `add_feature`

**Purpose**: Create a new feature with validation and activity logging

**Parameters**:
```python
def add_feature(
    feature_name: str,
    feature_type: str,
    description: str,
    project_id: str,
    priority: int = 5,
    parent_feature_id: str = None,
    planned_by_identity_id: str = None,
    design_doc_path: str = None
) -> dict:
```

**Validation Steps**:
1. Validate `feature_name` (min 5 chars, not duplicate in project)
2. Validate `feature_type` (must be in VALID_FEATURE_TYPES)
3. Validate `project_id` exists
4. Validate `priority` (1-10)
5. If `parent_feature_id` provided:
   - Validate exists
   - Check for circular reference
6. Validate `description` (min 20 chars if moving to 'planned')

**Side Effects**:
1. Generate UUID for `feature_id`
2. Set `status='not_started'`
3. Set `completion_percentage=0`
4. Set `created_at=now()`
5. Set `updated_at=now()`
6. Insert into `features` table
7. Log to `activity_feed`:
   ```python
   {
       'source_type': 'feature',
       'source_id': feature_id,
       'activity_type': 'created',
       'title': f'Feature created: {feature_name}',
       'summary': f'New {feature_type} feature added to project',
       'project_name': get_project_name(project_id),
       'actor': get_identity_name(planned_by_identity_id),
       'severity': 'info'
   }
   ```

**Return**:
```python
{
    'feature_id': 'uuid',
    'feature_name': 'str',
    'status': 'not_started',
    'completion_percentage': 0,
    'created_at': 'timestamp',
    'validation_warnings': ['list of non-critical issues']
}
```

---

### Tool: `update_feature_status`

**Purpose**: Change feature status with workflow validation

**Parameters**:
```python
def update_feature_status(
    feature_id: str,
    new_status: str,
    reason: str = None,  # Required for 'blocked', 'cancelled'
    implemented_by_identity_id: str = None  # Required for 'in_progress'
) -> dict:
```

**Validation Steps**:
1. Validate `feature_id` exists
2. Validate `new_status` in VALID_FEATURE_STATUSES
3. Check valid transition from current status
4. Status-specific validation:
   - `planned`: requires `description` (min 20 chars)
   - `in_progress`: requires `implemented_by_identity_id`
   - `blocked`: requires `reason`
   - `completed`: check all components/requirements complete
   - `cancelled`: requires `reason`

**Side Effects**:
1. Update `status` field
2. Update timestamps:
   - `in_progress`: set `started_date=now()`
   - `completed`: set `completed_date=now()`
3. Update `updated_at=now()`
4. Recalculate `completion_percentage` if completing
5. Log to `activity_feed`:
   ```python
   {
       'source_type': 'feature',
       'source_id': feature_id,
       'activity_type': 'status_changed',
       'title': f'Feature {old_status} → {new_status}',
       'summary': reason or f'Feature moved to {new_status}',
       'severity': 'info' if new_status == 'completed' else 'warning'
   }
   ```
6. If `completed`, trigger notifications to stakeholders

**Return**:
```python
{
    'feature_id': 'uuid',
    'old_status': 'str',
    'new_status': 'str',
    'completion_percentage': 'int',
    'updated_at': 'timestamp',
    'validation_errors': [],
    'validation_warnings': []
}
```

---

### Tool: `add_component`

**Purpose**: Add component to a feature

**Parameters**:
```python
def add_component(
    feature_id: str,
    component_name: str,
    component_type: str,
    planned_functions: list[str] = None,
    planned_dependencies: list[str] = None,
    file_path: str = None
) -> dict:
```

**Validation Steps**:
1. Validate `feature_id` exists
2. Validate `component_name` (min 3 chars, unique within feature)
3. Validate `component_type` in VALID_COMPONENT_TYPES
4. Auto-generate `file_path` if not provided (based on type and name)
5. Validate `planned_functions` (at least one recommended)

**Side Effects**:
1. Generate UUID for `component_id`
2. Set `status='planned'`
3. Set `has_tests=false`, `has_documentation=false`
4. Set `created_at=now()`, `updated_at=now()`
5. Insert into `components` table
6. Update feature's completion percentage
7. Log to `activity_feed`:
   ```python
   {
       'source_type': 'component',
       'source_id': component_id,
       'activity_type': 'created',
       'title': f'Component planned: {component_name}',
       'summary': f'{component_type} component added to feature',
       'severity': 'info'
   }
   ```

**Return**:
```python
{
    'component_id': 'uuid',
    'component_name': 'str',
    'status': 'planned',
    'file_path': 'str',
    'validation_warnings': []
}
```

---

### Tool: `complete_component`

**Purpose**: Mark component as completed with validation

**Parameters**:
```python
def complete_component(
    component_id: str,
    actual_functions: list[str],
    file_path: str = None,
    lines_of_code: int = None,
    has_tests: bool = False,
    test_coverage_percentage: int = 0
) -> dict:
```

**Validation Steps**:
1. Validate `component_id` exists
2. Validate current status is 'in_progress'
3. Validate `actual_functions` not empty
4. Compare with `planned_functions`, warn on differences
5. Validate `file_path` (must be provided or already set)
6. Warn if `has_tests=false`
7. Warn if `test_coverage_percentage < 80`

**Side Effects**:
1. Update `status='completed'`
2. Update `actual_functions`, `file_path`, `lines_of_code`
3. Update `has_tests`, `test_coverage_percentage`
4. Set `implemented_at=now()`, `updated_at=now()`
5. Recalculate feature completion percentage
6. Check if feature can be completed
7. Log to `activity_feed`:
   ```python
   {
       'source_type': 'component',
       'source_id': component_id,
       'activity_type': 'completed',
       'title': f'Component completed: {component_name}',
       'summary': f'{lines_of_code} LOC, {test_coverage_percentage}% coverage',
       'severity': 'info'
   }
   ```

**Return**:
```python
{
    'component_id': 'uuid',
    'status': 'completed',
    'implemented_at': 'timestamp',
    'feature_completion_percentage': 'int',
    'validation_warnings': [],
    'feature_ready_to_complete': 'bool'
}
```

---

### Tool: `add_task`

**Purpose**: Create a build task

**Parameters**:
```python
def add_task(
    task_name: str,
    task_description: str,
    task_type: str,
    component_id: str = None,
    feature_id: str = None,
    priority: int = 5,
    estimated_hours: float = None,
    assigned_to_identity_id: str = None,
    blocked_by_task_id: str = None
) -> dict:
```

**Validation Steps**:
1. Validate `task_name` (min 5 chars)
2. Validate `task_description` (min 10 chars)
3. Validate `task_type` in VALID_TASK_TYPES
4. Validate `component_id` OR `feature_id` (at least one)
5. If both provided, validate component belongs to feature
6. Validate `priority` (1-10)
7. Validate `estimated_hours > 0` if provided
8. If `blocked_by_task_id`, validate exists and not circular

**Side Effects**:
1. Generate UUID for `task_id`
2. Set `status='todo'`
3. Set `created_at=now()`, `updated_at=now()`
4. Insert into `build_tasks` table
5. If `assigned_to_identity_id`, notify assignee
6. Log to `activity_feed`:
   ```python
   {
       'source_type': 'build_task',
       'source_id': task_id,
       'activity_type': 'created',
       'title': f'Task created: {task_name}',
       'summary': f'{task_type} task (priority {priority})',
       'actor': get_identity_name(assigned_to_identity_id),
       'severity': 'info'
   }
   ```

**Return**:
```python
{
    'task_id': 'uuid',
    'task_name': 'str',
    'status': 'todo',
    'priority': 'int',
    'is_blocked': 'bool',
    'validation_warnings': []
}
```

---

### Tool: `start_task`

**Purpose**: Begin work on a task

**Parameters**:
```python
def start_task(
    task_id: str,
    identity_id: str
) -> dict:
```

**Validation Steps**:
1. Validate `task_id` exists
2. Validate current status is 'todo'
3. Validate `identity_id` exists
4. Check dependencies (not blocked by incomplete tasks)
5. Warn if identity has > 5 active tasks

**Side Effects**:
1. Update `status='in_progress'`
2. Update `assigned_to_identity_id=identity_id`
3. Set `started_at=now()`, `updated_at=now()`
4. Log to `activity_feed`:
   ```python
   {
       'source_type': 'build_task',
       'source_id': task_id,
       'activity_type': 'started',
       'title': f'Task started: {task_name}',
       'actor': get_identity_name(identity_id),
       'severity': 'info'
   }
   ```
5. Send notification to assignee

**Return**:
```python
{
    'task_id': 'uuid',
    'status': 'in_progress',
    'started_at': 'timestamp',
    'assigned_to': 'str',
    'active_tasks_count': 'int',
    'validation_warnings': []
}
```

---

### Tool: `complete_task`

**Purpose**: Mark task as completed

**Parameters**:
```python
def complete_task(
    task_id: str,
    actual_hours: float,
    completion_notes: str = None
) -> dict:
```

**Validation Steps**:
1. Validate `task_id` exists
2. Validate current status is 'in_progress' or 'review'
3. Validate `actual_hours > 0`
4. Warn if `actual_hours` significantly differs from estimate
5. Check if completing this task unblocks others

**Side Effects**:
1. Update `status='completed'`
2. Update `actual_hours`
3. Set `completed_at=now()`, `updated_at=now()`
4. Recalculate feature/component completion
5. Unblock dependent tasks
6. Calculate velocity metric
7. Log to `activity_feed`:
   ```python
   {
       'source_type': 'build_task',
       'source_id': task_id,
       'activity_type': 'completed',
       'title': f'Task completed: {task_name}',
       'summary': f'Completed in {actual_hours}h (est: {estimated_hours}h)',
       'actor': get_identity_name(assigned_to_identity_id),
       'severity': 'info'
   }
   ```
8. Notify dependent task assignees

**Return**:
```python
{
    'task_id': 'uuid',
    'status': 'completed',
    'completed_at': 'timestamp',
    'actual_hours': 'float',
    'estimate_accuracy': 'float',  # actual / estimated
    'unblocked_tasks': ['list of task_ids'],
    'validation_warnings': []
}
```

---

### Tool: `add_requirement`

**Purpose**: Define a requirement for a feature

**Parameters**:
```python
def add_requirement(
    feature_id: str,
    requirement_name: str,
    requirement_type: str,
    description: str,
    acceptance_criteria: list[str],
    priority: int = 5,
    must_have: bool = False,
    created_by_identity_id: str = None
) -> dict:
```

**Validation Steps**:
1. Validate `feature_id` exists
2. Validate `requirement_name` (min 5 chars)
3. Validate `requirement_type` in VALID_REQUIREMENT_TYPES
4. Validate `description` (min 20 chars)
5. Validate `acceptance_criteria` has at least 1 item
6. Validate each criterion is not empty
7. Warn if criteria not in Given/When/Then format

**Side Effects**:
1. Generate UUID for `requirement_id`
2. Set `status='draft'`
3. Set `created_at=now()`, `updated_at=now()`
4. Insert into `requirements` table
5. Log to `activity_feed`:
   ```python
   {
       'source_type': 'requirement',
       'source_id': requirement_id,
       'activity_type': 'created',
       'title': f'Requirement defined: {requirement_name}',
       'summary': f'{requirement_type} requirement (must_have={must_have})',
       'actor': get_identity_name(created_by_identity_id),
       'severity': 'info'
   }
   ```

**Return**:
```python
{
    'requirement_id': 'uuid',
    'requirement_name': 'str',
    'status': 'draft',
    'must_have': 'bool',
    'criteria_count': 'int',
    'validation_warnings': []
}
```

---

### Tool: `verify_requirement`

**Purpose**: Mark requirement as verified

**Parameters**:
```python
def verify_requirement(
    requirement_id: str,
    component_id: str,
    test_results: str = None
) -> dict:
```

**Validation Steps**:
1. Validate `requirement_id` exists
2. Validate current status is 'implemented'
3. Validate `component_id` exists
4. Validate component status is 'completed' or 'tested'
5. Validate component `has_tests=true`
6. Warn if test coverage < 80%

**Side Effects**:
1. Update `status='verified'`
2. Update `implemented_by_component_id=component_id`
3. Set `verified_at=now()`, `updated_at=now()`
4. Check if all must-have requirements verified
5. Log to `activity_feed`:
   ```python
   {
       'source_type': 'requirement',
       'source_id': requirement_id,
       'activity_type': 'verified',
       'title': f'Requirement verified: {requirement_name}',
       'summary': f'Implemented by {component_name}',
       'severity': 'info'
   }
   ```
6. If all must-haves verified, notify feature owner

**Return**:
```python
{
    'requirement_id': 'uuid',
    'status': 'verified',
    'verified_at': 'timestamp',
    'implemented_by': 'str',
    'all_must_haves_verified': 'bool',
    'validation_warnings': []
}
```

---

**Version**: 2.0 (Split from original spec)
**Date Split**: 2025-12-26
**Original Version**: 1.0
**Original Date**: 2025-12-04
**Location**: docs/BUILD_TRACKER_SPEC_Workflows.md

See [[BUILD_TRACKER_SPEC_Overview]] for overview and [[BUILD_TRACKER_SPEC_Implementation]] for implementation recommendations.
