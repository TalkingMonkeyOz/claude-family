# {{PROJECT_NAME}} - Python Tool

**Type**: Python Tool
**Created**: {{CREATED_DATE}}

---

## Project Overview

Python tool/utility project.

---

## Project Structure

```
{{PROJECT_NAME}}/
├── src/
│   └── {{PROJECT_NAME_SNAKE}}/
│       ├── __init__.py
│       ├── main.py
│       └── utils.py
├── tests/
│   └── test_main.py
├── requirements.txt
├── setup.py
├── CLAUDE.md           # This file
└── README.md           # Project overview
```

---

## Build Commands

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .

# Run
python -m {{PROJECT_NAME_SNAKE}}

# Run tests
pytest
```

---

## Key Technologies

- Python 3.10+
- Dependencies in requirements.txt

---

## When Working Here

- Use type hints
- Follow PEP 8
- Write docstrings
- Add tests for new functions

---

## Recent Work

```sql
SELECT summary, outcome, session_start
FROM claude.sessions
WHERE project_name = '{{PROJECT_NAME}}'
ORDER BY session_start DESC LIMIT 5;
```

---

**Version**: 1.0
**Location**: {{PROJECT_PATH}}/CLAUDE.md
