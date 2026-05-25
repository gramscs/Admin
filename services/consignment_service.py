import logging
import uuid
from werkzeug.utils import secure_filename
import base64
import binascii

from app.services import consignment_repo as repo
from app.db.session import transaction

logger = logging.getLogger(__name__)

MAX_POD_IMAGE_BYTES = 5 * 1024 * 1024


def validate_and_normalize_rows(
    rows,
    deleted_ids,
    normalize_consignment_number,
    normalize_status,
    normalize_indian_pincode,
):
    """Validate and normalize incoming rows from client.

    Returns (validated_rows, validated_deleted_ids, errors)
    """
    if not isinstance(rows, list) or not isinstance(deleted_ids, list):
        return None, None, [{"message": "Invalid request payload."}]

    validated_deleted_ids = set()
    for raw_deleted_id in deleted_ids:
        try:
            deleted_id = int(raw_deleted_id)
        except (TypeError, ValueError):
            return (
                None,
                None,
                [{"message": f"Invalid deleted row id: {raw_deleted_id}"}],
            )

        if deleted_id <= 0:
            continue

        validated_deleted_ids.add(deleted_id)

    seen_numbers = set()
    validated_rows = []
    errors = []

    for idx, row in enumerate(rows):
        row_id = row.get("id")
        try:
            consignment_number = normalize_consignment_number(
                row.get("consignment_number")
            )
        except ValueError as error:
            errors.append(
                {"index": idx, "field": "consignment_number", "message": str(error)}
            )
            consignment_number = None

        try:
            status = normalize_status(row.get("status"))
        except ValueError as error:
            errors.append({"index": idx, "field": "status", "message": str(error)})
            status = None

        try:
            pickup_pincode = normalize_indian_pincode(
                row.get("pickup_pincode"), "pickup_pincode"
            )
        except ValueError as error:
            errors.append(
                {"index": idx, "field": "pickup_pincode", "message": str(error)}
            )
            pickup_pincode = None

        try:
            drop_pincode = normalize_indian_pincode(
                row.get("drop_pincode"), "drop_pincode"
            )
        except ValueError as error:
            errors.append(
                {"index": idx, "field": "drop_pincode", "message": str(error)}
            )
            drop_pincode = None

        eta = str(row.get("eta") or "").strip()

        if consignment_number:
            if consignment_number in seen_numbers:
                errors.append(
                    {
                        "index": idx,
                        "field": "consignment_number",
                        "message": f"Duplicate consignment number in sheet: {consignment_number}",
                    }
                )
            seen_numbers.add(consignment_number)

        if row_id is not None:
            try:
                row_id = int(row_id)
            except (TypeError, ValueError):
                errors.append(
                    {
                        "index": idx,
                        "field": "id",
                        "message": f"Invalid row id: {row_id}",
                    }
                )
                row_id = None

            if row_id and row_id <= 0:
                row_id = None

        pickup_tag = str(row.get("pickup_tag") or "").strip()
        pickup_date = str(row.get("pickup_date") or "").strip()
        drop_tag = str(row.get("drop_tag") or "").strip()
        drop_date = str(row.get("drop_date") or "").strip()
        pod_file_data = str(row.get("pod_file_data") or "").strip() or None
        pod_file_name = str(row.get("pod_file_name") or "").strip() or None
        pod_file_type = str(row.get("pod_file_type") or "").strip() or None

        validated_rows.append(
            {
                "id": row_id,
                "consignment_number": consignment_number,
                "status": status,
                "pickup_pincode": pickup_pincode,
                "pickup_address": str(row.get("pickup_address") or "").strip(),
                "pickup_tag": pickup_tag,
                "pickup_date": pickup_date,
                "drop_pincode": drop_pincode,
                "drop_address": str(row.get("drop_address") or "").strip(),
                "drop_tag": drop_tag,
                "drop_date": drop_date,
                "eta": eta,
                "pod_image": str(row.get("pod_image") or "").strip() or None,
                "pod_file_data": pod_file_data,
                "pod_file_name": pod_file_name,
                "pod_file_type": pod_file_type,
            }
        )

    if errors:
        return None, None, errors

    return validated_rows, validated_deleted_ids, []


def _decode_pod_data_url(data_url):
    if not data_url or not isinstance(data_url, str):
        raise ValueError("POD file data is missing.")
    if "," not in data_url:
        raise ValueError("Invalid POD file data.")

    header, encoded = data_url.split(",", 1)
    if not header.startswith("data:image/") or ";base64" not in header:
        raise ValueError("POD file data must be a base64 encoded image.")

    try:
        file_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("POD file data is invalid.")

    if len(file_bytes) > MAX_POD_IMAGE_BYTES:
        raise ValueError("POD image must be smaller than 5 MB.")

    return file_bytes


def apply_consignment_changes(
    validated_rows,
    validated_deleted_ids,
    Consignment,
    db,
    store_pod_bytes_func,
    delete_pod_file_func,
):
    """Apply validated rows and deletions to the database.

    `store_pod_bytes_func(filename, file_bytes, content_type, bucket_name)` and
    `delete_pod_file_func(pod_value)` are injected to keep this function testable.
    Returns (deleted_count, total)
    """
    existing = repo.get_map_all()

    with transaction(db):
        for deleted_id in validated_deleted_ids:
            if deleted_id in existing:
                db.session.delete(existing[deleted_id])

        for row in validated_rows:
            if row["id"]:
                consignment = existing[row["id"]]
            else:
                consignment = Consignment()
                db.session.add(consignment)

            previous_pod_image = getattr(consignment, "pod_image", None)
            new_pod_image = row.get("pod_image")

            if row.get("pod_file_data"):
                pod_bytes = _decode_pod_data_url(row["pod_file_data"])
                original_name = row.get("pod_file_name") or "pod.jpg"
                filename = f"{uuid.uuid4().hex}_{secure_filename(original_name)}"
                new_pod_image = store_pod_bytes_func(
                    filename, pod_bytes, row.get("pod_file_type")
                )

            if (
                previous_pod_image
                and new_pod_image
                and previous_pod_image != new_pod_image
            ):
                try:
                    delete_pod_file_func(previous_pod_image)
                except Exception:
                    logger.exception("Failed to delete previous POD")

            consignment.consignment_number = row["consignment_number"]
            consignment.status = row["status"]
            consignment.pickup_pincode = row["pickup_pincode"]
            consignment.pickup_address = row.get("pickup_address")
            consignment.pickup_tag = row.get("pickup_tag")
            consignment.pickup_date = row.get("pickup_date")
            consignment.drop_pincode = row["drop_pincode"]
            consignment.drop_address = row.get("drop_address")
            consignment.drop_tag = row.get("drop_tag")
            consignment.drop_date = row.get("drop_date")
            consignment.eta = row["eta"]
            consignment.pod_image = new_pod_image

    try:
        total = repo.count()
    except Exception:
        total = None

    deleted_count = len(validated_deleted_ids)
    return deleted_count, total
