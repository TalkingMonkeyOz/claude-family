"""
Auto-Sync Startup Script for Claude Desktop

Purpose: Run this script at Claude Desktop startup to:
1. Load PostgreSQL startup context (identity, knowledge, recent sessions)
2. Generate MCP memory sync instructions
3. Save instructions to file for Claude to execute

This provides the "glue" between PostgreSQL (permanent storage)
and MCP memory (session storage).

Usage: Add to Claude Desktop startup config or run manually at session start

Date: 2025-10-10
Author: Claude Desktop & John
"""

import sys
import os
import io
import subprocess

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Get script directory
script_dir = os.path.dirname(os.path.abspath(__file__))

def main():
    """Run both startup scripts"""
    print('=' * 80)
    print('CLAUDE FAMILY AUTO-SYNC STARTUP')
    print('=' * 80)
    print()

    # Step 1: Load PostgreSQL context
    print('Step 1: Loading PostgreSQL startup context...')
    print('-' * 80)
    startup_script = os.path.join(script_dir, 'load_claude_startup_context.py')
    result = subprocess.run([sys.executable, startup_script], capture_output=False)

    if result.returncode != 0:
        print('\n❌ Failed to load startup context')
        return 1

    print()

    # Step 2: Generate MCP sync data
    print('Step 2: Generating MCP memory sync data...')
    print('-' * 80)
    sync_script = os.path.join(script_dir, 'sync_postgres_to_mcp.py')
    result = subprocess.run([sys.executable, sync_script], capture_output=False)

    if result.returncode != 0:
        print('\n❌ Failed to generate MCP sync data')
        return 1

    print()
    print('=' * 80)
    print('✅ AUTO-SYNC COMPLETE')
    print('=' * 80)
    print()
    print('Next: Claude will read the JSON files and populate MCP memory graph')
    print()

    # Create instruction file for Claude
    instructions_file = os.path.join(script_dir, 'MCP_SYNC_INSTRUCTIONS.txt')
    with open(instructions_file, 'w', encoding='utf-8') as f:
        f.write('=' * 80 + '\n')
        f.write('MCP MEMORY SYNC INSTRUCTIONS\n')
        f.write('=' * 80 + '\n\n')
        f.write('PostgreSQL data has been exported to JSON files. To restore your memory:\n\n')
        f.write('1. Read: mcp_sync_entities.json\n')
        f.write('2. Use create_entities tool to add all identities and knowledge\n')
        f.write('3. Read: mcp_sync_relations.json\n')
        f.write('4. Use create_relations tool to link everything together\n\n')
        f.write('Files are in: ' + script_dir + '\n\n')
        f.write('This restores your persistent memory from PostgreSQL into the MCP graph.\n')

    print(f'📝 Instructions saved to: {instructions_file}')
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
