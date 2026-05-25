"""Moved from track/models.py."""

from app.models.base import db
from app.models.consignment import Consignment


class TrackConsignment(db.Model):
    __table__ = Consignment.__table__
