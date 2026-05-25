import logging
import sys
import uuid
from logging.handlers import RotatingFileHandler

from flask import g, request, has_request_context

__all__ = ["init_app", "RequestIdFilter"]


def _current_request_id():
    try:
        if has_request_context():
            return getattr(g, "request_id", None) or request.headers.get("X-Request-ID")
    except Exception:
        pass
    return None


class RequestIdFilter(logging.Filter):
    """Logging filter that injects a request id into log records when available.

    Records will have a `request_id` attribute (or '-') so formatters can include it.
    """

    def filter(self, record):
        try:
            record.request_id = _current_request_id() or "-"
        except Exception:
            record.request_id = "-"
        return True


def init_app(app, level=None, logfile=None, max_bytes=10 * 1024 * 1024, backup_count=5):
    """Initialize structured logging for the given Flask `app`.

    - `level` may be a logging level or string (e.g. 'INFO'). If omitted, uses
      `app.config['LOG_LEVEL']` or 'INFO'.
    - If `logfile` is provided (or `app.config['LOG_FILE']`), a rotating file
      handler will be created in addition to stdout.

    This function also registers a `before_request` handler to populate
    `g.request_id` from the `X-Request-ID` header (or generate a UUID).
    """
    conf_level = level or app.config.get("LOG_LEVEL", "INFO")
    if isinstance(conf_level, str):
        conf_level = getattr(logging, conf_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(conf_level)

    fmt = "%(asctime)s %(levelname)s [%(name)s] %(request_id)s %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # Clear existing root handlers to avoid duplicate logs in some environments
    for h in list(root.handlers):
        root.removeHandler(h)

    stream = logging.StreamHandler(sys.stdout)
    stream.setLevel(conf_level)
    stream.setFormatter(formatter)
    stream.addFilter(RequestIdFilter())
    root.addHandler(stream)

    configured_logfile = logfile or app.config.get("LOG_FILE")
    if configured_logfile:
        fh = RotatingFileHandler(
            configured_logfile, maxBytes=max_bytes, backupCount=backup_count
        )
        fh.setLevel(conf_level)
        fh.setFormatter(formatter)
        fh.addFilter(RequestIdFilter())
        root.addHandler(fh)

    # Mirror handlers onto the Flask app logger and set its level
    app.logger.handlers = root.handlers
    app.logger.setLevel(conf_level)

    @app.before_request
    def _set_request_id():
        # Respect an incoming request id header, else generate one for correlation
        rid = (
            request.headers.get("X-Request-ID")
            or request.headers.get("X-RequestID")
            or str(uuid.uuid4())
        )
        g.request_id = rid
