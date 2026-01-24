#!/usr/bin/env python3
"""
Manager MUI MCP Server

Provides tools to help develop the claude-manager-mui Tauri application.
Tools for understanding codebase structure, patterns, and types.
"""

import os
import re
import json
import subprocess
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("manager-mui")

# Project paths
MANAGER_MUI_PATH = Path("C:/Projects/claude-manager-mui")
SRC_PATH = MANAGER_MUI_PATH / "src"
FEATURES_PATH = SRC_PATH / "features"
COMPONENTS_PATH = SRC_PATH / "components"
RUST_SRC = MANAGER_MUI_PATH / "src-tauri" / "src"


@mcp.tool()
def get_project_structure() -> str:
    """
    Get an overview of the claude-manager-mui project structure.
    Returns the main directories and their purposes.
    """
    structure = {
        "src/": {
            "App.tsx": "Main application component with sidebar navigation",
            "main.tsx": "Entry point, theme provider setup",
            "features/": "Feature-based organization (launcher, sessions, messages, etc.)",
            "components/": "Shared UI components (TabPanel, EntityList, etc.)",
            "contexts/": "React contexts (ThemeContext)",
            "hooks/": "Custom hooks (useNotification, useEntityCRUD)",
            "services/": "Tauri API service layer",
            "types/": "TypeScript type definitions",
            "theme/": "MUI theme configuration",
        },
        "src-tauri/": {
            "src/main.rs": "Tauri entry point",
            "src/lib.rs": "Command definitions",
            "src/commands/": "Rust command implementations",
            "Cargo.toml": "Rust dependencies",
        },
        "Key patterns": {
            "Feature folders": "Each feature has its own folder with components",
            "API layer": "All DB access through Tauri invoke commands",
            "Entity CRUD": "Reusable CRUD pattern via useEntityCRUD hook",
            "Configuration": "Database-driven config with skills, instructions, rules",
        }
    }
    return json.dumps(structure, indent=2)


@mcp.tool()
def list_features() -> str:
    """
    List all features in the features directory with their components.
    """
    features = {}

    if not FEATURES_PATH.exists():
        return json.dumps({"error": "Features path not found"})

    for feature_dir in FEATURES_PATH.iterdir():
        if feature_dir.is_dir():
            components = []
            for file in feature_dir.rglob("*.tsx"):
                rel_path = file.relative_to(feature_dir)
                components.append(str(rel_path))

            # Check for index.ts
            has_index = (feature_dir / "index.ts").exists()

            features[feature_dir.name] = {
                "components": sorted(components),
                "has_index": has_index,
                "path": f"src/features/{feature_dir.name}/"
            }

    return json.dumps(features, indent=2)


@mcp.tool()
def list_components() -> str:
    """
    List all shared components in the components directory.
    """
    components = {}

    if not COMPONENTS_PATH.exists():
        return json.dumps({"error": "Components path not found"})

    for file in COMPONENTS_PATH.rglob("*.tsx"):
        name = file.stem
        rel_path = file.relative_to(COMPONENTS_PATH)

        # Try to extract component props interface
        content = file.read_text(encoding='utf-8')
        props_match = re.search(r'interface\s+(\w+Props)\s*\{([^}]+)\}', content, re.DOTALL)

        props = None
        if props_match:
            props = props_match.group(2).strip()

        components[name] = {
            "path": f"src/components/{rel_path}",
            "props_preview": props[:200] + "..." if props and len(props) > 200 else props
        }

    return json.dumps(components, indent=2)


@mcp.tool()
def get_api_endpoints() -> str:
    """
    Get all available Tauri API endpoints from the api service.
    Returns function names, parameters, and return types.
    """
    api_file = SRC_PATH / "services" / "api.ts"

    if not api_file.exists():
        return json.dumps({"error": "API file not found"})

    content = api_file.read_text(encoding='utf-8')

    # Extract API methods
    endpoints = []

    # Match various patterns of method definitions
    patterns = [
        # Arrow functions: methodName: () => invoke<Type>('command')
        r'(\w+):\s*\(([^)]*)\)\s*=>\s*invoke<([^>]+)>\s*\([\'"](\w+)[\'"]',
        # Async functions: methodName: async (): Promise<Type>
        r'(\w+):\s*async\s*\(([^)]*)\):\s*Promise<([^>]+)>',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, content):
            method_name = match.group(1)
            params = match.group(2).strip()
            return_type = match.group(3)

            endpoints.append({
                "method": method_name,
                "params": params if params else "none",
                "returns": return_type
            })

    # Deduplicate by method name
    seen = set()
    unique_endpoints = []
    for ep in endpoints:
        if ep["method"] not in seen:
            seen.add(ep["method"])
            unique_endpoints.append(ep)

    return json.dumps({
        "count": len(unique_endpoints),
        "endpoints": sorted(unique_endpoints, key=lambda x: x["method"])
    }, indent=2)


@mcp.tool()
def get_types() -> str:
    """
    Get all TypeScript type/interface definitions from types/index.ts
    """
    types_file = SRC_PATH / "types" / "index.ts"

    if not types_file.exists():
        return json.dumps({"error": "Types file not found"})

    content = types_file.read_text(encoding='utf-8')

    types_list = []

    # Match interfaces
    for match in re.finditer(r'export\s+interface\s+(\w+)\s*\{', content):
        types_list.append({"name": match.group(1), "kind": "interface"})

    # Match type aliases
    for match in re.finditer(r'export\s+type\s+(\w+)\s*=', content):
        types_list.append({"name": match.group(1), "kind": "type"})

    # Match const objects
    for match in re.finditer(r'export\s+const\s+(\w+):\s*Record<', content):
        types_list.append({"name": match.group(1), "kind": "const"})

    return json.dumps({
        "count": len(types_list),
        "types": sorted(types_list, key=lambda x: x["name"])
    }, indent=2)


@mcp.tool()
def get_type_definition(type_name: str) -> str:
    """
    Get the full definition of a specific TypeScript type/interface.

    Args:
        type_name: Name of the type or interface to look up
    """
    types_file = SRC_PATH / "types" / "index.ts"

    if not types_file.exists():
        return json.dumps({"error": "Types file not found"})

    content = types_file.read_text(encoding='utf-8')

    # Try to find interface definition
    pattern = rf'export\s+interface\s+{type_name}\s*\{{([^}}]+)\}}'
    match = re.search(pattern, content, re.DOTALL)

    if match:
        return json.dumps({
            "name": type_name,
            "kind": "interface",
            "definition": match.group(1).strip()
        }, indent=2)

    # Try type alias
    pattern = rf'export\s+type\s+{type_name}\s*=\s*([^;]+);'
    match = re.search(pattern, content)

    if match:
        return json.dumps({
            "name": type_name,
            "kind": "type",
            "definition": match.group(1).strip()
        }, indent=2)

    return json.dumps({"error": f"Type '{type_name}' not found"})


@mcp.tool()
def search_code(pattern: str, file_type: str = "tsx") -> str:
    """
    Search for a pattern in the codebase.

    Args:
        pattern: Regex pattern to search for
        file_type: File extension to search (tsx, ts, rs, etc.)
    """
    results = []

    search_path = SRC_PATH if file_type in ["tsx", "ts"] else RUST_SRC

    if not search_path.exists():
        return json.dumps({"error": f"Search path not found: {search_path}"})

    for file in search_path.rglob(f"*.{file_type}"):
        try:
            content = file.read_text(encoding='utf-8')
            matches = list(re.finditer(pattern, content))

            if matches:
                rel_path = file.relative_to(MANAGER_MUI_PATH)
                file_matches = []

                for m in matches[:5]:  # Limit to 5 matches per file
                    # Get line number
                    line_num = content[:m.start()].count('\n') + 1
                    # Get the line content
                    lines = content.split('\n')
                    line_content = lines[line_num - 1].strip() if line_num <= len(lines) else ""

                    file_matches.append({
                        "line": line_num,
                        "content": line_content[:100]
                    })

                results.append({
                    "file": str(rel_path),
                    "matches": file_matches,
                    "total_matches": len(matches)
                })
        except Exception as e:
            continue

    return json.dumps({
        "pattern": pattern,
        "results": results[:20],  # Limit to 20 files
        "files_searched": file_type
    }, indent=2)


@mcp.tool()
def get_component_usage(component_name: str) -> str:
    """
    Find where a component is used throughout the codebase.

    Args:
        component_name: Name of the component to find usages of
    """
    results = []

    for file in SRC_PATH.rglob("*.tsx"):
        try:
            content = file.read_text(encoding='utf-8')

            # Look for import and usage
            has_import = re.search(rf"import\s+.*{component_name}.*from", content)
            usages = list(re.finditer(rf"<{component_name}[\s/>]", content))

            if has_import or usages:
                rel_path = file.relative_to(MANAGER_MUI_PATH)
                results.append({
                    "file": str(rel_path),
                    "imported": bool(has_import),
                    "usage_count": len(usages)
                })
        except Exception:
            continue

    return json.dumps({
        "component": component_name,
        "usages": results
    }, indent=2)


@mcp.tool()
def get_rust_commands() -> str:
    """
    Get all Tauri command definitions from the Rust backend.
    These are the commands that can be invoked from the frontend.
    """
    commands = []

    if not RUST_SRC.exists():
        return json.dumps({"error": "Rust src path not found"})

    # Look for #[tauri::command] annotations
    for file in RUST_SRC.rglob("*.rs"):
        try:
            content = file.read_text(encoding='utf-8')
            rel_path = file.relative_to(MANAGER_MUI_PATH)

            # Find command annotations followed by function definitions
            pattern = r'#\[tauri::command\]\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)'

            for match in re.finditer(pattern, content):
                fn_name = match.group(1)
                commands.append({
                    "command": fn_name,
                    "file": str(rel_path)
                })
        except Exception:
            continue

    return json.dumps({
        "count": len(commands),
        "commands": sorted(commands, key=lambda x: x["command"])
    }, indent=2)


@mcp.tool()
def get_hooks() -> str:
    """
    List all custom React hooks defined in the project.
    """
    hooks = []

    hooks_path = SRC_PATH / "hooks"

    if not hooks_path.exists():
        return json.dumps({"error": "Hooks path not found"})

    for file in hooks_path.rglob("*.ts*"):
        try:
            content = file.read_text(encoding='utf-8')
            rel_path = file.relative_to(MANAGER_MUI_PATH)

            # Find hook definitions (functions starting with 'use')
            pattern = r'export\s+(?:function|const)\s+(use\w+)'

            for match in re.finditer(pattern, content):
                hook_name = match.group(1)
                hooks.append({
                    "name": hook_name,
                    "file": str(rel_path)
                })
        except Exception:
            continue

    return json.dumps({
        "count": len(hooks),
        "hooks": hooks
    }, indent=2)


@mcp.tool()
def get_theme_config() -> str:
    """
    Get the MUI theme configuration from the theme file.
    """
    theme_file = SRC_PATH / "theme" / "theme.ts"

    if not theme_file.exists():
        return json.dumps({"error": "Theme file not found"})

    content = theme_file.read_text(encoding='utf-8')

    # Just return the file content since it's likely small
    return json.dumps({
        "file": "src/theme/theme.ts",
        "content": content
    }, indent=2)


@mcp.tool()
def get_feature_detail(feature_name: str) -> str:
    """
    Get detailed information about a specific feature including its components,
    exports, and structure.

    Args:
        feature_name: Name of the feature folder (e.g., 'launcher', 'sessions')
    """
    feature_path = FEATURES_PATH / feature_name

    if not feature_path.exists():
        return json.dumps({"error": f"Feature '{feature_name}' not found"})

    detail = {
        "name": feature_name,
        "path": f"src/features/{feature_name}/",
        "components": [],
        "exports": []
    }

    # List all TSX files
    for file in feature_path.rglob("*.tsx"):
        rel_path = file.relative_to(feature_path)

        content = file.read_text(encoding='utf-8')

        # Find exported components
        exports = re.findall(r'export\s+(?:default\s+)?(?:function|const)\s+(\w+)', content)

        detail["components"].append({
            "file": str(rel_path),
            "exports": exports
        })

    # Check index.ts for re-exports
    index_file = feature_path / "index.ts"
    if index_file.exists():
        content = index_file.read_text(encoding='utf-8')
        detail["index_exports"] = content.strip()

    return json.dumps(detail, indent=2)


@mcp.tool()
def check_build_status() -> str:
    """
    Check if the project builds successfully by running tsc.
    Returns any TypeScript errors.
    """
    try:
        result = subprocess.run(
            ["npx", "tsc", "--noEmit"],
            cwd=MANAGER_MUI_PATH,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            return json.dumps({
                "status": "success",
                "message": "No TypeScript errors"
            })
        else:
            # Parse errors
            errors = result.stdout + result.stderr
            return json.dumps({
                "status": "error",
                "errors": errors[:2000]  # Limit output
            }, indent=2)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "message": "Build check timed out"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


if __name__ == "__main__":
    mcp.run()
