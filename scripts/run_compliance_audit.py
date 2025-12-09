#!/usr/bin/env python3
"""
Compliance Audit Runner

Runs a compliance audit for a project and stores results in the database.
Called by /check-compliance command or manually.

Usage:
    python run_compliance_audit.py [project_name] [audit_type]

    audit_type: governance, documentation, data_quality, standards, all

Author: claude-code-unified
Date: 2025-12-08
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import uuid

# Add config path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')

try:
    from config import POSTGRES_CONFIG
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_DB = True
except ImportError:
    HAS_DB = False

CONN_STR = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'
PROJECTS_BASE = Path('C:/Projects')

# Required governance files
GOVERNANCE_FILES = [
    'CLAUDE.md',
    'ARCHITECTURE.md',
    'PROBLEM_STATEMENT.md'
]

# Required command files (universal)
REQUIRED_COMMANDS = [
    'session-start.md',
    'session-end.md',
    'session-resume.md',
    'broadcast.md',
    'inbox-check.md',
    'team-status.md'
]


def get_db_connection():
    """Get database connection."""
    if HAS_DB:
        try:
            return psycopg2.connect(**POSTGRES_CONFIG, cursor_factory=RealDictCursor)
        except Exception:
            pass
    try:
        return psycopg2.connect(CONN_STR, cursor_factory=RealDictCursor)
    except Exception as e:
        print(f"Database connection failed: {e}")
        return None


def check_governance(project_path: Path) -> List[Dict]:
    """Check governance document compliance."""
    findings = []

    for doc in GOVERNANCE_FILES:
        doc_path = project_path / doc
        if doc_path.exists():
            # Check file has content
            try:
                content = doc_path.read_text(encoding='utf-8')
                if len(content) < 100:
                    findings.append({
                        'check': f'governance/{doc}',
                        'status': 'warning',
                        'details': f'{doc} exists but has very little content ({len(content)} chars)'
                    })
                else:
                    findings.append({
                        'check': f'governance/{doc}',
                        'status': 'pass',
                        'details': f'{doc} exists with {len(content)} chars'
                    })
            except Exception as e:
                findings.append({
                    'check': f'governance/{doc}',
                    'status': 'fail',
                    'details': f'Failed to read {doc}: {e}'
                })
        else:
            findings.append({
                'check': f'governance/{doc}',
                'status': 'fail',
                'details': f'{doc} is missing'
            })

    # Check hooks.json exists
    hooks_path = project_path / '.claude' / 'hooks.json'
    if hooks_path.exists():
        findings.append({
            'check': 'governance/hooks.json',
            'status': 'pass',
            'details': 'Hooks configuration exists'
        })
    else:
        findings.append({
            'check': 'governance/hooks.json',
            'status': 'fail',
            'details': 'hooks.json is missing'
        })

    # Check commands directory
    commands_path = project_path / '.claude' / 'commands'
    if commands_path.exists():
        commands = list(commands_path.glob('*.md'))
        if len(commands) >= len(REQUIRED_COMMANDS):
            findings.append({
                'check': 'governance/commands',
                'status': 'pass',
                'details': f'{len(commands)} commands found'
            })
        else:
            findings.append({
                'check': 'governance/commands',
                'status': 'warning',
                'details': f'Only {len(commands)} commands found, expected at least {len(REQUIRED_COMMANDS)}'
            })
    else:
        findings.append({
            'check': 'governance/commands',
            'status': 'fail',
            'details': 'Commands directory is missing'
        })

    return findings


def check_documentation(project_path: Path) -> List[Dict]:
    """Check documentation quality."""
    findings = []

    docs_path = project_path / 'docs'
    if not docs_path.exists():
        findings.append({
            'check': 'documentation/docs_folder',
            'status': 'fail',
            'details': 'docs/ folder is missing'
        })
        return findings

    findings.append({
        'check': 'documentation/docs_folder',
        'status': 'pass',
        'details': 'docs/ folder exists'
    })

    # Count docs
    md_files = list(docs_path.rglob('*.md'))
    findings.append({
        'check': 'documentation/file_count',
        'status': 'pass',
        'details': f'{len(md_files)} markdown files found'
    })

    # Check for recent updates (any file modified in last 30 days)
    recent_updates = 0
    cutoff = datetime.now().timestamp() - (30 * 24 * 60 * 60)
    for f in md_files:
        if f.stat().st_mtime > cutoff:
            recent_updates += 1

    if recent_updates > 0:
        findings.append({
            'check': 'documentation/recent_updates',
            'status': 'pass',
            'details': f'{recent_updates} files updated in last 30 days'
        })
    else:
        findings.append({
            'check': 'documentation/recent_updates',
            'status': 'warning',
            'details': 'No documentation updates in last 30 days'
        })

    return findings


def check_data_quality(conn, project_name: str) -> List[Dict]:
    """Check data quality in the database for this project."""
    findings = []

    if not conn:
        findings.append({
            'check': 'data_quality/database',
            'status': 'skip',
            'details': 'No database connection'
        })
        return findings

    cur = conn.cursor()

    # Check for test data in sessions
    cur.execute("""
        SELECT COUNT(*) as count FROM claude.sessions
        WHERE project_name = %s
          AND (session_summary ILIKE '%%test%%' OR session_summary ILIKE '%%dummy%%')
    """, (project_name,))
    result = cur.fetchone()
    if result['count'] > 0:
        findings.append({
            'check': 'data_quality/test_sessions',
            'status': 'warning',
            'details': f'{result["count"]} sessions with test/dummy in summary'
        })
    else:
        findings.append({
            'check': 'data_quality/test_sessions',
            'status': 'pass',
            'details': 'No test data found in sessions'
        })

    # Check session count
    cur.execute("""
        SELECT COUNT(*) as count FROM claude.sessions
        WHERE project_name = %s AND session_start > NOW() - INTERVAL '30 days'
    """, (project_name,))
    result = cur.fetchone()
    findings.append({
        'check': 'data_quality/session_count',
        'status': 'pass',
        'details': f'{result["count"]} sessions in last 30 days'
    })

    return findings


def check_standards(project_path: Path) -> List[Dict]:
    """Check standards compliance."""
    findings = []

    # Check if standards docs exist (should be in claude-family)
    standards_path = PROJECTS_BASE / 'claude-family' / 'docs' / 'standards'
    if not standards_path.exists():
        findings.append({
            'check': 'standards/standards_docs',
            'status': 'warning',
            'details': 'Standards documents not found in claude-family'
        })
        return findings

    standards = list(standards_path.glob('*.md'))
    findings.append({
        'check': 'standards/standards_docs',
        'status': 'pass',
        'details': f'{len(standards)} standards documents available'
    })

    # Check if process_router is referenced in hooks
    hooks_path = project_path / '.claude' / 'hooks.json'
    if hooks_path.exists():
        try:
            hooks = json.loads(hooks_path.read_text(encoding='utf-8'))
            if 'UserPromptSubmit' in hooks.get('hooks', {}):
                findings.append({
                    'check': 'standards/process_router',
                    'status': 'pass',
                    'details': 'Process router configured in UserPromptSubmit hook'
                })
            else:
                findings.append({
                    'check': 'standards/process_router',
                    'status': 'fail',
                    'details': 'UserPromptSubmit hook not configured'
                })
        except Exception as e:
            findings.append({
                'check': 'standards/process_router',
                'status': 'fail',
                'details': f'Failed to parse hooks.json: {e}'
            })

    return findings


def run_audit(project_name: str, audit_type: str, session_id: Optional[str] = None) -> Tuple[str, List[Dict]]:
    """Run an audit and return audit_id and findings."""
    project_path = PROJECTS_BASE / project_name

    if not project_path.exists():
        return None, [{'check': 'project_exists', 'status': 'fail', 'details': f'Project {project_name} not found'}]

    conn = get_db_connection()
    findings = []

    # Run appropriate checks
    if audit_type in ('governance', 'all'):
        findings.extend(check_governance(project_path))

    if audit_type in ('documentation', 'all'):
        findings.extend(check_documentation(project_path))

    if audit_type in ('data_quality', 'all'):
        findings.extend(check_data_quality(conn, project_name))

    if audit_type in ('standards', 'all'):
        findings.extend(check_standards(project_path))

    # Count results
    passed = len([f for f in findings if f['status'] == 'pass'])
    failed = len([f for f in findings if f['status'] == 'fail'])
    skipped = len([f for f in findings if f['status'] == 'skip'])
    warnings = len([f for f in findings if f['status'] == 'warning'])

    # Store results
    if conn:
        try:
            cur = conn.cursor()
            audit_id = str(uuid.uuid4())
            cur.execute("""
                INSERT INTO claude.compliance_audits (
                    audit_id, project_name, audit_type, status,
                    triggered_by, checks_passed, checks_failed, checks_skipped,
                    findings, initiated_by_session_id, completed_at
                )
                VALUES (%s, %s, %s, 'completed', 'manual', %s, %s, %s, %s, %s, NOW())
                RETURNING audit_id
            """, (
                audit_id, project_name, audit_type,
                passed, failed + warnings, skipped,
                json.dumps(findings),
                session_id
            ))

            # Update schedule
            cur.execute("""
                UPDATE claude.audit_schedule
                SET last_audit_date = NOW(),
                    next_audit_date = NOW() + (frequency_days || ' days')::INTERVAL,
                    updated_at = NOW()
                WHERE project_name = %s AND audit_type = %s
            """, (project_name, audit_type))

            conn.commit()
            conn.close()
            return audit_id, findings
        except Exception as e:
            print(f"Failed to store audit results: {e}")
            if conn:
                conn.rollback()
                conn.close()

    return None, findings


def format_findings(findings: List[Dict]) -> str:
    """Format findings for display."""
    output = []

    for f in findings:
        icon = {
            'pass': '[OK]',
            'fail': '[FAIL]',
            'warning': '[WARN]',
            'skip': '[SKIP]'
        }.get(f['status'], '[?]')

        output.append(f"  {icon} {f['check']}: {f['details']}")

    return '\n'.join(output)


def main():
    """Main entry point."""
    # Parse args
    project_name = sys.argv[1] if len(sys.argv) > 1 else 'claude-family'
    audit_type = sys.argv[2] if len(sys.argv) > 2 else 'all'

    print(f"Compliance Audit - {project_name}")
    print(f"Type: {audit_type}")
    print("=" * 50)

    audit_id, findings = run_audit(project_name, audit_type)

    print(format_findings(findings))
    print()

    # Summary
    passed = len([f for f in findings if f['status'] == 'pass'])
    failed = len([f for f in findings if f['status'] == 'fail'])
    warnings = len([f for f in findings if f['status'] == 'warning'])

    print(f"Summary: {passed} passed, {failed} failed, {warnings} warnings")

    if audit_id:
        print(f"Audit ID: {audit_id}")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
