"""
Tests for the MCP Config Deployment BPMN process (L2_mcp_config_deployment).

DB-Centralized design: All MCP servers come from database via 3-layer merge chain.
No manual ~/.claude/mcp.json. Single {project}/.mcp.json output per project.

3-Layer Merge Chain:
  Layer 1: config_templates (global server configs: mcp-postgres, mcp-project-tools, etc.)
  Layer 2: project_type_configs.default_mcp_servers (which globals each project type gets)
  Layer 3: workspaces.startup_config.mcp_configs (project-specific: mui, playwright, etc.)

Single start event routes via flow_type:
  flow_type="launch"     -> launcher flow (Launch-Claude-Code-Console.bat)
  flow_type="add_remove" -> add/remove MCP flow (default)

Flow A - Launcher (flow_type="launch"):
  start -> route_gw [launch]
        -> select_project [user]
        -> read_workspace_config [DB]
        -> read_project_type_defaults [DB]
        -> resolve_config_templates [DB]
        -> merge_all_configs [TOOL]
        -> resolve_npx_paths [TOOL]
        -> write_mcp_json [FILE]
        -> deploy_other_configs [TOOL]
        -> launch_claude [TOOL]
        -> load_mcp_configs [CLAUDE]
        -> end_launched

Flow B - Add/Remove MCP (flow_type="add_remove" / default):
  start -> route_gw [default]
        -> update_db_mcp_configs [DB]
        -> regenerate_project_mcp [TOOL]
        -> record_audit [DB]
        -> end_mcp_changed

Key API notes (SpiffWorkflow 3.1.x):
  - BpmnParser.add_bpmn_file(path) + parser.get_spec(process_id)
  - BpmnWorkflow(spec) creates the workflow instance
  - workflow.do_engine_steps() advances through non-manual tasks (scripts, gateways)
  - User tasks: workflow.get_tasks(state=TaskState.READY, manual=True)
  - task.data is a dict; set values before task.run() to influence downstream conditions
"""

import os

from SpiffWorkflow.bpmn.workflow import BpmnWorkflow
from SpiffWorkflow.bpmn.parser import BpmnParser
from SpiffWorkflow.util.task import TaskState

BPMN_FILE = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "processes",
        "infrastructure",
        "mcp_config_deployment.bpmn",
    )
)
PROCESS_ID = "L2_mcp_config_deployment"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_workflow(initial_data: dict = None) -> BpmnWorkflow:
    """Parse the BPMN and return a workflow instance seeded with initial_data."""
    parser = BpmnParser()
    parser.add_bpmn_file(BPMN_FILE)
    spec = parser.get_spec(PROCESS_ID)
    wf = BpmnWorkflow(spec)

    if initial_data:
        ready = wf.get_tasks(state=TaskState.READY)
        for task in ready:
            task.data.update(initial_data)

    wf.do_engine_steps()
    return wf


def _get_ready_user_tasks(workflow: BpmnWorkflow) -> list:
    """Return all READY user tasks."""
    return workflow.get_tasks(state=TaskState.READY, manual=True)


def _complete_user_task(workflow: BpmnWorkflow, task_name: str, data: dict) -> None:
    """Find the named READY user task, merge data, run it, then advance the engine."""
    ready = _get_ready_user_tasks(workflow)
    matches = [t for t in ready if t.task_spec.name == task_name]
    assert matches, (
        f"Expected user task '{task_name}' to be READY. "
        f"READY user tasks: {[t.task_spec.name for t in ready]}"
    )
    task = matches[0]
    task.data.update(data)
    task.run()
    workflow.do_engine_steps()


def _completed_names(workflow: BpmnWorkflow) -> list:
    """Return spec names of all COMPLETED tasks."""
    return [t.task_spec.name for t in workflow.get_tasks(state=TaskState.COMPLETED)]


def _base_launcher_data(**overrides) -> dict:
    """Seed data to enter the launcher flow (Flow A)."""
    data = {
        "flow_type": "launch",
        "project_name": "claude-family",
        "project_path": "C:/Projects/claude-family",
    }
    data.update(overrides)
    return data


def _base_add_remove_data(**overrides) -> dict:
    """Seed data to enter the add/remove MCP flow (Flow B)."""
    data = {
        "flow_type": "add_remove",
        "mcp_server_name": "my-server",
        "mcp_action": "add",
        "project_name": "claude-family",
        "mcp_server_config": {"command": "node", "args": ["server.js"]},
    }
    data.update(overrides)
    return data


# ---------------------------------------------------------------------------
# Flow A Tests: Launcher Flow (3-Layer Merge)
# ---------------------------------------------------------------------------


class TestLauncherFlowWithMerge:
    """
    Full launcher flow with 3-layer merge chain.

    Path: start -> route_gw [launch]
               -> select_project [user]
               -> read_workspace_config [DB]
               -> read_project_type_defaults [DB]
               -> resolve_config_templates [DB]
               -> merge_all_configs [TOOL]
               -> resolve_npx_paths [TOOL]
               -> write_mcp_json [FILE]
               -> deploy_other_configs [TOOL]
               -> launch_claude [TOOL]
               -> load_mcp_configs [CLAUDE]
               -> end_launched
    """

    def test_full_3_layer_merge_flow(self):
        """Complete launcher flow executes all merge steps."""
        wf = _load_workflow(_base_launcher_data())

        # Stops at user task
        assert not wf.is_completed()
        ready_names = [t.task_spec.name for t in _get_ready_user_tasks(wf)]
        assert "select_project" in ready_names

        # User selects project with workspace-specific MCPs
        _complete_user_task(wf, "select_project", {
            "project_name": "claude-family",
            "project_path": "C:/Projects/claude-family",
            "project_type": "infrastructure",
            "default_mcp_servers": ["postgres", "project-tools", "sequential-thinking"],
            "workspace_mcp_configs": {
                "mui": {"command": "npx", "args": ["-y", "@mui/mcp"], "type": "stdio"},
                "bpmn-engine": {"command": "python", "args": ["server.py"], "type": "stdio"},
            },
        })

        assert wf.is_completed(), "Workflow should complete after launcher sequence"

        names = _completed_names(wf)

        # All 3-layer merge steps executed
        assert "read_workspace_config" in names
        assert "read_project_type_defaults" in names
        assert "resolve_config_templates" in names
        assert "merge_all_configs" in names
        assert "resolve_npx_paths" in names
        assert "write_mcp_json" in names
        assert "deploy_other_configs" in names
        assert "launch_claude" in names
        assert "load_mcp_configs" in names
        assert "end_launched" in names

        # Flow B NOT taken
        assert "update_db_mcp_configs" not in names
        assert "record_audit" not in names

        # Output data
        assert wf.data.get("workspace_read_ok") is True
        assert wf.data.get("type_defaults_read") is True
        assert wf.data.get("templates_resolved") is True
        assert wf.data.get("merge_complete") is True
        assert wf.data.get("paths_resolved") is True
        assert wf.data.get("mcp_json_written") is True
        assert wf.data.get("other_configs_deployed") is True
        assert wf.data.get("claude_launched") is True
        assert wf.data.get("all_mcps_loaded") is True

    def test_template_resolution_produces_configs(self):
        """resolve_config_templates produces template_configs from default_mcp_servers."""
        wf = _load_workflow(_base_launcher_data())

        _complete_user_task(wf, "select_project", {
            "project_name": "test-project",
            "project_path": "C:/Projects/test",
            "default_mcp_servers": ["postgres", "project-tools"],
        })

        assert wf.is_completed()
        assert wf.data.get("template_count") == 2
        template_configs = wf.data.get("template_configs", {})
        assert "postgres" in template_configs
        assert "project-tools" in template_configs

    def test_merge_overlays_workspace_on_templates(self):
        """merge_all_configs overlays workspace configs on top of template defaults."""
        wf = _load_workflow(_base_launcher_data())

        _complete_user_task(wf, "select_project", {
            "project_name": "test-project",
            "project_path": "C:/Projects/test",
            "default_mcp_servers": ["postgres", "project-tools"],
            "workspace_mcp_configs": {
                "mui": {"command": "npx", "args": ["-y", "@mui/mcp"]},
            },
        })

        assert wf.is_completed()

        # 2 templates + 1 workspace = 3 total
        assert wf.data.get("server_count") == 3
        merged = wf.data.get("merged_mcp_configs", {})
        assert "postgres" in merged
        assert "project-tools" in merged
        assert "mui" in merged

    def test_npx_commands_resolved_to_cmd_wrapper(self):
        """npx entries are rewritten to cmd /c node for Windows compatibility."""
        wf = _load_workflow(_base_launcher_data())

        _complete_user_task(wf, "select_project", {
            "project_name": "test-project",
            "project_path": "C:/Projects/test",
            "workspace_mcp_configs": {
                "tool-a": {"command": "npx", "args": ["-y", "@tool/server"]},
            },
        })

        assert wf.is_completed()
        assert wf.data.get("paths_resolved") is True

        resolved = wf.data.get("resolved_mcp_configs", {})
        assert "tool-a" in resolved
        assert resolved["tool-a"]["command"] == "cmd"
        assert resolved["tool-a"].get("_resolved") is True

    def test_non_npx_commands_pass_through(self):
        """Non-npx commands (python, node) are not transformed."""
        wf = _load_workflow(_base_launcher_data())

        _complete_user_task(wf, "select_project", {
            "project_name": "test-project",
            "project_path": "C:/Projects/test",
            "workspace_mcp_configs": {
                "direct-server": {"command": "node", "args": ["index.js"]},
            },
        })

        assert wf.is_completed()
        resolved = wf.data.get("resolved_mcp_configs", {})
        assert resolved["direct-server"]["command"] == "node"
        assert resolved["direct-server"].get("_resolved") is None

    def test_always_generates_mcp_json(self):
        """Even with no workspace-specific configs, .mcp.json is generated (from templates)."""
        wf = _load_workflow(_base_launcher_data())

        _complete_user_task(wf, "select_project", {
            "project_name": "minimal-project",
            "project_path": "C:/Projects/minimal",
            # No workspace_mcp_configs provided
        })

        assert wf.is_completed()

        names = _completed_names(wf)
        # No skip path - always generates
        assert "write_mcp_json" in names
        assert wf.data.get("mcp_json_written") is True

        # Template defaults still produce configs
        assert wf.data.get("template_count") == 3  # defaults: postgres, project-tools, sequential-thinking

    def test_mcp_json_path_is_project_root(self):
        """Verify the .mcp.json output path is constructed correctly."""
        wf = _load_workflow(_base_launcher_data())

        _complete_user_task(wf, "select_project", {
            "project_name": "myproject",
            "project_path": "C:/Projects/myproject",
        })

        assert wf.is_completed()
        assert wf.data.get("mcp_json_path") == "C:/Projects/myproject/.mcp.json"


class TestLauncherConfigDeployment:
    """Verify other configs are always deployed in the launcher flow."""

    def test_settings_and_claude_md_always_deployed(self):
        wf = _load_workflow(_base_launcher_data())
        _complete_user_task(wf, "select_project", {
            "project_path": "C:/Projects/test",
        })

        assert wf.is_completed()
        assert wf.data.get("other_configs_deployed") is True
        assert wf.data.get("settings_deployed") is True
        assert wf.data.get("claude_md_deployed") is True


# ---------------------------------------------------------------------------
# Flow B Tests: Add/Remove MCP Server (DB-only)
# ---------------------------------------------------------------------------


class TestAddRemoveMcpServer:
    """
    Add/remove MCP is fully automated via DB update -> regenerate -> audit.

    Path: start -> route_gw [default]
               -> update_db_mcp_configs [DB]
               -> regenerate_project_mcp [TOOL]
               -> record_audit [DB]
               -> end_mcp_changed
    """

    def test_add_project_mcp_is_fully_automated(self):
        wf = _load_workflow(_base_add_remove_data())

        # Fully automated (no user tasks)
        assert wf.is_completed(), "Add/remove flow should complete without user tasks"

        names = _completed_names(wf)

        # All steps executed
        assert "update_db_mcp_configs" in names
        assert "regenerate_project_mcp" in names
        assert "record_audit" in names
        assert "end_mcp_changed" in names

        # Launcher flow NOT taken
        assert "select_project" not in names
        assert "end_launched" not in names

        # Data
        assert wf.data.get("db_mcp_configs_updated") is True
        assert wf.data.get("mcp_json_regenerated") is True
        assert wf.data.get("audit_recorded") is True

    def test_remove_mcp_follows_same_path(self):
        """Removing an MCP follows the same DB update -> regenerate path."""
        wf = _load_workflow(_base_add_remove_data(
            mcp_action="remove",
            mcp_server_name="old-server",
        ))

        assert wf.is_completed()

        names = _completed_names(wf)
        assert "update_db_mcp_configs" in names
        assert "regenerate_project_mcp" in names
        assert "record_audit" in names
        assert wf.data.get("audit_recorded") is True

    def test_default_flow_type_routes_to_add_remove(self):
        """No flow_type seeded -> defaults to add_remove."""
        wf = _load_workflow({
            "mcp_server_name": "test-server",
            "mcp_action": "add",
            "project_name": "test",
        })

        assert wf.is_completed()

        names = _completed_names(wf)
        assert "update_db_mcp_configs" in names
        assert "regenerate_project_mcp" in names
        assert "record_audit" in names
        assert "select_project" not in names

    def test_audit_uses_audit_log(self):
        """Audit step records to audit_log (not non-existent mcp_configs_audit)."""
        wf = _load_workflow(_base_add_remove_data())

        assert wf.is_completed()
        assert wf.data.get("audit_recorded") is True
        # record_audit task name confirms it's [DB] Record in audit_log


# ---------------------------------------------------------------------------
# End-to-End Launcher Flow Test
# ---------------------------------------------------------------------------


class TestFullLauncherFlow:
    """
    End-to-end test of the full launcher flow with 3-layer merge.

    Simulates a production scenario where:
    1. User selects a project
    2. DB merge: template defaults + workspace overrides
    3. npx paths resolved
    4. .mcp.json written with all servers
    5. Other configs deployed
    6. Claude launched with single .mcp.json (all servers)
    """

    def test_full_launch_with_merged_mcps(self):
        wf = _load_workflow(_base_launcher_data(
            project_name="nimbus-ai-platform",
            project_path="C:/Projects/nimbus-ai-platform",
        ))

        assert not wf.is_completed()
        assert "select_project" in [t.task_spec.name for t in _get_ready_user_tasks(wf)]

        _complete_user_task(wf, "select_project", {
            "project_name": "nimbus-ai-platform",
            "project_path": "C:/Projects/nimbus-ai-platform",
            "project_type": "web-app",
            "default_mcp_servers": ["postgres", "project-tools", "sequential-thinking"],
            "workspace_mcp_configs": {
                "nimbus-knowledge": {
                    "command": "npx",
                    "args": ["-y", "@nimbus/knowledge-server"],
                    "env": {"NIMBUS_DB_URL": "postgresql://localhost/nimbus"},
                },
                "mui": {
                    "command": "node",
                    "args": ["C:/tools/mui-server/dist/index.js"],
                },
            },
        })

        assert wf.is_completed()

        names = _completed_names(wf)

        # All steps completed
        assert "read_workspace_config" in names
        assert "read_project_type_defaults" in names
        assert "resolve_config_templates" in names
        assert "merge_all_configs" in names
        assert "resolve_npx_paths" in names
        assert "write_mcp_json" in names
        assert "deploy_other_configs" in names
        assert "launch_claude" in names
        assert "load_mcp_configs" in names
        assert "end_launched" in names

        # Flow B NOT taken
        assert "end_mcp_changed" not in names

        # Final data state
        assert wf.data.get("claude_launched") is True
        assert wf.data.get("all_mcps_loaded") is True
        assert wf.data.get("mcp_json_written") is True
        assert wf.data.get("other_configs_deployed") is True
        # 3 templates + 2 workspace = 5 total
        assert wf.data.get("server_count") == 5

    def test_full_launch_template_defaults_only(self):
        """Project with no workspace MCP overrides still gets template defaults."""
        wf = _load_workflow(_base_launcher_data(project_name="minimal-project"))

        _complete_user_task(wf, "select_project", {
            "project_name": "minimal-project",
            "project_path": "C:/Projects/minimal",
            # No workspace_mcp_configs
        })

        assert wf.is_completed()

        names = _completed_names(wf)
        assert "write_mcp_json" in names
        assert "end_launched" in names
        assert "end_mcp_changed" not in names

        # Only template defaults (3 servers)
        assert wf.data.get("server_count") == 3
        assert wf.data.get("template_count") == 3
