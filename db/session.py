"""Moved from utils/db.py."""

from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


@contextmanager
def transaction(db):
    """Context manager to commit or rollback a DB session.

    Usage:
        with transaction(db):
            db.session.add(obj)
            ...
    Commits on success, rolls back on exception.
    """
    try:
        yield db.session
        db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            logger.exception("Failed to rollback DB session")
        raise
