"""
Feedback integration for self-test pipeline.

Converts test findings into feedback items in the database,
with deduplication to avoid filing the same issue twice.

Can be used standalone or called from the self-test skill.
"""

import json
import sys
import os
import argparse
from pathlib import Path
from typing import Optional

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_VERSION = 3
except ImportError:
    import psycopg2 as psycopg
    from psycopg2.extras import RealDictCursor
    PSYCOPG_VERSION = 2

from scripts.self_test.evaluation_schema import (
    TestReport, Finding, Severity, CATEGORY_TO_FEEDBACK,
)

# Self-test tag for deduplication
SELF_TEST_TAG = "[self-test]"

DEFAULT_DB_URI = os.environ.get(
    "DATABASE_URI",
    "postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation"
)


def get_connection():
    """Get database connection."""
    if PSYCOPG_VERSION == 3:
        return psycopg.connect(DEFAULT_DB_URI, row_factory=dict_row)
    else:
        return psycopg.connect(DEFAULT_DB_URI, cursor_factory=RealDictCursor)


def check_duplicate(conn, project_id: str, title: str) -> bool:
    """Check if a feedback item with similar title already exists for this project."""
    cur = conn.cursor()
    cur.execute("""
        SELECT COUNT(*) as cnt FROM claude.feedback
        WHERE project_id = %s
          AND title LIKE %s
          AND status NOT IN ('resolved', 'wont_fix', 'duplicate')
    """, (project_id, f"%{title}%"))
    row = cur.fetchone()
    count = dict(row).get("cnt", 0) if row else 0
    return count > 0


def get_project_id(conn, project_name: str) -> Optional[str]:
    """Look up project UUID from name."""
    cur = conn.cursor()
    cur.execute("""
        SELECT project_id FROM claude.workspaces
        WHERE project_name = %s
    """, (project_name,))
    row = cur.fetchone()
    if row:
        return str(dict(row).get("project_id", ""))
    return None


def create_feedback_item(
    conn,
    project_id: str,
    finding: Finding,
    project_name: str,
) -> Optional[str]:
    """Create a feedback item from a finding.

    Returns the short_code if created, None if skipped (duplicate).
    """
    title = f"{SELF_TEST_TAG} {finding.title} ({finding.route})"

    # Dedup check
    if check_duplicate(conn, project_id, finding.title):
        return None

    # Build description
    parts = [
        f"**Route**: `{finding.route}`",
        f"**Category**: {finding.category.value}",
        f"**Severity**: {finding.severity.value}",
        "",
        finding.description,
    ]
    if finding.console_message:
        parts.extend(["", f"**Console**: `{finding.console_message}`"])
    if finding.snapshot_excerpt:
        parts.extend(["", f"**Snapshot**: `{finding.snapshot_excerpt}`"])
    if finding.suggested_fix:
        parts.extend(["", f"**Suggested Fix**: {finding.suggested_fix}"])

    parts.extend(["", f"*Auto-filed by self-test pipeline*"])
    description = "\n".join(parts)

    # Map severity to priority
    priority = "high" if finding.severity == Severity.CRITICAL else "medium"

    # Map category to feedback type
    feedback_type = finding.feedback_type.value

    cur = conn.cursor()
    cur.execute("""
        INSERT INTO claude.feedback (
            feedback_id, project_id, feedback_type, title, description,
            priority, status, notes, created_at, updated_at
        ) VALUES (
            gen_random_uuid(), %s, %s, %s, %s,
            %s, 'new', %s, NOW(), NOW()
        )
        RETURNING short_code
    """, (
        project_id,
        feedback_type,
        title,
        description,
        priority,
        f"source=self-test; route={finding.route}",
    ))

    row = cur.fetchone()
    conn.commit()
    if row:
        code = dict(row).get("short_code", "")
        return f"FB{code}"
    return None


def file_findings(
    report: TestReport,
    min_severity: Severity = Severity.WARNING,
) -> dict:
    """File findings from a test report as feedback items.

    Args:
        report: TestReport with findings
        min_severity: Minimum severity to file (default: WARNING)

    Returns:
        Summary dict with counts
    """
    severity_order = {Severity.CRITICAL: 0, Severity.WARNING: 1, Severity.INFO: 2}
    min_level = severity_order[min_severity]

    conn = get_connection()
    project_id = get_project_id(conn, report.project)

    if not project_id:
        conn.close()
        return {
            "error": f"Project '{report.project}' not found in database",
            "created": 0,
            "skipped": 0,
            "total_findings": len(report.findings),
        }

    created = []
    skipped = 0
    errors = 0

    for finding in report.findings:
        level = severity_order.get(finding.severity, 2)
        if level > min_level:
            continue

        try:
            code = create_feedback_item(conn, project_id, finding, report.project)
            if code:
                created.append(code)
                print(f"  [CREATED] {code}: {finding.title} ({finding.route})")
            else:
                skipped += 1
                print(f"  [SKIP] Duplicate: {finding.title} ({finding.route})")
        except Exception as e:
            errors += 1
            print(f"  [ERROR] {finding.title}: {e}", file=sys.stderr)

    conn.close()

    return {
        "created": len(created),
        "created_codes": created,
        "skipped": skipped,
        "errors": errors,
        "total_findings": len(report.findings),
        "filed_severity": min_severity.value,
    }


def file_from_report_file(report_path: str, min_severity: str = "warning") -> dict:
    """Load a JSON report file and file its findings."""
    from scripts.self_test.evaluation_schema import Category, PageResult

    with open(report_path, "r") as f:
        data = json.load(f)

    # Reconstruct report with proper PageResult objects
    report = TestReport(
        project=data["project"],
        base_url=data["base_url"],
        started_at=data.get("started_at", ""),
        completed_at=data.get("completed_at", ""),
        total_routes=data.get("total_routes", 0),
        routes_navigated=data.get("routes_navigated", 0),
        routes_failed=data.get("routes_failed", 0),
    )

    for page_data in data.get("pages", []):
        page = PageResult(
            route=page_data["route"],
            url=page_data["url"],
            title=page_data.get("title", ""),
            navigated=page_data.get("navigated", False),
            snapshot_captured=page_data.get("snapshot_captured", False),
        )
        for f_data in page_data.get("findings", []):
            page.findings.append(Finding(
                severity=Severity(f_data["severity"]),
                category=Category(f_data["category"]),
                title=f_data["title"],
                description=f_data["description"],
                route=f_data["route"],
                suggested_fix=f_data.get("suggested_fix"),
                element_ref=f_data.get("element_ref"),
                snapshot_excerpt=f_data.get("snapshot_excerpt"),
                console_message=f_data.get("console_message"),
            ))
        report.pages.append(page)

    severity_map = {"critical": Severity.CRITICAL, "warning": Severity.WARNING, "info": Severity.INFO}
    return file_findings(report, severity_map.get(min_severity, Severity.WARNING))


def main():
    parser = argparse.ArgumentParser(description="File self-test findings as feedback items")
    parser.add_argument("report", help="Path to JSON report file")
    parser.add_argument("--severity", default="warning", choices=["critical", "warning", "info"],
                        help="Minimum severity to file (default: warning)")
    args = parser.parse_args()

    print(f"Filing findings from: {args.report}")
    print(f"Minimum severity: {args.severity}")
    print("=" * 40)

    result = file_from_report_file(args.report, args.severity)

    print("=" * 40)
    print(f"Created: {result['created']} feedback items")
    if result.get("created_codes"):
        print(f"  Codes: {', '.join(result['created_codes'])}")
    print(f"Skipped: {result['skipped']} (duplicates)")
    if result.get("errors", 0):
        print(f"Errors: {result['errors']}")


if __name__ == "__main__":
    main()
