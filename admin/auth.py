"""
Session-based authentication utilities for the admin module.

Environment variables
---------------------
SECRET_KEY           Flask session signing key (required by app config).
ADMIN_USERNAME       Admin login username (default: admin).
ADMIN_PASSWORD_HASH  Werkzeug-hashed password for the admin user (required).
"""

import os
from functools import wraps

from flask import redirect, request, session, url_for
from app.controllers.responses import json_error
from werkzeug.security import check_password_hash

ADMIN_USERNAME: str = (os.environ.get("ADMIN_USERNAME") or "admin").strip() or "admin"
# Prefer an explicit password hash, but allow an unhashed ADMIN_PASSWORD for convenience
# or generate a dev default when running in development mode.
ADMIN_PASSWORD_HASH: str = (os.environ.get("ADMIN_PASSWORD_HASH") or "").strip()
ADMIN_PASSWORD_PLAIN: str = (os.environ.get("ADMIN_PASSWORD") or "").strip()

if not ADMIN_PASSWORD_HASH:
    if ADMIN_PASSWORD_PLAIN:
        # Derive hash from provided plain password
        from werkzeug.security import generate_password_hash

        ADMIN_PASSWORD_HASH = generate_password_hash(ADMIN_PASSWORD_PLAIN)
    else:
        # In development, provide a safe default to simplify local runs.
        if os.getenv("FLASK_ENV", "").strip().lower() == "development":
            from werkzeug.security import generate_password_hash

            ADMIN_PASSWORD_HASH = generate_password_hash("admin-pass")
            import logging

            logging.getLogger(__name__).warning(
                "ADMIN_PASSWORD_HASH not set; using development default password (admin-pass)."
            )
        else:
            raise RuntimeError(
                "ADMIN_PASSWORD_HASH is required and must be set in environment variables."
            )

ADMIN_SESSION_KEY = "admin_authenticated"
ADMIN_SESSION_USERNAME_KEY = "admin_username"


def check_admin_credentials(username: str, password: str) -> bool:
    """Return True when username and password match configured admin credentials."""
    if username != ADMIN_USERNAME:
        return False

    # Allow direct match against an unhashed ADMIN_PASSWORD for local/dev convenience.
    if ADMIN_PASSWORD_PLAIN:
        try:
            if password == ADMIN_PASSWORD_PLAIN:
                return True
        except Exception:
            pass

    # Fallback to hashed password verification
    try:
        return check_password_hash(ADMIN_PASSWORD_HASH, password)
    except Exception:
        return False


def login_admin(username: str | None = None) -> None:
    """Mark the current session as authenticated admin."""
    session[ADMIN_SESSION_KEY] = True
    if username:
        session[ADMIN_SESSION_USERNAME_KEY] = username


def logout_admin() -> None:
    """Clear admin authentication state from session."""
    session.pop(ADMIN_SESSION_KEY, None)
    session.pop(ADMIN_SESSION_USERNAME_KEY, None)


def is_admin_authenticated() -> bool:
    """Return True when current session is authenticated as admin."""
    return bool(session.get(ADMIN_SESSION_KEY))


def require_admin(f):
    """View decorator that enforces admin session authentication."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if is_admin_authenticated():
            return f(*args, **kwargs)

        wants_json = (
            request.path.startswith("/api/")
            or "application/json" in (request.accept_mimetypes.best or "")
            or (request.content_type or "").startswith("application/json")
        )
        if wants_json:
            return json_error("Authentication required", 401)

        return redirect(url_for("admin.login"))

    return decorated
