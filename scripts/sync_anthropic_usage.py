#!/usr/bin/env python3
"""
Anthropic Usage & Cost Sync Script

Purpose: Fetch usage and cost data from Anthropic API and store in PostgreSQL
Author: claude-code-unified
Date: 2025-11-04

Features:
- Fetches token usage data from Anthropic Usage API
- Fetches cost data from Anthropic Cost API
- Stores data in PostgreSQL with duplicate prevention
- Tracks sync status and errors
- Supports incremental sync (only fetch new data)

Usage:
    python scripts/sync_anthropic_usage.py [--days 7] [--type usage|cost|both]

Requirements:
    - ANTHROPIC_ADMIN_API_KEY environment variable (sk-ant-admin...)
    - PostgreSQL credentials in config.py
"""

import sys
import os
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
import argparse
import json

# Add ai-workspace to path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
from config import POSTGRES_CONFIG

# Anthropic API configuration
ANTHROPIC_API_BASE = "https://api.anthropic.com/v1/organizations"
ANTHROPIC_VERSION = "2023-06-01"


def get_admin_api_key():
    """Get Anthropic Admin API key from environment"""
    key = os.getenv('ANTHROPIC_ADMIN_API_KEY')
    if not key:
        print("❌ ERROR: ANTHROPIC_ADMIN_API_KEY environment variable not set")
        print("   This requires an Admin API key (starts with sk-ant-admin...)")
        print("   Get it from: https://console.anthropic.com/settings/keys")
        sys.exit(1)
    if not key.startswith('sk-ant-admin'):
        print("⚠️  WARNING: API key doesn't start with 'sk-ant-admin'")
        print("   Make sure you're using an Admin API key, not a regular key")
    return key


def get_last_sync_date(conn, sync_type):
    """Get the last successfully synced date"""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT MAX(end_date) as last_sync
        FROM claude_family.usage_sync_status
        WHERE sync_type = %s AND sync_status = 'success'
    """, (sync_type,))
    result = cur.fetchone()
    cur.close()

    if result and result['last_sync']:
        return result['last_sync']
    else:
        # Default to 30 days ago if never synced
        return datetime.now() - timedelta(days=30)


def fetch_usage_data(api_key, start_date, end_date, bucket_width='1d'):
    """
    Fetch usage data from Anthropic API

    Args:
        api_key: Admin API key
        start_date: Start timestamp
        end_date: End timestamp
        bucket_width: '1m', '1h', or '1d'

    Returns:
        List of usage records
    """
    url = f"{ANTHROPIC_API_BASE}/usage_report/messages"

    params = {
        'starting_at': start_date.isoformat() + 'Z',
        'ending_at': end_date.isoformat() + 'Z',
        'bucket_width': bucket_width
    }

    headers = {
        'anthropic-version': ANTHROPIC_VERSION,
        'x-api-key': api_key,
        'User-Agent': 'ClaudeFamily-UsageTracker/1.0'
    }

    all_records = []
    page = None

    while True:
        if page:
            params['page'] = page

        print(f"   Fetching usage data (page: {page or 'first'})...")

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Extract usage records
            if 'data' in data:
                all_records.extend(data['data'])
                print(f"   Retrieved {len(data['data'])} records")

            # Check for more pages
            if data.get('has_more'):
                page = data.get('next_page')
            else:
                break

        except requests.exceptions.HTTPError as e:
            print(f"   ❌ HTTP Error: {e}")
            print(f"   Response: {e.response.text}")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break

    return all_records


def fetch_cost_data(api_key, start_date, end_date):
    """
    Fetch cost data from Anthropic API

    Args:
        api_key: Admin API key
        start_date: Start date
        end_date: End date

    Returns:
        List of cost records
    """
    url = f"{ANTHROPIC_API_BASE}/cost_report"

    params = {
        'starting_at': start_date.isoformat() + 'Z',
        'ending_at': end_date.isoformat() + 'Z'
    }

    headers = {
        'anthropic-version': ANTHROPIC_VERSION,
        'x-api-key': api_key,
        'User-Agent': 'ClaudeFamily-UsageTracker/1.0'
    }

    all_records = []
    page = None

    while True:
        if page:
            params['page'] = page

        print(f"   Fetching cost data (page: {page or 'first'})...")

        try:
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            # Extract cost records
            if 'data' in data:
                all_records.extend(data['data'])
                print(f"   Retrieved {len(data['data'])} records")

            # Check for more pages
            if data.get('has_more'):
                page = data.get('next_page')
            else:
                break

        except requests.exceptions.HTTPError as e:
            print(f"   ❌ HTTP Error: {e}")
            print(f"   Response: {e.response.text}")
            break
        except Exception as e:
            print(f"   ❌ Error: {e}")
            break

    return all_records


def import_usage_data(conn, records):
    """Import usage records into PostgreSQL"""
    if not records:
        return 0, 0

    cur = conn.cursor()
    imported = 0
    skipped = 0

    for record in records:
        try:
            # Extract bucket times
            bucket_start = datetime.fromisoformat(record['bucket_start_time'].replace('Z', '+00:00'))
            bucket_end = datetime.fromisoformat(record['bucket_end_time'].replace('Z', '+00:00'))

            # Extract token metrics
            uncached_input = record.get('uncached_input_tokens', 0)
            cached_input = record.get('cached_input_tokens', 0)
            cache_creation = record.get('cache_creation_tokens', 0)
            output = record.get('output_tokens', 0)

            # Insert with ON CONFLICT to handle duplicates
            cur.execute("""
                INSERT INTO claude_family.api_usage_data (
                    bucket_start_time, bucket_end_time, bucket_width,
                    model, workspace_id, workspace_name,
                    service_tier, context_window, api_key_id,
                    uncached_input_tokens, cached_input_tokens,
                    cache_creation_tokens, output_tokens
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (bucket_start_time, bucket_width, model, workspace_id, service_tier, context_window, api_key_id)
                DO NOTHING
            """, (
                bucket_start, bucket_end, record.get('bucket_width'),
                record.get('model'), record.get('workspace_id'), record.get('workspace_name'),
                record.get('service_tier'), record.get('context_window'), record.get('api_key_id'),
                uncached_input, cached_input, cache_creation, output
            ))

            if cur.rowcount > 0:
                imported += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"   ⚠️  Error importing record: {e}")
            print(f"   Record: {json.dumps(record, indent=2)}")
            continue

    conn.commit()
    cur.close()

    return imported, skipped


def import_cost_data(conn, records):
    """Import cost records into PostgreSQL"""
    if not records:
        return 0, 0

    cur = conn.cursor()
    imported = 0
    skipped = 0

    for record in records:
        try:
            # Extract date
            date = datetime.fromisoformat(record['date'].replace('Z', '+00:00')).date()

            # Cost is in cents (USD)
            cost_cents = int(float(record['cost_usd']) * 100)

            # Insert with ON CONFLICT to handle duplicates
            cur.execute("""
                INSERT INTO claude_family.api_cost_data (
                    date, workspace_id, workspace_name, description, cost_cents
                ) VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (date, workspace_id, description)
                DO UPDATE SET
                    cost_cents = EXCLUDED.cost_cents,
                    synced_at = NOW()
            """, (
                date,
                record.get('workspace_id'),
                record.get('workspace_name'),
                record.get('description', 'Token Usage'),
                cost_cents
            ))

            if cur.rowcount > 0:
                imported += 1
            else:
                skipped += 1

        except Exception as e:
            print(f"   ⚠️  Error importing record: {e}")
            print(f"   Record: {json.dumps(record, indent=2)}")
            continue

    conn.commit()
    cur.close()

    return imported, skipped


def log_sync_status(conn, sync_type, start_date, end_date, imported, skipped, status, error=None):
    """Log sync status to database"""
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO claude_family.usage_sync_status (
                sync_type, start_date, end_date,
                records_imported, records_skipped,
                sync_status, error_message, completed_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (sync_type, start_date, end_date, imported, skipped, status, error))
        conn.commit()
    except Exception as e:
        print(f"   ⚠️  Failed to log sync status: {e}")
    finally:
        cur.close()


def sync_usage(conn, api_key, days=7):
    """Sync usage data"""
    print("\n📊 Syncing Usage Data...")

    # Determine date range
    last_sync = get_last_sync_date(conn, 'usage')
    start_date = last_sync
    end_date = datetime.now()

    if (end_date - start_date).days > days:
        start_date = end_date - timedelta(days=days)

    print(f"   Date range: {start_date.date()} to {end_date.date()}")

    try:
        # Fetch data from API
        records = fetch_usage_data(api_key, start_date, end_date, bucket_width='1d')
        print(f"   Total records fetched: {len(records)}")

        # Import into database
        imported, skipped = import_usage_data(conn, records)
        print(f"   ✅ Imported: {imported}, Skipped (duplicates): {skipped}")

        # Log success
        log_sync_status(conn, 'usage', start_date, end_date, imported, skipped, 'success')

        return True

    except Exception as e:
        print(f"   ❌ Sync failed: {e}")
        log_sync_status(conn, 'usage', start_date, end_date, 0, 0, 'failed', str(e))
        return False


def sync_costs(conn, api_key, days=7):
    """Sync cost data"""
    print("\n💰 Syncing Cost Data...")

    # Determine date range
    last_sync = get_last_sync_date(conn, 'cost')
    start_date = last_sync
    end_date = datetime.now()

    if (end_date - start_date).days > days:
        start_date = end_date - timedelta(days=days)

    print(f"   Date range: {start_date.date()} to {end_date.date()}")

    try:
        # Fetch data from API
        records = fetch_cost_data(api_key, start_date, end_date)
        print(f"   Total records fetched: {len(records)}")

        # Import into database
        imported, skipped = import_cost_data(conn, records)
        print(f"   ✅ Imported: {imported}, Updated/Skipped: {skipped}")

        # Log success
        log_sync_status(conn, 'cost', start_date, end_date, imported, skipped, 'success')

        return True

    except Exception as e:
        print(f"   ❌ Sync failed: {e}")
        log_sync_status(conn, 'cost', start_date, end_date, 0, 0, 'failed', str(e))
        return False


def main():
    parser = argparse.ArgumentParser(description='Sync Anthropic usage and cost data')
    parser.add_argument('--days', type=int, default=7, help='Number of days to sync (default: 7)')
    parser.add_argument('--type', choices=['usage', 'cost', 'both'], default='both', help='What to sync')
    args = parser.parse_args()

    print("=" * 80)
    print("🔄 Anthropic Usage & Cost Sync")
    print("=" * 80)

    # Get API key
    api_key = get_admin_api_key()
    print(f"✅ Admin API key loaded (starts with: {api_key[:15]}...)")

    # Connect to database
    try:
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        print("✅ Connected to PostgreSQL")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return 1

    # Perform sync
    success = True

    if args.type in ['usage', 'both']:
        success = sync_usage(conn, api_key, args.days) and success

    if args.type in ['cost', 'both']:
        success = sync_costs(conn, api_key, args.days) and success

    # Cleanup
    conn.close()

    print("\n" + "=" * 80)
    if success:
        print("✅ Sync completed successfully!")
    else:
        print("⚠️  Sync completed with errors (check logs above)")
    print("=" * 80 + "\n")

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
