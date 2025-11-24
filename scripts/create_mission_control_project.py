#!/usr/bin/env python3
"""
Claude Mission Control - Project Setup Script

Creates the complete project structure for Claude Mission Control at:
C:\Projects\claude-mission-control

This script is run from claude-family repo to bootstrap the new project.

Usage:
    python scripts/create_mission_control_project.py

Author: claude-code-unified
Created: 2025-11-15
"""

import os
from pathlib import Path
import shutil

# Project root
PROJECT_ROOT = Path("C:/Projects/claude-mission-control")

# Project structure
DIRECTORIES = [
    "src/database",
    "src/views",
    "src/services",
    "src/models",
    "docs",
    "tests",
]

# File templates
FILES = {
    "requirements.txt": """# Claude Mission Control - Python Dependencies

# GUI Framework
flet>=0.23.0

# Database
psycopg2-binary>=2.9.9

# Utilities
python-dotenv>=1.0.0

# Development
pytest>=7.4.0
black>=23.0.0
""",

    ".gitignore": """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Project
.env
*.log
*.db

# OS
.DS_Store
Thumbs.db
""",

    ".env.example": """# Claude Mission Control - Environment Configuration

# Database Connection
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_company_foundation
DB_USER=your_username
DB_PASSWORD=your_password

# Application
DEBUG=True
LOG_LEVEL=INFO
""",

    "src/__init__.py": "",
    "src/database/__init__.py": "",
    "src/views/__init__.py": "",
    "src/services/__init__.py": "",
    "src/models/__init__.py": "",
    "tests/__init__.py": "",
}

def create_project_structure():
    """Create the complete project directory structure."""

    print(f"Creating Claude Mission Control project at: {PROJECT_ROOT}")

    # Create root directory
    PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created root directory")

    # Create subdirectories
    for directory in DIRECTORIES:
        dir_path = PROJECT_ROOT / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created {directory}/")

    # Create files
    for file_path, content in FILES.items():
        full_path = PROJECT_ROOT / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
        print(f"✓ Created {file_path}")

    print("\n" + "="*60)
    print("✅ Project structure created successfully!")
    print("="*60)
    print(f"\nNext steps:")
    print(f"1. cd {PROJECT_ROOT}")
    print(f"2. Copy .env.example to .env and configure database credentials")
    print(f"3. python -m venv venv")
    print(f"4. venv\\Scripts\\activate (Windows) or source venv/bin/activate (Linux/Mac)")
    print(f"5. pip install -r requirements.txt")
    print(f"6. python src/main.py")

if __name__ == "__main__":
    create_project_structure()
