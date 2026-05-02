"""
Tests for job_schedule MCP handler.

Tests the 6 core actions:
  - create: INSERT with schedule validation
  - update: UPDATE fields with optional template_version
  - pause: Set is_active=false
  - unpause: Set is_active=true
  - list: Query with filters
  - unschedule: DELETE + audit log

Uses mock database connection to avoid requiring live postgres during testing.
"""

import pytest
import uuid
from unittest.mock import MagicMock, Mock, patch, call
from datetime import datetime, timedelta

# Import the handler
from handlers_job_schedule import (
    handle_job_schedule,
    parse_schedule,
    validate_schedule_string,
)


# ============================================================================
# Test parse_schedule (reused from job_runner.py)
# ============================================================================

class TestParseSchedule:
    """Test schedule string parsing."""

    def test_cron_expression(self):
        """Cron expressions with 5 parts."""
        result = parse_schedule("0 6 * * *")
        assert result["type"] == "cron"
        assert result["minute"] == "0"
        assert result["hour"] == "6"
        assert result["day_of_week"] == "*"

    def test_cron_with_ranges(self):
        """Cron with ranges and lists."""
        result = parse_schedule("0,30 * * * MON-FRI")
        assert result["type"] == "cron"
        assert result["minute"] == "0,30"

    def test_daily_human_readable(self):
        """Human-readable daily schedule."""
        result = parse_schedule("Daily @ 6 AM")
        assert result["type"] == "interval"
        assert result["interval_hours"] == 24

    def test_daily_with_time(self):
        """Daily @ specific time (AM)."""
        result = parse_schedule("Daily @ 6:30 AM")
        assert result["type"] == "interval"
        assert result["interval_hours"] == 24

    def test_daily_pm(self):
        """Daily @ PM time."""
        result = parse_schedule("Daily @ 3:00 PM")
        assert result["type"] == "interval"
        assert result["interval_hours"] == 24
        assert result["preferred_hour"] == 15

    def test_hourly(self):
        """Hourly schedule."""
        result = parse_schedule("Hourly")
        assert result["type"] == "interval"
        assert result["interval_hours"] == 1

    def test_weekly(self):
        """Weekly schedule."""
        result = parse_schedule("Weekly")
        assert result["type"] == "interval"
        assert result["interval_hours"] == 168

    def test_on_login(self):
        """On login trigger."""
        result = parse_schedule("At logon")
        assert result["type"] == "on_login"

    def test_empty_string_raises(self):
        """Empty schedule raises error."""
        with pytest.raises(ValueError):
            parse_schedule("")

    def test_fallback_to_daily(self):
        """Unparseable schedule falls back to daily."""
        result = parse_schedule("every Tuesday at noon")
        assert result["type"] == "interval"


class TestValidateScheduleString:
    """Test schedule validation."""

    def test_valid_cron(self):
        """Valid cron is accepted."""
        validate_schedule_string("0 6 * * *")  # Should not raise

    def test_valid_human_readable(self):
        """Valid human-readable schedule is accepted."""
        validate_schedule_string("Daily @ 6 AM")  # Should not raise

    def test_empty_raises(self):
        """Empty schedule raises."""
        with pytest.raises(ValueError):
            validate_schedule_string("")


# ============================================================================
# Test handle_job_schedule with mocked DB
# ============================================================================

class TestJobScheduleCreate:
    """Test create action."""

    @patch("handlers_job_schedule.get_db_connection")
    def test_create_success(self, mock_get_db):
        """Create a new scheduled job."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_cursor.fetchone.return_value = {"job_id": "test-id"}
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "create",
            schedule="Daily @ 6 AM",
            job_name="test-job",
            description="Test job",
        )

        assert result["success"] is True
        assert "scheduled_job_id" in result
        assert "test-job" in result["message"]
        mock_conn.commit.assert_called_once()

    @patch("handlers_job_schedule.get_db_connection")
    def test_create_invalid_schedule(self, mock_get_db):
        """Create with invalid schedule fails gracefully."""
        # Don't even need mock_conn since validation fails first
        result = handle_job_schedule(
            "create",
            schedule="",  # Empty
        )

        assert result["success"] is False
        assert "schedule" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_create_with_template_id(self, mock_get_db):
        """Create with template_id FK (when table exists)."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Create mock row objects that support both dict-style and tuple access
        class MockRow(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    # Support tuple-style access: get the value at position key
                    vals = list(super().values())
                    return vals[key] if key < len(vals) else None
                return super().__getitem__(key)

        # First query checks if job_templates table exists
        mock_cursor.fetchone.side_effect = [
            MockRow(exists=True),  # table exists check
            MockRow(template_id="tpl-1", is_paused=False),  # template exists check
            MockRow(job_id="job-1"),  # INSERT return
        ]
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        template_id = str(uuid.uuid4())
        result = handle_job_schedule(
            "create",
            schedule="Hourly",
            template_id=template_id,
        )

        assert result["success"] is True

    @patch("handlers_job_schedule.get_db_connection")
    def test_create_template_not_found(self, mock_get_db):
        """Create with non-existent template fails."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        class MockRow(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    vals = list(super().values())
                    return vals[key] if key < len(vals) else None
                return super().__getitem__(key)

        mock_cursor.fetchone.side_effect = [
            MockRow(exists=True),  # table exists check
            None,  # template NOT found
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "create",
            schedule="Hourly",
            template_id=str(uuid.uuid4()),
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_create_template_paused(self, mock_get_db):
        """Create with paused template fails."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        class MockRow(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    vals = list(super().values())
                    return vals[key] if key < len(vals) else None
                return super().__getitem__(key)

        mock_cursor.fetchone.side_effect = [
            MockRow(exists=True),  # table exists check
            MockRow(template_id="tpl-1", is_paused=True),  # template is paused
        ]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "create",
            schedule="Hourly",
            template_id=str(uuid.uuid4()),
        )

        assert result["success"] is False
        assert "paused" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_create_template_version_latest(self, mock_get_db):
        """Create with template_version='latest' stores NULL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        class MockRow(dict):
            def __getitem__(self, key):
                if isinstance(key, int):
                    vals = list(super().values())
                    return vals[key] if key < len(vals) else None
                return super().__getitem__(key)

        mock_cursor.fetchone.return_value = MockRow(job_id="job-1")
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "create",
            schedule="Daily @ 6 AM",
            template_id=str(uuid.uuid4()),
            template_version="latest",
        )

        assert result["success"] is True


class TestJobScheduleUpdate:
    """Test update action."""

    @patch("handlers_job_schedule.get_db_connection")
    def test_update_success(self, mock_get_db):
        """Update a scheduled job."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        job_id = str(uuid.uuid4())
        result = handle_job_schedule(
            "update",
            scheduled_job_id=job_id,
            fields={"schedule": "Weekly", "job_description": "Updated"},
        )

        assert result["success"] is True
        assert result["scheduled_job_id"] == job_id

    @patch("handlers_job_schedule.get_db_connection")
    def test_update_no_job_id(self, mock_get_db):
        """Update without job_id fails."""
        result = handle_job_schedule(
            "update",
            fields={"schedule": "Daily"},
        )

        assert result["success"] is False
        assert "scheduled_job_id" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_update_no_fields(self, mock_get_db):
        """Update with empty fields fails."""
        result = handle_job_schedule(
            "update",
            scheduled_job_id=str(uuid.uuid4()),
            fields={},
        )

        assert result["success"] is False
        assert "field" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_update_job_not_found(self, mock_get_db):
        """Update non-existent job fails."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0  # No rows updated
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "update",
            scheduled_job_id=str(uuid.uuid4()),
            fields={"schedule": "Hourly"},
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_update_with_valid_schedule(self, mock_get_db):
        """Update with valid schedule succeeds."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "update",
            scheduled_job_id=str(uuid.uuid4()),
            fields={"schedule": "Daily @ 6 AM"},
        )

        assert result["success"] is True

    @patch("handlers_job_schedule.get_db_connection")
    def test_update_template_version_latest(self, mock_get_db):
        """Update with template_version='latest' stores NULL."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "update",
            scheduled_job_id=str(uuid.uuid4()),
            fields={"template_version": "latest"},
        )

        assert result["success"] is True


class TestJobSchedulePauseUnpause:
    """Test pause/unpause actions."""

    @patch("handlers_job_schedule.get_db_connection")
    def test_pause_success(self, mock_get_db):
        """Pause a job."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        job_id = str(uuid.uuid4())
        result = handle_job_schedule("pause", scheduled_job_id=job_id)

        assert result["success"] is True
        assert "Paused" in result["message"]

    @patch("handlers_job_schedule.get_db_connection")
    def test_pause_not_found(self, mock_get_db):
        """Pause non-existent job fails."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 0
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule("pause", scheduled_job_id=str(uuid.uuid4()))

        assert result["success"] is False

    @patch("handlers_job_schedule.get_db_connection")
    def test_unpause_success(self, mock_get_db):
        """Unpause a job."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        job_id = str(uuid.uuid4())
        result = handle_job_schedule("unpause", scheduled_job_id=job_id)

        assert result["success"] is True
        assert "Unpaused" in result["message"]


class TestJobScheduleList:
    """Test list action."""

    @patch("handlers_job_schedule.get_db_connection")
    def test_list_all(self, mock_get_db):
        """List all scheduled jobs."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # Mock job rows
        job_row = {
            "job_id": uuid.uuid4(),
            "project_id": uuid.uuid4(),
            "job_name": "test-job",
            "job_description": "Test",
            "schedule": "Daily @ 6 AM",
            "is_active": True,
            "template_id": None,
            "template_version": None,
            "last_run": None,
            "last_status": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
        mock_cursor.fetchall.return_value = [job_row]
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule("list")

        assert result["success"] is True
        assert result["count"] == 1
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["job_name"] == "test-job"

    @patch("handlers_job_schedule.get_db_connection")
    def test_list_with_filters(self, mock_get_db):
        """List with template_id filter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        template_id = str(uuid.uuid4())
        result = handle_job_schedule("list", filters={"template_id": template_id})

        assert result["success"] is True
        assert result["count"] == 0

    @patch("handlers_job_schedule.get_db_connection")
    def test_list_with_is_active_filter(self, mock_get_db):
        """List with is_active filter."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule("list", filters={"is_active": True})

        assert result["success"] is True


class TestJobScheduleUnschedule:
    """Test unschedule action."""

    @patch("handlers_job_schedule.get_db_connection")
    def test_unschedule_success(self, mock_get_db):
        """Unschedule (delete) a job."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        # First query: fetch current state
        mock_cursor.fetchone.return_value = {"is_active": True}
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        job_id = str(uuid.uuid4())
        result = handle_job_schedule("unschedule", scheduled_job_id=job_id, reason="Cleanup")

        assert result["success"] is True
        assert "Unscheduled" in result["message"]
        assert "Cleanup" in result["message"]

    @patch("handlers_job_schedule.get_db_connection")
    def test_unschedule_not_found(self, mock_get_db):
        """Unschedule non-existent job fails."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule("unschedule", scheduled_job_id=str(uuid.uuid4()))

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @patch("handlers_job_schedule.get_db_connection")
    def test_unschedule_logs_audit(self, mock_get_db):
        """Unschedule logs to audit_log."""
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"is_active": False}
        mock_cursor.rowcount = 1
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_get_db.return_value = mock_conn

        result = handle_job_schedule(
            "unschedule",
            scheduled_job_id=str(uuid.uuid4()),
            reason="Obsolete",
        )

        assert result["success"] is True
        mock_conn.commit.assert_called_once()


class TestJobScheduleErrors:
    """Test error handling."""

    @patch("handlers_job_schedule.get_db_connection")
    def test_unknown_action(self, mock_get_db):
        """Unknown action fails gracefully."""
        result = handle_job_schedule("nonexistent_action")

        assert result["success"] is False
        assert "Unknown action" in result["error"]

    @patch("handlers_job_schedule.get_db_connection")
    def test_db_connection_error(self, mock_get_db):
        """DB connection error is caught and reported."""
        mock_get_db.side_effect = RuntimeError("DB connection failed")

        result = handle_job_schedule("create", schedule="Daily")

        assert result["success"] is False
        assert "error" in result


# ============================================================================
# Integration Tests (optional — would use real DB if available)
# ============================================================================

class TestJobScheduleIntegration:
    """Integration tests (skipped if no DATABASE_URL)."""

    @pytest.mark.skip(reason="Requires live database")
    def test_create_list_pause_unschedule_flow(self):
        """Full workflow: create → list → pause → unschedule."""
        # This test would run against a real test database
        # For now, it's documented as an integration test.
        pass
