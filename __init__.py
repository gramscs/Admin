from flask import (
    Flask,
    send_from_directory,
    request,
    render_template,
    jsonify,
    Response,
)
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import sys
from cachelib import FileSystemCache
from functools import wraps
import hashlib
import os
import logging
from sqlalchemy import text
from werkzeug.exceptions import HTTPException

if __name__ != "app":
    sys.modules.setdefault("app", sys.modules[__name__])

from app.models import db as models_db
from app.db.maintenance import ensure_consignment_columns_async

try:
    from app.utils.logging import init_app as init_logging
except ImportError:
    from utils.logging import init_app as init_logging

# Configure logging
logging.basicConfig(
    level=getattr(
        logging, os.getenv("LOG_LEVEL", "INFO").strip().upper(), logging.INFO
    ),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _resolve_rate_limit_storage_uri():
    configured = os.getenv("RATELIMIT_STORAGE_URI", "").strip()
    if configured:
        return configured

    redis_url = os.getenv("REDIS_URL", "").strip()
    if redis_url:
        return redis_url

    return "memory://"


def _env_bool(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name, default):
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning(
            "Invalid integer for %s: %s. Using default %s", name, raw, default
        )
        return default

from app.db.config import require_database_uri, build_engine_options
from app.db.seed import seed_development_data


# Simple cache shim exposing `cached(timeout=...)` decorator.
class CacheShim:
    def __init__(self, cache_dir="flask_cache", default_timeout=300):
        self._cache = FileSystemCache(cache_dir)
        self.default_timeout = default_timeout

    def _make_key(self):
        key = request.path
        if request.query_string:
            key += "?" + request.query_string.decode()
        return hashlib.sha1(key.encode("utf-8")).hexdigest()

    def cached(self, timeout=None):
        def decorator(func):
            @wraps(func)
            def wrapped(*args, **kwargs):
                try:
                    cache_key = self._make_key()
                    cached_val = self._cache.get(cache_key)
                    if cached_val is not None:
                        return cached_val

                    result = func(*args, **kwargs)
                    self._cache.set(cache_key, result, timeout or self.default_timeout)
                    return result

                except Exception as e:
                    logger.error(f"Cache error: {e}")
                    return func(*args, **kwargs)

            return wrapped

        return decorator


# cache instance
cache = CacheShim()

# limiter instance shared across the application
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_resolve_rate_limit_storage_uri(),
)


def _load_env_file(path):
    """Load simple KEY=VALUE pairs from a local env file if it exists."""
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value


def _should_load_local_env_files():
    # Render injects env vars directly; avoid reading local files in production by default.
    if _env_bool("LOAD_LOCAL_ENV_FILES", False):
        return True
    return os.getenv("FLASK_ENV", "").strip().lower() != "production"


def _should_auto_create_tables():
    if os.getenv("FLASK_ENV", "").strip().lower() == "production":
        if _env_bool("AUTO_CREATE_TABLES", False):
            logger.warning(
                "Ignoring AUTO_CREATE_TABLES in production; manage schema externally."
            )
        return False

    return _env_bool("AUTO_CREATE_TABLES", default=True)


if _should_load_local_env_files():
    _load_env_file(".env.local")
    _load_env_file(".env")


def _build_content_security_policy():
    return (
        "default-src 'self'; "
        "base-uri 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'self'; "
        "form-action 'self'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data: https://fonts.gstatic.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
        "connect-src 'self'; "
        "frame-src 'self' https://www.google.com https://maps.google.com;"
    )


def _apply_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
        )
        response.headers.setdefault(
            "Content-Security-Policy", _build_content_security_policy()
        )

        if (
            request.is_secure
            or request.headers.get("X-Forwarded-Proto", "").lower() == "https"
        ):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        return response


def create_app():
    app = Flask(__name__)
    # Log effective PORT so platform startup probes can be debugged in deployment logs.
    try:
        effective_port = os.getenv("PORT", "10000")
        logger.info("STARTUP: effective PORT=%s", effective_port)
    except Exception:
        logger.exception("Failed to log STARTUP port")

    # DATABASE CONFIG
    db_uri = require_database_uri()
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    app.config["SESSION_COOKIE_SECURE"] = _env_bool(
        "SESSION_COOKIE_SECURE",
        default=os.getenv("FLASK_ENV", "").strip().lower() == "production",
    )
    app.config["PREFERRED_URL_SCHEME"] = (
        "https"
        if os.getenv("FLASK_ENV", "").strip().lower() == "production"
        else "http"
    )

    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = build_engine_options(
        db_uri, _env_bool, _env_int
    )

    app.config["RATELIMIT_STORAGE_URI"] = _resolve_rate_limit_storage_uri()
    app.config["RATELIMIT_HEADERS_ENABLED"] = True
    app.config.from_object("app.config")

    models_db.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": os.getenv("ALLOWED_ORIGINS", "*")}})
    init_logging(app)

    auto_create_tables = _should_auto_create_tables()
    if auto_create_tables:
        try:
            if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite://"):
                ensure_consignment_columns_async(
                    app.config["SQLALCHEMY_DATABASE_URI"], logger
                )
        except Exception:
            logger.exception("Failed to start consignment schema repair")

        with app.app_context():
            models_db.create_all()
            seed_development_data(models_db, app)
    else:
        try:
            if not app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite://"):
                ensure_consignment_columns_async(
                    app.config["SQLALCHEMY_DATABASE_URI"], logger
                )
        except Exception:
            logger.exception("Failed to start consignment schema repair")

        logger.info("AUTO_CREATE_TABLES disabled. Skipping db.create_all() at startup.")
        logger.info("Consignment schema repair runs asynchronously in production.")

    from app.frontend import frontend_bp
    from app.api.public import public_api_bp
    from app.api.admin_api import admin_api_bp
    from app.admin import admin_bp
    from app.admin.flask_admin_setup import init_flask_admin

    app.register_blueprint(frontend_bp)
    app.register_blueprint(public_api_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(admin_bp)

    # Debug: log registered blueprint names before initializing Flask-Admin
    try:
        logger.info("Registered blueprints before Flask-Admin init: %s", list(app.blueprints.keys()))
    except Exception:
        pass

    try:
        init_flask_admin(app)
    except Exception:
        logger.exception("Flask-Admin failed to initialize; continuing without admin UI")
    _apply_security_headers(app)

    @app.route("/health")
    def health():
        return (
            jsonify(
                {
                    "status": "ok",
                    "message": "Application is healthy",
                }
            ),
            200,
        )

    @app.route("/health/db")
    def database_health():
        try:
            models_db.session.execute(text("SELECT 1"))
            return (
                jsonify(
                    {
                        "status": "ok",
                        "database": "postgresql",
                        "message": "Database connection is healthy",
                    }
                ),
                200,
            )
        except Exception as e:
            logger.error("Database health check failed: %s", e)
            return (
                jsonify(
                    {
                        "status": "error",
                        "database": "postgresql",
                        "message": "Database connection failed",
                    }
                ),
                503,
            )

    @app.route("/favicon.ico")
    def favicon():
        return send_from_directory(frontend_bp.static_folder, "favicon.ico")

    # Global error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        logger.warning(f"404 error: {request.url}")
        if request.path.startswith("/api/") or request.accept_mimetypes.accept_json:
            return jsonify({"error": "Resource not found"}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"500 error: {e}")
        if request.path.startswith("/api/") or request.accept_mimetypes.accept_json:
            return jsonify({"error": "Internal server error"}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(403)
    def forbidden(e):
        logger.warning(f"403 error: {request.url}")
        if request.path.startswith("/api/") or request.accept_mimetypes.accept_json:
            return jsonify({"error": "Access forbidden"}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(429)
    def rate_limited(e):
        logger.warning(
            "Rate limit exceeded for %s %s from %s",
            request.method,
            request.path,
            request.headers.get("X-Forwarded-For", request.remote_addr),
        )

        message = "Too many requests. Please try again later."
        if (
            request.path.startswith("/api/")
            or request.accept_mimetypes.accept_json
            or request.is_json
        ):
            response = jsonify({"error": message})
            response.status_code = 429
            return response

        return Response(message, status=429, mimetype="text/plain")

    @app.errorhandler(Exception)
    def handle_exception(e):
        if isinstance(e, HTTPException):
            return e
        logger.error(f"Unhandled exception: {e}", exc_info=True)
        wants_json = request.path.startswith("/api/") or request.accept_mimetypes.accept_json
        if wants_json:
            # In development show the traceback in the JSON response to aid debugging.
            if os.getenv("FLASK_ENV", "").strip().lower() == "development":
                import traceback

                tb = traceback.format_exc()
                return (
                    jsonify({"error": str(e) or "Exception", "traceback": tb}),
                    500,
                )

            return jsonify({"error": "An unexpected error occurred"}), 500

        return render_template("errors/500.html"), 500

    return app
