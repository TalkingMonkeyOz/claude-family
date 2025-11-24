#!/usr/bin/env python3
"""
Anthropic Usage & Cost Viewer

Purpose: Interactive console interface to view API usage and costs
Author: claude-code-unified
Date: 2025-11-04

Features:
- Daily/weekly/monthly spending reports
- Usage by model, project, identity
- Cache efficiency metrics
- Budget alert status
- Export to CSV

Usage:
    python scripts/view_usage.py [command] [options]

Commands:
    summary - Show overall summary (default)
    daily - Show daily spending
    models - Show usage by model
    projects - Show usage by project
    alerts - Show budget alert status
    export - Export data to CSV

Examples:
    python scripts/view_usage.py
    python scripts/view_usage.py daily --days 30
    python scripts/view_usage.py models --sort tokens
    python scripts/view_usage.py export --output usage.csv
"""

import sys
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import argparse
from decimal import Decimal
import csv

# Add ai-workspace to path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
from config import POSTGRES_CONFIG

# Terminal colors (Windows compatible)
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def format_number(num):
    """Format large numbers with commas"""
    if num is None:
        return "0"
    return f"{int(num):,}"

def format_currency(amount):
    """Format currency with $ sign"""
    if amount is None:
        return "$0.00"
    return f"${float(amount):.2f}"

def format_percent(value):
    """Format percentage"""
    if value is None:
        return "0%"
    return f"{float(value):.1f}%"

def print_header(title):
    """Print section header"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{title.center(80)}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 80}{Colors.ENDC}\n")

def print_row(label, value, color=Colors.GREEN):
    """Print a label-value row"""
    print(f"  {Colors.BOLD}{label:.<50}{Colors.ENDC} {color}{value}{Colors.ENDC}")

def show_summary(conn):
    """Show overall usage summary"""
    print_header("📊 USAGE & COST SUMMARY")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Total spending (all time)
    cur.execute("""
        SELECT
            SUM(cost_usd) as total_cost,
            MIN(date) as first_date,
            MAX(date) as last_date,
            COUNT(DISTINCT date) as days_tracked
        FROM claude_family.api_cost_data
    """)
    cost_summary = cur.fetchone()

    # Total tokens (last 30 days)
    cur.execute("""
        SELECT
            SUM(total_tokens) as total_tokens,
            SUM(uncached_input_tokens) as uncached_input,
            SUM(cached_input_tokens) as cached_input,
            SUM(output_tokens) as output,
            COUNT(*) as total_requests
        FROM claude_family.api_usage_data
        WHERE bucket_start_time >= NOW() - INTERVAL '30 days'
    """)
    usage_summary = cur.fetchone()

    # Recent spending
    cur.execute("""
        SELECT
            SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '1 day' THEN cost_usd ELSE 0 END) as today,
            SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '7 days' THEN cost_usd ELSE 0 END) as week,
            SUM(CASE WHEN date >= CURRENT_DATE - INTERVAL '30 days' THEN cost_usd ELSE 0 END) as month
        FROM claude_family.api_cost_data
    """)
    recent_costs = cur.fetchone()

    cur.close()

    # Display cost summary
    print(f"{Colors.BOLD}💰 COST SUMMARY{Colors.ENDC}")
    print_row("Total Spending (All Time)", format_currency(cost_summary['total_cost']), Colors.GREEN)
    print_row("Today", format_currency(recent_costs['today']), Colors.CYAN)
    print_row("Last 7 Days", format_currency(recent_costs['week']), Colors.CYAN)
    print_row("Last 30 Days", format_currency(recent_costs['month']), Colors.CYAN)
    print_row("Days Tracked", str(cost_summary['days_tracked'] or 0), Colors.BLUE)
    if cost_summary['first_date']:
        print_row("Tracking Since", cost_summary['first_date'].strftime('%Y-%m-%d'), Colors.BLUE)

    # Display token summary
    print(f"\n{Colors.BOLD}🎯 TOKEN USAGE (Last 30 Days){Colors.ENDC}")
    print_row("Total Tokens", format_number(usage_summary['total_tokens']), Colors.GREEN)
    print_row("Uncached Input Tokens", format_number(usage_summary['uncached_input']), Colors.CYAN)
    print_row("Cached Input Tokens", format_number(usage_summary['cached_input']), Colors.CYAN)
    print_row("Output Tokens", format_number(usage_summary['output']), Colors.CYAN)
    print_row("Total Requests", format_number(usage_summary['total_requests']), Colors.BLUE)

    # Calculate cache efficiency
    if usage_summary['uncached_input'] and usage_summary['cached_input']:
        total_input = usage_summary['uncached_input'] + usage_summary['cached_input']
        cache_hit_rate = (usage_summary['cached_input'] / total_input) * 100
        print_row("Cache Hit Rate", format_percent(cache_hit_rate), Colors.GREEN if cache_hit_rate > 20 else Colors.YELLOW)


def show_daily(conn, days=30):
    """Show daily spending breakdown"""
    print_header(f"📅 DAILY SPENDING (Last {days} Days)")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            date,
            SUM(cost_usd) as daily_cost,
            COUNT(DISTINCT workspace_id) as workspaces
        FROM claude_family.api_cost_data
        WHERE date >= CURRENT_DATE - INTERVAL '%s days'
        GROUP BY date
        ORDER BY date DESC
        LIMIT %s
    """, (days, days))

    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("  No data available for this period.")
        return

    # Print table
    print(f"  {'Date':<15} {'Cost':<15} {'Workspaces':<15}")
    print(f"  {'-' * 45}")

    total_cost = Decimal(0)
    for row in rows:
        cost_color = Colors.GREEN if row['daily_cost'] < 5 else (Colors.YELLOW if row['daily_cost'] < 10 else Colors.RED)
        print(f"  {row['date'].strftime('%Y-%m-%d'):<15} {cost_color}{format_currency(row['daily_cost']):<15}{Colors.ENDC} {row['workspaces']}")
        total_cost += Decimal(str(row['daily_cost']))

    print(f"  {'-' * 45}")
    print(f"  {'TOTAL':<15} {Colors.BOLD}{format_currency(total_cost):<15}{Colors.ENDC}")


def show_models(conn, sort_by='tokens'):
    """Show usage by model"""
    print_header("🤖 USAGE BY MODEL (Last 30 Days)")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    sort_column = {
        'tokens': 'total_tokens',
        'requests': 'request_count',
        'cache': 'cache_hit_rate_percent'
    }.get(sort_by, 'total_tokens')

    cur.execute(f"""
        SELECT
            model,
            COUNT(*) as request_count,
            SUM(total_tokens) as total_tokens,
            SUM(uncached_input_tokens) as uncached_input,
            SUM(cached_input_tokens) as cached_input,
            SUM(output_tokens) as output,
            ROUND(
                CASE
                    WHEN SUM(uncached_input_tokens + cached_input_tokens) > 0
                    THEN (SUM(cached_input_tokens)::DECIMAL / SUM(uncached_input_tokens + cached_input_tokens)) * 100
                    ELSE 0
                END,
                1
            ) as cache_hit_rate
        FROM claude_family.api_usage_data
        WHERE bucket_start_time >= NOW() - INTERVAL '30 days'
        GROUP BY model
        ORDER BY {sort_column} DESC
    """)

    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("  No data available.")
        return

    # Print table
    print(f"  {'Model':<30} {'Requests':<12} {'Total Tokens':<15} {'Cache Hit %':<12}")
    print(f"  {'-' * 69}")

    for row in rows:
        cache_color = Colors.GREEN if row['cache_hit_rate'] > 20 else Colors.YELLOW
        print(f"  {row['model']:<30} {format_number(row['request_count']):<12} {format_number(row['total_tokens']):<15} {cache_color}{format_percent(row['cache_hit_rate']):<12}{Colors.ENDC}")


def show_projects(conn):
    """Show usage by project"""
    print_header("📁 USAGE BY PROJECT (Last 30 Days)")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            COALESCE(project_name, 'Unknown') as project,
            COUNT(*) as sessions,
            SUM(total_tokens) as total_tokens,
            AVG(total_tokens) as avg_tokens
        FROM claude_family.api_usage_data
        WHERE bucket_start_time >= NOW() - INTERVAL '30 days'
        GROUP BY project_name
        ORDER BY total_tokens DESC
    """)

    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("  No project data available.")
        return

    # Print table
    print(f"  {'Project':<30} {'Sessions':<12} {'Total Tokens':<15} {'Avg/Session':<15}")
    print(f"  {'-' * 72}")

    for row in rows:
        print(f"  {row['project']:<30} {format_number(row['sessions']):<12} {format_number(row['total_tokens']):<15} {format_number(row['avg_tokens']):<15}")


def show_alerts(conn):
    """Show budget alert status"""
    print_header("⚠️  BUDGET ALERTS")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            alert_name,
            alert_type,
            threshold_type,
            threshold_value,
            current_value,
            ROUND((current_value / NULLIF(threshold_value, 0)) * 100, 1) as percent_of_threshold,
            threshold_exceeded,
            last_checked
        FROM claude_family.budget_alerts
        WHERE is_active = TRUE
        ORDER BY percent_of_threshold DESC
    """)

    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("  No active alerts configured.")
        print(f"\n  {Colors.YELLOW}💡 TIP: Create alerts to monitor your spending!{Colors.ENDC}")
        print("  Example: INSERT INTO claude_family.budget_alerts")
        print("           (alert_name, alert_type, threshold_type, threshold_value)")
        print("           VALUES ('Daily Budget', 'daily', 'cost', 10.00);")
        return

    # Print table
    print(f"  {'Alert':<25} {'Type':<10} {'Current':<12} {'Threshold':<12} {'Status':<15}")
    print(f"  {'-' * 74}")

    for row in rows:
        status_color = Colors.RED if row['threshold_exceeded'] else (Colors.YELLOW if row['percent_of_threshold'] > 80 else Colors.GREEN)
        status_text = "🔴 EXCEEDED" if row['threshold_exceeded'] else (f"⚠️  {format_percent(row['percent_of_threshold'])}" if row['percent_of_threshold'] > 80 else f"✅ {format_percent(row['percent_of_threshold'])}")

        current = format_currency(row['current_value']) if row['threshold_type'] == 'cost' else format_number(row['current_value'])
        threshold = format_currency(row['threshold_value']) if row['threshold_type'] == 'cost' else format_number(row['threshold_value'])

        print(f"  {row['alert_name']:<25} {row['alert_type']:<10} {current:<12} {threshold:<12} {status_color}{status_text:<15}{Colors.ENDC}")


def export_to_csv(conn, output_file='usage_export.csv'):
    """Export usage data to CSV"""
    print_header(f"📄 EXPORTING TO CSV: {output_file}")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("""
        SELECT
            bucket_start_time,
            model,
            workspace_name,
            project_name,
            total_tokens,
            uncached_input_tokens,
            cached_input_tokens,
            output_tokens
        FROM claude_family.api_usage_data
        ORDER BY bucket_start_time DESC
    """)

    rows = cur.fetchall()
    cur.close()

    if not rows:
        print("  No data to export.")
        return

    # Write to CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"  ✅ Exported {len(rows)} records to {output_file}")


def main():
    parser = argparse.ArgumentParser(description='View Anthropic usage and costs')
    parser.add_argument('command', nargs='?', default='summary', choices=['summary', 'daily', 'models', 'projects', 'alerts', 'export'],
                       help='Command to run (default: summary)')
    parser.add_argument('--days', type=int, default=30, help='Number of days for daily view')
    parser.add_argument('--sort', choices=['tokens', 'requests', 'cache'], default='tokens', help='Sort models by')
    parser.add_argument('--output', default='usage_export.csv', help='Output file for export')

    args = parser.parse_args()

    # Connect to database
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
    except Exception as e:
        print(f"{Colors.RED}❌ Database connection failed: {e}{Colors.ENDC}")
        return 1

    # Execute command
    try:
        if args.command == 'summary':
            show_summary(conn)
        elif args.command == 'daily':
            show_daily(conn, args.days)
        elif args.command == 'models':
            show_models(conn, args.sort)
        elif args.command == 'projects':
            show_projects(conn)
        elif args.command == 'alerts':
            show_alerts(conn)
        elif args.command == 'export':
            export_to_csv(conn, args.output)
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        conn.close()

    return 0


if __name__ == '__main__':
    sys.exit(main())
