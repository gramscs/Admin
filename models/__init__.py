"""Moved from models.py and track/models.py."""

from app.models.base import db
from app.models.consignment import Consignment
from app.models.lead import Lead

__all__ = ["db", "Consignment", "Lead"]
