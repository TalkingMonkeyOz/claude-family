#!/bin/bash
# Generate all Claude Mission Control source files

MC_ROOT="/c/Projects/claude-mission-control"

echo "Generating Claude Mission Control source files..."

# Main application
cat > "$MC_ROOT/src/main.py" << 'EOF'
#!/usr/bin/env python3
"""
Claude Mission Control - Main Application

Central coordination hub for Claude Family instances.
Focus: Claude coordination, not project management.

Author: claude-code-unified
Created: 2025-11-15
"""

import flet as ft
from views.launcher import ProjectLauncher
from views.sessions import SessionDashboard
from views.feedback import FeedbackHub
from views.procedures import ProcedureViewer

def main(page: ft.Page):
    """Main application entry point."""
    
    # Configure page
    page.title = "Claude Mission Control"
    page.window_width = 1400
    page.window_height = 900
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    
    # Navigation rail
    def route_change(e):
        page.views.clear()
        
        if page.route == "/":
            page.views.append(ProjectLauncher(page))
        elif page.route == "/sessions":
            page.views.append(SessionDashboard(page))
        elif page.route == "/feedback":
            page.views.append(FeedbackHub(page))
        elif page.route == "/procedures":
            page.views.append(ProcedureViewer(page))
        
        page.update()
    
    page.on_route_change = route_change
    page.go(page.route)

if __name__ == "__main__":
    ft.app(target=main)
EOF

echo "OK - src/main.py"

# Database connection
cat > "$MC_ROOT/src/database/connection.py" << 'EOF'
"""
Database connection management for Claude Mission Control.

Provides PostgreSQL connection pooling and context managers.
"""

import psycopg2
from psycopg2 import pool
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connection pool (lazy initialization)
_connection_pool = None

def get_connection_pool():
    """Get or create the PostgreSQL connection pool."""
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "ai_company_foundation"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
    
    return _connection_pool

class DatabaseConnection:
    """Context manager for database connections."""
    
    def __enter__(self):
        self.pool = get_connection_pool()
        self.conn = self.pool.getconn()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        self.pool.putconn(self.conn)
        return False

def execute_query(query, params=None, fetch=True):
    """
    Execute a SQL query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters (tuple or dict)
        fetch: Whether to fetch results (SELECT) or just execute (INSERT/UPDATE/DELETE)
    
    Returns:
        List of dicts for SELECT queries, None for others
    """
    with DatabaseConnection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            
            if fetch:
                columns = [desc[0] for desc in cur.description]
                return [dict(zip(columns, row)) for row in cur.fetchall()]
            else:
                conn.commit()
                return None
EOF

echo "OK - src/database/connection.py"

echo "All source files generated!"
