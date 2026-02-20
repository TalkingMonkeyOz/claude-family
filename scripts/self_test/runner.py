"""
Self-test runner - orchestrates Playwright MCP to test web applications.

Communicates with Playwright MCP server via JSON-RPC over stdio.
Navigates routes, captures snapshots, evaluates against criteria,
and produces structured reports.

Usage:
    python -m scripts.self_test.runner --project claude-manager-mui --port 5173
    python -m scripts.self_test.runner --manifest path/to/routes.json --base-url http://localhost:5173
"""

import json
import subprocess
import sys
import time
import re
import urllib.request
import urllib.error
import argparse
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from scripts.self_test.evaluation_schema import (
    TestReport, PageResult, Finding, Severity, Category,
    evaluate_snapshot, evaluate_console,
)


class PlaywrightMCPClient:
    """Communicates with Playwright MCP server via JSON-RPC over stdio."""

    def __init__(self, headless: bool = True, viewport: str = "1280x720"):
        self.headless = headless
        self.viewport = viewport
        self.process: Optional[subprocess.Popen] = None
        self._request_id = 0
        self._buffer = ""

    def start(self) -> bool:
        """Start the Playwright MCP server process."""
        args = ["npx", "@playwright/mcp@latest"]
        if self.headless:
            args.append("--headless")
        args.extend(["--viewport-size", self.viewport])

        try:
            self.process = subprocess.Popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )
        except FileNotFoundError:
            # Windows: try cmd /c npx
            self.process = subprocess.Popen(
                ["cmd", "/c"] + args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,
            )

        # Initialize MCP protocol
        init_response = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "self-test-runner", "version": "1.0"},
        })

        if not init_response or "error" in init_response:
            print(f"[FAIL] MCP initialization failed: {init_response}", file=sys.stderr)
            return False

        # Send initialized notification
        self._send_notification("notifications/initialized")
        time.sleep(0.5)

        print(f"[OK] Playwright MCP started (headless={self.headless})")
        return True

    def stop(self):
        """Stop the Playwright MCP server."""
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=5)
            except Exception:
                self.process.kill()
            self.process = None

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _send_request(self, method: str, params: dict) -> Optional[dict]:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin:
            return None

        req_id = self._next_id()
        request = json.dumps({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params,
        })

        try:
            self.process.stdin.write(request + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            return None

        return self._read_response(req_id)

    def _send_notification(self, method: str, params: Optional[dict] = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return

        notification = json.dumps({
            "jsonrpc": "2.0",
            "method": method,
            **({"params": params} if params else {}),
        })

        try:
            self.process.stdin.write(notification + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    def _read_response(self, expected_id: int, timeout: float = 30.0) -> Optional[dict]:
        """Read JSON-RPC response with matching ID."""
        if not self.process or not self.process.stdout:
            return None

        start = time.time()
        while time.time() - start < timeout:
            try:
                line = self.process.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue

                response = json.loads(line)
                if response.get("id") == expected_id:
                    return response
                # Skip notifications/other messages
            except json.JSONDecodeError:
                continue
            except Exception:
                break

        return None

    def call_tool(self, tool_name: str, arguments: dict, timeout: float = 30.0) -> Optional[dict]:
        """Call a Playwright MCP tool."""
        return self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments,
        })

    def navigate(self, url: str) -> Optional[str]:
        """Navigate to URL and return the response text."""
        result = self.call_tool("browser_navigate", {"url": url})
        if result and "result" in result:
            content = result["result"].get("content", [])
            if content:
                return content[0].get("text", "")
        return None

    def snapshot(self) -> Optional[str]:
        """Capture accessibility snapshot of current page."""
        result = self.call_tool("browser_snapshot", {})
        if result and "result" in result:
            content = result["result"].get("content", [])
            if content:
                return content[0].get("text", "")
        return None

    def console_messages(self) -> Optional[str]:
        """Get console messages."""
        result = self.call_tool("browser_console_messages", {"level": "error"})
        if result and "result" in result:
            content = result["result"].get("content", [])
            if content:
                return content[0].get("text", "")
        return None

    def screenshot(self, filename: str = "") -> Optional[str]:
        """Take screenshot of current page."""
        args = {"type": "png"}
        if filename:
            args["filename"] = filename
        result = self.call_tool("browser_take_screenshot", args)
        if result and "result" in result:
            content = result["result"].get("content", [])
            if content:
                return content[0].get("text", "")
        return None

    def click(self, ref: str, element_desc: str = "") -> Optional[str]:
        """Click an element by its ref from a snapshot."""
        args = {"ref": ref}
        if element_desc:
            args["element"] = element_desc
        result = self.call_tool("browser_click", args)
        if result and "result" in result:
            content = result["result"].get("content", [])
            if content:
                return content[0].get("text", "")
        return None

    def find_and_click(self, snapshot_text: str, target_text: str) -> Optional[str]:
        """Find an element by text in snapshot and click it.

        Searches the snapshot YAML for elements containing target_text
        and returns the ref to click. Prefers buttons, links, and tabs
        over generic elements.
        """
        if not snapshot_text:
            return None

        # Extract just the YAML part from the snapshot response
        yaml_match = re.search(r'```yaml\n(.*?)```', snapshot_text, re.DOTALL)
        search_text = yaml_match.group(1) if yaml_match else snapshot_text

        # Parse snapshot for clickable elements with matching text
        candidates = []
        for line in search_text.split("\n"):
            if target_text.lower() in line.lower() and "[ref=" in line:
                ref_match = re.search(r'\[ref=(\w+)\]', line)
                if ref_match:
                    ref = ref_match.group(1)
                    # Score: buttons/links/tabs get priority
                    score = 0
                    if "button" in line.lower():
                        score = 3
                    elif "link" in line.lower():
                        score = 3
                    elif "tab" in line.lower():
                        score = 3
                    elif "listitem" in line.lower():
                        score = 2
                    elif "paragraph" in line.lower():
                        score = 1
                    # Exact text match gets bonus
                    if f'"{target_text}"' in line or f"'{target_text}'" in line:
                        score += 5
                    candidates.append((score, ref, line.strip()))

        if not candidates:
            return None

        # Sort by score descending, pick best match
        candidates.sort(key=lambda x: x[0], reverse=True)
        best_ref = candidates[0][1]
        return self.click(best_ref, target_text)


def wait_for_server(base_url: str, timeout: int = 30) -> bool:
    """Poll until the dev server responds."""
    print(f"Waiting for server at {base_url}...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(base_url, timeout=2)
            print(" ready!")
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            print(".", end="", flush=True)
            time.sleep(1)
    print(" timeout!")
    return False


def load_route_manifest(manifest_path: str) -> list[dict]:
    """Load routes from a JSON manifest file.

    Manifest format:
    {
        "routes": [
            {"path": "/", "name": "Dashboard", "expected": ["heading", "link"]},
            {"path": "/project/1", "name": "Project View", "params": {"id": "1"}}
        ]
    }
    """
    with open(manifest_path, "r") as f:
        data = json.load(f)
    return data.get("routes", [])


def parse_nav_response(text: str) -> dict:
    """Parse the navigate response text for page info and console errors."""
    info = {"title": "", "console_errors": 0, "console_warnings": 0, "console_text": ""}

    if not text:
        return info

    # Extract page title
    title_match = re.search(r"Page Title:\s*(.+)", text)
    if title_match:
        info["title"] = title_match.group(1).strip()

    # Extract console counts
    console_match = re.search(r"Console:\s*(\d+)\s*errors?,\s*(\d+)\s*warnings?", text)
    if console_match:
        info["console_errors"] = int(console_match.group(1))
        info["console_warnings"] = int(console_match.group(2))

    # Extract snapshot section if present
    snapshot_match = re.search(r"### Snapshot\n```yaml\n(.*?)```", text, re.DOTALL)
    if snapshot_match:
        info["snapshot"] = snapshot_match.group(1)

    # Extract events/console text
    events_match = re.search(r"### Events\n(.*?)(?=###|$)", text, re.DOTALL)
    if events_match:
        info["console_text"] = events_match.group(1).strip()

    return info


def run_self_test(
    base_url: str,
    routes: list[dict],
    project_name: str = "unknown",
    headless: bool = True,
) -> TestReport:
    """Run the self-test pipeline against a set of routes.

    Args:
        base_url: Base URL of the running dev server
        routes: List of route dicts from manifest
        project_name: Project name for the report
        headless: Whether to run browser headless

    Returns:
        TestReport with all findings
    """
    report = TestReport(
        project=project_name,
        base_url=base_url,
        started_at=datetime.now().isoformat(),
        total_routes=len(routes),
    )

    # Start Playwright MCP
    client = PlaywrightMCPClient(headless=headless)
    if not client.start():
        print("[FAIL] Could not start Playwright MCP", file=sys.stderr)
        report.completed_at = datetime.now().isoformat()
        return report

    try:
        # Track if we've done initial navigation
        initial_nav_done = False

        for i, route in enumerate(routes):
            route_path = route.get("path", "/")
            route_name = route.get("name", route_path)
            nav_type = route.get("type", "url")
            url = f"{base_url.rstrip('/')}{route_path}"

            print(f"\n[{i+1}/{len(routes)}] Testing: {route_name}")
            start_time = time.time()

            page_result = PageResult(
                route=route_path,
                url=url,
                title="",
                navigated=False,
                snapshot_captured=False,
            )

            if nav_type == "click":
                # SPA navigation: click an element in the current page
                click_text = route.get("click_text", "")
                if not click_text:
                    print(f"  [SKIP] No click_text specified")
                    report.pages.append(page_result)
                    continue

                # First ensure we're on the page
                if not initial_nav_done:
                    client.navigate(base_url)
                    time.sleep(2)
                    initial_nav_done = True

                # Get current snapshot to find the element
                current_snapshot = client.snapshot()
                if not current_snapshot:
                    print(f"  [FAIL] Could not get snapshot for click navigation")
                    report.routes_failed += 1
                    report.pages.append(page_result)
                    continue

                # Find and click the target
                click_result = client.find_and_click(current_snapshot, click_text)
                if click_result is None:
                    print(f"  [FAIL] Could not find '{click_text}' to click")
                    page_result.findings.append(Finding(
                        severity=Severity.WARNING,
                        category=Category.NAVIGATION,
                        title=f"Cannot find clickable element: {click_text}",
                        description=f"Element '{click_text}' not found in snapshot for SPA navigation",
                        route=route_path,
                        suggested_fix=f"Check sidebar/nav for '{click_text}' element.",
                    ))
                    report.routes_failed += 1
                    report.pages.append(page_result)
                    continue

                page_result.navigated = True
                report.routes_navigated += 1

                # Parse click response for console info
                nav_info = parse_nav_response(click_result)
                page_result.title = nav_info.get("title", "")
                page_result.console_errors = nav_info.get("console_errors", 0)
                page_result.console_warnings = nav_info.get("console_warnings", 0)

            else:
                # URL navigation
                nav_text = client.navigate(url)
                if nav_text is None:
                    print(f"  [FAIL] Navigation failed")
                    page_result.findings.append(Finding(
                        severity=Severity.CRITICAL,
                        category=Category.NAVIGATION,
                        title=f"Cannot navigate to {route_path}",
                        description=f"Playwright MCP returned no response for {url}",
                        route=route_path,
                        suggested_fix="Check if the route exists and the server is running.",
                    ))
                    report.routes_failed += 1
                    report.pages.append(page_result)
                    continue

                page_result.navigated = True
                report.routes_navigated += 1
                initial_nav_done = True

                # Parse navigation response
                nav_info = parse_nav_response(nav_text)
                page_result.title = nav_info["title"]
                page_result.console_errors = nav_info["console_errors"]
                page_result.console_warnings = nav_info["console_warnings"]

            # Wait for SPA rendering
            time.sleep(1.5)

            # Get full snapshot
            snapshot_text = client.snapshot()
            if snapshot_text:
                page_result.snapshot_captured = True
                # Evaluate snapshot
                snapshot_findings = evaluate_snapshot(snapshot_text, route_path)
                page_result.findings.extend(snapshot_findings)
                print(f"  Snapshot: {len(snapshot_text)} chars, {len(snapshot_findings)} findings")
            else:
                print(f"  [WARN] Could not capture snapshot")

            # Evaluate console from nav response
            console_text = nav_info.get("console_text", "")
            if console_text:
                console_findings = evaluate_console(console_text, route_path)
                page_result.findings.extend(console_findings)
                if console_findings:
                    print(f"  Console: {len(console_findings)} findings")

            # Check expected elements from manifest
            expected = route.get("expected", [])
            if expected and snapshot_text:
                for element in expected:
                    if element.lower() not in snapshot_text.lower():
                        page_result.findings.append(Finding(
                            severity=Severity.WARNING,
                            category=Category.FUNCTIONALITY,
                            title=f"Expected element missing: {element}",
                            description=f"Route manifest expects '{element}' but not found in snapshot",
                            route=route_path,
                            suggested_fix=f"Verify that '{element}' renders on this page.",
                        ))

            page_result.duration_ms = int((time.time() - start_time) * 1000)
            report.pages.append(page_result)

            total_findings = len(page_result.findings)
            status = "OK" if total_findings == 0 else f"{total_findings} findings"
            print(f"  Result: {status} ({page_result.duration_ms}ms)")

    finally:
        client.stop()

    report.completed_at = datetime.now().isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description="Self-test runner for web applications")
    parser.add_argument("--project", default="unknown", help="Project name")
    parser.add_argument("--base-url", default="http://localhost:5173", help="Base URL of dev server")
    parser.add_argument("--manifest", help="Path to route manifest JSON file")
    parser.add_argument("--port", type=int, help="Dev server port (shortcut for base-url)")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument("--output", help="Output JSON report file path")
    parser.add_argument("--no-wait", action="store_true", help="Skip waiting for dev server")
    args = parser.parse_args()

    if args.port:
        args.base_url = f"http://localhost:{args.port}"

    # Load routes
    if args.manifest:
        routes = load_route_manifest(args.manifest)
    else:
        # Default: just test the root
        routes = [{"path": "/", "name": "Home"}]

    print(f"Self-Test Runner v1.0")
    print(f"Project: {args.project}")
    print(f"Base URL: {args.base_url}")
    print(f"Routes: {len(routes)}")
    print(f"Mode: {'headed' if args.headed else 'headless'}")
    print("=" * 50)

    # Wait for server
    if not args.no_wait:
        if not wait_for_server(args.base_url):
            print("[FAIL] Dev server not responding", file=sys.stderr)
            sys.exit(1)

    # Run tests
    report = run_self_test(
        base_url=args.base_url,
        routes=routes,
        project_name=args.project,
        headless=not args.headed,
    )

    # Output report
    print("\n" + "=" * 50)
    print(report.summary())

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nReport saved to: {output_path}")
    else:
        # Save to temp
        output_dir = Path.home() / ".claude" / "self-test-reports"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"{args.project}_{timestamp}.json"
        with open(output_path, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nReport saved to: {output_path}")

    # Exit code based on findings
    if report.critical_count > 0:
        sys.exit(2)
    elif report.warning_count > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
