"""Compatibility module for consignment model/database handles.

Legacy panel/list helper functions were removed after Flask-Admin migration.
"""

from app.models import Consignment, db

__all__ = ["Consignment", "db"]
