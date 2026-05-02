#!/usr/bin/env python3
"""
Smoke tests for F224 task_queue table governance.

Tests verify that:
1. Direct writes to F224 task_queue tables are blocked
2. OVERRIDE: worker_daemon comment bypasses the block
3. Error messages point to correct MCP tools
"""

import sys
import json
import pytest
from pathlib import Path

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from sql_governance_hook import main as sql_governance_main


def run_governance_hook(sql: str) -> dict:
    """
    Simulate hook execution by calling sql_governance_main with mocked stdin.
    Returns the hook output (allow/deny with reason).
    """
    import io
    from unittest.mock import patch

    hook_input = json.dumps({
        "tool_input": {
            "sql": sql
        }
    })

    output = []

    def mock_print(msg):
        output.append(msg)

    with patch('sys.stdin', io.StringIO(hook_input)):
        with patch('builtins.print', side_effect=mock_print):
            with patch('sys.exit'):  # Prevent sys.exit from stopping test
                sql_governance_main()

    if output:
        return json.loads(output[0]).get("hookSpecificOutput", {})
    return {}


class TestF224TaskQueueGovernance:
    """Test governance of F224 task_queue and related tables."""

    def test_task_queue_direct_insert_blocked(self):
        """Direct INSERT into claude.task_queue should be blocked."""
        sql = "INSERT INTO claude.task_queue (job_template_id, enqueued_at) VALUES (1, NOW())"
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "deny"
        assert "claude.task_queue" in result.get("permissionDecisionReason", "")
        assert "job_enqueue" in result.get("permissionDecisionReason", "")

    def test_task_queue_insert_with_override_allowed(self):
        """INSERT with -- OVERRIDE: worker_daemon should pass."""
        sql = """
        INSERT INTO claude.task_queue (job_template_id, enqueued_at)
        VALUES (1, NOW()) -- OVERRIDE: worker_daemon
        """
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "allow"

    def test_job_templates_direct_insert_blocked(self):
        """Direct INSERT into claude.job_templates should be blocked."""
        sql = "INSERT INTO claude.job_templates (name, kind) VALUES ('test', 'script')"
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "deny"
        assert "claude.job_templates" in result.get("permissionDecisionReason", "")
        assert "job_template" in result.get("permissionDecisionReason", "")

    def test_job_template_versions_direct_insert_blocked(self):
        """Direct INSERT into claude.job_template_versions should be blocked."""
        sql = "INSERT INTO claude.job_template_versions (job_template_id, version_num) VALUES (1, 1)"
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "deny"
        assert "claude.job_template_versions" in result.get("permissionDecisionReason", "")
        assert "publish_version" in result.get("permissionDecisionReason", "")

    def test_job_template_origins_direct_insert_blocked(self):
        """Direct INSERT into claude.job_template_origins should be blocked."""
        sql = "INSERT INTO claude.job_template_origins (job_template_id, origin_kind) VALUES (1, 'hook')"
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "deny"
        assert "claude.job_template_origins" in result.get("permissionDecisionReason", "")
        assert "add_origin" in result.get("permissionDecisionReason", "")

    def test_job_run_history_read_allowed(self):
        """SELECT on claude.job_run_history should be allowed (read-mostly)."""
        sql = "SELECT * FROM claude.job_run_history WHERE job_run_id = 1"
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "allow"

    def test_job_run_history_write_with_override_allowed(self):
        """INSERT into job_run_history with OVERRIDE should pass."""
        sql = """
        INSERT INTO claude.job_run_history (job_run_id, ran_at)
        VALUES (1, NOW()) -- OVERRIDE: worker_daemon
        """
        result = run_governance_hook(sql)
        assert result.get("permissionDecision") == "allow"

    def test_error_message_points_to_correct_tools(self):
        """Error message should guide user to correct MCP tools."""
        sql = "UPDATE claude.task_queue SET status = 'cancelled' WHERE job_run_id = 1"
        result = run_governance_hook(sql)
        reason = result.get("permissionDecisionReason", "")
        assert "job_enqueue" in reason or "job_status" in reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
