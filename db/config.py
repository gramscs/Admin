"""Moved from __init__.py."""

import os
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


def require_database_uri():
    """Require a PostgreSQL DATABASE_URL for production, allow SQLite in development."""
    raw_uri = os.getenv("DATABASE_URL", "").strip()
    if not raw_uri:
        if os.getenv("FLASK_ENV", "").strip().lower() == "development":
            return "sqlite:///test.db"
        raise RuntimeError("DATABASE_URL is required. SQLite is no longer supported.")

    if raw_uri.startswith("sqlite://"):
        if os.getenv("FLASK_ENV", "").strip().lower() == "development":
            return raw_uri
        raise RuntimeError("SQLite is only supported for development testing.")

    raw_uri = normalize_postgres_uri(raw_uri)

    if not raw_uri.startswith("postgresql://"):
        raise RuntimeError("DATABASE_URL must be a PostgreSQL URL (postgresql://...).")

    return raw_uri


def normalize_postgres_uri(raw_uri):
    """Normalize postgres URIs and enforce SSL for Supabase hosts."""
    # Some platforms expose postgres:// which SQLAlchemy does not accept.
    if raw_uri.startswith("postgres://"):
        raw_uri = raw_uri.replace("postgres://", "postgresql://", 1)

    parsed = urlparse(raw_uri)
    hostname = (parsed.hostname or "").lower()

    if "supabase.com" in hostname:
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_params.setdefault("sslmode", "require")
        parsed = parsed._replace(query=urlencode(query_params))
        raw_uri = urlunparse(parsed)

    return raw_uri


def build_engine_options(db_uri, env_bool_fn, env_int_fn):
    if db_uri.startswith("sqlite://"):
        return {
            "pool_pre_ping": False,
        }

    return {
        # Supabase/Render-safe defaults; overridable via env vars.
        "pool_pre_ping": env_bool_fn("DB_POOL_PRE_PING", True),
        "pool_recycle": env_int_fn("DB_POOL_RECYCLE", 180),
        "pool_size": env_int_fn("DB_POOL_SIZE", 3),
        "max_overflow": env_int_fn("DB_MAX_OVERFLOW", 2),
        "pool_timeout": env_int_fn("DB_POOL_TIMEOUT", 30),
        "connect_args": {
            "connect_timeout": env_int_fn("DB_CONNECT_TIMEOUT", 10),
        },
    }
