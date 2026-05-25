"""Shared controller helpers for backup and serialization.

This module centralizes common controller logic so routes can remain thin
and focused on HTTP concerns.
"""
from datetime import datetime, UTC
import io
import json
import logging

logger = logging.getLogger(__name__)


def to_json_safe(value):
    """Convert model values into JSON-serializable primitives."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def serialize_model_row(model_row, excluded_fields=None):
    excluded_fields = set(excluded_fields or [])
    serialized = {}

    for column in model_row.__table__.columns:
        if column.name in excluded_fields:
            continue
        serialized[column.name] = to_json_safe(getattr(model_row, column.name))

    return serialized


def build_backup_payload(table_specs):
    """Given table_specs [(name, model_class, excluded_fields), ...],
    return a BytesIO buffer containing JSON and metadata dict.
    """
    backup_payload = {}
    table_counts = {}

    for table_name, model_class, excluded_fields in table_specs:
        rows = model_class.query.order_by(model_class.id.asc()).all()
        backup_payload[table_name] = [
            serialize_model_row(row, excluded_fields=excluded_fields) for row in rows
        ]
        table_counts[table_name] = len(rows)

    started_at = datetime.now(UTC).isoformat()
    backup_payload["metadata"] = {
        "generated_at": started_at,
        "total_rows": sum(table_counts.values()),
        "table_counts": table_counts,
    }

    backup_json = json.dumps(backup_payload, ensure_ascii=True, indent=2)
    buffer = io.BytesIO()
    buffer.write(backup_json.encode("utf-8"))
    buffer.seek(0)

    return buffer, backup_payload["metadata"]
