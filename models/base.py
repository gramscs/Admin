"""Single source of truth for the SQLAlchemy db instance."""

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()
