"""Shared error helpers used across route modules."""


def is_missing_column_error(error):
    """Return True when the database rejected a query because a column is absent.

    Recognizes the common Postgres error code and the SQLAlchemy/psycopg class name.
    """
    original = getattr(error, "orig", None)
    if original is None:
        return False

    pgcode = getattr(original, "pgcode", None)
    if pgcode == "42703":
        return True

    return original.__class__.__name__ == "UndefinedColumn"
