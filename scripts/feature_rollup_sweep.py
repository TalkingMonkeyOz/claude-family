#!/usr/bin/env python3
"""
Feature Rollup Sweep — Advance stale in_progress features, notify on stale planned ones.

F209: Complements the synchronous auto-rollup in WorkflowEngine.check_feature_completion
by catching features whose last child transitioned WITHOUT triggering the side-effect
(e.g. status flipped manually, external tool edits).

Logic:
  - Find features where status IN ('in_progress','planned') and:
      * all direct build_tasks are completed/cancelled, AND
      * all child features are completed/cancelled, AND
      * feature has at least one child (direct task or child feature)
  - For in_progress: advance to completed via WorkflowEngine with change_source='sweep_rollup'
  - For planned: log notification to audit_log (no auto-advance — pre-gate policy varies by project)

Usage:
    python feature_rollup_sweep.py            # Run sweep
    python feature_rollup_sweep.py --dry-run  # Report only, no changes
    python feature_rollup_sweep.py --project claude-family  # Limit to one project

Author: Claude Family
Feature: F209
Date: 2026-04-19
"""

import argparse
import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import get_db_connection

# Make the project-tools WorkflowEngine importable for the in_progress path.
_PROJECT_TOOLS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'mcp-servers', 'project-tools',
)
sys.path.insert(0, os.path.abspath(_PROJECT_TOOLS))

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('feature_rollup_sweep')


STALE_FEATURES_SQL = """
WITH feature_children AS (
  SELECT
    f.feature_id,
    f.short_code,
    f.feature_name,
    f.status,
    f.project_id,
    COUNT(DISTINCT cf.feature_id) FILTER (WHERE cf.status NOT IN ('completed','cancelled')) AS open_child_features,
    COUNT(DISTINCT cf.feature_id) AS total_child_features,
    COUNT(DISTINCT bt.task_id) FILTER (WHERE bt.status NOT IN ('completed','cancelled')) AS open_direct_tasks,
    COUNT(DISTINCT bt.task_id) AS total_direct_tasks,
    COUNT(DISTINCT cbt.task_id) FILTER (WHERE cbt.status NOT IN ('completed','cancelled')) AS open_grandchild_tasks,
    COUNT(DISTINCT cbt.task_id) AS total_grandchild_tasks
  FROM claude.features f
  LEFT JOIN claude.features cf ON cf.parent_feature_id = f.feature_id
  LEFT JOIN claude.build_tasks bt ON bt.feature_id = f.feature_id
  LEFT JOIN claude.build_tasks cbt ON cbt.feature_id = cf.feature_id
  WHERE f.status IN ('in_progress','planned')
  GROUP BY f.feature_id, f.short_code, f.feature_name, f.status, f.project_id
)
SELECT fc.feature_id, fc.short_code, fc.feature_name, fc.status,
       p.project_name
FROM feature_children fc
LEFT JOIN claude.projects p ON p.project_id = fc.project_id
WHERE (fc.total_child_features + fc.total_direct_tasks + fc.total_grandchild_tasks) > 0
  AND fc.open_child_features = 0
  AND fc.open_direct_tasks = 0
  AND fc.open_grandchild_tasks = 0
ORDER BY fc.short_code;
"""


def find_stale_features(conn, project_filter=None):
    """Return features where all children are done but the feature is still open."""
    cur = conn.cursor()
    try:
        cur.execute(STALE_FEATURES_SQL)
        rows = cur.fetchall()
        if project_filter:
            rows = [r for r in rows if r['project_name'] == project_filter]
        return rows
    finally:
        cur.close()


def auto_advance_in_progress(conn, feature_row, dry_run=False):
    """Advance an in_progress feature to completed via WorkflowEngine."""
    code = f"F{feature_row['short_code']}"
    if dry_run:
        logger.info(f"[dry-run] Would advance {code} ({feature_row['feature_name']}) → completed")
        return {'success': True, 'dry_run': True, 'entity_code': code}

    # Import lazily so dry-run mode works without project-tools on path
    from server_v2 import WorkflowEngine  # noqa: E402
    engine = WorkflowEngine(conn)
    result = engine.execute_transition(
        entity_type='features',
        item_id=code,
        new_status='completed',
        change_source='sweep_rollup',
        metadata={
            'reason': 'all_children_completed',
            'detected_by': 'feature_rollup_sweep',
        },
    )
    if result.get('success'):
        logger.info(f"Advanced {code} ({feature_row['feature_name']}) → completed")
    else:
        logger.warning(f"Failed to advance {code}: {result.get('error')}")
    return result


def notify_planned(conn, feature_row, dry_run=False):
    """Log a notification to audit_log for a planned feature with all children done.

    Planned features are NOT auto-advanced — project policy varies (e.g. METIS uses
    'planned' as pre-gate). The audit entry surfaces the state for human review.
    """
    code = f"F{feature_row['short_code']}"
    if dry_run:
        logger.info(
            f"[dry-run] Would log notification: {code} ({feature_row['feature_name']}) "
            f"is 'planned' with all children done — review manually"
        )
        return {'success': True, 'dry_run': True, 'entity_code': code}

    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO claude.audit_log
              (entity_type, entity_id, entity_code, from_status, to_status,
               changed_by, change_source, event_type, metadata)
            VALUES (%s, %s::uuid, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                'features',
                str(feature_row['feature_id']),
                code,
                'planned',
                'planned',
                None,
                'feature_rollup_sweep',
                'rollup_notification',
                json.dumps({
                    'reason': 'all_children_completed_but_planned',
                    'project': feature_row['project_name'],
                    'note': 'Planned feature has all tasks done. Review policy — auto-advance disabled.',
                }),
            ),
        )
        conn.commit()
        logger.info(f"Notified: {code} ({feature_row['feature_name']}) — planned with all children done")
        return {'success': True, 'entity_code': code, 'action': 'notified'}
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to log notification for {code}: {e}")
        return {'success': False, 'error': str(e)}
    finally:
        cur.close()


def run_sweep(dry_run=False, project_filter=None):
    """Find and process all stale features. Return a summary dict."""
    conn = get_db_connection()
    try:
        stale = find_stale_features(conn, project_filter=project_filter)
        logger.info(f"Found {len(stale)} stale feature(s){' in project ' + project_filter if project_filter else ''}")

        advanced = []
        notified = []
        failed = []
        for row in stale:
            if row['status'] == 'in_progress':
                result = auto_advance_in_progress(conn, row, dry_run=dry_run)
                if result.get('success'):
                    advanced.append(f"F{row['short_code']}")
                else:
                    failed.append({'code': f"F{row['short_code']}", 'error': result.get('error')})
            elif row['status'] == 'planned':
                result = notify_planned(conn, row, dry_run=dry_run)
                if result.get('success'):
                    notified.append(f"F{row['short_code']}")
                else:
                    failed.append({'code': f"F{row['short_code']}", 'error': result.get('error')})

        summary = {
            'total_stale': len(stale),
            'advanced': advanced,
            'notified': notified,
            'failed': failed,
            'dry_run': dry_run,
        }
        logger.info(f"Sweep complete: {json.dumps(summary)}")
        return summary
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description='Feature rollup sweep (F209)')
    parser.add_argument('--dry-run', action='store_true', help='Report only, no changes')
    parser.add_argument('--project', help='Limit sweep to a single project')
    args = parser.parse_args()

    summary = run_sweep(dry_run=args.dry_run, project_filter=args.project)
    # Exit 0 on success (even if some individual features failed — sweep itself completed)
    # Non-zero only on script-level errors (DB connect, query crash).
    if summary['failed']:
        logger.warning(f"Sweep completed with {len(summary['failed'])} per-feature failures")
    return 0


if __name__ == '__main__':
    sys.exit(main())
