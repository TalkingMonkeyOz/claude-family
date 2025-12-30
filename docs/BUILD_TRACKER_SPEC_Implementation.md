# Build Tracker Data Gateway Specification - Implementation

**Purpose**: Activity logging strategy, database improvements, code patterns, and implementation recommendations.

See [[BUILD_TRACKER_SPEC_Overview]] for context and [[BUILD_TRACKER_SPEC_Workflows]] for workflow specifications.

---

## Activity Logging Strategy

### Activity Feed Table Structure

**Table**: `claude.activity_feed`

**Columns**:
- `id` (uuid, PK)
- `source_type` (varchar, NOT NULL) - 'feature', 'component', 'build_task', 'requirement'
- `source_id` (uuid) - Reference to entity
- `actor` (varchar) - Who performed action
- `activity_type` (varchar, NOT NULL) - 'created', 'updated', 'status_changed', 'completed', etc.
- `title` (varchar, NOT NULL) - Short summary
- `summary` (text) - Detailed description
- `project_name` (varchar) - For filtering
- `severity` (varchar) - 'info', 'warning', 'error', 'success'
- `created_at` (timestamp, default: now())

### Activity Types

**Standard Activities**:
```python
ACTIVITY_TYPES = {
    'created': 'Entity created',
    'updated': 'Entity updated',
    'status_changed': 'Status transition',
    'completed': 'Work completed',
    'started': 'Work started',
    'assigned': 'Task assigned',
    'blocked': 'Work blocked',
    'unblocked': 'Blocker resolved',
    'verified': 'Requirement verified',
    'cancelled': 'Work cancelled',
    'deleted': 'Entity deleted'
}
```

### Logging Function

```python
def log_activity(
    source_type: str,
    source_id: str,
    activity_type: str,
    title: str,
    summary: str = None,
    actor: str = None,
    project_name: str = None,
    severity: str = 'info'
):
    """
    Log activity to activity_feed table

    Args:
        source_type: 'feature', 'component', 'build_task', 'requirement'
        source_id: UUID of entity
        activity_type: Type of activity (from ACTIVITY_TYPES)
        title: Short summary (max 255 chars)
        summary: Detailed description
        actor: Identity who performed action
        project_name: Project context
        severity: 'info', 'warning', 'error', 'success'
    """
    activity = {
        'id': generate_uuid(),
        'source_type': source_type,
        'source_id': source_id,
        'actor': actor,
        'activity_type': activity_type,
        'title': title[:255],  # Truncate if needed
        'summary': summary,
        'project_name': project_name,
        'severity': severity,
        'created_at': now()
    }

    insert_into_activity_feed(activity)

    # Optional: Trigger notifications for high-severity
    if severity in ['error', 'warning']:
        send_notification(activity)
```

### Indexing Strategy

```sql
-- Already exists
CREATE INDEX idx_activity_feed_time ON claude.activity_feed (created_at DESC);
CREATE INDEX idx_activity_feed_project ON claude.activity_feed (project_name, created_at DESC);

-- Recommended additions
CREATE INDEX idx_activity_feed_source ON claude.activity_feed (source_type, source_id);
CREATE INDEX idx_activity_feed_actor ON claude.activity_feed (actor, created_at DESC);
CREATE INDEX idx_activity_feed_type ON claude.activity_feed (activity_type, created_at DESC);
```

### Query Examples

```sql
-- Get recent activities for a feature
SELECT
    activity_type,
    title,
    summary,
    actor,
    created_at
FROM claude.activity_feed
WHERE source_type = 'feature'
  AND source_id = '...'
ORDER BY created_at DESC
LIMIT 50;

-- Get all activities for a project today
SELECT
    source_type,
    activity_type,
    title,
    actor,
    created_at
FROM claude.activity_feed
WHERE project_name = 'my-project'
  AND created_at >= CURRENT_DATE
ORDER BY created_at DESC;

-- Get error/warning activities
SELECT
    source_type,
    title,
    summary,
    severity,
    created_at
FROM claude.activity_feed
WHERE severity IN ('error', 'warning')
  AND created_at >= NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

---

## Implementation Recommendations

### 1. Database Schema Improvements

**Priority 1 - Critical**:

```sql
-- Add foreign key constraints (enable referential integrity)
ALTER TABLE claude.components
ADD CONSTRAINT fk_components_feature
FOREIGN KEY (feature_id) REFERENCES claude.features(feature_id)
ON DELETE CASCADE;

ALTER TABLE claude.build_tasks
ADD CONSTRAINT fk_tasks_component
FOREIGN KEY (component_id) REFERENCES claude.components(component_id)
ON DELETE SET NULL;

ALTER TABLE claude.build_tasks
ADD CONSTRAINT fk_tasks_feature
FOREIGN KEY (feature_id) REFERENCES claude.features(feature_id)
ON DELETE CASCADE;

ALTER TABLE claude.requirements
ADD CONSTRAINT fk_requirements_feature
FOREIGN KEY (feature_id) REFERENCES claude.features(feature_id)
ON DELETE CASCADE;

-- Standardize status values (fix 'complete' vs 'completed')
UPDATE claude.components SET status = 'completed' WHERE status = 'complete';

-- Add missing fields
ALTER TABLE claude.features
ADD COLUMN blocked_reason TEXT,
ADD COLUMN cancellation_reason TEXT;

ALTER TABLE claude.build_tasks
ADD COLUMN completion_notes TEXT;

ALTER TABLE claude.requirements
ADD COLUMN verified_by_test_run_id UUID;
```

**Priority 2 - Important**:

```sql
-- Add check constraints for enums
ALTER TABLE claude.features
ADD CONSTRAINT chk_feature_status
CHECK (status IN ('not_started', 'planned', 'in_progress', 'blocked', 'on_hold', 'completed', 'cancelled'));

ALTER TABLE claude.features
ADD CONSTRAINT chk_feature_type
CHECK (feature_type IN ('feature', 'enhancement', 'bug_fix', 'refactoring', 'integration', 'infrastructure', 'ui', 'api', 'data'));

ALTER TABLE claude.components
ADD CONSTRAINT chk_component_status
CHECK (status IN ('planned', 'in_progress', 'completed', 'tested', 'documented', 'deprecated'));

ALTER TABLE claude.build_tasks
ADD CONSTRAINT chk_task_status
CHECK (status IN ('todo', 'in_progress', 'blocked', 'review', 'completed', 'cancelled'));

-- Add check for priority range
ALTER TABLE claude.features
ADD CONSTRAINT chk_feature_priority
CHECK (priority >= 1 AND priority <= 10);

ALTER TABLE claude.build_tasks
ADD CONSTRAINT chk_task_priority
CHECK (priority >= 1 AND priority <= 10);

-- Add check for completion percentage
ALTER TABLE claude.features
ADD CONSTRAINT chk_completion_percentage
CHECK (completion_percentage >= 0 AND completion_percentage <= 100);
```

**Priority 3 - Nice to Have**:

```sql
-- Add indexes for common queries
CREATE INDEX idx_features_status ON claude.features(status);
CREATE INDEX idx_features_project ON claude.features(project_id, status);
CREATE INDEX idx_components_feature ON claude.components(feature_id, status);
CREATE INDEX idx_tasks_component ON claude.build_tasks(component_id, status);
CREATE INDEX idx_tasks_feature ON claude.build_tasks(feature_id, status);
CREATE INDEX idx_tasks_assigned ON claude.build_tasks(assigned_to_identity_id, status);
CREATE INDEX idx_requirements_feature ON claude.requirements(feature_id, status);

-- Add NOT NULL constraints for required fields
ALTER TABLE claude.features
ALTER COLUMN feature_name SET NOT NULL,
ALTER COLUMN feature_type SET NOT NULL,
ALTER COLUMN status SET NOT NULL,
ALTER COLUMN project_id SET NOT NULL;

ALTER TABLE claude.components
ALTER COLUMN component_name SET NOT NULL,
ALTER COLUMN component_type SET NOT NULL,
ALTER COLUMN feature_id SET NOT NULL,
ALTER COLUMN status SET NOT NULL;

ALTER TABLE claude.build_tasks
ALTER COLUMN task_name SET NOT NULL,
ALTER COLUMN task_description SET NOT NULL,
ALTER COLUMN task_type SET NOT NULL,
ALTER COLUMN status SET NOT NULL;
```

### 2. Application Layer Patterns

**Validation Layer**:
```python
# validators.py
class BuildTrackerValidator:
    """Centralized validation for Build Tracker domain"""

    def validate_feature(self, data, operation='create'):
        errors = []
        warnings = []

        # Run validation checks
        if operation == 'create':
            errors.extend(self._validate_feature_create(data))
        elif operation == 'update':
            errors.extend(self._validate_feature_update(data))

        return {'errors': errors, 'warnings': warnings}

    def validate_status_transition(self, entity_type, current, new):
        # Check valid transitions
        pass
```

**Service Layer**:
```python
# services.py
class FeatureService:
    """Business logic for features"""

    def __init__(self, db, validator, activity_logger):
        self.db = db
        self.validator = validator
        self.activity = activity_logger

    def create_feature(self, data):
        # Validate
        validation = self.validator.validate_feature(data, 'create')
        if validation['errors']:
            raise ValidationError(validation['errors'])

        # Generate ID
        data['feature_id'] = generate_uuid()
        data['status'] = 'not_started'
        data['completion_percentage'] = 0
        data['created_at'] = now()
        data['updated_at'] = now()

        # Insert
        feature = self.db.insert('features', data)

        # Log activity
        self.activity.log(
            source_type='feature',
            source_id=feature['feature_id'],
            activity_type='created',
            title=f"Feature created: {feature['feature_name']}",
            summary=f"New {feature['feature_type']} feature",
            project_name=get_project_name(feature['project_id'])
        )

        return feature
```

**Data Access Layer**:
```python
# repositories.py
class FeatureRepository:
    """Database access for features"""

    def __init__(self, db):
        self.db = db

    def get_by_id(self, feature_id):
        return self.db.query_one(
            "SELECT * FROM claude.features WHERE feature_id = %s",
            [feature_id]
        )

    def get_with_children(self, feature_id):
        """Get feature with all components, tasks, requirements"""
        return self.db.query_one("""
            SELECT
                f.*,
                json_agg(DISTINCT c.*) FILTER (WHERE c.component_id IS NOT NULL) as components,
                json_agg(DISTINCT t.*) FILTER (WHERE t.task_id IS NOT NULL) as tasks,
                json_agg(DISTINCT r.*) FILTER (WHERE r.requirement_id IS NOT NULL) as requirements
            FROM claude.features f
            LEFT JOIN claude.components c ON c.feature_id = f.feature_id
            LEFT JOIN claude.build_tasks t ON t.feature_id = f.feature_id
            LEFT JOIN claude.requirements r ON r.feature_id = f.feature_id
            WHERE f.feature_id = %s
            GROUP BY f.feature_id
        """, [feature_id])
```

### 3. API Design

**RESTful Endpoints**:

```
POST   /api/features                    - Create feature
GET    /api/features/:id                - Get feature
PUT    /api/features/:id                - Update feature
DELETE /api/features/:id                - Delete feature
PATCH  /api/features/:id/status         - Change status
GET    /api/features/:id/completion     - Get completion details
POST   /api/features/:id/complete       - Complete feature (validation gate)

POST   /api/components                  - Create component
GET    /api/components/:id              - Get component
PUT    /api/components/:id              - Update component
PATCH  /api/components/:id/complete     - Mark complete

POST   /api/tasks                       - Create task
GET    /api/tasks/:id                   - Get task
PATCH  /api/tasks/:id/start             - Start task
PATCH  /api/tasks/:id/complete          - Complete task
GET    /api/tasks/ready                 - Get unblocked tasks

POST   /api/requirements                - Create requirement
GET    /api/requirements/:id            - Get requirement
PATCH  /api/requirements/:id/verify     - Verify requirement

GET    /api/activity                    - Get activity feed
GET    /api/activity/feature/:id        - Get feature activity
```

**Response Format**:
```json
{
    "success": true,
    "data": {
        "feature_id": "uuid",
        "feature_name": "str",
        ...
    },
    "validation": {
        "errors": [],
        "warnings": [
            "No tests for this component"
        ]
    },
    "metadata": {
        "completion_percentage": 75,
        "feature_ready_to_complete": false
    }
}
```

### 4. Automated Workflows

**Triggers**:

```sql
-- Auto-update completion percentage
CREATE OR REPLACE FUNCTION update_feature_completion()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE claude.features
    SET completion_percentage = (
        SELECT COALESCE(
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE status IN ('completed', 'tested', 'documented')) /
                NULLIF(COUNT(*), 0)
            ), 0
        )
        FROM claude.components
        WHERE feature_id = NEW.feature_id
    ),
    updated_at = NOW()
    WHERE feature_id = NEW.feature_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_component_completion
AFTER INSERT OR UPDATE OF status ON claude.components
FOR EACH ROW
EXECUTE FUNCTION update_feature_completion();
```

**Background Jobs**:

```python
# jobs.py
class BuildTrackerJobs:
    """Scheduled jobs for build tracker"""

    def check_stale_tasks(self):
        """Find tasks in 'in_progress' for > 7 days"""
        stale_tasks = self.db.query("""
            SELECT task_id, task_name, assigned_to_identity_id, started_at
            FROM claude.build_tasks
            WHERE status = 'in_progress'
              AND started_at < NOW() - INTERVAL '7 days'
        """)

        for task in stale_tasks:
            self.notify_stale_task(task)

    def check_blocked_tasks(self):
        """Find tasks blocked by completed tasks"""
        unblocked = self.db.query("""
            SELECT t.task_id, t.task_name, t.blocked_by_task_id
            FROM claude.build_tasks t
            JOIN claude.build_tasks b ON t.blocked_by_task_id = b.task_id
            WHERE t.status = 'blocked'
              AND b.status = 'completed'
        """)

        for task in unblocked:
            self.notify_unblocked(task)

    def check_completion_readiness(self):
        """Find features with 100% completion but not marked complete"""
        ready = self.db.query("""
            SELECT feature_id, feature_name, completion_percentage
            FROM claude.features
            WHERE status = 'in_progress'
              AND completion_percentage = 100
        """)

        for feature in ready:
            can_complete, checks = self.validator.can_complete_feature(
                feature['feature_id']
            )
            if can_complete:
                self.notify_ready_to_complete(feature)
```

### 5. Testing Strategy

**Unit Tests**:
```python
# test_validators.py
def test_feature_name_validation():
    validator = BuildTrackerValidator()

    # Too short
    result = validator.validate_feature({'feature_name': 'abc'})
    assert len(result['errors']) > 0

    # Valid
    result = validator.validate_feature({'feature_name': 'Valid Name'})
    assert 'feature_name' not in [e['field'] for e in result['errors']]

# test_services.py
def test_create_feature():
    service = FeatureService(mock_db, validator, logger)

    data = {
        'feature_name': 'Test Feature',
        'feature_type': 'feature',
        'project_id': 'existing-uuid'
    }

    feature = service.create_feature(data)

    assert feature['feature_id'] is not None
    assert feature['status'] == 'not_started'
    assert feature['completion_percentage'] == 0
```

**Integration Tests**:
```python
# test_workflows.py
def test_feature_to_completion_workflow():
    """Test complete workflow from feature creation to completion"""

    # Create feature
    feature = create_feature(...)
    assert feature['status'] == 'not_started'

    # Add components
    comp1 = add_component(feature['feature_id'], ...)
    comp2 = add_component(feature['feature_id'], ...)

    # Complete components
    complete_component(comp1['component_id'], ...)
    complete_component(comp2['component_id'], ...)

    # Check feature completion updated
    feature = get_feature(feature['feature_id'])
    assert feature['completion_percentage'] == 100

    # Complete feature
    result = update_feature_status(feature['feature_id'], 'completed')
    assert result['success'] == True
```

---

## Summary

This specification provides a comprehensive framework for implementing a robust Data Gateway for the Build Tracker domain. Key takeaways:

1. **Database needs improvements**: Add FK constraints, standardize status values, add missing fields
2. **Validation is critical**: Implement multi-layer validation (database, application, business rules)
3. **Activity logging is essential**: Track all changes for audit trail and notifications
4. **Workflows must enforce rules**: Status transitions, dependency checking, completion gating
5. **Automation reduces errors**: Auto-calculate completion %, trigger notifications, check for stale work

**Next Steps**:
1. Implement Priority 1 database changes
2. Build validation layer
3. Create service layer with workflow tools
4. Add comprehensive tests
5. Deploy and monitor

---

**Version**: 2.0 (Split from original spec)
**Date Split**: 2025-12-26
**Original Version**: 1.0
**Original Date**: 2025-12-04
**Location**: docs/BUILD_TRACKER_SPEC_Implementation.md

See [[BUILD_TRACKER_SPEC_Overview]] for overview, [[BUILD_TRACKER_SPEC_Table_Analysis]] for table definitions, and [[BUILD_TRACKER_SPEC_Workflows]] for workflow specifications.
