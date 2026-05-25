import os
import logging

logger = logging.getLogger(__name__)


def _resolve_secret_key() -> str:
    configured = os.environ.get("SECRET_KEY", "").strip()
    if not configured:
        raise RuntimeError(
            "SECRET_KEY is required and must be set in environment variables."
        )
    return configured


SECRET_KEY = _resolve_secret_key()
