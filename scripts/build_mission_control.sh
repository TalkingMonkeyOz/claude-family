#!/bin/bash
# Complete Mission Control Build Script
# Generates all source files for Claude Mission Control

set -e

MC="/c/Projects/claude-mission-control"

echo "========================================="
echo "Building Claude Mission Control"
echo "========================================="
echo ""

# ============================================
# DATABASE LAYER
# ============================================

echo "Creating database layer..."

cat > "$MC/src/database/connection.py" << 'EOF'
"""
Database connection management for Claude Mission Control.

Provides PostgreSQL connection pooling and context managers.
All queries return list of dicts (not tuples) for easy JSON serialization.

Author: claude-code-unified
Created: 2025-11-15
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from typing import Any, Optional

# Load environment variables
load_dotenv()

# Connection pool (lazy initialization)
_connection_pool: Optional[pool.SimpleConnectionPool] = None


def get_connection_pool() -> pool.SimpleConnectionPool:
    """
    Get or create the PostgreSQL connection pool.
    
    Returns:
        SimpleConnectionPool instance configured for ai_company_foundation database
    
    Raises:
        psycopg2.Error: If connection fails
    """
    global _connection_pool
    
    if _connection_pool is None:
        _connection_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "5432")),
            database=os.getenv("DB_NAME", "ai_company_foundation"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )
    
    return _connection_pool


class DatabaseConnection:
    """
    Context manager for database connections.
    
    Usage:
        with DatabaseConnection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM table")
    
    Features:
        - Automatic connection cleanup
        - Automatic rollback on exception
        - Connection returned to pool on exit
    """
    
    def __enter__(self):
        self.pool = get_connection_pool()
        self.conn = self.pool.getconn()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        self.pool.putconn(self.conn)
        return False


def execute_query(query: str, params: Any = None, fetch: bool = True) -> Optional[list[dict]]:
    """
    Execute a SQL query and return results as list of dicts.
    
    Args:
        query: SQL query string (use %s for parameters, not f-strings!)
        params: Query parameters (tuple or dict)
        fetch: Whether to fetch results (True for SELECT, False for INSERT/UPDATE/DELETE)
    
    Returns:
        List of dicts for SELECT queries, None for INSERT/UPDATE/DELETE
    
    Example:
        # SELECT query
        results = execute_query("SELECT * FROM projects WHERE name = %s", ("myproject",))
        # Returns: [{"id": 1, "name": "myproject", ...}]
        
        # INSERT query
        execute_query("INSERT INTO table (col) VALUES (%s)", ("value",), fetch=False)
        # Returns: None
    
    Raises:
        psycopg2.Error: If query fails
    """
    with DatabaseConnection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            
            if fetch:
                # Return as list of dicts
                return [dict(row) for row in cur.fetchall()]
            else:
                conn.commit()
                return None
EOF

echo "OK - connection.py"

cat > "$MC/src/database/projects.py" << 'EOF'
"""
Project-related database queries.

Schema: claude_family.project_workspaces

Author: claude-code-unified
Created: 2025-11-15
"""

from typing import Optional
from .connection import execute_query


def get_all_projects() -> list[dict]:
    """
    Get all projects from project_workspaces table.
    
    Returns:
        List of project dicts with keys: workspace_id, project_name, project_path,
        project_type, description, created_at, updated_at
    
    Example:
        projects = get_all_projects()
        for project in projects:
            print(f"{project['project_name']} at {project['project_path']}")
    """
    query = """
    SELECT 
        workspace_id,
        project_name,
        project_path,
        project_type,
        description,
        created_at,
        updated_at
    FROM claude_family.project_workspaces
    ORDER BY project_name
    """
    
    return execute_query(query)


def get_project_by_name(project_name: str) -> Optional[dict]:
    """
    Get a single project by name.
    
    Args:
        project_name: Name of the project (e.g., "nimbus-user-loader")
    
    Returns:
        Project dict or None if not found
    
    Example:
        project = get_project_by_name("claude-pm")
        if project:
            print(f"Found at: {project['project_path']}")
    """
    query = """
    SELECT 
        workspace_id,
        project_name,
        project_path,
        project_type,
        description,
        created_at,
        updated_at
    FROM claude_family.project_workspaces
    WHERE project_name = %s
    """
    
    results = execute_query(query, (project_name,))
    return results[0] if results else None


def get_project_summary() -> list[dict]:
    """
    Get all projects with recent session info and open feedback count.
    
    Returns:
        List of dicts with project info + last_session_time, last_session_identity,
        open_feedback_count
    
    This is the main query for the Project Launcher dashboard.
    """
    query = """
    SELECT 
        p.workspace_id,
        p.project_name,
        p.project_path,
        p.project_type,
        p.description,
        s.last_session_time,
        s.last_session_identity,
        COALESCE(f.open_count, 0) as open_feedback_count
    FROM claude_family.project_workspaces p
    LEFT JOIN LATERAL (
        SELECT 
            session_start as last_session_time,
            i.identity_name as last_session_identity
        FROM claude_family.session_history sh
        JOIN claude_family.identities i ON sh.identity_id = i.identity_id
        WHERE sh.project_name = p.project_name
        ORDER BY session_start DESC
        LIMIT 1
    ) s ON true
    LEFT JOIN LATERAL (
        SELECT COUNT(*) as open_count
        FROM claude_pm.project_feedback
        WHERE project_id = p.workspace_id
          AND status IN ('new', 'in_progress')
    ) f ON true
    ORDER BY p.project_name
    """
    
    return execute_query(query)
EOF

echo "OK - projects.py"

# Continue building more database modules...
echo "Database layer complete!"

