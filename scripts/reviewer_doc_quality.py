#!/usr/bin/env python3
"""
Documentation Quality Reviewer

Reviews project documentation for staleness, completeness, and consistency.
Used by doc-reviewer-sonnet agent or run standalone.

Usage:
    python reviewer_doc_quality.py [--project <name>] [--all]

Output:
    JSON report with findings by severity
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Database imports
DB_AVAILABLE = False
try:
    import psycopg
    from psycopg.rows import dict_row
    DB_AVAILABLE = True
    PSYCOPG_VERSION = 3
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        DB_AVAILABLE = True
        PSYCOPG_VERSION = 2
    except ImportError:
        DB_AVAILABLE = False

CONN_STR = 'postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation'

# Core documents that every project must have
REQUIRED_DOCS = {
    'CLAUDE.md': {
        'stale_days': 7,
        'required_sections': [
            '## Problem Statement',
            '## Current Phase',
            '## Architecture Overview',
            '## Coding Standards',
            '## Work Tracking',
            '## Recent Changes',
            '**Version**:',
            '**Updated**:'
        ]
    },
    'PROBLEM_STATEMENT.md': {
        'stale_days': 30,
        'required_sections': [
            '## Problem Definition',
            '## Target Users',
            '## Success Criteria'
        ]
    },
    'ARCHITECTURE.md': {
        'stale_days': 30,
        'required_sections': [
            '## Overview',
            '## System Components'
        ]
    }
}

PROJECTS_ROOT = Path('C:/Projects')


def get_db_connection():
    """Get PostgreSQL connection."""
    try:
        if PSYCOPG_VERSION == 3:
            return psycopg.connect(CONN_STR, row_factory=dict_row)
        else:
            return psycopg.connect(CONN_STR, cursor_factory=RealDictCursor)
    except Exception:
        return None


def get_projects_from_db() -> list:
    """Get active projects from database."""
    if not DB_AVAILABLE:
        return []

    conn = get_db_connection()
    if not conn:
        return []

    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT project_id, project_name, status, phase
            FROM claude.projects
            WHERE is_archived = false
            ORDER BY project_name
        """)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return [dict(r) if not isinstance(r, dict) else r for r in results]
    except Exception as e:
        return []


def check_doc_exists(project_path: Path, doc_name: str) -> dict:
    """Check if a document exists."""
    doc_path = project_path / doc_name
    return {
        'exists': doc_path.exists(),
        'path': str(doc_path)
    }


def check_doc_staleness(project_path: Path, doc_name: str, stale_days: int) -> dict:
    """Check if document is stale based on modification date."""
    doc_path = project_path / doc_name
    if not doc_path.exists():
        return {'stale': None, 'age_days': None, 'threshold': stale_days}

    mtime = datetime.fromtimestamp(doc_path.stat().st_mtime)
    age_days = (datetime.now() - mtime).days

    return {
        'stale': age_days > stale_days,
        'age_days': age_days,
        'threshold': stale_days,
        'last_modified': mtime.isoformat()
    }


def check_doc_sections(project_path: Path, doc_name: str, required_sections: list) -> dict:
    """Check if document has all required sections."""
    doc_path = project_path / doc_name
    if not doc_path.exists():
        return {'complete': None, 'missing': required_sections}

    try:
        content = doc_path.read_text(encoding='utf-8')
        missing = [s for s in required_sections if s not in content]
        return {
            'complete': len(missing) == 0,
            'missing': missing,
            'found': [s for s in required_sections if s in content]
        }
    except Exception as e:
        return {'complete': None, 'error': str(e)}


def check_version_footer(project_path: Path, doc_name: str) -> dict:
    """Check if document has valid version footer."""
    doc_path = project_path / doc_name
    if not doc_path.exists():
        return {'valid': None}

    try:
        content = doc_path.read_text(encoding='utf-8')
        has_version = '**Version**:' in content
        has_updated = '**Updated**:' in content

        # Try to extract the updated date
        updated_date = None
        for line in content.split('\n'):
            if '**Updated**:' in line:
                parts = line.split('**Updated**:')
                if len(parts) > 1:
                    updated_date = parts[1].strip()
                break

        return {
            'valid': has_version and has_updated,
            'has_version': has_version,
            'has_updated': has_updated,
            'updated_date': updated_date
        }
    except Exception as e:
        return {'valid': None, 'error': str(e)}


def review_project(project_name: str) -> dict:
    """Review a single project's documentation."""
    project_path = PROJECTS_ROOT / project_name

    if not project_path.exists():
        return {
            'project': project_name,
            'error': f'Project path does not exist: {project_path}',
            'findings': []
        }

    findings = []

    for doc_name, config in REQUIRED_DOCS.items():
        doc_findings = {
            'document': doc_name,
            'checks': {}
        }

        # Check existence
        exists_check = check_doc_exists(project_path, doc_name)
        doc_findings['checks']['exists'] = exists_check

        if not exists_check['exists']:
            findings.append({
                'severity': 'critical',
                'document': doc_name,
                'issue': 'Document missing',
                'remediation': f'Create {doc_name} from template'
            })
            continue

        # Check staleness
        stale_check = check_doc_staleness(project_path, doc_name, config['stale_days'])
        doc_findings['checks']['staleness'] = stale_check

        if stale_check.get('stale'):
            severity = 'critical' if doc_name == 'CLAUDE.md' else 'warning'
            findings.append({
                'severity': severity,
                'document': doc_name,
                'issue': f'Document stale ({stale_check["age_days"]} days old, threshold: {stale_check["threshold"]})',
                'remediation': f'Review and update {doc_name}'
            })

        # Check sections
        section_check = check_doc_sections(project_path, doc_name, config['required_sections'])
        doc_findings['checks']['sections'] = section_check

        if section_check.get('missing'):
            findings.append({
                'severity': 'warning',
                'document': doc_name,
                'issue': f'Missing sections: {", ".join(section_check["missing"])}',
                'remediation': f'Add missing sections to {doc_name}'
            })

        # Check version footer
        version_check = check_version_footer(project_path, doc_name)
        doc_findings['checks']['version_footer'] = version_check

        if not version_check.get('valid'):
            findings.append({
                'severity': 'info',
                'document': doc_name,
                'issue': 'Missing or incomplete version footer',
                'remediation': 'Add **Version**: and **Updated**: to document footer'
            })

    return {
        'project': project_name,
        'path': str(project_path),
        'reviewed_at': datetime.now().isoformat(),
        'summary': {
            'critical': len([f for f in findings if f['severity'] == 'critical']),
            'warning': len([f for f in findings if f['severity'] == 'warning']),
            'info': len([f for f in findings if f['severity'] == 'info'])
        },
        'findings': findings
    }


def review_all_projects() -> dict:
    """Review all active projects from database."""
    projects = get_projects_from_db()

    if not projects:
        # Fallback to directory scan
        projects = [
            {'project_name': p.name}
            for p in PROJECTS_ROOT.iterdir()
            if p.is_dir() and not p.name.startswith('.')
        ]

    results = {
        'reviewed_at': datetime.now().isoformat(),
        'project_count': len(projects),
        'projects': []
    }

    total_critical = 0
    total_warning = 0
    total_info = 0

    for project in projects:
        project_name = project.get('project_name') or project.get('name')
        review = review_project(project_name)
        results['projects'].append(review)

        if 'summary' in review:
            total_critical += review['summary']['critical']
            total_warning += review['summary']['warning']
            total_info += review['summary']['info']

    results['total_summary'] = {
        'critical': total_critical,
        'warning': total_warning,
        'info': total_info
    }

    return results


def main():
    if '--all' in sys.argv:
        results = review_all_projects()
    elif '--project' in sys.argv:
        idx = sys.argv.index('--project') + 1
        if idx < len(sys.argv):
            results = review_project(sys.argv[idx])
        else:
            print(json.dumps({'error': 'No project name provided'}))
            return 1
    else:
        # Default: review from current directory
        cwd = Path.cwd()
        if 'Projects' in cwd.parts:
            idx = cwd.parts.index('Projects')
            if len(cwd.parts) > idx + 1:
                project_name = cwd.parts[idx + 1]
                results = review_project(project_name)
            else:
                results = {'error': 'Cannot determine project from current directory'}
        else:
            results = {'error': 'Not in a project directory'}

    print(json.dumps(results, indent=2, default=str))

    # Always return 0 on successful run (scheduler interprets non-zero as failure)
    # Critical findings are reported via JSON output
    return 0


if __name__ == '__main__':
    sys.exit(main())
