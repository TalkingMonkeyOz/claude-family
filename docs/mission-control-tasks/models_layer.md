# Models Layer

**Agent:** coder-haiku
**Timeout:** 180s
**Files:** 4

## Task Specification

Build the models layer using Python dataclasses.

Location: C:/Projects/claude-mission-control/src/models/

Create these 4 files with dataclasses:

1. **project.py**
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID

@dataclass
class Project:
    workspace_id: UUID
    project_name: str
    project_path: str
    project_type: str
    description: str
    created_at: datetime
    updated_at: datetime
    last_session_time: Optional[datetime] = None
    last_session_identity: Optional[str] = None
    open_feedback_count: int = 0
```

2. **session.py** - Session dataclass with all session_history fields

3. **feedback.py** - FeedbackItem and FeedbackComment dataclasses

4. **procedure.py** - Procedure dataclass

Requirements:
- Use dataclasses for all models
- Include type hints (UUID, datetime, Optional, etc.)
- Add __str__ methods for debugging
- Include from_dict() class method to create from database row
