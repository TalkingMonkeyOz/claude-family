#!/usr/bin/env python3
"""
Database Logger for Claude Agent Orchestrator

Logs agent spawning events to PostgreSQL for:
- Audit trail
- Cost tracking
- Performance analytics
- Debugging
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import json

try:
    import psycopg
    from psycopg.types.json import Json
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import Json
    except ImportError:
        print("WARNING: psycopg not installed. Install with: pip install psycopg[binary]")
        psycopg = None


class AgentLogger:
    """Logs agent execution to PostgreSQL."""

    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize logger with database connection.

        Args:
            connection_string: PostgreSQL connection string
                             Default: connects to ai_company_foundation database
        """
        if connection_string is None:
            # Default connection from environment/config
            connection_string = (
                "host=localhost "
                "dbname=ai_company_foundation "
                "user=postgres "
                "password=postgres"
            )

        self.connection_string = connection_string
        self.conn = None
        self._ensure_schema()

    def _get_connection(self):
        """Get database connection (create if needed)."""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg.connect(self.connection_string)
        return self.conn

    def _ensure_schema(self):
        """Ensure agent_sessions table exists."""
        if psycopg is None:
            return

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS claude_family.agent_sessions (
                    session_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    agent_type VARCHAR(50) NOT NULL,
                    task_description TEXT NOT NULL,
                    workspace_dir VARCHAR(500) NOT NULL,
                    spawned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    execution_time_seconds DECIMAL(10, 2),
                    success BOOLEAN,
                    output_text TEXT,
                    error_message TEXT,
                    stderr_text TEXT,
                    estimated_cost_usd DECIMAL(10, 4),
                    model VARCHAR(100),
                    mcp_servers JSONB,
                    metadata JSONB,
                    created_by VARCHAR(100) DEFAULT 'claude-code-unified'
                );
            """)

            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_sessions_type
                ON claude_family.agent_sessions(agent_type);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_sessions_spawned
                ON claude_family.agent_sessions(spawned_at DESC);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_sessions_success
                ON claude_family.agent_sessions(success);
            """)

            conn.commit()
            cursor.close()

        except Exception as e:
            print(f"WARNING: Failed to ensure schema: {e}")
            if self.conn:
                self.conn.rollback()

    def log_spawn(
        self,
        agent_type: str,
        task: str,
        workspace_dir: str,
        model: str,
        mcp_servers: list
    ) -> Optional[str]:
        """
        Log agent spawn event.

        Returns:
            session_id (UUID) for tracking, or None if logging fails
        """
        if psycopg is None:
            return None

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO claude_family.agent_sessions
                (agent_type, task_description, workspace_dir, spawned_at, model, mcp_servers)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING session_id;
            """, (
                agent_type,
                task,
                workspace_dir,
                datetime.now(),
                model,
                Json(mcp_servers)
            ))

            session_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()

            return str(session_id)

        except Exception as e:
            print(f"WARNING: Failed to log spawn: {e}")
            if self.conn:
                self.conn.rollback()
            return None

    def log_completion(
        self,
        session_id: str,
        result: Dict[str, Any]
    ):
        """Log agent completion event."""
        if psycopg is None or session_id is None:
            return

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE claude_family.agent_sessions
                SET
                    completed_at = %s,
                    execution_time_seconds = %s,
                    success = %s,
                    output_text = %s,
                    error_message = %s,
                    stderr_text = %s,
                    estimated_cost_usd = %s
                WHERE session_id = %s;
            """, (
                datetime.now(),
                result.get('execution_time_seconds'),
                result.get('success', False),
                result.get('output'),
                result.get('error'),
                result.get('stderr'),
                result.get('estimated_cost_usd'),
                session_id
            ))

            conn.commit()
            cursor.close()

        except Exception as e:
            print(f"WARNING: Failed to log completion: {e}")
            if self.conn:
                self.conn.rollback()

    def get_agent_stats(self, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics for agent usage."""
        if psycopg is None:
            return {}

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            where_clause = ""
            params = []
            if agent_type:
                where_clause = "WHERE agent_type = %s"
                params = [agent_type]

            cursor.execute(f"""
                SELECT
                    COUNT(*) as total_sessions,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_sessions,
                    AVG(execution_time_seconds) as avg_execution_time,
                    SUM(estimated_cost_usd) as total_cost
                FROM claude_family.agent_sessions
                {where_clause};
            """, params)

            row = cursor.fetchone()
            cursor.close()

            return {
                'total_sessions': row[0] or 0,
                'successful_sessions': row[1] or 0,
                'avg_execution_time_seconds': float(row[2]) if row[2] else 0,
                'total_cost_usd': float(row[3]) if row[3] else 0
            }

        except Exception as e:
            print(f"WARNING: Failed to get stats: {e}")
            return {}

    def close(self):
        """Close database connection."""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
