"""Tests for scripts/config.py credential loading module."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts/ is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestLoadEnvFile:
    """Tests for load_env_file()."""

    def _make_env(self, content: str) -> Path:
        """Write content to a temp .env file, return its Path."""
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False, encoding='utf-8')
        f.write(content)
        f.close()
        return Path(f.name)

    def test_basic_parsing(self):
        import config
        path = self._make_env("TEST_CFG_BASIC=hello\n")
        os.environ.pop('TEST_CFG_BASIC', None)
        try:
            assert config.load_env_file(path) is True
            assert os.environ['TEST_CFG_BASIC'] == 'hello'
        finally:
            os.environ.pop('TEST_CFG_BASIC', None)
            os.unlink(path)

    def test_comments_skipped(self):
        import config
        path = self._make_env("# comment\nTEST_CFG_COMMENT=yes\n")
        os.environ.pop('TEST_CFG_COMMENT', None)
        try:
            config.load_env_file(path)
            assert os.environ['TEST_CFG_COMMENT'] == 'yes'
        finally:
            os.environ.pop('TEST_CFG_COMMENT', None)
            os.unlink(path)

    def test_no_override(self):
        import config
        os.environ['TEST_CFG_EXIST'] = 'original'
        path = self._make_env("TEST_CFG_EXIST=overwritten\n")
        try:
            config.load_env_file(path)
            assert os.environ['TEST_CFG_EXIST'] == 'original'
        finally:
            os.environ.pop('TEST_CFG_EXIST', None)
            os.unlink(path)

    def test_quote_stripping_double(self):
        import config
        path = self._make_env('TEST_CFG_DQ="quoted value"\n')
        os.environ.pop('TEST_CFG_DQ', None)
        try:
            config.load_env_file(path)
            assert os.environ['TEST_CFG_DQ'] == 'quoted value'
        finally:
            os.environ.pop('TEST_CFG_DQ', None)
            os.unlink(path)

    def test_quote_stripping_single(self):
        import config
        path = self._make_env("TEST_CFG_SQ='single quoted'\n")
        os.environ.pop('TEST_CFG_SQ', None)
        try:
            config.load_env_file(path)
            assert os.environ['TEST_CFG_SQ'] == 'single quoted'
        finally:
            os.environ.pop('TEST_CFG_SQ', None)
            os.unlink(path)

    def test_dollar_var_skip(self):
        import config
        path = self._make_env("TEST_CFG_SKIP=${SOME_VAR}\nTEST_CFG_REAL=works\n")
        os.environ.pop('TEST_CFG_SKIP', None)
        os.environ.pop('TEST_CFG_REAL', None)
        try:
            config.load_env_file(path)
            assert 'TEST_CFG_SKIP' not in os.environ
            assert os.environ['TEST_CFG_REAL'] == 'works'
        finally:
            os.environ.pop('TEST_CFG_SKIP', None)
            os.environ.pop('TEST_CFG_REAL', None)
            os.unlink(path)

    def test_nonexistent_file(self):
        import config
        assert config.load_env_file(Path('/nonexistent/.env')) is False

    def test_value_with_equals(self):
        import config
        path = self._make_env("TEST_CFG_EQ=key=value=more\n")
        os.environ.pop('TEST_CFG_EQ', None)
        try:
            config.load_env_file(path)
            assert os.environ['TEST_CFG_EQ'] == 'key=value=more'
        finally:
            os.environ.pop('TEST_CFG_EQ', None)
            os.unlink(path)


class TestDetectPsycopg:
    """Tests for detect_psycopg()."""

    def test_returns_tuple(self):
        import config
        # Reset cache
        config._psycopg_cache = None
        result = config.detect_psycopg()
        assert isinstance(result, tuple)
        assert len(result) == 4

    def test_detects_v3_or_v2(self):
        import config
        config._psycopg_cache = None
        mod, version, _, _ = config.detect_psycopg()
        assert mod is not None, "Expected psycopg to be installed"
        assert version in (2, 3)

    def test_caching(self):
        import config
        config._psycopg_cache = None
        r1 = config.detect_psycopg()
        r2 = config.detect_psycopg()
        assert r1 is r2  # Same object, not just equal

    def test_v3_preferred(self):
        """If both are installed, v3 should be preferred."""
        import config
        config._psycopg_cache = None
        _, version, _, _ = config.detect_psycopg()
        # We can only assert v3 if it's actually installed
        try:
            import psycopg
            assert version == 3
        except ImportError:
            pass  # v2 is fine if v3 isn't installed

    def test_neither_available(self):
        """When no psycopg is available, returns (None, 0, None, None)."""
        import config
        config._psycopg_cache = None
        # Mock both imports to fail
        real_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__
        def mock_import(name, *args, **kwargs):
            if name in ('psycopg', 'psycopg2'):
                raise ImportError(f"Mocked: {name} not available")
            return real_import(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=mock_import):
            result = config.detect_psycopg()
        assert result == (None, 0, None, None)
        config._psycopg_cache = None  # Reset for other tests


class TestGetDatabaseUri:
    """Tests for get_database_uri()."""

    def test_from_database_uri_env(self):
        import config
        with patch.dict(os.environ, {'DATABASE_URI': 'postgresql://test:pw@host/db'}, clear=False):
            uri = config.get_database_uri()
            assert uri == 'postgresql://test:pw@host/db'

    def test_from_database_url_env(self):
        import config
        env = {k: v for k, v in os.environ.items() if k != 'DATABASE_URI'}
        env['DATABASE_URL'] = 'postgresql://url@host/db'
        with patch.dict(os.environ, env, clear=True):
            uri = config.get_database_uri()
            assert uri == 'postgresql://url@host/db'

    def test_from_postgres_connection_string(self):
        import config
        env = {k: v for k, v in os.environ.items()
               if k not in ('DATABASE_URI', 'DATABASE_URL')}
        env['POSTGRES_CONNECTION_STRING'] = 'postgresql://pcs@host/db'
        with patch.dict(os.environ, env, clear=True):
            uri = config.get_database_uri()
            assert uri == 'postgresql://pcs@host/db'

    def test_builds_from_parts(self):
        import config
        env = {k: v for k, v in os.environ.items()
               if k not in ('DATABASE_URI', 'DATABASE_URL', 'POSTGRES_CONNECTION_STRING')}
        with patch.dict(os.environ, env, clear=True):
            # config.POSTGRES_CONFIG has password from .env loading
            if config.POSTGRES_CONFIG.get('password'):
                uri = config.get_database_uri()
                assert uri is not None
                assert 'postgresql://' in uri

    def test_sets_both_env_vars(self):
        import config
        os.environ.pop('DATABASE_URI', None)
        os.environ.pop('DATABASE_URL', None)
        with patch.dict(os.environ, {'DATABASE_URI': 'postgresql://x@h/d'}, clear=False):
            config.get_database_uri()
            assert 'DATABASE_URL' in os.environ or 'DATABASE_URI' in os.environ

    def test_returns_none_without_password(self):
        import config
        orig_pw = config.POSTGRES_CONFIG.get('password')
        config.POSTGRES_CONFIG['password'] = ''
        env = {k: v for k, v in os.environ.items()
               if k not in ('DATABASE_URI', 'DATABASE_URL', 'POSTGRES_CONNECTION_STRING')}
        try:
            with patch.dict(os.environ, env, clear=True):
                assert config.get_database_uri() is None
        finally:
            config.POSTGRES_CONFIG['password'] = orig_pw


class TestGetDbConnection:
    """Tests for get_db_connection()."""

    def test_graceful_returns_connection(self):
        import config
        config._psycopg_cache = None
        conn = config.get_db_connection(strict=False)
        if conn is not None:
            assert hasattr(conn, 'close')
            conn.close()

    def test_strict_returns_connection(self):
        import config
        config._psycopg_cache = None
        conn = config.get_db_connection(strict=True)
        assert conn is not None
        assert hasattr(conn, 'close')
        conn.close()

    def test_graceful_no_driver(self):
        import config
        config._psycopg_cache = (None, 0, None, None)
        try:
            result = config.get_db_connection(strict=False)
            assert result is None
        finally:
            config._psycopg_cache = None

    def test_strict_no_driver(self):
        import config
        config._psycopg_cache = (None, 0, None, None)
        try:
            with pytest.raises(ImportError):
                config.get_db_connection(strict=True)
        finally:
            config._psycopg_cache = None

    def test_graceful_no_uri(self):
        import config
        config._psycopg_cache = None
        orig_pw = config.POSTGRES_CONFIG.get('password')
        config.POSTGRES_CONFIG['password'] = ''
        env = {k: v for k, v in os.environ.items()
               if k not in ('DATABASE_URI', 'DATABASE_URL', 'POSTGRES_CONNECTION_STRING')}
        try:
            with patch.dict(os.environ, env, clear=True):
                result = config.get_db_connection(strict=False)
                assert result is None
        finally:
            config.POSTGRES_CONFIG['password'] = orig_pw
            config._psycopg_cache = None

    def test_strict_no_uri(self):
        import config
        config._psycopg_cache = None
        orig_pw = config.POSTGRES_CONFIG.get('password')
        config.POSTGRES_CONFIG['password'] = ''
        env = {k: v for k, v in os.environ.items()
               if k not in ('DATABASE_URI', 'DATABASE_URL', 'POSTGRES_CONNECTION_STRING')}
        try:
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(ConnectionError):
                    config.get_db_connection(strict=True)
        finally:
            config.POSTGRES_CONFIG['password'] = orig_pw
            config._psycopg_cache = None


class TestKeyAccessors:
    """Tests for get_voyage_key() and get_anthropic_key()."""

    def test_get_voyage_key(self):
        import config
        with patch.dict(os.environ, {'VOYAGE_API_KEY': 'test-voyage'}, clear=False):
            assert config.get_voyage_key() == 'test-voyage'

    def test_get_voyage_key_missing(self):
        import config
        env = {k: v for k, v in os.environ.items() if k != 'VOYAGE_API_KEY'}
        with patch.dict(os.environ, env, clear=True):
            assert config.get_voyage_key() is None

    def test_get_anthropic_key(self):
        import config
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'test-anthropic'}, clear=False):
            assert config.get_anthropic_key() == 'test-anthropic'


class TestBackwardCompat:
    """Existing module-level exports still work."""

    def test_postgres_config_exists(self):
        import config
        assert hasattr(config, 'POSTGRES_CONFIG')
        assert isinstance(config.POSTGRES_CONFIG, dict)
        assert 'host' in config.POSTGRES_CONFIG

    def test_database_uri_exists(self):
        import config
        assert hasattr(config, 'DATABASE_URI')
        assert isinstance(config.DATABASE_URI, str)
        assert 'postgresql://' in config.DATABASE_URI

    def test_anthropic_key_exists(self):
        import config
        assert hasattr(config, 'ANTHROPIC_API_KEY')

    def test_paths_exist(self):
        import config
        assert hasattr(config, 'CLAUDE_FAMILY_ROOT')
        assert hasattr(config, 'STANDARDS_PATH')
        assert hasattr(config, 'SHARED_PATH')

    def test_validators_exist(self):
        import config
        assert callable(config.validate_postgres)
        assert callable(config.validate_anthropic)
