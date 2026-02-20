"""
Interactive app explorer - captures detailed snapshots of every view.

Unlike the automated runner, this captures full snapshots for human/AI
analysis of UX, layout, and design quality.
"""

import json
import subprocess
import sys
import time
import re
from pathlib import Path


class MCPExplorer:
    """Drives Playwright MCP to explore an app and capture snapshots."""

    def __init__(self, base_url: str, headless: bool = True):
        self.base_url = base_url
        self.headless = headless
        self.process = None
        self._id = 0
        self.snapshots = []

    def start(self):
        args = ["cmd", "/c", "npx", "@playwright/mcp@latest"]
        if self.headless:
            args.append("--headless")
        args.extend(["--viewport-size", "1280x720"])

        self.process = subprocess.Popen(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=0,
        )

        self._send('initialize', {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "explorer", "version": "1.0"},
        })
        self._notify("notifications/initialized")
        time.sleep(0.5)

    def stop(self):
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=5)
            except:
                self.process.kill()

    def _next_id(self):
        self._id += 1
        return self._id

    def _send(self, method, params):
        rid = self._next_id()
        msg = json.dumps({"jsonrpc": "2.0", "id": rid, "method": method, "params": params})
        self.process.stdin.write(msg + "\n")
        self.process.stdin.flush()
        return self._read(rid)

    def _notify(self, method):
        msg = json.dumps({"jsonrpc": "2.0", "method": method})
        self.process.stdin.write(msg + "\n")
        self.process.stdin.flush()

    def _read(self, expected_id, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            line = self.process.stdout.readline().strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("id") == expected_id:
                    return data
            except:
                continue
        return None

    def tool(self, name, args):
        result = self._send("tools/call", {"name": name, "arguments": args})
        if result and "result" in result:
            content = result["result"].get("content", [])
            return content[0].get("text", "") if content else ""
        return ""

    def navigate(self, url):
        return self.tool("browser_navigate", {"url": url})

    def snapshot(self):
        return self.tool("browser_snapshot", {})

    def click_ref(self, ref, desc=""):
        args = {"ref": ref}
        if desc:
            args["element"] = desc
        return self.tool("browser_click", args)

    def console(self):
        return self.tool("browser_console_messages", {"level": "error"})

    def find_ref(self, snapshot_text, target_text):
        """Find best matching ref in snapshot."""
        yaml_match = re.search(r'```yaml\n(.*?)```', snapshot_text, re.DOTALL)
        text = yaml_match.group(1) if yaml_match else snapshot_text

        best = None
        best_score = -1
        for line in text.split("\n"):
            if target_text.lower() in line.lower() and "[ref=" in line:
                ref_match = re.search(r'\[ref=(\w+)\]', line)
                if ref_match:
                    score = 0
                    if "button" in line.lower() or "link" in line.lower() or "tab" in line.lower():
                        score += 3
                    if f'"{target_text}"' in line:
                        score += 5
                    if score > best_score:
                        best_score = score
                        best = ref_match.group(1)
        return best

    def explore_view(self, name, click_target=None):
        """Navigate to a view and capture its snapshot."""
        print(f"\n--- {name} ---")

        if click_target:
            snap = self.snapshot()
            ref = self.find_ref(snap, click_target)
            if ref:
                self.click_ref(ref, click_target)
                time.sleep(1.5)
            else:
                print(f"  Could not find '{click_target}'")
                return None

        snap = self.snapshot()
        cons = self.console()

        # Extract just the YAML
        yaml_match = re.search(r'```yaml\n(.*?)```', snap, re.DOTALL)
        yaml_text = yaml_match.group(1) if yaml_match else snap

        entry = {
            "name": name,
            "snapshot": yaml_text,
            "console": cons,
            "snapshot_length": len(yaml_text),
        }
        self.snapshots.append(entry)

        print(f"  Captured: {len(yaml_text)} chars")
        return yaml_text


def main():
    base_url = "http://localhost:1420"
    explorer = MCPExplorer(base_url, headless=True)
    explorer.start()

    try:
        # 1. Initial load
        explorer.navigate(base_url)
        time.sleep(3)
        explorer.explore_view("Initial Load (Dashboard)")

        # 2. Expand and explore Projects
        explorer.explore_view("Sidebar: Projects expanded", "Projects")
        time.sleep(1)

        # Try to click a project (claude-family)
        snap = explorer.snapshot()
        ref = explorer.find_ref(snap, "claude-family")
        if ref:
            explorer.click_ref(ref, "claude-family")
            time.sleep(2)
            explorer.explore_view("Project: claude-family selected")

            # Navigate through project tabs
            for tab in ["Sessions", "Messages", "Management", "Todos", "Feedback"]:
                snap = explorer.snapshot()
                ref = explorer.find_ref(snap, tab)
                if ref:
                    explorer.click_ref(ref, tab)
                    time.sleep(1.5)
                    explorer.explore_view(f"Project Tab: {tab}")
                else:
                    print(f"  Could not find tab '{tab}'")

        # 3. Configuration section
        explorer.explore_view("Sidebar: Configuration", "Configuration")
        time.sleep(1)

        # Try config sub-items
        for item in ["Templates", "Projects", "Deployment"]:
            snap = explorer.snapshot()
            ref = explorer.find_ref(snap, item)
            if ref:
                explorer.click_ref(ref, item)
                time.sleep(1.5)
                explorer.explore_view(f"Config: {item}")

        # 4. Monitoring section
        explorer.explore_view("Sidebar: Monitoring", "Monitoring")
        time.sleep(1)

        for item in ["Sessions", "Messages", "Scheduler", "Agents", "Lifecycle", "Logs"]:
            snap = explorer.snapshot()
            ref = explorer.find_ref(snap, item)
            if ref:
                explorer.click_ref(ref, item)
                time.sleep(1.5)
                explorer.explore_view(f"Monitoring: {item}")

    finally:
        explorer.stop()

    # Save all snapshots
    output = Path.home() / ".claude" / "self-test-reports" / "exploration.json"
    with open(output, "w") as f:
        json.dump(explorer.snapshots, f, indent=2)

    print(f"\n{'='*60}")
    print(f"Explored {len(explorer.snapshots)} views")
    print(f"Saved to: {output}")

    # Also print all snapshots for analysis
    for entry in explorer.snapshots:
        print(f"\n{'='*60}")
        print(f"VIEW: {entry['name']}")
        print(f"{'='*60}")
        print(entry['snapshot'][:2000])


if __name__ == "__main__":
    main()
