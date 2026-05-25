import io
import logging
import os
import re

from flask import Blueprint, current_app, redirect, request, send_file

from app import limiter
from app.controllers.responses import json_error, json_success
from app.db.session import transaction
from app.models import Consignment, Lead, db
from app.services.pod_storage import get_pod_url

logger = logging.getLogger(__name__)
public_api_bp = Blueprint("public_api", __name__, url_prefix="/api/public")
CONSIGNMENT_NUMBER_PATTERN = re.compile(r"^[A-Za-z0-9]{1,16}$")


def lookup_consignment(number: str) -> dict | None:
    consignment = Consignment.query.filter_by(consignment_number=number).first()
    if not consignment:
        return None
    return {
        "consignment_number": consignment.consignment_number,
        "status": consignment.status,
        "pickup_pincode": consignment.pickup_pincode,
        "pickup_date": consignment.pickup_date,
        "drop_pincode": consignment.drop_pincode,
        "drop_date": consignment.drop_date,
        "eta": consignment.eta,
        "pod_url": get_pod_url(consignment.pod_image, ttl=int(os.getenv("SUPABASE_SIGNED_URL_TTL", "30"))) if getattr(consignment, "pod_image", None) else None,
    }


@public_api_bp.route('/track/<consignment_number>', methods=['GET'])
def track_consignment(consignment_number):
    number = (consignment_number or "").strip().upper()
    if not number or not CONSIGNMENT_NUMBER_PATTERN.fullmatch(number):
        return json_error("Invalid consignment number format.", 400)
    result = lookup_consignment(number)
    if not result:
        return json_error("Consignment not found.", 404)
    return json_success(result)


@public_api_bp.route("/pod/<consignment_number>", methods=["GET"])
def pod_redirect(consignment_number):
    number = (consignment_number or "").strip().upper()
    if not number:
        return json_error("Consignment number required.", 400)
    consignment = Consignment.query.filter_by(consignment_number=number).first()
    if not consignment or not getattr(consignment, "pod_image", None):
        return json_error("No POD found.", 404)
    pod_path = consignment.pod_image
    url = get_pod_url(pod_path, ttl=int(os.getenv("SUPABASE_SIGNED_URL_TTL", "30")))
    if url:
        return redirect(url)
    upload_folder = os.path.join(current_app.instance_path, "uploads")
    safe_path = os.path.normpath(os.path.join(upload_folder, pod_path))
    if not safe_path.startswith(os.path.abspath(upload_folder)):
        return json_error("Invalid POD path.", 400)
    if not os.path.exists(safe_path):
        return json_error("POD file missing.", 404)
    return send_file(safe_path, as_attachment=True, download_name=f"{number}_pod.jpg")


@public_api_bp.route('/contact', methods=['POST'])
@limiter.limit('10 per minute')
def submit_contact():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    phone = (data.get("phone") or "").strip()
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if not name or not email or not phone or not message:
        return json_error("Please fill in all required fields.", 400)

    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email):
        return json_error("Please enter a valid email address.", 400)

    try:
        lead = Lead(name=name, email=email, phone=phone, subject=subject, message=message)
        with transaction(db) as session:
            session.add(lead)
        logger.info("Contact lead saved to database for %s", email)
    except Exception as e:
        logger.error(f"Failed to save contact lead: {e}")
        return json_error("There was an issue submitting your message. Please try again.", 500)

    return json_success({"message": "Message sent successfully! We'll get back to you soon."})
