#!/usr/bin/env python3
"""
Claude Mission Control - Project Setup Script
Creates the project structure at C:/Projects/claude-mission-control
"""

import os
from pathlib import Path

PROJECT_ROOT = Path("C:/Projects/claude-mission-control")

DIRECTORIES = [
    "src/database",
    "src/views",
    "src/services",
    "src/models",
    "docs",
    "tests",
]

FILES = {
    "requirements.txt": """# Claude Mission Control Dependencies
flet>=0.23.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
pytest>=7.4.0
black>=23.0.0
""",
    ".gitignore": """__pycache__/
*.py[cod]
venv/
.env
*.log
.DS_Store
""",
    "src/__init__.py": "",
    "src/database/__init__.py": "",
    "src/views/__init__.py": "",
    "src/services/__init__.py": "",
    "src/models/__init__.py": "",
    "tests/__init__.py": "",
}

def create_project():
    print(f"Creating project at: {PROJECT_ROOT}")
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    
    for directory in DIRECTORIES:
        (PROJECT_ROOT / directory).mkdir(parents=True, exist_ok=True)
        print(f"OK - {directory}/")
    
    for file_path, content in FILES.items():
        full_path = PROJECT_ROOT / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"OK - {file_path}")
    
    print("\nProject created successfully!")

if __name__ == "__main__":
    create_project()
