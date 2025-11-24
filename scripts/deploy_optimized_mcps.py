"""
Deploy Optimized MCP Configurations - Option A (Conservative)

This script:
1. Backs up existing MCP configurations
2. Deploys optimized configs to appropriate locations
3. Validates JSON syntax
4. Logs changes to PostgreSQL

Run: python scripts/deploy_optimized_mcps.py
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
import psycopg2

# Paths
BACKUP_DIR = Path("C:/Projects/claude-family/backups/mcp-configs")
CONFIG_SOURCE = Path("C:/Projects/claude-family/configs")

DEPLOYMENTS = {
    "global": {
        "source": CONFIG_SOURCE / "global-mcp-optimized.json",
        "target": Path.home() / ".claude" / "mcp.json",
        "description": "Global minimal MCPs (all instances)"
    },
    "nimbus": {
        "source": CONFIG_SOURCE / "nimbus-mcp-optimized.json",
        "target": Path("C:/Projects/nimbus-user-loader/.mcp.json"),
        "description": "Nimbus C# WinForms project"
    },
    "claude-pm": {
        "source": CONFIG_SOURCE / "claudepm-mcp-optimized.json",
        "target": Path("C:/Projects/claude-pm/.mcp.json"),
        "description": "Claude PM C# WPF project"
    },
    "ato": {
        "source": CONFIG_SOURCE / "ato-mcp-optimized.json",
        "target": Path("C:/Projects/ATO-Tax-Agent/.mcp.json"),
        "description": "ATO web research project"
    },
    "claude-family": {
        "source": CONFIG_SOURCE / "claude-family-mcp-optimized.json",
        "target": Path("C:/Projects/claude-family/.mcp.json"),
        "description": "Claude Family infrastructure project"
    }
}

DB_URI = "postgresql://postgres:05OX79HNFCjQwhotDjVx@localhost/ai_company_foundation"

def validate_json(file_path):
    """Validate JSON file syntax."""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        # Remove comment fields for deployment
        if "mcpServers" in data:
            clean_data = {"mcpServers": data["mcpServers"]}
            return clean_data
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {file_path}: {e}")
        return None

def backup_existing(target_path, backup_dir):
    """Backup existing config file."""
    if target_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backup_dir / f"{target_path.stem}_{timestamp}.json"
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, backup_path)
        print(f"  📦 Backed up to: {backup_path}")
        return backup_path
    return None

def deploy_config(name, config_info, dry_run=False):
    """Deploy a single configuration file."""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Deploying {name}:")
    print(f"  Description: {config_info['description']}")
    print(f"  Source: {config_info['source']}")
    print(f"  Target: {config_info['target']}")

    # Validate source
    clean_data = validate_json(config_info['source'])
    if not clean_data:
        return False

    # Backup existing
    if not dry_run:
        backup_existing(config_info['target'], BACKUP_DIR)

    # Deploy
    if not dry_run:
        with open(config_info['target'], 'w') as f:
            json.dump(clean_data, f, indent=2)
        print(f"  ✅ Deployed successfully")
    else:
        print(f"  ✅ Validation passed (dry run)")

    return True

def log_to_database(deployment_summary):
    """Log deployment to PostgreSQL."""
    try:
        conn = psycopg2.connect(DB_URI)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO claude_family.shared_knowledge
            (knowledge_type, knowledge_category, title, description, code_example, confidence_level)
            VALUES ('procedure', 'mcp', %s, %s, %s, 10)
        """, (
            "MCP Configuration Optimization Deployment",
            deployment_summary['description'],
            deployment_summary['changes']
        ))

        conn.commit()
        cursor.close()
        conn.close()
        print("\n✅ Logged deployment to PostgreSQL")
    except Exception as e:
        print(f"\n⚠️  Could not log to database: {e}")

def main():
    import sys

    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    print("=" * 80)
    print("MCP Configuration Optimization Deployment - Option A (Conservative)")
    print("=" * 80)
    print(f"\nMode: {'DRY RUN (no changes)' if dry_run else 'LIVE DEPLOYMENT'}")

    if not dry_run:
        print("\n⚠️  WARNING: This will modify MCP configurations!")
        print("⚠️  Make sure ALL Claude instances are CLOSED before proceeding.")
        response = input("\nContinue? (yes/no): ")
        if response.lower() != "yes":
            print("Aborted.")
            return

    # Deploy each configuration
    results = {}
    for name, config_info in DEPLOYMENTS.items():
        success = deploy_config(name, config_info, dry_run)
        results[name] = "✅ Success" if success else "❌ Failed"

    # Summary
    print("\n" + "=" * 80)
    print("DEPLOYMENT SUMMARY")
    print("=" * 80)
    for name, result in results.items():
        print(f"{result} {name}")

    if not dry_run:
        # Log to database
        deployment_summary = {
            "description": f"Deployed optimized MCP configs to {len(DEPLOYMENTS)} locations",
            "changes": json.dumps(results, indent=2)
        }
        log_to_database(deployment_summary)

        print("\n" + "=" * 80)
        print("NEXT STEPS")
        print("=" * 80)
        print("1. Restart Claude Code instances")
        print("2. Run /mcp list to verify configs loaded")
        print("3. Run /context to check token savings")
        print("4. Test for 1 week, monitor for missing tools")
        print("5. If successful, proceed to Option B (remove tree-sitter)")

    print("\nBackups stored in:", BACKUP_DIR)

if __name__ == "__main__":
    main()
