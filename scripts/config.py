"""
Claude Family - Configuration
Centralized config loading for all scripts.

Loads from multiple sources in priority order:
1. Environment variables (highest priority)
2. .env file in scripts directory
3. .env file in project root
4. Shared .env in C:/claude/shared/
5. Legacy ai-workspace .env (fallback)

Provides:
- load_env_file / load_all_env_files: .env loading with quote stripping
- detect_psycopg: Cached psycopg v2/v3 detection
- get_database_uri: Lazy URI resolution from multiple env var names
- get_db_connection: Full connection with auto-detect, strict/graceful modes
- get_voyage_key / get_anthropic_key: Lazy key accessors
- POSTGRES_CONFIG, DATABASE_URI, ANTHROPIC_API_KEY: Legacy module-level exports
"""
import os
from pathlib import Path


def load_env_file(filepath: Path) -> bool:
    """Load .env file if it exists. Returns True if loaded.

    Handles:
    - Comments (lines starting with #)
    - Surrounding quotes on values (single or double)
    - ${VAR} placeholder literals (Claude Desktop bug) — skipped
    - Existing env vars are NOT overridden
    """
    if not filepath.exists():
        return False

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Strip surrounding quotes
                    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                        value = value[1:-1]
                    # Skip ${VAR} placeholder literals (Claude Desktop bug)
                    if value.startswith('${') and value.endswith('}'):
                        continue
                    # Don't override existing env vars
                    if key not in os.environ:
                        os.environ[key] = value
        return True
    except (IOError, OSError):
        return False


def load_all_env_files():
    """Load env files from all possible locations (priority order)."""
    locations = [
        Path(__file__).parent / '.env',                          # scripts/.env
        Path(__file__).parent.parent / '.env',                   # claude-family/.env
        Path(r'C:\claude\shared\.env'),                          # Shared config
        Path.home() / '.claude' / '.env',                        # User config
        Path(r'C:\Users\johnd\OneDrive\Documents\AI_projects\ai-workspace\.env'),  # Legacy
    ]

    for loc in locations:
        load_env_file(loc)


# Load environment on import
load_all_env_files()


# Database configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', '5432')),
    'database': os.getenv('POSTGRES_DATABASE', 'ai_company_foundation'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', ''),
}

# Build DATABASE_URI for MCP compatibility
DATABASE_URI = (
    f"postgresql://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}"
    f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
)

# API Keys
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')

# Paths
CLAUDE_FAMILY_ROOT = Path(__file__).parent.parent
STANDARDS_PATH = CLAUDE_FAMILY_ROOT / 'docs' / 'standards'
SHARED_PATH = Path(r'C:\claude\shared')


# --- Psycopg detection (cached) ---

_psycopg_cache = None


def detect_psycopg():
    """Detect available psycopg driver. Cached after first call.

    Returns:
        tuple: (module, version, row_factory_or_cursor, cursor_class_or_none)
            - v3: (psycopg, 3, dict_row, None)
            - v2: (psycopg2, 2, None, RealDictCursor)
            - none: (None, 0, None, None)
    """
    global _psycopg_cache
    if _psycopg_cache is not None:
        return _psycopg_cache

    try:
        import psycopg
        from psycopg.rows import dict_row
        _psycopg_cache = (psycopg, 3, dict_row, None)
    except ImportError:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            _psycopg_cache = (psycopg2, 2, None, RealDictCursor)
        except ImportError:
            _psycopg_cache = (None, 0, None, None)

    return _psycopg_cache


def get_database_uri():
    """Get database connection URI. Checks multiple env var names.

    Priority: DATABASE_URI > DATABASE_URL > POSTGRES_CONNECTION_STRING > build from POSTGRES_CONFIG.
    Sets both DATABASE_URI and DATABASE_URL in os.environ for backward compatibility.

    Returns:
        str or None: Connection URI, or None if no password configured.
    """
    uri = (
        os.environ.get('DATABASE_URI')
        or os.environ.get('DATABASE_URL')
        or os.environ.get('POSTGRES_CONNECTION_STRING')
    )

    if not uri:
        # Build from POSTGRES_CONFIG parts
        pw = POSTGRES_CONFIG.get('password', '')
        if not pw:
            return None
        uri = (
            f"postgresql://{POSTGRES_CONFIG['user']}:{pw}"
            f"@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"
        )

    # Set both names for backward compat
    os.environ.setdefault('DATABASE_URI', uri)
    os.environ.setdefault('DATABASE_URL', uri)
    return uri


def get_db_connection(strict=False):
    """Get a PostgreSQL connection with auto-detected psycopg driver.

    Args:
        strict: If True, raises on failure (for MCP servers).
                If False, returns None on failure (for hooks).

    Returns:
        Connection object or None (when strict=False).

    Raises:
        ImportError: When strict=True and no psycopg driver found.
        ConnectionError: When strict=True and connection fails.
    """
    mod, version, dict_row_factory, cursor_class = detect_psycopg()

    if mod is None:
        if strict:
            raise ImportError("No psycopg driver found. Install psycopg or psycopg2.")
        return None

    uri = get_database_uri()
    if not uri:
        if strict:
            raise ConnectionError(
                "No database URI. Set DATABASE_URI env var or POSTGRES_PASSWORD in .env"
            )
        return None

    try:
        if version == 3:
            return mod.connect(uri, row_factory=dict_row_factory)
        else:
            return mod.connect(uri, cursor_factory=cursor_class)
    except Exception as e:
        if strict:
            raise ConnectionError(f"Database connection failed: {e}") from e
        return None


def get_voyage_key():
    """Get Voyage AI API key from environment."""
    return os.environ.get('VOYAGE_API_KEY')


def get_anthropic_key():
    """Get Anthropic API key from environment."""
    return os.environ.get('ANTHROPIC_API_KEY')


# Validation helpers
def validate_postgres():
    """Check if postgres config is complete."""
    if not POSTGRES_CONFIG['password']:
        raise ValueError(
            "POSTGRES_PASSWORD not found. Create .env file with POSTGRES_PASSWORD=..."
        )
    return True


def validate_anthropic():
    """Check if Anthropic API key is set."""
    if not ANTHROPIC_API_KEY:
        raise ValueError(
            "ANTHROPIC_API_KEY not found. Create .env file with ANTHROPIC_API_KEY=..."
        )
    return True


__all__ = [
    # Legacy module-level exports (unchanged)
    'POSTGRES_CONFIG',
    'DATABASE_URI',
    'ANTHROPIC_API_KEY',
    'CLAUDE_FAMILY_ROOT',
    'STANDARDS_PATH',
    'SHARED_PATH',
    'validate_postgres',
    'validate_anthropic',
    # New functions
    'load_env_file',
    'load_all_env_files',
    'detect_psycopg',
    'get_database_uri',
    'get_db_connection',
    'get_voyage_key',
    'get_anthropic_key',
]
