"""
Run all Claude Family setup scripts in order
Executes: 01, 02, 03, 04 SQL files
"""
import sys
import os
import io

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add ai-workspace to path
sys.path.insert(0, r'c:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace')
from config import POSTGRES_CONFIG

import psycopg2

def run_sql_file(conn, filepath):
    """Execute a SQL file"""
    print(f'\n{"="*80}')
    print(f'Running: {os.path.basename(filepath)}')
    print("="*80)

    with open(filepath, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Remove psql-specific commands
    sql = sql.replace('\\c ai_company_foundation', '-- \\c ai_company_foundation (handled by Python connection)')

    cur = conn.cursor()

    try:
        cur.execute(sql)
        conn.commit()
        print(f'✅ {os.path.basename(filepath)} executed successfully')
        return True
    except Exception as e:
        print(f'❌ Error in {os.path.basename(filepath)}: {e}')
        conn.rollback()
        return False
    finally:
        cur.close()

def main():
    print('='*80)
    print('CLAUDE FAMILY FOUNDATION SETUP')
    print('='*80)
    print()
    print('This will create the claude_family schema and populate it with:')
    print('  1. Schema with 5 tables and helper functions')
    print('  2. 5 Claude identities (Desktop, Cursor, VS Code, Claude Code, Diana)')
    print('  3. Links to nimbus_context and public schemas')
    print('  4. Universal knowledge extracted from nimbus_context')
    print()

    try:
        # Connect
        print('Connecting to PostgreSQL...')
        conn = psycopg2.connect(**POSTGRES_CONFIG)
        print(f'✅ Connected to {conn.info.dbname} as {conn.info.user}')
        print()

        script_dir = os.path.dirname(os.path.abspath(__file__))
        # SQL scripts are in ../postgres/schema/
        schema_dir = os.path.join(os.path.dirname(script_dir), 'postgres', 'schema')
        scripts = [
            '01_create_claude_family_schema.sql',
            '02_seed_claude_identities.sql',
            '03_link_schemas.sql',
            '04_extract_universal_knowledge.sql'
        ]

        success_count = 0
        for script in scripts:
            filepath = os.path.join(schema_dir, script)
            if os.path.exists(filepath):
                if run_sql_file(conn, filepath):
                    success_count += 1
            else:
                print(f'❌ Script not found: {script}')

        conn.close()

        print()
        print('='*80)
        if success_count == len(scripts):
            print('✅ ALL SCRIPTS EXECUTED SUCCESSFULLY!')
        else:
            print(f'⚠️  {success_count}/{len(scripts)} scripts succeeded')
        print('='*80)
        print()

        if success_count == len(scripts):
            print('Next steps:')
            print('  1. Run: python load_claude_startup_context.py')
            print('  2. Verify identity and context loads correctly')
            print('  3. Test cross-Claude visibility')
            print()

        return 0 if success_count == len(scripts) else 1

    except Exception as e:
        print(f'\n❌ ERROR: {e}')
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
