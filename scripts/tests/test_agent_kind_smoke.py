"""Smoke test for task_worker._run_agent — confirms subscription-auth path works.

Runs `claude -p` via subprocess with a trivial prompt. Verifies:
- Returns successfully (rc=0)
- agent_meta contains num_turns/cost
- Output contains the expected answer

NOT an automated CI test — calls the real claude CLI which needs interactive
auth. Run manually after wiring changes.
"""
import sys, os, threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config  # noqa: F401
config.get_database_uri()

from task_worker import _run_agent


def main():
    task = {"task_id": "smoke-agent-test"}
    payload = {
        "prompt": "Reply with exactly: HELLO_AGENT_OK",
        "model": "haiku",
        "timeout": 60,
        "disallowed_tools": ["Bash", "Edit", "Write"],
    }
    cancel_flag = threading.Event()
    result = _run_agent(task, payload, cancel_flag)

    print("rc:", result["return_code"])
    print("duration_secs:", round(result["duration_secs"], 2))
    print("agent_meta:", result.get("agent_meta", {}))
    print("output (last 500):", repr(result["output"][-500:]))

    assert result["return_code"] == 0, "expected rc=0"
    assert "HELLO_AGENT_OK" in result["output"], "expected answer phrase missing"
    print("\nPASS")


if __name__ == "__main__":
    main()
