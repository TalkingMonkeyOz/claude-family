"""
Evaluation criteria schema for self-test pipeline.

Defines the structured format for test findings, evaluation rules,
and report generation. Used by the self-test runner to evaluate
Playwright MCP accessibility snapshots and console output.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional
from datetime import datetime


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Category(str, Enum):
    NAVIGATION = "navigation"
    LAYOUT = "layout"
    ACCESSIBILITY = "accessibility"
    ERROR_STATE = "error_state"
    FUNCTIONALITY = "functionality"
    CONSOLE = "console"
    PERFORMANCE = "performance"


class FeedbackType(str, Enum):
    """Maps finding categories to feedback types for auto-filing."""
    BUG = "bug"
    DESIGN = "design"
    IMPROVEMENT = "improvement"


# Category → feedback type mapping
CATEGORY_TO_FEEDBACK: dict[Category, FeedbackType] = {
    Category.NAVIGATION: FeedbackType.BUG,
    Category.LAYOUT: FeedbackType.DESIGN,
    Category.ACCESSIBILITY: FeedbackType.IMPROVEMENT,
    Category.ERROR_STATE: FeedbackType.BUG,
    Category.FUNCTIONALITY: FeedbackType.BUG,
    Category.CONSOLE: FeedbackType.BUG,
    Category.PERFORMANCE: FeedbackType.IMPROVEMENT,
}


@dataclass
class Finding:
    """A single evaluation finding from testing a page."""
    severity: Severity
    category: Category
    title: str
    description: str
    route: str
    suggested_fix: Optional[str] = None
    element_ref: Optional[str] = None
    snapshot_excerpt: Optional[str] = None
    console_message: Optional[str] = None

    @property
    def feedback_type(self) -> FeedbackType:
        return CATEGORY_TO_FEEDBACK[self.category]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["category"] = self.category.value
        d["feedback_type"] = self.feedback_type.value
        return d


@dataclass
class PageResult:
    """Results from evaluating a single page/route."""
    route: str
    url: str
    title: str
    navigated: bool
    snapshot_captured: bool
    console_errors: int = 0
    console_warnings: int = 0
    findings: list[Finding] = field(default_factory=list)
    duration_ms: int = 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["findings"] = [f.to_dict() for f in self.findings]
        return d


@dataclass
class TestReport:
    """Complete self-test report for a project."""
    project: str
    base_url: str
    started_at: str = ""
    completed_at: str = ""
    total_routes: int = 0
    routes_navigated: int = 0
    routes_failed: int = 0
    pages: list[PageResult] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        return [f for p in self.pages for f in p.findings]

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == Severity.INFO)

    def summary(self) -> str:
        lines = [
            f"Self-Test Report: {self.project}",
            f"URL: {self.base_url}",
            f"Routes: {self.routes_navigated}/{self.total_routes} navigated, {self.routes_failed} failed",
            f"Findings: {self.critical_count} critical, {self.warning_count} warning, {self.info_count} info",
        ]
        if self.critical_count > 0:
            lines.append("\nCritical findings:")
            for f in self.findings:
                if f.severity == Severity.CRITICAL:
                    lines.append(f"  - [{f.category.value}] {f.title} ({f.route})")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "project": self.project,
            "base_url": self.base_url,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_routes": self.total_routes,
            "routes_navigated": self.routes_navigated,
            "routes_failed": self.routes_failed,
            "summary": {
                "critical": self.critical_count,
                "warning": self.warning_count,
                "info": self.info_count,
            },
            "pages": [p.to_dict() for p in self.pages],
        }


# --- Evaluation Rules ---
# These define what to check in snapshots and console output.

@dataclass
class EvaluationRule:
    """A single evaluation rule applied to page snapshots."""
    name: str
    category: Category
    severity: Severity
    description: str
    check_type: str  # "snapshot", "console", "navigation"

    def to_dict(self) -> dict:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        return d


# Default evaluation rules
DEFAULT_RULES: list[EvaluationRule] = [
    # Navigation rules
    EvaluationRule(
        name="route_reachable",
        category=Category.NAVIGATION,
        severity=Severity.CRITICAL,
        description="Route should be navigable without errors",
        check_type="navigation",
    ),
    EvaluationRule(
        name="page_has_content",
        category=Category.NAVIGATION,
        severity=Severity.WARNING,
        description="Page should have meaningful content (not empty/blank)",
        check_type="snapshot",
    ),
    EvaluationRule(
        name="page_has_heading",
        category=Category.LAYOUT,
        severity=Severity.INFO,
        description="Page should have at least one heading element",
        check_type="snapshot",
    ),

    # Accessibility rules
    EvaluationRule(
        name="links_have_text",
        category=Category.ACCESSIBILITY,
        severity=Severity.WARNING,
        description="Links should have descriptive text (not empty or generic)",
        check_type="snapshot",
    ),
    EvaluationRule(
        name="buttons_have_labels",
        category=Category.ACCESSIBILITY,
        severity=Severity.WARNING,
        description="Buttons should have accessible labels",
        check_type="snapshot",
    ),
    EvaluationRule(
        name="images_have_alt",
        category=Category.ACCESSIBILITY,
        severity=Severity.WARNING,
        description="Images should have alt text",
        check_type="snapshot",
    ),

    # Console rules
    EvaluationRule(
        name="no_js_errors",
        category=Category.CONSOLE,
        severity=Severity.CRITICAL,
        description="Page should not have JavaScript errors in console",
        check_type="console",
    ),
    EvaluationRule(
        name="no_failed_requests",
        category=Category.CONSOLE,
        severity=Severity.WARNING,
        description="Page should not have failed network requests (excluding favicon)",
        check_type="console",
    ),

    # Functionality rules
    EvaluationRule(
        name="interactive_elements_present",
        category=Category.FUNCTIONALITY,
        severity=Severity.INFO,
        description="Page should have interactive elements (buttons, links, inputs)",
        check_type="snapshot",
    ),
]


def evaluate_snapshot(snapshot_text: str, route: str) -> list[Finding]:
    """Evaluate an accessibility snapshot against default rules.

    Args:
        snapshot_text: YAML accessibility snapshot from Playwright MCP
        route: The route being tested

    Returns:
        List of findings from evaluation
    """
    findings = []

    # Check: page has content
    if not snapshot_text or len(snapshot_text.strip()) < 20:
        findings.append(Finding(
            severity=Severity.WARNING,
            category=Category.NAVIGATION,
            title="Page appears empty",
            description="Accessibility snapshot has minimal or no content",
            route=route,
            suggested_fix="Check if the page renders content. May need data or auth.",
        ))

    # Check: page has heading
    if "heading" not in snapshot_text.lower():
        findings.append(Finding(
            severity=Severity.INFO,
            category=Category.LAYOUT,
            title="No heading found",
            description="Page has no heading elements in accessibility tree",
            route=route,
            suggested_fix="Add an h1/h2 heading for page structure and a11y.",
        ))

    # Check: links have text
    lines = snapshot_text.split("\n")
    for line in lines:
        if 'link ""' in line or "link ''" in line:
            findings.append(Finding(
                severity=Severity.WARNING,
                category=Category.ACCESSIBILITY,
                title="Link with empty text",
                description="Found a link element with no accessible text",
                route=route,
                snapshot_excerpt=line.strip(),
                suggested_fix="Add aria-label or visible text to the link.",
            ))

    # Check: buttons have labels
    for line in lines:
        if 'button ""' in line or "button ''" in line:
            findings.append(Finding(
                severity=Severity.WARNING,
                category=Category.ACCESSIBILITY,
                title="Button with empty label",
                description="Found a button element with no accessible label",
                route=route,
                snapshot_excerpt=line.strip(),
                suggested_fix="Add aria-label or visible text to the button.",
            ))

    # Check: images have alt text
    for line in lines:
        if 'img ""' in line or "img ''" in line:
            findings.append(Finding(
                severity=Severity.WARNING,
                category=Category.ACCESSIBILITY,
                title="Image without alt text",
                description="Found an image element with no alt text",
                route=route,
                snapshot_excerpt=line.strip(),
                suggested_fix="Add descriptive alt text to the image.",
            ))

    return findings


def evaluate_console(console_text: str, route: str) -> list[Finding]:
    """Evaluate console output for errors and warnings.

    Args:
        console_text: Console output text from Playwright MCP
        route: The route being tested

    Returns:
        List of findings from console evaluation
    """
    findings = []

    if not console_text:
        return findings

    lines = console_text.split("\n")
    for line in lines:
        line_lower = line.lower()

        # Skip favicon errors (expected/harmless)
        if "favicon" in line_lower:
            continue

        if "[error]" in line_lower or "error" in line_lower[:20]:
            findings.append(Finding(
                severity=Severity.CRITICAL,
                category=Category.CONSOLE,
                title="JavaScript error in console",
                description=f"Console error detected on page",
                route=route,
                console_message=line.strip()[:200],
                suggested_fix="Investigate and fix the JavaScript error.",
            ))
        elif "failed to load" in line_lower or "404" in line_lower:
            findings.append(Finding(
                severity=Severity.WARNING,
                category=Category.CONSOLE,
                title="Failed network request",
                description="A network request failed (404 or load error)",
                route=route,
                console_message=line.strip()[:200],
                suggested_fix="Check if the resource URL is correct.",
            ))

    return findings
