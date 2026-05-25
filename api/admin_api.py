import io as _io
import os
import uuid

from flask import Blueprint, current_app, redirect, request, send_file
from werkzeug.utils import secure_filename

from app.admin.auth import require_admin
from app.controllers import build_backup_payload
from app.controllers.responses import json_error, json_success
from app.controllers.serializers import serialize_consignment
from app.db.session import transaction
from app.models import Consignment, Lead, db
from app.services import consignment_repo
from app.services.pod_storage import get_pod_url as _get_pod_url, get_supabase_client as _get_supabase_client

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@admin_api_bp.route("/consignments", methods=["GET"])
@require_admin
def list_consignments():
    page = int(request.args.get("page", 1))
    per_page = int(request.args.get("per_page", 10))
    search = request.args.get("search", "")
    sort_by = request.args.get("sort_by", "id")
    sort_order = request.args.get("sort_order", "asc")
    items, total, pages, has_prev, has_next = consignment_repo.list_paginated(page, per_page, search, sort_by, sort_order)
    return json_success({"items": [serialize_consignment(c) for c in items], "total": total, "pages": pages, "has_prev": has_prev, "has_next": has_next})


@admin_api_bp.route("/consignments/save", methods=["POST"])
@require_admin
def save_consignments_bulk():
    return json_error("Not implemented in prior routes; no logic changes applied.", 501)








@admin_api_bp.route("/consignments/import-template.xlsx", methods=["GET"])
@require_admin
def import_template():
    return json_error("Template endpoint unavailable in current codebase.", 501)


@admin_api_bp.route("/leads", methods=["GET"])
@require_admin
def list_leads():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return json_success({"items": [{"id": l.id, "name": l.name, "email": l.email, "phone": l.phone, "subject": l.subject, "message": l.message, "created_at": l.created_at.isoformat() if l.created_at else None} for l in leads]})


@admin_api_bp.route("/leads/reject-blank-phone", methods=["POST"])
@require_admin
def reject_blank_phone():
    deleted = Lead.query.filter((Lead.phone.is_(None)) | (Lead.phone == "")).delete(synchronize_session=False)
    db.session.commit()
    return json_success({"deleted": deleted})


@admin_api_bp.route("/backup", methods=["GET"])
@require_admin
def backup():
    table_specs = [("consignments", Consignment, {"eta_debug_json"}), ("leads", Lead, set())]
    buffer, metadata = build_backup_payload(table_specs)
    filename = f"backup_{metadata['generated_at'].replace(':', '').replace('-', '').replace('T', '_')}.json"
    return send_file(buffer, as_attachment=True, download_name=filename, mimetype="application/json")


@admin_api_bp.route("/consignments/<int:consignment_id>/pod", methods=["GET"])
@require_admin
def consignment_pod_file(consignment_id):
    consignment = db.session.get(Consignment, consignment_id)
    if not consignment or not getattr(consignment, "pod_image", None):
        return json_error("No POD found.", 404)
    pod_path = consignment.pod_image
    url = _get_pod_url(pod_path, ttl=30)
    if url:
        return redirect(url)
    upload_folder = os.path.join(current_app.instance_path, "uploads")
    safe_path = os.path.normpath(os.path.join(upload_folder, pod_path))
    if not safe_path.startswith(os.path.abspath(upload_folder)):
        return json_error("Invalid POD path.", 400)
    if not os.path.exists(safe_path):
        return json_error("POD file missing.", 404)
    return send_file(safe_path)


@admin_api_bp.route("/consignments/<int:consignment_id>/pod/upload", methods=["POST"])
@require_admin
def consignment_pod_upload(consignment_id):
    upload = request.files.get("file")
    if not upload or not upload.filename:
        return json_error("No file uploaded.", 400)
    if not (upload.mimetype or "").startswith("image/"):
        return json_error("POD must be an image file.", 400)
    consignment = db.session.get(Consignment, consignment_id)
    if not consignment:
        return json_error("Consignment not found.", 404)
    filename = f"{uuid.uuid4().hex}_{secure_filename(upload.filename)}"
    file_bytes = upload.read()
    supa = _get_supabase_client(); bucket = os.getenv("SUPABASE_BUCKET", "pod-uploads")
    if supa:
        try:
            object_path = f"{consignment_id}/{filename}"
            supa.storage.from_(bucket).upload(object_path, _io.BytesIO(file_bytes), {"content-type": upload.mimetype or "application/octet-stream"})
            with transaction(db):
                consignment.pod_image = f"supabase:{bucket}/{object_path}"
            return json_success({"pod_image": consignment.pod_image})
        except Exception:
            db.session.rollback()
    upload_folder = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(upload_folder, exist_ok=True)
    with open(os.path.join(upload_folder, filename), "wb") as fh:
        fh.write(file_bytes)
    with transaction(db):
        consignment.pod_image = filename
    return json_success({"pod_image": filename})


@admin_api_bp.route("/consignments/<int:consignment_id>/pod/delete", methods=["POST"])
@require_admin
def consignment_pod_delete(consignment_id):
    consignment = db.session.get(Consignment, consignment_id)
    if not consignment or not getattr(consignment, "pod_image", None):
        return json_error("No POD to delete.", 404)
    with transaction(db):
        consignment.pod_image = None
    return json_success()
