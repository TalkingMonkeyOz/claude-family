"""
Tests for the Messaging BPMN process.

Inter-Claude Messaging Lifecycle (messaging):
  Models 6 messaging intents: send, broadcast, check_inbox, acknowledge, reply, discover.
  Channel delivery (F159): After INSERT, pg_notify fires → channel push if online, else poll fallback.

  Key behaviors:
    1. Send: Validate → INSERT → pg_notify → channel delivery (online/offline) → end_sent
    2. Broadcast: Prepare → INSERT → pg_notify → channel delivery → end_sent
    3. Check Inbox: Build query → SELECT → format → end_inbox / end_empty_inbox
    4. Acknowledge: Determine action → UPDATE/INSERT → end_acknowledged
    5. Reply: Fetch original → route to from_project + threading → INSERT → channel delivery → end_sent
    6. Discover: Query valid recipients → format list → end_recipients

  Test paths:
    1. Send valid message → pg_notify → offline → end_sent
    2. Send invalid (missing params) → end_send_invalid
    3. Broadcast → pg_notify → offline → end_sent
    4. Check inbox with messages → end_inbox
    5. Check inbox empty → end_empty_inbox
    6-9. Acknowledge: read/acknowledged/actioned/deferred → end_acknowledged
   10. Reply: original found → pg_notify → offline → end_sent
   11. Reply: original not found → end_reply_not_found
   12. Default intent (check_inbox) → end_empty_inbox
   13. Discover recipients → end_recipients
   14-15. Send with from_project / invalid recipient
   16-17. Reply threading and routing
   18. Send with recipient online → pg_notify → channel_push → end_sent
   19. Send with recipient offline → pg_notify → end_sent (no channel_push)
   20. Broadcast with recipient online → pg_notify → channel_push → end_sent

Implementation: mcp-servers/project-tools/server_v2.py
Channel MCP: mcp-servers/channel-messaging/server.js
"""

import os
import pytest

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "processes", "lifecycle", "messaging.bpmn")
)
PROCESS_ID = "messaging"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a fresh workflow instance."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)
    if initial_data:
        start_tasks = [t for t in wf.get_tasks() if t.task_spec.name == "start"]
        assert start_tasks, "Could not find BPMN start event"
        start_tasks[0].data.update(initial_data)
    wf.do_engine_steps()
    return wf


def complete_user_task(wf: BpmnWorkflow, task_name: str, data: dict = None):
    """Find and complete a specific user task, then run engine steps."""
    ready = [t for t in wf.get_tasks(state=TaskState.READY) if t.task_spec.name == task_name]
    assert ready, f"No READY user task named '{task_name}'. Ready tasks: {[t.task_spec.name for t in wf.get_tasks(state=TaskState.READY)]}"
    task = ready[0]
    if data:
        task.data.update(data)
    task.run()
    wf.do_engine_steps()
    return wf


def completed_spec_names(workflow: BpmnWorkflow) -> set:
    """Return spec names of all COMPLETED tasks."""
    return {t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)}


# ---------------------------------------------------------------------------
# Test 1: Send Valid Message
# ---------------------------------------------------------------------------

class TestSendMessage:
    """
    intent="send", valid params → validate → insert → end_sent.

    Expected path:
      start → determine_intent → intent_gw (send) → validate_send →
      send_valid_gw (True) → insert_message → end_sent
    """

    def test_send_valid_message(self):
        wf = load_workflow()

        # Complete user task: determine_intent
        wf = complete_user_task(wf, "determine_intent", {
            "intent": "send",
            "message_type": "notification",
            "body": "Hello from Claude A",
            "to_project": "claude-family",
            "from_project": "nimbus-import",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "determine_intent" in names
        assert "validate_send" in names
        assert "insert_message" in names
        assert "end_sent" in names

        # Should not hit other branches
        assert "prepare_broadcast" not in names
        assert "build_inbox_query" not in names
        assert "determine_ack_action" not in names

        assert wf.data.get("message_sent") is True


# ---------------------------------------------------------------------------
# Test 2: Send Invalid Message (missing required params)
# ---------------------------------------------------------------------------

class TestSendInvalidMessage:
    """
    intent="send", missing body → validate fails → end_send_invalid.

    Expected path:
      start → determine_intent → intent_gw (send) → validate_send →
      send_valid_gw (False) → end_send_invalid
    """

    def test_send_missing_body(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "send",
            "message_type": "notification",
            "body": "",  # empty = falsy
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "validate_send" in names
        assert "end_send_invalid" in names
        assert "insert_message" not in names


# ---------------------------------------------------------------------------
# Test 3: Broadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    """
    intent="broadcast" → prepare_broadcast → insert_message → end_sent.

    Expected path:
      start → determine_intent → intent_gw (broadcast) → prepare_broadcast →
      insert_message → end_sent
    """

    def test_broadcast_message(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "broadcast",
            "body": "System maintenance at 2am",
            "subject": "Maintenance Notice",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "prepare_broadcast" in names
        assert "insert_message" in names
        assert "end_sent" in names

        assert wf.data.get("broadcast_prepared") is True
        assert wf.data.get("message_type") == "broadcast"
        assert wf.data.get("to_project") is None
        assert wf.data.get("to_session_id") is None


# ---------------------------------------------------------------------------
# Test 4: Check Inbox With Messages
# ---------------------------------------------------------------------------

class TestCheckInboxWithMessages:
    """
    intent="check_inbox" (default), has_messages=True → format → end_inbox.

    Expected path:
      start → determine_intent → intent_gw (default/check_inbox) →
      build_inbox_query → execute_inbox_query → has_messages_gw (True) →
      format_messages → end_inbox
    """

    def test_inbox_with_messages(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "check_inbox",
            "project_name": "claude-family",
            "messages": [{"message_id": "123", "body": "test"}],
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "build_inbox_query" in names
        assert "execute_inbox_query" in names
        assert "format_messages" in names
        assert "end_inbox" in names

        assert wf.data.get("inbox_checked") is True


# ---------------------------------------------------------------------------
# Test 5: Check Inbox Empty
# ---------------------------------------------------------------------------

class TestCheckInboxEmpty:
    """
    intent="check_inbox", no messages → end_empty_inbox.

    Expected path:
      start → determine_intent → intent_gw (check_inbox) →
      build_inbox_query → execute_inbox_query → has_messages_gw (False) →
      end_empty_inbox
    """

    def test_inbox_empty(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "check_inbox",
            "messages": [],
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "build_inbox_query" in names
        assert "execute_inbox_query" in names
        assert "end_empty_inbox" in names

        assert "format_messages" not in names
        assert wf.data.get("has_messages") is False


# ---------------------------------------------------------------------------
# Test 6: Acknowledge - Mark as Read
# ---------------------------------------------------------------------------

class TestAcknowledgeRead:
    """
    intent="acknowledge", ack_action="read" → mark_read → end_acknowledged.

    Expected path:
      start → determine_intent → intent_gw (acknowledge) →
      determine_ack_action → ack_action_gw (default/read) →
      mark_read → ack_end_merge → end_acknowledged
    """

    def test_mark_as_read(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "acknowledge",
            "message_id": "abc-123",
        })

        # Complete ack action user task
        wf = complete_user_task(wf, "determine_ack_action", {
            "ack_action": "read",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "determine_ack_action" in names
        assert "mark_read" in names
        assert "ack_end_merge" in names
        assert "end_acknowledged" in names

        assert wf.data.get("new_status") == "read"


# ---------------------------------------------------------------------------
# Test 7: Acknowledge - Mark as Acknowledged
# ---------------------------------------------------------------------------

class TestAcknowledgeAcknowledged:
    """
    intent="acknowledge", ack_action="acknowledged" → mark_acknowledged → end_acknowledged.
    """

    def test_mark_as_acknowledged(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {"intent": "acknowledge"})
        wf = complete_user_task(wf, "determine_ack_action", {"ack_action": "acknowledged"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "mark_acknowledged" in names
        assert "end_acknowledged" in names
        assert wf.data.get("new_status") == "acknowledged"


# ---------------------------------------------------------------------------
# Test 8: Acknowledge - Action (Create Todo)
# ---------------------------------------------------------------------------

class TestAcknowledgeActioned:
    """
    intent="acknowledge", ack_action="actioned" → fetch → create_todo → end_acknowledged.

    Expected path:
      start → determine_intent → intent_gw (acknowledge) →
      determine_ack_action → ack_action_gw (actioned) →
      fetch_message_for_action → create_todo_from_message →
      ack_end_merge → end_acknowledged
    """

    def test_action_creates_todo(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {"intent": "acknowledge"})
        wf = complete_user_task(wf, "determine_ack_action", {"ack_action": "actioned"})

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fetch_message_for_action" in names
        assert "create_todo_from_message" in names
        assert "end_acknowledged" in names

        assert wf.data.get("todo_created") is True
        assert wf.data.get("new_status") == "actioned"


# ---------------------------------------------------------------------------
# Test 9: Acknowledge - Defer
# ---------------------------------------------------------------------------

class TestAcknowledgeDeferred:
    """
    intent="acknowledge", ack_action="deferred" → defer_with_reason → end_acknowledged.
    """

    def test_defer_with_reason(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {"intent": "acknowledge"})
        wf = complete_user_task(wf, "determine_ack_action", {
            "ack_action": "deferred",
            "defer_reason": "Will handle next session",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "defer_with_reason" in names
        assert "end_acknowledged" in names
        assert wf.data.get("new_status") == "deferred"


# ---------------------------------------------------------------------------
# Test 10: Reply - Original Found
# ---------------------------------------------------------------------------

class TestReplyFound:
    """
    intent="reply", original found → prepare_reply → insert_message → end_sent.

    Expected path:
      start → determine_intent → intent_gw (reply) →
      fetch_original_message → original_found_gw (True) →
      prepare_reply → insert_message → end_sent
    """

    def test_reply_to_existing_message(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "reply",
            "original_message_id": "msg-456",
            "body": "Thanks for the info!",
            "original_found": True,
            "from_project": "nimbus-import",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fetch_original_message" in names
        assert "prepare_reply" in names
        assert "insert_message" in names
        assert "end_sent" in names

        assert wf.data.get("reply_prepared") is True
        assert wf.data.get("message_type") == "notification"
        assert wf.data.get("parent_message_id") == "msg-456"
        assert wf.data.get("thread_id") is not None


# ---------------------------------------------------------------------------
# Test 11: Reply - Original Not Found
# ---------------------------------------------------------------------------

class TestReplyNotFound:
    """
    intent="reply", original not found → end_reply_not_found.
    """

    def test_reply_original_missing(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "reply",
            "original_found": False,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fetch_original_message" in names
        assert "end_reply_not_found" in names

        assert "prepare_reply" not in names
        assert "insert_message" not in names


# ---------------------------------------------------------------------------
# Test 12: Default Intent (check_inbox when no intent set)
# ---------------------------------------------------------------------------

class TestDefaultIntent:
    """
    No explicit intent → default branch = check_inbox.

    The intent_gw has default="flow_check_inbox", so if none of the
    conditions match, it falls through to check_inbox.
    """

    def test_default_goes_to_check_inbox(self):
        wf = load_workflow()

        # Set intent to something not matching any condition
        wf = complete_user_task(wf, "determine_intent", {
            "intent": "unknown",
            "messages": [],
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        # Should take the default (check_inbox) path
        assert "build_inbox_query" in names


# ---------------------------------------------------------------------------
# Test 13: Discover Recipients
# ---------------------------------------------------------------------------

class TestDiscoverRecipients:
    """
    intent="discover" → query_valid_recipients → format_recipients → end_recipients.

    Expected path:
      start → determine_intent → intent_gw (discover) →
      query_valid_recipients → format_recipients → end_recipients
    """

    def test_discover_recipients(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "discover",
            "recipients": [
                {"project_name": "claude-family", "display_name": "Claude Family"},
                {"project_name": "nimbus-import", "display_name": "Nimbus Import"},
            ],
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "query_valid_recipients" in names
        assert "format_recipients" in names
        assert "end_recipients" in names
        assert wf.data.get("recipients_listed") is True

        # Should not hit other branches
        assert "validate_send" not in names
        assert "build_inbox_query" not in names
        assert "determine_ack_action" not in names


# ---------------------------------------------------------------------------
# Test 14: Send with from_project Resolved
# ---------------------------------------------------------------------------

class TestSendWithFromProject:
    """
    intent="send", from_project set → validate resolves from_project → insert → end_sent.

    Verifies that from_project_resolved is True when from_project is provided.
    """

    def test_send_with_from_project(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "send",
            "message_type": "notification",
            "body": "Status update from nimbus",
            "to_project": "claude-family",
            "from_project": "nimbus-import",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "validate_send" in names
        assert "insert_message" in names
        assert "end_sent" in names
        assert wf.data.get("from_project_resolved") is True
        assert wf.data.get("from_project") == "nimbus-import"


# ---------------------------------------------------------------------------
# Test 15: Send with Invalid Recipient
# ---------------------------------------------------------------------------

class TestSendInvalidRecipient:
    """
    intent="send", recipient_valid=False → validate → send_valid_gw (False) → end_send_invalid.

    When to_project doesn't match any workspace, the send is rejected.
    """

    def test_send_invalid_recipient(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "send",
            "message_type": "notification",
            "body": "Hello",
            "to_project": "nonexistent-project",
            "recipient_valid": False,  # Invalid recipient triggers default (invalid) path
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "validate_send" in names
        assert "end_send_invalid" in names
        assert "insert_message" not in names


# ---------------------------------------------------------------------------
# Test 16: Reply Sets Threading (parent_message_id, thread_id)
# ---------------------------------------------------------------------------

class TestReplyThreading:
    """
    intent="reply", original found → prepare_reply sets parent_message_id and thread_id.

    Verifies the threading fields are populated on reply.
    """

    def test_reply_sets_threading(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "reply",
            "original_message_id": "msg-789",
            "body": "Got it, will do!",
            "original_found": True,
            "from_project": "claude-family",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "prepare_reply" in names
        assert "insert_message" in names
        assert "end_sent" in names

        # Threading fields must be set
        assert wf.data.get("parent_message_id") == "msg-789"
        assert wf.data.get("thread_id") == "msg-789"  # New thread started from original


# ---------------------------------------------------------------------------
# Test 17: Reply Routes to from_project (Not from_session_id)
# ---------------------------------------------------------------------------

class TestReplyRoutesToFromProject:
    """
    intent="reply" → reply routes to original.from_project, not from_session_id.

    This is the key fix: sessions are ephemeral, so replies must target projects.
    """

    def test_reply_routes_to_from_project(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "reply",
            "original_message_id": "msg-abc",
            "body": "Replying to your message",
            "original_found": True,
            # Simulate original message had from_project="nimbus-import"
            "from_project": "nimbus-import",
            "original_from_project": "nimbus-import",
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "fetch_original_message" in names
        assert "prepare_reply" in names
        assert "insert_message" in names
        assert "end_sent" in names

        # Reply should be prepared with project routing
        assert wf.data.get("reply_prepared") is True
        assert wf.data.get("message_type") == "notification"
        assert wf.data.get("parent_message_id") == "msg-abc"


# ---------------------------------------------------------------------------
# Test 18: Channel Delivery - Recipient Online (F159)
# ---------------------------------------------------------------------------

class TestChannelDeliveryOnline:
    """
    intent="send", recipient_online=True → insert → pg_notify → channel_push → end_sent.

    When recipient has an active channel MCP server, the message is pushed
    via MCP channel notification in real-time.
    """

    def test_send_with_online_recipient(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "send",
            "message_type": "notification",
            "body": "Real-time message",
            "to_project": "nimbus-import",
            "from_project": "claude-family",
            "recipient_online": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "insert_message" in names
        assert "pg_notify_trigger" in names
        assert "channel_push" in names
        assert "end_sent" in names

        assert wf.data.get("pg_notify_fired") is True
        assert wf.data.get("channel_delivered") is True


# ---------------------------------------------------------------------------
# Test 19: Channel Delivery - Recipient Offline (F159)
# ---------------------------------------------------------------------------

class TestChannelDeliveryOffline:
    """
    intent="send", recipient_online not set (default) → insert → pg_notify → offline → end_sent.

    When recipient has no channel MCP server, the message is stored in DB
    and will be picked up by poll-based inbox check.
    """

    def test_send_with_offline_recipient(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "send",
            "message_type": "notification",
            "body": "Queued message",
            "to_project": "nimbus-import",
            "from_project": "claude-family",
            # recipient_online not set → defaults to offline path
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "insert_message" in names
        assert "pg_notify_trigger" in names
        assert "end_sent" in names

        # Channel push should NOT have been reached
        assert "channel_push" not in names

        assert wf.data.get("pg_notify_fired") is True
        assert wf.data.get("channel_delivered") is None or wf.data.get("channel_delivered") is not True


# ---------------------------------------------------------------------------
# Test 20: Channel Delivery - Broadcast Online (F159)
# ---------------------------------------------------------------------------

class TestChannelDeliveryBroadcastOnline:
    """
    intent="broadcast", recipient_online=True → prepare → insert → pg_notify → channel_push → end_sent.

    Broadcast messages also go through channel delivery when recipients are online.
    """

    def test_broadcast_with_online_recipients(self):
        wf = load_workflow()

        wf = complete_user_task(wf, "determine_intent", {
            "intent": "broadcast",
            "body": "System announcement",
            "subject": "Update",
            "recipient_online": True,
        })

        assert wf.is_completed()
        names = completed_spec_names(wf)

        assert "prepare_broadcast" in names
        assert "insert_message" in names
        assert "pg_notify_trigger" in names
        assert "channel_push" in names
        assert "end_sent" in names

        assert wf.data.get("broadcast_prepared") is True
        assert wf.data.get("pg_notify_fired") is True
        assert wf.data.get("channel_delivered") is True
